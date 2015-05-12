"""
Compact Font File specified in Adobe Technical Note #5176
Version 1.0 dated 2003-Dec-4
"""

import struct
"""
From struct docs:

Format		C Type					Python type			Standard size		Notes
----------------------------------------------------------------------------------
x			pad byte				no value	 	 
c			char					bytes of length 1	1	 
b			signed char				integer				1	(1),(3)
B			unsigned char			integer				1	(3)
?			_Bool					bool				1	(1)
h			short					integer				2	(3)
H			unsigned short			integer				2	(3)
i			int						integer				4	(3)
I			unsigned int			integer				4	(3)
l			long					integer				4	(3)
L			unsigned long			integer				4	(3)
q			long long				integer				8	(2), (3)
Q			unsigned long long		integer				8	(2), (3)
n			ssize_t					integer	 				(4)
N			size_t					integer	 				(4)
f			float					float				4	(5)
d			double					float				8	(5)
s			char[]					bytes
p			char[]					bytes
P			void *					integer	 				(6)

Character		Byte order				Size		Alignment
--------------------------------------------------------------
@				native					native		native
=				native					standard	none
<				little-endian			standard	none
>				big-endian				standard	none
!				network (= big-endian)	standard	none
"""

class _CFFUnpacker:
	def __init__(self, txt):
		self.buf = bytes(txt, 'latin-1')
		self.offset = 0

	def _unpack(self, fmt):
		# Always big-endian
		fmt = ">" + fmt

		# Get data
		ret = struct.unpack_from(fmt, self.buf, self.offset)

		# Adjust offset
		self.offset += struct.calcsize(fmt)

		return ret

	def Get8(self):				return self._unpack("B")[0]
	def Get16(self):			return self._unpack("H")[0]
	def Get24(self):
		b = self._unpack("BBB")
		return (b[0]<<16)+(b[1]<<8)+b[2]
	def Get32(self):			return self._unpack("L")[0]
	def GetOffSize(self):		return self._unpack("B")[0]
	def GetSID(self):			return self._unpack("H")[0]

	def GetOffsets(self, offSize, count):
		if offSize == 1:		return [self.Get8() for i in range(count)]
		elif offSize == 2:		return [self.Get16() for i in range(count)]
		elif offSize == 3:		return [self.Get24() for i in range(count)]
		elif offSize == 4:		return [self.Get32() for i in range(count)]
		else:
			raise ValueError("Unexpected offSize value: %d" % offSize)

	def GetHeader(self):
		#print(['offset', self.offset])
		header = {}
		header['major'] = self.Get8()
		header['minor'] = self.Get8()
		header['hdrSize'] = self.Get8()
		header['offSize'] = self.GetOffSize()

		#print(['offset a', self.offset])

		return header

	def GetIndex(self):
		index = {}
		#print(['offset a', self.offset])

		index['count'] = self.Get16()
		if index['count'] == 0:
			return
		#print(['offset b', self.offset])

		index['offSize'] = self.GetOffSize()
		#print(['offset c', self.offset])
		offsets = self.GetOffsets(index['offSize'], index['count']+1)
		#print(['offset d', self.offset])

		index['offsets'] = []
		index['data'] = []

		for offset in range( len(offsets)-1 ):
			sidx = offsets[offset]
			eidx = offsets[offset+1]

			# Offsets is a two-tuple of the data block (with offsets based from last byte of offSize data)
			index['offsets'].append( (sidx,eidx) )

			# sidx and eidx are based on last byte of the offSize data, so subtract one
			index['data'].append( self.buf[self.offset + sidx - 1:self.offset + eidx - 1] )

		# Last offset is the jump over the data
		self.offset += offsets[-1] -1
		#print(['offset e', self.offset])

		return index

	def ParseTopDict(self, dat):
		ret = []

		offset = 0
		while offset < len(dat):
			if dat[offset] == 255 or dat[offset] == 31:
				raise ValueError("Found reserved Top Dict value: %d" % dat[offset])

			# Numbers
			if dat[offset] >= 32 and dat[offset] <= 246:
				# One byte number
				ret.append(dat[offset])
				offset += 1
			elif dat[offset] >= 247 and dat[offset] <= 250:
				# Two byte number
				ret.append( ((dat[offset]-247)<<8) + dat[offset+1] + 108 )
				offset += 2
			elif dat[offset] >= 251 and dat[offset] <= 254:
				# Two byte number
				ret.append( -((dat[offset]-251)<<8) - dat[offset+1] - 108 )
				offset += 2
			elif dat[offset] == 28:
				# Three byte number
				ret.append( (dat[offset+1]<<8) + dat[offset+2] )
				offset += 3
			elif dat[offset] == 29:
				# Five byte number
				ret.append( (dat[offset+1]<<24) + (dat[offset+2]<<16) + (dat[offset+3]<<8) + dat[offset+4] )
				offset += 5

			# Real-value: Tabel 5 of CF spec (don't forget padding nibbles)
			elif dat[offset] == 30:
				raise NotImplementedError("Real value number (30) not implemented yet")

			# Non-number
			elif dat[offset] == 0:
				ret.append('version')
				offset += 1
			elif dat[offset] == 1:
				ret.append('Notice')
				offset += 1
			elif dat[offset] == 2:
				ret.append('FullName')
				offset += 1
			elif dat[offset] == 3:
				ret.append('FamilyName')
				offset += 1
			elif dat[offset] == 4:
				ret.append('Weight')
				offset += 1
			elif dat[offset] == 5:
				ret.append('FontBBox')
				offset += 1
			elif dat[offset] == 6:
				ret.append('BlueValues')
				offset += 1
			elif dat[offset] == 7:
				ret.append('OtherBlues')
				offset += 1
			elif dat[offset] == 8:
				ret.append('FamilyBlues')
				offset += 1
			elif dat[offset] == 9:
				ret.append('FamilyOtherBlues')
				offset += 1
			elif dat[offset] == 10:
				ret.append('StdHW')
				offset += 1
			elif dat[offset] == 11:
				ret.append('StdVW')
				offset += 1
			elif dat[offset] == 13:
				ret.append('UniqueID')
				offset += 1
			elif dat[offset] == 14:
				ret.append('XUID')
				offset += 1
			elif dat[offset] == 15:
				ret.append('charset')
				offset += 1
			elif dat[offset] == 16:
				ret.append('Encoding')
				offset += 1
			elif dat[offset] == 17:
				ret.append('CharStrings')
				offset += 1
			elif dat[offset] == 18:
				ret.append('Private')
				offset += 1
			elif dat[offset] == 19:
				ret.append('Subrs')
				offset += 1
			elif dat[offset] == 20:
				ret.append('defaultWidthX')
				offset += 1
			elif dat[offset] == 21:
				ret.append('nominalWidthX')
				offset += 1
			elif dat[offset] == 12:
				if dat[offset+1] == 0:
					ret.append('Copyright')
					offset += 2
				elif dat[offset+1] == 1:
					ret.append('isFixedPitch')
					offset += 2
				elif dat[offset+1] == 2:
					ret.append('ItalicAngle')
					offset += 2
				elif dat[offset+1] == 3:
					ret.append('UnderlinePosition')
					offset += 2
				elif dat[offset+1] == 4:
					ret.append('UnderlineThickness')
					offset += 2
				elif dat[offset+1] == 5:
					ret.append('PaintType')
					offset += 2
				elif dat[offset+1] == 6:
					ret.append('CharstringType')
					offset += 2
				elif dat[offset+1] == 7:
					ret.append('FontMatrix')
					offset += 2
				elif dat[offset+1] == 8:
					ret.append('StrokeWidth')
					offset += 2
				elif dat[offset+1] == 20:
					ret.append('SyntheticBase')
					offset += 2
				elif dat[offset+1] == 21:
					ret.append('PostScript')
					offset += 2
				elif dat[offset+1] == 22:
					ret.append('BaseFontName')
					offset += 2
				elif dat[offset+1] == 23:
					ret.append('BaseFontBlend')
					offset += 2
				elif dat[offset+1] == 30:
					ret.append('ROS')
					offset += 2
				elif dat[offset+1] == 31:
					ret.append('CIDFontVersion')
					offset += 2
				elif dat[offset+1] == 32:
					ret.append('CIDFontRevision')
					offset += 2
				elif dat[offset+1] == 33:
					ret.append('CIDFontType')
					offset += 2
				elif dat[offset+1] == 34:
					ret.append('CIDCount')
					offset += 2
				elif dat[offset+1] == 35:
					ret.append('UIDBase')
					offset += 2
				elif dat[offset+1] == 36:
					ret.append('FDArray')
					offset += 2
				elif dat[offset+1] == 37:
					ret.append('FDSelect')
					offset += 2
				elif dat[offset+1] == 38:
					ret.append('FontName')
					offset += 2
				else:
					raise ValueError("Got escape character 12 at offset %d (x%X) with an unknown value afterward: %d (x%X)" % (offset,offset, dat[offset+1],dat[offset+1]))
			else:
				raise ValueError("Got unknown operand %d (x%x)" % (dat[offset],dat[offset]))

		return ret

def TokenizeString(txt):
	u = _CFFUnpacker(txt)

	for i in range(0, len(u.buf), 8):
		print("%4x | %02x %02x %02x %02x   %02x %02x %02x %02x" % (i, u.buf[i], u.buf[i+1], u.buf[i+2], u.buf[i+3], u.buf[i+4], u.buf[i+5], u.buf[i+6], u.buf[i+7]))
		if i > 1000: break

	header = u.GetHeader()

	print(['header', "%X"%u.offset, header])

	name_index = u.GetIndex()

	print(['Name INDEX', "%X"%u.offset, name_index])

	name_dict_index = u.GetIndex()

	print(['Top DICT INDEX', "%X"%u.offset, name_dict_index])

	fonts = []
	for font in name_dict_index['data']:
		f = u.ParseTopDict(font)
		fonts.append(f)
		print(['font', font, f])

	string_index = u.GetIndex()

	print(['String INDEX', "%X"%u.offset, string_index])

	global_subr_index = u.GetIndex()

	print(['Global Subr INDEX', "%X"%u.offset, global_subr_index])

	# Read Encoding section if present in Top Dict
	if 'Encoding' in fonts[0]:
		pass

	# Read charsets section if present in Top Dict
	if 'charset' in fonts[0]:
		pass

	# FDSelect
	# CharStrings INDEX
	# Font DICT INDEX
	# Private DICT
	# Local Subr INDEX
	# Copyright and trademark notices

	raise NotImplementedError()


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

StandardStrings = {}
StandardStrings[0] = '.notdef'
StandardStrings[1] = 'space'
StandardStrings[2] = 'exclam'
StandardStrings[3] = 'quotedbl'
StandardStrings[4] = 'numbersign'
StandardStrings[5] = 'dollar'
StandardStrings[6] = 'percent'
StandardStrings[7] = 'ampersand'
StandardStrings[8] = 'quoteright'
StandardStrings[9] = 'parenleft'
StandardStrings[10] = 'parenright'
StandardStrings[11] = 'asterisk'
StandardStrings[12] = 'plus'
StandardStrings[13] = 'comma'
StandardStrings[14] = 'hyphen'
StandardStrings[15] = 'period'
StandardStrings[16] = 'slash'
StandardStrings[17] = 'zero'
StandardStrings[18] = 'one'
StandardStrings[19] = 'two'
StandardStrings[20] = 'three'
StandardStrings[21] = 'four'
StandardStrings[22] = 'five'
StandardStrings[23] = 'six'
StandardStrings[24] = 'seven'
StandardStrings[25] = 'eight'
StandardStrings[26] = 'nine'
StandardStrings[27] = 'colon'
StandardStrings[28] = 'semicolon'
StandardStrings[29] = 'less'
StandardStrings[30] = 'equal'
StandardStrings[31] = 'greater'
StandardStrings[32] = 'question'
StandardStrings[33] = 'at'
StandardStrings[34] = 'A'
StandardStrings[35] = 'B'
StandardStrings[36] = 'C'
StandardStrings[37] = 'D'
StandardStrings[38] = 'E'
StandardStrings[39] = 'F'
StandardStrings[40] = 'G'
StandardStrings[41] = 'H'
StandardStrings[42] = 'I'
StandardStrings[43] = 'J'
StandardStrings[44] = 'K'
StandardStrings[45] = 'L'
StandardStrings[46] = 'M'
StandardStrings[47] = 'N'
StandardStrings[48] = 'O'
StandardStrings[49] = 'P'
StandardStrings[50] = 'Q'
StandardStrings[51] = 'R'
StandardStrings[52] = 'S'
StandardStrings[53] = 'T'
StandardStrings[54] = 'U'
StandardStrings[55] = 'V'
StandardStrings[56] = 'W'
StandardStrings[57] = 'X'
StandardStrings[58] = 'Y'
StandardStrings[59] = 'Z'
StandardStrings[60] = 'bracketleft'
StandardStrings[61] = 'backslash'
StandardStrings[62] = 'bracketright'
StandardStrings[63] = 'asciicircum'
StandardStrings[64] = 'underscore'
StandardStrings[65] = 'quoteleft'
StandardStrings[66] = 'a'
StandardStrings[67] = 'b'
StandardStrings[68] = 'c'
StandardStrings[69] = 'd'
StandardStrings[70] = 'e'
StandardStrings[71] = 'f'
StandardStrings[72] = 'g'
StandardStrings[73] = 'h'
StandardStrings[74] = 'i'
StandardStrings[75] = 'j'
StandardStrings[76] = 'k'
StandardStrings[77] = 'l'
StandardStrings[78] = 'm'
StandardStrings[79] = 'n'
StandardStrings[80] = 'o'
StandardStrings[81] = 'p'
StandardStrings[82] = 'q'
StandardStrings[83] = 'r'
StandardStrings[84] = 's'
StandardStrings[85] = 't'
StandardStrings[86] = 'u'
StandardStrings[87] = 'v'
StandardStrings[88] = 'w'
StandardStrings[89] = 'x'
StandardStrings[90] = 'y'
StandardStrings[91] = 'z'
StandardStrings[92] = 'braceleft'
StandardStrings[93] = 'bar'
StandardStrings[94] = 'braceright'
StandardStrings[95] = 'asciitilde'
StandardStrings[96] = 'exclamdown'
StandardStrings[97] = 'cent'
StandardStrings[98] = 'sterling'
StandardStrings[99] = 'fraction'
StandardStrings[100] = 'yen'
StandardStrings[101] = 'florin'
StandardStrings[102] = 'section'
StandardStrings[103] = 'currency'
StandardStrings[104] = 'quotesingle'
StandardStrings[105] = 'quotedblleft'
StandardStrings[106] = 'guillemotleft'
StandardStrings[107] = 'guilsinglleft'
StandardStrings[108] = 'guilsinglright'
StandardStrings[109] = 'fi'
StandardStrings[110] = 'fl'
StandardStrings[111] = 'endash'
StandardStrings[112] = 'dagger'
StandardStrings[113] = 'daggerdbl'
StandardStrings[114] = 'periodcentered'
StandardStrings[115] = 'paragraph'
StandardStrings[116] = 'bullet'
StandardStrings[117] = 'quotesinglbase'
StandardStrings[118] = 'quotedblbase'
StandardStrings[119] = 'quotedblright'
StandardStrings[120] = 'quillemotright'
StandardStrings[121] = 'ellipsis'
StandardStrings[122] = 'perthousand'
StandardStrings[123] = 'questiondown'
StandardStrings[124] = 'grave'
StandardStrings[125] = 'acute'
StandardStrings[126] = 'circumflex'
StandardStrings[127] = 'tilde'
StandardStrings[128] = 'macron'
StandardStrings[129] = 'breve'
StandardStrings[130] = 'dotaccent'
StandardStrings[131] = 'dieresis'
StandardStrings[132] = 'ring'
StandardStrings[133] = 'cedilla'
StandardStrings[134] = 'hungarumlaut'
StandardStrings[135] = 'ogonek'
StandardStrings[136] = 'caron'
StandardStrings[137] = 'emdash'
StandardStrings[138] = 'AE'
StandardStrings[139] = 'ordfeminine'
StandardStrings[140] = 'Lslash'
StandardStrings[141] = 'Oslash'
StandardStrings[142] = 'OE'
StandardStrings[143] = 'ordmasculine'
StandardStrings[144] = 'ae'
StandardStrings[145] = 'dotlessi'
StandardStrings[146] = 'lslash'
StandardStrings[147] = 'oslash'
StandardStrings[148] = 'oe'
StandardStrings[149] = 'germandbls'
StandardStrings[150] = 'onesuperior'
StandardStrings[151] = 'logicalnot'
StandardStrings[152] = 'mu'
StandardStrings[153] = 'trademark'
StandardStrings[154] = 'Eth'
StandardStrings[155] = 'onehalf'
StandardStrings[156] = 'plusminus'
StandardStrings[157] = 'Thorn'
StandardStrings[158] = 'onequarter'
StandardStrings[159] = 'divide'
StandardStrings[160] = 'brokenbar'
StandardStrings[161] = 'degree'
StandardStrings[162] = 'thorn'
StandardStrings[163] = 'threequarters'
StandardStrings[164] = 'twosuperior'
StandardStrings[165] = 'registered'
StandardStrings[166] = 'minus'
StandardStrings[167] = 'eth'
StandardStrings[168] = 'multiply'
StandardStrings[169] = 'threesuperior'
StandardStrings[170] = 'copyright'
StandardStrings[171] = 'Aacute'
StandardStrings[172] = 'Acircumflex'
StandardStrings[173] = 'Adieresis'
StandardStrings[174] = 'Agrave'
StandardStrings[175] = 'Aring'
StandardStrings[176] = 'Atilde'
StandardStrings[177] = 'Ccedilla'
StandardStrings[178] = 'Eacute'
StandardStrings[179] = 'Ecircumflex'
StandardStrings[180] = 'Edieresis'
StandardStrings[181] = 'Egrave'
StandardStrings[182] = 'Iacute'
StandardStrings[183] = 'Icircumflex'
StandardStrings[184] = 'Idieresis'
StandardStrings[185] = 'Igrave'
StandardStrings[186] = 'Ntilde'
StandardStrings[187] = 'Oacute'
StandardStrings[188] = 'Ocricumflex'
StandardStrings[189] = 'Odieresis'
StandardStrings[190] = 'Ograve'
StandardStrings[191] = 'Otilde'
StandardStrings[192] = 'Scaron'
StandardStrings[193] = 'Uacute'
StandardStrings[194] = 'Ucircumflex'
StandardStrings[195] = 'Udieresis'
StandardStrings[196] = 'Ugrave'
StandardStrings[197] = 'Yacute'
StandardStrings[198] = 'Ydieresis'
StandardStrings[199] = 'Zcaron'
StandardStrings[200] = 'aacute'
StandardStrings[201] = 'acricumflex'
StandardStrings[202] = 'adieresis'
StandardStrings[203] = 'agrave'
StandardStrings[204] = 'aring'
StandardStrings[205] = 'atilde'
StandardStrings[206] = 'ccedilla'
StandardStrings[207] = 'eacute'
StandardStrings[208] = 'ecircumflex'
StandardStrings[209] = 'edieresis'
StandardStrings[210] = 'egrave'
StandardStrings[211] = 'iacute'
StandardStrings[212] = 'icrcumflex'
StandardStrings[213] = 'idieresis'
StandardStrings[214] = 'igrave'
StandardStrings[215] = 'ntilde'
StandardStrings[216] = 'oacute'
StandardStrings[217] = 'ocricumflex'
StandardStrings[218] = 'odieresis'
StandardStrings[219] = 'ograve'
StandardStrings[220] = 'otilde'
StandardStrings[221] = 'scaron'
StandardStrings[222] = 'uacute'
StandardStrings[223] = 'ucircumflex'
StandardStrings[224] = 'udieresis'
StandardStrings[225] = 'ugrave'
StandardStrings[226] = 'yacute'
StandardStrings[227] = 'ydieresis'
StandardStrings[228] = 'zcaron'
StandardStrings[229] = 'exclamsmall'
StandardStrings[230] = 'Hungarumlautsmall'
StandardStrings[231] = 'dollaroldstyle'
StandardStrings[232] = 'dollarsuperior'
StandardStrings[233] = 'ampersandsmall'
StandardStrings[234] = 'Acutesmall'
StandardStrings[235] = 'parenleftsuperior'
StandardStrings[236] = 'parentrightsuperior'
StandardStrings[237] = 'twodotenleader'
StandardStrings[238] = 'onedotenleader'
StandardStrings[239] = 'zerooldstyle'
StandardStrings[240] = 'oneoldstyle'
StandardStrings[241] = 'twooldstyle'
StandardStrings[242] = 'threeoldstyle'
StandardStrings[243] = 'fouroldstyle'
StandardStrings[244] = 'fiveoldstyle'
StandardStrings[245] = 'sixoldstyle'
StandardStrings[246] = 'sevenoldstyle'
StandardStrings[247] = 'eightoldstyle'
StandardStrings[248] = 'nineoldstyle'
StandardStrings[249] = 'commasuperior'
StandardStrings[250] = 'threequartersemdash'
StandardStrings[251] = 'periodsuperior'
StandardStrings[252] = 'questionsmall'
StandardStrings[253] = 'asuperior'
StandardStrings[254] = 'bsuperior'
StandardStrings[255] = 'centsuperior'
StandardStrings[256] = 'dsuperior'
StandardStrings[257] = 'esuperior'
StandardStrings[258] = 'isuperior'
StandardStrings[259] = 'lsuperior'
StandardStrings[260] = 'msuperior'
StandardStrings[261] = 'nsuperior'
StandardStrings[262] = 'osuperior'
StandardStrings[263] = 'rsuperior'
StandardStrings[264] = 'ssuperior'
StandardStrings[265] = 'tsuperior'
StandardStrings[266] = 'ff'
StandardStrings[267] = 'ffi'
StandardStrings[268] = 'ffl'
StandardStrings[269] = 'parenleftinferior'
StandardStrings[270] = 'parenrightinferior'
StandardStrings[271] = 'Circumflexsmall'
StandardStrings[272] = 'hyphensuperior'
StandardStrings[273] = 'Gravesmall'
StandardStrings[274] = 'Asmall'
StandardStrings[275] = 'Bsmall'
StandardStrings[276] = 'Csmall'
StandardStrings[277] = 'Dsmall'
StandardStrings[278] = 'Esmall'
StandardStrings[279] = 'Fsmall'
StandardStrings[280] = 'Gsmall'
StandardStrings[281] = 'Hsmall'
StandardStrings[282] = 'Ismall'
StandardStrings[283] = 'Jsmall'
StandardStrings[284] = 'Ksmall'
StandardStrings[285] = 'Lsmall'
StandardStrings[286] = 'Msmall'
StandardStrings[287] = 'Nsmall'
StandardStrings[288] = 'Osmall'
StandardStrings[289] = 'Psmall'
StandardStrings[290] = 'Qsmall'
StandardStrings[291] = 'Rsmall'
StandardStrings[292] = 'Ssmall'
StandardStrings[293] = 'Tsmall'
StandardStrings[294] = 'Usmall'
StandardStrings[295] = 'Vsmall'
StandardStrings[296] = 'Wsmall'
StandardStrings[297] = 'Xsmall'
StandardStrings[298] = 'Ysmall'
StandardStrings[299] = 'Zsmall'
StandardStrings[300] = 'colonmonetary'
StandardStrings[301] = 'onefitted'
StandardStrings[302] = 'rupiah'
StandardStrings[303] = 'Tildesmall'
StandardStrings[304] = 'exclamdownsmall'
StandardStrings[305] = 'centoldstyle'
StandardStrings[306] = 'Lslashsmall'
StandardStrings[307] = 'Scaronsmall'
StandardStrings[308] = 'Zcaronsmall'
StandardStrings[309] = 'Dieresissmall'
StandardStrings[310] = 'Brevesmall'
StandardStrings[311] = 'Caronsmall'
StandardStrings[312] = 'Dotaccentsmall'
StandardStrings[313] = 'Macronsmall'
StandardStrings[314] = 'figuredash'
StandardStrings[315] = 'hypheninferior'
StandardStrings[316] = 'Ogoneksmall'
StandardStrings[317] = 'Ringsmall'
StandardStrings[318] = 'Cedillasmall'
StandardStrings[319] = 'questiondownsmall'
StandardStrings[320] = 'oneeight'
StandardStrings[321] = 'threeeights'
StandardStrings[322] = 'fiveeights'
StandardStrings[323] = 'seveneights'
StandardStrings[324] = 'onethird'
StandardStrings[325] = 'twothirds'
StandardStrings[326] = 'zerosuperior'
StandardStrings[327] = 'foursuperior'
StandardStrings[328] = 'fivesuperior'
StandardStrings[329] = 'sixsuperior'
StandardStrings[330] = 'sevensuperior'
StandardStrings[331] = 'eightsuperior'
StandardStrings[332] = 'ninesuperior'
StandardStrings[333] = 'zeroinferior'
StandardStrings[334] = 'oneinferior'
StandardStrings[335] = 'twoinferior'
StandardStrings[336] = 'threeinferior'
StandardStrings[337] = 'fourinferior'
StandardStrings[338] = 'fiveinferior'
StandardStrings[339] = 'sixinferior'
StandardStrings[340] = 'seveninferior'
StandardStrings[341] = 'eightinferior'
StandardStrings[342] = 'nineinferior'
StandardStrings[343] = 'centinferior'
StandardStrings[344] = 'dollarinferior'
StandardStrings[345] = 'periodinferior'
StandardStrings[346] = 'commainferior'
StandardStrings[347] = 'Agravesmall'
StandardStrings[348] = 'Aacutesmall'
StandardStrings[349] = 'Acircumflexsmall'
StandardStrings[350] = 'Atildesmall'
StandardStrings[351] = 'Adieresissmall'
StandardStrings[352] = 'Aringsmall'
StandardStrings[353] = 'AEsmall'
StandardStrings[354] = 'Ccedillasmall'
StandardStrings[355] = 'Egravesmall'
StandardStrings[356] = 'Eacutesmall'
StandardStrings[357] = 'Ecircumflexsmall'
StandardStrings[358] = 'Edieresissmall'
StandardStrings[359] = 'Igravesmall'
StandardStrings[360] = 'Iacutesmall'
StandardStrings[361] = 'Icircumflexsmall'
StandardStrings[362] = 'Idieresissmall'
StandardStrings[363] = 'Ethsmall'
StandardStrings[364] = 'Ntildesmall'
StandardStrings[365] = 'Ogravesmall'
StandardStrings[366] = 'Oacutesmall'
StandardStrings[367] = 'Ocircumflexsmall'
StandardStrings[368] = 'Otildesmall'
StandardStrings[369] = 'Odieresissmall'
StandardStrings[370] = 'OEsmall'
StandardStrings[371] = 'Oslashsmall'
StandardStrings[372] = 'Ugravesmall'
StandardStrings[373] = 'Uacutesmall'
StandardStrings[374] = 'Ucircumflexsmall'
StandardStrings[375] = 'Udieresissmall'
StandardStrings[376] = 'Yacutesmall'
StandardStrings[377] = 'Thornsmall'
StandardStrings[378] = 'Ydieresissmall'
StandardStrings[379] = '001.000'
StandardStrings[380] = '001.001'
StandardStrings[381] = '001.002'
StandardStrings[382] = '001.003'
StandardStrings[383] = 'Black'
StandardStrings[384] = 'Bold'
StandardStrings[385] = 'Book'
StandardStrings[386] = 'Light'
StandardStrings[387] = 'Medium'
StandardStrings[388] = 'Regular'
StandardStrings[389] = 'Roman'
StandardStrings[390] = 'Semibold'
NumStandardStrings = len(StandardStrings)

class _CFFUnpacker:
	def __init__(self, txt):
		self.buf = bytes(txt, 'latin-1')
		self.offset = 0

	def DumpBinary(self):
		l = len(self.buf)

		for i in range(0, int(l/8), 8):
			print("%4x | %02x %02x %02x %02x   %02x %02x %02x %02x" % (i, self.buf[i], self.buf[i+1], self.buf[i+2], self.buf[i+3], self.buf[i+4], self.buf[i+5], self.buf[i+6], self.buf[i+7]))
		if l%8:
			out = "%4x |" % int(l/8)
			for i in range(l%8):
				if i == 4:
					out += "  "
				out += " %02x" % self.buf[l+i]
			print(out)

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

	def ParseCharStrings(self, dat):
		raise NotImplementedError("See tech #5177")

	def GetCharsets(self, idx, nGlyphs):
		self.offset = idx
		fmt = self.Get8()

		if fmt == 0:
			glyphs = [self.GetSID() for i in range(nGlyphs-1)]

			return {'format': fmt, 'nGlyphs': nGlyphs, 'glyph': glyphs}
		else:
			raise NotImplementedError("Format %d of charsets not implemented yet" % fmt)

	@staticmethod
	def GetString(top_dict_font, idx):
		if idx > NumStandardStrings:
			init_idx = idx
			# Ignore through the length of the standard strings
			idx -= NumStandardStrings

			# Ensure enough strings are present
			if idx > len(top_dict_font):
				raise IndexError("Standard string %d is above standard string size (%d) to %d and is larger than in the string INDEX" % (init_idx, NumStandardStrings, idx))

			# Make zero-based index
			#idx -= 1

			# Return the non-standard string
			return top_dict_font[idx]

		else:
			# Return standard string
			return StandardStrings[idx]

def TokenizeString(txt):
	u = _CFFUnpacker(txt)

	off = u.offset
	header = u.GetHeader()
	header['_offset'] = off

	off = u.offset
	name_index = u.GetIndex()
	name_index['_offset'] = off

	off = u.offset
	top_dict_index = u.GetIndex()
	top_dict_index['_offset'] = off

	fonts = []
	for font in top_dict_index['data']:
		f = u.ParseTopDict(font)
		fonts.append(f)
	top_dict_index['fonts'] = fonts

	off = u.offset
	string_index = u.GetIndex()
	string_index['_offset'] = off

	off = u.offset
	global_subr_index = u.GetIndex()
	if global_subr_index:
		global_subr_index['_offset'] = off

	# Read Encoding section if present in Top Dict
	if 'Encoding' in fonts[0]:
		raise NotImplementedError("Encoding handling not implemented yet")

	try:
		# Find index for CharStrings...
		idx = fonts[0].index('CharStrings')
		# ...and the offset is the value prior to it in the list
		u.offset = fonts[0][idx-1]
		off = u.offset

		charstrings_index = u.GetIndex()
		charstrings_index['_offset'] = off

		# TODO: ParseCharStrings()
	except ValueError:
		off = 0
		charstrings_index = None
		pass

	if charstrings_index:
		nGlyphs = charstrings_index['count']
		# Read charsets section if present in Top Dict
		try:
			idx = fonts[0].index('charset')
			offset = idx

			charsets = u.GetCharsets(idx, nGlyphs)
			charsets['_offset'] = offset
		except ValueError:
			charsets = None

	# FDSelect
	# CharStrings INDEX
	# Font DICT INDEX
	# Private DICT
	# Local Subr INDEX
	# Copyright and trademark notices

	ret = {}
	ret['unpacker'] = u
	ret['Header'] = header
	ret['Name INDEX'] = name_index
	ret['Top DICT INDEX'] = top_dict_index
	ret['String INDEX'] = string_index
	ret['Global Subr INDEX'] = global_subr_index
	ret['Encoding'] = None
	ret['CharStrings INDEX'] = charstrings_index
	ret['Charset'] = charsets
	return ret


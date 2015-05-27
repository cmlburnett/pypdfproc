"""
Font cache used to speed up repetative glyph lookups.
"""

# Local files
from . import parser
from . import encodingmap as _encodingmap
from . import pdf as _pdf
from .glyph import Glyph
from .parser import CFFTokenizer

from .cmap_identity_h import CMapIdentityH
from .cmap_identity_v import CMapIdentityV

class FontCache:
	"""
	Font cache for various font information to speed-up glyph lookups.
	"""

	# PDF object that this cache is related to
	# This is found in pdf.py
	pdf = None

	# Font map: maps (object id, generation) to Font object
	font_map = None

	# Glyph map: maps (object id, generation) of font to dictionary of glyphs indexed by CID
	glyph_map = None

	# Differences array maps: maps (object id, generation) of FontEncoding object to map dictionary (made by DifferencesArrayToMap)
	diff_map = None

	def __init__(self, pdf):
		"""
		Start cache related to PDF object @pdf.
		"""

		self.pdf = pdf
		self.font_map = {}
		self.glyph_map = {}
		self.diff_map = {}
		self.type0_map = {}

	def GetGlyph(self, oid, cid):
		"""
		Dig into font with id @oid and get Glyph object given the character code @cid.
		"""

		# Get glyph from cache if it's there
		if oid in self.glyph_map:
			if cid in self.glyph_map[oid]:
				return self.glyph_map[oid][cid]

		# Get font from PDF or cache
		if oid not in self.font_map:
			f = self.pdf.p.GetFont(oid)
			self.font_map[oid] = f
			self.glyph_map[oid] = {}
		else:
			f = self.font_map[oid]

		# ------------------------------------------------------

		if f.Subtype == 'Type0':
			g = self.GetGlyph_Type0(f, cid)

		elif type(f.Encoding) == str:
			# NB: unused for WinAnsiEncoding map to bullet
			# which means g.cid != cid since the glyph returned is that of the bullet with proper cid set
			g = self.GetGlyph_Enc_str(f, cid)

		elif isinstance(f.Encoding, _pdf.FontEncoding):
			g = self.GetGlyph_Enc_indobj(f, cid)

		else:
			raise TypeError("Unrecognized font encoding type: '%s'" % f.Encoding)

		# Cache glyph
		# NB: do not change this to use g.cid instead of cid (see note above about WinAnsiEncoding and bullet)
		self.glyph_map[oid][cid] = g

		return g

	def GetGlyph_Type0(self, f, cid):
		"""
		Font @f is a Type0 font, so find glyph for character ID @cid.
		"""

		# Get object ID for the font
		oid = f.oid

		# Cache instance if not present
		if oid not in self.type0_map:
			self.type0_map[oid] = Type0FontCache(f)

		# Get glyph
		return self.type0_map[oid].GetGlyph(cid)

	def GetGlyph_Enc_str(self, f, cid):
		"""
		Font @f has a FontEncoding that is a string (one of the four standard encoding types).
		"""

		encmap = _encodingmap.MapCIDToGlyphName(f.Encoding)

		# Footnote 3 in Appendix D:
		# "3. In WinAnsiEncoding, all unused codes greater than 40 map to the bullet character. However, only code 225 is specifically assigned to the bullet character; other codes are subject to future reassignment."
		# I interpret this as 40 in octal (32 decimal)
		#
		# Such a lovely and ridiculous exception to use a bullet for everything not encoded, no?
		if cid not in encmap and f.Encoding == 'WinAnsiEncoding' and cid > int('40', 8):
			# Assigned CID of /bullet is 225 in octal (149 decimal)
			# So just remap
			cid = int('225', 8)

		# Bounds checking since these error strings are more descriptive than KeyErrors
		if cid not in encmap:
			raise ValueError("Unable to find character code %d ('%s') in encoding map for encoding %s" % (cid, chr(cid), f.Encoding))
		if cid - f.FirstChar > len(f.Widths):
			raise KeyError("Character code (%d) from the first character (%d) exceeds the widths array (len=%d)" % (cid, f.FirstChar, len(f.Widths)))

		# Character code to glyph name to unicode
		gname = encmap[cid]
		u = _encodingmap.MapGlyphNameToUnicode(gname)
		if u == None:
			raise NotImplementedError()

		# Get width based on character code
		w = f.Widths[ cid - f.FirstChar ]

		# Create glyph
		g = Glyph(cid)
		g.unicode = u
		g.width = w

		return g

	def GetGlyph_Enc_indobj(self, f, cid):
		"""
		Font @f has a FontEncoding that is an indirect object, which means it is slightly more complicated than
		one of the four standard encoding types.
		"""

		# Get object ID for the font
		oid = f.oid

		# Get objects
		cmap = f.ToUnicode
		enc = f.Encoding

		# Check for a base encoding value and use that, otherwise assume StandardEncoding
		if enc.BaseEncoding:
			be = enc.BaseEncoding
		else:
			# Assume this if can't find anything better in font objects
			be = 'StandardEncoding'

		# Get base encoding map
		encmap = _encodingmap.MapCIDToGlyphName(be)

		# Get differences mapping and CMap function
		if enc.oid not in self.diff_map:
			self.diff_map[ enc.oid ] = DifferencesArrayToMap(enc.Differences)
		if cmap and not cmap.CMapper:
			cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

		# Bounds checking since these error strings are more descriptive than KeyErrors
		if cid not in self.diff_map[enc.oid] and cid not in encmap:
			raise ValueError("Unable to find character code %d ('%s') in differences map for encoding oid %s and base encoding '%s'" % (cid, chr(cid), f.Encoding.oid, be))

		# Get glyph name from differences mapping first, but otherwise fallback on the standard encoding map
		if cid in self.diff_map[enc.oid]:
			gname = self.diff_map[ enc.oid ][cid]
		else:
			gname = encmap[cid]

		# Attempt to map glyph name to unicode, and call the magic function if it's not found
		u = _encodingmap.MapGlyphNameToUnicode(gname)
		if u == None:
			u = self.MissingGlyphName(f, encmap, cid, gname)

		# Get width of glyph
		w = f.Widths[ cid - f.FirstChar ]

		# TODO: catch fi, fl, etc. ligatures here???

		g = Glyph(cid)
		g.unicode = u
		g.width = w

		return g

	def MissingGlyphName(self, f, encmap, cid, gname):
		"""
		Sometimes a glyph name is found and it cannot be mapped.
		This is a common method to search harder for the glyph.
		"""

		fd = f.FontDescriptor
		cmap = f.ToUnicode
		enc = f.Encoding

		# Try the cmap
		if f.ToUnicode:
			try:
				return cmap.CMapper(cid)
			except KeyError:
				# Not there, try again
				pass

		if f.BaseFont != None:
			if f.BaseFont.endswith('AdvP4C4E74'):
				if gname == 'C0':		return '\u2212' # Minus sign
				elif gname == 'C6':		return '\u00B1' # Plus-mins sign
				elif gname == 'C14':	return '\u00B0' # Degree symbol
				elif gname == 'C15':	return '\u2022' # Bullet
				elif gname == 'C211':	return '\u00A9' # Copyright
			if f.BaseFont.endswith('AdvPSSym'):
				if gname == 'C211':		return '\u00A9' # Copyright

		#print(['cid', cid])
		#print(['f', f.getsetprops()])
		#print(['fd', fd.getsetprops()])
		#print(['enc', f.Encoding.getsetprops()])
		#print(['cmap', cmap])
		#print(['encmap', encmap])
		#print(['gname', gname])

		ff = fd.FontFile3
		#print(['ff3', ff.Dict])

		cfft = CFFTokenizer(ff.Stream)
		cfft.Parse()

		gmatch = None
		for g in cfft.tzdat['Glyphs'][0]:
			if g['cname'] == gname:
				gmatch = g
				break

		#print(['gmatch', gmatch])
		if gmatch:
			gcid = gmatch['cid']
			if f.BaseFont != None and f.BaseFont.endswith('MathematicalPi-One'):
				if gcid == ord('A'):	return '\u0391' # Capital Alpha
				elif gcid == ord('B'):	return '\u0392' # Capital Beta
				elif gcid == ord('C'):	return '\u03A8' # Capital Psi
				elif gcid == ord('D'):	return '\u0394' # Capital Delta
				elif gcid == ord('E'):	return '\u0395' # Capital Epsilon
				elif gcid == ord('F'):	return '\u03A6' # Capital Phi
				elif gcid == ord('G'):	return '\u0393' # Capital Gamma
				elif gcid == ord('H'):	return '\u0397' # Capital Eta
				elif gcid == ord('I'):	return '\u0399' # Capital Iota
				elif gcid == ord('J'):	return '\u039E' # Capital Xi
				elif gcid == ord('K'):	return '\u039A' # Capital Kappa
				elif gcid == ord('L'):	return '\u039B' # Capital Lambda
				elif gcid == ord('M'):	return '\u039C' # Capital Mu
				elif gcid == ord('N'):	return '\u039D' # Capital Nu
				elif gcid == ord('O'):	return '\u039F' # Capital Omicron
				elif gcid == ord('P'):	return '\u03A0' # Capital Pi
				elif gcid == ord('Q'):	return '\u03F4' # Capital Theta symbol (script)
				elif gcid == ord('R'):	return '\u03A1' # Capital Rho
				elif gcid == ord('S'):	return '\u03A3' # Capital Sigma
				elif gcid == ord('T'):	return '\u03A4' # Capital Tau
				elif gcid == ord('U'):	return '\u0398' # Capital Theta
				elif gcid == ord('V'):	return '\u03A9' # Capital Omega
				elif gcid == ord('W'):	return '\u03D0' # Capital Beta symbol
				elif gcid == ord('X'):	return '\u03A7' # Capital Chi
				elif gcid == ord('Y'):	return '\u03A5' # Capital Upsilon
				elif gcid == ord('Z'):	return '\u0396' # Capital Zeta
				elif gcid == ord('a'):	return '\u03B1' # Small Alpha
				elif gcid == ord('b'):	return '\u03B2' # Small Beta
				elif gcid == ord('c'):	return '\u03C8' # Small Psi
				elif gcid == ord('d'):	return '\u03B4' # Small Delta
				elif gcid == ord('e'):	return '\u03B5' # Small Epsilon
				elif gcid == ord('f'):	return '\u03C6' # Small Phi
				elif gcid == ord('g'):	return '\u03B3' # Small Gamma
				elif gcid == ord('h'):	return '\u03B7' # Small Eta
				elif gcid == ord('i'):	return '\u03B9' # Small Iota
				elif gcid == ord('j'):	return '\u03BE' # Small Xi
				elif gcid == ord('k'):	return '\u03BA' # Small Kappa
				elif gcid == ord('l'):	return '\u03BB' # Small Lambda
				elif gcid == ord('m'):	return '\u03BC' # Small Mu
				elif gcid == ord('n'):	return '\u03BD' # Small Nu
				elif gcid == ord('o'):	return '\u03BF' # Small Omicron
				elif gcid == ord('p'):	return '\u03C0' # Small Pi
				elif gcid == ord('q'):	return '\u03D1' # Small Theta symbol (script)
				elif gcid == ord('r'):	return '\u03C1' # Small Rho
				elif gcid == ord('s'):	return '\u03C3' # Small Sigma
				elif gcid == ord('t'):	return '\u03C4' # Small Tau
				elif gcid == ord('u'):	return '\u03B8' # Small Theta
				elif gcid == ord('v'):	return '\u03C9' # Small Omega
				elif gcid == ord('w'):	return '\u03D5' # Small phi symbol (script)
				elif gcid == ord('x'):	return '\u03C7' # Small Chi
				elif gcid == ord('y'):	return '\u03C5' # Small Upsilon
				elif gcid == ord('z'):	return '\u03B6' # Small Zeta
				elif gcid == ord('0'):	return '\u2033' # Double prime
				elif gcid == ord('1'):	return '\u0028' # Plus sign
				elif gcid == ord('2'):	return '\u2212' # Minus sign
				elif gcid == ord('3'):	return '\u00D7' # Multiplication sign
				elif gcid == ord('4'):	return '\u00F7' # Division sign
				elif gcid == ord('5'):	return '\u003D' # Equal sign
				elif gcid == ord('6'):	return '\u00B1' # Plus-minus
				elif gcid == ord('7'):	return '\u2213' # Minus-plus
				elif gcid == ord('8'):	return '\u00B0' # Degree symbol
				elif gcid == ord('9'):	return '\u2032' # Prime
				elif gcid == ord('!'):	return '\u226A' # Much less-than
				elif gcid == ord('@'):	return '\u226B' # Much greater-than
				elif gcid == ord('#'):	return '\u2264' # Less-than or equal to
				elif gcid == ord('$'):	return '\u2265' # Greater-than or equal to
				elif gcid == ord('%'):	return '\u2266' # Less-than over equal to
				elif gcid == ord('^'):	return '\u2267' # Greater-than over equal to
				elif gcid == ord('&'):	return '\u2272' # Less-than or equivalent to
				elif gcid == ord('*'):	return '\u2273' # Greater-than or equivalent to
				#elif gcid == ord('('):	return '\u' # Looks like less-than or equivalent to, but the squiggle underneath is flipped
				#elif gcid == ord(')'):	return '\u' # Looks like greater-than or equivalent to, but the squiggle underneath is angled more
				elif gcid == ord('{'):	return '\u002D' # Hyphen-minus (I think this is hyphen)
				elif gcid == ord('}'):	return '\u2014' # Em dash; (I think this is em)
				elif gcid == ord('['):	return '\u2205' # Empty set
				elif gcid == ord(']'):	return '\u2013' #  En dash; (I think this is en)
				elif gcid == ord(':'):	return '\u2135' # Alef symbol
				elif gcid == ord(';'):	return '\u2200' # For all
				elif gcid == ord('?'):	return '\u2219' # Bullet operator
				#elif gcid == ord('<'):	return '\u0' # Looks like less-than or equal to, but the bar is slanted
				#elif gcid == ord('>'):	return '\u0' # Looks like greater-than or equal to, but the bar is slanted
				elif gcid == ord('-'):	return '\u2034' # Triple prime
				elif gcid == ord('+'):	return '\u2276' # Less-than or greater-than
				elif gcid == ord('='):	return '\u2207' # Del operator/nabla

		raise ValueError("Unable to find unicode for character ord=%d" % cid)

class Type0FontCache:
	"""
	Handle Type0 fonts.
	More complex than simple fonts so having a dedicated structure seems reasonable.
	"""

	# Font this cachine
	font = None

	# Maps CDI to width
	widthmap = None

	def __init__(self, f):
		"""
		Type0 font cache for the font @f.
		"""

		self.font = f
		self.widthmap = {}

		# Index widths by CID
		for subf in f.DescendantFonts:
			m = CIDWidthArrayToMap(subf.W)
			for k,v in m.items():
				self.widthmap[k] = (v, subf)

	def GetGlyph(self, cid):
		"""
		Get glyph information based on the character ID @cid.
		"""

		# Get CMap and build mapper if not already cached
		cmap = self.font.ToUnicode
		if cmap == None:
			if self.font.Encoding == 'Identity-H':
				cmap = CMapIdentityH()
			elif self.f.Encoding == 'Identity-V':
				cmap = CMapIdentityV()
			else:
				for subf in self.font.DescendantFonts:
					print(['subf', subf.getsetprops()])
					print(['subf desc', subf.FontDescriptor.getsetprops()])

					ff3 = subf.FontDescriptor.FontFile3

					print(['fontfile3', ff3])
					t = parser.CFFTokenizer(ff3.Stream)
					t.Parse()
					t.DumpBinary()
					print(t.tzdat['Top DICT INDEX'])
					print(t.tzdat['CharStrings INDEX'])
					print(t.tzdat['Charset'])
					raise NotImplementedError()


		if not cmap.CMapper:
			cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

		# Map CID
		try:
			u = cmap.CMapper(cid)
		except KeyError as e:
			# Try backup cmap based on encoding
			if self.font.Encoding == 'Identity-H':
				u = CMapIdentityH().CMapper(cid)
			elif self.f.Encoding == 'Identity-V':
				u = CMapIdentityV().CMapper(cid)
			else:
				raise

		# Create glyph information
		g = Glyph(cid)
		g.width = self.widthmap[cid][0]
		g.unicode = u

		# NB: glyph caching is done in FontCache, not here

		return g

def CIDWidthArrayToMap(arr):
	"""
	CID width array comes as an array with two patterns of information.
	The first is an integer followed by an array: the integer is the starting character ID and the array is a set of widths.
	The second is three integers: the first two specify a range and the third is the width for the entire range.
	"""
	mapdat = {}

	i = 0
	imax = len(arr)
	while i < imax:
		if type(arr[i]) == int and isinstance(arr[i+1], _pdf.Array):
			# Base code is given first
			basecode = arr[i]

			# Then incrementally applied to each element in the array
			for v in arr[i+1]:
				mapdat[basecode] = v
				basecode += 1

			# Two: one for int, one for array
			i += 2

		elif type(arr[i]) == int and type(arr[i+1]) == int and type(arr[i+2]) == int:
			# First and second number define a range, and each within the range
			# is the same width that is the third number
			for k in range(arr[i], arr[i+1]+1):
				mapdat[k] = arr[i+2]

			# Three: one for start index, one for end index, one for width
			i += 3
		else:
			raise TypeError("Unrecognized type (%s) when iterating through CID widths array: %s" % (arr[i], arr))

	return mapdat

def DifferencesArrayToMap(arr):
	"""
	Format of the Differences array is an integer followed by literals.
	The integer refers to the character code/ID (CID) of the first literal and each
	subsequent literal auto-increments the associated CID.
	For example [10, 'a', 'b'] would make 10 to 'a' and 11 to 'b'.
	Numerous integer/literals can be in the array and each segment may not overlap with another.
	"""

	mapdat = {}

	lastcode = 0
	for item in arr:
		# If an integer then set the last code used
		if type(item) == int:
			lastcode = item
		else:
			# Assign literal to code and increment code
			mapdat[ lastcode ] = item
			lastcode += 1

	return mapdat


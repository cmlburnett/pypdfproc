"""
Font cache used to speed up repetative glyph lookups.
"""

from . import encodingmap as _encodingmap
from .glyph import Glyph

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
		if not cmap.CMapper:
			cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

		# Map CID
		u = cmap.CMapper(cid)

		# Create glyph information
		g = Glyph(cid)
		g.width = self.widthmap[cid][0]
		g.unicode = u

		# NB: glyph caching is done in FontCache, not here

		return g

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
			f = self.pdf.p.GetObject(oid[0], oid[1])
			self.font_map[oid] = f
			self.glyph_map[oid] = {}
		else:
			f = self.font_map[oid]

		# ------------------------------------------------------

		if f.Subtype == 'Type0':
			g = self.GetGlyph_Type0(f, cid)

		elif type(f.Encoding) == str:
			g = self.GetGlyph_Enc_str(f, cid)

		elif isinstance(f.Encoding, _pdf.FontEncoding):
			g = self.GetGlyph_Enc_indobj(f, cid)

		else:
			raise TypeError("Unrecognized font encoding type: '%s'" % f.Encoding)

		# Cache glyph
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

		# Try the cmap
		if f.ToUnicode:
			try:
				return f.ToUnicode.CMapper(cid)
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

		print(['f', f.getsetprops()])
		print(['enc', f.Encoding.getsetprops()])
		print(['cmap', f.ToUnicode])
		print(['encmap', encmap])
		print(['gname', gname])

		raise NotImplementedError()


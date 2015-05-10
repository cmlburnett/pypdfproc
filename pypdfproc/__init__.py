"""
PDF Processor
"""

__version__ = "1.0.0"

__all__ = ['parser']

# System libs
import mmap

from . import parser
from . import pdf as _pdf
from . import encodingmap as _encodingmap

def isindirect(o):
	return isinstance(o, _pdf.IndirectObject)

class PDF:
	"""
	Basic entry point into manipulating PDF files.
	"""

	# File name, file object (from open()), and mmap object
	fname = None
	f = None
	m = None

	# PDF parser (from pdf.py)
	p = None

	# Font cache keeps track of glyph information, etc.
	fonts = None

	def __init__(self, fname):
		# Copy the file name
		self.fname = fname

		# Open file and mmap it (binary is important here so that python does not interpret the file as text)
		self.f = open(fname, 'rb')
		self.m = mmap.mmap(self.f.fileno(), 0, prot=mmap.PROT_READ)

		# Open the file and initialize it (xref/trailer reading)
		self.p = parser.PDFTokenizer(self.m)
		self.p.Initialize()

		self.fonts = FontCache(self)

	def Close(self):
		self.m.close()
		self.f.close()

		self.m = None
		self.f = None
		self.p = None

	def GetRootObject(self):
		"""
		Gets the root object (aka catalog) of the file.
		"""

		return self.p.GetRootObject()

	def GetDFSPages(self):
		root = self.GetRootObject()

		return root.Pages.DFSPages()

	def GetFont(self, page, fontname):
		"""
		The text operation Tf uses a font name that maps to a font via the page's Resources object.
		This looks up the fontname for the given page.
		The page can be a Page object or a page number (page is found by DFS'ing the page tree and
		counting (i.e., it does not look at page labels)).
		"""

		# Page number provided, find corresponding page
		if type(page) == int:
			root = self.GetRootObject()
			pages = root.Pages.DFSPages()

			if page < 1:				raise ValueError("Page number (%d) must be a positive number" % page)
			if page > len(pages):		raise ValueError("Page number (%d) is larger the total number of pages" % page)

			# Get page (pages is zero-based and pagenum is one-based, so subtract one)
			page = pages[page-1]

		elif isinstance(page, _pdf.Page):
			# Page supplied, nothing to get
			pass

		else:
			raise TypeError("Unrecognized page type passed: %s" % page)

		# Get resources for the page
		recs = page.Resources

		# Check that there is a font with this name for this page
		if fontname not in recs.Font:
			raise ValueError("Unrecognize font name (%s) for page (%d)" % (fontname, page))

		# Get font object
		f = recs.Font[fontname]

		# If it's an indirect, then fetch object
		if isindirect(f):
			f = self.p.GetFont(f)

		# Return Font1, Font3, or FontTrue object
		return f

	def GetGraphicsState(self, page, gsname):
		"""
		The text operation Gs uses a external graphics state name that maps to a dictionary via the page's Resources object.
		This looks up the gsname for the given page.
		The page can be a Page object or a page number (page is found by DFS'ing the page tree and
		counting (i.e., it does not look at page labels)).
		"""

		# Page number provided, find corresponding page
		if type(page) == int:
			root = self.GetRootObject()
			pages = root.Pages.DFSPages()

			if page < 1:				raise ValueError("Page number (%d) must be a positive number" % page)
			if page > len(pages):		raise ValueError("Page number (%d) is larger the total number of pages" % page)

			# Get page (pages is zero-based and pagenum is one-based, so subtract one)
			page = pages[page-1]

		elif isinstance(page, _pdf.Page):
			# Page supplied, nothing to get
			pass

		else:
			raise TypeError("Unrecognized page type passed: %s" % page)

		# Get resources for the page
		recs = page.Resources

		# Check that there is a font with this name for this page
		if gsname not in recs.ExtGState:
			raise ValueError("Unrecognize external graphics state name (%s) for page (%d)" % (gsname, page))

		# Get graphics state object
		g = recs.ExtGState[gsname]

		# If it's an indirect, then fetch object
		if isindirect(g):
			g = self.p.GetGraphicsState(g)

		# Return GraphicsState object
		return g


	def GetGlyph(self, page, fontname, cid):
		# Get font just to get object ID
		f = self.GetFont(page, fontname)

		# Glyph is irrespective of page, just font and character ID
		g = self.fonts.GetGlyph(f.oid, cid)
		return g

	def RenderPage(self, page, callback):
		"""
		Renders the page by processing every content command.
		"""

		# Page number provided, find corresponding page
		if type(page) == int:
			root = self.GetRootObject()
			pages = root.Pages.DFSPages()

			if page < 1:				raise ValueError("Page number (%d) must be a positive number" % page)
			if page > len(pages):		raise ValueError("Page number (%d) is larger the total number of pages" % page)

			# Get page (pages is zero-based and pagenum is one-based, so subtract one)
			page = pages[page-1]

		elif isinstance(page, _pdf.Page):
			# Page supplied, nothing to get
			pass

		else:
			raise TypeError("Unrecognized page type passed: %s" % page)

		# The text tokenizer
		tt = parser.TextTokenizer(self.f, self.p)

		cts = page.Contents
		if type(cts) == list:
			ct = " ".join([ct.Stream for ct in cts])
		else:
			ct = cts.Stream
		#print(ct)

		s = parser.StateManager()

		toks = tt.TokenizeString(ct)['tokens']
		for tok in toks:
			#print(['tok', tok])
			# Save and restore state
			if tok.type == 'q':			s.Push()
			elif tok.type == 'Q':		s.Pop()

			# Graphics state
			elif tok.type == 'i':		s.S.flatness = tok.value[0].value

			# Graphics
			elif tok.type == 'd':		s.S.d = (tok.value[0], tok.value[1])
			elif tok.type == 'j':		s.S.j = tok.value[0].value
			elif tok.type == 'J':		s.S.J = tok.value[0].value
			elif tok.type == 'M':		s.S.M = tok.value[0].value
			elif tok.type == 'ri':		s.S.ri = tok.value[0].value
			elif tok.type == 'w':		s.S.w = tok.value[0].value
			elif tok.type == 'gs':
				gs = self.GetGraphicsState(page, tok.value[0].value)

				# Order is as shown in Table 4.8 (pg 220-3) of 1.7 spec
				if gs.LW != None:		s.S.w = gs.LW # Line width
				if gs.LC != None:		s.S.J = gs.LC # Line cap
				if gs.LJ != None:		s.S.j = gs.LJ # Line join
				if gs.ML != None:		s.S.M = gs.ML # Miter limit
				if gs.D != None:		raise NotImplementedError("Graphics state setting dash pattern not implemented yet")
				if gs.RI != None:		s.S.ri = gs.RI # Rendering intent

				if gs.OP != None and gs.op != None:
					s.S.overprint = (gs.OP, gs.op)
				elif gs.OP != None:
					s.S.overprint = (gs.OP, gs.OP)
				elif gs.op != None:
					s.S.overprint = (s.S.overprint[0], gs.op)
				else:
					pass

				if gs.OPM != None:		s.S.overprintmode = gs.OPM # Overprint mode
				if gs.Font != None:
					s.T.Tf = gs.Font[0]
					s.T.Tfs = gs.Font[1]

				if gs.BG != None:		raise NotImplementedError("Graphics state setting (BG) black-generation function not implemented yet")
				if gs.BG2 != None:		raise NotImplementedError("Graphics state setting (BG2) black-generation function not implemented yet")
				if gs.UCR != None:		raise NotImplementedError("Graphics state setting (UCR) undercolor-removal function not implemented yet")
				if gs.UCR2 != None:		raise NotImplementedError("Graphics state setting (UCR2) undercolor-removal function not implemented yet")
				if gs.TR != None:		raise NotImplementedError("Graphics state setting (TR) transfer function not implemented yet")
				#if gs.TR2 != None:		raise NotImplementedError("Graphics state setting (TR2) transfer function not implemented yet")
				if gs.HT != None:		raise NotImplementedError("Graphics state setting (HT) halftone not implemented yet")
				if gs.FL != None:		s.S.flatness = gs.FL # Flatness
				if gs.SM != None:		s.S.smoothness = gs.SM # Smoothness
				if gs.SA != None:		s.S.strokeadjustment = gs.SA # Automatic stroke adjustment
				if gs.BM != None:		s.S.blendmode = gs.BM
				if gs.SMask != None:	raise NotImplementedError("Graphics state setting (SMask) soft mask not implemented yet")
				if gs.CA != None:		s.S.alphaconstant = (gs.CA, s.S.alphaconstant[1]) # Alpha constant for stroking
				if gs.ca != None:		s.S.alphaconstant = (s.S.alphaconstant[0], gs.ca) # Alpha constant for non-stroking
				if gs.AIS != None:		s.S.alphasource = gs.AIS # Alpha mode
				if gs.TK != None:		raise NotImplementedError("Graphics state setting (TK) text knockout flag not implemented yet")

			elif tok.type == 'l':		s.S.do_l(tok.value[0].value, tok.value[1].value)
			elif tok.type == 'm':		s.S.do_m(tok.value[0].value, tok.value[1].value)
			elif tok.type == 'Fstar':	pass
			elif tok.type == 'fstar':	pass
			elif tok.type == 'F':		pass
			elif tok.type == 'f':		pass
			elif tok.type == 'S':		pass
			elif tok.type == 's':		pass
			elif tok.type == 'n':		pass
			elif tok.type == 're':		s.S.do_re(*[v.value for v in tok.value])
			elif tok.type == 'W':		pass
			elif tok.type == 'W*':		pass

			elif tok.type == 'Do':		pass # Paint Xobject named by tok.value[0].value

			# Colorspaces
			elif tok.type == 'cs':		s.S.colorspace = (s.S.colorspace[0], tok.value[0].value)
			elif tok.type == 'CS':		s.S.colorspace = (tok.value[0].value, s.S.colorspace[1])
			elif tok.type == 'sc':		s.S.color = (s.S.color[0], tok.value[0].value)
			elif tok.type == 'SC':		s.S.color = (tok.value[0].value, s.S.color[1])
			elif tok.type == 'G':		s.S.do_G(tok.value[0].value)
			elif tok.type == 'g':		s.S.do_g(tok.value[0].value)
			elif tok.type == 'RG':		s.S.do_RG(*[t.value for t in tok.value])
			elif tok.type == 'rg':		s.S.do_rg(*[t.value for t in tok.value])
			elif tok.type == 'K':		s.S.do_K(*[t.value for t in tok.value])
			elif tok.type == 'k':		s.S.do_k(*[t.value for t in tok.value])

			# Transforms
			elif tok.type == 'cm':		s.S.cm = parser.Mat3x3(*[v.value for v in tok.value]) # Six numbers representing the matrix

			# Text
			elif tok.type == 'BT':		s.T.text_begin()
			elif tok.type == 'ET':		s.T.text_end()

			elif tok.type == 'Tc':		s.T.Tc = tok.value[0].value
			elif tok.type == 'Tf':
				s.T.Tf = tok.value[0].value # Font name
				s.T.Tfs = tok.value[1].value # Font size
			elif tok.type in ('Tj', 'TJ'):
				for subtok in tok.value:
					#print(['stok', subtok])

					if subtok.type in ('INT', 'FLOAT'):
						# Adjust character spacing
						s.T.do_Tj(subtok.value, None)

						# TODO: If sufficient width to constitute a space, then inject that space
					else:
						if subtok.type == 'HEXSTRING':
							f = self.GetFont(page, s.T.Tf)
							if type(f.Encoding) == str:
								if f.Encoding.startswith('Identity'):
									txt = GetTokenString(subtok, bytesize=2)
								else:
									raise NotImplementedError("Unknown encoding for HEXSTRING: '%s'" % f.Encoding)
							else:
								raise NotImplementedError("Unknown encoding for HEXSTRING: '%s'" % f.Encoding)
						else:
							txt = GetTokenString(subtok)

						for t in txt:
							g = self.GetGlyph(page, s.T.Tf, ord(t))
							#print(['t', t, g.width, g.unicode])

							# Calculate current drawing position before updating Tm
							m = parser.Mat3x3(s.T.Tfs*s.T.Tz,0, 0,s.T.Tfs, 0,s.T.Tr) * s.T.Tm * s.S.cm
							#print("<%.2f, %.2f> '%s'" % (m.E, m.F, g.unicode))

							callback('glyph draw', (m.E, m.F), g)

							# Adjust for width of glyph
							s.T.do_Tj(None, g)

			elif tok.type == 'TL':		s.T.TL = tok.value[0].value
			elif tok.type == 'Tm':		s.T.Tm = parser.Mat3x3(*[v.value for v in tok.value]) # Six numbers representing the Tm matrix
			elif tok.type == 'Tr':		s.T.Tr = tok.value[0].value
			elif tok.type == 'Ts':		s.T.Ts = tok.value[0].value
			elif tok.type == 'Tw':		s.T.Tw = tok.value[0].value
			elif tok.type == 'Tz':		s.T.Tz = tok.value[0].value
			elif tok.type == 'Td':		s.T.do_Td(tok.value[0].value, tok.value[1].value)
			elif tok.type == 'TD':		s.T.do_TD(tok.value[0].value, tok.value[1].value)
			elif tok.type == 'Tstar':	s.T.do_Tstar()

			else:
				raise ValueError("Cannot render '%s' token yet" % tok.type)

	def GetFullText(self):
		"""
		Get the full text in the document.
		This mashes all text into one continuous string with rows of text having newlines separating them.
		Returns a list of txt streings, with one string per page.
		"""

		# Get the root object and the pages in DFS order
		root = self.GetRootObject()
		pages = root.Pages.DFSPages()

		# Final text and callback state
		fulltxt = []
		txt = []
		state = {'y': -1.0}

		def cb(action, *args):
			if action != 'glyph draw':
				return

			x,y = args[0]
			g = args[1]

			# New row then add newline
			if state['y'] != y:
				txt.append('\n')
				state['y'] = y

			# Add character
			txt.append(g.unicode)

		# Iterate through pages
		for page in pages:
			self.RenderPage(page, cb)

			# Index by page
			fulltxt.append( "".join(txt) )
			txt.clear()

		return fulltxt

	def GetPageThumbnail(self, page):
		"""
		Returns the Thumb object for the provided page.
		If no Thumb is provided in the file then None is returned instead.

		The page can be a Page object or a page number (page is found by DFS'ing the page tree and
		counting (i.e., it does not look at page labels)).
		"""

		if type(page) == int:
			root = self.GetRootObject()
			pages = root.Pages.DFSPages()

			if page < 1:				raise ValueError("Page number (%d) must be a positive number" % page)
			if page > len(pages):		raise ValueError("Page number (%d) is larger the total number of pages" % page)

			# Get page (pages is zero-based and pagenum is one-based, so subtract one)
			page = pages[page-1]

		elif isinstance(page, _pdf.Page):
			# Page supplied, nothing to get
			pass

		else:
			raise TypeError("Unrecognized page type passed: %s" % page)

		t = page.Thumb
		raise NotImplementedError()

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
		self.font = f
		self.widthmap = {}

		# Index widths by CID
		for subf in f.DescendantFonts:
			m = CIDWidthArrayToMap(subf.W)
			for k,v in m.items():
				self.widthmap[k] = (v, subf)

	def GetGlyph(self, cid):
		cmap = self.font.ToUnicode
		if not cmap.CMapper:
			cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

		# Map CID
		u = cmap.CMapper(cid)

		g = Glyph(cid)
		g.width = self.widthmap[cid][0]
		g.unicode = u

		return g

class FontCache:
	pdf = None

	# Font map: maps (object id, generation) to Font object
	font_map = None

	# Glyph map: maps (object id, generation) of font to dictionary of glyphs indexed by CID
	glyph_map = None

	# Differences array maps: maps (object id, generation) of FontEncoding object to map dictionary (made by DifferencesArrayToMap)
	diff_map = None

	def __init__(self, pdf):
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
			# Cache instance if not present
			if oid not in self.type0_map:
				self.type0_map[oid] = Type0FontCache(f)

			# Get glyph
			g = self.type0_map[oid].GetGlyph(cid)

			# Cache glyph
			self.glyph_map[oid][cid] = g

			return g

		elif type(f.Encoding) == str:
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

			# Cache glyph
			self.glyph_map[oid][cid] = g

			return g

		elif isinstance(f.Encoding, _pdf.FontEncoding):
			# Get objects
			cmap = f.ToUnicode
			enc = f.Encoding

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
			if not cmap.CMapper:
				cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

			# Bounds checking since these error strings are more descriptive than KeyErrors
			if cid not in self.diff_map[enc.oid] and cid not in encmap:
				raise ValueError("Unable to find character code %d ('%s') in differences map for encoding oid %s and base encoding '%s'" % (cid, chr(cid), f.Encoding.oid, be))

			# Get glyph name from differences mapping first, but otherwise fallback on the standard encoding map
			if cid in self.diff_map[enc.oid]:
				gname = self.diff_map[ enc.oid ][cid]
			else:
				gname = encmap[cid]

			u = _encodingmap.MapGlyphNameToUnicode(gname)
			if u == None:
				u = self.MissingGlyphName(f, encmap, cid, gname)

			w = f.Widths[ cid - f.FirstChar ]

			g = Glyph(cid)
			g.unicode = u
			g.width = w

			# Cache glyph
			self.glyph_map[oid][cid] = g

			return g
		else:
			raise TypeError("Unrecognized font encoding type: '%s'" % f.Encoding)

class Glyph:
	def __init__(self, cid):
		self.cid = cid
		self.unicode = None
		self.width = 0

	def __repr__(self):
		return str(self)
	def __str__(self):
		return "<Glyph cid=%d unicode='%s' width=%d>" % (self.cid, self.unicode, self.width or 0)

	def get_cid(self):				return self._cid
	def set_cid(self,v):			self._cid = v
	cid = property(get_cid, set_cid, doc="Character ID")

	def get_unicode(self):			return self._uni
	def set_unicode(self,v):		self._uni = v
	uni = property(get_unicode, set_unicode, doc="Glyph unicode")

	def get_width(self):			return self._width
	def set_width(self,v):			self._width = float(v)
	width = property(get_width, set_width, doc="Glyph width")


def GetTokenString(tok, bytesize=None):
	if tok.type == 'LIT':
		l = tok.value
		#print(['l', l])

		ret = SplitLiteral(l)

	elif tok.type == 'HEXSTRING':
		h = tok.value
		#print(['h', h])

		ret = SplitHex(h, bytesize)
	else:
		raise TypeError("Unrecognized Tj token type: %s" % tok.type)

	#print(ret)
	#print([ord(c) for c in ret])
	return ret

def SplitLiteral(lit):
	"""
	Split a literal string up by character by accounting for escape sequences.
	"""

	ret = []

	imax = len(lit)
	i = 0
	while i < imax:
		if lit[i] == '\\':
			# Ignore the backslash (I think this is the correct interpretation
			if lit[i+1] in ('\n', '\r', '\t', '\b', '\f'):
				ret.append(lit[i+1])
				i += 2

			# Intended character is the escaped character
			elif lit[i+1] == 'n':
				ret.append('\n')
				i += 2
			elif lit[i+1] == 'r':
				ret.append('\r')
				i += 2
			elif lit[i+1] == 't':
				ret.append('\t')
				i += 2
			elif lit[i+1] == 'b':
				ret.append('\b')
				i += 2
			elif lit[i+1] == 'f':
				ret.append('\f')
				i += 2

			elif lit[i+1] in ('(', ')'):
				ret.append(lis[i+1])
				i += 2

			elif lit[i+1].isdigit() and lit[i+2].isdigit() and lit[i+3].isdigit():
				ret.append( chr(int(lit[i+1:i+4], 8)) )
				i += 4

			elif lit[i+1].isdigit() and lit[i+2].isdigit():
				ret.append( chr(int('0' + lit[i+1:i+3], 8)) )
				i += 3

			elif lit[i+1].isdigit():
				ret.append( chr(int('00' + lit[i+1], 8)) )
				i += 2
			else:
				raise ValueError("Unable to handle literal at index %d for character '%s'" % (i, lit[i]))

		else:
			# No escape
			ret.append(lit[i])
			i += 1

	return ret

def SplitHex(txt, bytesize):
	"""
	Split hex string into characters of specified number of bytes.
	"""

	if bytesize == None:
		raise ValueError("Byte size not provided, cannot split hex string without it")

	# Trailing zero can be dropped per PDF standard, so put it back
	if len(txt)%2 == 1:
		txt += '0'

	if len(txt)%(bytesize*2) != 0:
		raise ValueError("Cannot split hex string (len=%d) into %d bytes without assuming padding" % (len(txt), bytesize*2))

	# If bytesize == 1 then need 2 characters, bytesize == 2 then need 4 characters
	ret = []
	for i in range(0, len(txt), bytesize*2):
		ret.append( chr(int(txt[i:i+(bytesize*2)],16)) )

	return ret

def CIDWidthArrayToMap(arr):
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


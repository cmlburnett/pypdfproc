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
				if gs.BM != None:		raise NotImplementedError("Graphics state setting (BM) blend mode not implemented yet")
				if gs.SMask != None:	raise NotImplementedError("Graphics state setting (SMask) soft mask not implemented yet")
				if gs.CA != None:		s.S.alphaconstant = (gs.CA, s.S.alphaconstant[1]) # Alpha constant for stroking
				if gs.ca != None:		s.S.alphaconstant = (s.S.alphaconstant[0], gs.ca) # Alpha constant for non-stroking
				if gs.AIS != None:		s.S.alphasource = gs.AIS # Alpha mode
				if gs.TK != None:		raise NotImplementedError("Graphics state setting (TK) text knockout flag not implemented yet")

			elif tok.type == 'l':		s.S.do_l(tok.value[0].value, tok.value[1].value)
			elif tok.type == 'm':		s.S.do_m(tok.value[0].value, tok.value[1].value)
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
		"""

		# Get the root object and the pages in DFS order
		root = self.GetRootObject()
		pages = root.Pages.DFSPages()

		# Final text and callback state
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

		return "".join(txt)

	def GetFullText2(self):
		"""
		Get the full text in the document.
		This mashes all text into one continuous string and does not subdivide the text by page, bead, column, or anything.
		One stream of text.
		For example, this would be useful for making a search index.
		"""

		# Get the root object and the pages in DFS order
		root = self.GetRootObject()
		pages = root.Pages.DFSPages()

		# Final text
		txt = []

		# The text tokenizer: one for the entire document
		tt = parser.TextTokenizer(self.f, self.p)

		# Iterate through each page since the font names change with each page
		for page in pages:
			cts = page.Contents

			# Can be an array of streams or a single stream
			if type(cts) == list:
				ct = " ".join([ct.Stream for ct in cts])
			else:
				ct = cts.Stream

			#print(ct)

			# Tokenize stream as text operations
			#print(ct)
			toks = tt.TokenizeString(ct)
			# Ignore the residual
			toks = toks['tokens']

			# Keep track of font information
			font = {}
			font['Tf'] = None		# Font name specified by Tf
			font['Tfs'] = None		# Font size specified by Tf
			font['f'] = None		# _pdf.Font object
			font['Tc'] = 0			# Character width specified by Tc
			font['Tw'] = 0			# Word width specified by Tw
			font['Th'] = 100		# Horizontal spacing specified by Tz (units of 1%)
			font['Tl'] = 0			# Leading specified by TL
			font['Tmode'] = 0		# Rendering mode specified by Tr
			font['Trise'] = 0		# Rise specified by Ts
			font['Tk'] = None		# Kncokout specified by ????
			font['Tm'] = None		# Text matrix
			font['Tlm'] = None		# Text line matrix
			font['Trm'] = None		# Text rendering matrix

			# Needed some times for Identity-H encoded fonts with hexstrings that are 2 bytes rather than 1 byte
			btsz = None

			# Iterate through the tokens that draw text to the page
			for tok in toks:
				# Font information (needs to be tracked until it changes)
				if tok.type == 'Tf':
					#print(['tok', tok])
					font['name'] = tok.value[0].value
					font['size'] = tok.value[1].value

					f = font['f'] = self.GetFont(page, font['name'])
					if f.Subtype == 'Type0':
						fd = None
					else:
						fd = f.FontDescriptor
					enc = f.Encoding
					cmap = f.ToUnicode

					# Identity-H needs 2 bytes from hex strings
					if type(enc) == str and enc == 'Identity-H':
						btsz = 2
					else:
						btsz = None

					#print(['f', f])
					#print(f.getsetprops())
					#print('Font: %s' % f.BaseFont)
					#print('Size: %s' % font['size'])

					#if f.Subtype in ('Type1', 'Type3', 'TrueType'):
					#	print('First char: %d' % f.FirstChar)
					#	print('Last char: %d' % f.LastChar)
					#elif f.Subtype in ('Font0'):
					#	print(['descendant fonts', f.DescendantFonts])

					#print([f, fd, enc, cmap])
					#print(f.getsetprops())
					#print(f.DescendantFonts)
					if f.Subtype in ('Font0'):
						if len(f.DescendantFonts) == 1:
							w = f.DescendantFonts[0].W.array
							wmap = CIDWidthArrayToMap(w)

							w = [_ for _ in wmap.values() if _>0]
							avg = (sum(w))/len(w)
							font['sizes'] = {'min': min(w), 'avg': avg, 'max': max(w)}


					#for d in f.DescendantFonts:
					#	print(d)
					#	print(d.getsetprops())
					#	print(d.FontDescriptor)
					#	print(d.FontDescriptor.getsetprops())

					if f.Subtype in ('Type1', 'Type3', 'TrueType'):
						w = f.Widths.array

						w = [_ for _ in w if _>0]
						avg = (sum(w))/len(w)
						font['sizes'] = {'min': min(w), 'avg': avg, 'max': max(w)}
						#print(['w', w, min(w), avg, max(w)])
						#print(fd.getsetprops())
						#if type(enc) != str:
						#	print(enc.getsetprops())
						#print(cmap.Stream)
					else:
						font['sizes'] = {}

				# Token value is a single literal of text
				elif tok.type == 'Tj':
					#print(['tok', tok])

					ret = GetTokenString(tok.value[0], bytesize=btsz)
					#print(ret)
					#print([ord(r) for r in ret])

					ret = [MapCharacter(f, enc, cmap, c) for c in ret]
					#print(ret)
					#print([ord(r) for r in ret])
					txt += ret

					# FIXME: need to more fully implement graphics state to ascertain if a space is needed
					# (e.g., starting next line vs. changing font mid-word)
					#txt += ' '

				# Token is an array of literal and inter-character spacing integers
				elif tok.type == 'TJ':
					#print(['tok', tok])
					v = tok.value
					for part in v:
						if part.type == 'LIT':
							ret = GetTokenString(part, bytesize=btsz)

							ret = [MapCharacter(f, enc, cmap, c) for c in ret]
							#print(ret)
							#print([ord(r) for r in ret])
							txt += ret
						elif part.type in ('INT', 'FLOAT'):
							# FIXME: may have to content with inter-character spacing used for space characters...
							# For now just ignore
							#print(part)

							# Somewhat of a fix for the above mentioned space issue
							# This heuristically assumes that any inter-word spacing that's greater than 50% of
							# the average character width is a space
							if abs(part.value) > 0.5*font['sizes']['avg']:
								txt += ' '

						else:
							raise TypeError("Unrecognize type in TJ array: %s" % part.type)

					# FIXME: need to more fully implement graphics state to ascertain if a space is needed
					# (e.g., starting next line vs. changing font mid-word)
					#txt += ' '

				# Don't care about anything else
				# NB: possible that state is pushed and poped (Q and q) that changes the current font information, but that's more advanced for now
				else:
					pass

		return "".join(txt)

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

		if type(f.Encoding) == str:
			encmap = _encodingmap.MapCIDToGlyphName(f.Encoding)

			# Character code to glyph name to unicode
			gname = encmap[cid]
			u = _encodingmap.MapGlyphNameToUnicode(gname)

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
			raise NotImplementedError()
		else:
			raise TypeError("Unrecognized font encoding type: '%s'" % f.Encoding)

		raise NotImplementedError()

	def GetGlyph2(self, oid, cid):
		# Get font from PDF or cache
		if oid not in self.font_map:
			f = self.pdf.p.GetObject(oid[0], oid[1])
			self.font_map[oid] = f
			self.glyph_map[oid] = {}
		else:
			f = self.font_map[oid]

		cid_cmap = None
		if f.ToUnicode != None:
			cmap = f.ToUnicode
			if not cmap.CMapper:
				cmap.CMapper = parser.CMapTokenizer().BuildMapper(cmap.Stream)

			try:
				ret = cmap.Cmapper(cid)
				if type(ret) == int:
					raise TypeError("Should return char for '%s' (ord %d) but got integer %d" % (c, ord(c), ret))

				if ret in diffmap:
					ret = diffmap[ret]

				cid_cmap = ret

			except KeyError:
				# Not in CMap, so try the differences array
				pass

		# Get glyph if not cached
		if cid not in self.glyph_map:
			# Getting glyph differs with each font type
			if f.Subtype == 'TrueType':
				g = self.GetGlyph_TrueType(f, cid)
			elif f.Subtype == 'Type1':
				g = self.GetGlyph_Type1(f, cid)
			else:
				raise ValueError("Unknown font type: %s" % f.Subtype)

			# Remap regardless of what font did
			if cid_cmap != None:
				g.unicode = cid_cmap

			self.glyph_map[cid] = g

		# Return Glyph object
		return self.glyph_map[cid]

	def GetGlyph_Type1(self, f, cid):
		return self.GetGlyph_TrueType(f, cid)

	def GetGlyph_TrueType(self, f, cid):
		g = Glyph(cid)
		g.width = f.Widths[ cid - f.FirstChar ]

		fd = f.FontDescriptor
		enc = f.Encoding

		if type(enc) == str:
			if enc == 'MacRomanEncoding':
				g.unicode = chr(cid).encode('latin-1').decode('mac_roman')
			elif enc == 'WinAnsiEncoding':
				# Close enough to WinAnsiEncoding
				g.unicode = chr(cid)
			elif enc == 'Identity-H':
				g.unicode = chr(cid)
			else:
				raise ValueError("Unrecognized encoding '%s' for font: %s" % (enc, f))

		elif isinstance(enc, _pdf.FontEncoding):
			if enc.oid not in self.diff_map:
				self.diff_map[ enc.oid ] = DifferencesArrayToMap(enc.Differences)

			g.unicode = self.diff_map[ enc.oid ][cid]

		else:
			raise NotImplementedError()

		# FIXME: not long-term solution
		if g.unicode in diffmap:
			g.unicode = diffmap[g.unicode]

		return g

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

# FIXME: not the way to do this I don't think
diffmap = {}
diffmap['hyphen'] = '-'
diffmap['space'] = ' '
diffmap['period'] = '.'
diffmap['comma'] = ','
diffmap['semicolon'] = ';'
diffmap['colon'] = ':'
diffmap['endash'] = '\u2013'
diffmap['emdash'] = '\u2014'
diffmap['parenleft'] = '('
diffmap['parenright'] = ')'
diffmap['bullet'] = '\u2022'
diffmap['bracketleft'] = '['
diffmap['bracketright'] = ']'
diffmap['equal'] = '='

diffmap['one'] = '1'
diffmap['two'] = '2'
diffmap['three'] = '3'
diffmap['four'] = '4'
diffmap['five'] = '5'
diffmap['six'] = '6'
diffmap['seven'] = '7'
diffmap['eight'] = '8'
diffmap['nine'] = '9'
diffmap['zero'] = '0'

# FIXME: work-around for font AdvP4C4E51
diffmap['C0'] = '\u2212'		# Minus sign
diffmap['C6'] = '\u00B1'		# Plus-minus sign
diffmap['C14'] = '\u00B0'		# Degree symbol
diffmap['C15'] = '\u2022'		# Bullet
diffmap['C211'] = '\u00A9'		# Copyright

unicode_mapdat = {}
#unicode_mapdat[8211] = "-"		# x2013 is EN DASH but can just use hyphen
unicode_mapdat[8217] = "'"		# x2019 is RIGHT SINGLE QUATATION MARK but is often used as an apostrophe
unicode_mapdat[64428] = "ff"	# xFB00 is LATIN SMALL LIGATURE FF is sometimes used instead of "ff" for some reason
unicode_mapdat[64429] = "fi"	# xFB01 is LATIN SMALL LIGATURE FI is sometimes used instead of "fi" for some reason
unicode_mapdat[64430] = "fl"	# xFB02 is LATIN SMALL LIGATURE FL is sometimes used instead of "fl" for some reason
unicode_mapdat[64431] = "ffi"	# xFB03 is LATIN SMALL LIGATURE FFI is sometimes used instead of "ffi" for some reason
unicode_mapdat[64432] = "ffl"	# xFB04 is LATIN SMALL LIGATURE FFL is sometimes used instead of "ffl" for some reason
unicode_mapdat[64434] = "st"	# xFB06 is LATIN SMALL LIGATURE ST is sometimes used instead of "st" for some reason

def MapCharacter(f, enc, cmap, c, dounicodemap=True):
	"""
	This has the challenging task of converting a PDF character code to a unicode character.
	Not trivial...
	"""

	# Map certain characters back to ascii stuff
	c = _MapCharacter(f, enc, cmap, c)

	if dounicodemap and ord(c) in unicode_mapdat:
		return unicode_mapdat[ord(c)]
	else:
		return c

def _MapCharacter(f, enc, cmap, c):
	if cmap:
		# Do this once for each cmap stream
		if not cmap.CMapper:
			ct = parser.CMapTokenizer()
			cmap.CMapper = ct.BuildMapper(cmap.Stream)

		try:
			ret = cmap.CMapper(c)
			if type(ret) == int:
				raise TypeError("Should return char for '%s' (ord %d) but got integer %d" % (c, ord(c), ret))

			if ret in diffmap:
				ret = diffmap[ret]
			return ret

		except KeyError:
			# Not in CMap, so try the differences array
			pass

	if isinstance(enc, _pdf.FontEncoding):
		if enc.Differences:
			m = DifferencesArrayToMap(enc.Differences)

			if ord(c) not in m:
				raise KeyError("Cannot map character (ord %d) in differences array with length %d" % (ord(c), len(enc.Differences)))

			ec = m[ord(c)]

			if ec in diffmap:
				ret = diffmap[ec]
			else:
				ret = ec

			if ret == 'C6':
				print(['diff', enc.Differences])
				print(['enc', enc.getsetprops()])
				print(m)
				print(f.FontDescriptor.getsetprops())
				print(f.FontDescriptor.FontFile3)
				print(f.FontDescriptor.FontFile3.Dict)
				print(f.FontDescriptor.FontFile3.Stream)

			if type(ret) == int:
				raise TypeError("Should return char for '%s' but got integer %d" % (c, ret))
			return ret
	elif type(enc) == str:
		if enc == 'MacRomanEncoding':
			return c.encode('latin-1').decode('mac_roman')
		elif enc == 'WinAnsiEncoding':
			# Apparently WinAnsiEncoding is close enough to latin-1
			return c
		elif enc == 'Identity-H':
			return c
		else:
			raise NotImplementedError("Unrecognized font encoding: '%s'" % enc)
	else:
		# No mapping: PDF character code is equivalent to unicode character (neat)
		return c

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

	lastcode = 0
	for i in range(len(arr)):
		if type(arr[i]) == int:
			lastcode = i
		elif isinstance(arr[i], _pdf.Array):
			for k in range(len(arr[i])):
				mapdat[lastcode] = arr[i][k]
				lastcode += 1
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


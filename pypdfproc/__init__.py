"""
PDF Processor
"""

__version__ = "1.0.0"

__all__ = ['parser']

# System libs
import mmap

# Local files
from . import parser
from . import pdf as _pdf
from .fontcache import FontCache

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

	def GetPage(self, page):
		"""
		Page number provided, find corresponding page
		"""

		if type(page) == int:
			root = self.GetRootObject()
			pages = root.Pages.DFSPages()

			if page < 1:				raise ValueError("Page number (%d) must be a positive number" % page)
			if page > len(pages):		raise ValueError("Page number (%d) is larger the total number of pages" % page)

			# Get page (pages is zero-based and pagenum is one-based, so subtract one)
			return pages[page-1]

		elif isinstance(page, _pdf.Page):
			return page

		else:
			raise TypeError("Unrecognized page type passed: %s" % page)

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

		page = self.GetPage(page)

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

		page = self.GetPage(page)

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

		page = self.GetPage(page)

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

			elif tok.type == 'h':		s.S.do_h()
			elif tok.type == 'l':		s.S.do_l(*[v.value for v in tok.value])
			elif tok.type == 'm':		s.S.do_m(*[v.value for v in tok.value])
			elif tok.type == 'c':		s.S.do_c(*[v.value for v in tok.value])
			elif tok.type == 'v':		s.S.do_v(*[v.value for v in tok.value])
			elif tok.type == 'y':		s.S.do_y(*[v.value for v in tok.value])
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

				callback(s, 'change font', page, s.T.Tf, s.T.Tfs)
			elif tok.type in ('Tj', 'TJ'):
				for subtok in tok.value:
					#print(['stok', subtok])

					if subtok.type in ('INT', 'FLOAT'):
						# Adjust character spacing
						s.T.do_Tj(subtok.value, None)

						callback(s, 'space draw', page, subtok.value)
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
							#print(['t', s.T.Tf, t, ord(t)])
							g = self.GetGlyph(page, s.T.Tf, ord(t))
							#print(['g', t, g.width, g.unicode])

							# Calculate current drawing position before updating Tm
							m = parser.Mat3x3(s.T.Tfs*s.T.Tz,0, 0,s.T.Tfs, 0,s.T.Tr) * s.T.Tm * s.S.cm
							#print("<%.2f, %.2f> '%s'" % (m.E, m.F, g.unicode))

							callback(s, 'glyph draw', page, (m.E, m.F), g)

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
			elif tok.type == 'BDC':		pass
			elif tok.type == 'EMC':		pass

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
		state = {'y': -1.0, 'widths': None}

		def cb(s, action, page, *args):
			if action == 'change font':
				Tf = args[0]
				Tfs = args[1]

				f = self.GetFont(page, Tf)

				w = f.Widths
				w = [v for v in w if v != 0]
				state['widths'] = {'avg': sum(w)/float(len(w)), 'min': min(w), 'max': max(w)}

			elif action == 'glyph draw':
				x,y = args[0]
				g = args[1]

				# New row then add newline
				if state['y'] != y:
					txt.append('\n')
					state['y'] = y

				# Add character
				txt.append(g.unicode)

			elif action == 'space draw':
				w = args[0]

				# If the inter-character spacing is >50% of the average glyph width (both are in text space)
				# then assume an implied space
				#
				# NB: 50% is completely arbitrary; could be more thorough and find the width for a space character instead...
				if abs(w) > 0.5*state['widths']['avg']:
					txt.append(' ')


			else:
				# Don't care
				pass

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

		page = self.GetPage(page)

		t = page.Thumb
		raise NotImplementedError()


# FIXME: not the way to do this I don't think
unicode_mapdat = {}
#unicode_mapdat[8211] = "-"		# x2013 is EN DASH but can just use hyphen
unicode_mapdat[8217] = "'"		# x2019 is RIGHT SINGLE QUATATION MARK but is often used as an apostrophe
unicode_mapdat[64428] = "ff"	# xFB00 is LATIN SMALL LIGATURE FF is sometimes used instead of "ff" for some reason
unicode_mapdat[64429] = "fi"	# xFB01 is LATIN SMALL LIGATURE FI is sometimes used instead of "fi" for some reason
unicode_mapdat[64430] = "fl"	# xFB02 is LATIN SMALL LIGATURE FL is sometimes used instead of "fl" for some reason
unicode_mapdat[64431] = "ffi"	# xFB03 is LATIN SMALL LIGATURE FFI is sometimes used instead of "ffi" for some reason
unicode_mapdat[64432] = "ffl"	# xFB04 is LATIN SMALL LIGATURE FFL is sometimes used instead of "ffl" for some reason
unicode_mapdat[64434] = "st"	# xFB06 is LATIN SMALL LIGATURE ST is sometimes used instead of "st" for some reason

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


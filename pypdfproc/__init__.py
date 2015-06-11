"""
PDF Processor
"""

__version__ = "1.0.0"

__all__ = ['parser', 'PDF', '_pdf', 'cli']

# System libs
import cmd, mmap, os, sys, traceback

# Local files
from . import parser
from . import pdf as _pdf
from .fontcache import FontCache, CIDWidthArrayToMap
from .fontmetrics import FontMetricsManager
from .stdfonts import StandardFonts
from .betterfile import betterfile

STANDARD_FONT_AFM_ZIP = "StandardFonts_AFM.zip"

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

	_StandardFonts = None
	def get_StandardFonts(self):
		if self._StandardFonts == None:
			dname = os.path.dirname(__file__)
			self._StandardFonts = StandardFonts()
			self._StandardFonts.AddZip(dname + '/' + STANDARD_FONT_AFM_ZIP)

		return self._StandardFonts
	StandardFonts = property(get_StandardFonts, doc="Gets the StandardFonts object, loaded only until it's needed")

	def __init__(self, fname):
		# Copy the file name
		self.fname = fname

		# Open file and mmap it (binary is important here so that python does not interpret the file as text)
		self.f = betterfile.open(fname, 'rb')
		self.m = mmap.mmap(self.f.fileno(), 0, prot=mmap.PROT_READ)

		# Open the file and initialize it (xref/trailer reading)
		self.p = parser.PDFTokenizer(self.f)
		self.p.Initialize()

		self.fonts = FontCache(self)

	def Close(self):
		"""
		Closes the file and all associated things.
		This object becomes useless after closing.
		"""

		self.m.close()
		self.f.close()

		self.m = None
		self.f = None
		self.p = None

	# --------------------------------------------------------------------------------
	# Helper functions

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

	def GetFontWidths(self, f):
		if f.Subtype in ('TrueType', 'Type1'):
			# Not found, find from standard font
			if f.Widths == None:
				fm = self.StandardFonts.GetFontMetrics(f.BaseFont)
				# NB: this is a dictionary indexed by character name
				wids = fm.GetWidths()
				#print(['w', wids])

				mincid = 256
				maxcid = 0

				by_cname = {}
				for cname in wids.keys():
					c = fm.GetCharacter(cname)
					if c['C'] == -1: continue

					by_cname[cname] = c

					if c['C'] < mincid: mincid = c['C']
					if c['C'] > maxcid: maxcid = c['C']

				# If they are not provided, then the min and max character ids need to be determined
				if f.FirstChar == None:		f.FirstChar = mincid
				if f.LastChar == None:		f.LastChar = maxcid

				by_cid = {}
				for wcname in wids.keys():
					if wcname not in by_cname: continue

					w = by_cname[wcname]
					cid = w['C']
					if cid >= f.FirstChar and cid <= f.LastChar:
						by_cid[cid] = w['W'][0]

				# Must add in missing CID's as zeros
				cids = list(by_cid.keys())
				cids.sort()
				for i in range(mincid, maxcid+1):
					if i not in cids:
						by_cid[i] = 0

				# Resort and form contiguous widths array
				cids = list(by_cid.keys())
				cids.sort()
				f.Widths = [by_cid[cid] for cid in cids]


			return f.Widths

		elif f.Subtype == 'Type0':
			widths = {}

			for subf in f.DescendantFonts:
				m = CIDWidthArrayToMap(subf.W)
				for k,v in m.items():
					widths[k] = v

			keys = list(widths.keys())
			keys.sort()

			# Return in order, but may have gaps in CID coverage
			return [widths[k] for k in keys]

		else:
			raise NotImplementedError("Unrecognized font type '%s'" % f.Subtype)

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
		"""
		Simple function that maps a character ID (@cid) of a font name (@fontname) on a given page (@page) to a Glyph object.
		Utilizes a cache object to speed lookups, but no caching is done locally.
		"""

		# Get font just to get object ID
		f = self.GetFont(page, fontname)

		# Glyph is irrespective of page, just font and character ID
		# NB: this object does all CID->glyph caching
		return self.fonts.GetGlyph(f.oid, cid)

	def RenderPages(self, callback):
		"""
		Renders the entire document by steping through each page in a DFS fashion, and invoking a callback function @callback as appropriate.
		"""

		# Get the root object and the pages in DFS order
		root = self.GetRootObject()
		pages = root.Pages.DFSPages()

		callback(None, 'render pages start', None)

		for page in pages:
			try:
				self.RenderPage(page, callback)
			except:
				# Return is whether or not to stop rendering on exception
				ret = callback(None, 'page exception', None)
				if ret:
					# Quit by re-raising exception
					raise

		callback(None, 'render pages end', None)

	def RenderPage(self, page, callback):
		"""
		Renders a single page @page by processing every content command and invoking a callback function @callback as appropriate.
		"""

		page = self.GetPage(page)

		# The text tokenizer
		tt = parser.TextTokenizer(self.f, self.p)

		cts = page.Contents
		if type(cts) == list or type(cts) == _pdf.Array:
			ct = []
			for c in cts:
				if isindirect(c):
					ct.append(self.p.GetContent(c))
				elif isinstance(c, _pdf.Content):
					ct.append(c)
				else:
					raise TypeError("Unexpected type for content array: '%s'" % c)
			ct = " ".join([c.Stream for c in ct])
		else:
			ct = cts.Stream
		#print(ct)

		s = parser.StateManager()
		callback(s, 'page start', page)


		# Tokenize the string as a list of tokens
		toks = tt.TokenizeString(ct)['tokens']

		# Iterate through each token and handle it appropriate by manipulating the state object
		# and calling the callback function as appropriate
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
			elif tok.type == 'Wstar':	pass

			elif tok.type == 'Do':		pass # Paint Xobject named by tok.value[0].value

			# Colorspaces
			elif tok.type == 'cs':		s.S.colorspace = (s.S.colorspace[0], tok.value[0].value)
			elif tok.type == 'CS':		s.S.colorspace = (tok.value[0].value, s.S.colorspace[1])
			elif tok.type == 'sc':		s.S.color = (s.S.color[0], tok.value[0].value)
			elif tok.type == 'SC':		s.S.color = (tok.value[0].value, s.S.color[1])
			elif tok.type == 'scn':		s.S.color = (s.S.color[0], tok.value[0].value)
			elif tok.type == 'SCN':		s.S.color = (tok.value[0].value, s.S.color[1])
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

		callback(s, 'page end', page)

	# --------------------------------------------------------------------------------
	# Utility functions that provide a some sort of utility function

	def GetFullText(self):
		"""
		Get the full text in the document.
		This mashes all text into one continuous string with rows of text having newlines separating them.
		Returns a list of txt streings, with one string per page.
		"""

		# Final text and callback state
		fulltxt = []
		txt = []
		state = {'y': -1.0, 'widths': None}

		# Callback function that si appropriate to handle generation of a fulltext transcript of the document
		def cb(s, action, page, *args):
			if action == 'page exception':
				# Keep going and do nothing about the exception
				traceback.print_exc()
				return False
			elif action == 'change font':
				Tf = args[0]
				Tfs = args[1]

				f = self.GetFont(page, Tf)

				w = self.GetFontWidths(f)

				if type(w) == dict:
					# Dict is keyed on character name with (horizontal, vertical) 2-tuple widths
					w = [v[0] for v in list(w.values()) if v[0] != 0]
					state['widths'] = {'avg': sum(w)/float(len(w)), 'min': min(w), 'max': max(w)}
				elif type(w) == list or type(w) == _pdf.Array:
					w = [v for v in w if v != 0]
					state['widths'] = {'avg': sum(w)/float(len(w)), 'min': min(w), 'max': max(w)}
				else:
					raise TypeError("Unrecognized widths object type: '%s'" % str(w))


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

			elif action == 'page end':
				# Index by page
				fulltxt.append( "".join(txt) )
				txt.clear()

			else:
				# Don't care
				pass

		# Render all the pages and use the above callback function
		self.RenderPages(cb)

		# Return a list of strings where each string represents one page of text
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
	"""
	Based on the token type, get the data as an array of characters to operate on.
	Hex strings require a size be specified as to how many bytes are blocked together to form a single character (supply this via @bytesize).
	"""

	if tok.type == 'LIT':				return SplitLiteral(tok.value)
	elif tok.type == 'HEXSTRING':		return SplitHex(tok.value, bytesize)
	else:
		raise TypeError("Unrecognized Tj token type: %s" % tok.type)

def SplitLiteral(lit):
	"""
	Split a literal string up by character by accounting for escape sequences.
	"""

	ret = []

	imax = len(lit)
	i = 0
	while i < imax:
		if lit[i] == '\\':
			if lit[i+1] == '\\':
				ret.append(lit[i])
				i += 2

			# Ignore the backslash (I think this is the correct interpretation
			elif lit[i+1] in ('\n', '\r', '\t', '\b', '\f'):
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
	# NB: mod 2 is correct since only one trailing zero may be trimmed
	if len(txt)%2 == 1:
		txt += '0'

	# NB: bytesize*2 since two base-16 characters form a byte
	if len(txt)%(bytesize*2) != 0:
		raise ValueError("Cannot split hex string (len=%d) into %d bytes without assuming padding" % (len(txt), bytesize*2))

	# If bytesize == 1 then need 2 characters, bytesize == 2 then need 4 characters
	# Iterate through starting indexes (@i) and jump by the number of characters in @txt to form hexstring character
	return [chr(int(txt[i:i+(bytesize*2)],16)) for i in range(0, len(txt), bytesize*2)]


# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------

def format_cols(dat, pre="  ", celldiv=" ", rowdiv="\n", post=""):
	"""
	Simple method for formating multi-column data.
	"""

	# No data = no output
	if not len(dat):
		return ""

	# Create list of max column sizes
	maxes = [0] * len(dat[0])
	# Calculate max column sizes
	for i in range(len(dat)):
		row = dat[i]
		for j in range(len(row)):
			# Get cell length
			l = len(row[j])
			# If longer than max then update max
			if maxes[j] < l:
				maxes[j] = l

	# Now format each row as a collection of cells
	ret = []
	for i in range(len(dat)):
		retrow = []

		row = dat[i]
		for j in range(len(row)):
			cell = ("%%%ds" % maxes[j]) % row[j]
			retrow.append(cell)

		# Space between each column
		ret.append(pre + celldiv.join(retrow) + post)

	# Newline between each row
	return rowdiv.join(ret)

def pdfbase_objects(obj):
	dat = []

	if isinstance(obj, _pdf.PDFHigherBase):
		ps = obj.getsetprops()
		for k,v in ps.items():
			if k == '_Loader': continue
			if k[0] != '_': continue

			if v == None: continue

			dat.append( (k[1:],) )

	elif isinstance(obj, _pdf.PDFStreamBase):
		dat.append( ('Dict',) )
		dat.append( ('Stream',) )
		dat.append( ('StreamRaw',) )

	elif isinstance(obj, _pdf.Dictionary):
		keys = obj.dictionary.keys()
		keys.sort()

		for k in keys:
			v = obj.dictionary[k]

			if type(v) == str:
				dat.append( (k,v) )
			else:
				dat.append( (k,"%s"%v) )

	else:
		raise CmdError("Unrecognized type: '%s'" % obj)

	return dat


class CmdError(Exception):
	"""
	Catching this exception results in the message being printed.
	Other exceptions caught result in the full traceback being printed.
	"""

	def get_Message(self):
		return self.args[0]
	Message = property(get_Message)

class PDFCmdState:
	"""
	Handles and maintains the CLI state.
	This is so that that is separate from the actual CLI parsing.
	"""

	_files = None
	_pdfs = None
	_pwd = None

	def __init__(self):
		self._files = []
		self._pdfs = {}
		self._pwd = []

	def quit(self):
		for f in self._files:
			if self._pdfs[f[0]] != None:
				self._pdfs[f[0]].Close()
		self._files = []
		self._pdfs.clear()

	def prompt(self):
		if len(self._pwd):
			return "%s $ " % self._pwd_item( self._pwd[-1] )
		else:
			return "/ $ "

	# ---------------------------------------------------------------
	# Commands

	def open(self, item):
		f = item.strip()

		absf = os.path.abspath(f)
		fname = os.path.basename(absf)
		if not os.path.exists(f):
			raise CmdError("File '%s' does not exist" % f)

		# Cannot have more than one file with the same filename open, sorry
		# This restriction also exists in Word, Excel, etc. for the same reason I'm sure
		if fname in self._pdfs:
			raise CmdError("Cannot open more than one file with the same filename: '%s'" % f)

		self._files.append( (fname,absf,os.stat(absf)) )
		self._pdfs[fname] = PDF(absf)

	def close(self, item):
		item = item.strip()

		# If somewhere inside the file being closed, then cd to the root first
		if len(self._pwd) and self._pwd[0] == item:
				self.cd("/")

		# Close file if it is found
		for i in range(len(self._files)):
			f = self._files[i]
			if f[0] == item:
				self._pdfs[ f[0] ].Close()

				del self._files[i]
				del self._pdfs[ f[0] ]
				return

		raise CmdError("File '%s' not found, cannot close it" % item)

	def _pwd_item(self, item):
		if type(item) == str:
			return item
		elif type(item) == tuple:
			# Tuple format is (object, text to show)
			return item[1]
		elif isinstance(item, _pdf.PDFBase):
			return str(item.__class__.__name__)
		else:
			raise TypeError("Unrecognized pwd stack type: '%s' (type %s)" % (item, type(item)))

	def pwd(self):
		ret = []
		for p in self._pwd:
			_ = self._pwd_item(p)
			ret.append(_)

		return "/" + "/".join(ret)

	def cd(self, line):
		line = line.strip()

		if line == '' or line == '/':
			self._pwd = []
			return

		# Strip trailing slash as it is unnecessary
		if line.endswith('/'):
			line = line[0:-1]

		parts = line.split('/')
		for part in parts:
			self._cd(part)

	def _cd(self, line):
		if line == '' or line == '/':
			self._pwd = []
		elif line == '.':
			# Nothing to do
			pass
		elif line == '..':
			self._pwd.pop()

		elif len(self._pwd) == 0:
			# At root, cd'ing into a file
			for f in self._files:
				if f[0] == line:
					self._pwd.append(f[0])
					return

			raise CmdError("File '%s' not opened, open it first to use it" % line)

		elif len(self._pwd) == 1:
			# cd'ing around inside a file
			item = line.strip().lower()

			if item == 'catalog':
				fname = self._pwd[0]
				p = self._pdfs[fname]
				self._pwd.append(p.GetRootObject())
			elif item == 'objects':
				self._pwd.append('Objects')
			elif item == 'xref':
				self._pwd.append('XRef')
			else:
				raise CmdError("No PDF root level of '%s'" % line)

		elif len(self._pwd) > 1:
			prev = self._pwd[-1]

			# Unpack tuple
			if type(prev) == tuple:
				prev = prev[0]

			if type(prev) == list:
				idx = int(line)
				self._pwd.append( (prev[idx],"[%d]"%idx) )
			elif isinstance(prev, _pdf.Dictionary):
				self._pwd.append( line )

			elif isinstance(prev, _pdf.PDFStreamBase):
				line = line.lower()

				if line == 'dict':
					self._pwd.append( prev.Dict )
				elif line == 'stream':
					self._pwd.append( "Stream" )
				elif line == 'streamraw':
					self._pwd.append( "StreamRaw" )
				else:
					raise CmdError("Stream has no property '%s'" % line)

			elif isinstance(prev, _pdf.PDFBase):
				# TODO: requires case to be exact
				ps = prev.getsetprops()
				if '_Loader' in ps: del ps['_Loader']
				k = '_'+line
				if k in ps:
					v = getattr(prev, line)
					if isinstance(v, _pdf.Array) or type(v) == list:
						# Tuple of (object, text to show in pwd)
						self._pwd.append( (v, line) )
					else:
						self._pwd.append(v)
				else:
					raise CmdError("Object does not have property '%s'" % line)
			else:
				raise TypeError("Unrecognized type: '%s'" % prev)

		else:
			raise CmdError("Cannot cd for '%s'" % line)

	def ls(self, line):
		if not len(self._pwd):
			dat = []
			for f in self._files:
				dat.append( (f[0], "%d bytes" % f[2].st_size) )

			ret = "total %d\n" % len(self._files)
			ret += format_cols(dat, celldiv="  ")
			return ret

		elif len(self._pwd) == 1:
			# Root listing
			fname = self._pwd[0]
			p = self._pdfs[fname]
			root = p.GetRootObject()

			dat = [ ('Catalog',), ('Objects',), ('XRef',) ]
			return format_cols(dat)

		elif len(self._pwd) == 2:
			# Listing of one of the root pieces of inforamtion in a file
			fname = self._pwd[0]
			p = self._pdfs[fname]

			typ = self._pwd[1]

			if isinstance(typ, _pdf.Catalog):
				root = typ

				dat = []

				ps = root.getsetprops()
				for k,v in ps.items():
					if k == '_Loader': continue
					if k[0] != '_': continue

					if v == None: continue

					dat.append( (k[1:],) )

				return format_cols(dat)

			elif typ.lower() == 'objects':
				pass
			elif typ.lower() == 'xref':
				pass
			else:
				raise CmdError("Unrecognized level '%s' under object" % typ)

		elif len(self._pwd) > 2:
			item = self._pwd[-1]
			if isinstance(item, _pdf.PDFBase):
				dat = pdfbase_objects(item)
				return format_cols(dat)

			# Tuple format is (object, text to show in pwd)
			elif type(item) == tuple:
				if isinstance(item[0], _pdf.PDFBase):
					dat = pdfbase_objects(item[0])
				elif type(item[0]) == list:
					dat = []
					for i in range(len(item[0])):
						dat.append( ("[%d]"%i, str(item[0][i].__class__).split('.')[-1]) )

				else:
					raise TypeError("Unexpected tuple[0] object: '%s'" % item[0])

				return format_cols(dat)

			elif type(item) == str:
				pprev = self._pwd[-2]

				if isinstance(pprev, _pdf.PDFStreamBase):
					if item == 'Stream':
						# Nowhere else to go
						return
					elif item == 'StreamRaw':
						# Nowhere else to go
						return
					else:
						raise TypeError("Unrecognized Stream property: '%s'" % item)
				else:
					raise TypeError("Unrecognized top pwd type: '%s'" % (pprev,))
			else:
				raise TypeError("Unexpected top pwd type: '%s'" % (self._pwd[-1],))

		else:
			raise NotImplementedError

	def cat(self, line):
		if len(self._pwd) == 0:
			raise CmdError("Nothing to cat at root level")
		elif len(self._pwd) == 1:
			raise CmdError("Nothing to cat at root level of the file")
		else:
			prev = self._pwd[-1]
			pprev = self._pwd[-2]

			if isinstance(pprev, _pdf.PDFStreamBase):
				if prev == 'Stream':
					return pprev.Stream
				elif prev == 'StreamRaw':
					return pprev.StreamRaw
				else:
					raise CmdError("Unrecognized part of stream: '%s'" % prev)

			elif isinstance(pprev, _pdf.Dictionary):
				k = prev
				v = pprev[k]

				if type(v) == str:
					return v
				else:
					raise TypeError("Unrecognized type for dictionary value for key '%s': '%s'" % (k,v))
			else:
				raise TypeError("Unrecognized type for cat: '%s'" % prev)

class PDFCmd(cmd.Cmd):
	"""
	CLI interface handling class.
	Explicitly does not handle or store any state information.
	Utilizes the PDFCmdState class to store and maintain state.
	"""

	state = None

	def get_prompt(self): return self.state.prompt()
	prompt = property(get_prompt)

	def __init__(self, *args, **kargs):
		cmd.Cmd.__init__(self, *args, **kargs)

		self.state = PDFCmdState()

	def setinitargs(self, args):
		for arg in args:
			self.do_open(arg)

	# ----------------------------------------------------------------------------------------
	# ----------------------------------------------------------------------------------------

	def onecmd(self, line):
		try:
			return cmd.Cmd.onecmd(self, line)

		except SystemExit:
			print("")
			raise
		except CmdError as e:
			# Print just the message instead of the whole exception traceback
			print(e.Message)
		except:
			traceback.print_exc()
			# That's it, just print and continue on with life

	# ----------------------------------------------------------------------------------------
	# ----------------------------------------------------------------------------------------
	# Commands

	def do_open(self, line):
		"""Open a file. Doing so adds it to the root file list."""
		ret = self.state.open(line)
		if ret:
			print(ret)

	def do_close(self, line):
		"""Close a file. Doing so removes it from the root file list."""
		ret = self.state.close(line)
		if ret:
			print(ret)

	def do_ls(self, line):
		"""List available objects at current location"""
		ret = self.state.ls(line)
		if ret:
			print(ret)

	def do_pwd(self, line):
		"""Print current working directory"""
		ret = self.state.pwd()
		if ret:
			print(ret)

	def do_cd(self, line):
		"""Change directory"""
		ret = self.state.cd(line)
		if ret:
			print(ret)

	def do_cat(self, line):
		"""Print output to screen"""
		ret = self.state.cat(line)
		if ret:
			print(ret)

	def do_quit(self, line):
		"""Quit the command-line interface"""
		self.state.quit()

		sys.exit(0)
	def do_EOF(self, line):
		"""Quit the command-line interface (ctrl-d)"""
		self.do_quit(line)

	@staticmethod
	def Run(args=None):
		c = PDFCmd()
		c.setinitargs(args)
		c.cmdloop(intro="PDF command-line interface. Type 'help' or '?' to get available commands.")


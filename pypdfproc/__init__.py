"""
PDF Processor
"""

__version__ = "1.0.0"

__all__ = ['parser']

# System libs
import mmap

from . import parser
from . import pdf as _pdf

def isindirect(o):
	return isinstance(o, _pdf.IndirectObject)

class PDF:
	"""
	Basic entry point into manipulating PDF files.
	"""

	# File name, file object, and mmap object
	fname = None
	f = None
	m = None

	# PDF parser
	p = None

	def __init__(self, fname):
		self.fname = fname

		# Open file and mmap it
		self.f = open(fname, 'rb')
		self.m = mmap.mmap(self.f.fileno(), 0, prot=mmap.PROT_READ)

		# Open the file and initialize it (xref/trailer reading)
		self.p = parser.PDFTokenizer(self.m)
		self.p.Initialize()

	def Close(self):
		self.m.close()
		self.f.close()

		self.m = None
		self.f = None
		self.p = None

	def GetRootObject(self):
		return self.p.GetRootObject()

	def GetFont(self, page, fontname):
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
			raise ValueError("Unrecognize font name (%s) for page (%d)" % (fontname, pagenum))

		# Get font object
		f = recs.Font[fontname]

		# If it's an indirect, then fetch object
		if isindirect(f):
			f = self.p.GetFont(f)

		# Return Font1, Font3, or FontTrue object
		return f

	def GetFullText(self):
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
			toks = tt.TokenizeString(ct)
			# Ignore the residual
			toks = toks['tokens']

			# Keep track of font information
			font = {'name': None, 'size': None, 'f': None}

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

					#print('Font: %s' % f.BaseFont)
					#print('Size: %s' % font['size'])
					#print('First char: %d' % f.FirstChar)
					#print('Last char: %d' % f.LastChar)
					#print([f, fd, enc, cmap])
					#print(f.getsetprops())
					#print(f.DescendantFonts)

					w = f.Widths.array
					w = [_ for _ in w if _>0]
					avg = (sum(w))/len(w)
					font['sizes'] = {'min': min(w), 'avg': avg, 'max': max(w)}
					#print(['w', w, min(w), avg, max(w)])
					#print(fd.getsetprops())
					#if type(enc) != str:
					#	print(enc.getsetprops())
					#print(cmap.Stream)

				# Token value is a single literal of text
				elif tok.type == 'Tj':
					#print(['tok', tok])
					l = tok.value[0].value

					#print(['l', l])
					ret = SplitLiteral(l)
					#print(ret)
					ret = [MapCharacter(f, enc, cmap, c) for c in ret]
					#print(ret)
					txt += ret

					txt += ' '

				# Token is an array of literal and inter-character spacing integers
				elif tok.type == 'TJ':
					#print(['tok', tok])
					v = tok.value
					for part in v:
						if part.type == 'LIT':
							ret = SplitLiteral(part.value)
							ret = [MapCharacter(f, enc, cmap, c) for c in ret]
							#print(ret)
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

					txt += ' '

				# Don't care about anything else
				# NB: possible that state is pushed and poped (Q and q) that changes the current font information, but that's more advanced for now
				else:
					pass

		return "".join(txt)

	def GetPageThumbnail(self, page):
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

def MapCharacter(f, enc, cmap, c):
	"""
	This has the challenging task of converting a PDF character code to a unicode character.
	Not trivial...
	"""

	if isinstance(enc, _pdf.FontEncoding):
		if cmap:
			ct = parser.CMapTokenizer()
			m = ct.BuildMapper(cmap.Stream)

			try:
				ret = m(c)
				if type(ret) == int:
					raise TypeError("Should return char for '%s' (ord %d) but got integer %d" % (c, ord(c), ret))
				return ret

			except KeyError:
				# Not in CMap, so try the differences array
				pass

		if enc.Differences:
			m = DifferencesArrayToMap(enc.Differences)
			#print(['enc', enc.getsetprops()])
			#print(m)

			if ord(c) not in m:
				raise KeyError("Cannot map character (ord %d) in differences array with length %d" % (ord(c), len(enc.Differences)))

			ec = m[ord(c)]

			if ec in diffmap:
				ret = diffmap[ec]
			else:
				ret = ec

			if type(ret) == int:
				raise TypeError("Should return char for '%s' but got integer %d" % (c, ret))
			return ret
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

def DifferencesArrayToMap(arr):
	mapdat = {}

	lastcode = 0
	for item in arr:
		if type(item) == int:
			lastcode = item
		else:
			mapdat[ lastcode ] = item
			lastcode += 1

	return mapdat


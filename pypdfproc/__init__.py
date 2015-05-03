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

	# File name, file object (from open()), and mmap object
	fname = None
	f = None
	m = None

	# PDF parser (from pdf.py)
	p = None

	def __init__(self, fname):
		# Copy the file name
		self.fname = fname

		# Open file and mmap it (binary is important here so that python does not interpret the file as text)
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
			print(ct)
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

					print(['f', f])
					print(f.getsetprops())
					print('Font: %s' % f.BaseFont)
					print('Size: %s' % font['size'])

					#if f.Subtype in ('Type1', 'Type3', 'TrueType'):
					#	print('First char: %d' % f.FirstChar)
					#	print('Last char: %d' % f.LastChar)
					#elif f.Subtype in ('Font0'):
					#	print(['descendant fonts', f.DescendantFonts])

					print([f, fd, enc, cmap])
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
					print(['tok', tok])

					ret = GetTokenString(tok.value[0], bytesize=btsz)
					print(ret)
					print([ord(r) for r in ret])

					ret = [MapCharacter(f, enc, cmap, c) for c in ret]
					print(ret)
					print([ord(r) for r in ret])
					txt += ret

					# FIXME: need to more fully implement graphics state to ascertain if a space is needed
					# (e.g., starting next line vs. changing font mid-word)
					#txt += ' '

				# Token is an array of literal and inter-character spacing integers
				elif tok.type == 'TJ':
					print(['tok', tok])
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
		raise TypeError("Unrecognized Tj token type: %s" % tok.value[0].type)

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
	print(['cpre', c])
	c = _MapCharacter(f, enc, cmap, c)
	print(['cpst', c])
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


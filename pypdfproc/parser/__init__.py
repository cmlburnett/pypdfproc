import os

from . import pdf as pdfloc
from . import text as textloc
from . import cmap as cmaploc

from .. import pdf as _pdf

__all__ = ['PDFTokenizer']

def gotoend(f):
	"""
	Helper function that jumps to lass byte in the file.
	"""

	f.seek(-1, os.SEEK_END)

def readlinerev(f, n=1):
	"""
	Helper function that reads @n lines in reverse.
	"""

	if n == 1:
		return _readlinerev(f)

	lines = []
	for i in range(n):
		lines.append(_readlinerev(f))
	return lines

def _readlinerev(f):
	"""
	Helper function that reads a single line in reverse.
	"""

	# Stop at start of file
	ofs = f.tell()
	if ofs == 0:
		return None

	# Iterate until EOL is found
	startidx = ofs
	endidx = ofs
	while ofs >= 0:
		# Get current character
		c = f[ofs]

		# Found EOL, check if CRLF or just LF or Just CR
		if c == ord('\r'):
			startidx = ofs
			f.seek(-1, os.SEEK_CUR) # CR

			buf = f[startidx+1:endidx+1]
			return buf

		elif c == ord('\n'):
			startidx = ofs

			if f[ofs-1] == ord('\r'):
				f.seek(-2, os.SEEK_CUR) # CRLF
			else:
				f.seek(-1, os.SEEK_CUR) # LF

			buf = f[startidx+1:endidx+1]
			return buf

		if ofs == 0:
			break

		f.seek(-1, os.SEEK_CUR)
		ofs = f.tell()

	return f[0:endidx]


class PDFTokenizer:
	"""
	Tokenizer for PDF files that understand the Carousel object system.
	"""

	# File object, IOStream object, whatever as long as it meets basic read/seek/tell functionality
	file = None

	# PDF object (i.e., _pdf.PDF); must keep a copy so other functions can build upon it as needed
	pdf = None

	def __init__(self, file):
		if not hasattr(file, 'read'):		raise TypeError('PDF file object has no read() method')
		if not hasattr(file, 'seek'):		raise TypeError('PDF file object has no seek() method')
		if not hasattr(file, 'tell'):		raise TypeError('PDF file object has no tell() method')

		self.file = file
		self.pdf = None

	def Initialize(self):
		"""
		Initializes PDF reading by creating a PDF object.
		In order for this object to be useful, the xref/trailer combo must be read in its entirety.
		Thus, this reads the xref sections but does not parse any objects.
		"""

		self.pdf = _pdf.PDF()

		# Read header line
		h = self.ParseHeader(0)
		self.pdf.AddContentToMap(0, h)


		# Read trailer at end of file
		gotoend(self.file)

		# Iterate backward until first "xref" is found, which is followed by the end trailer
		lines = []
		while True:
			line = readlinerev(self.file).decode('latin-1').rstrip()

			if line == "xref":
				break

		# This offset is the start of the last xref/trailer combo in the file.
		# Parsing this xref/trailer combo permits chained parsing of linked xref/trailers
		# throughout the file.
		offset = self.file.tell()
		offset += 1

		prevx = None
		prevt = None

		# Iterate until startxref in the trialer is zero, which means the end of the chain
		while offset != 0:
			# Parse xref
			x = self.ParseXref(offset)
			self.pdf.AddContentToMap(offset, x)
			offset = self.file.tell()

			# Parse trailer that follows the xref section
			t = self.ParseTrailer(offset)
			self.pdf.AddContentToMap(offset, t)

			# Cross-link these
			x.trailer = t
			t.xref = x

			# Next xref is located here (if zero then no more)
			offset = t.startxref.offset

			# If there's only one xref/trailer combo then this could lead to recursively looping if this was not checked
			if offset > 0 and offset in self.pdf.contents:
				break

			# Link this xref/trailer combo to previous combo
			x.prev = prevx
			t.prev = prevt

			# Need to set root xref section in PDF object (this means prevx has not been set yet, so it is None)
			if prevx == None:	self.pdf.rootxref = x

			# Link previous xref/trailer combo to this combo
			if prevx != None:	prevx.next = x
			if prevt != None:	prevt.next = t

			# Save to link them in next iteration
			prevx = x
			prevt = t

		# Now that all xrefs have been read, create the xref map to permit fast access
		self.pdf.MakeXRefMap()

		# Could return self.pdf but I don't see the need at this point (keep it interal)
		#return self.pdf
		pass



	def ParseHeader(self, offset):
		"""
		Parses the PDF header. If this goes bad then the file is not a PDF.
		"""

		# Jump to header
		self.file.seek(offset)

		# Expected is "%PDF-X.X\r\x...\x...\x...\x..."
		# The \x bytes are to convince FTP programs that it's binary
		# The X.X is the version, so tease that out of that nastyness

		line = self.file.readline()
		line = line.decode('latin-1')
		parts = line.split()
		if not parts[0].startswith('%PDF-'):
			raise ValueError("File does not begin with %PDF and therefore is not a PDF")

		# Split "%PDF-X.X" to ["%PDF", "X.X"]
		parts = parts[0].split('-')

		h = _pdf.Header()
		h.version = parts[1]
		return h

	def ParseXref(self, offset):
		"""
		Parses an xref section into a pdf.XRef object that represents all of the objectid to offset maps.
		"""

		# Jump to trailer
		self.file.seek(offset)

		# Iterate backward until "trailer" is found then stop
		lines = []
		while True:
			preoffset = self.file.tell()
			line = self.file.readline().decode('latin-1').rstrip()

			if line == "trailer":
				self.file.seek(preoffset)
				break

			# Append if not "trailer"
			lines.append(line)

		# Convert trailer to tokens
		toks = pdfloc.TokenizeString("\r\n".join(lines))
		toks = pdfloc.ConsolidateTokens(toks)

		# Convert tokens to python objects
		return TokenHelpers.Convert_XRef(toks)

	def ParseTrailer(self, offset):
		"""
		Parses a trailer section into a pdf.Trailer object that represents the trailer dictionary and startxref offset.
		"""

		# Jump to trailer
		self.file.seek(offset)

		# Iterate until %%EOF indicating end of trailer
		lines = []
		while True:
			line = self.file.readline().decode('latin-1').rstrip()
			# Always append %%EOF
			lines.append(line)

			if line == "%%EOF":
				break

		# Convert trailer to tokens
		toks = pdfloc.TokenizeString("\r\n".join(lines))
		toks = pdfloc.ConsolidateTokens(toks)

		# Convert tokens to python objects
		return TokenHelpers.Convert_Trailer(toks)



	def LoadObject(self, objid, generation, handler=None):
		"""
		Loads an object, regardless of cache, as a token stream if handler is not provided.
		"""

		k = (objid, generation)

		if k not in self.pdf.objmap:
			raise ValueError("Object %d (generation %d) not found in file" % (objid, generation))

		# Get offset and seek to it
		offset = self.pdf.objmap[k]
		self.file.seek(offset)

		# FIXME: I don't like this solution but it worse for now since I haven't hit objects larger than 768 kB
		# Read a block and tokenize it
		dat = self.file.read(768*1024).decode('latin-1')

		# Stop at endobj token
		# Handle streams by catching the exception, processing for the length and then recalling on second iteration of the loop
		streamlength = None
		while True:
			try:
				toks = pdfloc.TokenizeString(dat, stoptoken="endobj", streamlength=streamlength)
				break
			except pdfloc.NeedStreamLegnthError as e:
				# Have to terminate object or consolidator will complain (important that e.tokens won't be used elsewhere since it is being modified)
				t = pdfloc.plylex.LexToken()
				t.type = 'endobj'
				t.value = 'endobj'
				t.lineno = 0
				t.lexpos = 0
				e.tokens.append(t)

				# Example of e.tokens:
				# [LexToken(INT,59,1,0), LexToken(INT,0,1,3), LexToken(obj,'obj',1,5), LexToken(DICT_START,'<<',1,8), LexToken(NAME,'Length',1,10), LexToken(INT,1070,1,18), LexToken(NAME,'Filter',1,22), LexToken(NAME,'FlateDecode',1,29), LexToken(DICT_END,'>>',1,41), LexToken(endobj,'endobj',0,0)]
				#
				# Consolidated:
				# [LexToken(OBJECT,(59, 0, [LexToken(DICT,[(LexToken(NAME,'Length',1,10), LexToken(INT,1070,1,18)), (LexToken(NAME,'Filter',1,22), LexToken(NAME,'FlateDecode',1,29))],1,8)]),1,5)]
				#
				# Converted
				# [<Dictionary {'Length': 1070, 'Filter': 'FlateDecode'}>]
				#
				# So, etoks[0] is the OBJECT token and etoks[0].value[2] is the DICT token
				# and d[0] is the dictionary after converting

				# Consolidate
				etoks = pdfloc.ConsolidateTokens(e.tokens)
				d = TokenHelpers.Convert(etoks[0].value[2])
				dlen = d[0]['Length']

				# If it's an indirect then that integer needs to be loaded
				# Otherwise if it's an integer then nothing else needs to be done
				if isinstance(dlen, _pdf.IndirectObject):
					streamlength = self.LoadObject(dlen.objid, dlen.generation, self._ParseInt)
				elif type(dlen) == int:
					streamlength = dlen
				else:
					raise TypeError("Unknown type for stream length: %s" % dlen)

				# At this point, streamlength should be set and iterating around the loop will find a successful TokenizeString call

		# Consolidate tokens
		toks = pdfloc.ConsolidateTokens(toks)

		# Process the token stream into something better
		# The result should not have tokens or any similar concept (separation of layers)
		if handler != None:
			o = handler(k, toks)
		else:
			raise NotImplementedError()

		# Return processed token stream
		return o

	def GetObject(self, objid, generation, handler=None):
		"""
		Pull an object from the cache or load it if it's not loaded yet.
		Must provide a handler to convert raw object data into something meaningful.
		"""

		k = (objid, generation)

		# Check the cache first
		if k in self.pdf.contents:
			return self.pdf.contents[k]

		# Load object
		o = self.LoadObject(objid, generation, handler)

		# Store in cache
		self.pdf.contents[k] = o

		# Return object
		return o



	def FindRootObject(self):
		"""
		Iterates through xref/trailer combos until the /Root (X X R) is found indicating the root object of the document.
		"""

		x = self.pdf.rootxref
		t = x.trailer

		while x != None:
			if 'Root' in t.dictionary:
				v = t.dictionary['Root']
				# This should be an indirect
				return v

			x = x.next
			t = t.next

		return None

	def GetRootObject(self):
		"""
		Find the root (catalog) object, process it, and return it.
		"""

		ind = self.FindRootObject()
		if ind == None:
			raise ValueError("Failed to find root catalog node")

		return self.GetObject(ind.objid, ind.generation, self._ParseCatalog)

	def GetDictionary(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseDictionary)

	def GetPageTreeNode(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePageTreeNode)

	def GetPageTreeNodeOrPage(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePageTreeNodeOrPage)

	def GetPage(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePage)

	def GetNumberTreeNode(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseNumberTreeNode)

	def GetContent(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseContent)

	def GetResource(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseResource)

	def GetColorSpace(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseColorSpace)

	def GetGraphicsState(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseGraphicsState)

	def GetFont(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFont)

	def GetFontDescriptor(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFontDescriptor)

	def GetFontEncoding(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFontEncoding)

	def GetFontToUnicode(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFontToUnicode)

	def GetFontWidths(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseArray)

	def GetFontFile2(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFontFile2)

	def GetFontFile3(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseFontFile3)

	def GetXObject(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseXObject)




	def _ParseStream(self, objidgen, tokens, klass=_pdf.Content):
		d = TokenHelpers.Convert(tokens[0].value[2][0])
		s = TokenHelpers.Convert(tokens[0].value[2][1])

		r = klass()
		r.Dict = d
		r.StreamRaw = s

		return r

	def _ParseDictionary(self, objidgen, tokens):
		d = TokenHelpers.Convert(tokens[0].value[2])
		return d[0]

	def _ParseArray(self, objidgen, tokens):
		a = TokenHelpers.Convert(tokens[0].value[2])
		return a[0]

	def _ParseInt(self, objidgen, tokens):
		# Example
		# tokens =							[LexToken(OBJECT,(5, 0, [LexToken(INT,5312,1,8)]),1,4)]
		# tokens[0] =						LexToken(OBJECT,(5, 0, [LexToken(INT,5312,1,8)]),1,4)
		# tokens[0].value[2] =				[LexToken(INT,5312,1,1,8)]
		# tokens[0].value[2][0].value =		5312

		return tokens[0].value[2][0].value

	def _ParseCatalog(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.Catalog)

	def _ParsePageTreeNode(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.PageTreeNode)

	def _ParsePageTreeNodeOrPage(self, objidgen, tokens):
		return self._ParserPageTreeNodeOrPageOject(objidgen, tokens)

	def _ParsePage(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.Page)

	def _ParseNumberTreeNode(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.NumberTreeNode)

	def _ParseContent(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens)

	def _ParserPageTreeNodeOrPageOject(self, objidgen, tokens):
		"""
		PageTreeNode.Kids can be PageTreeNode or Page, so must check Type before picking klass.
		"""

		o = TokenHelpers.Convert(tokens[0].value[2])
		typ = o[0]['Type']

		if typ == 'Pages':		r = _pdf.PageTreeNode(self._DynamicLoader)
		elif typ == 'Page':		r = _pdf.Page(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s) for this function: neither Pages nor Page" % typ)

		for k in o[0]:
			setattr(r, '_' + k, o[0][k])

		return r

	def _ParseResource(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.Resource)

	def _ParseColorSpace(self, objidgen, tokens):
		"""
		Several subtypes of ColorSpace, must switch depending on Subtype
		"""

		raise NotImplementedError()
		print(tokens)
		o = TokenHelpers.Convert(tokens[0].value[2])
		print(o)
		typ = o[0]['Subtype']

		if styp == 'CalGray':	r = _pdf.ColorSpaceGray(self._DynamicLoader)
		elif styp == 'CalRGB':	r = _pdf.ColorSpaceRGB(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object subtype (%s) for this type ColorSpace" % styp)

		for k in o[0]:
			setattr(r, '_' + k, o[0][k])

		return r

	def _ParseGraphicsState(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.GraphicsState)

	def _ParseFont(self, objidgen, tokens):
		"""
		Several subtypes of Font, must switch depending on Subtype
		"""

		o = TokenHelpers.Convert(tokens[0].value[2])
		typ = o[0]['Type']
		styp = o[0]['Subtype']

		if styp == 'Type0':				r = _pdf.Font0(self._DynamicLoader)
		elif styp == 'Type1':			r = _pdf.Font1(self._DynamicLoader)
		elif styp == 'Type3':			r = _pdf.Font3(self._DynamicLoader)
		elif styp == 'TrueType':		r = _pdf.FontTrue(self._DynamicLoader)
		elif styp == 'CIDFontType0':	r = _pdf.FontCID0(self._DynamicLoader)
		elif styp == 'CIDFontType2':	r = _pdf.FontCID2(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s) for this function: neither Type1,  Type3, or TrueType" % styp)

		for k in o[0]:
			setattr(r, '_' + k, o[0][k])

		return r

	def _ParseFontDescriptor(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.FontDescriptor)

	def _ParseFontEncoding(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.FontEncoding)

	def _ParseFontToUnicode(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens, _pdf.FontToUnicode)

	def _ParseFontFile2(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens, _pdf.FontFile2)

	def _ParseFontFile3(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens, _pdf.FontFile3)


	def _ParseXObject(self, objidgen, tokens):
		"""
		Several subtypes of XObject, must switch depending on Subtype.
		"""

		d = TokenHelpers.Convert(tokens[0].value[2][0])
		s = TokenHelpers.Convert(tokens[0].value[2][1])

		if 'Type' in d:				typ = d['Type']
		else:						typ = 'XObject'
		styp = d['Subtype']

		if styp == 'Form':			r = _pdf.XObjectForm(self._DynamicLoader)
		elif styp == 'Image':		r = _pdf.XObjectImage(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s) for this function: neither Form or Image" % styp)

		for k in d:
			setattr(r, '_' + k, d[k])

		r.Dict = d
		r.StreamRaw = s

		return r



	def _StupidObjectParser(self, objidgen, tokens, klass):
		"""
		This takes an object (tokens[0]) and pulls out the data (tokens[0].value[2]) and
		sets the dictionary of data to _Dict so that the object can load objects on demand.
		"""

		o = TokenHelpers.Convert(tokens[0].value[2])

		r = klass(self._DynamicLoader)
		for k in o[0]:
			setattr(r, '_' + k, o[0][k])

		return r

	def _DynamicLoader(self, obj, key, value):
		klass = obj.__class__

		# This is never an indirect object for any object
		if key == 'Type':			return value
		if key == 'Subtype':		return value

		if klass == _pdf.Catalog:
			if key == 'Pages':
				# Catalog.Pages is a PageTreeNode
				return self.GetPageTreeNode(value)
			elif key == 'PageLabels':
				return self.GetNumberTreeNode(value)

		elif klass == _pdf.PageTreeNode:
			if key == 'Kids':
				# PageTreeNode is an array of PageTreeNode and Page
				ret = []
				for v in value.array:
					ret.append( self.GetPageTreeNodeOrPage(v) )
				return ret
			elif key == 'Count':
				return value

		elif klass == _pdf.Page:
			if key == 'Parent':
				return self.GetPageTreeNode(value)
			elif key in ('MediaBox', 'CropBox', 'BleedBox', 'TrimBox', 'ArtBox'):
				if not isinstance(value, _pdf.IndirectObject):
					return value
			elif key == 'Contents':
				if isinstance(value, _pdf.Array):
					ret = []
					for v in value.array:
						ret.append( self.GetContent(v) )
					return ret
				elif isinstance(value, _pdf.IndirectObject):
					return self.GetContent(value)
				else:
					raise TypeError("Unrecognized type for Page.Contents: %s" % type(value))
			elif key == 'Resources':
				if isinstance(value, _pdf.Dictionary):
					r = _pdf.Resource(self._DynamicLoader)
					for k in value:
						setattr(r, '_' + k, value[k])
					return r
				elif isinstance(value, _pdf.IndirectObject):
					return self.GetResource(value)

		elif klass == _pdf.NumberTreeNode:
			if key == 'Nums':
				ret = []
				for i in range(0, len(value.array), 2):
					ret.append( tuple(value.array[i:i+2]) )
				print(ret)
				raise NotImplementedError()

				return [self.GetNumberTreeNode(v) for v in value.array]


		elif klass == _pdf.Resource:
			if isinstance(value, _pdf.Dictionary) or isinstance(value, _pdf.Array):
				return value
			elif key == 'Font':
				if isinstance(value, _pdf.IndirectObject):
					return self.GetDictionary(value)

		elif klass == _pdf.Font0:
			if isinstance(value, _pdf.IndirectObject):
				if key == 'Encoding':
					return self.GetFontEncoding(value)
				elif key == 'ToUnicode':
					return self.GetFontToUnicode(value)
				else:
					pass
			else:
				if key == 'DescendantFonts':
					r = []
					for a in value.array:
						r.append( self.GetFont(a) )
					return r

				return value

		elif klass == _pdf.Font1 or klass == _pdf.FontTrue:
			# Some of these may well be indirects but otherwise just return the value
			if isinstance(value, _pdf.IndirectObject):
				if key == 'FontDescriptor':
					return self.GetFontDescriptor(value)
				elif key == 'Encoding':
					return self.GetFontEncoding(value)
				elif key == 'ToUnicode':
					return self.GetFontToUnicode(value)
				elif key == 'Widths':
					return self.GetFontWidths(value)
				else:
					pass
			else:
				return value

		elif klass == _pdf.Font3:
			if key == 'FontDescriptor':
				return self.GetFontDescriptor(value)

		elif klass in (_pdf.FontCID0, _pdf.FontCID2):
			if isinstance(value, _pdf.IndirectObject):
				if key == 'FontDescriptor':
					return self.GetFontDescriptor(value)
			else:
				return value

		elif klass == _pdf.FontDescriptor:
			if key == 'FontFile3':
				return self.GetFontFile3(value)
			elif key == 'FontFile2':
				return sefl.GetFontFile2(value)

		elif klass == _pdf.FontEncoding:
			if isinstance(value, _pdf.IndirectObject):
				pass
			else:
				return value

		elif klass == _pdf.XObjectImage:
			if isinstance(value, _pdf.IndirectObject):
				pass
			else:
				return value

		print(value)
		raise NotImplementedError("Dynamic loader for class '%s' and key '%s' not implemented" % (klass.__name__, key))


class TextTokenizer:
	"""
	Tokenizer for text streams.
	"""

	# File object, IOStream object, whatever as long as it meets basic read/seek/tell functionality
	file = None

	# PDF object (i.e., _pdf.PDF); must keep a copy so other functions can build upon it as needed
	pdf = None

	def __init__(self, file, pdf):
		if not hasattr(file, 'read'):		raise TypeError('PDF file object has no read() method')
		if not hasattr(file, 'seek'):		raise TypeError('PDF file object has no seek() method')
		if not hasattr(file, 'tell'):		raise TypeError('PDF file object has no tell() method')

		self.file = file
		self.pdf = pdf

	def TokenizeString(self, txt):
		return textloc.TokenizeString(txt)

	def TokensToText(self, tokens, page):
		ret = []

		state = {}
		state['font'] = {}

		#print('=================')
		for i in range(len(tokens)):
			tok = tokens[i]
			print(tok)

			if tok.type == 'Tf':
				f = state['font']['font'] = tok.value[0].value
				s = state['font']['size'] = tok.value[1].value
				fo = state['font']['obj'] = page.ResourcesOBJS['Font'][f]
				fd = fo.FontDescriptorOBJ

				# Pull out object stuff
				fbase = fo.BaseFont
				fchar = fo.FirstChar
				lchar = fo.LastChar
				widths = fo.Widths
				enc = fo.Encoding
				touni = fo.ToUnicode
				charset = fd.CharSetARR
				fname = fd.FontName
				ffile = fd.FontFile3

				if fo.EncodingOBJ:
					enc = fo.EncodingOBJ
				if fo.ToUnicode:
					touni = fo.ToUnicodeOBJ

				print()
				print(['Tf font', f, s, fchar, lchar, enc, touni, charset, fbase, fname, ffile])

				if touni:
					cmaploc.cmaptxt = fo.ToUnicodeOBJ.InterpretStream()

					cmapint = cmaploc.pdfcmap()
					cmaptokens = cmapint.TokenizeString(cmaptxt)
					for cmpi in range(len(cmaptokens)):
						cmptok = cmaptokens[cmpi]
						print(cmptok)

			elif tok.type == 'Tj':
				ret.append(tok.value[0].value)
			elif tok.type == 'TJ':
				subret = ""
				for v in tok.value:
					if v.type == "LIT":
						subret += v.value
					elif v.type == "INT":
						# If longer than a threshold, assume it's a space
						# TODO: use FontDescription some how
						if abs(v.value) > 150:
							subret += " "
						else:
							pass

				ret.append(subret)


		print(ret)
		print("\n".join(ret))

		return " ".join(ret)


class CMapTokenizer:
	"""
	Tokenizer for CMap programs.
	"""

	def __init__(self):
		pass

	def TokenizeString(self, txt):
		return cmaploc.TokenizeString(txt)

	def BuildMapper(self, txt):
		toks = self.TokenizeString(txt)

		# Final map data
		mapdat = {}

		codes = []

		# Handle individual character mappings
		mapon = False
		for tok in toks:
			if tok.type == 'beginbfchar':
				mapon = True
			if mapon and tok.type == 'endbfchar':
				mapon = False

				# Make map
				for i in range(0, len(codes), 2):
					mapdat[ codes[i] ] = chr(codes[i+1])

				break

			if mapon:
				if tok.type == 'CODE':
					codes.append(tok.value)

		# Handle character range mappings
		codes = []
		mapon = False
		for tok in toks:
			if tok.type == 'beginbfrange':
				mapon = True
			if mapon and tok.type == 'endbfrange':
				mapon = False

				for i in range(0, len(codes), 3):
					sindex = codes[i]
					eindex = codes[i+1]
					offset = codes[i+2]

					for k in range(codes[i], codes[i+1]+1):
						mapdat[k] = chr(offset + (k - codes[i]))

				break

			if mapon:
				if tok.type == 'CODE':
					codes.append(tok.value)
				elif tok.type == 'ARR':
					raise NotImplementedError("Not setup to handle bf range arrays")

		def mapper(c):
			if type(c) != str:
				raise TypeError("Cannot map non-string: %s" % type(c))

			cc = ord(c)
			if cc in mapdat:
				return mapdat[cc]
			else:
				raise KeyError("Cannot map character '%s' (ord %d): not found in map" % (c, cc))

		return mapper

class TokenHelpers:
	@staticmethod
	def Convert(tok):
		# Handle a native list separately from below
		if type(tok) == list:
			return [TokenHelpers.Convert(p) for p in tok]


		if tok.type in ('NAME', 'INT', 'FLOAT'):
			return tok.value
		elif tok.type == 'HEXSTRING':
			o = _pdf.Hexstring()
			o.string = tok.value
			return o
		elif tok.type == 'LIT':
			return tok.value
		elif tok.type == 'INDIRECT':
			o = _pdf.IndirectObject()
			o.objid = tok.value[0]
			o.generation = tok.value[1]
			return o
		elif tok.type == 'ARR':
			o = _pdf.Array()
			o.array = [TokenHelpers.Convert(z) for z in tok.value]
			return o
		elif tok.type == 'DICT':
			return TokenHelpers.Convert_Dictionary(tok)
		elif tok.type == 'stream':
			return tok.value
		elif tok.type == 'true':
			return True
		elif tok.type == 'false':
			return False
		elif tok.type == 'NULL':
			return None
		else:
			print(tok.value)
			raise ValueError("Unknown token type '%s'" % tok.type)

	@staticmethod
	def Convert_XRef(toks):
		x = _pdf.XRef()
		x.offsets = []

		for row in toks[0].value:
			me = _pdf.XRefMapEntry()
			me.objid = row[0]
			me.offset = row[1]
			me.generation = row[2]
			me.inuse = row[3] == 'n' # n=in use, f=free

			x.offsets.append(me)

		return x

	@staticmethod
	def Convert_Trailer(toks):
		t = _pdf.Trailer()
		t.dictionary = TokenHelpers.Convert_Dictionary(toks[0].value[0])
		t.startxref =  TokenHelpers.Convert_StartXRef(toks[0].value[1:3])

		return t

	@staticmethod
	def Convert_Dictionary(toks):
		ret = {}

		for kv in toks.value:
			k = kv[0]
			v = kv[1]

			ret[ TokenHelpers.Convert(k) ] = TokenHelpers.Convert(v)

		d = _pdf.Dictionary()
		d.dictionary = ret

		return d

	@staticmethod
	def Convert_StartXRef(toks):
		s = _pdf.StartXRef()
		s.offset = toks[1].value

		return s


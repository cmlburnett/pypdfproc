import os

from . import pdf as pdfloc

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
		if not hasattr(file, 'read'):		raise TypeError('PDF object has no read() method')
		if not hasattr(file, 'seek'):		raise TypeError('PDF object has no seek() method')
		if not hasattr(file, 'tell'):		raise TypeError('PDF object has no tell() method')

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
		o = handler(k, toks)

		# Return processed token stream
		return o

	def GetObject(self, objid, generation, handler):
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

	def GetRootObject(self):
		"""
		Find the root (catalog) object, process it, and return it.
		"""

		ind = self.FindRootObject()
		if ind == None:
			raise ValueError("Failed to find root catalog node")

		return self.GetObject(ind.objid, ind.generation, self._ParseCatalog)

	def GetPageTreeNode(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePageTreeNode)

	def GetPageTreeNodeOrPage(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePageTreeNodeOrPage)

	def GetPage(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParsePage)

	def GetContent(self, ind):
		return self.GetObject(ind.objid, ind.generation, self._ParseContent)


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

	def _ParseContent(self, objidgen, tokens):
		d = TokenHelpers.Convert(tokens[0].value[2][0])
		s = TokenHelpers.Convert(tokens[0].value[2][1])

		r = _pdf.Content()
		r.Dict = d
		r.StreamRaw = s

		return r

	def _ParserPageTreeNodeOrPageOject(self, objidgen, tokens):
		"""
		PageTreeNode.Kids can be PageTreeNode or Page, so must check Type before picking klass.
		"""

		o = TokenHelpers.Convert(tokens[0].value[2])
		typ = o[0]['Type']

		if typ == 'Pages':		r = _pdf.PageTreeNode(self._DynamicLoader)
		elif typ == 'Page':		r = _pdf.Page(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s)for this function: neither Pages nor Page" % typ)

		for k in o[0]:
			setattr(r, '_' + k, o[0][k])

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
		if key == 'Type':
			return value

		if klass == _pdf.Catalog:
			if key == 'Pages':
				# Catalog.Pages is a PageTreeNode
				return self.GetPageTreeNode(value)

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

		raise NotImplementedError("Dynamic loader for class '%s' and key '%s' not implemented" % (klass.__name__, key))

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
		else:
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


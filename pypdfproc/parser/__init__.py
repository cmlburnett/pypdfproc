import os, struct

from . import pdf as pdfloc
from . import text as textloc
from . import cmap as cmaploc
from . import cff as cffloc
from . import fontmetrics as fmloc
from .state import StateManager, State, Mat3x3, Pos

from .. import pdf as _pdf

__all__ = ['PDFTokenizer', 'TextTokenizer', 'CMapTokenizer', 'CFFTokenizer', 'ObjectStreamTokenizer', 'FontMetricsTokenizer', 'State']

# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------

def cuttokens(toks, starttok, endtok):
	start,end = None,None

	for i in range(len(toks)):
		tok = toks[i]

		if tok.type == starttok:
			start = i
		elif tok.type == endtok:
			end = i

		if start and end:
			break

	# Not found
	if start == None or end == None:
		return toks,None

	pretoks = toks[:start]
	subtoks = toks[start:end+1]
	endtoks = toks[end+1:]

	return (pretoks+endtoks,subtoks)

# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------

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
		self.file.gotoend()

		# Iterate backward until first "xref" is found, which is followed by the end trailer
		lines = []
		while True:
			l = self.file.readlinerev()
			if len(l) == 0:
				print(lines)
				raise Exception("Unable to finish reading backward to find xref: offset=%d" % self.file.tell())

			line = l.decode('latin-1').rstrip()
			lines.append(line)

			if line == "startxref":
				break

		lines.reverse()

		toks = pdfloc.TokenizeString("\r\n".join(lines))
		toks = pdfloc.ConsolidateTokens(toks)
		#print(['toks start', toks])

		if toks[0].type != 'xref_start':	raise TypeError("Expected xref_start token, got '%s' instead" % toks[0].type)
		if toks[1].type != 'INT':			raise TypeError("Expected int token, got '%s' instead" % toks[1].type)
		if toks[2].type != 'EOF':			raise TypeError("Expected EOF token, got '%s' instead" % toks[2].type)

		offset = toks[1].value

		x = None
		t = None

		prevx = None
		prevt = None

		# Iterate until startxref in the trialer is zero, which means the end of the chain
		while offset != 0:
			# Parse xref
			x = self.ParseXRef(offset)
			self.pdf.AddContentToMap(offset, x)

			if isinstance(x, _pdf.XRefStream):
				# XRef stream doesn't have a trailer associated, so skip to next ("Prev" in PDF nomenclature) xref/trailer combo
				if 'Prev' in x.Dict:
					offset = x.Dict['Prev']
				else:
					# Done
					offset = 0

			elif isinstance(x, _pdf.XRef):
				offset = self.file.tell()

				# Parse trailer that follows the xref section
				t = self.ParseTrailer(offset)
				self.pdf.AddContentToMap(offset, t)

				# Cross-link these
				x.trailer = t
				t.xref = x

				# Next xref is located here (if zero then no more)
				if 'Prev' in t.dictionary:
					offset = t.dictionary['Prev']
				else:
					offset = t.startxref.offset

			else:
				raise TypeError("Unrecognized xref object type: %s" % x)

			#print(['x', x])
			#print(['t', t])
			#print(['offset', offset])

			# Link this xref/trailer combo to previous combo
			x.prev = prevx
			if t: t.prev = prevt

			# Need to set root xref section in PDF object (this means prevx has not been set yet, so it is None)
			if prevx == None:
				self.pdf.rootxref = x

			# Link previous xref/trailer combo to this combo
			if prevx != None:	prevx.next = x
			if prevt != None:	prevt.next = t

			# Save to link them in next iteration
			prevx = x
			if t: prevt = t

			# If there's only one xref/trailer combo then this could lead to recursively looping if this was not checked
			if offset > 0 and offset in self.pdf.contents:
				break

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

	def ParseXRef(self, offset):
		"""
		Parses an xref section into a pdf.XRef object that represents all of the objectid to offset maps.
		"""

		# Jump to trailer
		self.file.seek(offset)

		# Read first line to check if it's an xref stream
		line = self.file.readline().decode('latin-1').strip()

		# Regardless, go back to start
		# 1) If it's an xref stream then _LoadObject needs to start fromt he object definition (i.e., "INT INT obj")
		# 2) If it's a plaintext xref table then that also needs to be from the given offset
		self.file.seek(offset)

		# Check if found an object definition (i.e., "INT INT obj")
		toks = pdfloc.TokenizeString(line)
		if len(toks) == 3 and toks[0].type == 'INT' and toks[1].type == 'INT' and toks[2].type == 'obj':
			objidgen = (toks[0].value, toks[1].value)

			return self.ParseXRef_stream(offset, objidgen)

		# Not an object so assume a plaintext xref section
		else:
			return self.ParseXRef_plaintext(offset)

	def ParseXRef_stream(self, offset, objidgen):
		# Move to proper offset
		self.file.seek(offset)

		# Read the xref stream object
		toks = self._LoadObject()
		toks = pdfloc.ConsolidateTokens(toks)

		# Get _pdf.XRefStream object
		return self._ParseXRefStream(objidgen, toks)

	def ParseXRef_plaintext(self, offset):
		# Move to proper offset
		self.file.seek(offset)

		# Iterate backward until "trailer" is found then stop
		lines = []
		while True:
			preoffset = self.file.tell()
			line = self.file.readline()
			if not len(line):
				raise ValueError("Reached end-of-file before xref was read")

			line = line.decode('latin-1').rstrip()
			#print(['line', line])

			if line.startswith("trailer"):
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
			line = self.file.readline()
			if not len(line):
				raise ValueError("Reached end-of-file before trailer was read")

			line = line.decode('latin-1').rstrip()
			#print(['line', line])
			lines.append(line)

			if line == "%%EOF":
				break

		# Convert trailer to tokens
		toks = pdfloc.TokenizeString("\r\n".join(lines))
		toks = pdfloc.ConsolidateTokens(toks)

		# Convert tokens to python objects
		return TokenHelpers.Convert_Trailer(toks)



	def LoadObject(self, objid, handler=None):
		"""
		Loads an object, regardless of cache, as a token stream if handler is not provided.
		"""


		# Convert to tuple
		if isinstance(objid, _pdf.IndirectObject):
			objid = (objid.objid, objid.generation)

		if objid not in self.pdf.objmap:
			raise ValueError("Object %d (generation %d) not found in file" % (objid[0], objid[1]))

		# Get offset and seek to it
		offset = self.pdf.objmap[objid]
		#print('--------- LOAD OBJECT %s (offset %s) ----------' % (objid, offset))
		if type(offset) == int:
			self.file.seek(offset)

			# All this does is read from offset until the end of the object
			toks = self._LoadObject()

			# Consolidate tokens
			toks = pdfloc.ConsolidateTokens(toks)

		elif type(offset) == tuple:
			stream_oid = offset[0]
			stream_offset = offset[1]

			# Get stream object
			so = self.GetObjectStream(stream_oid)

			toks = so.GetObjectTokens(stream_offset)
			#print(['toks', toks])

		else:
			raise TypeError("Unrecognized type of offset, expected int or tuple but got '%s'" % offset)


		# Process the token stream into something better
		# The result should not have tokens or any similar concept (separation of layers)
		if handler != None:
			o = handler(objid, toks)
		else:
			raise NotImplementedError("No handler provided for fetching object %s" % (objid,))

		# Set object ID
		if isinstance(o, _pdf.PDFBase):
			o.oid = _pdf.IndirectObject()
			o.oid.objid = objid[0]
			o.oid.generation = objid[1]

		# Return processed token stream
		return o

	def _LoadObject(self):
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
					streamlength = self.LoadObject(dlen, self._ParseInt)
				elif type(dlen) == int:
					streamlength = dlen
				else:
					raise TypeError("Unknown type for stream length: %s" % dlen)

				# At this point, streamlength should be set and iterating around the loop will find a successful TokenizeString call

		return toks

	def GetObject(self, objid, handler=None):
		"""
		Pull an object from the cache or load it if it's not loaded yet.
		Must provide a handler to convert raw object data into something meaningful.
		"""

		#print('--------- GET OBJECT %s ----------' % (objid,))

		if isinstance(objid, _pdf.IndirectObject):
			k = (objid.objid, objid.generation)

			# Check the cache first
			if k in self.pdf.contents:
				return self.pdf.contents[k]

			# Load object
			o = self.LoadObject(objid, handler)

			# Store in cache
			self.pdf.contents[k] = o

			# Return object
			return o

		else:
			raise TypeError("Expected objid type, got '%s'" % (objid,))

	def FindRootObject(self):
		"""
		Iterates through xref/trailer combos until the /Root (X X R) is found indicating the root object of the document.
		"""

		x = self.pdf.rootxref

		while x != None:
			if isinstance(x, _pdf.XRef):
				if 'Root' in x.trailer.dictionary:
					# This should be an indirect
					return x.trailer.dictionary['Root']

			elif isinstance(x, _pdf.XRefStream):
				if 'Root' in x.Dict:
					return x.Dict['Root']

			else:
				raise TypeError("Unknown xref object type: %s" % x)

		return None

	def GetRootObject(self):
		"""
		Find the root (catalog) object, process it, and return it.
		"""

		ind = self.FindRootObject()
		if ind == None:
			raise ValueError("Failed to find root catalog node")

		return self.GetObject(ind, self._ParseCatalog)

	def GetArray(self, ind):
		return self.GetObject(ind, self._ParseArray)

	def GetDictionary(self, ind):
		return self.GetObject(ind, self._ParseDictionary)

	def GetObjectStream(self, ind):
		return self.GetObject(ind, self._ParseObjectStream)

	def GetPageTreeNode(self, ind):
		return self.GetObject(ind, self._ParsePageTreeNode)

	def GetPageTreeNodeOrPage(self, ind):
		return self.GetObject(ind, self._ParsePageTreeNodeOrPage)

	def GetPage(self, ind):
		return self.GetObject(ind, self._ParsePage)

	def GetNumberTreeNode(self, ind):
		return self.GetObject(ind, self._ParseNumberTreeNode)

	def GetContent(self, ind):
		return self.GetObject(ind, self._ParseContent)

	def GetContentOrArray(self, ind):
		return self.GetObject(ind, self._ParseContentOrArray)

	def GetResource(self, ind):
		return self.GetObject(ind, self._ParseResource)

	def GetColorSpace(self, ind):
		return self.GetObject(ind, self._ParseColorSpace)

	def GetGraphicsState(self, ind):
		return self.GetObject(ind, self._ParseGraphicsState)

	def GetFont(self, ind):
		return self.GetObject(ind, self._ParseFont)

	def GetFontDescriptor(self, ind):
		return self.GetObject(ind, self._ParseFontDescriptor)

	def GetFontEncoding(self, ind):
		return self.GetObject(ind, self._ParseFontEncoding)

	def GetFontToUnicode(self, ind):
		return self.GetObject(ind, self._ParseFontToUnicode)

	def GetFontWidths(self, ind):
		return self.GetObject(ind, self._ParseArray)

	def GetFontFile2(self, ind):
		return self.GetObject(ind, self._ParseFontFile2)

	def GetFontFile3(self, ind):
		return self.GetObject(ind, self._ParseFontFile3)

	def GetXObject(self, ind):
		return self.GetObject(ind, self._ParseXObject)




	def _ParseXRefStream(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens, _pdf.XRefStream)

	def _ParseObjectStream(self, objidgen, tokens):
		o = self._ParseStream(objidgen, tokens, _pdf.ObjectStream)

		# Initialize tokenizer for the object stream so that PDF.GetObject can pry into the stream on-demand
		o._Processor = ObjectStreamTokenizer(o)

		return o

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
		if tokens[0].type == 'ARR':
			return tokens[0]
		elif tokens[0].type == 'OBJECT':
			return TokenHelpers.Convert(tokens[0].value[2][0])
		else:
			raise TypeError("Unrecognized type for array parsing: '%s'" % tokens[0])

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
		return self._ParsePageTreeNodeOrPageOject(objidgen, tokens)

	def _ParsePage(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.Page)

	def _ParseNumberTreeNode(self, objidgen, tokens):
		return self._StupidObjectParser(objidgen, tokens, _pdf.NumberTreeNode)

	def _ParseContent(self, objidgen, tokens):
		return self._ParseStream(objidgen, tokens)

	def _ParseContentOrArray(self, objidgen, tokens):

		if tokens[0].value[2][0].type == 'ARR':
			return self._ParseArray(objidgen, tokens)
		else:
			return self._ParseContent(objidgen, tokens)

	def _ParsePageTreeNodeOrPageOject(self, objidgen, tokens):
		"""
		PageTreeNode.Kids can be PageTreeNode or Page, so must check Type before picking klass.
		"""

		if tokens[0].type == 'OBJECT':
			o = TokenHelpers.Convert(tokens[0].value[2][0])
		elif tokens[0].type == 'DICT':
			o = TokenHelpers.Convert(tokens[0])
		else:
			raise TypeError("Unrecognized type for stupid object parser; need dictionary got: '%s'" % tokens[0].type)

		typ = o['Type']

		if typ == 'Pages':		r = _pdf.PageTreeNode(self._DynamicLoader)
		elif typ == 'Page':		r = _pdf.Page(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s) for this function: neither Pages nor Page" % typ)

		for k in o:
			setattr(r, '_' + k, o[k])

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

		if tokens[0].type == 'OBJECT':
			o = TokenHelpers.Convert(tokens[0].value[2][0])
		elif tokens[0].type == 'DICT':
			o = TokenHelpers.Convert(tokens[0])
		else:
			raise TypeError("Unrecognized type for stupid object parser; need dictionary got: '%s'" % tokens[0].type)

		typ = o['Type']
		styp = o['Subtype']

		if styp == 'Type0':				r = _pdf.Font0(self._DynamicLoader)
		elif styp == 'Type1':			r = _pdf.Font1(self._DynamicLoader)
		elif styp == 'Type3':			r = _pdf.Font3(self._DynamicLoader)
		elif styp == 'TrueType':		r = _pdf.FontTrue(self._DynamicLoader)
		elif styp == 'CIDFontType0':	r = _pdf.FontCID0(self._DynamicLoader)
		elif styp == 'CIDFontType2':	r = _pdf.FontCID2(self._DynamicLoader)
		else:
			raise ValueError("Unrecognized object type (%s) for this function: neither Type1,  Type3, or TrueType" % styp)

		for k in o:
			setattr(r, '_' + k, o[k])

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

		if tokens[0].type == 'OBJECT':
			o = TokenHelpers.Convert(tokens[0].value[2][0])
		elif tokens[0].type == 'DICT':
			o = TokenHelpers.Convert(tokens[0])
		else:
			raise TypeError("Unrecognized type for stupid object parser; need dictionary got: '%s'" % tokens[0].type)

		r = klass(self._DynamicLoader)
		for k in o:
			setattr(r, '_' + k, o[k])

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
					return self.GetContentOrArray(value)
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
			elif isinstance(value, _pdf.IndirectObject):
				return self.GetDictionary(value)

		elif klass == _pdf.Font0:
			if isinstance(value, _pdf.IndirectObject):
				if key == 'Encoding':
					return self.GetFontEncoding(value)
				elif key == 'ToUnicode':
					return self.GetFontToUnicode(value)
				elif key == 'DescendantFonts':
					arr = self.GetArray(value)
					r = []
					for a in arr:
						r.append( self.GetFont(a) )
					return r

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
				elif key == 'W':
					return self.GetArray(value)
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

		elif klass == _pdf.GraphicsState:
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

		# Final map data and range data (keys are ranges; value is starting unicode value)
		mapdat = {}
		rangedat = {}

		codes = []

		# Handle individual character mappings
		mapon = False
		for tok in toks:
			if tok.type == 'beginbfchar':
				mapon = True
				continue
			if mapon and tok.type == 'endbfchar':
				mapon = False

				# Make map
				for i in range(0, len(codes), 2):
					mapdat[ codes[i] ] = chr(codes[i+1])

				break

			if mapon:
				if tok.type == 'CODE':
					codes.append(tok.value)
				else:
					raise NotImplementedError("Unrecognized token: '%s'" % str(tok))

		# Handle character range mappings
		codes = []
		mapon = False
		for tok in toks:
			if tok.type == 'beginbfrange':
				mapon = True
				continue
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
				else:
					raise NotImplementedError("Unrecognized token: '%s'" % str(tok))

		# Handle cid range mappings
		ranges = []
		mapon = False
		for tok in toks:
			if tok.type == 'begincidrange':
				mapon = True
				continue
			if mapon and tok.type == 'endcidrange':
				mapon = False

				for r in ranges:
					rangedat[ (r[0],r[1]) ] = r[2]

				break

			if mapon:
				if tok.type == 'CODE':
					ranges.append(tok.value)
				elif tok.type == 'INT':
					e = ranges.pop()
					s = ranges.pop()
					ranges.append( (s,e, tok.value) )
				else:
					raise NotImplementedError("Unrecognized token: '%s'" % str(tok))

		def mapper(c):
			if type(c) == int:
				cc = c
			elif type(c) == str:
				cc = ord(c)
			else:
				raise TypeError("Cannot map non-string: %s" % type(c))

			if cc in mapdat:
				return mapdat[cc]

			for r,unistart in rangedat.items():
				s,e = r
				if cc >= s and cc <= e:
					# Find offset of code (@cc) from range start (@s), which is then added to the unicode starting value (@unistart)
					diff = cc-s
					return chr(unistart + diff)

			raise KeyError("Cannot map character '%s' (ord %d): not found in map" % (c, cc))

		return mapper

class CFFTokenizer:
	def __init__(self, txt):
		self.txt = txt

	def Parse(self):
		self.tzdat = cffloc.TokenizeString(self.txt)

	def DumpBinary(self):
		self.tzdat['unpacker'].DumpBinary()

	# --------------------------------------------------------------------------------
	# Derivatives of parsing

	def get_version(self):
		return (self.tzdat['Header']['major'], self.tzdat['Header']['minor'])
	version = property(get_version)

class ObjectStreamTokenizer:
	N = None
	First = None
	ObjectStream = None
	Tokens = None
	Objects = None

	def __init__(self, obj):
		self.ObjectStream = obj
		self.N = obj.Dict['N']
		self.First = obj.Dict['First']
		self.Tokens = None # Delay processing until needed
		self.Objects = None

	def Process(self):
		# Delay processing until needed
		if self.Tokens != None:
			return self.Tokens

		self.Tokens = pdfloc.TokenizeString(self.ObjectStream.Stream)

		# Objects keyed by offset
		self.Objects = {}

		# Index objects by their offset in the stream
		# 1) Pull out the integers that comprise the index of this object stream
		indexes = self.Tokens[0:(self.N*2)]
		# 2) Chunk the list of integers into pairs (first is object number; second is offset from self.First)
		indexes = [ (indexes[i].value,indexes[i+1].value) for i in range(0,len(indexes),2) ]
		# 3) Add a last placeholder with the full-length of the stream so that step (4) works correctly without running passed the end
		indexes.append( (None, len(self.ObjectStream.Stream)) )
		# 4) Basically remake list from (2) and include the ending offset for each object resulting in a list of (object id, (start offset, end offset))
		indexes = [(indexes[i][0], (indexes[i][1],indexes[i+1][1]-1)) for i in range(len(indexes)-1)]

		for i in range(len(indexes)):
			idx = indexes[i]

			# Unpack the structure created in (4) above
			oid, (startidx,endidx) = idx

			# Need to account for offset in which the object data begins (this is after the integer index plus whatever padding the creating app put in between)
			startidx += self.First
			endidx += self.First

			# Iterate through entire token range to pull out the tokens whose lexer position is between the start and end indices
			# NB: this is not all that efficient since the entire token list is iterated through for every object in the stream, however, functioning first and optimize later
			toks = [ self.Tokens[_] for _ in range(len(self.Tokens)) if (self.Tokens[_].lexpos >= startidx and self.Tokens[_].lexpos <= endidx) ]

			# Map array index to tuple of (object id, tokens)
			# NB: object type is unknown at this point so no appropriate handler can/should be called,
			# and since LoadObject is up the stack which does contain the appropriate handler then defer processing of tokens until that point
			self.Objects[i] = (oid, pdfloc.ConsolidateTokens(toks))

			#print([off, (startidx, endidx), toks, self.Objects[off]])
			#print([off, (startidx, endidx), self.Objects[off]])

	def GetObjectTokens(self, index):
		if self.Objects == None:
			self.Process()

		# Returns the tokens corresponding to this object
		# NB: the object id in [0] is ignored since the XRefRowCompressed has the object id that led to parsing the object stream
		return self.Objects[index][1]

class FontMetricsTokenizer:
	def __init__(self, txt):
		self.txt = txt

		self.Comments = []

	def Parse(self):
		tokens = fmloc.TokenizeString(self.txt)

		tokens,charmetrics = cuttokens(tokens, 'StartCharMetrics', 'EndCharMetrics')
		tokens,kerndata = cuttokens(tokens, 'StartKernData', 'EndKernData')

		if kerndata != None:
			kerndata,kernpairs = cuttokens(kerndata, 'StartKernPairs', 'EndKernPairs')
		else:
			kernpairs = None


		# Could do this, or block the for loop below under an if statement....
		if kernpairs == None:
			kernpairs = []

		ret = {}
		ret['Comments'] = []
		ret['CharMetrics'] = {}
		ret['Ligatures'] = []
		ret['Kerning'] = {}
		ret['Kerning']['Pairs'] = {}

		# Everything leftover
		for tok in tokens:
			if tok.type == 'StartFontMetrics':		ret['FMVersion'] = tok.value
			elif tok.type == 'EndFontMetrics':		pass

			elif tok.type == 'Ascender':			ret['Ascender'] = tok.value
			elif tok.type == 'CapHeight':			ret['CapHeight'] = tok.value
			elif tok.type == 'COMMENT':				ret['Comments'].append(tok.value)
			elif tok.type == 'CharacterSet':		ret['CharacterSet'] = tok.value
			elif tok.type == 'Descender':			ret['Descender'] = tok.value
			elif tok.type == 'EncodingScheme':		ret['EncodingScheme'] = tok.value
			elif tok.type == 'FontBBox':			ret['FontBBox'] = tok.value
			elif tok.type == 'FontName':			ret['FontName'] = tok.value
			elif tok.type == 'FullName':			ret['FullName'] = tok.value
			elif tok.type == 'FamilyName':			ret['FamilyName'] = tok.value
			elif tok.type == 'IsFixedPitch':		ret['IsFixedPitch'] = tok.value
			elif tok.type == 'ItalicAngle':			ret['ItalicAngle'] = tok.value
			elif tok.type == 'Notice':				ret['Notice'] = tok.value
			elif tok.type == 'StdHW':				ret['StdHW'] = tok.value
			elif tok.type == 'StdVW':				ret['StdVW'] = tok.value
			elif tok.type == 'UnderlinePosition':	ret['UnderlinePosition'] = tok.value
			elif tok.type == 'UnderlineThickness':	ret['UnderlineThickness'] = tok.value
			elif tok.type == 'Version':				ret['Version'] = tok.value
			elif tok.type == 'Weight':				ret['Weight'] = tok.value
			elif tok.type == 'XHeight':				ret['XHeight'] = tok.value
			else:
				raise TypeError("Unrecognized token: '%s'" % tok)

		lastchar = None
		curchar = {}
		for tok in charmetrics:
			if tok.type == 'StartCharMetrics':		pass
			elif tok.type == 'EndCharMetrics':		pass
			elif tok.type == 'SemiColon':			pass

			elif tok.type == 'C':
				if len(curchar):
					ret['CharMetrics'][curchar['N']] = curchar
					lastchar = curchar
					curchar = {}

				curchar['C'] = tok.value
			elif tok.type == 'WX':					curchar['W'] = (tok.value, 0)
			elif tok.type == 'N':					curchar['N'] = tok.value
			elif tok.type == 'B':					curchar['B'] = tok.value
			elif tok.type == 'L':
				l = {}
				l['base'] = lastchar
				l['successor'] = tok.value[0]
				l['ligature'] = tok.value[1]
				ret['Ligatures'].append(l)

			else:
				raise TypeError("Unrecognized token: '%s'" % tok)

		for tok in kernpairs:
			if tok.type == 'StartKernPairs':		pass
			elif tok.type == 'EndKernPairs':		pass

			elif tok.type == 'KPX':
				ret['Kerning']['Pairs'][tok.value[0]] =		(tok.value[1], 0)
			else:
				raise TypeError("Unrecognized token: '%s'" % tok)

		return ret


class TokenHelpers:
	@staticmethod
	def Convert(tok):
		# Handle a native list separately from below
		if type(tok) == list:
			return [TokenHelpers.Convert(p) for p in tok]


		#print(['tok', tok])
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
			if row[3] == 'n':
				me = _pdf.XRefRowUsed(objid=row[0], offset=row[1], generation=row[2])
			else:
				me = _pdf.XRefRowFree(objid=row[0], generation=row[2])

			x.offsets.append(me)

		return x

	@staticmethod
	def Convert_Trailer(toks):
		#print(['toks', toks])
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


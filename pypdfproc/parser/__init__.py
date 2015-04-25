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

	def FindRootObject(self):
		x = self.pdf.rootxref
		t = x.trailer

		while x != None:
			print([x,t])

			if 'Root' in t.dictionary:
				v = t.dictionary['Root']
				print(v)

			x = x.next
			t = t.next

	def LoadObject(self, objid, generation):
		k = (objid, generation)

		if k not in self.pdf.objmap:
			raise ValueError("Object %d (generation %d) not found in file" % (objid, generation))

		raise NotImplemented()

class TokenHelpers:
	@staticmethod
	def Convert(tok):
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


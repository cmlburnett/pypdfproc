"""
PDF classes that represent Carousel object information but in python form.
No references to underlying parsing is made.
"""

import zlib

class PDF:
	"""
	Primary class that represents a PDF file.
	"""

	# Object map permits direct access to reading objects in the file
	# Keyed by (objid, generation) tuples and value is integer offset within the file
	objmap = None
	# Contents of the file, indexed by offset within file with the value being one
	# of the classes contained within this file
	contents = None

	# Root xref in the file
	rootxref = None

	def __init__(self):
		self.objmap = {}
		self.contents = {}
		self.objcache = {}
		self.rootxref = None

	def MakeOrderedContents(self):
		"""
		Take the dictionary self.contents and return an ordered set of contents objects
		based on offset order. This is never cached since other objects may be loaded.
		"""

		ret = []

		keys = list(self.contents.keys())
		keys.sort()
		for key in keys:
			ret.append(self.contents[key])

		return ret

	def AddContentToMap(self, offset, o):
		self.contents[offset] = o

	def MakeXRefMap(self):
		"""
		Makes the xref map that is self.objmap.
		Keys the self.objmap by (objid, generation) tuples with value of the integer offset within the file.
		
		This follows the xref/trailer chain throughout the file and keeps the "newest" version of each object,
		meaning that this correctly handles incremental updates to objects.
		"""

		# Reset map
		self.objmap = {}

		# Pull out first xref/trailer combo
		x = self.rootxref
		t = x.trailer

		# Iterate until no more xref/trailer combos
		while x != None:
			# Iterate through offsets in xref and make map to objects
			for me in x.offsets:
				# Ignore if object is marked free
				if not me.inuse:
					continue

				# Key to index offset by
				p = (me.objid, me.generation)
				if p in self.objmap:
					# Already exists which means the me.offset is the old object and self.objmap[p] is the newer object
					pass
				else:
					# Object not mapped yet so map it to the offset
					self.objmap[p] = me.offset

			# Jump to next xref/trailer combo (last one will set x to None and stop iteration)
			x = x.next
			t = t.next


class PDFBase:
	# Nothing yet
	pass

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Data types

class Hexstring(PDFBase):
	string = None

class Dictionary(PDFBase):
	dictionary = None

	def __contains__(self, k):		return k in self.dictionary
	def __getitem__(self, k):		return self.dictionary[k]
	def __setitem__(self, k,v):		self.dictionary[k] = v

	def __iter__(self):				return iter(self.dictionary)

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s %s>" % (self.__class__.__name__, str(self.dictionary))

class Array(PDFBase):
	array = None

	def __len__(self):				return len(self.array)
	def __getitem__(self, k):		return self.array[k]
	def __setitem__(self, k,v):		self.array[k] = v

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s %s>" % (self.__class__.__name__, str(self.array))

class IndirectObject(PDFBase):
	objid = None
	generation = None

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s (%d %d R)>" % (self.__class__.__name__, self.objid, self.generation)

class XRefMapEntry(PDFBase):
	objid = None
	offset = None
	generation = None
	inuse = None

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s (%d %d) -> %d inuse=%b>" % (self.__class__.__name__, self.objid, self.generation, self.offset, self.inuse)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# PDF parts

class Header(PDFBase):
	version = None

class Trailer(PDFBase):
	dictionary = None
	xref = None
	startxref = None

	prev = None
	next = None

	def __repr__(self):				return str(self)
	def __str__(self):
		if self.prev == None:		prevtrail = "None"
		else:						prevtrail = "%x" % id(self.prev)

		if self.next == None:		nexttrail = "None"
		else:						nexttrail = "%x" % id(self.next)

		return "<%s %x prev=%s next=%s xref=%x startxref=%d %s>" % (self.__class__.__name__, id(self), prevtrail, nexttrail, id(self.xref), self.startxref.offset, str(self.dictionary))

class StartXRef(PDFBase):
	offset = None

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s %d>" % (self.__class__.__name__, self.offset)

class XRef(PDFBase):
	offsets = None
	trailer = None

	prev = None
	next = None

	def __repr__(self):				return str(self)
	def __str__(self):
		if self.prev == None:		prevxref = "None"
		else:						prevxref = "%x" % id(self.prev)

		if self.next == None:		nextxref = "None"
		else:						nextxref = "%x" % id(self.next)

		minobjid = min([me.objid for me in self.offsets])
		maxobjid = max([me.objid for me in self.offsets])

		return "<%s %x prev=%s next=%s trailer=%x objid=%d..%d>" % (self.__class__.__name__, id(self), prevxref, nextxref, id(self.trailer), minobjid, maxobjid)

class Object(PDFBase):
	objid = None
	generation = None

class EOF(PDFBase):
	pass

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Higher-order PDF parts

class PDFHigherBase(PDFBase):
	_Loader = None

	def __init__(self, loader):
		PDFBase.__init__(self)

		self._Loader = loader

	def __getattr__(self, k):
		# Possibilities:
		# 1) k is a valid property name and loaded
		# 2) k is a valid property name and is not loaded and is None
		# 3) k is a valid property name and is not loaded and is not None
		# 4) k is a valid property name and was not provided in the file
		# 5) k is not a valid property name

		kk = '_' + k

		# Handle (5)
		kval = self.__class__.__dict__[kk]

		# Handle (1-3)
		if kk in self.__dict__:
			# Handle (2)
			if self.__dict__[kk] == None:
				self.__dict__[k] = None
			else:
				# Handle (3)
				if k not in self.__dict__:
					v = self._Loader(self, k, self.__dict__[kk])
					self.__dict__[k] = v

			# Handled (2-3) and also (1) require falling through

		# Handles (4)
		else:
			# Assumes klass default value
			self.__dict__[k] = kval

		# Handle (1)
		return self.__dict__[k]

	def _Load(self, key, rawvalue):
		raise NotImplementedError("Class %s does not implement _Load function to dynamically load properties" % self.__class__.__name__)

	def getsetprops(self):
		ret = {}

		for k in self.__dict__:
			if k in self.__class__.__dict__:
				ret[k] = self.__dict__[k]

		return ret

class PDFStreamBase(PDFBase):
	Dict = None
	StreamRaw = None

	def __getattr__(self, k):
		if k == 'Stream':
			if 'Filter' in self.Dict:
				if self.Dict['Filter'] == 'FlateDecode':
					s = zlib.decompress(bytes(self.StreamRaw, 'latin-1'))
					self.__dict__['Stream'] = s.decode('latin-1')
				else:
					raise ValueError("Unknown filter for content stream: %s" % self.Dict['Filter'])

			else:
				# No filtering
				self.__dict__['Stream'] = self.StreamRaw

			return self.__dict__['Stream']
		else:
			return self.__dict__[k]

# ------------------------------------------------------------------------------

class Catalog(PDFHigherBase):
	# Table 3.25 (pg 139-142) of 1.7 spec
	_Type = None
	_Version = None
	_Pages = None
	_PageLabels = None
	_Names = None
	_Dests = None
	_ViewerPreferences = None
	_PageLayout = None
	_PageMode = None
	_Outlines = None
	_Threads = None
	_OpenAction = None
	_AA = None
	_URI = None
	_AcroForm = None
	_Metadata = None
	_StructTreeRoot = None
	_MarkInfo = None
	_Lang = None
	_SpiderInfo = None
	_OutputIntents = None
	_PieceInfo = None
	_OCProperties = None
	_Perms = None
	_Legal = None
	_Requirements = None
	_Collection = None
	_NeedsRendering = None

class PageTreeNode(PDFHigherBase):
	# Table 3.26 (pg 143) of 1.7 spec
	_Type = None
	_Parent = None
	_Kids = None
	_Count = None

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s parent=%s count=%d kids=%s>" % (self.__class__.__name__, self.Parent, self.Count, [id(k) for k in self.Kids])

	def DFSPages(self):
		"""
		Do a depth-first search for Page objects.
		This returns all Page leaf nodes in the order that they should be displayed.
		"""

		ret = []

		for k in self.Kids:
			if k.Type == 'Page':
				ret.append(k)
			elif k.Type == 'Pages':
				ret = ret + k.DFSPages()
			else:
				raise TypeError("Unrecognized kid type (%s) of PageTreeNode: expected Page or Pages" % k.Type)

		return ret

class Page(PDFHigherBase):
	# Table 3.27 (pg 145-8) of 1.7 spec
	_Type = None
	_Parent = None
	_LasModified = None
	_Resources = None
	_MediaBox = None
	_CropBox = None
	_BleedBox = None
	_TrimBox = None
	_ArtBox = None
	_BoxColorInfo = None
	_Contents = None
	_Rotate = None
	_Group = None
	_Thumb = None
	_B = None
	_Dur = None
	_Trans = None
	_Annots = None
	_AA = None
	_Metadata = None
	_PieceInfo = None
	_StructParents = None
	_ID = None
	_PZ = None
	_SeparationInfo = None
	_Tabs = None
	_TemplateInstantiated = None
	_PresSteps = None
	_UserUnit = None
	_VP = None

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s %x parent=%x>" % (self.__class__.__name__, id(self), id(self.Parent))

class NumberTreeNode(PDFHigherBase):
	# Table 3.34 (pg 166) of 1.7 spec
	_Type = None
	_Kids = None
	_Nums = None
	_Limits = None

	def DFSPageLabels(self):
		"""
		Do a depth-first search for NumberTreeNode objects.
		This returns all NumberTreeNode leaf nodes in the order that they should be displayed.
		"""

		ret = []

		if self.Kids:
			for k in self.Kids:
				ret = ret + self.DFSPages(k)
		else:
			return self.Nums

		return ret

class Content(PDFStreamBase):
	pass

class Resource(PDFHigherBase):
	# Table 3.30 (pg 154) of 1.7 spec
	_ExtGState = None
	_ColorSpace = None
	_Pattern = None
	_Shading = None
	_XObject = None
	_Font = None
	_ProcSet = None
	_Properties = None

class ColorSpaceGray(PDFHigherBase):
	# Table 4.13 (pg 246) of 1.7 spec
	_Type = None
	_Subtype = None
	_WhitePoint = None
	_BlackPoint = None
	_Gamma = None

class ColorSpaceRGB(PDFHigherBase):
	# Table 4.14 (pg 248) of 1.7 spec
	_Type = None
	_Subtype = None
	_WhitePoint = None
	_BlackPoint = None
	_Gamma = None
	_Matrix = None

class ColorSpaceLab(PDFHigherBase):
	# Table 4.13 (pg 246) of 1.7 spec
	_Type = None
	_Subtype = None
	_WhitePoint = None
	_BlackPoint = None
	_Range = None

class ColorSpaceICC(PDFHigherBase):
	# Table 4.16 (pg 253) of 1.7 spec
	_Type = None
	_Subtype = None
	_N = None
	_Alternate = None
	_Range = None
	_Metadata = None

class ColorSpaceDeviceN(PDFHigherBase):
	# Table 4.21 (pg 272) of 1.7 spec
	_Type = None
	_Colorants = None
	_Process = None
	_MixingHints = None

class GraphicsState(PDFHigherBase):
	# Table 4.8 (pg 220-3) of 1.7 spec
	_Type = None
	_LW = None
	_LC = None
	_LJ = None
	_ML = None
	_D = None
	_RI = None
	_OP = None
	_op = None
	_OPM = None
	_Font = None
	_BG = None
	_BG2 = None
	_UCR = None
	_UCR2 = None
	_TR = None
	_TR2 = None
	_HT = None
	_FL = None
	_SM = None
	_SA = None
	_BM = None
	_SMask = None
	_CA = None
	_ca = None
	_AIS = None
	_TK = None

class Font1(PDFHigherBase):
	# Table 5.8 (pg 413-5) of 1.7 spec
	_Type = None
	_Subtype = None
	_Name = None
	_BaseFont = None
	_FirstChar = None
	_LastChar = None
	_Widths = None
	_FontDescriptor = None
	_Encoding = None
	_ToUnicode = None

class Font3(PDFHigherBase):
	# Table 5.9 (page 420-1) of 1.7 spec
	_Type = None
	_Subtype = None
	_Name = None
	_FontBBox = None
	_FontMatrix = None
	_CharProcs = None
	_Encoding = None
	_FirstChar = None
	_LastChar = None
	_Widths = None
	_FontDescriptor = None
	_Resources = None
	_ToUnicode = None

class FontTrue(Font1):
	# Same as Font1 with interpretive differences (5.5.2, pg 418)
	_Type = None
	_Subtype = None
	_Name = None
	_BaseFont = None
	_FirstChar = None
	_LastChar = None
	_Widths = None
	_FontDescriptor = None
	_Encoding = None
	_ToUnicode = None

class FontDescriptor(PDFHigherBase):
	# Table 5.19 (pg 456-8) of 1.7 spec
	_Type = None
	_FontName = None
	_FontFamily = None
	_FontStretch = None
	_FontWeight = None
	_Flags = None
	_FontBBox = None
	_ItalicAngle = None
	_Ascent = None
	_Descent = None
	_Leading = None
	_CapHeight = None
	_XHeight = None
	_StemV = None
	_StemH = None
	_AvgWidth = None
	_MaxWidth = None
	_MissingWidth = None
	_FontFile = None
	_FontFile2 = None
	_FontFile3 = None
	_CharSet = None

class FontEncoding(PDFHigherBase):
	# Table 5.11 (pg 427) of 1.7 spec
	_Type = None
	_BaseEncoding = None
	_Differences = None

class FontToUnicode(PDFStreamBase):
	pass

class XObject(PDFHigherBase):
	# Table ???
	_Type = None
	_Subtype = None


class XObjectForm(PDFHigherBase):
	# Table 4.45 (pg 358-60) of 1.7 spec
	_Type = None
	_Subtype = None
	_FormType = None
	_BBox = None
	_Matrix = None
	_Resources = None
	_Group = None
	_Ref = None
	_Metadata = None
	_PieceInfo = None
	_LastModified = None
	_StructParent = None
	_StructParents = None
	_OPI = None
	_OC = None
	_Name = None

class XObjectImage(PDFHigherBase):
	# Table 4.39 (pg 340-3) of 1.7 spec
	_Type = None
	_Subtype = None
	_Width = None
	_Height = None
	_ColorSpace = None
	_BitsPerComponent = None
	_Intent = None
	_ImageMask = None
	_Mask = None
	_Decode = None
	_Interpolate = None
	_Alternates = None
	_SMask = None
	_SMaskInData = None
	_Name = None
	_SructParent = None
	_ID = None
	_OPI = None
	_Metadata = None
	_OC = None


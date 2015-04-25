"""
PDF classes that represent Carousel object information but in python form.
No references to underlying parsing is made.
"""

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

	# Cache of objects to avoid having to repeatedly read them
	# Indexed by (objid, generation) tuples and value is one of the classes contained within this file
	objcache = None

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

	def __repr__(self):				return str(self)
	def __str__(self):				return "<%s [%s]>" % (self.__class__.__name__, str(self.array))

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
		# If not loaded, then load it
		if k not in self.__dict__:
			kk = '_' + k

			# No data provided to use to load it, so return None
			if self.__dict__[kk] == None:
				return None
			else:
				v = self._Loader(self, k, self.__dict__[kk])
				self.__dict__[k] = v

		return self.__dict__[k]

	def _Load(self, key, rawvalue):
		raise NotImplementedError("Class %s does not implement _Load function to dynamically load properties" % self.__class__.__name__)

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


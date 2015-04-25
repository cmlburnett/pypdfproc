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

class Root(PDFBase):
	# Table 3.25 (pg 139-142) of 1.7 spec
	Type = None
	Version = None
	Pages = None
	PageLabels = None
	Names = None
	Dests = None
	ViewerPreferences = None
	PageLayout = None
	PageMode = None
	Outlines = None
	Threads = None
	OpenAction = None
	AA = None
	URI = None
	AcroForm = None
	Metadata = None
	StructTreeRoot = None
	MarkInfo = None
	Lang = None
	SpiderInfo = None
	OutputIntents = None
	PieceInfo = None
	OCProperties = None
	Perms = None
	Legal = None
	Requirements = None
	Collection = None
	NeedsRendering = None

class PageTreeNode(PDFBase):
	# Table 3.26 (pg 143) of 1.7 spec
	Type = None
	Parent = None
	Kids = None
	Count = None


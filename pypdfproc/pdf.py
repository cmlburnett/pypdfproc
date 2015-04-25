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

	def __init__(self):
		self.objmap = {}
		self.contents = {}
		self.objcache = {}

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

		# Get ordered set to start with end xref/trailer combo
		oc = self.MakeOrderedContents()

		# Must start with last xref/trailer combo
		if not isinstance(oc[-2], XRef):
			raise ValueError("Expected second-to-last object in contents to be a XRef, got %s instead" % oc[-2].__class__.__name__)
		if not isinstance(oc[-1], Trailer):
			raise ValueError("Expected last object in contents to be a Trailer, got %s instead" % oc[-1].__class__.__name__)

		# Pull out first xref/trailer combo
		x = oc[-2]
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

class Array(PDFBase):
	array = None

class IndirectObject(PDFBase):
	objid = None
	generation = None

class XRefMapEntry(PDFBase):
	objid = None
	offset = None
	generation = None
	inuse = None

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# PDF parts

class Header(PDFBase):
	version = None

class Trailer(PDFBase):
	dictionary = None
	startxref = None

	prev = None
	next = None

class StartXRef(PDFBase):
	offset = None

class XRef(PDFBase):
	offsets = None
	trailer = None

	prev = None
	next = None

class Object(PDFBase):
	objid = None
	generation = None

class EOF(PDFBase):
	pass


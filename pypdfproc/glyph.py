"""
Represents a glyph and its character ID, width, and unicode value.
No font information is included.
"""

class Glyph:
	def __init__(self, cid):
		self.cid = cid
		self.unicode = None
		self.width = 0

	def __repr__(self):
		return str(self)
	def __str__(self):
		return "<Glyph cid=%d unicode='%s' width=%d>" % (self.cid, self.unicode, self.width or 0)

	def get_cid(self):				return self._cid
	def set_cid(self,v):			self._cid = v
	cid = property(get_cid, set_cid, doc="Character ID")

	def get_unicode(self):			return self._uni
	def set_unicode(self,v):		self._uni = v
	uni = property(get_unicode, set_unicode, doc="Glyph unicode")

	def get_width(self):			return self._width
	def set_width(self,v):			self._width = float(v)
	width = property(get_width, set_width, doc="Glyph width")


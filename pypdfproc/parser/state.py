"""
Keeps track of state during rendering of the PDF page contents.
"""

import copy

class StateManager:
	"""
	Manager of state information.
	"""

	stack = None

	def __init__(self):
		self.stack = []

		self.stack.append( State() )

	def Pop(self):
		if len(self.stack) == 0:
			raise ValueError("Cannot pop an empty stack")
		elif len(self.stack) == 1:
			raise ValueError("Cannot pop initial values of the stack")

		else:
			self.stack.pop()

	def Push(self):
		if len(self.stack) == 0:
			raise ValueError("Cannot push an empty stack")

		sc = self.S.Copy()
		self.stack.append(sc)

	@property
	def S(self):
		return self.stack[-1]

class State:
	"""
	State information for processing.
	"""

	# Position of a start of graphics operations
	startpos = None
	# Current position
	pos = None

	graphics = None

	def __init__(self):
		# Current cursor position
		self.startpos = None
		self.pos = None

		# Graphics commands
		self.graphics = []


	# Save and restore state

	def Copy(self):
		return copy.deepcopy(self)


	# Graphics

	def do_re(self, x,y, w,h):
		if self.startpos == None:
			self.startpos = Pos(x,y)

		# Equivalent per 1.7 spec (page 227)
		self.do_m(x,y)
		self.do_l(x+w, y)
		self.do_l(x+w, y+h)
		self.do_l(x, y+h)
		self.do_h()

	def do_m(self, x,y):
		self.pos = Pos(x,y)

	def do_l(self, x,y):
		# draw from self.pos to Pos(x,y)
		self.pos = Pos(x,y)

	def do_h(self):
		# End subpath if one is defined
		if self.startpos:
			self.do_l(self.startpos.X, self.startpos.Y)
			self.pos = self.startpos

		# End subpath
		self.startpos = None

	# Colorspaces


	# Transformations

	def get_cm(self):		return self._cm
	def set_cm(self,v):		self._cm = v
	cm = property(get_cm, set_cm, "cm -- Current transformation matrix")


	# Text

	def get_Tf(self):		return self._Tf
	def set_Tf(self,v):		self._Tf = v
	Tf = property(get_Tf, set_Tf, "Tf -- Font size")


class Mat3x3:
	def __init__(self, a, b, c, d, e, f):
		self.A = float(a)
		self.B = float(b)
		self.C = float(c)
		self.D = float(d)
		self.E = float(e)
		self.F = float(f)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "(%.2f %.2f %.2f %.2f %.2f %.2f)" % (self.A, self.B, self.C, self.D, self.E, self.F)

class Pos:
	def __init__(self, x, y):
		self.X = float(x)
		self.Y = float(y)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "(%.2f, %.2f)" % (self.X, self.Y)


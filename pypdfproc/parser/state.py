"""
Keeps track of state during rendering of the PDF page contents.
"""

import copy


# Color spaces: Table 4.12 (pg 237) of 1.7 spec
CS_DeviceGray = 0
CS_DeviceRGB = 1
CS_DeviceCMYK = 2
CS_CalGray = 3
CS_CalRGB = 4
CS_Lab = 5
CS_ICCBased = 6
CS_Indexed = 7
CS_Pattern = 8
CS_Separation = 9
CS_DeviceN = 10

# Line caps: Table 4.4 (pg 216) of 1.7 spec
LC_Butt = 0
LC_Round = 1
LC_ProjSquare = 2

# Line joint: Table 4.5 (pg 216) of 1.7 spec
LJ_Miter = 0
LJ_Round = 1
LJ_Bevel = 2

# Rendering intent: Table 4.20 (pg 261-2) of 1.7 spec
RI_AbsoluteColorimetric = 0
RI_RelativeColorimetric = 1
RI_Saturation = 2
RI_Perception = 3


# Blend mode: Table 7.2 (pg 520-2) of 1.7 spec
BM_Normal = 0
BM_Multiply = 1
BM_Screen = 2
BM_Overlay = 3
BM_Darken = 4
BM_Lighten = 5
BM_ColorDodge = 6
BM_ColorBurn = 7
BM_HardLight = 8
BM_SoftLight = 9
BM_Difference = 10
BM_Exclusion = 11

class StateManager:
	"""
	Manager of state information.
	"""

	stack = None

	def __init__(self):
		self.stack = []

		self.stack.append( State() )

	@property
	def S(self):
		"""
		Get current graphics state.
		"""
		return self.stack[-1]

	@property
	def T(self):
		"""
		Get current text state.
		"""
		return self.S.text

	def Pop(self):
		"""
		Invoked by the Q command.
		"""

		if len(self.stack) == 0:
			raise ValueError("Cannot pop an empty stack")
		elif len(self.stack) == 1:
			raise ValueError("Cannot pop initial values of the stack")

		else:
			self.stack.pop()

	def Push(self):
		"""
		Invoked by the q command.
		"""

		if len(self.stack) == 0:
			raise ValueError("Cannot push an empty stack")

		sc = self.S.Copy()
		self.stack.append(sc)

class State:
	"""
	Full graphics state information.
	"""

	# See Table 4.2 (pg 210-3) of 1.7 spec
	ctm = None
	clippath = None
	text = None

	# Position of a start of graphics operations
	startpos = None
	# Current position
	pos = None

	graphics = None

	def __init__(self):
		self.startpos = Pos.Origin()
		self.pos = Pos.Origin()

		self.ctm = Mat3x3.Identity()
		self.clippath = []
		self.colorspace = (CS_DeviceGray, CS_DeviceGray)
		self.color = (None, None)
		self.text = TextState()
		self.linewidth = 1.0
		self.linecap = LC_Butt
		self.linejoin = LJ_Miter
		self.miterlimit = 10.0
		self.dashpattern = (tuple(), 0)
		self.renderingintent = RI_RelativeColorimetric
		self.strokeadjustment = False
		self.blendmode = BM_Normal
		self.softmask = None
		self.alphaconstant = 1.0
		self.alphasource = False

	def Copy(self):
		return copy.deepcopy(self)

	@property
	def T(self):
		"""
		Get current text state.
		"""
		return self.text


	# Graphics state

	def get_d(self):		return self._dashpattern
	def set_d(self,v):		self._dashpattern = v
	dashpattern = property(get_d, set_d, doc="d -- Dash pattern")

	def get_j(self):		return self._linejoin
	def set_j(self,v):		self._linejoin = v
	linejoin = property(get_j, set_j, doc="j -- Line join")

	def get_J(self):		return self._linecap
	def set_J(self,v):		self._linecap = v
	linecap = property(get_J, set_J, doc="J -- Line cap")

	def get_M(self):		return self._miterlimit
	def set_M(self,v):		self._miterlimit = v
	miterlimit = property(get_M, set_M, doc="M -- Miter limit")

	def get_ri(self):		return self._miterlimit
	def set_ri(self,v):		self._miterlimit = v
	miterlimit = property(get_ri, set_ri, doc="ri -- riiter limit")

	def get_w(self):		return self._linewidth
	def set_w(self,v):		self._linewidth = v
	linewidth = property(get_w, set_w, doc="w -- Line width")


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



class TextState:
	"""
	State information for processing text functions.
	Easier to segment into a separate object to track the state.
	"""

	def __init__(self):
		# Graphics commands
		self.graphics = []

		# Text
		self.Tf = (None, None)
		self.Tc = 0.0
		self.TL = 0.0
		self.Tr = 0
		self.Ts = 0.0
		self.Tw = 0.0
		self.Tz = 100.0
		self.Tm = None
		self.Tlm = None

	def text_begin(self):
		self.Tm = Mat3x3.Identity()
		self.Tlm = Mat3x3.Identity()
	def text_end(self):
		self.Tm = None
		self.Tlm = None

	def get_Tc(self):		return self._Tc
	def set_Tc(self,v):		self._Tc = float(v)
	Tc = property(get_Tc, set_Tc, "Tc -- Character spacing")

	def get_Tf(self):		return self._Tf
	def set_Tf(self,v):		self._Tf = v
	Tf = property(get_Tf, set_Tf, doc="Tf -- Font name")

	def get_Tfs(self):		return self._Tfs
	def set_Tfs(self,v):	self._Tfs = float(v)
	Tfs = property(get_Tfs, set_Tfs, doc="Tfs -- Font size")

	def get_TL(self):		return self._TL
	def set_TL(self,v):		self._TL = float(v)
	TL = property(get_TL, set_TL, doc="TL -- Leading (Tl)")

	def get_Tlm(self):		return self._Tlm
	def set_Tlm(self,v):	self._Tlm = v
	Tlm = property(get_Tlm, set_Tlm, doc="Tlm -- Text line matrix")

	def get_Tm(self):		return self._Tm
	def set_Tm(self,v):		self._Tm = self._Tlm = v
	Tm = property(get_Tm, set_Tm, doc="Tm -- Text matrix")

	def get_Tr(self):		return self._Tr
	def set_Tr(self,v):		self._Tr = int(v)
	Tr = property(get_Tr, set_Tr, doc="Tr -- Rendering mode (Tmode)")

	def get_Ts(self):		return self._Ts
	def set_Ts(self,v):		self._Ts = float(v)
	Ts = property(get_Ts, set_Ts, doc="Ts -- Text rise (Trise)")

	def get_Tw(self):		return self._Tw
	def set_Tw(self,v):		self._Tw = float(v)
	Tw = property(get_Tw, set_Tw, doc="Tw -- Word spacing")

	def get_Tz(self):		return self._Tz
	def set_Tz(self,v):		self._Tz = float(v)
	Tz = property(get_Tz, set_Tz, doc="Tz -- Horizontal scaling (Th)")


	def do_Td(self, x,y):
		self.Tm = self.Tlm = Mat3x3(1,0, 0,1, x,y) * self.Tlm

	def do_TD(self, x,y):
		self.do_TL(-y)
		self.do_Td(x,y)

	def do_Tj(self, w, glyph):
		#print(['do_Tj', w, glyph])

		#if glyph: print("Pre <%.2f, %.2f> '%s'" % (self.Tm.E, self.Tm.F, glyph.unicode))

		# Adjust Tm based on width from TJ or glyph from TJ/Tj
		if w != None:
			# Assuming horizontal (i.e., ignoring self.Tr)
			tx = ((0.0 - w)/1000.0*self.Tfs + self.Tc + self.Tw)*(self.Tz / 100.0)
			#print(['tx w', tx, w, self.Tfs, self.Tc, self.Tw, self.Tz])

			self.Tm = Mat3x3(1,0, 0,1, tx,0) * self.Tm
		else:
			# Assuming horizontal (i.e., ignoring self.Tr)
			tx = ((glyph.width - 0.0)/1000.0*self.Tfs + self.Tc + self.Tw)*(self.Tz / 100.0)
			#print(['tx g', tx, glyph.width, self.Tfs, self.Tc, self.Tw, self.Tz])

			self.Tm = Mat3x3(1,0, 0,1, tx,0) * self.Tm

		#if glyph: print("Pst <%.2f, %.2f> '%s'" % (self.Tm.E, self.Tm.F, glyph.unicode))


	def do_Tstar(self):
		self.do_Td(0, self.TL)

# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
# Data strctures

class Mat3x3:
	"""
	3x3 matrix whose arguments are primarily the six elements specified for Tm command.

	[a b g
	 c d h
	 e f i]

	Where (a,b,c,d,e,f) are the six common to Tm command.
	However, setting the 3rd column is also possible but presumed to be:

	[a b g=0
	 c d h=0
	 e f i=1]
	"""

	def __init__(self, a, b, c, d, e, f, g=0, h=0, i=1):
		self.A = float(a)
		self.B = float(b)
		self.C = float(c)
		self.D = float(d)
		self.E = float(e)
		self.F = float(f)
		self.G = float(g)
		self.H = float(h)
		self.I = float(i)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "[%.2f %.2f %.2f; %.2f %.2f %.2f; %.2f %.2f %.2f]" % (self.A, self.B, self.G, self.C, self.D, self.H, self.E, self.F, self.I)

	def __mul__(a, b):
		"""
		[a b g    [A B G    [a*A+b*c+g*E a*B+b*D+g*F a*G+b*H+g*I
		 c d h  *  C D H  =  c*A+d*c+h*E c*B+d*D+h*F c*G+d*H+h*I
		 e f i]    E F I]    e*A+f*c+i*E e*B+f*D+i*F e*G+f*H+i*I]


		"""

		c = Mat3x3(
				a.A*b.A + a.B*b.C + a.G*b.E,
				a.A*b.B + a.B*b.D + a.G*b.F,
				a.C*b.A + a.D*b.C + a.H*b.E,
				a.C*b.B + a.D*b.D + a.H*b.F,
				a.E*b.A + a.F*b.C + a.I*b.E,
				a.E*b.B + a.F*b.D + a.I*b.F,
				a.A*b.G + a.B*b.H + a.G*b.I,
				a.C*b.G + a.D*b.H + a.H*b.I,
				a.E*b.G + a.F*b.H + a.I*b.I
			)

		#print(a)
		#print(b)
		#print(c)
		return c

	@staticmethod
	def Identity():
		return Mat3x3(1,0, 0,1, 0,0)

class Pos:
	def __init__(self, x, y, z=1.0):
		self.X = float(x)
		self.Y = float(y)
		self.Z = float(z)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "(%.2f, %.2f, %.2f)" % (self.X, self.Y, self.Z)

	@staticmethod
	def Origin():
		return Pos(0,0)


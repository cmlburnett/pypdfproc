
from . import parser


class FontMetricsData:
	FMVersion = None

	Ascender = None
	CapHeight = None
	CharacterSet = None
	Comments = None
	Descender = None
	EncodingScheme = None
	FontBBox = None
	FontName = None
	FullName = None
	FamilyName = None
	IsFixedPitch = None
	ItalicAngle = None
	Notice = None
	StdHW = None
	StdVW = None
	UnderlinePosition = None
	UnderlineThickness = None
	Version = None
	Weight = None
	XHeight = None

	CharMetrics = None
	Ligatures = None
	Kerning = None

	def __init__(self, filename):
		self.filename = filename

		f = open(filename, 'r')
		txt = f.read()
		f.close()

		t = parser.FontMetricsTokenizer(txt)

		# Parse and then set data on this object
		dat = t.Parse()
		for k in dat:
			setattr(self, k, dat[k])


		for k in self.CharMetrics:
			print([k, self.CharMetrics[k]])
		for k in self.Kerning['Pairs']:
			print([k, self.Kerning['Pairs'][k]])

		print(['width', self.GetWidth('space')])

	def GetWidth(self, charname):
		if charname not in self.CharMetrics:
			return None

		c = self.CharMetrics[charname]

		# NB: assumes horizontal direction
		return c['W'][0]


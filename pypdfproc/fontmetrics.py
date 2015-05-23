"""
Classes to work with Font Metrics (Tech Note #5004) data files.
* FontMetricsData will parse a file given a file name
"""

from . import parser

class FontMetricsData:
	"""
	Parses the font metrics file provided.
	All of the properties should be self-explanatory, otherwise see the font metrics specification.
	"""

	# This is the value that accompanies the StartFontMetrics line; not the Version line below (font program version)
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
	# Font program version (matches FontInfo dictionary of the font program); not the font metrics version
	Version = None
	Weight = None
	XHeight = None

	CharMetrics = None
	Ligatures = None
	Kerning = None

	def __init__(self, filename):
		"""
		Parses the font metrics file with filename @filename.
		All font metrics data is then applied to this object for use.
		"""

		self.filename = filename

		f = open(filename, 'r')
		txt = f.read()
		f.close()

		t = parser.FontMetricsTokenizer(txt)

		# Parse and then set data on this object
		dat = t.Parse()
		self.__dict__.update(dat)

	def GetCharacter(self, val):
		"""
		Gets character information based on the value supplied.
		If @val is an integer, then it is assumed to be a character code.
		If @val is a string, then it is assumed to be a character name.
		"""

		if type(val) == int:
			for k,v in self.CharMetrics:
				if v['C'] == val:
					return v

			# Character code not found
			return None

		elif type(val) == str:
			if val not in self.CharMetrics:
				# Character name not found
				return None
			else:
				return self.CharMetrics[val]

		else:
			raise TypeError("Unrecognized type '%s', need str or int" % str(val))

	def GetLigaturesForward(self, firstchar):
		"""
		Gets all ligatures composed by the given character: the first character of the ligature.
		"""

		ret = []

		for l in self.Ligatures:
			if l['base'] == firstchar:
				ret.append(l)

		return ret

	def GetLigaturesBackward(self, ligchar):
		"""
		Gets all ligatures where the ligature character is @ligchar.
		"""

		ret = []

		for l in self.Ligatures:
			if l['ligature'] == ligchar:
				ret.append(l)

		return ret

	def GetWidths(self):
		"""
		Gets all widths for all characters provided, indexed by character name.
		Widths are a two-tuple of horizontal and vertical widths.
		Vertical may not apply to all fonts, and it is represented as zero.
		"""

		ret = {}

		for k,v in self.CharMetrics.items():
			ret[k] = v['W']

		return ret

	def GetWidthsX(self):
		"""
		Gets all horizontal widths for all characters provided, indexed by character name.
		"""

		ret = {}

		for k,v in self.CharMetrics.items():
			ret[k] = v['W'][0]

		return ret

	def GetWidthsY(self):
		"""
		Gets all vertical widths for all characters provided, indexed by character name.
		"""

		ret = {}

		for k,v in self.CharMetrics.items():
			ret[k] = v['W'][1]

		return ret

	def GetWidth(self, charname):
		"""
		Get the widths of the character @charname as a two-tuple of horizontal & vertical widths.
		Vertical may not apply to all fonts, and it is represented as zero.
		"""

		if charname not in self.CharMetrics:
			return None

		c = self.CharMetrics[charname]

		return c['W']

	def GetWidthX(self, charname):
		"""
		Get the horizontal width of character @charname.
		"""

		ret = self.GetWidth(charname)
		if ret == None:
			return None

		return ret[0]

	def GetWidthY(self, charname):
		"""
		Get the vertical width of character @charname.
		"""

		ret = self.GetWidth(charname)
		if ret == None:
			return None

		return ret[1]

	def GetKerningPairsForChar(self, charname):
		"""
		Gets kerning pair information for the given character.
		The returned dictionary is indexed by the successor character and the value is the kerning adjustment.
		For example, if kerning for "o" is asked for then kerning pairs (o,v), (o,w) will be returned as {'v': ..., 'w': ...} as the first character is assumed.
		"""

		ret = {}

		for k in self.Kerning['Pairs']:
			if k[0] != charname: continue

			ret[k[1]] = self.Kerning['Pairs'][k]

		return ret


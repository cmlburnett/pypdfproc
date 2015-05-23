"""
Classes to work with Font Metrics (Tech Note #5004) data files.

The FontMetricsManager is probably the class you want to work directly with.
It has functions to load plaintext files, zip files, and can index numerous FontMetricsData objects by font name.


Font metric data is loaded, parsed, and stored via the following classes:
* FontMetricsData contains data from a font metrics file, but that data is loaded via a derivative class
* FontMetricsData_File loads from a file
* FontMetricsData_String loads from a text string
"""

from zipfile import ZipFile

from . import parser

class FontMetricsManager:
	"""
	Manager class
	"""

	# FontMetricsData objects (and derivatives), indexed by font name (FontName value in the AFM files)
	Data = None

	def __init__(self):
		self.Data = {}

	def AddFMD(self, fmd):
		"""
		Adds the FontMetricsData object to the manager.
		This is mostly an internal function, but there's little reason not to expose it.
		"""

		fname = fmd.FontName

		if fname in self.Data:
			raise ValueError("Already loaded font '%s', why load it a second time?" % fname)

		self.Data[fname] = fmd

		return fmd

	def AddFile(self, filename):
		"""
		Add an individual plaintext AFM file to the list.
		"""

		o = FontMetricsData_File(filename)
		return self.AddFMD(o)

	def AddZip(self, filename, fonts=None):
		"""
		Add all fonts in the zip file @filename.
		All font files should be in the 'root' directory of the zip file as this does not traverse directories.
		If @fonts is provided, then only those listed in the list will be loaded.
		"""

		ret = []

		z = ZipFile(filename)
		fnames = z.namelist()

		for fname in fnames:
			name = fname.split('.')[0]

			# Skip if not in list of fonts to load
			if type(fonts) == list and name not in fonts:
				continue

			dat = z.read(fname)
			# returns a bytes object, so convert to text
			dat = dat.decode('latin-1')

			try:
				o = FontMetricsData_String(dat)
			except Exception as e:
				print("Caught exception while parsing filename '%s' in zip file '%s'" % (name, filename))
				raise e

			self.AddFMD(o)
			ret.append(o)

		return ret

	def RemoveFont(self, fname):
		"""
		Removes the font from this manager.
		Provided is @fname the FontName in the AFM.
		"""

		if fname not in self.Data:
			raise ValueError("Font '%s' is not currently loaded, cannot remove it" % fname)

		# Get the FDM
		o = self.Data[fname]

		# Remove the FDM from the list
		del self.Data[fname]

		# Return it, just in case the caller cares (otherwise no big deal)
		return o

	def HasFontName(self, fname):
		return fname in self.Data

	def GetFontNames(self):
		return list(self.Data.keys())

	def __getitem__(self, k):
		if not k in self.Data:
			raise KeyError("Font '%s' has not been loaded yet" % k)

		return self.Data[k]

class FontMetricsData:
	"""
	YOU PROBABLY DON'T WANT TO INSTANTIATE THIS CLASS, see derivative classes.

	Merely a container for font metrics data.
	Classess inherit from this that implement specific methods for loading in font metrics data.
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

	def GetWidths(self, firstchar=None, lastchar=None):
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

class FontMetricsData_File(FontMetricsData):
	"""
	Font metrics data loaded from a file.
	"""

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

class FontMetricsData_String(FontMetricsData):
	"""
	Font metrics data loaded from a text string.
	"""

	def __init__(self, txt):
		"""
		Parses the font metrics file when supplied as a string
		All font metrics data is then applied to this object for use.
		"""

		t = parser.FontMetricsTokenizer(txt)

		# Parse and then set data on this object
		dat = t.Parse()
		self.__dict__.update(dat)


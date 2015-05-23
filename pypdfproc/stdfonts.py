"""
Standard 14 PDF fonts.
"""

from .fontmetrics import FontMetricsManager

class StandardFonts:
	"""
	"""

	# FontMetricsManager object
	FM = None

	def __init__(self):
		self.FM = FontMetricsManager()

	def AddZip(self, filename):
		self.FM.AddZip(filename)

	def GetFontMetrics(self, fname):
		return self.FM[fname]


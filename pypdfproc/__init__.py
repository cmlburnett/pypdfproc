"""
PDF Processor
"""

__version__ = "1.0.0"

__all__ = ['parser']

# System libs
import mmap

from . import parser
from . import pdf as _pdf

class PDF:
	# File name, file object, and mmap object
	fname = None
	f = None
	m = None

	# PDF parser
	p = None

	def __init__(self, fname):
		self.fname = fname

		# Open file and mmap it
		self.f = open(fname, 'rb')
		self.m = mmap.mmap(self.f.fileno(), 0, prot=mmap.PROT_READ)

		# Open the file and initialize it (xref/trailer reading)
		self.p = parser.PDFTokenizer(self.m)
		self.p.Initialize()

	def Close(self):
		self.m.close()
		self.f.close()

		self.m = None
		self.f = None
		self.p = None

	def GetRootObject(self):
		return self.p.GetRootObject()

	def GetFullText(self):
		root = self.GetRootObject()

		contents = []

		pages = root.Pages.DFSPages()
		for page in pages:
			cts = page.Contents

			pgct = None
			if type(cts) == list:
				contents += [ct.Stream for ct in cts]
			else:
				contents.append(cts.Stream)

		content = " ".join(contents)

		tt = parser.TextTokenizer(self.f, self.p)

		toks = tt.TokenizeString(content)
		return toks


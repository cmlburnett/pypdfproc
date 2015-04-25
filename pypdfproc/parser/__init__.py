
from .pdf import lexer as _lexer

__all__ = ['PDFTokenizer']

class PDFTokenizer:
	file = None

	def __init__(self, file):
		self.file = file



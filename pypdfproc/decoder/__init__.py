"""
Various decoders needed for parsing PDF files.
"""

__all__ = ['flate']

from .flate import FlateDecode

class Decoder:
	def __init__(self):
		raise Exception("Do not instantiate, everything is a static method")

	@staticmethod
	def Flate(data, parms):
		return FlateDecode(data, parms)


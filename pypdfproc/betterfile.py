
import os

class betterfile:
	@staticmethod
	def open(fname, mode):
		o = betterfile()
		o.f = open(fname, mode)
		return o

	def close(self):
		self.f.close()
		self.f = None

	def fileno(self):
		return self.f.fileno()

	def peek(self, n):
		return self.f.peek(n)

	def seek(self, off, whence=os.SEEK_SET):
		ret = self.f.seek(off, whence)
		return ret

	def tell(self):
		pos = self.f.tell()
		return pos

	def read(self, cnt=-1):
		c = self.f.read(cnt)
		return c

	def readline(self):
		line = bytearray()
		while True:
			s = self.read(1)

			if len(s) == 0:
				return line

			# CR or CRLF
			if s == b'\r':
				p = self.peek(1)
				# CRLF
				if len(p) and p[0] == b'\n':
					self.f.read(1) # Consume LF
					if not len(line): line = bytearray('\n', 'latin-1')
					return line

				# Just CR
				else:
					if not len(line): line = bytearray('\n', 'latin-1')
					return line

			# Just LF
			elif s == b'\n':
				if not len(line): line = bytearray('\n', 'latin-1')
				return line
			else:
				line.append(ord(s))

	# Non-standard functions

	def readrev(self):
		if self.tell() == 0:
			return 0

		# One step forward, two steps back
		c = self.f.read(1)
		self.seek(-2, os.SEEK_CUR)

		return c

	def gotoend(self):
		"""
		Helper function that jumps to lass byte in the file.
		"""

		self.seek(-1, os.SEEK_END)

	def readlinerev(self, n=1):
		"""
		Helper function that reads @n lines in reverse.
		"""

		if n == 1:
			return self._readlinerev()

		lines = []
		for i in range(n):
			lines.append(self._readlinerev())
		return lines

	def _readlinerev(self):
		"""
		Helper function that reads a single line in reverse.
		"""

		line = bytearray()
		while True:
			s = self.readrev()

			if len(s) == 0:
				if len(line) > 0:
					return line

			# LF or CRLF
			if s == b'\n':
				ss = self.readrev()

				# CRLF
				if ss == b'\r':
					if not len(line): line = bytearray('\n', 'latin-1')
					return line

				# Just LF
				else:
					# Un-read the @ss character
					self.seek(1, SEEK_CUR)

					if not len(line): line = bytearray('\n', 'latin-1')
					return line

			# CR
			elif s == b'\r':
				if not len(line): line = bytearray('\n', 'latin-1')
				return line

			else:
				# Insert at start
				line.insert(0, ord(s))


"""
PDF command-line interface to navigate PDF files at an object-level.
"""

# System libs
import cmd, os, sys, traceback

# Libraries
from ..__init__ import PDF
from .. import pdf as _pdf

__all__ = ['Init', 'Run']

def format_cols(dat, pre="  ", celldiv=" ", rowdiv="\n", post=""):
	"""
	Simple method for formating multi-column data.
	"""

	# No data = no output
	if not len(dat):
		return ""

	# Create list of max column sizes
	maxes = [0] * len(dat[0])
	# Calculate max column sizes
	for i in range(len(dat)):
		row = dat[i]
		for j in range(len(row)):
			# Get cell length
			l = len(row[j])
			# If longer than max then update max
			if maxes[j] < l:
				maxes[j] = l

	# Now format each row as a collection of cells
	ret = []
	for i in range(len(dat)):
		retrow = []

		row = dat[i]
		for j in range(len(row)):
			cell = ("%%%ds" % maxes[j]) % row[j]
			retrow.append(cell)

		# Space between each column
		ret.append(pre + celldiv.join(retrow) + post)

	# Newline between each row
	return rowdiv.join(ret)

def pdfbase_objects(obj):
	dat = []

	if isinstance(obj, pypdfproc._pdf.PDFHigherBase):
		ps = obj.getsetprops()
		for k,v in ps.items():
			if k == '_Loader': continue
			if k[0] != '_': continue

			if v == None: continue

			dat.append( (k[1:],) )

	elif isinstance(obj, pypdfproc._pdf.PDFStreamBase):
		dat.append( ('Dict',) )
		dat.append( ('Stream',) )
		dat.append( ('StreamRaw',) )

	elif isinstance(obj, pypdfproc._pdf.Dictionary):
		keys = obj.dictionary.keys()
		keys.sort()

		for k in keys:
			v = obj.dictionary[k]

			if type(v) == str:
				dat.append( (k,v) )
			else:
				dat.append( (k,"%s"%v) )

	else:
		raise CmdError("Unrecognized type: '%s'" % obj)

	return dat


class CmdError(Exception):
	"""
	Catching this exception results in the message being printed.
	Other exceptions caught result in the full traceback being printed.
	"""
	pass

class PDFCmdState:
	"""
	Handles and maintains the CLI state.
	This is so that that is separate from the actual CLI parsing.
	"""

	_files = None
	_pdfs = None
	_pwd = None

	def __init__(self):
		self._files = []
		self._pdfs = {}
		self._pwd = []

	def quit(self):
		for f in self._files:
			if self._pdfs[f[0]] != None:
				self._pdfs[f[0]].Close()
		self._files = []
		self._pdfs.clear()

	def prompt(self):
		if len(self._pwd):
			return "%s $ " % self._pwd_item( self._pwd[-1] )
		else:
			return "/ $ "

	# ---------------------------------------------------------------
	# Commands

	def open(self, item):
		f = item.strip()

		absf = os.path.abspath(f)
		fname = os.path.basename(absf)
		if not os.path.exists(f):
			raise CmdError("File '%s' does not exist" % f)

		# Cannot have more than one file with the same filename open, sorry
		# This restriction also exists in Word, Excel, etc. for the same reason I'm sure
		if fname in self._pdfs:
			raise CmdError("Cannot open more than one file with the same filename: '%s'" % f)

		self._files.append( (fname,absf,os.stat(absf)) )
		self._pdfs[fname] = pypdfproc.PDF(absf)

	def close(self, item):
		item = item.strip()

		# If somewhere inside the file being closed, then cd to the root first
		if len(self._pwd) and self._pwd[0] == item:
				self.cd("/")

		# Close file if it is found
		for i in range(len(self._files)):
			f = self._files[i]
			if f[0] == item:
				self._pdfs[ f[0] ].Close()

				del self._files[i]
				del self._pdfs[ f[0] ]
				return

		raise CmdError("File '%s' not found, cannot close it" % item)

	def _pwd_item(self, item):
		if type(item) == str:
			return item
		elif type(item) == tuple:
			# Tuple format is (object, text to show)
			return item[1]
		elif isinstance(item, pypdfproc._pdf.PDFBase):
			return str(item.__class__).split('.')[-1]
		else:
			raise TypeError("Unrecognized pwd stack type: '%s'" % item)

	def pwd(self):
		ret = []
		for p in self._pwd:
			_ = self._pwd_item(p)
			ret.append(_)

		return "/" + "/".join(ret)

	def cd(self, line):
		line = line.strip()

		if line == '' or line == '/':
			self._pwd = []
			return

		parts = line.split('/')
		for part in parts:
			self._cd(part)

	def _cd(self, line):
		if line == '' or line == '/':
			self._pwd = []
		elif line == '.':
			# Nothing to do
			pass
		elif line == '..':
			self._pwd.pop()

		elif len(self._pwd) == 0:
			# At root, cd'ing into a file
			for f in self._files:
				if f[0] == line:
					self._pwd.append(f[0])
					return

			raise CmdError("File '%s' not opened, open it first to use it" % line)

		elif len(self._pwd) == 1:
			# cd'ing around inside a file
			item = line.strip().lower()

			if item == 'catalog':
				fname = self._pwd[0]
				p = self._pdfs[fname]
				self._pwd.append(p.GetRootObject())
			elif item == 'objects':
				self._pwd.append('Objects')
			elif item == 'xref':
				self._pwd.append('XRef')
			else:
				raise CmdError("No PDF root level of '%s'" % line)

		elif len(self._pwd) > 1:
			prev = self._pwd[-1]

			# Unpack tuple
			if type(prev) == tuple:
				prev = prev[0]

			if type(prev) == list:
				idx = int(line)
				self._pwd.append( (prev[idx],"[%d]"%idx) )
			elif isinstance(prev, pypdfproc._pdf.Dictionary):
				self._pwd.append( (prev, "Dict") )

			elif isinstance(prev, pypdfproc._pdf.PDFStreamBase):
				line = line.lower()

				if line == 'dict':
					self._pwd.append( prev.Dict )
				elif line == 'stream':
					self._pwd.append( "Stream" )
				elif line == 'streamRaw':
					self._pwd.append( "StreamRaw" )
				else:
					raise CmdError("Stream has no property '%s'" % line)

			elif isinstance(prev, pypdfproc._pdf.PDFBase):
				# TODO: requires case to be exact
				ps = prev.getsetprops()
				if '_Loader' in ps: del ps['_Loader']
				k = '_'+line
				if k in ps:
					v = getattr(prev, line)
					if isinstance(v, pypdfproc._pdf.Array) or type(v) == list:
						# Tuple of (object, text to show in pwd)
						self._pwd.append( (v, line) )
					else:
						self._pwd.append(v)
				else:
					raise CmdError("Object does not have property '%s'" % line)
			else:
				raise TypeError("Unrecognized type: '%s'" % prev)

		else:
			raise CmdError("Cannot cd for '%s'" % line)

	def ls(self, line):
		if not len(self._pwd):
			dat = []
			for f in self._files:
				dat.append( (f[0], "%d bytes" % f[2].st_size) )

			ret = "total %d\n" % len(self._files)
			ret += format_cols(dat, celldiv="  ")
			return ret

		elif len(self._pwd) == 1:
			# Root listing
			fname = self._pwd[0]
			p = self._pdfs[fname]
			root = p.GetRootObject()

			dat = [ ('Catalog',), ('Objects',), ('XRef',) ]
			return format_cols(dat)

		elif len(self._pwd) == 2:
			# Listing of one of the root pieces of inforamtion in a file
			fname = self._pwd[0]
			p = self._pdfs[fname]

			typ = self._pwd[1]

			if isinstance(typ, pypdfproc._pdf.Catalog):
				root = typ

				dat = []

				ps = root.getsetprops()
				for k,v in ps.items():
					if k == '_Loader': continue
					if k[0] != '_': continue

					if v == None: continue

					dat.append( (k[1:],) )

				return format_cols(dat)

			elif typ.lower() == 'objects':
				pass
			elif typ.lower() == 'xref':
				pass
			else:
				raise CmdError("Unrecognized level '%s' under object" % typ)

		elif len(self._pwd) > 2:
			item = self._pwd[-1]
			if isinstance(item, pypdfproc._pdf.PDFBase):
				dat = pdfbase_objects(item)
				return format_cols(dat)

			# Tuple format is (object, text to show in pwd)
			elif type(item) == tuple:
				if isinstance(item[0], pypdfproc._pdf.PDFBase):
					dat = pdfbase_objects(item[0])
				elif type(item[0]) == list:
					dat = []
					for i in range(len(item[0])):
						dat.append( ("[%d]"%i, str(item[0][i].__class__).split('.')[-1]) )

				else:
					raise TypeError("Unexpected tuple[0] object: '%s'" % item[0])

				return format_cols(dat)

			elif type(item) == str:
				pprev = self._pwd[-2]

				if isinstance(pprev, pypdfproc._pdf.PDFStreamBase):
					if item == 'Stream':
						# Nowhere else to go
						return
					elif item == 'StreamRaw':
						# Nowhere else to go
						return
					else:
						raise TypeError("Unrecognized Stream property: '%s'" % item)
				else:
					raise TypeError("Unrecognized top pwd type: '%s'" % (pprev,))
			else:
				raise TypeError("Unexpected top pwd type: '%s'" % (self._pwd[-1],))

		else:
			raise NotImplementedError

	def cat(self, line):
		if not len(self._pwd):
			raise CmdError("Nothing to cat at root level")

		prev = self._pwd[-1]

		raise NotImplementedError

class PDFCmd(cmd.Cmd):
	"""
	CLI interface handling class.
	Explicitly does not handle or store any state information.
	Utilizes the PDFCmdState class to store and maintain state.
	"""

	state = None

	def get_prompt(self): return self.state.prompt()
	prompt = property(get_prompt)

	def __init__(self, *args, **kargs):
		cmd.Cmd.__init__(self, *args, **kargs)

		self.state = PDFCmdState()

	def setinitargs(self, args):
		for arg in args:
			self.do_open(arg)

	# ----------------------------------------------------------------------------------------
	# ----------------------------------------------------------------------------------------

	def onecmd(self, line):
		try:
			return cmd.Cmd.onecmd(self, line)

		except SystemExit:
			print("")
			raise
		except CmdError as e:
			# Print just the message instead of the whole exception traceback
			print(e.message)
		except:
			traceback.print_exc()
			# That's it, just print and continue on with life

	# ----------------------------------------------------------------------------------------
	# ----------------------------------------------------------------------------------------
	# Commands

	def do_open(self, line):
		"""Open a file. Doing so adds it to the root file list."""
		ret = self.state.open(line)
		if ret:
			print(ret)

	def do_close(self, line):
		"""Close a file. Doing so removes it from the root file list."""
		ret = self.state.close(line)
		if ret:
			print(ret)

	def do_ls(self, line):
		"""List available objects at current location"""
		ret = self.state.ls(line)
		if ret:
			print(ret)

	def do_pwd(self, line):
		"""Print current working directory"""
		ret = self.state.pwd()
		if ret:
			print(ret)

	def do_cd(self, line):
		"""Change directory"""
		ret = self.state.cd(line)
		if ret:
			print(ret)

	def do_cat(self, line):
		"""Print output to screen"""
		ret = self.state.cat(line)
		if ret:
			print(ret)

	def do_quit(self, line):
		"""Quit the command-line interface"""
		self.state.quit()

		sys.exit(0)
	def do_EOF(self, line):
		"""Quit the command-line interface (ctrl-d)"""
		self.do_quit(line)

def Run(args=None):
	c = PDFCmd()
	c.setinitargs(args)
	c.cmdloop(intro="PDF command-line interface. Type 'help' or '?' to get available commands.")


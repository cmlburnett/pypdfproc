"""
Tokenizer and parser for the Carousel object system that makes up the PDF file.
"""

import ply.lex as plylex

tokens = (
	'EOF',
	'FLOAT',
	'INT',
	'COMMENT',

	'DICT_START',
	'DICT_END',
	'ARR_START',
	'ARR_END',
	'LIT_START',
	'LIT_END',
	'LITERAL',

	'NAME',
	'HEXSTRING',
	'WS',

	'true',
	'false',

	'obj',
	'endobj',
	'stream',
	'endstream',
	'xref',
	'xref_free',
	'xref_inuse',
	'xref_start',
	'trailer',
	'indirect'
)

t_DICT_START =	r'\<\<'
t_DICT_END =	r'\>\>'
t_ARR_START =	r'\['
t_ARR_END =	r'\]'
t_LIT_START =	r'\('
t_LIT_END =	r'\)'

# Literal strings to match
t_true =	r'true'
t_false =	r'false'

t_obj =		r'obj'
t_endobj =	r'endobj'
t_stream =	r'stream'
t_endstream =	r'endstream'
t_trailer =	r'trailer'
t_xref =	r'xref'
t_xref_start =	r'startxref'
t_xref_free =	r'f'
t_xref_inuse =	r'n'
t_indirect =	r'R'

# Import that this is before t_COMMENT otherwise "%%EOF" will be read as a comment, not an EOF
def t_EOF(t):
	r'%%EOF'
	return t

def t_COMMENT(t):
	r'%[^\r\n]+'

	# Consume leading % that indicates comment
	t.value = t.value[1:]
	return t

# Import that this is before t_INT otherwise something like "13.0" will match t_INT before t_FLOAT and
# result in (INT, 13) and (FLOAT, 0.0) by matching "13" and ".0" respectively
def t_FLOAT(t):
	r'\d*\.\d*'
	t.value = float(t.value)
	return t

def t_INT(t):
	r'-?\d+'
	t.value = int(t.value)
	return t

def t_NAME(t):
	r'/[^\(\)\<\>\[\]\/ \t\r\n]+'

	# Ignore slash (not formally a part of the name)
	t.value = t.value[1:]
	return t

def t_HEXSTRING(t):
	r'\<([0-9A-Fa-f]+)\>'

	# Ignore brackets
	t.value = t.value.rstrip('>').lstrip('<')
	return t

def t_error(t):
	print([t])
	raise Exception("Bad character ord='%d' on line %d" % (ord(t.value[0]), t.lexer.lineno))

def t_WS(t):
	r'[\t \r\n]+'

	# Ignore these tokens by returning None
	return None

# Ignore nothing, whitespace is handled above
t_ignore = ''

# Initiate lexer
lexer = plylex.lex()

class pdftokenizer:
	file = None

	def __init__(self, file):
		self.file = file


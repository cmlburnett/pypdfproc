"""
Parses CMap (character map) blocks
"""

import ply.lex as plylex

tokens = (
	'FLOAT',
	'INT',

	'DICT_START',
	'DICT_END',
	'ARR_START',
	'ARR_END',
	'LIT_START',
	'LIT_END',
	'NAME',

	'CODE',

	'findresource',
	'dict',
	'def',
	'cmap',
	'CMapName',
	'currentdict',
	'defineresource',
	'pop',

	'begin',
	'begincmp',
	'beginbfchar',
	'beginbfrange',
	'begincodespacerange',

	'end',
	'endcmp',
	'endbfchar',
	'endbfrange',
	'endcodespacerange',
)

t_DICT_START =			r'\<\<'
t_DICT_END =			r'\>\>'
t_ARR_START =			r'\['
t_ARR_END =				r'\]'
t_LIT_START =			r'\('
t_LIT_END =				r'\)'

t_findresource =		r'findresource'
t_dict =				r'dict'
t_def =					r'def'
t_cmap =				r'cmap'
t_CMapName =			r'CMapName'
t_currentdict =			r'currentdict'
t_defineresource =		r'defineresource'
t_pop =					r'pop'

t_begin =				r'begin'
t_begincmp =			r'begincmp'
t_beginbfchar =			r'beginbfchar'
t_beginbfrange =		r'beginbfrange'
t_begincodespacerange =	r'begincodespacerange'

t_end =					r'end'
t_endcmp =				r'endcmp'
t_endbfchar =			r'endbfchar'
t_endbfrange =			r'endbfrange'
t_endcodespacerange =	r'endcodespacerange'



# Import that this is before t_INT otherwise something like "13.0" will match t_INT before t_FLOAT and
# result in (INT, 13) and (FLOAT, 0.0) by matching "13" and ".0" respectively
def t_FLOAT(t):
	r'[-+]?\d*\.\d*'
	t.value = float(t.value)
	return t

def t_INT(t):
	r'[-+]?\d+'
	t.value = int(t.value)
	return t

def t_NAME(t):
	r'/[^\(\)\<\>\[\]\/ \t\r\n]+'

	# Ignore slash (not formally a part of the name)
	t.value = t.value[1:]
	return t

def t_error(t):
	print([t])
	raise Exception("Bad character ord='%d' on line %d" % (ord(t.value[0]), t.lexer.lineno))

def t_WS(t):
	r'[\t \r\n]+'

	t.lexer.lineno += len([c for c in t.value if c=='\n'])

	# Ignore these tokens by returning None
	return None

def t_CODE(t):
	r'\<[0-9A-Fa-f]+\>'

	t.value = int(t.value[1:-1], 16)
	return t

# Ignore nothing, whitespace is handled above
t_ignore = ''

# Initiate lexer
lexer = plylex.lex()

def TokenizeString(txt):
	lexer.input(txt)

	tokens = []
	tokcnt = 0

	# Parse text stream into tokens
	while True:
		tok = lexer.token()
		if not tok:
			break

		# Special handling by yanking out literal text because balanced parenthesis is hard in regex
		if tok.type == 'LIT_START':
			cnt = 1

			# Keep track so to know indices of literal string
			startpos = lexer.lexpos

			while cnt>0:
				if lexer.lexdata[lexer.lexpos] == '(' and lexer.lexdata[lexer.lexpos-1] != '\\':
					cnt += 1
				elif lexer.lexdata[lexer.lexpos] == ')' and lexer.lexdata[lexer.lexpos-1] != '\\':
					cnt -= 1

				# Make a step
				lexer.lexpos += 1

			# Save some typing
			endpos = lexer.lexpos

			# Yank out literal data excluding the last byte since that is the LIT_END
			tok.type = 'LIT'
			tok.value = lexer.lexdata[startpos:(endpos-1)]

			# Strip out escaped parentheses
			tok.value = tok.value.replace("\\(", "(").replace("\\)", ")")

			# SCRATCH THIS: SKIP THE LIT_END TOKEN COMPLETELY
			# Go back a space so the lexer pulls out the LIT_END token
			#lexer.lexpos -= 1

		tokcnt += 1
		tokens.append(tok)

	return tokens


"""
Font Metrics 4.1 specification (Tech note #5004).

Needed to import information about the 14 standard fonts
"""

def intorfloat(v):
	try:
		return int(v)
	except:
		pass

	return float(v)

import ply.lex as plylex

tokens = (
	'FLOAT',
	'INT',
	'COMMENT',

	'StartFontMetrics',		'EndFontMetrics',
	'StartCharMetrics',		'EndCharMetrics',
	'StartKernData',		'EndKernData',
	'StartKernPairs',		'EndKernPairs',

	'FontName',
	'FullName',
	'FamilyName',
	'Weight',
	'ItalicAngle',
	'IsFixedPitch',
	'CharacterSet',
	'FontBBox',
	'UnderlinePosition',
	'UnderlineThickness',
	'Version',
	'Notice',
	'EncodingScheme',
	'CapHeight',
	'XHeight',
	'Ascender',
	'Descender',
	'StdHW',
	'StdVW',

	'C', 'CH',
	'W', 'W0', 'W1', 'WX', 'W0X', 'W1X', 'WY', 'W0Y', 'W1Y',
	'N', 'B', 'L',
	'KP', 'KPH', 'KPX', 'KPY',

	'SemiColon',
)

t_EndFontMetrics =			r'EndFontMetrics'
t_EndCharMetrics =			r'EndCharMetrics'
t_EndKernData =				r'EndKernData'
t_EndKernPairs =			r'EndKernPairs'

t_SemiColon =				r';'


def t_StartFontMetrics(t):
	r'StartFontMetrics[^\r\n]*'

	t.value = t.value[len("StartFontMetrics"):]
	if len(t.value):
		t.value = intorfloat(t.value)
	else:
		t.value = None
	return t

def t_StartCharMetrics(t):
	r'StartCharMetrics[^\r\n]*'

	t.value = t.value[len("StartCharMetrics"):]
	if len(t.value):
		t.value = intorfloat(t.value)
	else:
		t.value = None
	return t

def t_StartKernData(t):
	r'StartKernData[^\r\n]*'

	t.value = t.value[len("StartKernData"):]
	if len(t.value):
		t.value = intorfloat(t.value)
	else:
		t.value = None
	return t

def t_StartKernPairs(t):
	r'StartKernPairs[^\r\n]*'

	t.value = t.value[len("StartKernPairs"):]
	if len(t.value):
		t.value = intorfloat(t.value)
	else:
		t.value = None
	return t

def t_COMMENT(t):
	r'Comment [^\r\n]+'

	t.value = t.value[len("Comment "):]
	return t

def t_FontName(t):
	r'FontName [^\r\n]+'

	t.value = t.value[len("FontName "):]
	return t

def t_FullName(t):
	r'FullName [^\r\n]+'

	t.value = t.value[len("FullName "):]
	return t

def t_FamilyName(t):
	r'FamilyName [^\r\n]+'

	t.value = t.value[len("FamilyName "):]
	return t

def t_Weight(t):
	r'Weight [^\r\n]+'

	t.value = t.value[len("Weight "):]
	return t

def t_ItalicAngle(t):
	r'ItalicAngle [^\r\n]+'

	t.value = t.value[len("ItalicAngle "):]
	t.value = intorfloat(t.value)
	return t

def t_IsFixedPitch(t):
	r'IsFixedPitch [^\r\n]+'

	t.value = t.value[len("IsFixedPitch "):]
	t.value = bool(t.value)
	return t

def t_CharacterSet(t):
	r'CharacterSet [^\r\n]+'

	t.value = t.value[len("CharacterSet "):]
	return t

def t_FontBBox(t):
	r'FontBBox [^\r\n]+'

	t.value = t.value[len("FontBBox "):]
	parts = t.value.strip()
	parts = parts.split(' ')
	parts = [p.strip() for p in parts]
	parts = [int(p) for p in parts]
	t.value = parts

	return t

def t_UnderlinePosition(t):
	r'UnderlinePosition [^\r\n]+'

	t.value = t.value[len("UnderlinePosition "):]
	t.value = intorfloat(t.value)
	return t

def t_UnderlineThickness(t):
	r'UnderlineThickness [^\r\n]+'

	t.value = t.value[len("UnderlineThickness "):]
	t.value = intorfloat(t.value)
	return t

def t_Version(t):
	r'Version [^\r\n]+'

	t.value = t.value[len("Version "):]
	t.value = intorfloat(t.value)
	return t

def t_Notice(t):
	r'Notice [^\r\n]+'

	t.value = t.value[len("Notice "):]
	return t

def t_EncodingScheme(t):
	r'EncodingScheme [^\r\n]+'

	t.value = t.value[len("EncodingScheme "):]
	return t

def t_CapHeight(t):
	r'CapHeight [^\r\n]+'

	t.value = t.value[len("CapHeight "):]
	t.value = intorfloat(t.value)
	return t

def t_XHeight(t):
	r'XHeight [^\r\n]+'

	t.value = t.value[len("XHeight "):]
	t.value = intorfloat(t.value)
	return t

def t_Ascender(t):
	r'Ascender [^\r\n]+'

	t.value = t.value[len("Ascender "):]
	t.value = intorfloat(t.value)
	return t

def t_Descender(t):
	r'Descender [^\r\n]+'

	t.value = t.value[len("Descender "):]
	t.value = intorfloat(t.value)
	return t

def t_StdHW(t):
	r'StdHW [^\r\n]+'

	t.value = t.value[len("StdHW "):]
	t.value = intorfloat(t.value)
	return t

def t_StdVW(t):
	r'StdVW [^\r\n]+'

	t.value = t.value[len("StdVW "):]
	t.value = intorfloat(t.value)
	return t


def t_C(t):
	r'C [^\;]+'

	t.value = t.value[len("C "):]
	t.value = intorfloat(t.value)
	return t

def t_CH(t):
	r'CH [^;]+'

	t.value = t.value[len("CH "):]
	t.value = intorfloat(t.value)
	return t

def t_WX(t):
	r'WX [^;]+'

	t.value = t.value[len("WX "):]
	t.value = intorfloat(t.value)
	return t

def t_N(t):
	r'N [^;]+'

	t.value = t.value[len("N "):].strip()
	return t

def t_B(t):
	r'B [^;]+'

	t.value = t.value[len("B "):]
	parts = t.value.strip()
	parts = parts.split(' ')
	parts = [p.strip() for p in parts]
	parts = [int(p) for p in parts]
	t.value = parts

	return t

def t_L(t):
	r'L [^;]+'

	t.value = t.value[len("L "):]
	parts = t.value.strip()
	parts = parts.split(' ')
	parts = [p.strip() for p in parts]
	t.value = parts

	return t

def t_KPX(t):
	r'KPX [^\r\n]+'

	t.value = t.value[len("KPX "):]
	parts = t.value.strip()
	parts = parts.split(' ')
	parts = [p.strip() for p in parts]
	parts[2] = int(parts[2])
	t.value = ( (parts[0],parts[1]), parts[2] )

	return t



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

def TokenizeString(dat):
	tokens = []

	lexer.input(dat)

	tokcnt = 0
	while True:
		tok = lexer.token()
		#print(tok)
		if not tok: break

		tokens.append(tok)

	return tokens


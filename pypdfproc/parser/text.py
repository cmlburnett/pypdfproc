"""
Text stream parser of content streams that contain the rendering instructions for text and graphics
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
	'HEXSTRING',

	'NAME',
	'WS',

	# -------------------------------------------------------------------------------
	# -------------------------------------------------------------------------------
	# Text stream tokens
	# -------------------------------------------------------------------------------
	# -------------------------------------------------------------------------------

	'BT',
	'ET',

	'Tc',
	'Tw',
	'Tz',
	'TL',
	'Tf',
	'Tr',
	'Ts',

	'Tk',

	'Td',
	'TD',
	'Tm',

	'Tstar',
	'TstarTj',
	'TwTcTstarTj',
	'Tj',
	'TJ',

	# Color space
	'CS',
	'cs',
	'SCN',
	'SC',
	'scn',
	'sc',
	'G',
	'g',
	'RG',
	'rg',
	'K',
	'k',

	'MP',
	'DP',
	'BMC',
	'BDC',
	'EMC',

	# -------------------------------------------------------------------------------
	# -------------------------------------------------------------------------------
	# Graphic stream tokens
	# -------------------------------------------------------------------------------
	# -------------------------------------------------------------------------------

	'q',
	'Q',
	'cm',
	'w',
	'j',
	'J',
	'M',
	'd',
	'ri',
	'i',
	'gs',

	'm',
	'l',
	'c',
	'v',
	'y',
	'h',
	're',

	'S',
	's',
	'f',
	'F',
	'fstar',
	'B',
	'Bstar',
	'b',
	'bstar',
	'n',

	'W',
	'Wstar',


	'Do',
)

t_DICT_START =	r'\<\<'
t_DICT_END =	r'\>\>'
t_ARR_START =	r'\['
t_ARR_END =		r'\]'
t_LIT_START =	r'\('
t_LIT_END =		r'\)'

t_BT =		r'BT' # Begin text object (5.3; pg 405)
t_ET =		r'ET' # End text object (5.3; pg 405)

t_Tc =		r'Tc' # Character space (5.2.1)
t_Tw =		r'Tw' # Word space (5.2.2)
t_Tz =		r'Tz' # Scale (5.2.3)
t_TL =		r'TL' # Leading (5.2.4)
t_Tf =		r'Tf' # Font size
t_Tr =		r'Tr' # Render
t_Ts =		r'Ts' # Rise (5.2.6)

t_Tk =		r'Tk' # Knockout (5.2.7)

t_Td =		r'Td' # Text positioning (5.3.1; pg 406)
t_TD =		r'TD' # Text positioning (5.3.1; pg 406)
t_Tm =		r'Tm' # Text transformation matrix (5.3.1; pg 406)

t_Tstar =	r'T\*' # Text showing operations (5.3.2)
t_TstarTj =	r'\''  # Text showing operations (5.3.2)
t_TwTcTstarTj =	r'"'   # Text showing operations (5.3.2)
t_Tj =		r'Tj'  # Text showing operations (5.3.2)
t_TJ =		r'TJ'  # Text showing operations (5.3.2)

t_CS =		r'CS' # Set current color space for stroking (4.5.7; pg 287)
t_cs =		r'cs' # Set current color space for non-stroking (4.5.7; pg 287)
t_SC =		r'SC' # Set color used for stroking (4.5.7; pg 287)
t_sc =		r'sc' # Set color used for non-stroking (4.5.7; pg 287)
t_SCN =		r'SCN'# Set color/pattern/separation/deviceN/ICCBased used for stroking (4.5.7; pg 288)
t_scn =		r'scn'# Set color/pattern/separation/deviceN/ICCBased used for non-stroking (4.5.7; pg 288)
t_G =		r'G'  # Set colorspace to gray and set gray level for stroking (4.5.7; pg 288)
t_g =		r'g'  # Set colorspace to gray and set gray level for non-stroking (4.5.7; pg 288)
t_RG =		r'RG' # Set colorspace to RBG and set RGB level for stroking (4.5.7; pg 288)
t_rg =		r'rg' # Set colorspace to RBG and set RGB level for non-stroking (4.5.7; pg 288)
t_K =		r'K'  # Set colorspace to CMYK and set CMYK level for stroking (4.5.7; pg 288)
t_k =		r'k'  # Set colorspace to CMYK and set CMYK level for non-stroking (4.5.7; pg 288)

t_MP =		r'MP' # Marked content point (10.5; pg 850)
t_DP =		r'DP' # Marked content point with associated properites (10.5; pg 850)
t_BMC =		r'BMC'# Begin marked content (10.5; pg 850)
t_BDC =		r'BDC'# Begin marked content with associated properties (10.5; pg 850); end with EMC
t_EMC =		r'EMC'# End marked content (10.5; pg 850); begin with BMC or BDC


t_q =		r'q' # Save current state (4.3.3; pg 219)
t_Q =		r'Q' # Restore current state (4.3.3; pg 219)
t_cm =		r'cm'# Modify current transformation matrix (4.3.3; pg 219)
t_w =		r'w' # Line width (4.3.3; pg 219)
t_j =		r'j' # Line cap style (4.3.3; pg 219)
t_J =		r'J' # Line join style (4.3.3; pg 219)
t_M =		r'M' # Miter limit (4.3.3; pg 219)
t_d =		r'd' # Dash pattern (4.3.3; pg 219)
t_ri =		r'ri'# Rendering intent (4.3.3; pg 219)
t_i =		r'i' # Flatness tolerance (4.3.3; pg 219)
t_gs =		r'gs'# Graphic state parameters (4.3.3; pg 219)

t_m =		r'm' # Begin new subpath (4.4.1; pg 226)
t_l =		r'l' # Append straight light (4.4.1; pg 226)
t_c =		r'c' # Append cubic bezier based on three points (4.4.1; pg 226)
t_v =		r'v' # Append cubic bezier given second control point and final point (4.4.1; pg 226)
t_y =		r'y' # Append cubic bezier given first control point and final point (4.4.1; pg 226)
t_h =		r'h' # Close current subpath using a straight line (4.4.1; pg 227)
t_re =		r're'# Append rectangle (4.4.1; pg 227)

t_s =		r's' # Close path (h) and stroke the path (4.4.2; pg 230)
t_S =		r'S' # Stroke the path (4.4.2; pg 230)
t_f =		r'f' # Fill path using non-zero winding rule (4.4.2; pg 230)
t_F =		r'F' # Equivalent to 'f'
t_fstar =	r'f\*'# Fill path using even-odd rule (4.4.2; pg 230)
t_B =		r'B'  # Fill and stroke path using non-zero winding rule (4.4.2; pg 230)
t_Bstar =	r'B\*'# Fill and stroke path using even-odd rule (4.4.2; pg 230)
t_b =		r'b'  # Close path (h) and stroke the path (B) using non-zero winding rule (4.4.2; pg 230)
t_bstar =	r'b\*'# Close path (h) and stroke the path (B) using even-odd rule (4.4.2; pg 230)
t_n =		r'n'  # End the path object with filling or stroking it (4.4.2; pg 230)

t_W =		r'W'  # Modify current clipping path by intersecting with current path using non-zero winding rule (4.4.3; pg 235)
t_Wstar =	r'W\*'# Modify current clipping path by intersecting with current path using even-odd rule (4.4.3; pg 235)


t_Do =		r'Do' # Paint specified XObject (Table 4.37; pg 332)

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

	t.lexer.lineno += len([c for c in t.value if c=='\n'])

	# Ignore these tokens by returning None
	return None

# Ignore nothing, whitespace is handled above
t_ignore = ''

# Initiate lexer
lexer = plylex.lex()

class PDFToken(object):
	"""
	Reimplementation of the LexToken.
	Primary purpose of this is separation of levels as post-fix is converted to pre-fix notation (essentially).
	"""

	def __init__(self, type, value, lineno, lexpos, page=None):
		self.type = type
		self.value = value
		self.lineno = lineno
		self.lexpos = lexpos
		self.page = page

	@staticmethod
	def FromLexToken(tok):
		if type(tok) != list:
			return PDFToken(tok.type, tok.value, tok.lineno, tok.lexpos)

		return [PDFToken(t.type, t.value, t.lineno, t.lexpos) for t in tok]

	def __str__(self):
		#return "PDFToken(%s,%r,%d,%d)" % (self.type, self.value, self.lineno, self.lexpos)
		return "{%s,%r}" % (self.type, self.value)
	def __repr__(self):
		return str(self)


def TokenizeString(txt, residual=None):
	lexer.input(txt)

	tokens = []
	tokcnt = 0

	# Start the tokens list with the residual
	if type(residual) == list:
		tokens = tokens + residual
	elif residual == None:
		pass
	else:
		raise TypeError("Residual expected to be a list, got %s" % type(residual))

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

	# I'm sure they had a good reason, but the tokens are "postfixed" in the sense that the operator comes after the operand
	# which makes linear parsing one step harder
	# So flip it around so all the tokens (operands) for a given operator are the token value
	return TokensPostfixToPrefix(tokens)

def TokensPostfixToPrefix(tokens):
	ret = []

	lastidx = -1
	for i in range(len(tokens)):
		t = tokens[i]

		# 0 operands
		if t.type in ('q', 'Q', 'h', 'S', 's', 'F', 'f', 'fstar', 'B', 'B*', 'b', 'b*', 'n', 'W', 'Wstar', 'BT', 'ET', 'Tstar', 'EMC'):
			#print('0', t.type)
			# Pg 219
			# q
			# Q
			# Pg 227
			# h
			# Pg 230
			# S
			# s
			# F
			# f
			# f*
			# B
			# B*
			# b
			# b*
			# n
			# Pg 235
			# W
			# W*
			# Pg 405
			# BT
			# ET
			# Pg 406
			# T*
			# Pg 850
			# EMC
			ret.append( PDFToken.FromLexToken(t) )

			if lastidx != i-1:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i, tokens[i]))

			# Update last index used
			lastidx = i

		# 1 operand
		elif t.type in ('w', 'J', 'j', 'M', 'ri', 'i', 'gs', 'CS', 'cs', 'G', 'g', 'Do', 'Tc', 'Tw', 'Tz', 'TL', 'Tr', 'Ts', 'Tj', 'TstarTj', 'MP', 'BMC'):
			#print('1', t.type)
			# Pg 219
			# number w
			# number J
			# number j
			# number M
			# number ri
			# number i
			# dictName gs
			# Pg 287
			# name CS
			# name cs
			# Pg 288
			# gray G
			# gray g
			# Pg 332
			# name Do
			# Pg 398
			# number Tc
			# number Tw
			# number Tz
			# number TL
			# number Tr
			# number Ts
			# Pg 407
			# string Tj
			# string '
			# Pg 850
			# tag MP
			# tag BMC
			ret.append( PDFToken(t.type, tuple([PDFToken.FromLexToken(tokens[i-1])]), tokens[i-1].lineno, tokens[i-1].lexpos) )

			if lastidx != i-2:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i-1, tokens[i-1]))

			# Update last index used
			lastidx = i

		# 2 operands
		elif t.type in ('m', 'l', 'Tf', 'Td', 'TD', 'DP', 'BDC'):
			#print('2', t.type)
			# Pg 226
			# x y m
			# x y l
			# Pg 398
			# font size Tf
			# Pg 406
			# tx tx Td
			# tx tx TD
			# tag properites DP
			# tag properites BDC

			normalCheck = True

			if t.type == 'BDC' and tokens[i-1].type == 'DICT_END':
				j = i-1
				while j > 0:
					if tokens[j].type == 'DICT_START':
						# Assume something like "NAME <<.....>> BDC" so the index of DICT_START is j and j-1 is the NAME, so
						# the tokens under BDC should be (NAME, DICT)

						# Collapse the dictionary into a single DICT token
						#      tokens[j-1] == NAME
						#        tokens[j] == DICT_START
						#        tokens[i] == BDC
						#      tokens[i-1] == DICT_END
						#  tokens[j+1:i-1] == all the tokens between DICT_START and DICT_END without including either
						dict_tok = PDFToken('DICT', tokens[j+1:i-1], tokens[j+1].lineno, tokens[j+1].lexpos)

						ret.append( PDFToken(t.type, tuple([PDFToken.FromLexToken(tokens[j-1]), dict_tok]), tokens[j-1].lineno, tokens[j-1].lexpos) )

						if lastidx != j-2:
							raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], j-2, tokens[j-2]))

						# Not a normal length check
						normalCheck = False
						lastidx = j-1
						break
					else:
						j -= 1
			else:
				ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[i-2:i])), tokens[i-2].lineno, tokens[i-2].lexpos) )

			if lastidx != i-3 and normalCheck:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i-2, tokens[i-2]))

			# Update last index used
			lastidx = i

		# 3 operands
		elif t.type in ('RG', 'rg', 'TwTcTstarTj'):
			#print('3', t.type)
			# Pg 288
			# r g b RG
			# r g b rg
			# Pg 407
			# aw ac string "
			ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[i-3:i])), tokens[i-3].lineno, tokens[i-3].lexpos) )

			if lastidx != i-4:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i-3, tokens[i-3]))

			# Update last index used
			lastidx = i

		# 4 operands
		elif t.type in ('v', 'y', 're', 'K', 'k'):
			#print('4', t.type)
			# Pg 226
			# x2 y2 x3 y3 v
			# x1 y1 x3 y3 y
			# x y w h re
			# Pg 288
			# c m y k K
			# c m y k k
			ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[i-4:i])), tokens[i-4].lineno, tokens[i-4].lexpos) )

			if lastidx != i-5:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i-4, tokens[i-4]))

			# Update last index used
			lastidx = i


		# 6 operands
		elif t.type in ('cm', 'c', 'Tm'):
			#print('6', t.type)
			# Pg 219
			# a b c d e f cm
			# Pg 226
			# x1 y1 x2 y2 x3 y3 c
			# Pg 406
			# a b c d e f Tm
			ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[i-6:i])), tokens[i-6].lineno, tokens[i-6].lexpos) )

			if lastidx != i-7:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], i-6, tokens[i-6]))

			# Update last index used
			lastidx = i

		# 1 operand that's an array
		elif t.type in ('TJ'):
			#print('1 ARR', t.type)
			# Pg 408
			# ARR_START ... ARR_END TJ
			j = i-1
			while j > 0:
				if tokens[j].type == 'ARR_START':
					ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[j+1:i-1])), tokens[j].lineno, tokens[j].lexpos) )
					break
				else:
					j -= 1

			if lastidx != j-1:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], j-1, tokens[j-1]))

			# Update last index used
			lastidx = i

		# 2 operands, the first is an array
		elif t.type in ('d'):
			#print('2 d', t.type)
			j = i-2
			while j > 0:
				if tokens[j].type == 'ARR_START':
					ret.append( PDFToken(t.type, tuple( [PDFToken.FromLexToken(tokens[j+1:i-2]), PDFToken.FromLexToken(tokens[i-1])] ), tokens[j].lineno, tokens[j].lexpos) )
					break
				else:
					j -= 1

			if lastidx != j-1:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], j-1, tokens[j-1]))

			# Update last index used
			lastidx = i

		# Variable number of operands
		elif t.type in ('SC', 'sc'):
			#print('var num', t.type)
			# Pg 287
			# c1 SC			% if color space is currently gray or indexed
			# c1 c2 c3 SC		% if color space is currently RGB or lab
			# c1 c2 c3 c4 SC	% if color space is currently CMYK
			j = i-1
			while j > 0:
				if tokens[j].type in ('INT', 'FLOAT'):
					j -= 1
				else:
					j += 1
					break

			ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[j:i])), tokens[j].lineno, tokens[j].lexpos) )

			if lastidx != j-1:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], j-1, tokens[j-1]))

			# Update last index used
			lastidx = i

		# Variable number of operands with optional string
		elif t.type in ('SCN', 'scn'):
			#print('var num + str', t.type)
			# Pg 287
			# c1 SC			% if color space is currently gray or indexed
			# c1 c2 c3 SC		% if color space is currently RGB or lab
			# c1 c2 c3 c4 SC	% if color space is currently CMYK
			# c1 name SC		% if color space is currently gray or indexed
			# c1 c2 c3 name SC	% if color space is currently RGB or lab
			# c1 c2 c3 c4 name SC	% if color space is currently CMYK
			j = i-1
			while j > 0:
				if tokens[j].type in ('INT', 'FLOAT', 'LIT'):
					j -= 1
				else:
					j += 1
					break

			ret.append( PDFToken(t.type, tuple(PDFToken.FromLexToken(tokens[j:i])), tokens[j].lineno, tokens[j].lexpos) )

			if lastidx != j-1:
				raise ValueError("Last token used %d (%s) skipped over tokens until %d (%s)" % (lastidx, tokens[lastidx], j-1, tokens[j-1]))

			# Update last index used
			lastidx = i

		elif t.type in ('INT', 'FLOAT', 'ARR_START', 'ARR_END', 'DICT_START', 'DICT_END', 'NAME', 'LIT', 'HEXSTRING'):
			pass

		else:
			raise Exception("Unrecognized token type '%s' at %d" % (tokens[i].type, i))

	return {'tokens': ret, 'residual': tokens[(lastidx+1):]}


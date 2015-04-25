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
t_ARR_END =		r'\]'
t_LIT_START =	r'\('
t_LIT_END =		r'\)'

# Literal strings to match
t_true =		r'true'
t_false =		r'false'

t_obj =			r'obj'
t_endobj =		r'endobj'
t_stream =		r'stream'
t_endstream =	r'endstream'
t_trailer =		r'trailer'
t_xref =		r'xref'
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



def TokenizeString(dat, pos=None, stoptoken=None):
	"""
	NB: if @dat is a fixed size block of text then any step here may run into
	a "IndexError: string index out of range" exception being thrown. It may be very puzzling since
	the document should be well-formed, but ensure that this isn't the problem first before hunting
	down other explanations.
	"""

	tokens = []

	lexer.input(dat)
	# lexer assumes it always starts at zero, which is wrong when parsing random objects in PDF files
	if pos != None:
		lexer.lexpos = pos

	# Keep track of the last length for when reading streams
	# [0] = saw /Length
	# [1] = INT following /Length
	streamlength = [False, 0]

	tokcnt = 0
	while True:
		tok = lexer.token()
		print(tok)
		if not tok: break

		# Found a name that is length, so indicate the key was seen
		if tok.type == 'NAME':
			if tok.value == 'Length':
				streamlength[0] = True
				streamlength[1] = -1

		# Found an integer and it's after a /Length name
		if tok.type == 'INT' and streamlength[0]:
			streamlength[1] = tok.value

			# No longer saw the length since the value is recorded
			streamlength[0] = False

		# End of dictionary means /Length was no longer seen (if it ever was)
		if tok.type == 'DICT_END':
			streamlength[0] = False




		# Special handling by yanking out streamlength[1] bytes from the stream token
		if tok.type == 'stream':
			if streamlength[1] < 0:
				tok.value = None
				continue

			# Leading CRLF
			if lexer.lexdata[lexer.lexpos] == '\r':
				lexer.lexpos += 1
			if lexer.lexdata[lexer.lexpos] == '\n':
				lexer.lexpos += 1

			# Yank out stream data
			tok.value = lexer.lexdata[ lexer.lexpos:(lexer.lexpos + streamlength[1]) ]

			# Increment position
			lexer.lexpos += streamlength[1]

			# Trailing CRLF
			if lexer.lexdata[lexer.lexpos] == '\r':
				lexer.lexpos += 1
			if lexer.lexdata[lexer.lexpos] == '\n':
				lexer.lexpos += 1
		if tok.type == 'endstream':
			streamlength[1] = -1


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

		# Record token (after potentially modifying it above)
		tokens.append(tok)

		# Count token
		tokcnt += 1

		if type(stoptoken) == str:
			if tok.type == stoptoken:
				break
		else:
			pass

	return tokens

# Provide function in this file to shortcut the class static method
def ConsolidateTokens(tokens):
	"""
	Consolidate tokens as logically appropriate for the tokens given (dictionary, array, etc.).
	"""
	return ConsolidateTokensClass.ConsolidateTokens(tokens)

class ConsolidateTokensClass:
	"""
	Put these in a class for organization purposes.
	"""

	@staticmethod
	def ConsolidateTokens(tokens):
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Xref)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Indirect)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Array)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Dictionary)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Stream)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Object)
		tokens = TokenIterator(tokens, 0, len(tokens), ConsolidateTokensClass.Trailer)

		return tokens

	@staticmethod
	def Xref(tokens, startpos, endpos):
		if tokens[startpos].type == 'xref':

			if tokens[startpos+1].type != 'INT':	raise Exception('Expected INT after xref start')
			if tokens[startpos+2].type != 'INT':	raise Exception('Expected two INTs after xref start')

			firstobj = tokens[startpos+1].value
			numobjs = tokens[startpos+2].value

			# index of first 3-tuple of xref data
			firstxref = startpos+3

			objs = []
			cnt = 0
			for i in range(firstxref, firstxref + numobjs*3, 3):
				# Validate data
				if tokens[i].type != 'INT':	raise Exception('Expected INT for xref row %d, found %s' % (cnt, tokens[i].type))
				if tokens[i+1].type != 'INT':	raise Exception('Expected two INTs for xref row %d, found %s' % (cnt, tokens[i+1].type))
				if tokens[i+2].type not in ('xref_inuse','xref_free'):
								raise Exception('Expected xref_free or xref_inuse for xref row %d, found %s' % (cnt, tokens[i+2].type))

				# Add new object reference
				# Format: (object number, offset, generation, 'n'=inuse or 'f'=free)
				objs.append( (firstobj+cnt, tokens[i].value, tokens[i+1].value, tokens[i+2].value) )


				cnt += 1

			# Skip ahead of last xref row less one because of the outer loop incrementing by one to the first token after the whole xref jazz
			i += 3-1

			# Replace xref token's value with the array of object xrefs
			tokens[startpos].value = objs

			# Replace the entire set of objects (xref and all of it's rows) with a single xref object and start with the object right after the last xref row token
			return ([tokens[startpos]], i)

		# Not an indirect object reference, so return current token
		else:
			return ([tokens[startpos]], startpos)

	@staticmethod
	def Indirect(tokens, startpos, endpos):
		if startpos+2 < endpos and tokens[startpos].type == 'INT' and tokens[startpos+1].type == 'INT' and tokens[startpos+2].type == 'indirect':
			tok = plylex.LexToken()
			tok.type = 'INDIRECT'
			tok.value = (tokens[startpos].value, tokens[startpos+1].value, tokens[startpos+2].value)
			tok.lineno = tokens[startpos].lineno
			tok.lexpos = tokens[startpos].lexpos

			return ([tok], startpos+2)

		# Not an indirect object reference, so return current token
		else:
			return ([tokens[startpos]], startpos)

	@staticmethod
	def Array(tokens, startpos, endpos):
		if tokens[startpos].type != 'ARR_START':
			# No chance for this token
			return ([tokens[startpos]], startpos)

		cnt = 0
		for i in range(startpos, endpos):
			if tokens[i].type == 'ARR_START':
				cnt += 1
			elif tokens[i].type == 'ARR_END':
				cnt -= 1

			if cnt == 0:
				break

		arrval = tokens[startpos+1:i]
		# Run through array and make sure every element is processed
		arrval = ConsolidateTokens(arrval)

		#NB: tokens[i].type == 'ARR_END'

		tok = plylex.LexToken()
		tok.type = 'ARR'
		tok.value = arrval
		tok.lineno = tokens[startpos].lineno
		tok.lexpos = tokens[startpos].lexpos

		# Consolidate the entire array into the one token and start at the ARR_END token (at tokens[i])
		return ([tok], i)

	@staticmethod
	def Dictionary(tokens, startpos, endpos):
		if tokens[startpos].type != 'DICT_START':
			return ([tokens[startpos]], startpos)

		# Find the corresponding DICT_END of this DICT_START (at startpos)
		cnt = 0
		endidx = 0
		for i in range(startpos, endpos):
			if tokens[i].type == 'DICT_START':
				cnt += 1
			if tokens[i].type == 'DICT_END':
				cnt -= 1
				endidx = i

			if cnt == 0:
				break

		if cnt != 0:
			raise Exception("Did not find end of dictionary (startpos=%d, endpos=%d)" % (startpos,endpos))

		# Scoop out the appropriate tokens belonging to this dictionary
		toks = tokens[startpos:endidx+1]

		# Step through each key/value in the dictionary and call this function recursively so that
		# a dictionary of dictionaries (of dictionaries of....) nests appropriately
		nexttoks = []

		# Recursively consolidate a dictionary's entries
		i = 1
		while i < len(toks)-1:
			# Recurse
			(ret,x) = ConsolidateTokensClass.Dictionary(toks, i, len(toks)-1)

			# Add tokens to processed list
			nexttoks = nexttoks + ret

			# Go to next indicated token
			i = x + 1

		# Ensure dictionary size is appropriate
		#if len(nexttoks)%2 != 0:
		#	raise Exception("Dictionary has odd number of keys and values: %s", nexttoks)

		if len(nexttoks)%2 != 0:
			t = plylex.LexToken()
			t.type = 'NULL'
			t.value = None
			t.lineno = nexttoks[-1].lineno
			t.lexpos = nexttoks[-1].lexpos
			nexttoks.append(t)

		# Pair dictionary keys & values as tuples
		# (range steps by two's at the indices of the keys and nexttoks[i:i+2] is a 2-elemet list of key+value)
		finaltoks = [tuple(nexttoks[i:i+2]) for i in range(0,len(nexttoks),2)]


		# Assign list of 2-tuples of dictionary entries back to DICT_START token's value
		tokens[startpos].type = 'DICT'
		tokens[startpos].value = finaltoks

		# Return a single token of type DICT with value of the nested dictionary 2-tuples
		# Return the index of the DICT_END so that the outer loop steps to the token after the dictionary
		return ([tokens[startpos]], endidx)

	@staticmethod
	def Stream(tokens, startpos, endpos):
		if tokens[startpos].type == 'endstream':
			# Strip out endstream tokens
			return ([], startpos)
		else:
			return ([tokens[startpos]], startpos)

	@staticmethod
	def Object(tokens, startpos, endpos):
		# This is a little weird since this function is consolidating object tokens, but it starts with two INTs before the object
		# therefore, hit every INT and look two ahead for object type
		if startpos+2 >= endpos:				return ([tokens[startpos]], startpos)
		if tokens[startpos].type != 'INT':		return ([tokens[startpos]], startpos)
		if tokens[startpos+1].type != 'INT':	return ([tokens[startpos]], startpos)
		if tokens[startpos+2].type != 'obj':	return ([tokens[startpos]], startpos)

		# Find endobject
		for i in range(startpos+2, endpos):
			if tokens[i].type == 'endobj':
				break

		# Pull out object number and generation
		objnum = tokens[startpos].value
		gen = tokens[startpos+1].value

		# Pull out all the relevant tokens (exclude the obj and endobj tokens)
		toks = tokens[startpos+3:i]

		# Create new token
		tok = plylex.LexToken()
		tok.type = 'OBJECT'
		tok.value = (objnum, gen, toks)
		tok.lineno = tokens[startpos+2].lineno
		tok.lexpos = tokens[startpos+2].lexpos

		return ([tok], i)

	@staticmethod
	def Trailer(tokens, startpos, endpos):
		if tokens[startpos].type != 'trailer':	return ([tokens[startpos]], startpos)

		endidx = 0
		for i in range(startpos+1, endpos):
			if tokens[i].type == 'EOF':
				endidx = i
				break

		if endidx == 0:
			raise Exception('Could not find EOF for given trailer')

		tok = plylex.LexToken()
		tok.type = 'TRAILER'
		tok.value = tokens[startpos+1:endidx+1]
		tok.lineno = tokens[startpos].lineno
		tok.lexpos = tokens[startpos].lexpos

		return ([tok], endidx)

def TokenIterator(tokens, startpos, endpos, func):
	"""
	Simple method that iterates through @tokens from starting index @startpos
	through index @endpos and calls the function @func on each item of @tokens.

	The return of @func is a 2-tuple of (new tokens, last index processed).
	This means that in place of the token passed to @func, insert the tokens
	in return[0] and skip ahead to the index of return[1]. When skipping ahead
	the index returned should be of the *LAST* item processed as this function
	will increment the counter for the next iteration.

	Essentially, this is a filter() method that calls @func on each entry with the
	ability to collapse/expand the resultant array and by skipping items in @tokens.

	Notably, this is useful to taken one or more items in @tokens and collapse
	into a single token, or to take one item in @tokens and expand it into multiple items.

	If @func does nothing with the supplied token, then return the token and the same starting
	index. I.e., lambda tokens,startpos,endpos: ([tokens[startpos]], startpos)
	"""
	ret = []

	i = startpos
	while i < endpos:
		tok = tokens[i]

		# Call function on token
		z,ii = func(tokens, i, endpos)

		# Add returned tokens to the resultant list
		ret = ret + z
		# Jump to specified end index (which is incremented next)
		i = ii

		# Go to next token
		i += 1

	return ret


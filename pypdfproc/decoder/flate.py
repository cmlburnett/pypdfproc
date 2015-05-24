"""
Implements the deflate decoder.
"""

from itertools import product as ITERproduct
import zlib

def FlateDecode(data, parms):
	"""
	FlateDecode is primarily based around zlib compression.
	However, predictors can be used to make the data more uniform prior to compression
	and so this must be undone.
	Unfortunately, zlib does not handle this stuff since it is out of its scope.
	"""

	# Decompress data before un-doing the predictor
	uncomp = zlib.decompress(data)

	# Determine predictor (required parameter, even though it's optional in PDF spec)
	if 'Predictor' not in parms:
		raise KeyError("Expected 'Predictor' key in parameters. Required in this implementation. HINT: {'Predictor': 0} is acceptable argument if, indeed, no predictor is used.")
	pred = parms['Predictor']

	if pred == 0:
		# No predictor, nothing to do so just return decompressed data
		return uncomp
	elif pred == 2:			raise NotImplementedError("TIFF predictor 2 not implemented yet")
	elif pred == 10:		raise NotImplementedError("PNG None predictor (10) not implemented yet")
	elif pred == 11:		raise NotImplementedError("PNG Sub predictor (11) not implemented yet")
	elif pred == 12:		return PNG_Up(uncomp, parms)
	elif pred == 13:		raise NotImplementedError("PNG Avg predictor (13) not implemented yet")
	elif pred == 14:		raise NotImplementedError("PNG Paeth predictor (14) not implemented yet")
	elif pred == 15:		raise NotImplementedError("PNG Optimum predictor (15) not implemented yet")

	else:
		raise NotImplementedError("Flate predictor %d unknonw and cannot be implemented" % pred)

def PNG_Up(data, parms):
	"""
	This predictor functions by dicing the data into rows (essentially making a 2-D 'image') and then using
	the current data value plus the 'up' row value to come up with the new value. This method is very good
	for columnar data where the data in the columns don't change.

	Example:

	Input:
	 2  3  4
	 5  0  1

	Output:
	 2  3  4
	 7  3  5

	The second row [5 0 1] is added to the previous output row [2 3 4] to get [7 3 5], the new output row.

	Now, it would be entirely feasible to dice the bytes into a list of lists and iterate through objects.
	Instead, I chose to get tricky with the indices and iterate over a static bytes array.
	The former way sounds "cleaner" from an object perspective, but the index ninjitsu is just as tricky, if not trickier.

	However, the data actually as an additional column that indicates the predictor algorithm (2 in this case).
	So, really, the data looks like this:
	 2  2  3  4
	 2  5  0  1

	This complicates the indexing.
	"""

	if 'Columns' not in parms:
		raise ValueError("Cannot do PNG Up predictor without knowing how many columns to use")

	# This is the number of columns that the predictor iterates
	# Which is actually one less than the columns that are actually in @data due to the predictor algorithm column (hence why you see col+1 below)
	col = parms['Columns']

	if len(data) % (col+1) != 0:
		raise ValueError("Expected a multiple of col+1 bytes (%d) but got %d bytes (%d remainder)" % (col+1, len(data), len(data) % (col+1)))

	# Return data is the size of the original data plus initial zero padding to account for the predictor needing a row of zeros
	ret = bytearray(len(data))

	# itertools.product takes two ranges and comes up with a 2-tuple of the range values
	# Essentially, fully permutes two ranges
	# Used to iterate through the data based on row,column which is then converted to indices
	#
	# Using the above example, this will iterate over [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
	# Note that these row,column tuples correspond to the geometry of @data
	# (r,c) tuples to index is easy math: row*columns + column
	# Of course, "columns" is confusing because @data and @ret have different numbers of columns (col+1 and col, respectively)
	#
	# Regardless of how messy it looks, it is necessary to iterate over the bytes in @data which means (r,c) tuples are not over @ret
	for r,c in list(ITERproduct(range(0,int(len(data)/(col+1))), range(0,col+1))):
		# Current index in @data that is being used for calculation
		# First byte in a column is the predictor code (0x02 in this case), so have to add 1 to the column value
		idx = r*(col+1)+c

		# Make sure predictor code doesn't change
		if c == 0:
			if r > 0 and data[idx] != 2:
				raise ValueError("Row %d predictor value expected to be 2 but was %d: indicates change in predictor algorithm" % (r, data[idx]))

			# Ignore this value once it's been checked
			continue

		# Index in the previous row in @ret where the previous value is read from; output has no predictor column so -1 from column value @c
		previdx = (r-1)*col+(c-1)
		# Index in the current row in @ret where the predicted value is written to; output has no predictor column so -1 from column value @c
		nowidx = r*col+(c-1)

		# Current output = current data value + previous output value
		# Mode 256 since this only supports addition (i.e., have to add 255 to essentially subtract 1)
		ret[nowidx] = (data[idx] + ret[previdx]) % 256

		#print(["%2d"%r,"%2d"%c, "%2d"%idx, "%2d"%nowidx, "%2d"%previdx, "%3d"%data[idx], "%3d"%ret[previdx], "%3d"%ret[nowidx]])

	# Convert to bytes
	return bytes(ret)


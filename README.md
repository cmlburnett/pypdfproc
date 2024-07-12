pypdfproc -- A pure python PDF processor

This library was a learning experience in parsing PDF files. There are better (more polished) libraries out there but this one is mine.
It can read PDF, read the vector graphics instructions, parse out text, etc.
Uses the PLY lexer in python to tokenize the PDF stream.
Includes parsers for PDF files, text/graphic streams, font metrics, character maps, and the compact file font.

-----------------
PDF file structure (brief)

The file starts with "%PDF-X.Y" where X.Y is version.
The file ends with %%EOF

Prior to the %%EOF can be a "startxref" line follow by an integer that is a byte offset for the XREF table that allows for quick jump to objects.

PDF contains sections that start with "X Y obj" and end with "endobj" where X is the object number and Y is the generation.
Each section contains a dictionary of parameters between << and >> and option "stream" to "endstream" of data.
Strings start with a forward slash.
Dictionary keys can have values of "X Y R" that points to other objects.
This forms a tree of objects that forms the hierarchy of the document and data.
The key /Type can indicat the object type (eg, /Catalog, /Page).
Dictionary values can also be literals: square brackets [] forms a array/list, angle brackets <<>> forms a dictionary, parentheses () forms a literal string, single angle brackets <> forms a hex string.
A stream can have no dictionary and just be data (eg, "1 0 obj\n255\nendobj")

Streams can be compressed and encrypted.
Common is the use of flate "/Filter /FlateDecode" to compress stream data.

There's an entire language for the text & vector graphics.

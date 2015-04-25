"""Installs pypdfproc using distutils

Run:
	python setup.py install

to install this package.
"""

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

from distutils.command.install import INSTALL_SCHEMES
from distutils.command.build_py import build_py
import sys
import re

###############################################################################
# arguments for the setup command
###############################################################################
name = "pypydfproc"
version = "1.0.0"
desc = "PDF processor"
long_desc = "Processes and updates PDF files specifically for journal articles and references"
classifiers = [
	"Intended Audience :: Developers",
	"Programming Language :: Python :: 3",
	"Programming Language :: Python :: 3.3",
]
author = "Colin M Burnett"
author_email = "cmlburnett@gmail.com"
url = "http://www.candysporks.org"
cp_license = "BSD"
packages = [
	"pypdfproc",
]
data_files = [
	('src', [,
	]),
	('src/parser', ['src/parser/pdf.py',
					'src/parser/text.py'
	]),
]
scripts = []

if sys.version_info >= (3, 0):
    required_python_version = '3.3'

###############################################################################
# end arguments for setup
###############################################################################

setup_params = dict(
	name=name,
	version=version,
	description=desc,
	long_description=long_desc,
	classifiers=classifiers,
	author=author,
	author_email=author_email,
	url=url,
	license=cp_license,
	packages=packages,
	data_files=data_files,
	scripts=scripts,
)

def main():
	if sys.version < required_python_version:
		s = "I'm sorry, but %s %s requires Python %s or later."
		print(s % (name, version, required_python_version))
		sys.exit(1)

	setup(**setup_params)


if __name__ == "__main__":
    main()


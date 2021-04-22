#
# Copyright (c) 2018 Antti Kantee <pooka@iki.fi>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#

import sys

class PilotError(Exception):
	pass

def checktype(type, cls):
	if not isinstance(type, cls):
		raise PilotError('invalid input type for ' + cls.__name__)

def checktypes(lst):
	for chk in lst:
		checktype(*chk)

def warn(msg, prepend=''):
	sys.stderr.write(prepend + 'WARNING: ' + msg)

def notice(msg, prepend=''):
	sys.stderr.write(prepend + '>> ' + msg)

# print first line with prefix and rest indented at prefixlen,
# split at whitespaces
def prettyprint_withsugarontop(prefix, prefixlen, thestr, strmaxlen, sep=None):
	res = []
	while len(thestr) > strmaxlen:
		# this produces off-by-one lengths in a number of
		# pathological corner cases.  not going to worry about it.
		v = thestr[:strmaxlen+1].rsplit(sep, 1)
		res.append(v[0])
		thestr = thestr[len(v[0]):].lstrip()
	res.append(thestr)

	fmtstr = '{:' + str(prefixlen) + '}{:}'
	for s in res:
		print(fmtstr.format(prefix, s))
		prefix = ''

def prtsep(char='='):
	print(char * 79)

# used to avoid "-0" prints
def pluszero(v):
	if abs(v) < 0.000001: v = 0.000001
	return v

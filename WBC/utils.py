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

def istype(type, cls):
	try:
		checktype(type, cls)
		return True
	except PilotError:
		return False

def istupletype(type, clss):
	try:
		checktype(type, tuple)
		checktype(type[0], clss[0])
		checktype(type[1], clss[1])
		return True
	except PilotError:
		return False

def warn(msg):
	sys.stderr.write('WARNING: ' + msg)

def notice(msg):
	sys.stderr.write('>> ' + msg)

def diagnosticflush():
	sys.stderr.write('\n')

# used to avoid "-0" prints
def pluszero(v):
	if abs(v) < 0.000001: v = 0.000001
	return v

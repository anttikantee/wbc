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

global wbcparams
wbcparams = {}

needparams = \
	[ 'units_output', 'strength_output', 'mash_efficiency',
	  'boiloff_perhour', 'mlt_loss', 'mlt_heatcapacity', 'mlt_heat']
optparams = \
	[ 'grain_absorption' ]
for x in needparams + optparams:
	wbcparams[x] = None

from Utils import PilotError, notice

import os, sys

def getparam(what):
	global wbcparams
	rv = wbcparams[what]
	return rv

# XXX: should actually parse the values properly and check that they make sense
floatparams = \
	[ 'mash_efficiency', 'boiloff_perhour', 'mlt_loss', 'mlt_heatcapacity',
	  'grain_absorption' ]
def setparam(what, value):
	global wbcparams
	if what not in wbcparams:
		raise PilotError('invalid config knob: ' + what)
	wbcparams[what] = value

def processparam(paramstr):
	ar = paramstr.split('=')
	if len(ar) != 2:
		raise PilotError('invalid sysparam: ' + paramstr)
	what = ar[0].strip()
	value = ar[1].strip()
	if what in floatparams:
		value = float(value)
	setparam(what, value)

def _process(f):
	for line in f:
		_processline(line, False)

def _processline(line, emptyerror):
	line = line.strip()
	if len(line) == 0 or line[0] == '#':
		if emptyerror:
			raise PilotError('empty parameter line')
		else:
			return
	processparam(line)

def processline(line):
	_processline(line, True)

def processdefaults():
	for pf in [os.path.expanduser('~/.wbcsysparams'), './.wbcsysparams']:
		try:
			f = open(pf, 'r')
			notice('Using "' + pf + '" for WBC system parameters\n')
			_process(f)
			f.close()
		except IOError:
			continue

def processfile(filename):
	with open(filename, 'r') as f:
		notice('Using "' + filename + '" for WBC system parameters\n')
		_process(f)

def checkset():
	for p in needparams:
		if getparam(p) is None:
			raise PilotError('missing system parameter for: ' + p)

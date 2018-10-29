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

from Utils import PilotError, notice
from Getparam import getparam

import Constants

def _getparam(what):
	rv = wbcparams[what]
	return rv

wbcparams = {}

def setparam(what, value):
	if what not in paramparsers:
		raise PilotError('invalid parameter: ' + what)
	rv = paramparsers[what](value)
	wbcparams[what] = rv

def processparam(paramstr):
	ar = paramstr.split('=')
	if len(ar) != 2:
		raise PilotError('invalid sysparam: ' + paramstr)
	what = ar[0].strip()
	value = ar[1].strip()
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
	import os
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
	for p in paramparsers:
		if p not in wbcparams:
			raise PilotError('missing system parameter for: ' + p)

# do some fancypants stuff to avoid having to type things multiple times.
# one makes my fingers hurt, the other makes my brain hurt #PoisonChosen
# beginning to appreciate cpp ...
def _addparam(key, value):
	def x(arg):
		try:
			return value(arg)
		except (PilotError, ValueError):
			raise PilotError('invalid value "' + str(arg)
			    + '" for "' + str(key) + '"')
        paramparsers[key] = x

def _currystring(strings):
	def x(input):
		if input in strings:
			return input
		else:
			raise PilotError('invalid input')
	return x

def _curryratio(p1, p2):
	def x(input):
		return Parse.ratio(input, p1, p2)
	return x

def _parsefloat(input):
	return float(input)

import Parse

paramparsers = {}
_addparam('units_output',	_currystring(['metric', 'us']))
_addparam('strength_output',	_currystring(['plato','sg']))
_addparam('mash_efficiency',	Parse.percent)
_addparam('boiloff_perhour',	Parse.volume)
_addparam('mlt_loss',		Parse.volume)
_addparam('mlt_heatcapacity',	_parsefloat)
_addparam('mlt_heat',		_currystring(['transfer','direct']))
_addparam('grain_absorption',	_curryratio(Parse.volume, Parse.mass))

_defaults = {
	'grain_absorption' : Constants.grain_absorption,
}

for x in _defaults:
	setparam(x, _defaults[x])

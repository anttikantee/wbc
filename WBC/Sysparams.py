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

from WBC.Utils import PilotError, notice
from WBC.Getparam import getparam

from WBC import Constants
from WBC import Parse

def _getparam(what):
	rv = wbcparams[what]
	return rv

wbcparams = {}

def setparam(what, value):
	if what in paramshorts:
		what = paramshorts[what]
	if what not in paramparsers:
		raise PilotError('invalid parameter: ' + what)
	param = paramparsers[what]
	rv = param['parser'](value)
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
		if not paramparsers[p]['optional'] and p not in wbcparams:
			raise PilotError('missing system parameter for: ' + p)

# do some fancypants stuff to avoid having to type things multiple times.
# one makes my fingers hurt, the other makes my brain hurt #PoisonChosen
# beginning to appreciate cpp ...
def _addparam1(optional, name, shortname, handler):
	def x(arg):
		try:
			# reject special characters.  they should not be
			# allowed by the handlers anyway, but it's more
			# certain to check for them collectively.
			if '|' in arg or ':' in arg:
				raise PilotError('__unused')
			rv = handler(arg)
			paraminputs[name] = arg
			return rv
		except (PilotError, ValueError):
			raise PilotError('invalid value "' + str(arg)
			    + '" for "' + str(name) + '"')
	param = {}
	param['parser'] = x
	param['name'] = name
	param['shortname'] = shortname
	param['optional'] = optional
	paramparsers[name] = param

	assert(shortname not in paramshorts)
	paramshorts[shortname] = name

def _addparam(*args):
	return _addparam1(False, *args)
def _addoptparam(*args):
	return _addparam1(True, *args)

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

def _parsemashinratio(input):
	if '%' in input:
		rv = Parse.percent(input)
		return ('%', rv)
	else:
		rv = Parse.ratio(input, Parse.volume, Parse.mass)
		return ('/', rv)

def _parsefloat(input):
	return float(input)

from WBC import Parse

paraminputs = {}		# longname  -> unparsed text input
paramparsers = {}		# longname  -> param "struct"
paramshorts = {}		# shortname -> longname

_addparam('units_output',	'uo',	_currystring(['metric', 'us']))
_addparam('strength_output',	'so',	_currystring(['plato','sg']))

_addparam('mash_efficiency',	'me',	Parse.percent)

_addparam('boiloff_perhour',	'bo',	Parse.volume)

_addparam('mlt_loss',		'ml',	Parse.volume)
_addparam('mlt_heatcapacity',	'mh',	_parsefloat)
_addparam('mlt_heat',		'mt',	_currystring(['transfer','direct']))

_addparam('grain_absorption',	'ga',	_curryratio(Parse.volume, Parse.mass))

_addparam('ambient_temp',	'ta',	Parse.temp)
_addparam('preboil_temp',	'tp',	Parse.temp)
_addparam('postboil_temp',	'tb',	Parse.temp)
_addparam('sparge_temp',	'st',	Parse.temp)

_addparam('mashin_ratio',	'mr',	_parsemashinratio)

_addoptparam('mashwater_min',	'mm',	Parse.volume)
_addoptparam('mashvol_max',	'mM',	Parse.volume)
_addoptparam('lautervol_max',	'lM',	Parse.volume)

_defaults = {
	# water absortion for 1kg of grain, net (i.e. apparent absorption).
	# really somewhere around 1.05, but this value seems to work better
	# for grains not wrung dry
	'grain_absorption'	: '1.1l/kg',

	'ambient_temp'		: '20degC',
	'preboil_temp'		: '70degC',
	'postboil_temp'		: '100degC',
	'sparge_temp'		: '82degC',

	'mashin_ratio'		: '50%',
}

for p in paramparsers:
	wbcparams[p] = None
for x in _defaults:
	setparam(x, _defaults[x])

# return a string instead of an array of tuples so that we can
# maintain policy with decodeparamshorts()
def getparamshorts():
	out=[]
	for sn in sorted(paramshorts):
		n = paramshorts[sn]
		if n not in paraminputs:
			assert(paramparsers[n]['optional'])
			continue
		out.append(sn + ':' + paraminputs[paramshorts[sn]])
	return '|'.join(out)

def decodeparamshorts(pstr):
	res = []
	for x in pstr.split('|'):
		v = x.split(':')
		if len(v) != 2 or v[0] not in paramshorts:
			raise PilotError('invalid sysparam spec: ' + x)
		res.append((paramshorts[v[0]], v[1]))
	return res

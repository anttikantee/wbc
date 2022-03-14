#!/usr/bin/env python3
#
#-
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

from WBC.wbc import WBC
from WBC.utils import PilotError, notice
from WBC.getparam import getparam

from WBC import constants
from WBC import parse

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
def _addparam1(optional, name, shortname, handler, descr):
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
	param['descr'] = descr
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
		return parse.ratio(input, p1, p2)
	return x

def _parsemashinratio(input):
	if '%' in input:
		rv = parse.percent(input)
		return ('%', rv)
	else:
		rv = parse.ratio(input, parse.volume, parse.mass)
		return ('/', rv)

def _parsefloat(input):
	return float(input)

paraminputs = {}		# longname  -> unparsed text input
paramparsers = {}		# longname  -> param "struct"
paramshorts = {}		# shortname -> longname

_addparam('units_output',	'uo',	_currystring(['metric', 'us']),
				'Sets output units except for strength. '
				'Acceptable values: [metric, us]')
_addparam('strength_output',	'so',	_currystring(['plato','sg']),
				'Sets output units for strength. '
				'Acceptable values: [plato, sg]')

_addparam('mash_efficiency',	'me',	parse.percent,
				'The percentage of '
				'extract from the mash making it onto '
				'next stage.  If the wort you are collecting '
				'is too weak or strong, adjust this parameter. '
				'See also: mlt_loss. '
				'Acceptable values: percentage. Typical '
				'values: 70-90%')

_addparam('boiloff_perhour',	'bo',	parse.volume,
				'The volume-equivalent of room temperature '
				'water that is boiled off per hour. '
				'Acceptable values: volume. Typical values: '
				'3.5L, 1gal')

_addparam('mlt_loss',		'ml',	parse.volume,
				'The constant volume of wort that is lost in '
				'the MLT deadspace.  If you are not collecting '
				'the expected amount of wort from the sparge, '
				'adjust this parameter and/or '
				'grain_absorption.  See also: mash_efficiency. '
				'Acceptable values: volume.')
_addparam('mlt_heatcapacity',	'mh',	_parsefloat,
				'The amount of heat capacity that the mashtun '
				'has relative to a kilogram of water.  Adjust '
				'this value up or down if measured mash '
				'temperatures are too low or high, '
				'respectively. Acceptable values: number. '
				'Typical values: 1-2.')

# XXX: it's not M*L*T heat
_addparam('mlt_heat',		'mt',	_currystring(['transfer','direct']),
				'Heat source for the mashtun.  Acceptable '
				'values: [transfer, direct].  The former '
				'relies on heated water or decoction '
				'additions, the latter assumes no added water '
				'for infusion mashes.')

_addparam('grain_absorption',	'ga',	_curryratio(parse.volume, parse.mass),
				'The amount of liquid that grains hold. '
				'Adjust the default down if you are e.g. '
				'pressing the grains at the end of the mash. '
				'This parameter takes the *true* absorption '
				'of the grains instead of the difference '
				'between water added and wort collected; the '
				'former is constant and the latter depends '
				'on wort strength. '
				'Acceptable values: volume/mass (e.g. '
				'"1.1L/kg").  See also: mlt_loss')

_addparam('kettle_loss',	'kl',	parse.volume,
				'The constant volume of room temperature wort '
				'lost in the kettle.  Adjust this up or down '
				'if your postboil volume matches the '
				'prediction but your fermentor volume is off. '
				'The total kettle loss is this value plus '
				'the automatically calculated hop loss. '
				'Acceptable values: volume')
_addparam('fermentor_loss',	'fl',	parse.volume,
				'The constant volume of room temperature wort '
				'lost in the fermentor.  Adjust this up or '
				'down if your fermentor volume matches the '
				'prediction but your packaged volume is off. '
				'Acceptable values: volume')

_addparam('ambient_temp',	'Ta',	parse.temperature, 'TODO (maybe remove/rework?)')

_addparam('sparge_temp',	'Ts',	parse.temperature,
				'Temperature the sparge water volume is '
				'reported for.  Acceptable values: temperature')
_addparam('preboil_temp',	'Tp',	parse.temperature,
				'Temperature the preboil volume is '
				'reported for.  Acceptable values: temperature')
_addparam('postboil_temp',	'Tb',	parse.temperature,
				'Temperature the postboil volume is '
				'reported for.  Acceptable values: temperature')

_addparam('mashin_ratio',	'mr',	_parsemashinratio, 'TODO (rework what this means)')

_addoptparam('mashwater_min',	'mm',	parse.volume, 'TODO (I do not remember why this parameter is necessary)')

_addoptparam('mashvol_max',	'mM',	parse.volume,
					'Maximum volume for the mash.  If the '
					'limit is met, less water is used for '
					'the mash and transferred to the '
					'sparge. Overrides "mashin_ratio" in '
					'case of a conflict. '
					'Acceptable values: volume')
_addoptparam('lautervol_max',	'lM',	parse.volume,
					'Maximum volume for lauter. This '
					'parameter assumes a single-step '
					'lauter such as a "dunk sparge". '
					'Acceptable values: volume')
_addoptparam('boilvol_max',	'bM',	parse.volume,
					'Maximum volume in the boil kettle. '
					'If the limit is overrun, additional '
					'water is reserved from the mash & '
					'sparge, and automatically listed as '
					'a fermentor-stage ingredient.'
					'Acceptable values: volume')

_addoptparam('output_text-pagelen', 'oP',	parse.uint,
					'Page length used by text output. '
					'Sections are started on a new '
					'page if they do not fit the current '
					'one. '
					'Acceptable values: unsigned integer '
					'(0 = disabled). '
					'Typical values: 0 (tty), '
					'65/69 (A4/letter)')


_defaults = {
	# water absortion for 1kg of grain, gross (*true* absorption)
	'grain_absorption'	: '1.50L/kg',

	'ambient_temp'		: '20degC',
	'preboil_temp'		: '70degC',
	'postboil_temp'		: '100degC',
	'sparge_temp'		: '82degC',

	'mashin_ratio'		: '50%',

	# so that debug prints (i.e. __str()__) work without
	# having to depend on the program in question parsing
	# sysparams
	'units_output'		: 'metric',
	'strength_output'	: 'plato',
}

for p in paramparsers:
	if paramparsers[p]['optional']: wbcparams[p] = None
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
		out.append(sn + '=' + paraminputs[paramshorts[sn]])
	return '|'.join(out)

def decodeparamshorts(pstr):
	res = []
	for x in pstr.split('|'):
		v = x.split('=')
		if len(v) != 2 or v[0] not in paramshorts:
			raise PilotError('invalid sysparam spec: ' + x)
		res.append((paramshorts[v[0]], v[1]))
	return res

if __name__ == '__main__':
	for x in paramparsers:
		p = paramparsers[x]
		print(p['name'] + ': ' + p['descr'])
		print()

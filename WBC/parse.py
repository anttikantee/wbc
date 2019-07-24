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

from WBC import units
from WBC.utils import PilotError
from WBC.wbc import Recipe
from WBC.hop import Hop

from WBC import mash

import re
import string

def _unit(cls, sfxmap, input, fatal = True, name = None):
	inputstr = str(input).strip()
	alphastr = inputstr.lstrip(string.digits + '.' + '-')
	numstr = inputstr[0:len(inputstr) - len(alphastr)]
	alphastr = alphastr.strip()

	# if unit is missing, default to 1
	if numstr == "":
		numstr = "1"

	if name is None:
		name = cls.__name__

	if alphastr not in sfxmap:
		if fatal:
			raise PilotError('invalid suffix in: '
			    + inputstr + ' (for ' + name + ')')
		else:
			return None
	sfx = sfxmap[alphastr]
	if sfx is None:
		return cls(float(numstr))
	else:
		return cls(float(numstr), sfx)

masssfx = {
	'mg'	: units.Mass.MG,
	'g'	: units.Mass.G,
	'kg'	: units.Mass.KG,
	'oz'	: units.Mass.OZ,
	'lb'	: units.Mass.LB
}
def mass(input):
	return _unit(units.Mass, masssfx, input)

def volume(input):
	suffixes = {
		'bbl'	: units.Volume.BARREL,
		'gal'	: units.Volume.GALLON,
		'qt'	: units.Volume.QUART,
		'ml'	: units.Volume.MILLILITER,
		'dl'	: units.Volume.DECILITER,
		'l'	: units.Volume.LITER,
		'hl'	: units.Volume.HECTOLITER,
	}
	return _unit(units.Volume, suffixes, input)

def temperature(input):
	suffixes = {
		'degC'			: units.Temperature.degC,
		chr(0x00b0) + 'C'	: units.Temperature.degC,
		'degF'			: units.Temperature.degF,
		chr(0x00b0) + 'F'	: units.Temperature.degF,
		'K'			: units.Temperature.K,
	}
	return _unit(units.Temperature, suffixes, input)

def pressure(input):
	suffixes = {
		'Pa'	: units.Pressure.PASCAL,
		'atm'	: units.Pressure.ATMOSPHERE,
		'bar'	: units.Pressure.BAR,
		'psi'	: units.Pressure.PSI,
	}
	return _unit(units.Pressure, suffixes, input)

def kettletime(input):
	suffixes = {
		'min'	: None,
	}
	return _unit(int, suffixes, input, name = 'kettletime')

def timespec(input):
	# XXX: collision between timespec module and this function.
	# however, since this function is always seen as parse.timespec()
	# elsewhere, we can just do collision avoidance here.
	import WBC

	if input == 'package':
		return WBC.timespec.Package()
	elif 'mash' in input:
		t = None
		if '@' in input:
			r = input.split('@')
			t = temperature(r[1])
		return WBC.timespec.Mash(t)
	elif '->' in input:
		d1, d2 = split(input, '->', days, days)
		return WBC.timespec.Fermentor(d1, d2)
	elif '@' in input:
		time, temp = timedtemperature(input)
		return WBC.timespec.Steep(time, temp)
	elif input == 'FWH' or input == 'boiltime':
		return WBC.timespec.Boil(input)
	else:
		return WBC.timespec.Boil(kettletime(input))

def days(input):
	suffixes = {
		'days'	: None,
		'day'	: None,
		'd'	: None,
	}
	return _unit(int, suffixes, input, name = 'days')

def color(input):
	suffixes = {
		'EBC'	: units.Color.EBC,
		'SRM'	: units.Color.SRM,
		'L'	: units.Color.LOVIBOND,
	}
	return _unit(units.Color, suffixes, input)

percentsfxs = {
	'%'	: None,
}
def percent(input):
	return _unit(float, percentsfxs, input, name = 'percentage')

def strength(input):
	suffixes = {
		'degP'			: units.Strength.PLATO,
		chr(0x00b0) + 'P'	: units.Strength.PLATO,
		'SG'			: units.Strength.SG,
		'pts'			: units.Strength.SG_PTS,
	}
	input = str(input)
	if re.match(r'^\s*1\.[01][0-9][0-9]\s*$', input):
		return units.Strength(float(input), units.Strength.SG)
	if re.match(r'^\s*0\.9[7-9][0-9]\s*$', input):
		return units.Strength(float(input), units.Strength.SG)
	return _unit(units.Strength, suffixes, input)

def split(input, splitter, i1, i2):
	istr = str(input)
	marr = istr.split(splitter)
	if len(marr) != 2:
		raise PilotError('input must contain exactly one "' + splitter
		    + '", you gave: ' + istr)
	res1 = i1(marr[0])
	res2 = i2(marr[1])
	return (res1, res2)

def ratio(input, r1, r2):
	return split(input, '/', r1, r2)

def timedtemperature(input):
	return split(input, '@', kettletime, temperature)

def mashmethod(input):
	methods = {
		'infusion'	: mash.Mash.INFUSION,
		'decoction'	: mash.Mash.DECOCTION,
	}
	if input in methods:
		return methods[input]
	raise PilotError('unsupported mash method: ' + str(input))

def mashstep(input):
	if '@' in input:
		r = timedtemperature(input)
		return mash.MashStep(r[1], r[0])
	else:
		return mash.MashStep(temperature(input))

def fermentableunit(input):
	if input == 'rest':
		return (Recipe.fermentable_bypercent, Recipe.THEREST)

	rv = _unit(float, percentsfxs, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bypercent, rv)
	rv = _unit(units.Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bymass, rv)

	raise PilotError('invalid fermentable quantity: ' + str(input))

def opaquemassunit(input):
	if '/' in input:
		rv = ratio(input, mass, volume)
		return (Recipe.opaque_bymassvolratio, rv)
	else:
		return (Recipe.opaque_bymass, mass(input))

def hopunit(input):
	if input.startswith('AA '):
		input = input[3:]
		if '/' in input:
			rv = ratio(input, mass, volume)
			return (Recipe.hop_byAAvolratio, rv)
		else:
			rv = mass(input)
			return (Recipe.hop_byAA, rv)

	if '/' in input:
		rv = ratio(input, mass, volume)
		return (Recipe.hop_bymassvolratio, rv)

	rv = _unit(units.Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.hop_bymass, rv)

	rv = _unit(float, { 'IBU' : None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_byIBU, rv)

	rv = _unit(float, { 'Recipe IBU':None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_byrecipeIBU, rv)

	rv = _unit(float, { 'Recipe BUGU': None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_byrecipeBUGU, rv)

	raise PilotError('invalid boilhop quantity: ' + str(input))

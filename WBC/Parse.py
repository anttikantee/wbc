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

from WBC.Units import Mass, Temperature, Volume, Strength, Pressure, Color
from WBC.Utils import PilotError
from WBC.WBC import Recipe
from WBC.Hop import Hop
from WBC.Mash import Mash

import re
import string

def _unit(cls, sfxmap, input, fatal = True, name = None):
	inputstr = str(input).strip()
	alphastr = inputstr.lstrip(string.digits + '.')
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
	'mg'	: Mass.MG,
	'g'	: Mass.G,
	'kg'	: Mass.KG,
	'oz'	: Mass.OZ,
	'lb'	: Mass.LB
}
def mass(input):
	return _unit(Mass, masssfx, input)

def volume(input):
	suffixes = {
		'bbl'	: Volume.BARREL,
		'gal'	: Volume.GALLON,
		'qt'	: Volume.QUART,
		'l'	: Volume.LITER,
	}
	return _unit(Volume, suffixes, input)

def temp(input):
	suffixes = {
		'degC'			: Temperature.degC,
		chr(0x00b0) + 'C'	: Temperature.degC,
		'degF'			: Temperature.degF,
		chr(0x00b0) + 'F'	: Temperature.degF,
		'K'			: Temperature.K,
	}
	return _unit(Temperature, suffixes, input)

def pressure(input):
	suffixes = {
		'Pa'	: Pressure.PASCAL,
		'atm'	: Pressure.ATMOSPHERE,
		'bar'	: Pressure.BAR,
		'psi'	: Pressure.PSI,
	}
	return _unit(Pressure, suffixes, input)

def kettletime(input):
	suffixes = {
		'min'	: None,
	}
	return _unit(int, suffixes, input, name = 'kettletime')

def days(input):
	suffixes = {
		'days'	: None,
		'day'	: None,
		'd'	: None,
	}
	return _unit(int, suffixes, input, name = 'days')

def color(input):
	suffixes = {
		'EBC'	: Color.EBC,
		'SRM'	: Color.SRM,
		'L'	: Color.LOVIBOND,
	}
	return _unit(Color, suffixes, input)

percentsfxs = {
	'%'	: None,
}
def percent(input):
	return _unit(float, percentsfxs, input, name = 'percentage')

def strength(input):
	suffixes = {
		'degP'			: Strength.PLATO,
		chr(0x00b0) + 'P'	: Strength.PLATO,
		'SG'			: Strength.SG,
		'pts'			: Strength.SG_PTS,
	}
	if re.match(r'^\s*1\.[01][0-9][0-9]\s*$', input):
		return Strength(float(input), Strength.SG)
	if re.match(r'^\s*0\.9[7-9][0-9]\s*$', input):
		return Strength(float(input), Strength.SG)
	return _unit(Strength, suffixes, input)

def ratio(input, r1, r2):
	istr = str(input)
	marr = istr.split('/')
	if len(marr) != 2:
		raise PilotError('ratio must contain exactly one "/", you '
		    'gave: ' + istr)
	res1 = r1(marr[0])
	res2 = r2(marr[1])
	return (res1, res2)

def mashmethod(input):
	methods = {
		'infusion'	: Mash.INFUSION,
	}
	if input in methods:
		return methods[input]
	raise PilotError('unsupported mash method: ' + str(input))

def fermentableunit(input):
	if input == 'rest':
		return (Recipe.fermentable_bypercent, Recipe.THEREST)

	rv = _unit(float, percentsfxs, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bypercent, rv)
	rv = _unit(Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bymass, rv)

	raise PilotError('invalid fermentable quantity: ' + str(input))

def hopboil(input):
	suffixes = {
		'min'	: None,
	}
	if input == 'FWH':
		return Hop.Boil(Hop.Boil.FWH)
	elif input == 'boiltime':
		return Hop.Boil(Hop.Boil.BOILTIME)
	return _unit(Hop.Boil, suffixes, input)

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

	rv = _unit(Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.hop_bymass, rv)

	rv = _unit(float, { 'IBU' : None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_byIBU, rv)

	rv = _unit(float, { 'Recipe IBU':None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_recipeIBU, rv)

	rv = _unit(float, { 'Recipe BUGU': None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_recipeBUGU, rv)

	raise PilotError('invalid boilhop quantity: ' + str(input))

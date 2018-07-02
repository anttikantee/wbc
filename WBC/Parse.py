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

from Units import Mass, Temperature, Volume, Strength
from Utils import PilotError
from WBC import Recipe

def _unit(cls, sfxmap, input, fatal = True, name = None):
	inputstr = str(input).strip()
	numstr = filter(lambda x: x.isdigit() or x == '.', inputstr)
	alphastr = inputstr[len(numstr):].strip()

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
	'g'	: Mass.G,
	'kg'	: Mass.KG,
	'oz'	: Mass.OZ,
	'lb'	: Mass.LB
}
def mass(input):
	return _unit(Mass, masssfx, input)

def volume(input):
	suffixes = {
		'gal'	: Volume.GALLON,
		'l'	: Volume.LITER,
	}
	return _unit(Volume, suffixes, input)

def temp(input):
	suffixes = {
		'degC'	: Temperature.degC,
		'degF'	: Temperature.degF,
	}
	return _unit(Temperature, suffixes, input)

def kettletime(input):
	suffixes = {
		'min'	: None,
	}
	return _unit(int, suffixes, input, name = 'kettletime')

def days(input):
	suffixes = {
		'day'	: None,
	}
	return _unit(int, suffixes, input, name = 'days')

percentsfxs = {
	'%'	: None,
}
def percent(input):
	return _unit(float, percentsfxs, input, name = 'percentage')

def strength(input):
	suffixes = {
		'degP'	: Strength.PLATO,
		'SG'	: Strength.SG,
		'pts'	: Strength.SG_PTS,
	}
	return _unit(Strength, suffixes, input)

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

def hopunit(input):
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

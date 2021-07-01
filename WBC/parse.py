#
# Copyright (c) 2018, 2021 Antti Kantee <pooka@iki.fi>
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
from WBC.utils import PilotError, warn
from WBC.wbc import Recipe
from WBC.hop import Hop

from WBC import mash

import re
import string

def _unit(cls, sfxmap, input, name = None):
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
		raise ValueError('invalid suffix in: '
		    + inputstr + ' (for ' + name + ')')
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
		'cup'	: units.Volume.CUP,
		'tsp'	: units.Volume.TEASPOON,
		'ml'	: units.Volume.MILLILITER,
		'mL'	: units.Volume.MILLILITER,
		'dl'	: units.Volume.DECILITER,
		'dL'	: units.Volume.DECILITER,
		'l'	: units.Volume.LITER,
		'L'	: units.Volume.LITER,
		'hl'	: units.Volume.HECTOLITER,
		'hL'	: units.Volume.HECTOLITER,
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

def duration(input):
	suffixes = {
		units.Duration.MINUTE	: units.Duration.MINUTE,
	}
	return _unit(units.Duration, suffixes, input, name = 'duration')

def timespec(input):
	# XXX: collision between timespec module and this function.
	# however, since this function is (= should be!) always seen
	# as parse.timespec() elsewhere, we can just do collision
	# avoidance here.
	import WBC

	mash = WBC.timespec.Mash
	mspec = WBC.timespec.MashSpecial
	if input == 'package':
		return WBC.timespec.Package()
	elif 'mash' in input:
		if '@' in input:
			r = input.split('@')
			s = r[1].strip()

			try:
				ts = {**{ x: mash for x in mash.values },
				    **{ x: mspec for x in mspec.values }}[s]
				tv = s
			except KeyError:
				ts = WBC.timespec.Mash
				tv = temperature(r[1])
		else:
			ts = WBC.timespec.Mash
			tv = WBC.timespec.Mash.MASHIN
		return ts(tv)
	elif input == 'fermentor' or '->' in input:
		fspec = WBC.timespec.Fermentor
		if '->' in input:
			d1, d2 = split(input, '->', days, days)
			return fspec(d1, d2)
		else:
			return fspec(fspec.UNDEF, fspec.UNDEF)
	elif '@' in input:
		time, temp = timedtemperature(input)
		return WBC.timespec.Whirlpool(time, temp)
	elif input == 'FWH':
		warn('using deprecated "FWH" timespec. use "firstwort"\n')
		return mspec(mspec.FIRSTWORT)
	elif input == WBC.timespec.Boil.BOILTIME:
		return WBC.timespec.Boil(input)
	elif WBC.units.Duration.MINUTE in input:
		return WBC.timespec.Boil(duration(input))
	else:
		raise PilotError('could not parse timespec: ' + str(input))

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
		raise ValueError('input must contain exactly one "' + splitter
		    + '", you gave: ' + istr)
	res1 = i1(marr[0])
	res2 = i2(marr[1])
	return (res1, res2)

def ratio(input, r1, r2):
	return split(input, '/', r1, r2)

def timedtemperature(input):
	return split(input, '@', duration, temperature)

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

def _additionunit(input, acceptable):
	ts = [x for x in acceptable if isinstance(x, tuple)]
	for p in ts:
		try: return split(input, '/', p[0], p[1])
		except ValueError: pass
	for p in [x for x in acceptable if x not in ts]:
		try: return p(input)
		except ValueError: pass

	raise ValueError('additionunit mismatch')

def fermentableunit(input):
	try: return (Recipe.fermentable_bypercent, percent(input))
	except ValueError: pass

	if input == Recipe.THEREST:
		return (Recipe.fermentable_bypercent, Recipe.THEREST)

	try: return (Recipe.fermentable_byunit,
	    _additionunit(input, [mass, (mass, volume)]))
	except ValueError: pass

	raise PilotError('invalid fermentable quantity: ' + str(input))

def opaqueunit(input):
	try: return (Recipe.opaque_byunit, _additionunit(input,
	    [mass, volume, (mass, volume), (volume, volume)]))
	except ValueError: pass

	raise PilotError('invalid opaque quantity: ' + str(input))

def hopunit(input):
	if input.startswith('AA '):
		input = input[3:]
		if '/' in input:
			rv = ratio(input, mass, volume)
			return (Recipe.hop_byAAvolratio, rv)
		else:
			rv = mass(input)
			return (Recipe.hop_byAA, rv)

	try: return (Recipe.hop_byunit,
	    _additionunit(input, [mass, (mass, volume)]))
	except ValueError: pass

	for t in [
		( Recipe.hop_byIBU	  , { 'IBU' : None }		),
	        ( Recipe.hop_byrecipeIBU  , { 'Recipe IBU' : None }	),
	        ( Recipe.hop_byrecipeBUGU , { 'Recipe BUGU' : None }	),
	]:
		try: return (t[0], _unit(float, t[1], input))
		except ValueError: pass

	raise PilotError('invalid boilhop quantity: ' + str(input))

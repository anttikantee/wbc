#!/usr/bin/env python

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

from WBC.WBC import Recipe, Hop
from WBC.Units import Mass, Temperature, Volume, Strength
from WBC.Utils import PilotError, setconfig

import getopt
import sys
import yaml

def getdef_fatal(defs, v):
	for x in v:
		if x not in defs:
			raise PilotError('mandatory element missing: ' + str(v))
		defs = defs[x]
	return defs

def parseunit(cls, sfxmap, input, fatal = True, name = None):
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
def parsemass(input):
	return parseunit(Mass, masssfx, input)

def parsevolume(input):
	suffixes = {
		'gal'	: Volume.GALLON,
		'l'	: Volume.LITER,
	}
	return parseunit(Volume, suffixes, input)

def parsetemp(input):
	suffixes = {
		'degC'	: Temperature.degC,
		'degF'	: Temperature.degF,
	}
	return parseunit(Temperature, suffixes, input)

def parsekettletime(input):
	suffixes = {
		'min'	: None,
	}
	return parseunit(int, suffixes, input, name = 'kettletime')

def parsedays(input):
	suffixes = {
		'day'	: None,
	}
	return parseunit(int, suffixes, input, name = 'days')

percentsfxs = {
	'%'	: None,
}
def parsepercent(input):
	return parseunit(float, percentsfxs, input, name = 'percentage')

def parsestrength(input):
	suffixes = {
		'degP'	: Strength.PLATO,
		'SG'	: Strength.SG,
		'pts'	: Strength.SG_PTS,
	}
	return parseunit(Strength, suffixes, input)

def parsefermentableunit(input):
	if input == 'rest':
		return (Recipe.fermentable_bypercent, Recipe.THEREST)

	rv = parseunit(float, percentsfxs, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bypercent, rv)
	rv = parseunit(Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.fermentable_bymass, rv)

	raise PilotError('invalid fermentable quantity: ' + str(input))

def parsehopunit(input):
	rv = parseunit(Mass, masssfx, input, fatal = False)
	if rv is not None:
		return (Recipe.hop_bymass, rv)

	rv = parseunit(float, { 'IBU' : None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_byIBU, rv)

	rv = parseunit(float, { 'Recipe IBU':None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_recipeIBU, rv)

	rv = parseunit(float, { 'Recipe BUGU': None }, input, fatal=False)
	if rv is not None:
		return (Recipe.hop_recipeBUGU, rv)

	raise PilotError('invalid boilhop quantity: ' + str(input))

def dohops(r, d_hops):
	hops = {}

	def processhopdef(id, v):
		typstr = v[2] if len(v) > 2 else 'pellet'
		typ = { 'leaf' : Hop.Leaf, 'pellet': Hop.Pellet }[typstr]
		aa = parsepercent(v[1])
		hops[id] = Hop(v[0], aa, typ)
		return hops[id]

	for hd in d_hops.get('defs', []):
		processhopdef(hd, d_hops['defs'][hd])

	def hoptime2time(v):
		if v == 'FWH':
			return Hop.FWH
		return parsekettletime(v)

	def gethopinstance(v):
		if isinstance(v, list):
			return processhopdef('n/a', v)
		else:
			return hops[v]

	for h in d_hops.get('boil', []):
		(fun, hu) = parsehopunit(h[1])
		fun(r, gethopinstance(h[0]), hu, hoptime2time(h[2]))

	for h in d_hops.get('steep', []):
		ar = h[2].split("@")
		if len(ar) != 2:
			raise PilotError("whirlpool hops must be specified as "
			    + "\"time @ temperature\"")
		time = parsekettletime(ar[0])
		temp = parsetemp(ar[1])

		(fun, hu) = parsehopunit(h[1])
		fun(r, hops[h[0]], hu, Hop.Steep(temp, time))

	for h in d_hops.get('dryhop', []):
		if h[2] == 'keg':
			inday = outday = Hop.Dryhop.Keg
		else:
			ar = h[2].split("->")
			if len(ar) != 2:
				raise PilotError("dryhops must be specified as "
				    + "\"days_in -> days_out\" or \"keg\"")
			inday = parsedays(ar[0])
			outday = parsedays(ar[1])

		(fun, hu) = parsehopunit(h[1])
		fun(r, hops[h[0]], hu, Hop.Dryhop(inday, outday))

def dofermentables(r, ferms):
	fermtype = None
	for f in ferms['mash']:
		(fun, v) = parsefermentableunit(ferms['mash'][f])
		fun(r, f, v)

	if fun == Recipe.fermentable_bypercent:
		if 'anchor' not in ferms:
			raise PilotError("percent fermentables must set "
			    "an anchor")
		a = ferms['anchor']
		if a[0] == 'strength':
			r.anchor_bystrength(parsestrength(a[1]))
		elif a[0] == 'mass':
			r.anchor_bymass(a[1], parsemass(a[2]))
		else:
			raise PilotError('unexpected fermentable anchor: '
			    + a[0])

def processfile(clist, filename):
	with open(filename, "r") as data:
		d = yaml.safe_load(data.read())

	name = getdef_fatal(d, ['name'])
	volume = getdef_fatal(d, ['volume'])
	yeast = getdef_fatal(d, ['yeast'])

	mashtemps = [parsetemp(x) for x in getdef_fatal(d, ['mashtemps'])]
	bt = parsekettletime(d.get('boil', '60min'))
	r = Recipe(name, yeast, parsevolume(volume), mashtemps, bt)
	for c in clist:
		c[0](r, *c[1:])

	mashin = d.get('mashin', None)
	if mashin is not None:
		r.mashin_ratio_set(mashin)

	dofermentables(r, getdef_fatal(d, ['fermentables']))
	dohops(r, d.get('hops', []))

	r.do()

def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-u metric|us|plato|sg] [-s volume,strength] recipefile\n')
	sys.exit(1)

def processopts(opts):
	clist = []
	for o, a in opts:
		if o == '-h':
			usage()
		elif o == '-s':
			optarg = a.split(',')
			if len(optarg) != 2:
				usage()
			v = parsevolume(optarg[0])
			s = parsestrength(optarg[1])
			clist.append((Recipe.steal_preboil_wort, v, s))

		elif o == '-u':
			if a == 'us' or a == 'metric':
				setconfig('units_output', a)
			elif a == 'plato' or a == 'sg':
				setconfig('strength_output', a)
			else:
				usage()

	return clist

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'hs:u:')
	if len(args) != 1:
		usage()

	try:
		clist = processopts(opts)
		processfile(clist, args[0])
	except PilotError, pe:
		print 'Pilot Error: ' + str(pe)

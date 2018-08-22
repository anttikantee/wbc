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
from WBC import Parse

import getopt
import sys
import yaml

def getdef_fatal(defs, v):
	for x in v:
		if x not in defs:
			raise PilotError('mandatory element missing: ' + str(v))
		defs = defs[x]
	return defs

def dohops(r, d_hops):
	hops = {}

	def processhopdef(id, v):
		typstr = v[2] if len(v) > 2 else 'pellet'
		typ = { 'leaf' : Hop.Leaf, 'pellet': Hop.Pellet }[typstr]
		aa = Parse.percent(v[1])
		hops[id] = Hop(v[0], aa, typ)
		return hops[id]

	for hd in d_hops.get('defs', []):
		processhopdef(hd, d_hops['defs'][hd])

	def gethopinstance(v):
		if isinstance(v, list):
			return processhopdef('n/a', v)
		else:
			return hops[v]

	for h in d_hops.get('boil', []):
		(fun, hu) = Parse.hopunit(h[1])
		fun(r, gethopinstance(h[0]), hu, Parse.hopboil(h[2]))

	for h in d_hops.get('steep', []):
		ar = h[2].split("@")
		if len(ar) != 2:
			raise PilotError("whirlpool hops must be specified as "
			    + "\"time @ temperature\"")
		time = Parse.kettletime(ar[0])
		temp = Parse.temp(ar[1])

		(fun, hu) = Parse.hopunit(h[1])
		fun(r, hops[h[0]], hu, Hop.Steep(temp, time))

	for h in d_hops.get('dryhop', []):
		if h[2] == 'keg':
			inday = outday = Hop.Dryhop.Keg
		else:
			ar = h[2].split("->")
			if len(ar) != 2:
				raise PilotError("dryhops must be specified as "
				    + "\"days_in -> days_out\" or \"keg\"")
			inday = Parse.days(ar[0])
			outday = Parse.days(ar[1])

		(fun, hu) = Parse.hopunit(h[1])
		fun(r, hops[h[0]], hu, Hop.Dryhop(inday, outday))

def dofermentables(r, ferms):
	fermtype = None
	for f in ferms['mash']:
		(fun, v) = Parse.fermentableunit(ferms['mash'][f])
		fun(r, f, v, Recipe.MASH)

	for f in ferms.get('boil', []):
		(fun, v) = Parse.fermentableunit(ferms['boil'][f])
		fun(r, f, v, Recipe.BOIL)

	for f in ferms.get('ferment', []):
		(fun, v) = Parse.fermentableunit(ferms['ferment'][f])
		fun(r, f, v, Recipe.FERMENT)

	if fun == Recipe.fermentable_bypercent:
		if 'anchor' not in ferms:
			raise PilotError("percent fermentables must set "
			    "an anchor")
		a = ferms['anchor']
		if a[0] == 'strength':
			r.anchor_bystrength(Parse.strength(a[1]))
		elif a[0] == 'mass':
			r.anchor_bymass(a[1], Parse.mass(a[2]))
		else:
			raise PilotError('unexpected fermentable anchor: '
			    + a[0])

def processfile(clist, odict, filename):
	with open(filename, "r") as data:
		d = yaml.safe_load(data.read())

	name = getdef_fatal(d, ['name'])
	volume = getdef_fatal(d, ['volume'])
	yeast = getdef_fatal(d, ['yeast'])

	if 'volume' in odict:
		volume = odict['volume']

	mashtemps = [Parse.temp(x) for x in getdef_fatal(d, ['mashtemps'])]
	bt = Parse.kettletime(d.get('boil', '60min'))
	r = Recipe(name, yeast, Parse.volume(volume), mashtemps, bt)
	for c in clist:
		c[0](r, *c[1:])

	mashin = d.get('mashin', None)
	if mashin is not None:
		mstr = str(mashin)
		marr = mstr.split('/')
		if len(marr) != 2:
			raise PilotError('mashin ratio must be "vol / mass", '
			    'you gave: ' + mstr)
		mashin_vol = Parse.volume(marr[0])
		mashin_mass = Parse.mass(marr[1])
		r.mashin_ratio_set(mashin_vol, mashin_mass)

	dofermentables(r, getdef_fatal(d, ['fermentables']))
	dohops(r, d.get('hops', []))

	r.do()

def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-u metric|us|plato|sg] [-s volume,strength] [-v final vol] '
	    + 'recipefile\n')
	sys.exit(1)

def processopts(opts):
	clist = []
	odict = {}
	for o, a in opts:
		if o == '-h':
			usage()
		elif o == '-s':
			optarg = a.split(',')
			if len(optarg) != 2:
				usage()
			v = Parse.volume(optarg[0])
			s = Parse.strength(optarg[1])
			clist.append((Recipe.steal_preboil_wort, v, s))

		elif o == '-u':
			if a == 'us' or a == 'metric':
				setconfig('units_output', a)
			elif a == 'plato' or a == 'sg':
				setconfig('strength_output', a)
			else:
				usage()

		elif o == '-v':
			v = Parse.volume(a)
			odict['volume'] = v

	return (clist, odict)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'hs:u:v:')
	if len(args) != 1:
		usage()

	try:
		(clist, odict) = processopts(opts)
		processfile(clist, odict, args[0])
	except PilotError, pe:
		print 'Pilot Error: ' + str(pe)
		raise SystemExit, 1
	sys.exit(0)

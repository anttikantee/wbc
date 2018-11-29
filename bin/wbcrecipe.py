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

from WBC.WBC import Recipe, Hop, Mash
from WBC.Units import Mass, Temperature, Volume, Strength
from WBC.Units import _Mass, _Temperature, _Volume
from WBC.Utils import PilotError
from WBC import Sysparams
from WBC import Parse

import getopt
import sys

hoptypes = { 'leaf' : Hop.Leaf, 'pellet': Hop.Pellet }

def doboilhop(r, hop, amountspec, timespec):
	(fun, hu) = Parse.hopunit(amountspec)
	fun(r, hop, hu, Parse.hopboil(timespec))

def dosteephop(r, hop, amountspec, timespec):
	ar = timespec.split("@")
	if len(ar) != 2:
		raise PilotError("whirlpool hops must be specified as "
		    + "\"time @ temperature\"")
	time = Parse.kettletime(ar[0])
	temp = Parse.temp(ar[1])

	(fun, hu) = Parse.hopunit(amountspec)
	fun(r, hop, hu, Hop.Steep(temp, time))

def dodryhop(r, hop, amountspec, timespec):
	if timespec == 'keg':
		inday = outday = Hop.Dryhop.Keg
	else:
		ar = timespec.split("->")
		if len(ar) != 2:
			raise PilotError("dryhops must be specified as "
			    + "\"days_in -> days_out\" or \"keg\"")
		inday = Parse.days(ar[0])
		outday = Parse.days(ar[1])

	(fun, hu) = Parse.hopunit(amountspec)
	fun(r, hop, hu, Hop.Dryhop(inday, outday))

def dohops(r, d_hops):
	hops = {}

	def processhopdef(id, v):
		typstr = v[2] if len(v) > 2 else 'pellet'
		if typstr not in hoptypes:
			raise PilotError('invalid hop type: ' + typstr)
		typ = hoptypes[typstr]
		aa = Parse.percent(v[1])
		hops[id] = Hop(v[0], aa, typ)
		return hops[id]

	def gethopinstance(v):
		if isinstance(v, list):
			return processhopdef('n/a', v)
		else:
			return hops[v]

	for hd in d_hops.get('defs', []):
		processhopdef(hd, d_hops['defs'][hd])

	for h in d_hops.get('boil', []):
		doboilhop(r, gethopinstance(h[0]), h[1], h[2])

	for h in d_hops.get('steep', []):
		dosteephop(r, gethopinstance(h[0]), h[1], h[2])

	for h in d_hops.get('dryhop', []):
		dodryhop(r, gethopinstance(h[0]), h[1], h[2])

def dofermentables(r, ferms):
	fermtype = None
	for f in ferms['mash']:
		(fun, v) = Parse.fermentableunit(ferms['mash'][f])
		fun(r, f, v, Recipe.MASH)

	for f in ferms.get('steep', []):
		(fun, v) = Parse.fermentableunit(ferms['steep'][f])
		fun(r, f, v, Recipe.STEEP)

	for f in ferms.get('boil', []):
		(fun, v) = Parse.fermentableunit(ferms['boil'][f])
		fun(r, f, v, Recipe.BOIL)

	for f in ferms.get('ferment', []):
		(fun, v) = Parse.fermentableunit(ferms['ferment'][f])
		fun(r, f, v, Recipe.FERMENT)

	for f in ferms.get('package', []):
		(fun, v) = Parse.fermentableunit(ferms['package'][f])
		fun(r, f, v, Recipe.PACKAGE)

	a = ferms.get('anchor', [])
	if len(a) > 0:
		# XXX: validate input length
		if a[0] == 'strength':
			r.anchor_bystrength(Parse.strength(a[1]))
		elif a[0] == 'mass':
			r.anchor_bymass(a[1], Parse.mass(a[2]))
		else:
			raise PilotError('unexpected fermentable anchor: '
			    + a[0])

def domashparams(r, mashparams):
	for p in mashparams:
		value = mashparams[p]
		if p == 'mashin':
			if '%' in value:
				v = Parse.percent(value)
				r.mash.set_mashin_percent(v)
			elif '/' in value:
				(mashin_vol, mashin_mass) = \
				    Parse.ratio(value, Parse.volume, Parse.mass)
				r.mash.set_mashin_ratio(mashin_vol, mashin_mass)
			else:
				raise PilotError('invalid mashin ratio: '
				    + value)

		elif p == 'method':
			m = Parse.mashmethod(value)
			r.mash.set_method(m)

		elif p == 'temperature' or p == 'temperatures':
			if isinstance(value, str):
				mashtemps = [Parse.temp(value)]
			elif isinstance(value, list):
				mashtemps = [Parse.temp(x) for x in value]
			else:
				raise PilotError('mash temperature must be '
				    'given as a string or list of strings')
			r.mash.set_mash_temperature(mashtemps)

		else:
			raise PilotError('unknown mash parameter: ' + str(p))

def dowater(r, v):
	r.set_water_notes(v)

def applyparams(r, clist, odict):
	for f in odict.get('wbcparamfiles', []):
		Sysparams.processfile(f)
	for pl in odict.get('wbcparams', []):
		Sysparams.processline(pl)

	for c in clist:
		c[0](r, *c[1:])

	if 'volume' in odict:
		r.set_final_volume(odict['volume'])

	for n in odict.get('notes', []):
		r.add_note(n)

def processyaml(clist, odict, data):
	# importing yaml is unfathomably slow, so do it only if we need it
	import yaml

	try:
		d = yaml.safe_load(data.read())
	except yaml.parser.ParserError, e:
		print '>> failed to parse yaml recipe:'
		print e
		raise SystemExit, 1

	def getdef(x):
		if x not in d:
			raise PilotError('mandatory element missing: ' + str(v))
		rv = d[x]
		del d[x]
		return rv

	name = getdef('name')
	yeast = getdef('yeast')

	if 'volume' in d:
		volume = Parse.volume(getdef('volume'))
	else:
		volume = None

	if 'boil' in d:
		boiltime = getdef('boil')
	else:
		boiltime = '60min'

	r = Recipe(name, yeast, volume, Parse.kettletime(boiltime))

	applyparams(r, clist, odict)

	handlers = {
		'mashparams'	: domashparams,
		'fermentables'	: dofermentables,
		'hops'		: dohops,
		'water'		: dowater,
	}

	for p in d:
		v = d[p]
		if p in handlers:
			handlers[p](r, v)
		else:
			raise PilotError('invalid recipe field: ' + p)

	return r

def processcsv(clist, odict, data):
	import csv

	reader = csv.reader(data, delimiter='|')
	dataver = -1
	r = None
	for row in reader:
		if row[0][0] is "#":
			continue

		if row[0] == "wbcdata":
			dataver = int(row[1])
		if dataver != 1:
			raise PilotError("unsupported wbcdata version")

		if row[0] == "recipe":
			r = Recipe(row[1], row[2], _Volume(row[4]), int(row[3]))
			applyparams(r, clist, odict)

		elif row[0] == "mash":
			r.mash.set_mashin_ratio(_Volume(row[1]), _Mass(1000))
			mashtemps = [_Temperature(x) for x in row[3:]]
			r.mash.set_mash_temperature(mashtemps)

		elif row[0] == "fermentable":
			r.fermentable_bymass(row[1],
			    Mass(row[2], Mass.G), row[3])

		elif row[0] == "hop":
			hopfunmap = {
				'boil'   : doboilhop,
				'steep'  : dosteephop,
				'dryhop' : dodryhop,
			}
			h = Hop(row[1], float(row[3]), hoptypes[row[2]])
			hopfunmap[row[5]](r, h, row[4] + 'g', row[6])
	return r


def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-s volume,strength] [-v final volume] [-c] [-d] [-m]\n'
	    + '\t[-n note] [-n note ...]\n'
	    + '\t[-p paramsfile] [-P param=value] recipefile\n')
	sys.exit(1)

def processopts(opts):
	clist = []
	odict = {}
	for o, a in opts:
		if o == '-h':
			usage()

		elif o == '-m':
			odict['miniprint'] = True

		elif o == '-n':
			odict.setdefault('notes', []).append(a)

		elif o == '-p':
			odict.setdefault('wbcparamfiles', []).append(a)

		elif o == '-P':
			odict.setdefault('wbcparams', []).append(a)

		elif o == '-s':
			optarg = a.split(',')
			if len(optarg) != 2:
				usage()
			v = Parse.volume(optarg[0])
			s = Parse.strength(optarg[1])
			clist.append((Recipe.steal_preboil_wort, v, s))

		elif o == '-v':
			v = Parse.volume(a)
			odict['volume'] = v

	return (clist, odict)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'cdhmn:p:P:s:v:')
	if len(args) > 1:
		usage()

	try:
		(clist, odict) = processopts(opts)
		flags = [x[0] for x in opts]
		with open(args[0], "r") \
		    if (len(args) > 0 and args[0] is not "-") \
		    else sys.stdin as data:
			if '-d' in flags:
				r = processcsv(clist, odict, data)
			else:
				r = processyaml(clist, odict, data)
		r.calculate()
		if '-c' in flags:
			r.printcsv()
		else:
			r.printit(odict.get('miniprint', False))
	except PilotError, pe:
		print 'Pilot Error: ' + str(pe)
		raise SystemExit, 1
	except IOError, e:
		print e
	sys.exit(0)

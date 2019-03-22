#!/usr/bin/env python3

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

from WBC.WBC import Recipe, WBC
from WBC.Hop import Hop
from WBC.Mash import Mash
from WBC.Units import Mass, Temperature, Volume, Strength
from WBC.Units import _Mass, _Temperature, _Volume
from WBC.Utils import PilotError
from WBC import Sysparams
from WBC import Parse

import getopt
import io
import sys

hoptypes = { 'leaf' : Hop.Leaf, 'pellet': Hop.Pellet }

def dohop(r, hopspec, unit, timespec):
	typstr = hopspec[2] if len(hopspec) > 2 else 'pellet'
	if typstr not in hoptypes:
		raise PilotError('invalid hop type: ' + typstr)
	typ = hoptypes[typstr]
	aa = Parse.percent(hopspec[1])
	hop = Hop(hopspec[0], aa, typ)

	fun, hu = Parse.hopunit(unit)
	ts = Parse.timespec(timespec)
	fun(r, hop, hu, ts)

def dohops(r, d_hops):
	for h in d_hops:
		dohop(r, h[0], h[1], h[2])

def dofermentables(r, ferms):
	fermtype = None
	for stage in WBC.stages:
		for f in ferms.get(stage, []):
			(fun, v) = Parse.fermentableunit(ferms[stage][f])
			fun(r, f, v, stage)

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

		if p == 'method':
			m = Parse.mashmethod(value)
			r.mash.set_method(m)

		elif p == 'temperature' or p == 'temperatures':
			if isinstance(value, str):
				mashsteps = [Parse.mashstep(value)]
			elif isinstance(value, list):
				mashsteps = [Parse.mashstep(x) for x in value]
			else:
				raise PilotError('mash temperature must be '
				    'given as a string or list of strings')
			r.mash.set_steps(mashsteps)

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

	if 'volume_scale' in odict:
		r.set_volume_and_scale(odict['volume_scale'])
	if 'volume_noscale' in odict:
		r.set_volume(odict['volume_noscale'])

	for n in odict.get('notes', []):
		r.add_note(n)

def processyaml(clist, odict, data):
	# importing yaml is unfathomably slow, so do it only if we need it
	import yaml

	try:
		d = yaml.safe_load(data.read())
	except (yaml.parser.ParserError, e):
		print('>> failed to parse yaml recipe:')
		print(e)
		sys.exit(1)

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
		'defs'		: lambda *x: None,
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
	dataver = -1
	r = None
	# don't use csv, because using utf-8+csv on python2 is
	# just too painful
	for line in data.read().splitlines():
		row = line.split('|')
		if row[0][0] is "#":
			continue

		if row[0] == "wbcdata":
			dataver = int(row[1])
		if dataver == 1:
			massunit = Mass.G
			masssfx = 'g'
		elif dataver == 2:
			massunit = Mass.KG
			masssfx = 'kg'
		else:
			raise PilotError("unsupported wbcdata version")

		if row[0] == "recipe":
			r = Recipe(row[1], row[2], _Volume(row[4]), int(row[3]))
			applyparams(r, clist, odict)

		elif row[0] == "mash":
			mashsteps = [Parse.mashstep(x) for x in row[2:]]
			r.mash.set_steps(mashsteps)

		elif row[0] == "fermentable":
			r.fermentable_bymass(row[1],
			    Mass(float(row[2]), massunit), row[3])

		elif row[0] == "hop":
			dohop(r, [row[1], row[3] + '%', row[2]],
			    row[4] + masssfx, row[6])
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
			if 'volume_scale' in odict:
				raise PilotError('can give max one of -v/-V')
			odict['volume_noscale'] = v
		elif o == '-V':
			v = Parse.volume(a)
			if 'volume_noscale' in odict:
				raise PilotError('can give max one of -v/-V')
			odict['volume_scale'] = v

	return (clist, odict)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'cdhmn:p:P:s:v:V:')
	if len(args) > 1:
		usage()

	try:
		(clist, odict) = processopts(opts)
		flags = [x[0] for x in opts]
		with io.open(args[0], "r", encoding='utf-8') \
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
			from WBC import OutputText
			OutputText.printit(r.input, r.results,
			    odict.get('miniprint', False))
	except PilotError as pe:
		print('Pilot Error: ' + str(pe))
		sys.exit(1)
	except IOError as e:
		print(e)
	sys.exit(0)

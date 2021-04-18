#!/usr/bin/env python3

#
# Copyright (c) 2019, 2021 Antti Kantee <pooka@iki.fi>
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

from WBC.wbc import Recipe
from WBC.units import Mass, _Mass, Strength, _Strength, Volume, _Volume
from WBC import parse
from WBC.worter import Worter
from WBC.utils import PilotError

import getopt
import os
import sys

def usage():
	sys.stderr.write('usage: ' + os.path.basename(sys.argv[0])
	    + ' [-f final_strength[,adjustment_RA%]]\n'
	    + '\tstrength vol mass[@extract%]|vol@strength [...]\n')
	sys.exit(1)

def printline2(fname, value1, value2):
	print('{:28}:{:>14}{:>14}'.format(fname, value1, value2))
def printline3(fname, value1, value2, value3):
	print('{:28}:{:>14}{:>14}{:>14}'.format(fname, value1, value2, value3))
def printsep(txt):
	sep=10*"="
	print("\t {} {} {}".format(sep, txt, sep))
	print()

def oneround(w_orig, args, n):
	w_adj = Worter()
	w_new = Worter()

	arg = args[n]

	if '@' in arg:
		if '%' in arg:
			mass_adj, percent = parse.split(arg, '@',
			    parse.mass, parse.percent)

			ext_adj = _Mass(mass_adj * percent/100.0)
			w_adj.adjust_extract(ext_adj)
			w_adj.adjust_water(_Mass(mass_adj - ext_adj))
		else:
			vol_adj, s_adj = parse.split(arg, '@',
			    parse.volume, parse.strength)
			w_adj.set_volstrength(vol_adj, s_adj)
	else:
		try:
			m = parse.mass(arg)
			w_adj.adjust_extract(m)
		except PilotError:
			v = parse.volume(arg)
			w_adj.adjust_water(_Mass(v))

	printsep("Adjustment {}: \"{}\"".format(n+1, arg))

	w_new = w_orig + w_adj

	printline2('Strength, Original',
	    w_orig.strength().stras(Strength.PLATO),
	    w_orig.strength().stras(Strength.SG))
	printline2('Strength, Aggregate',
	    w_new.strength().stras(Strength.PLATO),
	    w_new.strength().stras(Strength.SG))

	print()
	printline2('Extract, Original',
	    w_orig.extract().stras_system('metric'),
	    w_orig.extract().stras_system('us'))
	printline2('Extract, Added',
	    w_adj.extract().stras_system('metric'),
	    w_adj.extract().stras_system('us'))
	printline2('Extract, Aggregate',
	    w_new.extract().stras_system('metric'),
	    w_new.extract().stras_system('us'))

	print()
	printline2('Water, Original',
	    w_orig.water().stras_system('metric'),
	    w_orig.water().stras_system('us'))
	printline2('Water, Added',
	    w_adj.water().stras_system('metric'),
	    w_adj.water().stras_system('us'))
	printline2('Water, New',
	    w_new.water().stras_system('metric'),
	    w_new.water().stras_system('us'))

	print()
	printline2('Volume, Original',
	    w_orig.volume().stras_system('metric'),
	    w_orig.volume().stras_system('us'))
	printline2('Volume, Aggregate',
	    w_new.volume().stras_system('metric'),
	    w_new.volume().stras_system('us'))

	return w_new

def do_sfin(s_fin, ra_arg, w_orig, w_new):
	r = w_orig.strength().attenuate_bystrength(s_fin)
	ra = r['ra']
	if ra_arg is None:
		ra_adj = 100.0
		aa = r['aa']
	else:
		ra_adj = ra_arg
		aa = None

	w_adj = w_new - w_orig

	# calculate aggregate RA, which is supplied RA for
	# the original plus the given RA (if RA was not given,
	# we'll calculate both 100% RA and [implicitly] given AA)
	wantedra = (100*(w_orig.extract()*ra/100.0
	    + w_adj.extract()*ra_adj/100.0)
	    / (w_orig.extract() + w_adj.extract()))
	s_guess = _Strength(w_new.strength()/2)

	# considering the formula for real extract (WBC/Units::Strength)
	# I'm not too keen on solving real attenuation analytically.
	# takes usually <=5 loops.
	while True:
		r = w_new.strength().attenuate_bystrength(s_guess)
		ra_delta = r['ra'] - wantedra
		if abs(ra_delta) < 0.01:
			break

		# adjust by the fraction of the range that
		# we're off by.  we don't hit it on the first tries
		# due to the non-linear nature, but we'll get close(r).
		s_guess = _Strength(s_guess + w_new.strength()*ra_delta/100.0)

	s_ra = s_guess
	abv_ra = r['abv']
	if aa is not None:
		r = w_new.strength().attenuate_bypercent(aa)
		s_aa = r['ae']
		abv_aa = r['abv']

	print()
	printsep('Final strength estimate')
	printline3('Final Strength (' + str(int(ra_adj)) + '% adj RA)',
	    s_ra.stras(Strength.PLATO), s_ra.stras(Strength.SG),
	    '{:.1f}% ABV'.format(abv_ra))
	if aa is not None:
		printline3('Final Strength (' + str(int(aa)) + '% AA)',
		    s_aa.stras(Strength.PLATO), s_aa.stras(Strength.SG),
		    '{:.1f}% ABV'.format(abv_aa))

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'f:')

	if len(args) < 3:
		usage()

	s_fin = ra_arg = None
	for o, a in opts:
		if o == '-f':
			if ',' in a:
				s_fin, ra_arg = parse.split(a, ',',
				    parse.strength, parse.percent)
				if ra_arg < 0.0 or ra_arg > 100.0:
					raise PilotError('need 0 < RA <= 100')
			else:
				s_fin = parse.strength(a)
		elif o == '-h':
			usage()

	w_orig = Worter()
	w_orig.set_volstrength(parse.volume(args[1]), parse.strength(args[0]))

	args = args[2:]
	w = w_orig
	for n in range(len(args)-1):
		w = oneround(w, args, n)
		print()
	w = oneround(w, args, len(args)-1)

	if s_fin is not None:
		do_sfin(s_fin, ra_arg, w_orig, w)

	sys.exit(0)

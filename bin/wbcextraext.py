#!/usr/bin/env python3

#
# Copyright (c) 2019 Antti Kantee <pooka@iki.fi>
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
from WBC.utils import PilotError

import getopt
import os
import sys

def usage():
	sys.stderr.write('usage: ' + os.path.basename(sys.argv[0])
	    + ' [-f final_strength[,addition_RA%]]\n'
	    + '\tstrength vol mass[@extract%]|vol@strength\n')
	sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'f:')

	if len(args) != 3:
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

	s_orig = parse.strength(args[0])
	vol_orig = parse.volume(args[1])

	if '@' in args[2]:
		if '%' in args[2]:
			mass_add, percent = parse.split(args[2], '@',
			    parse.mass, parse.percent)
			ext_add = _Mass(mass_add * percent/100.0)
		else:
			vol_add, s_add = parse.split(args[2], '@',
			    parse.volume, parse.strength)
			mass_add = _Mass(s_add.valueas(s_add.SG) * vol_add)
			ext_add = _Mass(mass_add * s_add/100.0)
	else:
		ext_add = mass_add = parse.mass(args[2])

	mass_orig = _Mass(s_orig.valueas(s_orig.SG) * vol_orig)
	ext_orig = _Mass(mass_orig * s_orig/100.0)

	ext_new = _Mass(ext_orig + ext_add)
	mass_new = _Mass(mass_orig + mass_add)

	s_new = _Strength(100.0*ext_new / mass_new)
	vol_new = _Volume(mass_new / s_new.valueas(s_new.SG))

	water_orig = _Mass(mass_orig - ext_orig)
	water_new = _Mass(mass_new - ext_new)

	if s_fin is not None:
		r = s_orig.attenuate_bystrength(s_fin)
		ra = r['ra']
		if ra_arg is None:
			ra_add = 100.0
			aa = r['aa']
		else:
			ra_add = ra_arg
			aa = None

		# calculate aggregate RA, which is supplied RA for
		# the original plus the given RA (if RA was not given,
		# we'll calculate both 100% RA and [implicitly] given AA)
		wantedra = 100*(ext_orig*ra/100.0 + ext_add*ra_add/100.0) \
		    / (ext_orig + ext_add)
		s_guess = _Strength(s_new/2)

		# considering the formula for real extract (WBC/Units::Strength)
		# I'm not too keen on solving real attenuation analytically.
		# takes usually <=5 loops.
		while True:
			r = s_new.attenuate_bystrength(s_guess)
			ra_delta = r['ra'] - wantedra
			if abs(ra_delta) < 0.01:
				break

			# adjust by the fraction of the range that
			# we're off by.  we don't hit it on the first tries
			# due to the non-linear nature, but we'll get close(r).
			s_guess = _Strength(s_guess + s_new*ra_delta/100.0)

		s_ra = s_guess
		abv_ra = r['abv']
		if aa is not None:
			r = s_new.attenuate_bypercent(aa)
			s_aa = r['ae']
			abv_aa = r['abv']

	def printline2(fname, value1, value2):
		print('{:28}:{:>14}{:>14}'.format(fname, value1, value2))
	def printline3(fname, value1, value2, value3):
		print('{:28}:{:>14}{:>14}{:>14}'.format(fname,
		    value1, value2, value3))

	printline2('Strength, Original',
	    s_orig.stras(Strength.PLATO), s_orig.stras(Strength.SG))
	printline2('Strength, Aggregate',
	    s_new.stras(Strength.PLATO), s_new.stras(Strength.SG))

	print()
	printline2('Extract, Original',
	    ext_orig.stras_system('metric'), ext_orig.stras_system('us'))
	printline2('Extract, Added',
	    ext_add.stras_system('metric'), ext_add.stras_system('us'))
	printline2('Extract, Aggregate',
	    ext_new.stras_system('metric'), ext_new.stras_system('us'))

	print()
	printline2('Water, Original',
	    water_orig.stras_system('metric'), water_orig.stras_system('us'))
	printline2('Water, New',
	    water_new.stras_system('metric'), water_new.stras_system('us'))

	print()
	printline2('Volume, Original',
	    vol_orig.stras_system('metric'), vol_orig.stras_system('us'))
	printline2('Volume, Aggregate',
	    vol_new.stras_system('metric'), vol_new.stras_system('us'))

	if s_fin is not None:
		print()
		printline3('Final Strength (' + str(int(ra_add)) + '% add RA)',
		    s_ra.stras(Strength.PLATO), s_ra.stras(Strength.SG),
		    '{:.1f}% ABV'.format(abv_ra))
		if aa is not None:
			printline3('Final Strength (' + str(int(aa)) + '% AA)',
			    s_aa.stras(Strength.PLATO), s_aa.stras(Strength.SG),
			    '{:.1f}% ABV'.format(abv_aa))

	sys.exit(0)

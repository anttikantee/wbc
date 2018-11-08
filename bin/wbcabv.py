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

from WBC.WBC import Recipe
from WBC.Units import Mass, Temperature, Volume, Strength, _Strength
from WBC.Utils import PilotError
from WBC import Parse

import getopt
import sys

def usage():
        sys.stderr.write('usage: ' + sys.argv[0] + ' [-r]\n'
            + '\toriginal_strength final_strength|apparent_attenuation%\n')
        sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'r')

	rflag = '-r' in [x[0] for x in opts]

	if len(args) != 2:
		usage()

	s_orig = Parse.strength(args[0])

	if '%' in args[1]:
		if rflag: raise PilotError('use refractometer reading with -r')
		attn = Parse.percent(args[1])
		r = s_orig.attenuate_bypercent(attn)
	else:
		s_fin_arg = Parse.strength(args[1])

		if rflag:
			s_fin = s_orig.refractometer_correction(s_fin_arg)
		else:
			s_fin = s_fin_arg
		r = s_orig.attenuate_bystrength(s_fin)

	def printline(fname, value):
		print u'{:28}:{:>12}'.format(fname, value)
	def printline2(fname, value1, value2):
		print u'{:28}:{:>12}{:>12}'.format(fname, value1, value2)
	def printstrength(what, s):
		printline2(what, s.stras(Strength.PLATO), s.stras(Strength.SG))

	printstrength('Original Strength', s_orig)
	if rflag:
		printstrength('Final Strength (apparent)', s_fin_arg)
		printstrength('Final Strength (corrected)', r['ae'])
	else:
		printstrength('Final Strength (apparent)', r['ae'])

	print

	def extractwvprint(what, str):
		v = r[what]
		v_us = Mass(v, Mass.G).valueas(Mass.OZ) \
		    / Volume(1, Volume.QUART)
		printline2(str + ' Extract (w/v)',
		    '{:.1f} g/l'.format(v), '{:.1f} oz/qt'.format(v_us))

	extractwvprint('oe_gl', 'Original ')
	extractwvprint('re_gl', 'Remaining')

	printline('Remaining Extract (w/w)', r['re'].stras(Strength.PLATO))
	print
	printline('Apparent attenuation (/sg)', '{:.1f}%'.format(r['aa']))
	printline('Real attenuation (/plato)', '{:.1f}%'.format(r['ra']))
	print
	printline('ABV', '{:.1f}%'.format(r['abv']))
	printline('ABW', '{:.1f}%'.format(r['abw']))

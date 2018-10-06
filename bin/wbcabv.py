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
from WBC import Parse

import getopt
import sys

def usage():
        sys.stderr.write('usage: ' + sys.argv[0]
            + ' original_strength final_strength|apparent_attenuation%\n')
        sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], '')

	if len(args) != 2:
		usage()

	s_orig = Parse.strength(args[0])

	if '%' in args[1]:
		attn = Parse.percent(args[1]) / 100.0
		s_fin  = _Strength(100 * int(s_orig * (1-attn)) / 100)
		s_fin_unit = s_orig.inputunit
	else:
		s_fin  = Parse.strength(args[1])
		s_fin_unit = s_fin.inputunit
		attn = 1 - s_fin/s_orig

	(x, abv) = s_orig.attenuate(attn)

	def printline(fname, value):
		print u'{:21}:{:>8}'.format(fname, value)

	printline('Orig. Strength', s_orig.stras(s_orig.inputunit))
	printline('Final Strength', s_fin.stras(s_fin_unit))
	printline('Apparent attenuation', '{:.1f}%'.format(100*attn))
	printline('Real attenuation', '{:.1f}%'.format(81.92*attn))
	print
	printline('ABV', '{:.1f}%'.format(abv))

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
from WBC import fermentables
from WBC.utils import PilotError

import getopt
import sys

def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-m maltster] product\n')
	sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'm:v')

	if len(args) == 0:
		product = None
	elif len(args) == 1:
		product = args[0]
	else:
		usage()

	maltster = None
	verbose = False
	for o, a in opts:
		if o == '-m':
			maltster = a
		elif o == '-v':
			verbose = True

	l = fermentables.Search(maltster, product)
	if len(l) == 0:
		print('No match')
		sys.exit(0)
	for x in l:
		print(x.name)
		if verbose:
			def prtln(what, f1, f2):
				fmtstr = '\t{:16}: {:>12}{:>12}'
				print(fmtstr.format(what, f1, f2))
			prtln('Extract CGAI', str(x.extract), '')
			c = x.color
			prtln('Color', '{:.1f} EBC'.format(c.valueas(c.EBC)),
			    '{:.1f} L'.format(c.valueas(c.LOVIBOND)))
			d = x.diap
			if d == 0:
				dstr = ('none', '')
			else:
				dstr = ('{:}'.format(d.stras(d.WK)),
				    '{:}'.format(d.stras(d.L)))
			prtln('Diastatic power', dstr[0], dstr[1])
			if not x.needmash:
				print('\tNo mash required')

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
from WBC.Units import Mass, Temperature, Volume, Strength
from WBC import Parse

import getopt
import sys

def usage():
        sys.stderr.write('usage: ' + sys.argv[0]
            + ' original_strength final_strength\n')
        sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], '')

	if len(args) != 2:
		usage()

	s_orig = Parse.strength(args[0])
	s_fin  = Parse.strength(args[1])
	attn = 1 - s_fin/s_orig

	(x, abv) = s_orig.attenuate(attn)
	print 'ABV: {:.1f}%, Apparent attenuation: {:.0f}%'\
	    .format(abv, 100*attn)

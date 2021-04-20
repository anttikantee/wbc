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

from WBC.sysparams import decodeparamshorts
from WBC.utils import PilotError

import getopt
import sys

def usage():
	sys.stderr.write('usage: ' + sys.argv[0] + ' paramstring\n')
	sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], '')

	if len(args) != 1:
		usage()

	try:
		res = decodeparamshorts(args[0])
		longest = max([len(x[0]) for x in res])
		fmtstr = '{:' + str(longest) + '} = {:}'
		for x in res:
			print(fmtstr.format(x[0], x[1]))
	except PilotError as e:
		print(e)
		sys.exit(1)
	sys.exit(0)

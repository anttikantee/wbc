#!/usr/bin/env python3

#
# Copyright (c) 2021 Antti Kantee <pooka@iki.fi>
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
from WBC.units import *
from WBC.units import _Mass, _Volume
from WBC import parse
from WBC.worter import Worter
from WBC.utils import PilotError

from WBC import brewutils

import getopt
import os, sys

def usage():
	sys.stderr.write('usage: ' + os.path.basename(sys.argv[0])
	    + ' [-e extract %]\n'
	    + '\tvolume|extract[@%]|strength volume|extract[@%]|strength\n')
	sys.exit(1)

def printline2(fname, value1, value2):
	print('{:28}:{:>14}{:>14}'.format(fname, value1, value2))
def printline2_system(fname, o):
	printline2(fname, o.stras_system('metric'), o.stras_system('us'))

def main(argv):
	opts, args = getopt.getopt(argv[1:], 'e:')

	wegot = {}

	def ep():
		if 'ep' in wegot:
			return wegot['ep']
		return 1.0

	for o, a in opts:
		if o == '-e':
			wegot['ep'] = parse.percent(a)/100.0

	if len(args) != 2:
		usage()

	def attempt(what):
		def extparse(arg):
			if '@' in arg:
				if 'ep' in wegot:
					# XXX (can't throw piloterror)
					sys.stderr.write('Extract percentage '
					    + 'given more than once\n')
					usage()
				v = arg.split('@')
				pers = parse.percent(v[1])/100.0
				wegot['ep'] = pers
				return _Mass(parse.mass(v[0]))
			return parse.mass(arg)

		for m in [ extparse, parse.volume, parse.strength ]:
			try:
				v = m(what)
				wegot[v.__class__] = v
				return
			except PilotError:
				# XXX: PilotError lossage, might be fatal error
				pass
		usage()
	attempt(args[0])
	attempt(args[1])

	def m(): return wegot[Mass]
	def v(): return wegot[Volume]
	def s(): return wegot[Strength]
	def e(): return _Mass(m() * ep())

	if Mass in wegot and Volume in wegot:
		wegot[Strength] = brewutils.solve_strength(e(), v())
		# "FALLTHROUGH"

	if Mass in wegot and Strength in wegot:
		w_mass = _Mass(e() / (s()/100.0) - e())
		w = Worter(e(), w_mass)
	elif Volume in wegot and Strength in wegot:
		w = Worter()
		w.set_volstrength(v(), s())
	else:
		sys.stderr.write('ERROR: need two different types\n')
		usage()

	ext = w.extract()
	ferm = _Mass(ext / ep())
	fermwater = _Mass(ferm * (1-ep()))

	waterreq = w.water() - fermwater
	if waterreq < 0:
		raise PilotError('fermentable strength below target strength')

	printline2_system('Fermentable (' + str(int(ep()*100)) + '%) addition',
	    ferm)
	printline2_system('    of which extract', ext)
	printline2_system('    of which water', fermwater)
	printline2_system('Water addition', _Volume(waterreq))

	ws = w.strength()
	printline2_system('=> Volume', w.volume())
	printline2('=> Strength', ws.stras(ws.PLATO), ws.stras(ws.SG))

if __name__ == '__main__':
	try:
		main(sys.argv)
	except PilotError as e:
		print(e)
		sys.exit(1)
	sys.exit(0)

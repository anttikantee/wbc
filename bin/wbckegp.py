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
from WBC.Units import Temperature, Pressure, Mass, Volume
from WBC import Brewutils
from WBC import Parse
from WBC.Utils import PilotError
from WBC import Constants

import getopt
import sys

def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-v keg volume]\n'
	    + '\ttemperature|pressure|(vols|co2 w/v) '
	    + 'temperature|pressure|(vols|co2 w/v)\n')
	sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'hv:')

	if len(args) != 2:
		usage()

	kegvol = None
	for o, a in opts:
		if o == '-v':
			kegvol = Parse.volume(a)
		elif o == '-h':
			usage()

	wegot = {}
	def attempt(what):
		for m in [ Parse.pressure, Parse.temp,
		    lambda x: Parse.ratio(x, Parse.mass, Parse.volume), float ]:
			try:
				v = m(what)
				wegot[v.__class__] = v
				return
			except (PilotError, ValueError):
				pass
		usage()
	attempt(args[0])
	attempt(args[1])

	# if wegot CO2 w/v, convert to volumes
	if tuple in wegot:
		t = wegot[tuple]
		wegot[float] = (t[0] / t[1]) / Constants.co2_stp_gl

	def p(): return wegot[Pressure]
	def t(): return wegot[Temperature]
	def v(): return wegot[float]

	if Pressure in wegot and Temperature in wegot:
		v3 = Brewutils.co2_vols_at_pressuretemperature(p(), t())
	elif Pressure in wegot and float in wegot:
		v3 = Brewutils.co2_temperature_at_pressurevols(p(), v())
	elif Temperature in wegot and float in wegot:
		v3 = Brewutils.co2_pressure_at_temperaturevols(t(), v())
	else:
		sys.stderr.write('ERROR: need two different types\n')
		usage()
	wegot[v3.__class__] = v3

	co2head_gl = Brewutils.co2_headspace(p(), t())

	def wvtous(x):
		return Mass(x, Mass.G).valueas(Mass.OZ) \
		    / Volume(1, Volume.QUART)

	print '{:24}:{:>12}{:>12}'.format('Pressure',
	    p().stras(Pressure.BAR), p().stras(Pressure.PSI))
	print u'{:24}:{:>12}{:>12}'.format('Temperature',
	    t().stras(Temperature.degC), t().stras(Temperature.degF))
	print '{:24}:{:>12.1f}'.format('CO2 (v/v)', v())
	print

	co2gl = v() * Constants.co2_stp_gl
	print '{:24}:{:>12}{:>12}'.format('Dissolved CO2 (w/v)',
	    '{:.2f}'.format(co2gl) + ' g/l',
	    '{:.2f}'.format(wvtous(co2gl)) + ' oz/qt')

	print '{:24}:{:>12}{:>12}'.format('Headspace CO2 (w/v)',
	    '{:.2f}'.format(co2head_gl) + ' g/l',
	    '{:.2f}'.format(wvtous(co2head_gl)) + ' oz/qt')

	if kegvol is not None:
		print
		co2dis = Mass(co2gl * kegvol, Mass.G)
		print '{:24}:{:>12}{:>12}'.format('Dissolved CO2 (init.)',
		    co2dis.stras(Mass.G), co2dis.stras(Mass.OZ))
		co2head = Mass(co2head_gl * kegvol, Mass.G)
		print '{:24}:{:>12}{:>12}'.format('Headspace CO2 (final)',
		    co2head.stras(Mass.G), co2head.stras(Mass.OZ))
		co2total = Mass(co2dis + co2head, Mass.G)
		print '{:24}:{:>12}{:>12}'.format('Total CO2 use',
		    co2total.stras(Mass.G), co2total.stras(Mass.OZ))

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

#
# This utility takes as input the wort volume and temperature
# (defaulting to boiling) and strength (defaulting to 12 Plato),
# desired temperature, the coolant (water) temperature and either
# coolant volume or cooling efficiency, and calculates the missing
# parameter.
# (water is called coolant because wort and water both start with "w")
#
# There are two approaches to cooling wort.  One is the "differential
# heat exchanger" method, such as a plate chiller or immersion chiller,
# and the other is a "lump heat exchanger" such as putting the pot
# of wort in a sink filled with water.  The former will get you cooler
# wort with the same amount of water; in the latter method you will
# end up with colder coolant and hotter wort.
#
#                                    t(n-1) * wm * whr + ct * cd
# Cooling can be modeled as: t(n) =  ---------------------------
#                                           wm * whr + cd
#
# where:
#	wm  = wort weight (= specific gravity * volume)
#	whr = wort specific heat relative to coolant
#	ct  = temperature of coolant
#       cd  = coolant differential mass
#
# Notably, the weight of a volume of wort goes up as the strength goes
# up, but the specific heat goes down, so it "almost" stays the same
# as water.  The specific heat also changes as a function of temperature,
# but to keep things simple, and especially since I didn't find an
# equation for how it changes, we ignore the temperature-dependency.
# We approximate the wort as a sucrose solution and can therefore
# use this formula:
#
#	absolute specific heat = 4.1868 - 0.0293*deg Plato
#   via Martin Brungard on rec.crafts.brewing: https://narkive.com/qefoOIz3.8
#
# therefore, with cc designating coolant heat capacity:
#	whr = (4.1868 - 0.0293*deg Plato)/cc
#
# The formula seems to roughly match the table from the April 1895 (no,
# that's not a typo) Ice and Refridgeration article "Arithmetic of
# Brewery Refridgeration", so we'll call it good enough for our
# purposes.
#

from WBC.wbc import Recipe
from WBC.units import Temperature, _Temperature, Strength, _Strength
from WBC.units import Mass, _Mass, Volume, _Volume
from WBC import parse
from WBC.utils import PilotError
from WBC import brewutils

import getopt
import sys

def usage():
	sys.stderr.write('usage: ' + sys.argv[0]
	    + ' [-d differential_coolant_volume]\n'
	    + '\t[-s wort_strength] [-t wort_temperature]\n'
	    + '\ttarget_temperature wort_volume coolant_temperature\n'
	    + '\t[coolant_volume|efficiency%]\n')
	sys.exit(1)

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], 'c:d:hi:s:t:')

	if len(args) != 3 and len(args) != 4:
		usage()

	# not sure why so many decimals, since the values change as a
	# function of temperature, but try to pick "average" values ...
	#
	# water goes from 4.22 @ 0degC to 4.1796 @ 40degC to 4.2157 @ 100degC
	# ice goes from 2.050 @ 0degC to 1.882 @ -30degC
	waterc = 4.1844		# (@  20degC)
	icec = 2.000		# (@ -10degC)
	icemelt = 333.61	# (@ 0.00degC, according to CRC)

	wt_orig = _Temperature(100)
	ws = _Strength(12)
	cd = None
	cc = waterc
	icemass = None
	strenset = False

	for o, a in opts:
		if o == '-c':
			# allow setting the heat capacity of the coolant
			# just for playing around.  undocumented.
			cc = float(a)
		elif o == '-d':
			cd = parse.volume(a)
		elif o == '-i':
			if '@' in a:
				icemass, icetemp = parse.split(a, '@',
				    parse.mass, parse.temperature)
			else:
				icemass = parse.mass(a)
				icetemp = _Temperature(-10)
		elif o == '-s':
			ws = parse.strength(a)
			strenset = True
		elif o == '-t':
			wt_orig = parse.temperature(a)
		elif o == '-h':
			usage()

	whc = waterc - 0.0293*ws
	whr = whc / cc
	wt = wt_orig

	tt = parse.temperature(args[0])
	wv = parse.volume(args[1])
	ct = parse.temperature(args[2])

	# compensate for temperature.  assume wort follows water
	# heat expansion (probably ok?)
	wm = _Mass(brewutils.water_voltemp_to_mass(wv, wt)
	    * ws.valueas(Strength.SG))

	# solve "perfect score".  if the differential size isn't
	# specified, use wort-volume / 10*1000 (for no particular
	# reason except it's small enough to be close-to-differential
	# but large enough for the computation to not take eons)
	if cd is None:
		cd = wv / 10000.0
	else:
		cd = float(cd)
	totalc = 0

	# first, deal with the ice.  assume that the given amount of ice
	# draws the heat out with 100% efficiency.  that might happen
	# if recirculating and might not happen if pre-chilling.
	# oh well, we really have to approximate somewhere ...
	# (also, ignores the temperature of the water after the ice
	# has melted)
	if icemass is not None:
		icecool = icemass * icec * (-icetemp) + icemass * icemelt

		wh = wm * whc * wt
		wh_new = max(tt * whc * wm, wh - icecool)
		wt = wh_new / (wm * whc)

		icepost = _Temperature(wt)
		iceused = 100.0*(wh-wh_new) / icecool

	tempmin = 0.001
	if wt > tt + tempmin and tt < ct + tempmin:
		raise PilotError('coolant not cool enough')

	while wt > tt + tempmin:
		# first, figure out how much water we need to complete
		# the cooling in one step.  then choose the min of the
		# differential and the amount required.  solving our
		# heat model equation for cd we get:
		cd_max = (wm*whr*(wt-tt))/(tt - ct)
		if cd_max < cd:
			cd = cd_max

		# now, calculate where we can get
		wt = (wt * wm * whr + ct * cd) / (wm * whr + cd)
		totalc += cd
	cv_perfect = _Volume(totalc)

	# yea I still don't understand the logic of python scoping,
	# so we'll just work around it with a map
	solutions = {}
	def solve_efficiency(vol):
		eff = 100.0 * (cv_perfect / vol)
		if eff > 100.0:
			raise PilotError('over 100% efficiency')
		solutions['volume'] = vol
		solutions['efficiency'] = eff

	def solve_volume(eff):
		solutions['efficiency'] = eff
		cv = _Volume(cv_perfect / (eff/100.0))
		solutions['volume'] = cv

	stab = {
		parse.volume : solve_efficiency,
		parse.percent : solve_volume,
	}

	# solve what we want, volume or efficiency
	def do(arg):
		for m in stab.keys():
			try:
				v = m(arg)
				stab[m](v)
				return
			except (PilotError, ValueError):
				pass
		usage()
	if len(args) == 4:
		what = args[3]
	else:
		what = '100%'
	do(what)

	# print results
	def printline_both(fname, v):
	    print('{:28}:{:>14}{:>14}'.format(fname,
		v.stras_system('metric'), v.stras_system('us')))
	def printline3(fname, v1, v2, v3):
	    print('{:28}:{:>14}{:>14}{:>14}'.format(fname, v1, v2, v3))

	printline_both('Wort volume before cooling', wv)
	printline_both('Wort temperature', wt_orig)
	wsstr = 'Wort strength'
	if not strenset:
		wsstr += ' [default]'
	printline3(wsstr, ws.stras(Strength.PLATO), ws.stras(Strength.SG),
	    'C/Cc: {:.3f}'.format(whr))
	printline_both('Wort mass', wm)

	print()
	printline_both('Coolant temperature', ct)
	effstr = '{:.0f}%'.format(solutions['efficiency'])
	printline_both('Coolant required (' + effstr + ' eff.)',
	    solutions['volume'])

	if icemass is not None:
		print()
		printline_both('Ice cools wort to', icepost)
		printline3('Ice melted', '{:.1f}%'.format(iceused), '', '')

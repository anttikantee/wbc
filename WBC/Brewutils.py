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

from Utils import PilotError
from Units import *
from Units import _Volume

import Constants

# figure out wort strength for given mass of extract and volume
def solve_strength(extract, volume):
	checktypes([(extract, Mass), (volume, Volume)])
	# first, calculate the starting point, approximate mass = volume
	# we will undershoot (because extract is heavier than water)
	mass = volume

	# actual volume of that amount of solution is the guess volume
	# divided by SG.  just keep creeping up the volume until we get
	# a reasonable accuracy.  numerical methods require no brains.
	# Usually getting to 10^-6 of the target takes 2 loops for weak
	# <20deg Plato worts and 3 loops for really strong worts.
	# I am guessing the plato_to_sg calculator is the bottleneck of
	# accuracy in any case.
	loop = 0
	while True:
		plato = 100 * ((extract/1000) / mass)
		diff = volume - mass / Strength.plato_to_sg(plato)
		if diff < 1.0/(1000*1000):
			break
		mass += diff
		loop += 1
		assert(loop < 10)
	return Strength(plato, Strength.PLATO)

def water_vol_at_temp(curvol, curtemp, totemp):
	checktype(curvol, Volume)
	def mycheck(temp):
		checktype(temp, Temperature)
		if temp < 0 or temp > 100:
			raise PilotError('invalid water temperature: '
			    + str(temp))
	mycheck(curtemp)
	mycheck(totemp)

	# water density values from:
	# www.engineeringtoolbox.com/water-density-specific-weight-d_595.html
	#
	# essentially a "quick integral" over the thermal expansion coefficients
	__watertab = {
		1:  0.9999017,
		4:  0.9999749,
		10: 0.9997000,
		15: 0.9991026,
		20: 0.9982067,
		25: 0.9970470,
		30: 0.9956488,
		35: 0.9940326,
		40: 0.9922152,
		45: 0.99021,
		50: 0.98804,
		55: 0.98569,
		60: 0.98320,
		65: 0.98055,
		70: 0.97776,
		75: 0.97484,
		80: 0.97179,
		85: 0.96861,
		90: 0.96531,
		95: 0.96189,
		100: 0.95835,
	}

	def nearest(temp):
		# assumes duplicate dict keys will be overriden
		# (we don't care which equally close one we get)
		tab = {abs(temp-t): __watertab[t] for t in __watertab}
		x = min(tab)
		return tab[x]

	return _Volume(curvol * (nearest(curtemp) / nearest(totemp)))

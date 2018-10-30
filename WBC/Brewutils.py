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

import math

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

# values for carbonation equations
_carbc1 = 0.00021705
_carbc2 = 2617.25
def _ptotal(p):
	return p.valueas(p.BAR) + Pressure(1, p.ATM).valueas(p.BAR)

def co2_vols_at_pressuretemperature(p, t):
	checktypes([(t, Temperature), (p, Pressure)])

	# from http://braukaiser.com/wiki/index.php?title=Carbonation_Tables
	# (Braukaiser refers to his source, but that link is dead, and
	# not available via archive.org either)
	#
	# Cgl = (p+1.013)*(2.71828182845904^(-10.73797+(2617.25/(T+273.15))))*10
	#
	# That's clearly blaablaaa * e^(moreblaablaa), written in a
	# curious way.
	#
	# using Kelvins, and defining ptot = p + atm (in bars), we can
	# write the above equation as:
	#
	# Cgl = 0.00021705*ptot * e^(2617.25/T)
	#
	# the above version is much easier to invert analytically...
	#
	# [research passes ... more research passes]
	#
	# There is another equation (2.1) available via a paper
	# on A.J. deLange's website:
	# http://www.wetnewf.org/pdfs/Brewing_articles/CO2%20Volumes.pdf
	#
	# The equation is a "Henry's law -fitted" (dissolved CO2 = p * H(T))
	# formula for the ASBC carbonation tables.  It has a maximum
	# discrepancy from the ASBC tables by -0.044 volumes, and rms
	# of 0.01 volumes, which we'll call "good enough".  The paper
	# does offer more accurate 2nd and 3rd degree polynomials, and
	# one where H(T) is H(T,p) but ends up recommending using
	# equation 2.1.
	#
	# Now, those two equations are not the same (former is f(p*t)
	# and equation 2.1 is f(p) + g(p*t)).  However, they give
	# similar results, with 2.1 usually producing slightly
	# smaller values (by some 0.0[1-4] volumes).  Specifically
	# at the "largest error" point for equation 2.1 (37degF, 19psi,
	# -0.044 volumes), the difference is 0.040 volumes, making the
	# former equation only 0.004 volumes off.  "yay"
	#
	# Anyway, enough, we'll use the first equation presented in the
	# comment.  For ballparking purposes it is more than adequate,
	# and those who don't want to ballpark probably actually measure
	# the carbonation anyway.

	cgl = _carbc1*_ptotal(p) * math.exp(_carbc2/t.valueas(t.K))
	return cgl / Constants.co2_stp_gl

def co2_pressure_at_temperaturevols(t, v):
	checktype(t, Temperature)

	# given:
	#   Cgl = 0.00021705 * ptot * e^(2617.25/t)
	#
	#   ptot = Cgl / (0.00021705 * e^(2617.25/t))

	cgl = v * Constants.co2_stp_gl
	p = cgl / (_carbc1 * math.exp(_carbc2/t.valueas(t.K)))

	pval = p - Pressure(1, Pressure.ATM).valueas(Pressure.BAR)
	return Pressure(pval, Pressure.BAR)

def co2_temperature_at_pressurevols(p, v):
	checktype(p, Pressure)

	# given:
	#   Cgl = 0.00021705 * ptot * e^(2617.25/t)
	#
	#   t = 2617.25 / ln(Cgl / 0.00021705 * ptot)

	cgl = v * Constants.co2_stp_gl
	t = _carbc2 / math.log(cgl / (_carbc1 * _ptotal(p)))

	return Temperature(t, Temperature.K)

def co2_headspace(p1, t1):
	checktypes([(t1, Temperature), (p1, Pressure)])

	# assuming pV = nRT, with constant V
	#  => n = pV/RT
	#  => n1/n2 = (p1*V/R*T1)/(p2*V/R*T2) = (p1*T2/p2*T1)

	stp_p = Pressure(1, Pressure.BAR)
	stp_t = Temperature(0, Temperature.degC)

	# the P in STP is defined as 1bar (not 1atm), so we can't use
	# _ptotal(), since the other equations use 1atm
	ptotal = Pressure(p1.valueas(Pressure.BAR) + 1, Pressure.BAR)
	ratio = (ptotal.valueas(ptotal.BAR) * stp_t.valueas(stp_t.K)) \
	    / (stp_p.valueas(stp_p.BAR) * t1.valueas(t1.K))

	return ratio * Constants.co2_stp_gl

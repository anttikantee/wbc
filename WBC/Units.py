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

import fractions
import math

from Utils import checktype, checktypes, getconfig

import Constants

class Volume(float):
	DEFAULT	= object()
	LITER	= object()
	GALLON	= object()
	def __new__(cls, value, unit=DEFAULT):
		if unit is Volume.DEFAULT:
			if getconfig('units_input') == 'metric':
				unit = Volume.LITER
			else:
				unit = Volume.GALLON

		if unit is Volume.GALLON:
			value = Constants.literspergallon * value

		return super(Volume, cls).__new__(cls, value)

	def __init__(self, value, unit=DEFAULT):
		super(Volume, self).__init__(value)

	def __str__(self):
		if getconfig('units_output') == 'metric':
			v = self
			sym = 'l'
		else:
			v = self / Constants.literspergallon
			sym = 'gal'

		return '{:.1f}{:s}'.format(v, sym)

class Temperature(float):
	DEFAULT	= object()
	degC	= object()
	degF	= object()
	def __new__(cls, value, unit=DEFAULT):
		if unit is Temperature.DEFAULT:
			if getconfig('units_input') == 'metric':
				unit = Temperature.degC
			else:
				unit = Temperature.degF

		if unit is Temperature.degF:
			value = Temperature.FtoC(value)

		return super(Temperature, cls).__new__(cls, value)

	def __init__(self, value, unit=DEFAULT):
		super(Temperature, self).__init__(value)

	def __str__(self):
		if getconfig('units_output') == 'metric':
			t = self
			sym = 'C'
		else:
			t = Temperature.CtoF(self)
			sym = 'F'
		rv = u'{:.1f}'.format(t) + unichr(0x00b0) + sym
		return unicode(rv)

	@staticmethod
	def FtoC(temp):
		return (temp-32) / 1.8

	@staticmethod
	def CtoF(temp):
		return 1.8*temp + 32

class Mass(float):
	G	= object()
	KG	= object()
	OZ	= object()
	LB	= object()
	def __new__(cls, value, unit):
		if unit is Mass.KG:
			value = 1000 * value
		elif unit is Mass.LB:
			value = Constants.gramsperpound * value
		elif unit is Mass.OZ:
			value = Constants.gramsperounce * value
		else:
			assert(unit is Mass.G)

		return super(Mass, cls).__new__(cls, value)

	def __init__(self, value, unit):
		if unit is Mass.OZ:
			self.small = True
		else:
			self.small = False
		super(Mass, self).__init__(value)

	def valueas(self, unit):
		if unit is Mass.KG:
			return self / 1000.0
		elif unit is Mass.G:
			return self
		else:
			assert(False)

	# output either in "small" units (g/oz) or "large" ones,
	# depending on input unit
	def __str__(self):
		if getconfig('units_output') == 'metric':
			if self < 1000:
				if self < 100:
					dec = '1'
				else:
					dec = '0'
				fmt = '{:.' + dec + 'f}'
				return fmt.format(self) + ' g'
			else:
				return '{:.2f}'.format(self/1000.0) + ' kg'
		else:
			if self.small or self < Constants.gramsperpound:
				small = True
			else:
				small = False
			if small:
				return '{:.2f}'.\
				    format(self/Constants.gramsperounce)+' oz'
			else:
				# format pounds in the "normal" way.  I'd use
				# some expletives here, but it's easier to
				# point to the comment in the Linux kernel
				# sources about renaming directories
				#
				# so, we print pounds as "whole fraction", where
				# fraction is max 1/16th and always a power of
				# two.... because it's logical, I guess
				#
				v = self / Constants.gramsperpound
				whole = int(16*v) / 16
				frac =  int(16*v) % 16
				thestr = ""
				if whole > 0:
					thestr = str(whole) + ' '
				return thestr \
				    + str(fractions.Fraction(frac/16.0)) + ' lb'


class Strength(float):
	PLATO	= object()
	SG	= object()
	SG_PTS	= object()
	DEFAULT	= object()

	def __new__(self, v, which=DEFAULT):
		if which is self.DEFAULT:
			which = {
			    'sg'	: self.SG,
			    'sg_pts'	: self.SG_PTS,
			    'plato'	: self.PLATO,
			}[getconfig('strength_input')]

		if which is Strength.SG:
			return float.__new__(self, self.to_points(v))
		elif which is Strength.SG_PTS:
			return float.__new__(self, v)
		elif which is Strength.PLATO:
			v = self.to_points(self.plato_to_sg(v))
			return float.__new__(self, v)
		else:
			raise Exception('invalid Strength type')

	# I did not trust the various ABV "magic number" formulae on the
	# internet because they lacked explanation.  So, I did a long
	# derivation of ABV calculation based on molar masses.  Those
	# results were off by roughly 5%.  Eventually, I discovered that
	# in addition to churning out CO2 and C2H6O, the sneaky yeasts
	# also produce some solids.
	#
	# Balling's discovery from the 1800's was:
	#   2.0665g extract => 1g C2H6O + 0.9565g CO2 + 0.11g solids
	#     (nb. molar masses of ethanol and CO2 are 46.07 and 44.01,
	#      respectively, so the equation checks out to the 3rd decimal,
	#      and three-figure math is plenty for homebrewing instruments.
	#      I have no idea how he measured with that accuracy so long ago!)
	#
	# ummm, then I got bored, realized how complicated reality actually
	# is, and searched literature for a "working" formula.
	#
	#	ABW = 0.38726*(OE-AE) + 0.00307*(OE-AE)^2
	#
	# Also,
	#
	#	ABW = 0.7907*ABV/SG
	#
	# two of the above from (though the latter indirectly via):
	#
	#    Examination of the Relationships Between Original, Real
	#    and Apparent Extracts, and Alcohol in Pilot Plant
	#    and Commercially Produced Beers
	#        Anthony J. Cutaia, Anna-Jean Reid and R. Alex Speers
	#
	# Now, of course, the following routine gives wildly different
	# values for ABV from all other methods on the interwebs (by some
	# tenths of a percent-unit), but we'll live with it.
	#
	def attenuate(self, aa):
		oe = self.valueas(self.PLATO)
		ae = oe * (1-aa)
		fg = Strength(self * (1-aa), self.SG_PTS)

		abw = 0.38726*(oe-ae) + 0.00307*(math.pow(oe-ae, 2))
		abv = abw * fg.valueas(fg.SG) / 0.7907
		return (fg, abv)

	# I probably should've documented where I got this magic
	# formula from.
	@staticmethod
	def plato_to_sg(plato):
		return 1 + (plato / (258.6 - ((plato/258.2)*227.1)))

	# ditto for this magic formula
	@staticmethod
	def sg_to_plato(sg):
		return -1*616.868			\
		    + (1111.14 * math.pow(sg, 1))	\
		    - (630.272 * math.pow(sg, 2))	\
		    + (135.997 * math.pow(sg, 3))

	@staticmethod
	def to_points(sg):
		return (sg - 1) * 1000

	@staticmethod
	def from_points(points):
		return (points / 1000 + 1)

	@staticmethod
	def name():
		if getconfig('strength_output') == 'plato':
			return unicode(unichr(0x00b0) + 'P')
		else:
			assert(getconfig('strength_output') == 'sg')
			return 'SG'

	def valueas(self, which):
		if which is Strength.SG:
			return self.from_points(self)
		elif which is Strength.SG_PTS:
			return self
		elif which is Strength.PLATO:
			return self.sg_to_plato(self.from_points(self))
		else:
			raise Exception('invalid Strength type')

	def __str__(self):
		if getconfig('strength_output') == 'plato':
			return u'{:.1f}{:}'.format(self.valueas(self.PLATO), \
			    Strength.name())
		else:
			assert(getconfig('strength_output') == 'sg')
			return '{:.3f}'.format(self.valueas(self.SG))

# shorthand names.  if they're confusing to you, use longhand instead.
class M(Mass):
	pass
class S(Strength):
	pass
class T(Temperature):
	pass
class V(Volume):
	pass

# Internally, we always use liters for volume and degC for temperature.
# So, define internal names to avoid having to type the units every
# time.  _Mass and _Strength use the internal value of the
# class (G and SG_PTS, respectively).
class _Volume(Volume):
	def __new__(cls, value):
		return super(_Volume, cls).__new__(cls, value, Volume.LITER)
	def __init__(self, value):
		super(_Volume, self).__init__(value, Volume.LITER)

class _Temperature(Temperature):
	def __new__(cls, value):
		return super(_Temperature, cls).__new__(cls,
		    value, Temperature.degC)
	def __init__(self, value):
		super(_Temperature, self).__init__(value, Temperature.degC)

class _Mass(Mass):
	def __new__(cls, value):
		return super(_Mass, cls).__new__(cls, value, Mass.G)
	def __init__(self, value):
		super(_Mass, self).__init__(value, Mass.G)

class _Strength(Strength):
	def __new__(cls, value):
		return super(_Strength, cls).__new__(cls,value,Strength.SG_PTS)
	def __init__(self, value):
		super(_Strength, self).__init__(value, Strength.SG_PTS)

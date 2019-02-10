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

from WBC.Utils import checktype, checktypes, PilotError

from WBC import Constants

from WBC.Getparam import getparam

def _checksystem(system):
	if system != 'metric' and system != 'us':
		raise PilotError('invalid unit system: ' + system)

class WBCUnit(float):
	def __new__(cls, value, unit):
		rv = super(WBCUnit, cls).__new__(cls, value)
		rv.inputunit = unit
		return rv

	def __init__(self, value, unit):
		super(WBCUnit, self).__init__()

class Volume(WBCUnit):
	LITER	= object()
	QUART	= object()
	GALLON	= object()
	BARREL	= object()

	def __new__(cls, value, unit):
		if unit is Volume.BARREL:
			value = Constants.gallonsperbarrel * value
			unit = Volume.GALLON
		if unit is Volume.GALLON:
			value = Constants.literspergallon * value
		elif unit is Volume.QUART:
			value = Constants.litersperquart * value
		elif unit is not Volume.LITER:
			raise PilotError('invalid Volume unit')

		return super(Volume, cls).__new__(cls, value, unit)

	def __str__(self):
		return self.stras_system(getparam('units_output'))

	def stras(self, which):
		if which == self.LITER:
			v = self
			sym = 'l'
		elif which == self.QUART:
			v = self.valueas(self.QUART)
			sym = 'qt'
		elif which == self.GALLON:
			v = self.valueas(self.GALLON)
			sym = 'gal'
		elif which == self.BARREL:
			v = self.valueas(self.BARREL)
			sym = 'bbl'
		else:
			raise PilotError('unsupported Volume stras unit')
		return '{:.1f}{:s}'.format(v, sym)

	def stras_system(self, system):
		_checksystem(system)
		if system == 'metric':
			return self.stras(self.LITER)
		else:
			if self.valueas(self.GALLON) < 1:
				return self.stras(self.QUART)
			elif self.valueas(self.BARREL) < 1:
				return self.stras(self.GALLON)
			return self.stras(self.BARREL)

	def valueas(self, unit):
		if unit is Volume.LITER:
			return self
		elif unit is Volume.QUART:
			return self / Constants.litersperquart
		elif unit is Volume.GALLON:
			return self / Constants.literspergallon
		elif unit is Volume.BARREL:
			return self.valueas(self.GALLON) \
			    / Constants.gallonsperbarrel
		else:
			assert(False)

class Temperature(WBCUnit):
	degC	= object()
	degF	= object()
	K	= object()

	def __new__(cls, value, unit):
		if unit is Temperature.degF:
			value = Temperature.FtoC(value)
		elif unit is Temperature.K:
			value = value + Constants.absolute_zero_c
		elif unit is not Temperature.degC:
			raise PilotError('invalid Temperature unit')

		return super(Temperature, cls).__new__(cls, value, unit)

	def stras_system(self, system):
		_checksystem(system)
		if system == 'metric':
			return self.stras(self.degC)
		else:
			return self.stras(self.degF)

	def __str__(self):
		return self.stras_system(getparam('units_output'))

	def valueas(self, unit):
		if unit is Temperature.degC:
			return self
		if unit is Temperature.degF:
			return self.CtoF(self)
		elif unit is Temperature.K:
			return self - Constants.absolute_zero_c
		else:
			raise PilotError('invalid Temperature unit')

	def stras(self, which):
		if which is self.K:
			return '{:.2f}'.format(self - Constants.absolute_zero_c)

		if which is self.degC:
			t = self
			sym = 'C'
		elif which is self.degF:
			t = Temperature.CtoF(self)
			sym = 'F'
		else:
			raise PilotError('invalid temperature unit')
		return '{:.1f}'.format(t) + chr(0x00b0) + sym

	@staticmethod
	def FtoC(temp):
		return (temp-32) / 1.8

	@staticmethod
	def CtoF(temp):
		return 1.8*temp + 32

class Mass(WBCUnit):
	MG	= object()
	G	= object()
	KG	= object()
	OZ	= object()
	LB	= object()
	def __new__(cls, value, unit):
		if unit is Mass.G:
			value = value / 1000.0
		elif unit is Mass.MG:
			value = value / (1000.0 * 1000.0)
		elif unit is Mass.LB:
			value = Constants.gramsperpound * value / 1000.0
		elif unit is Mass.OZ:
			value = Constants.gramsperounce * value / 1000.0
		else:
			assert(unit is Mass.KG)

		self = super(Mass, cls).__new__(cls, value, unit)
		if unit is Mass.OZ:
			self.small = True
		else:
			self.small = False
		return self

	def valueas(self, unit):
		if unit is Mass.G:
			return self * 1000.0
		elif unit is Mass.KG:
			return self
		elif unit is Mass.MG:
			return self * 1000.0 * 1000.0
		elif unit is Mass.LB:
			return (self*1000.0) / Constants.gramsperpound
		elif unit is Mass.OZ:
			return (self*1000.0) / Constants.gramsperounce
		else:
			assert(False)

	def stras(self, unit):
		if unit is self.G:
			m = 1000.0 * self
			if m < 100:
				dec = '1'
			else:
				dec = '0'
			fmt = '{:.' + dec + 'f}'
			return fmt.format(m) + ' g'
		elif unit is self.MG:
			return '{:.0f}'.format(self.valueas(self.MG)) + ' mg'
		elif unit is self.KG:
			return '{:.2f}'.format(self) + ' kg'
		elif unit is self.OZ:
			return '{:.2f}'.\
			    format((self*1000.0)/Constants.gramsperounce)+' oz'
		elif unit is self.LB:
			# format pounds in the "normal" way.  I'd use
			# some expletives here, but it's easier to
			# point to the comment in the Linux kernel
			# sources about renaming directories
			#
			# so, we print pounds as "whole fraction", where
			# fraction is max 1/16th and always a power of
			# two.... because it's logical, I guess
			#
			v = (self*1000.0) / Constants.gramsperpound
			whole = int(int(16*v) / 16)
			frac =  int(16*v) % 16
			thestr = ""
			if whole > 0:
				thestr = str(whole) + ' '
			return thestr \
			    + str(fractions.Fraction(frac/16.0)) + ' lb'

	# output either in "small" units (g/oz) or "large" ones,
	# depending on input unit
	def stras_system(self, system):
		_checksystem(system)
		if system == 'metric':
			if self < 1.0:
				if self < 1.0 / 1000.0:
					return self.stras(Mass.MG)
				else:
					return self.stras(Mass.G)
			else:
				return self.stras(Mass.KG)
		else:
			if self.small or self*1000.0 < Constants.gramsperpound:
				small = True
			else:
				small = False
			if small:
				return self.stras(Mass.OZ)
			else:
				return self.stras(Mass.LB)

	def __str__(self):
		return self.stras_system(getparam('units_output'))

class Strength(WBCUnit):
	PLATO	= object()
	SG	= object()
	SG_PTS	= object()

	def __new__(cls, value, unit):
		if unit is Strength.SG_PTS:
			value = cls.sg_to_plato(cls.from_points(value))
		elif unit is Strength.SG:
			value = cls.sg_to_plato(value)
		elif unit is not Strength.PLATO:
			raise Exception('invalid Strength unit')

		return super(Strength, cls).__new__(cls, value, unit)

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
	# the formula for remaining RE is from the same paper (used below)
	#
	# Now, of course, the following routine gives wildly different
	# values for ABV from all other methods on the interwebs (by some
	# tenths of a percent-unit), but we'll live with it.
	#
	def _attenuate(self, to, aa):
		oe = self
		ae = to
		abw = 0.38726*(oe-ae) + 0.00307*(math.pow(oe-ae, 2))
		abv = abw * to.valueas(to.SG) / 0.7907

		# calculate remaining real extract
		#
		# sometimes you're just really thankful for computers
		re = 0.496815689*abw + 1.001534136*ae - 0.000591051*abw*ae \
		    - 0.000294307*pow(ae, 2) - 0.0084747*pow(abw, 2) \
		    + 0.000183564*pow(abw, 3) + 0.000011151*pow(ae, 3) \
		    + 0.000002452*pow(abw, 2) * pow(ae, 2)
		re = _Strength(re)

		# calculate extracts also in g/l.  1l weighs
		# SG kilograms, so the weight of extract in g in 1l is
		# 1000*SG * plato/100
		oe_gl = 10 * self * self.valueas(self.SG)
		re_gl = 10 * re * to.valueas(to.SG)

		# if original percentage was given, return it back
		# (we could always calculate it, but might be off
		# by some decimal)
		if aa is None:
			aa = 100 * (1 - ae/oe)

		ra = 100*(1-re/self)

		return {
			'ae': to,
			're': re,
			'oe_gl': oe_gl,
			're_gl': re_gl,
			'aa': aa,
			'ra': ra,
			'abv': abv,
			'abw': abw,
		}

	def attenuate_bypercent(self, aa):
		# use attenuation for gravity, not strength
		fg = Strength(self.valueas(self.SG_PTS) * (1-aa/100.0),
		    self.SG_PTS)

		return self._attenuate(fg, aa)

	def attenuate_bystrength(self, strength):
		checktype(strength, Strength)

		return self._attenuate(strength, None)

	def refractometer_correction(self, strength):
		checktype(strength, Strength)

		oe = self
		ae = strength

		# http://seanterrill.com/2011/04/07/refractometer-fg-results/
		# (the linear equation, seems just as good as the cubic
		# one if not better)
		return Strength(1.0 - 0.00085683*oe + 0.0034941*ae, Strength.SG)

		# commented-out cubic fit (for testing)
		#return Strength(1.0 - 0.0044993*oe + 0.011774*ae
		    #+ 0.00027581*pow(oe, 2) - 0.0012717*pow(ae, 2)
		    #- 0.0000072800*pow(oe, 3) + 0.000063293*pow(ae, 3),
		    #Strength.SG)

	# from:
	# "Specific Gravity Measurement Methods and Applications in Brewing"
	#
	# it notes that plato_to_sg and sg_to_plato approximations do
	# not actually invert each other, and continues to state:
	# ""This is of no practical significance to anyone except those
	# writing computer codes".  Unfortunately, no better method is
	# given.  So, we'll just have to live with this conversion for now.
	# Besides, we use multiple sg_to_plato polynomials anyway, so a
	# single one wouldn't invert them anyway.
	@staticmethod
	def plato_to_sg(plato):
		return 1.0000131					 \
		    + 0.00386777 		    * math.pow(plato, 1) \
		    + 1.27447    * math.pow(10, -5) * math.pow(plato, 2) \
		    + 6.34964    * math.pow(10, -8) * math.pow(plato, 3)

	# Ok, um, this is "real world".  We use three different
	# conversion polynomials.  Each has its strengths and weaknesses.
	# We try to pick the most accurate polynomial for the range.
	# Ergo, there are discontinuity points in our translations.
	# I'm not going to worry about that for now ... though I *am* worried
	# that some of the iterative methods used in the program might hit
	# some gap and fail to converge.
	@staticmethod
	def sg_to_plato(sg):
		# Fourth order polynomial with constraint 1.000 = 0degP.
		# Inaccurate at 1.005
		if sg < 1.0020:
			return 2737.9302			\
			    - (11754.5873 * math.pow(sg, 1))	\
			    + (17868.5255 * math.pow(sg, 2))	\
			    - (11682.9897 * math.pow(sg, 3))	\
			    + (2831.1213  * math.pow(sg, 4))

		# ASBC polynomial
		elif sg < 1.088:
			return -1*616.868			\
			    + (1111.14 * math.pow(sg, 1))	\
			    - (630.272 * math.pow(sg, 2))	\
			    + (135.997 * math.pow(sg, 3))

		# The jump between the previous and this one is quite
		# significant ...
		else:
			return -1*585.23918			\
			    + (1038.82303 * math.pow(sg, 1))	\
			    - (577.93337  * math.pow(sg, 2))	\
			    + (124.3964   * math.pow(sg, 3))

	@staticmethod
	def to_points(sg):
		return (sg - 1) * 1000

	@staticmethod
	def from_points(points):
		return (points / 1000 + 1)

	def valueas(self, which):
		if which is Strength.SG:
			return self.plato_to_sg(self)
		elif which is Strength.SG_PTS:
			return self.to_points(self.plato_to_sg(self))
		elif which is Strength.PLATO:
			return self
		else:
			raise Exception('invalid Strength type')

	def stras(self, unit):
		if unit == self.PLATO:
			return '{:.1f}{:}'.format(self, str(chr(0x00b0) + 'P'))
		elif unit == self.SG:
			return '{:.3f}'.format(self.valueas(self.SG))
		else:
			raise PilotError('invalid Strength string unit')

	def __str__(self):
		if getparam('strength_output') == 'plato':
			return self.stras(self.PLATO)
		else:
			assert(getparam('strength_output') == 'sg')
			return self.stras(self.SG)

class Color(float):
	EBC		= object()
	SRM		= object()
	LOVIBOND	= object()

	def __new__(cls, value, unit):
		if unit is Color.SRM:
			value = Color.SRMtoEBC(value)
		elif unit is Color.LOVIBOND:
			value = Color.LtoEBC(value)

		return super(Color, cls).__new__(cls, value)

	def valueas(self, which):
		if which is Color.EBC:
			return self
		elif which is Color.SRM:
			return Color.EBCtoSRM(self)
		elif which is Color.LOVIBOND:
			return Color.EBCtoL(self)
		else:
			raise Exception('invalid Color type')

	# formulae from https://en.wikipedia.org/wiki/Standard_Reference_Method
	@staticmethod
	def SRMtoEBC(v):
		return v * Constants.ebcpersrm

	@staticmethod
	def EBCtoSRM(v):
		return v / Constants.ebcpersrm

	@staticmethod
	def LtoEBC(v):
		return Color.SRMtoEBC(1.3546 * v - 0.76)

	@staticmethod
	def EBCtoL(v):
		return (Color.EBCtoSRM(v) + 0.76) / 1.3546

class Pressure(WBCUnit):
	PASCAL		= object()
	BAR		= object()
	ATMOSPHERE	= object()
	ATM		= ATMOSPHERE
	PSI		= object()

	def __new__(cls, value, unit):
		if unit is Pressure.PSI:
			value = value * Constants.pascalsperpsi
		elif unit is Pressure.BAR:
			value = value * Constants.pascalsperbar
		elif unit is Pressure.ATMOSPHERE:
			value = value * Constants.pascalsperatm
		elif unit is not Pressure.PASCAL:
			raise Exception('invalid Pressure unit')

		return super(Pressure, cls).__new__(cls, value, unit)

	def valueas(self, which):
		if which is Pressure.PASCAL:
			return self
		elif which is Pressure.BAR:
			return self / Constants.pascalsperbar
		elif which is Pressure.ATMOSPHERE:
			return self / Constants.pascalsperatm
		elif which is Pressure.PSI:
			return self / Constants.pascalsperpsi
		else:
			raise Exception('invalid Pressure type')

	def __str__(self):
		# pick bar as the "metric" unit, because it seems to
		# be present on all of the pressure gauges I own
		if getparam('units_output') == 'metric':
			return self.stras(self.BAR)
		else:
			return self.stras(self.ATM)
			assert(getparam('units_output') == 'us')

	def stras(self, which):
		if which is self.PASCAL:
			return str(self) + ' Pa'
		elif which is self.BAR:
			return '{:.2f} bar'.format(self.valueas(self.BAR))
		elif which is self.ATM:
			return '{:.2f} atm'.format(self.valueas(self.ATM))
		elif which is self.PSI:
			return '{:.1f} psi'.format(self.valueas(self.PSI))
		else:
			raise PilotError('invalid pressure unit')

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
# class (KG and PLATO, respectively).
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
		return super(_Mass, cls).__new__(cls, value, Mass.KG)
	def __init__(self, value):
		super(_Mass, self).__init__(value, Mass.KG)

class _Strength(Strength):
	def __new__(cls, value):
		return super(_Strength, cls).__new__(cls,value,Strength.PLATO)
	def __init__(self, value):
		super(_Strength, self).__init__(value, Strength.PLATO)

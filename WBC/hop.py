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

from WBC.units import *
from WBC.units import _Temperature, _Volume, _Mass, _Duration
from WBC.utils import checktype
from WBC import timespec

class Hop:
	LEAF	= 'leaf'
	PLUG	= 'plug'
	WET	= 'wet'
	T90	= 'T90'
	T45	= 'T45'

	types = [ T90, T45, LEAF, PLUG, WET ]
	_lctypes = [x.lower() for x in types]

	def __init__(self, name, aapers, type = T90):
		if type.lower() not in self._lctypes:
			raise PilotError('invalid hop type: ' + type)

		aalow = 1
		# maybe the don't go that high, but the main goal is to
		# prevent 100% from screwing up [x]x.x% formatting
		aahigh = 88

		self.name = name
		self.type = self.types[self._lctypes.index(type.lower())]

		if aapers < aalow or aapers > aahigh:
			raise PilotError('Alpha acid percentage must be ' \
			    + 'between ' + str(aalow) + ' and ' + str(aahigh))

		self.aa = aapers/100.0

	def __repr__(self):
		return 'Hop object for: ' + self.name + '/' + self.type \
		    + '/' + '{:4.1%}'.format(self.aa)

	def namestr(self, maxlen):
		n = self.name
		t = self.type
		a = self.aa

		tstr = '[{:4s} {:5.1%}]'.format(t, a)
		tlen = len(tstr)
		minnamefield = 12
		minnamelen = tlen + minnamefield + 1
		if maxlen != None:
			if maxlen < minnamelen:
				raise PilotError('min field size:'
				    + str(minnamelen))
			nlen = maxlen - (tlen+1)
			if len(n) > nlen:
				n = n[0:nlen-2] + '..'
			nstr = str(nlen)
		else:
			nstr = ''
		fmt = '{:' + str(nlen) + '} {:}'
		return fmt.format(n, tstr)

	# format IBU
	def infostr(self, maxlen, info):
		return '{:.1f}'.format(info)

	#
	# Tinseth IBUs, from http://realbeer.com/hops/research.html
	#
	# XXXTODO: that formula doesn't take into account bittering from
	# whirlpool hops or dryhopping.
	#
	def __util(self, strength, time):
		if timespec._boiltime is None:
			return 0

		# account for anything that might qualify as first-wort
		# hopping.  Now, anything besides "MashSpecial / firstwort"
		# will have the solids removed, but since it's the
		# alpha acids that isomerize, we'll just assume they're
		# present in full force.  We could technically
		# adjust pre-firstwort by mash lautering efficiency, but
		# let's no do that until someone points out why the
		# added calculation accurately solves an actual problem.

		# FWH gets this much more mins for IBU calculations.
		# (some sources say it should get IBUs for this many minutes
		# total boil time.  we'll just roll with the bonus and
		# leave the sith to deal with absolutes)
		FWH_BONUS= _Duration(20)

		if isinstance(time, timespec.Mash) \
		    or isinstance(time, timespec.MashSpecial):
			mins = timespec._boiltime + FWH_BONUS

		elif isinstance(time, timespec.Boil):
			mins = time.spec
		else:
			return 0

		# strength needs to be SG
		SG = strength.valueas(strength.SG)

		bignessfact = 1.65 * pow(0.000125, SG-1)
		boilfact = (1 - pow(math.e, -0.04 * int(mins))) / 4.15
		bonus = 1.0
		if self.type != self.LEAF:
			bonus = 1.1
		return bonus * bignessfact * boilfact

	def mass2IBU(self, strength, volume, time, mass):
		checktypes([(strength, Strength), (mass, Mass)])

		util = self.__util(strength, time)
		v = util * self.aa * mass.valueas(Mass.MG) / volume
		return v

	def IBU2mass(self, strength, volume, time, IBU):
		checktype(strength, Strength)

		util = self.__util(strength, time)

		# calculate mass
		m = (IBU * volume) / (util * self.aa)

		# store with 0.01g accuracy.
		# need to round here and supply as the native unit,
		# otherwise Mass will internally convert and possibly
		# screw the roundup (not that the roundup is accurate
		# anyway due to floats, but ...)
		m = _Mass(round(m / (1000.0*1000.0), 5))
		return m

	def absorption(self, mass):
		checktype(mass, Mass)

		# use pellethop absorption also for wet hops.  they
		# don't technically absorb anything, but they adsorb
		# more wort than pellets, so maybe(?) it evens out.
		# seems to get me pretty close to sensible results,
		# at least.  can be refined later
		if self.type != self.LEAF:
			abs_c = constants.pellethop_absorption_mlg
		else:
			abs_c = constants.leafhop_absorption_mlg

		# l/kg == ml/g
		v = _Volume(mass * abs_c)
		return v

	def volume(self, mass):
		checktype(mass, Mass)
		if self.type != self.LEAF:
			density = constants.pellethop_density_gl
		else:
			density = constants.leafhop_density_gl
		return _Volume(mass.valueas(Mass.G) / density)

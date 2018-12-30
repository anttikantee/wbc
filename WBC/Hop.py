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

from WBC.Units import *
from WBC.Units import _Temperature, _Volume, _Mass
from WBC.Utils import checktype

class Hop:
	Pellet	= object()
	Leaf	= object()

	class Hoptime:
		def __lt__(self, other):
			scls = self.__class__
			ocls = other.__class__
			if scls == ocls:
				raise TypeError('I cannot compare')
			return Hop._order.index(scls) < Hop._order.index(ocls)

		def __eq__(self, other):
			if self.__class__ != other.__class__:
				return False
			raise TypeError('I cannot compare')

	class Boil(Hoptime):
		FWH		= object()
		BOILTIME	= object()

		# FWH adds this much to full boiltime for IBU calculations
		FWH_BONUS=	20
		assert(FWH_BONUS > 0)

		def __init__(self, spec):
			import numbers
			if not isinstance(spec, numbers.Number) \
			    and spec is not self.FWH \
			    and spec is not self.BOILTIME:
				raise PilotError('invalid boiltime format')
			self.time = None
			self.spec = spec

		# uuuh.  not sure why I'm punishing myself with
		# __str__() vs. timespecstr()
		def __str__(self):
			assert(self.time is not None)
			if self.spec is self.FWH:
				return 'FWH'
			elif self.spec is self.BOILTIME:
				return 'boiltime'
			return str(int(self.time)) + ' min'

		def timespecstr(self):
			assert(self.time is not None)
			if self.spec is self.BOILTIME:
				return '@ boil'
			else:
				return str(self)

		def __repr__(self):
			return 'Hop boil spec: ' + str(self)

		def __lt__(self, other):
			try:
				return super().__lt__(other)
			except TypeError:
				return self.time < other.time

		def __eq__(self, other):
			try:
				return super().__eq__(other)
			except TypeError:
				return self.time == other.time

		def resolvetime(self, boiltime):
			assert(self.time is None)

			if self.spec is self.FWH:
				self.time = boiltime + self.FWH_BONUS
			elif self.spec is self.BOILTIME:
				self.time = boiltime
			else:
				specval = int(self.spec)
				if specval > boiltime:
					raise PilotError('hop boiltime ('
					    + str(specval)+') > wort boiltime')
				self.time = specval

	class Steep(Hoptime):
		def __init__(self, temp, time):
			checktype(temp, Temperature)

			self.temp = temp
			self.time = time
			self.spec = None

		def __str__(self):
			return str(self.time) + ' min @ ' + str(self.temp)

		def timespecstr(self):
			return '@ ' + str(self.temp)

		def __repr__(self):
			return 'Hop steep spec: ' + str(self)

		def __lt__(self, other):
			try:
				return super().__lt__(other)
			except TypeError:
				if self.temp == other.temp:
					return self.time < other.time
				return self.temp < other.temp

		def __eq__(self, other):
			try:
				return super().__eq__(other)
			except TypeError:
				return self.temp == other.temp and \
				    self.time == other.time

		def resolvetime(self, boiltime):
			return

	class Dryhop(Hoptime):
		Package =	object()

		def __init__(self, indays, outdays):
			if indays == self.Package or outdays == self.Package:
				# I guess someone *could* put hops into
				# the fermenter for some days and transfer
				# them into the package.  We're not going to
				# support such activities.
				if indays is not outdays:
					raise PilotError('when dryhopping in '\
					    'package, indays and outdays must '\
					    'be "package"')
			else:
				if indays <= outdays:
					raise PilotError('trying to take ' \
					    'dryhops out before putting ' \
					    'them in')
			self.indays = indays
			self.outdays = outdays
			self.time = 0
			self.spec = None

		def __str__(self):
			if self.indays is self.Package:
				rv = 'package'
			else:
				rv = str(self.indays) \
				    + 'd -> ' + str(self.outdays) + 'd'
			return rv

		def timespecstr(self):
			return 'dryhop'

		def __repr__(self):
			return 'Hop dryhop spec: ' + str(self)

		def __lt__(self, other):
			try:
				return super().__lt__(other)
			except TypeError:
				pass

			if self.indays is self.Package:
				if other.indays is other.Package:
					return False
				return True

			if other.indays is other.Package:
				return False

			if self.indays < other.indays:
				return True
			elif self.indays == other.indays:
				if self.outdays < other.outdays:
					return True
			return False

		def __eq__(self, other):
			try:
				return super().__eq__(other)
			except TypeError:
				return self.indays == other.indays and \
				    self.outdays == other.outdays

		def resolvetime(self, boiltime):
			return

	def __init__(self, name, aapers, type = Pellet):
		aalow = 1
		aahigh = 100 # I guess some hop extracts are [close to] 100%

		self.name = name
		self.type = type
		if type is Hop.Pellet:
			self.typestr = 'pellet'
		elif type is Hop.Leaf:
			self.typestr = 'leaf'
		else:
			raise PilotError('invalid hop type: ' + type)

		if aapers < aalow or aapers > aahigh:
			raise PilotError('Alpha acid percentage must be ' \
			    + 'between ' + str(aalow) + ' and ' + str(aahigh))

		self.aapers = aapers

	def __repr__(self):
		return 'Hop object for: ' + self.name + '/' + self.typestr \
		    + '/' + str(self.aapers) + '%'

	#
	# Tinseth IBUs, from http://realbeer.com/hops/research.html
	#
	# XXXTODO: that formula doesn't take into account bittering from
	# whirlpool hops or dryhopping.
	#

	def __util(self, gravity, time):
		if not isinstance(time, Hop.Boil):
			return 0

		mins = time.time

		# gravity needs to be SG, not points (because sg is great
		# for all calculations?)
		SG = gravity.valueas(gravity.SG)

		bignessfact = 1.65 * pow(0.000125, SG-1)
		boilfact = (1 - pow(math.e, -0.04 * mins)) / 4.15
		bonus = 1.0
		if self.type is self.Pellet:
			bonus = 1.1
		return bonus * bignessfact * boilfact

	def IBU(self, gravity, volume, time, mass):
		checktypes([(gravity, Strength), (mass, Mass)])

		util = self.__util(gravity, time)
		return util * self.aapers/100.0 * mass * 1000 / volume

	def mass(self, gravity, volume, time, IBU):
		checktype(gravity, Strength)

		util = self.__util(gravity, time)

		# calculate mass, limit to 0.01g granularity
		m = (IBU * volume) / (util * self.aapers/100.0 * 1000)
		return _Mass(int(100*m)/100.0)

	def absorption(self, mass):
		checktype(mass, Mass)
		if self.type is self.Pellet:
			abs_c = Constants.pellethop_absorption
		else:
			assert(self.type is self.Leaf)
			abs_c = Constants.leafhop_absorption
		return _Volume(mass * abs_c)

	def volume(self, mass):
		checktype(mass, Mass)
		if self.type is self.Pellet:
			density = Constants.pellethop_density
		else:
			assert(self.type is self.Leaf)
			density = Constants.leafhop_density
		return _Volume(mass / density)

	# from "smallest" to "largest" (not first-to-last)
	_order = [Dryhop, Steep, Boil]

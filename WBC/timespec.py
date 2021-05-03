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

from WBC.utils import PilotError, checktype
from WBC.units import Temperature, _Temperature

# XXX
_boiltime = None
def set_boiltime(boiltime):
	global _boiltime
	_boiltime = boiltime

class Timespec:
	MASH=		'mash'
	POSTMASH=	'steep'
	KETTLE=		'boil'
	FERMENTOR=	'ferment'
	PACKAGE=	'package'

	stages=		[ MASH, POSTMASH, KETTLE, FERMENTOR, PACKAGE ]

	def __lt__(self, other):
		scls = self.__class__
		ocls = other.__class__
		if scls == ocls:
			return self._tslt(other)
		return _order.index(scls) < _order.index(ocls)

	def __eq__(self, other):
		if self.__class__ != other.__class__:
			return False
		return self._tseq(other)

	def __str__(self):
		return str(self.spec)

class Mash(Timespec):
	MASHIN=		'mashin'

	def __init__(self, when = MASHIN):
		if when != self.MASHIN:
			checktype(when, Temperature)
			if when < 1 or when > 99:
				raise PilotError('unbelievable mash '
				    + 'temperature: ' + when)
		self.spec = when

	def timespecstr(self):
		return 'mash'

	def __repr__(self):
		return 'Timespec mash: ' + str(self)

	def _cmpvalue(self, other):
		ts = self.spec
		to = other.spec
		tmap = {
			self.MASHIN  : 0,
		}
		if ts in tmap:
			ts = _Temperature(tmap[ts])
		if to in tmap:
			to = _Temperature(tmap[to])
		return (ts, to)

	# Note: for mashing, unlike boiling, a smaller value means
	# an *earlier* addition, so smaller is larger (i.e. earlier).
	def _tslt(self, other):
		c1, c2 = self._cmpvalue(other)
		return c1 > c2

	def _tseq(self, other):
		c1, c2 = self._cmpvalue(other)
		return c1 == c2

# Note: inherited from Mash, not Timespec
class MashSpecial(Mash):
	STEEP=		'steep'
	MASHOUT=	'mashout'
	SPARGE=		'sparge'

	values=		[ STEEP, MASHOUT, SPARGE ]

	def __init__(self, when):
		if when not in self.values:
			raise PilotError('invalid MashSpecial timing')
		self.spec = when

	def _cmpvalue(self, other):
		v = self.values
		rv = (v.index(self.spec), v.index(other.spec))
		return rv

class Boil(Timespec):
	specials = [ 'FWH', 'boiltime' ]

	def __init__(self, spec):
		import numbers
		if not isinstance(spec, numbers.Number) \
		    and spec not in Boil.specials:
			raise PilotError('invalid boiltime format')

		assert(_boiltime is not None)
		if spec in Boil.specials:
			self.time = _boiltime
		else:
			specval = int(spec)
			if specval > _boiltime:
				raise PilotError('boiltime ('
				    + str(specval)+') > wort boiltime')
			self.time = specval
		if spec == 'FWH':
			self._cmptime = self.time + 1
		else:
			self._cmptime = self.time
		self.spec = spec

	# uuuh.  not sure why I'm punishing myself with
	# __str__() vs. timespecstr()
	def __str__(self):
		assert(self.time is not None)
		if self.spec in Boil.specials:
			return self.spec
		return str(int(self.time)) + ' min'

	def timespecstr(self):
		assert(self.time is not None)
		if self.spec == 'boiltime':
			return '@ boil'
		else:
			return str(self)

	def __repr__(self):
		return 'Timespec boil: ' + str(self)

	def _tslt(self, other):
		return self._cmptime < other._cmptime

	def _tseq(self, other):
		return self._cmptime == other._cmptime

class Whirlpool(Timespec):
	def __init__(self, time, temp):
		checktype(temp, Temperature)

		self.temp = temp
		self.time = time
		self.spec = None

	def __str__(self):
		return str(self.time) + ' min @ ' + str(self.temp)

	def timespecstr(self):
		return '@ ' + str(self.temp)

	def __repr__(self):
		return 'Timespec steep: ' + str(self)

	def _tslt(self, other):
		if self.temp == other.temp:
			return self.time < other.time
		return self.temp < other.temp

	def _tseq(self, other):
		return self.temp == other.temp and self.time == other.time

class Fermentor(Timespec):
	# in case you don't want to care about the days,
	# don't have to invent any that mean nothing
	UNDEF=	'undef'

	def __init__(self, indays, outdays):
		if indays == self.UNDEF or outdays == self.UNDEF:
			if indays != outdays:
				raise PilotError('Timespec Fermentor: if one '
				    + ' day is undef, both must be')
		elif indays <= outdays:
			raise PilotError('trying to take ' \
			    'fermentor addition out before putting ' \
			    'it in')
		self.indays = indays
		self.outdays = outdays
		self.time = 0
		self.spec = None

	def __str__(self):
		if self.indays == self.UNDEF:
			return 'undef'
		return str(self.indays) + 'd -> ' + str(self.outdays) + 'd'

	def timespecstr(self):
		return 'fermentor'

	def __repr__(self):
		return 'Timespec fermentor: ' + str(self)

	def _tslt(self, other):
		# undef compares less than defined days (i.e.
		# "earlier" addition)
		if self.indays == self.UNDEF:
			if other.indays != self.UNDEF:
				return True
			else:
				return False

		if self.indays < other.indays:
			return True
		elif self.indays == other.indays:
			if self.outdays < other.outdays:
				return True
		return False

	def _tseq(self, other):
		return self.indays == other.indays and \
		    self.outdays == other.outdays

class Package(Timespec):
	def __init__(self):
		self.time = 0
		self.spec = 'package'

	def timespecstr(self):
		return 'package'

	def __repr__(self):
		return 'Timespec: package'

	def _tslt(self, other):
		return False

	def _tseq(self, other):
		return True

# from "smallest" to "largest" (opposite of first-to-last)
_order = [Package, Fermentor, Whirlpool, Boil, MashSpecial, Mash]

timespec2stage= {
	Mash: 		Timespec.MASH,
	MashSpecial:	Timespec.POSTMASH,
	Boil:		Timespec.KETTLE,
	Whirlpool:	Timespec.KETTLE,
	Fermentor:	Timespec.FERMENTOR,
	Package:	Timespec.PACKAGE,
}
stage2timespec = {
	x: [y for y in timespec2stage if timespec2stage[y] == x]
	    for x in timespec2stage.values()
}

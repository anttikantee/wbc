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

#
# Timespecs define the time when an "operation" is to be performed
# on the brew/fermentation.  For example, "15min boil left" would
# be described by a timespec.  Timespecs are not to be confused
# with Worter stages, even though they are superficially similar.
#

from WBC.utils import PilotError, checktype
from WBC.units import Temperature, _Temperature, Duration

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

	# return -1 if other is earlier, 0 is same, 1 if later
	def stagecmp(self, other):
		scls = self.__class__
		ocls = other.__class__
		if _order.index(scls) > _order.index(ocls):
			return -1
		elif _order.index(scls) == _order.index(ocls):
			return 0
		return 1

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

	values=		[ MASHIN ]

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
	FIRSTWORT=	'firstwort'

	values=		[ STEEP, MASHOUT, SPARGE, FIRSTWORT ]

	def __init__(self, when):
		if when not in self.values:
			raise PilotError('invalid MashSpecial timing')
		self.spec = when

	def _cmpvalue(self, other):
		v = self.values
		rv = (v.index(self.spec), v.index(other.spec))
		return rv

class Boil(Timespec):
	BOILTIME=	'boiltime'

	def __init__(self, value):
		if _boiltime is None:
			raise PilotError('boil specifier "' + str(value)
			    + '" in a recipe without a boil')

		if not isinstance(value, Duration) \
		    and value != self.BOILTIME:
			raise PilotError('invalid boiltime: ' + str(value))

		if value == self.BOILTIME:
			self.spec = _boiltime
		else:
			if value > _boiltime:
				raise PilotError('boiltime ('
				    + str(value)+') > wort boiltime')
			self.spec = value

	def timespecstr(self):
		if abs(self.spec - _boiltime) < 0.1:
			return '@ boil'
		else:
			return str(self)

	def __repr__(self):
		return 'Timespec boil: ' + str(self)

	def _tslt(self, other):
		return self.spec < other.spec

	def _tseq(self, other):
		return self.spec == other.spec

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
	UNDEF=		object()
	D_MAX=		999
	_undef_in=	-1
	_undef_out=	D_MAX+1

	def __init__(self, indays, outdays):
		if indays == self.UNDEF:
			if outdays != self.UNDEF:
				raise PilotError('Timespec Fermentor: if inday '
				    + ' is undef, outday must be')
			indays = self._undef_in
		elif indays < 0:
			raise PilotError('indays needs to be positive')

		if outdays != self.UNDEF and indays >= outdays:
			raise PilotError('trying to take ' \
			    'fermentor addition out before putting it in')

		if (indays > self.D_MAX
		    or (outdays != self.UNDEF and outdays > self.D_MAX)):
			raise PilotError('daycount value max '
			    + str(self.DM_MAX))

		if outdays == self.UNDEF:
			outdays = self._undef_out
		elif outdays < 0:
			raise PilotError('outdays needs to be positive')

		self._indays = indays
		self._outdays = outdays
		self.time = 0
		self.spec = None

	def __str__(self):
		if self._indays == self._undef_in:
			assert(self._outdays == self._undef_out)
			return 'undef'
		elif self._outdays == self._undef_out:
			return 'day {:3d}'.format(self._indays)
		return '{:3d} ->{:3d}'.format(self._indays, self._outdays)

	def timespecstr(self):
		return 'fermentor'

	def __repr__(self):
		return 'Timespec fermentor: ' + str(self)

	def _tslt(self, other):
		if self._indays < other._indays: return False
		if self._indays > other._indays: return True

		return self._outdays > other._outdays

	def _tseq(self, other):
		return self._indays == other._indays and \
		    self._outdays == other._outdays

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

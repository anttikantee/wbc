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

_boiltime = None
def set_boiltime(boiltime):
	global _boiltime
	_boiltime = boiltime

class Timespec:
	def __lt__(self, other):
		scls = self.__class__
		ocls = other.__class__
		if scls == ocls:
			raise TypeError('I cannot compare')
		return _order.index(scls) < _order.index(ocls)

	def __eq__(self, other):
		if self.__class__ != other.__class__:
			return False
		raise TypeError('I cannot compare')

# Note: for mashing, unlike boiling, a smaller value means an *earlier*
# addition, so smaller is actually larger (i.e. earlier).
class Mash(Timespec):
	def __init__(self, temp = None):
		if temp is not None:
			checktype(temp, Temperature)
		self.temp = temp
		self.spec = None

	def __str__(self):
		if self.temp is None:
			return 'mashin'
		else:
			return str(self.temp)

	def timespecstr(self):
		return 'mash'

	def __repr__(self):
		return 'Timespec mash: ' + str(self)

	def __adjtemp(self, other):
		ts = self.temp
		to = other.temp
		if ts is None:
			ts = _Temperature(0)
		if to is None:
			to = _Temperature(0)
		return (ts, to)

	def __lt__(self, other):
		try:
			return super().__lt__(other)
		except TypeError:
			ts, to = self.__adjtemp(other)
			return ts > to

	def __eq__(self, other):
		try:
			return super().__eq__(other)
		except TypeError:
			ts, to = self.__adjtemp(other)
			return ts == to

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

	def __lt__(self, other):
		try:
			return super().__lt__(other)
		except TypeError:
			return self._cmptime < other._cmptime

	def __eq__(self, other):
		try:
			return super().__eq__(other)
		except TypeError:
			return self._cmptime == other._cmptime

class Steep(Timespec):
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

class Fermentor(Timespec):
	def __init__(self, indays, outdays):
		if indays <= outdays:
			raise PilotError('trying to take ' \
			    'fermentor addition out before putting ' \
			    'it in')
		self.indays = indays
		self.outdays = outdays
		self.time = 0
		self.spec = None

	def __str__(self):
		return str(self.indays) + 'd -> ' + str(self.outdays) + 'd'

	def timespecstr(self):
		return 'fermentor'

	def __repr__(self):
		return 'Timespec fermentor: ' + str(self)

	def __lt__(self, other):
		try:
			return super().__lt__(other)
		except TypeError:
			pass

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

class Package(Timespec):
	def __init__(self):
		self.time = 0
		self.spec = None

	def __str__(self):
		return 'package'

	def timespecstr(self):
		return 'package'

	def __repr__(self):
		return 'Timespec: package'

	def __lt__(self, other):
		try:
			return super().__lt__(other)
		except TypeError:
			return False

	def __eq__(self, other):
		try:
			return super().__eq__(other)
		except TypeError:
			return True

# from "smallest" to "largest" (opposite of first-to-last)
_order = [Package, Fermentor, Steep, Boil, Mash]

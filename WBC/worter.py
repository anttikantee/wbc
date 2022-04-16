#
# Copyright (c) 2020 Antti Kantee <pooka@iki.fi>
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
# Worter: by-mass internal representation of wort.  (supports both
# wort and water ... duh).  Works also for must, so maybe it should
# be called Worster, but then again it also works for a wash, so
# we'd be at Worshter, and that's getting too Sean Connery.
#

from WBC.units import *
from WBC.units import _Mass, _Strength, _Temperature, _Volume

from WBC import brewutils

class Worter:
	# brewing/fermenting stages we are interested in volume
	MASH=		'mash'
	PREBOIL=	'preboil'
	POSTBOIL=	'postboil'
	FERMENTOR=	'fermentor'
	PACKAGE=	'package'
	stages=		[ MASH, PREBOIL, POSTBOIL, FERMENTOR, PACKAGE ]

	_maxdensity = _Temperature(4)

	def __init__(self, extract = _Mass(0), water = _Mass(0)):
		checktypes([(extract, Mass), (water, Mass)])

		self._extract = extract
		self._water = water

	def set_volstrength(self, v, s):
		checktypes([(v, Volume), (s, Strength)])
		if self._water != 0 or self._extract != 0:
			raise PilotError("volstrength can be set only on "
			    + "a virgin worter")
		m = _Mass(v * s.valueas(s.SG))
		extract = _Mass(m * s/100.0)
		self._extract = extract
		self._water = m - extract

	def adjust_extract(self, m):
		checktype(m, Mass)
		self._extract += m

	def adjust_water(self, m):
		checktype(m, Mass)
		self._water += m

	# adjust volume, lose/gain water and extract uniformly.  IOW, the
	# strength of the worter doesn't change
	#
	# the actual physical act is "loss", but can be used to add volume
	# in case calculating backwards from final wort to initial wort
	#
	# returns adjustment as worter
	def adjust_volume(self, v_adj, temperature = _maxdensity):
		checktypes([(v_adj, Volume), (temperature, Temperature)])

		v_adj = self._volume(v_adj, temperature, self._maxdensity)
		if -v_adj > self.volume():
			raise PilotError("Worter cannot lose more than its "
			    + "total volume")

		strn = self.strength()

		m_totadj = v_adj * strn.valueas(strn.SG)
		m_extadj = m_totadj * (strn/100.0)

		adj = Worter(_Mass(m_extadj), _Mass(m_totadj - m_extadj))
		self += adj
		return adj

	def mass(self):
		return _Mass(self._extract + self._water)

	def _volume(self, v, t1, t2):
		return brewutils.water_vol_at_temp(_Volume(v),
		    t1, t2)

	# FIXXXME: I don't know of a lookup table for wort volumetric
	# expansion, so for now we assume that wort behaves like water
	# with temperature changes.  Maybe it would be more correct
	# to expand only the water "part" of the wort, but since I don't
	# know, not doing extra work for now.
	def volume(self, temperature = _maxdensity):
		checktype(temperature, Temperature)

		v = self.mass() / self.strength().valueas(Strength.SG)
		return self._volume(v, self._maxdensity, temperature)

	def strength(self):
		if self.mass() == 0:
			return _Strength(0)
		else:
			return _Strength(100.0 * self._extract / self.mass())

	def extract(self):
		return _Mass(self._extract)

	def water(self):
		return _Mass(self._water)

	def __iadd__(self, a):
		if not isinstance(a, Worter):
			raise TypeError('Worter can be added only to Worter')
		self._extract += a._extract
		self._water += a._water
		return self

	def __add__(self, a):
		if not isinstance(a, Worter):
			raise TypeError('Worter can be added only to Worter')
		return Worter(self._extract + a._extract,
		    self._water + a._water)

	def __isub__(self, s):
		if not isinstance(s, Worter):
			raise TypeError('Worter can be added only to Worter')
		self._extract -= s._extract
		self._water -= s._water
		return self

	# How does subtracting arbitrary worts make sense you ask.
	# good question.  If you draw some wort from the runnings
	# of the mash, the drawn wort will be "subtracted" from what
	# would be the final wort.
	def __sub__(self, s):
		if not isinstance(s, Worter):
			raise TypeError('Worter can be added only to Worter')
		if s._water > self._water or s._extract > self._extract:
			raise PilotError("Cannot subtract more worter "
			    + "than what you have")
		return Worter(self._extract - s._extract,
		    self._water - s._water)

	def __neg__(self):
		return Worter(-self._extract, -self._water)

	def __str__(self):
		return 'Wort {} ({}): extract {} water {}'.format(
		    str(self.volume()),
		    str(self.strength()),
		    str(_Mass(self._extract)),
		    str(_Mass(self._water)))

# return True if "this" is a later worter than "that".
# for example, this = MASH, that = PREBOIL returns False,
# as does MASH / MASH
def laterworter(this, that):
	return Worter.stages.index(this) > Worter.stages.index(that)

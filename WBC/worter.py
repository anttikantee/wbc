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
# wort and water ... duh)
#

from WBC.units import *
from WBC.units import _Mass, _Strength, _Temperature, _Volume

from WBC import brewutils

class Worter:
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
		extract = m * s/100.0
		self._extract = extract
		self._water = m - extract

	def adjust_extract(self, m):
		checktype(m, Mass)
		self._extract += m

	def adjust_water(self, m):
		checktype(m, Mass)
		self._water += m

	# lose volume, water and extract uniformly.  IOW, the
	# strength of the worter doesn't change
	def volume_loss(self, v_loss, temperature = _maxdensity):
		checktypes([(v_loss, Volume), (temperature, Temperature)])

		v_loss = self._volume(v_loss, temperature, self._maxdensity)
		if v_loss > self.volume():
			raise PilotError("Worter cannot lose more than its "
			    + "total volume")

		strn = self.strength()
		m_loss = v_loss * strn.valueas(strn.SG)
		m_eloss = m_loss * (strn/100.0)
		self._extract -= m_eloss
		self._water -= m_loss - m_eloss

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

	def __add__(self, a):
		if not isinstance(a, Worter):
			raise TypeError('Worter can be added only to Worter')
		return Worter(_Mass(self._extract + a._extract),
		    _Mass(self._water + a._water))

	# How does subtracting arbitrary worts make sense you ask.
	# good question.  If you draw some wort from the runnings
	# of the mash, the drawn wort will be "subtracted" from what
	# would be the final wort.
	def __sub__(self, s):
		if not isinstance(a, Worter):
			raise TypeError('Worter can be added only to Worter')
		if s._water > self._water or s._extract > self._extract:
			raise PilotError("Cannot subtract more worter "
			    + "than what you have")
		return Worter(_Mass(self._extract - s._extract),
		    _Mass(self._water - s._water))

	def __str__(self):
		return 'Wort ({}): extract {} water {}'.format(
		    str(self.strength()),
		    str(_Mass(self._extract)),
		    str(_Mass(self._water)))

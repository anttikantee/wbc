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
from WBC.Units import _Mass, _Temperature, _Volume

from WBC.Brewutils import water_vol_at_temp

class MashStep:
	TIME_UNSPEC=	object()

	def __init__(self, temperature, time = TIME_UNSPEC):
		checktype(temperature, Temperature)
		if time is not self.TIME_UNSPEC:
			checktype(time, int)

		self.temperature = temperature
		self.time = time

	def __str__(self):
		rv = ''
		if self.time is not self.TIME_UNSPEC:
			rv = str(self.time) + 'min @ '
		return rv + str(self.temperature)

class Mash:
	INFUSION=	object()

	#DECOCTION=	object()
	#DIRECT_HEAT=	object()

	# infusion mash step state and calculator for the next.
	#
	# In the context of this class, we use the following terminology:
	#	capa: specific heat times mass (or equivalent thereof)
	#		in relation to that of water
	#	temp: temperature
	#	heat: total heat of the component, i.e. capa * temp
	#
	# the new temperature is the existing heat plus the new heat,
	# divided by the total heat capacity.  The calculations used
	# below derive from that equation.
	class __Step:
		# relative to capa of equivalent mass of water
		__grain_relativecapa = 0.38

		def _setvalues(self, nwater_capa, nwater_temp, newtemp):
			hts = self.hts

			hts['water']['capa'] += nwater_capa
			hts['mlt']['temp'] = newtemp
			hts['grain']['temp'] = newtemp
			hts['water']['temp'] = newtemp

			self.step_watermass = nwater_capa
			self.step_watertemp = nwater_temp

		def _heat(self, what):
			ho = self.hts[what]
			return ho['temp'] * ho['capa']

		def _capa(self, what):
			ho = self.hts[what]
			return ho['capa']

		def __init__(self, grain_mass, ambient_temp, target_temp,
		     water_capa):
			self.hts = {}
			hts = self.hts

			hts['mlt'] = {}
			hts['mlt']['capa'] = getparam('mlt_heatcapacity')

			hts['grain'] = {}
			hts['grain']['capa'] = self.__grain_relativecapa \
			    * grain_mass
			hts['grain']['temp'] = ambient_temp

			hts['water'] = {}
			hts['water']['capa'] = 0
			hts['water']['temp'] = 0

			_c = self._capa
			_h = self._heat

			# if we're using a transfer MLT, assume it's
			# at ambient temp.  else, for direct heated
			# ones, assume that the water is in there which
			# means that the MLT will be at strike water
			# temperature.
			#
			# in other words, in the transfer model (e.g. cooler),
			# the MLT will consume heat.  in the direct heat
			# model, it will contribute heat (well, assuming
			# you're not brewing in an oven or something weird ...
			# the math holds nonetheless, just not the
			# clarification in the above comment)
			p = getparam('mlt_heat')
			if p == 'transfer':
				hts['mlt']['temp'] = ambient_temp
				heatsource_capa = water_capa
				heatsink = _h('mlt') + _h('grain')
			elif p == 'direct':
				hts['mlt']['temp'] = target_temp
				heatsource_capa = water_capa + _c('mlt')
				heatsink = _h('grain')
			else:
				raise PilotError('invalid mlt_heat value: ' + p)

			newcapa = water_capa + _c('mlt') + _c('grain')

			# see what temp the strike water needs to be at
			# for the whole equation to settle
			water_temp = (target_temp * newcapa - heatsink) \
			  / heatsource_capa

			if water_temp > 100:
				raise PilotError('could not satisfy mashin '
				    + 'temperarture with available water. '
				    + 'check mash parameters.')

			self._setvalues(water_capa, water_temp, target_temp)

		# figure how much boiling water we need to add (or remove)
		# to get the system up to the new target temperature
		def nextstep(self, target_temp):
			assert(getparam('mlt_heat') == 'transfer')
			_c = self._capa
			_h = self._heat

			# assume slight loss while water is transferred
			watertemp = _Temperature(98)
			boiltemp = _Temperature(100)

			nw = (target_temp \
			      * (_c('mlt') \
				  + _c('grain') + _c('water'))\
			    - (_h('mlt') + _h('grain') + _h('water')))\
			  / (watertemp - target_temp)
			self._setvalues(nw, boiltemp, target_temp)

		def waterstep(self):
			return (_Volume(self.step_watermass),
			    _Temperature(self.step_watertemp))

		def watermass(self):
			return self.hts['water']['capa']

	def __init__(self):
		self.fermentables = []
		self.giant_steps = None

	def infusion_mash(self, ambient_temp, water_temp, watervol,
	    grains_absorb):
		if self.giant_steps is None:
			raise PilotError('trying to mash without temperature')
		steps = self.giant_steps
		assert(len(steps) >= 1)

		if len(self.fermentables) == 0:
			raise PilotError('trying to mash without fermentables')
		fmass = _Mass(sum(x['amount'] for x in self.fermentables))
		grainvol = fmass * Constants.grain_specificvolume

		def origwater(fromtemp, totemp, fromwater):
			if getparam('mlt_heat') == 'direct':
				return fromwater

			step = self.__Step(fmass, _Temperature(20),
			    fromtemp, fromwater)
			step.nextstep(totemp)
			return step.watermass()

		mashin_ratio = getparam('mashin_ratio')
		if mashin_ratio[0] == '%':
			absorb = fmass * grains_absorb
			wmass_end = (mashin_ratio[1] / 100.0) \
			    * (watervol + absorb)
			wmass = origwater(steps[-1].temperature,
			    steps[0].temperature, wmass_end)
		else:
			assert(mashin_ratio[0] == '/')
			rat = mashin_ratio[1][0] * mashin_ratio[1][1]
			wmass = rat * fmass

		# adjust minimum mash water, advisory parameter
		mwatermin = getparam('mashwater_min')
		if mwatermin is not None:
			if mwatermin > watervol:
				mwatermin = watervol
			if wmass < mwatermin:
				wmass = origwater(steps[-1].temperature,
				    steps[0].temperature, mwatermin)

		# if necessary, adjust final mash volume to limit,
		# or error if we can't
		mvolmax = getparam('mashvol_max')
		wmass_end = origwater(steps[0].temperature,
		    steps[-1].temperature, wmass)
		mvol = grainvol + wmass_end
		if mvolmax is not None and mvol > mvolmax:
			veryminvol = grainvol + getparam('mlt_loss')
			if mvolmax <= veryminvol+.1:
				raise PilotError('cannot satisfy maximum '
				    'mash volume. adjust param or recipe')
			wendmax = mvolmax - grainvol
			wmass = origwater(steps[-1].temperature,
			    steps[0].temperature, wendmax)

		wmass_end = origwater(steps[0].temperature,
		    steps[-1].temperature, wmass)

		# finally, if necessary adjust the lauter volume
		# or error if either mash or lauter volume is beyond limit
		lvolmax = getparam('lautervol_max')
		lvol = (watervol - wmass) + grainvol
		if lvolmax is not None and lvol > lvolmax:
			dl = lvol - lvolmax
			assert(dl > 0)
			if (mvolmax is not None \
			      and wmass_end + dl + grainvol > mvolmax) \
			    or wmass_end + dl > watervol:
				raise PilotError('cannot satisfy mash/lauter '
				    'max volumes, check params/recipe')
			wmass += dl

		res = {}
		res['steps'] = []
		res['total_water'] = watervol

		step = self.__Step(fmass, ambient_temp,
		    steps[0].temperature, wmass)
		totvol = watervol
		inmash = 0

		if getparam('mlt_heat') == 'transfer':
			for i, s in enumerate(steps):
				(vol, temp) = step.waterstep()
				totvol -= vol
				inmash += vol
				mashvol = _Volume(inmash
				    + fmass * Constants.grain_specificvolume)

				ratio = inmash / fmass
				if totvol < -0.0001:
					raise PilotError('cannot satisfy '
					    + 'transfer infusion steps '
					    + 'with given parameters '
					    + '(ran out of water)')

				actualvol = water_vol_at_temp(vol,
				    water_temp, temp)
				res['steps'].append((s, vol, actualvol,
				    temp, ratio, _Volume(mashvol)))
				if i+1 < len(steps):
					step.nextstep(steps[i+1].temperature)
		else:
			assert(getparam('mlt_heat') == 'direct')
			(vol, temp) = step.waterstep()
			totvol -= vol
			ratio = vol / fmass
			actualvol = water_vol_at_temp(vol, water_temp, temp)
			mashvol = _Volume(vol
			    + fmass * Constants.grain_specificvolume)
			for i, s in enumerate(steps):
				res['steps'].append((s, vol, actualvol,
				    temp, ratio, mashvol))

		res['mashstep_water'] = _Volume(watervol - totvol)
		res['sparge_water'] = \
		    water_vol_at_temp(_Volume(totvol), \
		    water_temp, getparam('sparge_temp'))

		return res

	def printcsv(self):
		print('# mash|method|mashtemp1|mashtemp2...')
		steps = ''
		for t in self.giant_steps:
			steps = steps + '|' + str(t)
		print('mash|infusion' + steps)

	def set_fermentables(self, fermentables):
		self.fermentables = fermentables

	def set_steps(self, mashsteps):
		if isinstance(mashsteps, MashStep):
			mashsteps = [mashsteps]
		elif mashsteps.__class__ is list:
			curtemp = 0
			if len(mashsteps) == 0:
				raise PilotError('must give at least one '
				    + 'mashing temperature')
			for s in mashsteps:
				checktype(s, MashStep)
				if s.temperature <= curtemp:
					raise PilotError('mash steps must be ' \
					    'given in strictly ascending order')
				curtemp = s.temperature
		else:
			raise PilotError('mash steps must be given as ' \
			    'MashStep or list of')

		self.giant_steps = mashsteps

	# mostly a placeholder
	def set_method(self, m):
		if m is not Mash.INFUSION:
			raise PilotError('unsupported mash method')


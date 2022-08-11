#
# Copyright (c) 2018-2022 Antti Kantee <pooka@iki.fi>
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
from WBC.units import _Mass, _Temperature, _Volume

from WBC.worter import Worter

from WBC import timespec

import copy

class MashStep:
	TIME_UNSPEC=	object()

	INFUSION=	'infusion'
	HEAT=		'heat'
	DECOCTION=	'decoction'

	valid_methods=	[ INFUSION, HEAT, DECOCTION ]

	def __init__(self, temperature, time = TIME_UNSPEC, method = None):
		checktype(temperature, Temperature)
		if time is not self.TIME_UNSPEC:
			checktype(time, Duration)

		self.temperature = temperature
		self.time = time
		self.method = method

	def __str__(self):
		rv = ''
		if self.time is not self.TIME_UNSPEC:
			rv = str(self.time) + ' @ '
		return rv + str(self.temperature)

class Mash:
	# mash state and advancement calculator.
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
	class __MashState:
		# relative to capa of equivalent mass of water
		# NOTE: includes "average" moisture in grains
		__grain_relativecapa = 0.38

		# thick decoction composition (by mass)
		# 1 = all grain, 0 = all water
		# Used to calculate the heat capacity of the decoction
		__decoctionsplit = 0.7

		def _setvalues(self, nwater_capa, newtemp):
			hts = self.hts

			hts['water']['capa'] += nwater_capa
			hts['mlt']['temp'] = newtemp
			hts['grain']['temp'] = newtemp
			hts['water']['temp'] = newtemp

		def _heat(self, what):
			ho = self.hts[what]
			return ho['temp'] * ho['capa']

		def _capa(self, what):
			ho = self.hts[what]
			return ho['capa']

		def _temp(self):
			ho = self.hts['water']
			return ho['temp']

		# capacity of everything
		def _allc(self):
			return (self._capa('mlt')
			    + self._capa('grain')
			    + self._capa('water'))

		def __init__(self, grain_mass, grain_temp, ambient_temp):
			self.hts = {}
			hts = self.hts

			hts['mlt'] = {}
			hts['mlt']['capa'] = getparam('mlt_heatcapacity')

			hts['grain'] = {}
			hts['grain']['capa'] = self.__grain_relativecapa \
			    * grain_mass
			hts['grain']['temp'] = grain_temp

			hts['water'] = {}
			hts['water']['capa'] = 0
			hts['water']['temp'] = 0

			self.ambient_temp = ambient_temp

		#
		# Calculate what temperature the given water mass must
		# be to reach the given system temperature.  Notably,
		# water_capa may also be negative for calculating
		# backwards (tip: it can't be negative in reality)
		#
		def strike(self, target_temp, water_capa):
			# if we're using a transfer MLT, assume it's
			# at ambient temp.  else, for direct heated
			# ones, assume that the water is in there which
			# means that the MLT will be at strike water
			# temperature.
			#
			# in other words, in the transfer model (e.g. cooler),
			# the MLT will consume heat.  in the direct heat
			# model, it will contribute heat (well, assuming
			# you're not brewing in an oven ...
			# the math holds nonetheless, just not the
			# clarification in the above comment)

			hts = self.hts
			_c = self._capa
			_h = self._heat

			p = getparam('mlt_heat')
			if p == 'transfer':
				hts['mlt']['temp'] = self.ambient_temp
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

			self._setvalues(water_capa, target_temp)
			return _Temperature(water_temp)

		# calculate how much water we need to add (or remove)
		# to get the system up to the new target temperature
		def infusion1(self, target_temp, water_temp):
			_c = self._capa
			_h = self._heat

			# assume losing 2% of the temperature of the water
			water_actual = 0.98 * water_temp

			nw = (target_temp * self._allc() \
			    - (_h('mlt') + _h('grain') + _h('water')))\
			  / (water_actual - target_temp)
			self._setvalues(nw, target_temp)
			return _Mass(nw)

		def infusion(self, target_temp):
			return self.infusion1(target_temp, _Temperature(100))

		# figure out how much decoction to pull to reach temp
		def decoction(self, target_temp, evap):
			_c = self._capa
			_h = self._heat
			_t = self._temp

			# assume more slight loss while decoction is transferred
			decoction_temp = _Temperature(95)

			# the new temperature of the system is:
			# mlt_heat + ((water/grainheat-decoctioncapa) * oldtemp)
			#   + decoctioncapa * newtemp) / system_capa
			#
			# where decoctioncapa
			#   = (totgrain - decoctiongrain) * graincapa * oldtemp
			#     + (totwater ...)
			#
			# and decoctiongrain = decoctionmass * decoctionsplit,
			#   decoctionwater = decoctionmass * (1-decoctionsplit)
			#
			# we solve for decoctionmass

			grc = self.__grain_relativecapa
			ds = self.__decoctionsplit
			dt = decoction_temp

			dm = (target_temp*self._allc()
			     - (_h('mlt')+_h('grain')+_h('water'))) \
			    / ((ds * grc + 1 - ds) * (dt - _t()))
			self._setvalues(-evap, target_temp)
			return (_Mass(ds*dm), _Mass((1-ds)*dm))

		# set the mash temperature to the given value
		# without otherwise affecting the state (= direct fire)
		def heat(self, target_temp):
			self._setvalues(0, target_temp)

	def __init__(self):
		self.didmash = False

		self.fermentables = []
		self.giant_steps = None

		self.defaultmethod = MashStep.INFUSION

		self._preprocd = False

	def preprocess(self):
		if self._preprocd:
			raise PilotError('can preprocess mash only once')

		# no mash steps?  Nothing more to do here
		if self.giant_steps is None:
			return

		# set default for all mash steps for which it was not
		# specifically supplied
		assert(self.giant_steps[0].method == MashStep.INFUSION)
		for s in self.giant_steps[1:]:
			if s.method is None:
				s.method = self.defaultmethod

		self._preprocd = True

	# mashing returns a dict which contains:
	#  * mashstep_water
	#  * sparge_water
	#  * [steps]:
	def do_mash(self, ambient_temp, water, grains_absorb):
		if self.giant_steps is None:
			raise PilotError('trying to mash without temperature')

		if not self._preprocd:
			raise PilotError('mash not preprocessed')

		steps = self.giant_steps

		if len(self.fermentables) == 0:
			raise PilotError('trying to mash without fermentables')
		fmass = _Mass(sum(x.get_amount() for x in self.fermentables))
		grainvol = self.__grainvol(fmass)

		# Calculate the amount of water, going either forwards
		# or backwards.  See usage examples below to understand
		# why it's needed.  (forwards means start from mashin
		# and calculate how much water we have at the end when
		# all additions are losses are accounted for.  backwards
		# means starting from the end, and figuring out how
		# much strike water we need)
		#
		# XXX: this routine is very similar to do_steps().  Could
		# they be merged with reasonably ?
		MASHDIR_BACK = -1
		MASHDIR_FWD = 1
		def water_otherend(dir, startwater):
			# To get a mashstate, first do the strike,
			# either using the initial or final temperature.
			fsnum = min(0, dir)
			fs = steps[fsnum]
			ms = self.__MashState(fmass, ambient_temp, ambient_temp)
			ms.strike(fs.temperature, startwater)

			# Then actually calculate the amount of water at
			# the other end.
			#
			# If we are going forwards, we go from steps
			# 1 to the last.  If we're going backwards,
			# we go from the penultimate step (-2) to the
			# first.  Also, if we're going backwards, we
			# need to use the method of the *previous*
			# step.
			method = fs.method
			for s in steps[fsnum+dir::dir]:
				if dir > 0: method = s.method
				if method == s.HEAT:
					ms.heat(s.temperature)
				elif method == s.INFUSION:
					mw = ms.infusion(s.temperature)
					startwater -= dir * mw
				elif method == s.DECOCTION:
					evap = self.__decoction_evaporation(s)
					evap *= dir
					ms.decoction(s.temperature, evap)
					startwater -= evap
				else:
					assert(False)
				if dir < 0: method = s.method
			return startwater

		mashin_ratio = getparam('mashin_ratio')
		if mashin_ratio[0] == '%':
			absorb = fmass * grains_absorb
			wmass_end = (mashin_ratio[1] / 100.0) \
			    * (water.water() + absorb)
			wmass = water_otherend(MASHDIR_BACK, wmass_end)
		else:
			assert(mashin_ratio[0] == '/')
			rat = mashin_ratio[1][0] * mashin_ratio[1][1]
			wmass = rat * fmass

		# adjust minimum mash water, advisory parameter
		mwatermin = getparam('mashwater_min')
		if mwatermin is not None:
			if mwatermin > water.water():
				mwatermin = water.water()
			if wmass < mwatermin:
				wmass = water_otherend(MASHDIR_BACK, mwatermin)

		# if necessary, adjust final mash volume to limit,
		# or error if we can't
		#
		# XXX: we should use the *largest* volume, not final volume;
		# largest volume may be in the middle due to evaporation
		#
		mvolmax = getparam('mashvol_max')
		wmass_end = water_otherend(MASHDIR_FWD, wmass)
		mvol = grainvol + wmass_end
		if mvolmax is not None and mvol > mvolmax:
			veryminvol = grainvol + getparam('mlt_loss')
			if mvolmax <= veryminvol+.1:
				raise PilotError('cannot satisfy maximum '
				    'mash volume. adjust param or recipe')
			wendmax = mvolmax - grainvol
			wmass = water_otherend(MASHDIR_BACK, wendmax)

		wmass_end = water_otherend(MASHDIR_FWD, wmass)

		# finally, if necessary adjust the lauter volume
		# or error if either mash or lauter volume is beyond limit
		lvolmax = getparam('lautervol_max')
		lvol = (water.water() - wmass) + grainvol
		if lvolmax is not None and lvol > lvolmax:
			dl = lvol - lvolmax
			assert(dl > 0)
			if (mvolmax is not None \
			      and wmass_end + dl + grainvol > mvolmax) \
			    or wmass_end + dl > water.water():
				raise PilotError('cannot satisfy mash/lauter '
				    'max volumes, check params/recipe')
			wmass += dl

		stepres = self._do_steps(_Mass(wmass), fmass,
		    water.water(), ambient_temp)

		w = water.water()
		mashwater = sum([x['water'].water() for x in stepres], _Mass(0))

		res = {}
		res['steps'] = stepres
		res['mashstep_water'] = Worter(water = mashwater)
		res['sparge_water'] = Worter(water = w - mashwater)

		self.didmash = True
		return res

	def _do_steps(self, infusion_wmass, fmass, water_available,
	    ambient_temp):
		def _decoction(step):
			return step.method == MashStep.DECOCTION
		def _infusion(step):
			return step.method == MashStep.INFUSION
		def _heat(step):
			return step.method == MashStep.HEAT

		stepres = []

		mashstate = self.__MashState(fmass, ambient_temp, ambient_temp)
		infusion_wtemp = mashstate.strike(
		    self.giant_steps[0].temperature, infusion_wmass)

		water_available -= infusion_wmass
		inmash = Worter(water = infusion_wmass)

		evap = _Mass(0)
		decoctionvol = _Volume(0)

		grainvol = self.__grainvol(fmass)

		steps = iter(self.giant_steps)
		s = next(steps)
		while True:
			if water_available < -0.0001:
				raise PilotError('could not satisfy mash '
				    + 'with given parameters (not enough H2O)')

			mashtemp = s.temperature
			mashvol = inmash.volume(mashtemp) + grainvol
			ratio = inmash.water() / fmass

			stepres.append({
				'step'		: s,
				'water'		: Worter(water=infusion_wmass),
				'decoction'	: decoctionvol,
				'temp'		: infusion_wtemp,
				'ratio'		: ratio,
				'mashvol'	: mashvol,
			})

			s = next(steps, None)
			if s is None:
				break

			step_temp = s.temperature
			infusion_wmass = _Mass(0)
			if _infusion(s):
				infusion_wmass = mashstate.infusion(step_temp)
				infusion_wtemp = _Temperature(100)
				water_available -= infusion_wmass
				inmash.adjust_water(infusion_wmass)
			elif _heat(s):
				mashstate.heat(step_temp)
			elif _decoction(s):
				evap = self.__decoction_evaporation(s)
				gm, wm = mashstate.decoction(step_temp, evap)
				inmash.adjust_water(-evap)

				w = Worter(water = wm)
				decoctionvol = _Volume(w.volume(mashtemp)
				    + self.__grainvol(gm))

		return stepres

	def __grainvol(self, fmass):
		return _Volume(fmass * constants.grain_specificvolume)

	def __decoction_evaporation(self, step):
		# assume a 15min boil per decoction, with the same
		# boiloff rate as in the main boil.
		#
		# XXX: make configurable
		return _Mass(getparam('boiloff_perhour') * .25)

	def evaporation(self):
		m = 0
		if self.giant_steps is not None:
			evasteps = [s for s in self.giant_steps[1:]
			    if s.method == s.DECOCTION]
			m = sum([self.__decoction_evaporation(s)
			    for s in evasteps])
		return Worter(water = _Mass(m))

	def printcsv(self):
		if not self.didmash: return

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

		if len(mashsteps) == 0:
			raise PilotError('mash needs at least one temperature')

		# strike is always infusion
		if (mashsteps[0].method is not None
		   and mashsteps[0].method != MashStep.INFUSION):
			raise PilotError('first mash step must be infusion')
		mashsteps[0].method = MashStep.INFUSION

		self.giant_steps = mashsteps

	def set_defaultmethod(self, m):
		if m not in MashStep.valid_methods:
			raise PilotError('unsupported mash method')
		self.defaultmethod = m

	def has_stepwithtimespec(self, spec):
		for x in self.giant_steps:
			if timespec.Mash(x.temperature) == spec:
				return True
		return False

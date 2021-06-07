#
# Copyright (c) 2018, 2021 Antti Kantee <pooka@iki.fi>
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

import copy
import inspect

from WBC import constants
from WBC import fermentables
from WBC.getparam import getparam

from WBC.addition import Addition, Opaque
from WBC.utils import *
from WBC.units import *
from WBC.units import _Mass, _Strength, _Temperature, _Volume, _Duration
from WBC.hop import Hop
from WBC.mash import Mash
from WBC.worter import Worter

from WBC import brewutils, timespec
from WBC.timespec import Timespec, Boil

def checkconfig():
	return True

class WBC:
	pass

class Recipe:
	def __init__(self, name, yeast, volume, boiltime = None):
		# volume may be None if the recipe contains only relative units
		if volume is not None:
			checktype(volume, Volume)

		input = {}
		input['name' ] = name
		input['yeast'] = yeast

		input['notes'] = {}
		input['notes']['water'] = None
		input['notes']['brewday'] = []
		input['notes']['recipe'] = []

		self.boiltime = input['boiltime'] = boiltime
		timespec.set_boiltime(boiltime)

		self.input = input

		self.volume_inherent = volume
		self.volume_set = self.volume_scaled = None
		self.needinherent = []

		self.hops = []
		self.hops_recipeIBUBUGU = None

		self.ferms_in = []

		# the current "best guess" for additional extract needed
		# to reach final-strength target (for applicable recipes)
		self.fermentable_extadj = _Mass(0)
		self.final_strength = None

		# cached educated guess of the water
		# amount used in the forward calculation
		self.waterguess = None

		self.opaques = []

		self.input['stolen_wort'] = Worter()
		self._boiladj = _Mass(0)

		self.hopsdrunk = {'kettle':_Volume(0), 'fermentor':_Volume(0),
		    'package':_Volume(0)}
		self.fermentables = []

		self._calculatestatus = 0

		self.mash = Mash()

		self._oncelst = []

		sysparams.processdefaults()

	def paramfile(self, filename):
		Sysparams.processfile(filename)

	THEREST=	'rest'

	def _final_volume(self):
		assert(self._calculatestatus > 0)
		v = [self.volume_scaled, self.volume_set, self.volume_inherent ]
		return ([x for x in v if x is not None] + [None])[0]

	def _final_extract(self):
		if self.final_strength is None:
			return None
		w = Worter()
		w.set_volstrength(self._final_volume(), self.final_strength)
		return w.extract()

	def _grain_absorption(self):
		rv = getparam('grain_absorption')
		absorp = rv[0] / rv[1]
		return absorp

	def _boiloff(self):
		if self.boiltime is None:
			return _Volume(0)
		return _Volume(getparam('boiloff_perhour')
		    * (self.boiltime/60.0))

	def _reference_temp(self):
		return getparam('ambient_temp')

	def _needinherentvol(self, what):
		if what not in self.needinherent:
			self.needinherent.append(what)

	#
	# various scaling routines
	#
	def _scale(self, what):
		if self.volume_inherent is None or self.volume_scaled is None:
			return what

		assert(isinstance(what, Mass) or isinstance(what, Volume))

		scale = self.volume_scaled / self.volume_inherent
		return what.__class__(scale * what, what.defaultunit)

	def _xvol2x(self, x):
		assert(isinstance(x, Mass) or isinstance(x, Volume))
		return x.__class__(x * self._final_volume(), x.defaultunit)

	#
	# other helpers
	#

	def _once(self, callme, *args):
		cf = inspect.stack()[1]
		caller = cf[1] + '/' + str(cf[2]) + '/' + cf[3]
		if caller in self._oncelst:
			return

		self._oncelst.append(caller)
		callme(*args)

	#
	# user interfaces
	#

	def set_volume_and_scale(self, volume):
		checktype(volume, Volume)
		self.volume_scaled = volume

	def set_volume(self, volume):
		checktype(volume, Volume)
		self.volume_set = volume

	# set opaque water notes to be printed with recipe
	def set_waternotes(self, waternotes):
		checktype(waternotes, str)
		if self.input['notes']['water'] is not None:
			warn('water notes already set')
		self.input['notes']['water'] = waternotes

	def add_brewdaynote(self, note):
		checktype(note, str)
		self.input['notes']['brewday'].append(note)

	def add_recipenote(self, note):
		checktype(note, str)
		self.input['notes']['recipe'].append(note)

	#
	# Hops.
	#
	def _hopstore(self, hop, amount, resolver, time, cookie):
		checktypes([(hop, Hop), (time, Timespec)])
		a = Addition(hop, amount, resolver, time, cookie = cookie)
		self.hops.append(a)
		return a

	def hop_bymass(self, hop, mass, time):
		checktype(mass, Mass)
		self._needinherentvol('hops')
		amount = mass
		self._hopstore(hop, mass, self._scale, time, 'm')

	# mass per final volume
	def hop_bymassvolratio(self, hop, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume)])
		amount = _Mass(mass / vol)
		self._hopstore(hop, amount, self._xvol2x, time, 'm')

	# alpha acid mass
	def hop_byAA(self, hop, mass, time):
		checktype(mass, Mass)
		self._needinherentvol('hops')
		amount = _Mass(mass / hop.aa)
		self._hopstore(hop, amount, self._scale, time, 'm')

	# alpha acid mass per final volume
	def hop_byAAvolratio(self, hop, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume)])
		amount = _Mass((mass / hop.aa) / vol)
		self._hopstore(hop, amount, self._xvol2x, time, 'm')

	def hop_byIBU(self, hop, IBU, time):
		a = self._hopstore(hop, None, None, time, 'i')
		a.info = IBU

	def _setIBUBUGU(self, hop, time, value, what):
		if self.hops_recipeIBUBUGU is not None:
			raise PilotError('total IBU/BUGU specified >once')
		checktypes([(hop, Hop), (time, Timespec)])

		self.hops_recipeIBUBUGU = {
			'hop': hop,
			'time': time,
			'value': value,
			'type': what,
		}

	def hop_byrecipeIBU(self, hop, IBU, time):
		if IBU > 120.0:
			warn("Hop \"" + hop.name + "\" has high IBU ("
			    + str(IBU) + ")\n")
		self._setIBUBUGU(hop, time, IBU, 'IBU')

	def hop_byrecipeBUGU(self, hop, BUGU, time):
		if BUGU > 2.0:
			warn("Hop \"" + hop.name + "\" has high BUGU ("
			    + str(BUGU) + ")\n")
		self._setIBUBUGU(hop, time, BUGU, 'BUGU')

	# opaque additions.  not used for in-recipe calculations,
	# just printed out in timed additions.

	def _opaquestore(self, opaque, amount, resolver, time):
		checktype(time, Timespec)
		a = Addition(Opaque(opaque), amount, resolver, time)
		self.opaques.append(a)

	def opaque_bymass(self, opaque, mass, time):
		checktypes([(mass, Mass), (time, Timespec)])
		self._needinherentvol('opaque_bymass')
		self._opaquestore(opaque, mass, self._scale, time)
	def opaque_byvol(self, opaque, volume, time):
		checktypes([(volume, Volume), (time, Timespec)])
		self._needinherentvol('opaque_byvol')
		self._opaquestore(opaque, volume, self._scale, time)

	def opaque_bymassvolratio(self, opaque, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume), (time, Timespec)])
		amount = _Mass(mass / vol)
		self._opaquestore(opaque, amount, self._xvol2x, time)
	def opaque_byvolvolratio(self, opaque, vv, time):
		(v1, v2) = vv
		checktypes([(v1, Volume), (v2, Volume), (time, Timespec)])
		amount = _Volume(v1 / v2)
		self._opaquestore(opaque, amount, self._xvol2x, time)

	def opaque_byopaque(self, opaque, ospec, time):
		checktype(time, Timespec)
		if ospec.__class__ != str:
			raise PilotError('opaque spec must be a string')
		self._opaquestore(opaque, ospec, None, time)

	def anchor_bystrength(self, strength):
		checktype(strength, Strength)

		if self.final_strength is not None:
			raise PilotError('final strength already set')
		self.final_strength = strength
		self.input['strength'] = strength

	def _fermstore(self, name, amount, resolver, time, cookie):
		ferm = fermentables.Get(name)
		v = [x for x in self.ferms_in
		    if x.obj.name.lower() == name.lower() and x.time == time ]
		if len(v) > 0:
			raise PilotError('fermentables may be specified max '
			    + 'once per stage')

		checktypes([(ferm, fermentables.Fermentable), (time, Timespec)])
		a = Addition(ferm, amount, resolver, time, cookie = cookie)
		self.ferms_in.append(a)
		return a

	def fermentable_bymass(self, name, mass, time):
		checktype(mass, Mass)
		self._needinherentvol('fermentable_bymass')
		amount = mass
		self._fermstore(name, amount, self._scale, time, 'm')

	def fermentable_bymassvolratio(self, name, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume)])
		amount = _Mass(mass / vol)

		self._fermstore(name, amount, self._xvol2x, time, 'm')

	# percent of fermentable's mass, not extract's mass
	def fermentable_bypercent(self, name, percent, time):
		if percent != self.THEREST:
			if percent <= 0:
				raise PilotError('grain percentage must be '
				   + 'positive (it is a fun thing!)')
			if sum([x.get_amount() for x in self.ferms_in
			    if x.cookie == 'p']) + percent > 100.0001:
				raise PilotError('captain, I cannot change the'
				    + ' laws of math; 100% fermentables max!')

		self._fermstore(name, percent, None, time,
		    'p' if percent != self.THEREST else 'r')

	# indicate that we want to "borrow" some wort at the preboil stage
	# for e.g. building starters.
	def steal_preboil_wort(self, vol, strength):
		checktypes([(vol, Volume), (strength, Strength)])

		self.input['stolen_wort'].set_volstrength(vol, strength)

	def _fermentable_percentage(self, what, theoretical=False):
		f = what.obj
		percent = f.extract.cgai()
		if f.conversion and not theoretical:
			percent *= getparam('mash_efficiency')/100.0
		return percent

	def _fermentable_extract(self, what, theoretical=False):
		return _Mass(what.get_amount()
		    * self._fermentable_percentage(what, theoretical)/100.0)

	def _fermentables_bytimespec(self, when):
		spec = timespec.stage2timespec[when]

		return [x for x in self.fermentables \
		    if x.time.__class__ in spec]

	def _fermentables_massof(self, fermlist):
		return sum(x.get_amount() for x in fermlist)

	def _fermfilter(self, sel):
		return [x for x in self.ferms_in if x.cookie in tuple(sel)]

	def _extract_bytimespec(self, stage, theoretical=False):
		assert(stage in Timespec.stages)

		return _Mass(sum([self._fermentable_extract(x, theoretical) \
		    for x in self._fermentables_bytimespec(stage)]))

	def _sanity_check(self):
		# XXX: none at the time
		pass

	# set initial guesses for fermentables
	def _dofermentables_preprocess(self):
		rlst, plst = self._fermfilter('r'), self._fermfilter('p')
		if len(rlst + plst) == 0:
			return

		ptot = sum([x.get_amount() for x in plst])
		if len(rlst) == 0:
			if abs(ptot - 100.) > .00001:
				raise PilotError('need 100% fermentables. '
				    + 'literally forgot "rest"?')
			return

		missing = 100. - ptot
		if missing > .000001:
			for f in rlst:
				f.set_amount(missing / len(rlst))

		# note: by-percent fermentables are 100% here.
		# all fermentables (if by-mass are specified)
		# might be over.  we'll adjust the guess for
		# "rest" later so that sum of fermentables is 100%.
		assert(abs(sum([x.get_amount() for x in rlst+plst])
		    - 100.) < .000001)

	def _dofermentables_bypercent(self, ferms):
		#
		#
		# Calculate fermentables given as percentages + strength.
		#
		# We do it iteratively, since analytically figuring out
		# a loss-function is "difficult" (it depends on the
		# strength, stage the fermentable is added at, amount
		# of hop thirst, etc).
		#
		#

		# Guess extract we get from "bymass" fermentables.
		mext = _Mass(sum([self._fermentable_extract(x) for x in ferms]))

		extract = self._final_extract() + self.fermentable_extadj

		# set the amount of extract we need from by-percent
		# fermentables (= total - yield_bymass)
		# per-mass additions
		if mext > extract:
			raise PilotError('strength anchor and '
			    'by-mass addition mismatch (overshooting strength)')
		extract -= mext

		# produce one best-current-guess for fermentable masses.
		def guess(f_in):
			allp = self._fermfilter(('r', 'p'))
			# solve for the total mass of fermentables
			# we need to reach our extract goal:
			#
			# extract = yield1 * m1 + yield2 * m2 + ...
			# where yieldn = whatever extract we get out of the
			#                mass (e.g. ~80% for honey, 100%
			#                for white sugar, masheff * extract
			#                for malts, ...)
			# and   mn = %n * totmass
			# and then solve: totmass = extract / (sum(yieldn*pn))
			thesum = sum([self._fermentable_percentage(x)/100.0
			    * x.get_amount()/100.0 for x in allp])
			totmass = _Mass(extract / thesum)

			f_out = []
			f_out += f_in

			# set the masses of each individual fermentable
			for x in allp:
				# limit mass to 0.1g accuracy
				m = (int(10000*(x.get_amount()/100.0 * totmass))
				    / 10000.0)
				n = copy.copy(x)
				# save original percent in info for later
				n.info = x.get_amount()
				n.set_amount(_Mass(m))
				f_out.append(n)
			return f_out

		# handle the situation where we have:
		# 1) mixed mass/percent fermentable quantities
		# AND
		# 2) one or more "rest" grains
		#
		# adjust the non-rest percentages to be as specified.
		# not sure if this could be solved analytically instead of
		# with iteration, but, as usual, my head started hurting
		# when thinking about it.
		#
		# we need to both reduce "rest" until the sum of the
		# percentages is 100% (otherwise the fixed percentages
		# are below their values), and recalculate the mass of
		# the by-percent fermentables.
		if (len(self._fermfilter('r')) > 0
		    and len(self._fermfilter('p')) > 0):
			iters = 30
			if mext > 0.0001:
				self._once(notice,
				    'finding the solution for fixed '
				    'percentages and masses\n')
			for g in range(iters):
				fr = self._fermfilter('r')
				f_guess = guess(ferms)
				fp = [x for x in f_guess if x.cookie == 'p']

				# pick largest value to adjust against.
				# gut feeling that it'll make things more
				# accurate.  we have to pick *some* value
				# in any case, so might as well pick this one.
				f = sorted(fp, key=lambda x: x.get_amount(),
				   reverse=True)[0]

				f_wanted = f.info
				allmass = self._fermentables_massof(f_guess)
				f_actual = 100.0 * (f.get_amount() / allmass)
				diff = f_wanted - f_actual
				if abs(diff) < 0.01:
					break
				nrest = len(fr)

				# scale the diff to the "rest" values we're
				# adjusting
				scale = (fr[0].get_amount() / f_wanted)
				if scale < 1:
					scale = 1/scale
				assert(scale >= 1)
				adj = scale * (diff / nrest)
				for x in fr:
					x.set_amount(x.get_amount() - adj)
					if (x.get_amount() < 0.01):
						raise PilotError('cannot solve '
						    'recipe. lower bymass or '
						    'raise strength')
			if g == iters-1:
				self._once(warn,
				    'fermentable "rest" percentages did not '
				    'converge in ' + str(iters) + ' tries\n')
		else:
			f_guess = guess(ferms)

		self._set_calcguess(f_guess, None)

	# turn percentages into masses, calculate expected worters
	# for each worter stage
	def _dofermentables_and_worters(self):
		ferms_bymass = self._fermfilter('m')
		if len(self._fermfilter(('r', 'p'))) == 0:
			self._set_calcguess(ferms_bymass, None)
			l = self.vol_losses

			if self.waterguess is None:
				vol_loss = _Volume(sum(l.values())
				    + self._boiloff()
				    + self.mash.evaporation().water())
				self.waterguess = _Mass(self._final_volume()
				    + vol_loss)

			while True:
				res = self._doworters_bymass()
				diff = (res[Worter.PACKAGE].volume()
				    - self._final_volume())
				if diff < 0.1:
					break
				self.waterguess = _Mass(self.waterguess - diff)
			self.worter = res
			return

		if self.final_strength is None:
			raise PilotError('final strength must be set for '
			    + 'by-percent fermentables')

		# account for "unknown" extract losses from stage to stage
		# ("unknown" = not solved analytically)
		for _ in range(10):
			self._dofermentables_bypercent(ferms_bymass)
			res = self._doworters_bystrength()
			extoff = res[Worter.MASH].extract()
			if abs(extoff.valueas(Mass.G)) < 1:
				break
			self.fermentable_extadj += extoff
		else:
			raise Exception('unable to calculate fermentables')

		self.waterguess = res[Worter.MASH].water() + self._boiladj
		self.worter = res

	def _dofermentablestats(self):
		assert('losses' in self.results)

		allmass = self._fermentables_massof(self.fermentables)
		stats = {}

		# Calculate amount of extract -- extract-equivalent --
		# that makes it into packaging.  We start with the amount
		# of extract we know we're getting, and then subtract
		# the normalized share at each stage until we're at
		# packaging.  Since the mash is accounted
		# for in configuration, we only need to handle the
		# losses in the kettle and fermentor.
		#
		# XXX: it's somewhat inelegant because fermentables
		# are added as timespecs, while losses are given
		# as worters.
		def extract_predicted(f, stage):
			f_ext = self._fermentable_extract(f)
			tss = Timespec.stages
			losses = self.results['losses']
			worters = self.worter

			def stageloss(stagecmp, wname):
				v = 0
				if tss.index(stage) < tss.index(stagecmp):
					stageloss = losses[wname].extract()
					stageext = worters[wname].extract()

					v = stageloss * (f_ext/stageext)
				return _Mass(v)

			f_ext -= stageloss(Timespec.FERMENTOR, Worter.POSTBOIL)
			f_ext -= stageloss(Timespec.PACKAGE, Worter.FERMENTOR)

			return f_ext

		for f in self.fermentables:
			stage = timespec.timespec2stage[f.time.__class__]
			fs = {}
			fs['percent'] = 100.0 * (f.get_amount() / allmass)
			fs['extract_predicted'] = extract_predicted(f, stage)
			fs['extract_theoretical'] \
			    = self._fermentable_extract(f, theoretical=True)

			stats.setdefault(stage, {})
			stats[stage].setdefault('percent', 0)
			stats[stage].setdefault('amount', _Mass(0))
			stats[stage].setdefault('extract_predicted', _Mass(0))
			stats[stage].setdefault('extract_theoretical', _Mass(0))
			stats[stage]['percent'] += fs['percent']
			stats[stage]['amount'] += f.get_amount()
			stats[stage]['extract_predicted'] \
			    += fs['extract_predicted']
			stats[stage]['extract_theoretical'] \
			    += fs['extract_theoretical']
			f.info = fs

		allstats = {}
		allstats['amount'] \
		    = _Mass(sum([stats[x]['amount'] for x in stats]))
		allstats['extract_predicted'] \
		    = _Mass(sum([stats[x]['extract_predicted'] for x in stats]))
		allstats['extract_theoretical'] \
		    = _Mass(sum([stats[x]['extract_theoretical']
				 for x in stats]))

		self.results['fermentable_stats_perstage'] = stats
		self.results['fermentable_stats_all'] = allstats

		# sort fermentables by 3 criteria (from most to least dominant)
		# 1) mass
		# 2) extract mass
		# 3) alphabet
		f = self.fermentables
		f = sorted(f, key=lambda x: x.obj.name, reverse=True)
		f = sorted(f, key=lambda x: x.info['extract_predicted'])
		f = sorted(f, key=lambda x: x.get_amount())
		self.fermentables = f[::-1]

	def _domash(self):
		mf = self._fermentables_bytimespec(Timespec.MASH)
		self.mash.set_fermentables(mf)

		self.results['mash'] \
		    = self.mash.do_mash(getparam('ambient_temp'),
			self._reference_temp(), self.worter[Worter.MASH],
			self._grain_absorption())

		self.results['mash_conversion'] = {}
		theor_extract = self._extract_bytimespec(Worter.MASH,
		    theoretical=True)
		watermass = self.results['mash']['mashstep_water'].water()
		for x in range(5, 100+1, 5):
			extract = theor_extract * x/100.0
			fw = 100 * (extract / (extract + watermass))
			self.results['mash_conversion'][x] = _Strength(fw)

		w = copy.deepcopy(self.results['mash']['mashstep_water'])
		w.adjust_extract(self._extract_bytimespec(Timespec.MASH))
		w -= self.mash.evaporation()
		rloss = (self._fermentables_massof(mf)*self._grain_absorption()
		    + getparam('mlt_loss'))
		w.adjust_volume(_Volume(-rloss))
		if w.volume() < 0:
			raise PilotError('mashin ratio ridiculously low')
		self.results['mash_first_runnings'] = w

	def _set_calcguess(self, ferms, hd):
		if ferms is not None:
			self.fermentables = ferms
		if hd is not None:
			self.hopsdrunk = hd

		# update volume loss caches
		l = {}
		f = self._fermentables_bytimespec(Timespec.MASH) \
		    + self._fermentables_bytimespec(Timespec.POSTMASH)
		m = self._fermentables_massof(f)
		l[Worter.MASH] = _Volume(m*self._grain_absorption()
		    + getparam('mlt_loss'))

		hd = self.hopsdrunk
		l[Worter.POSTBOIL] = hd['kettle'] + getparam('kettle_loss')
		l[Worter.FERMENTOR] = hd['fermentor'] \
		    + getparam('fermentor_loss')
		self.vol_losses = l

	# bymass: calculate worters based on a mashwater input.  We use
	# this both for figuring out the strength of the wort produced
	# from a bymass-brew, and also after percentage&strength
	# has been resolved into masses.
	def _doworters_bymass(self):
		res = {}
		l = self.vol_losses

		w = Worter(water = self.waterguess - self._boiladj)
		res[Worter.MASH] = copy.deepcopy(w)

		# worter at PREBOIL is mash plus extract minus
		# evaporation minus volume loss
		w.adjust_extract(self._extract_bytimespec(Timespec.MASH))
		w.adjust_extract(self._extract_bytimespec(Timespec.POSTMASH))

		w -= self.mash.evaporation()

		# We account for the extract loss already in the mash
		# efficiency (configured).  Therefore, coupled with the
		# loss volume we can calculate the amount of water lost,
		# and just subtract the water.

		maxext = sum([ self._extract_bytimespec(x, theoretical=True)
		    for x in [Timespec.MASH, Timespec.POSTMASH]], _Mass(0))
		extdiff = _Mass(maxext - w.extract())
		stren = brewutils.solve_strength(extdiff, l[Worter.MASH])

		w_mashloss = Worter()
		w_mashloss.set_volstrength(l[Worter.MASH], stren)
		w.adjust_water(-w_mashloss.water())

		res[Worter.PREBOIL] = copy.deepcopy(w)

		w.adjust_water(_Mass(-self._boiloff()))
		w.adjust_extract(self._extract_bytimespec(Timespec.KETTLE))
		res[Worter.POSTBOIL] = copy.deepcopy(w)

		w.adjust_volume(-l[Worter.POSTBOIL])
		w.adjust_extract(self._extract_bytimespec(Timespec.FERMENTOR))
		w.adjust_water(self._boiladj)
		res[Worter.FERMENTOR] = copy.deepcopy(w)

		w.adjust_volume(-l[Worter.FERMENTOR])
		w.adjust_extract(self._extract_bytimespec(Timespec.PACKAGE))
		res[Worter.PACKAGE] = copy.deepcopy(w)

		return res

	# bystrength: start from final volume / strength, calculate
	# backwards
	def _doworters_bystrength(self):
		res = {}
		l = self.vol_losses

		w = Worter()
		w.set_volstrength(self._final_volume(), self.final_strength)
		res[Worter.PACKAGE] = copy.deepcopy(w)

		w.adjust_extract(-self._extract_bytimespec(Timespec.PACKAGE))
		w.adjust_volume(l[Worter.FERMENTOR])
		res[Worter.FERMENTOR] = copy.deepcopy(w)

		w.adjust_extract(-self._extract_bytimespec(Timespec.FERMENTOR))
		w.adjust_volume(l[Worter.POSTBOIL])
		w.adjust_water(-self._boiladj)
		res[Worter.POSTBOIL] = copy.deepcopy(w)

		w.adjust_extract(-self._extract_bytimespec(Timespec.KETTLE))
		w.adjust_water(_Mass(self._boiloff()))
		res[Worter.PREBOIL] = copy.deepcopy(w)

		actext = (self._extract_bytimespec(Timespec.MASH)
		    + self._extract_bytimespec(Timespec.POSTMASH))
		w.adjust_extract(-actext)
		w += self.mash.evaporation()

		# We account for the extract loss already in the mash
		# efficiency (configured).  Therefore, coupled with the
		# loss volume we can calculate the amount of water lost,
		# and just subtract the water.
		maxext = sum([self._extract_bytimespec(x, theoretical=True)
		    for x in [Timespec.MASH, Timespec.POSTMASH]], _Mass(0))
		extdiff = _Mass(maxext - actext)
		stren = brewutils.solve_strength(extdiff, l[Worter.MASH])
		w_mashloss = Worter()
		w_mashloss.set_volstrength(l[Worter.MASH], stren)
		w.adjust_water(w_mashloss.water())

		res[Worter.MASH] = copy.deepcopy(w)

		return res

	def _dohops(self):
		allhop = []

		# ok, um, so the Tinseth formula uses postboil volume ...
		wrt = self.worter
		v_post = wrt[Worter.POSTBOIL].volume()

		# ... and average gravity during the boil.  *whee*
		t = (wrt[Worter.PREBOIL].strength().valueas(Strength.SG)
		    + wrt[Worter.POSTBOIL].strength().valueas(Strength.SG))
		sg = Strength(t/2, Strength.SG)

		#
		# Do the hop calculations.  We edit the original input
		# objects, but since we only use the original values on
		# all iterations.  Saves a big deepcopy.
		#
		# calculate IBU produced by "bymass" hops
		for hs, h in [(x, x.obj) for x in self.hops if x.cookie == 'm']:
			ibu = h.mass2IBU(sg, v_post, hs.time, hs.get_amount())
			hs.info = ibu

		# calculate mass of "byIBU" hops
		for hs, h in [(x, x.obj) for x in self.hops if x.cookie == 'i']:
			mass = h.IBU2mass(sg, v_post, hs.time, hs.info)
			hs.set_amount(mass)

		allhop = self.hops[:]
		totibus = sum([x.info for x in allhop])
		if self.hops_recipeIBUBUGU is not None:
			x = self.hops_recipeIBUBUGU
			h, t, v = x['hop'], x['time'], x['value']

			if x['type'] == 'BUGU':
				stren = self.worter[Worter.PACKAGE].strength()
				v *= stren.valueas(stren.SG_PTS)
			missibus = v - totibus
			if missibus <= 0:
				raise PilotError('recipe IBU/BUGU exceeded')

			mass = h.IBU2mass(sg, v_post, t, missibus)
			totibus += missibus
			hs = Addition(h, mass, None, t, cookie = 'r')
			hs.info = missibus
			allhop.append(hs)

		# calculate amount of wort that hops will drink
		hd = {x: 0 for x in self.hopsdrunk}
		packagedryhopvol = 0
		for h in allhop:
			hop = h.obj
			if isinstance(h.time, timespec.Fermentor):
				hd['fermentor'] += hop.absorption(h.get_amount())
			elif isinstance(h.time, timespec.Package):
				hd['package'] += hop.absorption(h.get_amount())
				packagedryhopvol += hop.volume(h.get_amount())
			else:
				# XXX
				hd['kettle'] += hop.absorption(h.get_amount())

		hopsdrunk = {x: _Volume(hd[x]) for x in hd}
		hopsdrunk['volume'] = _Volume(packagedryhopvol)
		self._set_calcguess(None, hopsdrunk)

		self.results['hops'] = allhop

		totmass = _Mass(sum(x.get_amount() for x in allhop))
		self.results['hop_stats'] = {'mass': totmass, 'ibu' : totibus}

	def _dotimers(self):
		# sort the timerable additions
		timers = self.results['hops'] + self.opaques

		# include boiltime fermentables under timers.
		# XXX: should be user-configurable
		timers += [x for x in self.fermentables
		    if isinstance(x.time, timespec.Boil)]

		timers = sorted(timers, key=lambda x: x.time, reverse=True)

		# calculate "timer" field values
		prevtype = None
		timer = 0
		boiltimer = _Duration(0)
		for t in reversed(timers):
			time = t.time
			if prevtype is None or not isinstance(time, prevtype):
				timer = _Duration(0)
				prevval = None
				prevtype = time.__class__

			if isinstance(time, (timespec.Mash, timespec.Fermentor,
			    timespec.Package)):
				t.timer = time

			if isinstance(time, timespec.Whirlpool):
				if prevval is not None \
				    and prevval[0] == time.temp:
					if prevval[1] == time.time:
						t.timer = '=='
					else:
						v = time.time - prevval[1]
						t.timer = v
				else:
					t.timer = time.time
				prevval = (time.temp, time.time)

			if isinstance(time, timespec.Boil):
				cmpval = time.spec
				thisval = '=='

				if cmpval != timer:
					thisval = str(cmpval - timer)
					timer = cmpval
				t.timer = thisval
				boiltimer = timer

		# if timers don't start from start of boil, add an opaque
		# to specify initial timer value
		if ((self.boiltime is not None and self.boiltime > 0)
		    and boiltimer != self.boiltime):
			sb = Addition(Opaque(''), '', None,
			    timespec.Boil('boiltime'))
			sb.timer = self.boiltime - boiltimer
			timers = sorted([sb] + timers,
			    key=lambda x: x.time, reverse=True)

		self.results['timer_additions'] = timers

	def _doattenuations(self, attenuation = (60, 101, 5)):
		res = []
		fin = self.worter[Worter.PACKAGE].strength()
		for x in range(*attenuation):
			t = fin.attenuate_bypercent(x)
			res.append((x, t['ae'], t['abv']))
		self.results['attenuation'] = res

	def _doboiladj(self):
		bvmax = getparam('boilvol_max')
		if bvmax is None:
			return

		boiltemp = _Temperature(100)
		pbwort = self.worter[Worter.PREBOIL]
		pbvol = pbwort.volume(boiltemp)
		diff = pbvol - bvmax
		if diff > 0:
			adj = brewutils.water_voltemp_to_mass(diff, boiltemp)
			self._boiladj += adj

	def _checkinputs(self):
		if self._final_volume() is None:
			raise PilotError("final volume is not set")

		if len(self.needinherent) > 0 and self.volume_inherent is None:
			raise PilotError("recipe has absolute amounts but "
			    + "no inherent volume: "
			    + ','.join(self.needinherent))

	def calculate(self):
		sysparams.checkset()

		if self._calculatestatus:
			raise PilotError("you can calculate() a recipe once")
		self._calculatestatus += 1

		self._checkinputs()

		s = self._scale(_Mass(1))
		if abs(s - 1.0) > .0001:
			notice('Scaling recipe ingredients by a factor of '
			    + '{:.4f}'.format(s) + '\n')

		self._dofermentables_preprocess()

		# ok, so the problem is that the amount of hops affects the
		# kettle crud, meaning we have non-constants loss between
		# postboil and the fermentor.  that loss, in turn, affects
		# the final volume.  we can't replace the lost wort with
		# water, since that affects both the IBUs and strength.
		#
		# to summarize the dependencies
		# hops => volume => strength => IBUs => hops
		#
		# of course, it's easy if we ignore fermentables-by-percent
		# and hops-by-IBU ... but we don't
		#
		# trying to solve analytically gives me a headache, plus it
		# would (probably?) lead to messy code, since we couldn't
		# calculate each subcomponent separately anymore.  so, just
		# do a few loops for the fermentables/mash/hops calculations,
		# and stop when we reach <0.01l difference with desired final
		# volume
		#
		for x in range(10):
			self.results = {}

			self._dofermentables_and_worters()
			self._doboiladj()

			if self._extract_bytimespec(Timespec.MASH) > 0.001:
				self._domash()
			self._dohops()

			# We need to have hit *at least* the final volume.
			# Additionally, if final strength was specified,
			# we need to hit that too.
			self.worter = self._doworters_bymass()
			voldiff = self._final_volume() \
			    - self.worter[Worter.PACKAGE].volume()
			if self._final_extract() is not None:
				extdiff = self._final_extract() \
				    - self.worter[Worter.PACKAGE].extract()
			else:
				extdiff = _Mass(0)
			if abs(voldiff < 0.1 and extdiff < 0.1):
				break
			self.waterguess += _Mass(voldiff)
			self.fermentable_extadj += extdiff
		else:
			raise Exception('recipe failed to converge ... panic?')

		self.results['worter'] = self.worter

		if self._boiladj > 0.001:
			tf = timespec.Fermentor
			self.opaque_byvol('WBC boil volume adj.',
			    _Volume(self._boiladj), tf(tf.UNDEF, tf.UNDEF))

		self._dotimers()

		# calculate losses as worters
		rl = {}
		for x in self.vol_losses:
			w = Worter()
			w.set_volstrength(self.vol_losses[x],
			    self.worter[x].strength())
			rl[x] = w
		self.results['losses'] = rl

		self._dofermentablestats()
		self._doattenuations()

		# calculate suggested pitch rates in billions of cells,
		# using 0.75mil/ml/degP for ales and 1.5mil for lagers
		wrt = Worter.FERMENTOR
		mldegp = (self.worter[wrt].volume().valueas(Volume.MILLILITER)
		    * self.worter[wrt].strength())
		mil = 1000*1000
		bil = 1000*mil
		self.results['pitch'] = {}
		self.results['pitch']['ale']   = mldegp * 0.75*mil / bil
		self.results['pitch']['lager'] = mldegp * 1.50*mil / bil

		# calculate color, via MCU & Morey equation
		t = sum(f.get_amount().valueas(Mass.LB) \
		    * f.obj.color.valueas(Color.LOVIBOND) \
		        for f in self.fermentables)
		v = (self.worter[Worter.POSTBOIL].volume()
		    + _Volume(self._boiladj)).valueas(Volume.GALLON)
		mcu = t / v
		self.results['color'] = \
		    Color(1.4922 * pow(mcu, 0.6859), Color.SRM)

		# calculate brewhouse estimated afficiency ... NO, efficiency
		maxext = sum([self._extract_bytimespec(x, theoretical=True)
		    for x in Timespec.stages])
		self.results['brewhouse_efficiency'] = \
		    self.worter[Worter.PACKAGE].extract() / maxext

		# these are easy
		self.results['hopsdrunk'] = self.hopsdrunk
		self.results['fermentables'] = self.fermentables

		self.results['total_water'] = self.worter[Worter.MASH] \
		    + Worter(water = self._boiladj)

		self._sanity_check()
		self._calculatestatus += 1

	def _assertcalculate(self):
		if self._calculatestatus == 0:
			raise PilotError('must calculate recipe first')

	# dump the recipe as a CSV, which has all of the quantities
	# resolved, and contains enough information to recalculate
	# the recipe.  uses are both for tracking brewhouse resource
	# usage, and reverse engineering various parameters (e.g.
	# figure out true mash efficiency)
	#
	# ok, it's really a PSV (pipe-separated values), but aaaanyhooo
	#
	# the format is not meant to be human-readable, only readable
	# by semi-humans
	def printcsv(self):
		self._assertcalculate()
		print('wbcdata|2')
		print('# recipe|name|yeast|boiltime|volume')
		print('recipe|' + self.input['name'] + '|'
		    + self.input['yeast'] + '|'
		    + str(self.boiltime)
		    + '|' + str(float(self.worter[Worter.PACKAGE].volume())))

		print('# sysparams')
		print('sysparams|' + sysparams.getparamshorts())

		self.mash.printcsv()

		print('# fermentable|name|mass|when')
		for g in self.fermentables:
			print('fermentable|{:}|{:}|{:}'\
			    .format(g.obj.name,
			      float(g.get_amount()), g.time))

		print('# hop|name|type|aa%|mass|timeclass|timespec')
		for h in self.results['hops']:
			hop = h.obj
			time = h.time
			timeclass = time.__class__.__name__.lower()
			timespec = str(time).replace(chr(0x00b0), "deg")
			timespec = str(timespec)

			print('hop|{:}|{:}|{:.1f}|{:}|{:}|{:}'
			    .format(hop.name, hop.type, 100.0*hop.aa,
				float(h.get_amount()), timeclass, timespec))

	# parti-gyle calculations was actually the reason I initially
	# started writing WBC, but parti-gyle is now bitrotted a bit
	# and does not really "fit nicely" into the interfaces, so it's
	# not usable until it's fixed
	def parti_mash(self, bigbeer_sg, bigbeer_vol, smallbeer_vol,
	    mashtemp = Temperature(65, Temperature.degC)):
		raise PilotError('parti-gyle mashing not currently tested')

		checktypes([(bigbeer_sg, Strength), (bigbeer_vol, Volume),
		    (smallbeer_vol, Volume), (mashtemp, Temperature)])

		tot_vol = _Volume(bigbeer_vol + smallbeer_vol)

		strike_vol = _Volume(2.5*self.grams_grain)
		#potential_points = Strength(yieldpkg) * self.grams_grain

		# solve for how much first/second runnings we can afford
		firstrun_vol = _Volume(strike_vol - self.grams_grain)
		secondrun_vol = _Volume(tot_vol - firstrun_vol)

		firstrun_sg = _Strength(potential_points*.45/firstrun_vol)
		secondrun_sg = _Strength(potential_points*.35/secondrun_vol)

		# so, we want to know how much of the strong wort we need
		# to blend into the weak one to produce a bigbeer of given
		# volume and strength.  the assumption is that we need to
		# remove some to satisfy our boil volume; otherwise enough
		# small wort would not fit into the given boil volume
		#
		# given that:
		#  vb: volume to blend the two worts (what we are looking for)
		#
		#  v1: firstrun_vol
		#  vt: bigbeer_vol
		#  p1 & p2: gravity points of 1st and 2nd runnings
		#  pf: bigbeer_sg
		#
		# doing the math it works out to:
		#  vb = (vt*pf - v1*p1 - (vt-v1)*p2) / (p2-p1)
		vb = _Volume((bigbeer_vol*bigbeer_sg		\
		    - firstrun_vol*firstrun_sg			\
		    - (bigbeer_vol-firstrun_vol)*secondrun_sg)	\
		  / (secondrun_sg - firstrun_sg))

		smallbeer_sg = Strength((vb*firstrun_sg
		    + (smallbeer_vol-vb)*secondrun_sg) / smallbeer_vol,
		    Strength.SG_PTS)

		# The other option is to run the second runnings into the
		# first wort until the desired gravity is reached, and then
		# run the mixed wort into the second kettle.  The advantage
		# is that not as much HLT volume is required.  The disadvantage
		# is that the first pot will be heavier.
		#
		# So, doing the math again, we end up with:
		# vr = (pf*v1 - p1*v1) / (p2-pf)
		vr = _Volume((bigbeer_sg*firstrun_vol - firstrun_sg*firstrun_vol)
		    / (secondrun_sg - bigbeer_sg))

		if firstrun_sg < bigbeer_sg or vb < 0:
			raise PilotError('not enough malts for ' \
			    + str(bigbeer_vol) + ' of ' + str(bigbeer_sg))

		print('Water temp:\t', \
		    self.__striketemp(mashtemp, strike_vol))

		print('1st run vol:\t', firstrun_vol)
		print('1st run SG:\t', firstrun_sg)
		print('2nd run vol:\t', secondrun_vol)
		print('2nd run SG:\t', secondrun_sg)
		print()
		print('Big beer SG:\t', bigbeer_sg)
		print('Big beer vol:\t', bigbeer_vol)
		print('Small beer SG:\t', smallbeer_sg)
		print('Small beer vol:\t', smallbeer_vol)

		print()
		print('\tBlend first:')
		print('1) Gather first runnings into BK1')
		print('2) Run', vb, 'from BK1 to BK2')
		print('3) Fill BK1 up to total volume using second runnings')
		print('4) Fill BK2 with remainder of the runnings')

		print()
		print('\tRun first:')
		print('1) Gather first runnings into BK1')
		print('2) Run', vr, 'of second runnings into BK1')
		print('3) Fill BK2 with remainder of the runnings')
		print('4) Run', Volume((firstrun_vol+vr)-bigbeer_vol),
		    'from BK1 to BK2')

from WBC import sysparams

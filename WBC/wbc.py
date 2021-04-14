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

import copy
import inspect

from WBC import constants
from WBC import fermentables
from WBC.getparam import getparam

from WBC.utils import *
from WBC.units import *
from WBC.units import _Mass, _Strength, _Temperature, _Volume
from WBC.hop import Hop
from WBC.mash import Mash
from WBC.worter import Worter

from WBC import brewutils, timespec
from WBC.timespec import Timespec

def checkconfig():
	return True

class WBC:
	pass

class Recipe:
	def __init__(self, name, yeast, volume, boiltime = 60):
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
		timespec.set_boiltime(self.boiltime)
		self.input = input

		self.volume_inherent = volume
		self.volume_scaled = None

		self.hops_bymass = []
		self.hops_bymassvolume = []
		self.hops_byIBU = []
		self.hops_recipeIBU = None
		self.hops_recipeBUGU = None

		self.fermentables_bymass = []
		self.fermentables_bymassvol = []
		self.fermentables_bypercent = []
		self.fermentables_restguess = []
		self.fermentables_therest = []

		self.opaques_bymass = []
		self.opaques_bymassvolume = []
		self.opaques_byvolume = []
		self.opaques_byvolumevolume = []
		self.opaques_byopaque = []

		# final strength
		self.anchor = None

		self.input['stolen_wort'] = Worter()

		self.hopsdrunk = {'kettle':_Volume(0), 'fermentor':_Volume(0),
		    'package':_Volume(0)}

		self._calculatestatus = 0

		self.mash = Mash()

		self.__once = []

		sysparams.processdefaults()

	def paramfile(self, filename):
		Sysparams.processfile(filename)

	def __havefermentable(self, fermentable, when):
		v = [x for x in self.fermentables_bymass
		    + self.fermentables_bypercent
		    if x['fermentable'].name==fermentable and x['when']==when]
		if len(v) > 0:
			return True
		return False

	THEREST=	object()

	def __final_volume(self):
		assert(self._calculatestatus > 0)
		if self.volume_scaled is not None:
			return self.volume_scaled
		return self.volume_inherent

	def __grain_absorption(self):
		rv = getparam('grain_absorption')
		absorp = rv[0] / rv[1]
		return absorp

	def __reference_temp(self):
		return getparam('ambient_temp')

	def __volume_at_stage(self, stage):
		stgs = Worter.stages
		assert(stage in stgs)
		sidx = stgs.index(stage)
		assert(sidx >= stgs.index(Worter.MASH)
		    and sidx <= stgs.index(Worter.PACKAGE))

		v = self.__final_volume()

		# configured kettle loss + dryhop loss
		if sidx <= stgs.index(Worter.FERMENTOR):
			v += self.hopsdrunk['fermentor']
			v += getparam('fermentor_loss')

		# configured kettle loss + hop loss
		if sidx <= stgs.index(Worter.POSTBOIL):
			v += self.hopsdrunk['kettle']
			v += getparam('kettle_loss')

		# preboil volume is postboil + boil loss
		if sidx <= stgs.index(Worter.PREBOIL):
			v += getparam('boiloff_perhour') * (self.boiltime/60.0)

		if sidx <= stgs.index(Worter.MASH):
			# XXX: should not calculate non-grains into this figure
			# (rarely relevant problem, only e.g. when doing a
			# "topped-up" partigyle-mash)
			f = self._fermentables_atstage(Timespec.MASH) + \
			    self._fermentables_atstage(Timespec.POSTMASH)
			m = self._fermentables_mass(f)
			v += m*self.__grain_absorption() + getparam('mlt_loss')

			v += self.mash.evaporation()

		return _Volume(v)

	def __scale(self, what):
		if self.volume_inherent is None or self.volume_scaled is None:
			return what

		assert(isinstance(what, Mass) or isinstance(what, Volume))

		scale = self.volume_scaled / self.volume_inherent
		return what.__class__(scale * what, what.defaultunit)

	def once(self, callme, *args):
		cf = inspect.stack()[1]
		caller = cf[1] + '/' + str(cf[2]) + '/' + cf[3]
		if caller in self.__once:
			return

		self.__once.append(caller)
		callme(*args)

	def set_volume_and_scale(self, volume):
		checktype(volume, Volume)
		self.volume_scaled = volume

	def set_volume(self, volume):
		checktype(volume, Volume)
		self.volume_inherent = volume

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

	def _hopstore(self, hop, amount, time):
		return [hop, amount, time]

	#
	# hop additions all have the signature (hop, amountspec, time)
	# where "amountspec" is more complicated than one variable,
	# e.g. mass/vol, a tuple is used to retain signature
	#
	def hop_bymass(self, hop, mass, time):
		checktypes([(hop, Hop), (mass, Mass)])
		self.hops_bymass.append(self._hopstore(hop, mass, time))

	# mass per final volume
	def hop_bymassvolratio(self, hop, mv, time):
		(mass, vol) = mv
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass(mass / vol)
		self.hops_bymassvolume.append(self._hopstore(hop,
		    hopmass, time))

	# alpha acid mass
	def hop_byAA(self, hop, mass, time):
		checktypes([(hop, Hop), (mass, Mass)])
		hopmass = _Mass(mass / (hop.aapers/100.0))
		self.hops_bymass.append(self._hopstore(hop, hopmass, time))

	# alpha acid mass per final volume
	def hop_byAAvolratio(self, hop, mv, time):
		(mass, vol) = mv
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass((mass / (hop.aapers/100.0)) / vol)
		self.hops_bymassvolume.append(self._hopstore(hop,
		    hopmass, time))

	def hop_byIBU(self, hop, IBU, time):
		checktype(hop, Hop)
		self.hops_byIBU.append(self._hopstore(hop, IBU, time))

	def hop_byrecipeIBU(self, hop, IBU, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			if IBU > 120.0:
				warn("Hop \"" + hop.name + "\" has high IBU ("
				    + str(IBU) + ")\n")
			self.hops_recipeIBU = self._hopstore(hop, IBU, time)
		else:
			raise PilotError('total IBU/BUGU specified >once')

	def hop_byrecipeBUGU(self, hop, bugu, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			if bugu > 2.0:
				warn("Hop \"" + hop.name + "\" has high BUGU ("
				    + str(bugu) + ")\n")
			self.hops_recipeBUGU = self._hopstore(hop, bugu, time)
		else:
			raise PilotError('total IBU/BUGU specified >once')


	# opaque additions.  not used for in-recipe calculations,
	# just printed out in timed additions.
	@staticmethod
	def _opaquestore(opaque, amount, time):
		return {
			'opaque': opaque,
			'amount': amount,
			'time'  : time,
		}

	def opaque_bymass(self, opaque, mass, time):
		checktypes([(mass, Mass), (time, Timespec)])
		self.opaques_bymass.append(self._opaquestore(opaque,
		    mass, time))
	def opaque_byvol(self, opaque, volume, time):
		checktypes([(volume, Volume), (time, Timespec)])
		self.opaques_byvolume.append(self._opaquestore(opaque,
		    volume, time))

	def opaque_bymassvolratio(self, opaque, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume), (time, Timespec)])
		opaquemass = _Mass(mass / vol)
		self.opaques_bymassvolume.append(self._opaquestore(opaque,
		    opaquemass, time))
	def opaque_byvolvolratio(self, opaque, vv, time):
		(v1, v2) = vv
		checktypes([(v1, Volume), (v2, Volume), (time, Timespec)])
		opaquevolume = _Volume(v1 / v2)
		self.opaques_byvolumevolume.append(self._opaquestore(opaque,
		    opaquevolume, time))

	# mass per final volume
	def opaque_byopaque(self, opaque, ospec, time):
		checktype(time, Timespec)
		if ospec.__class__ != str:
			raise PilotError('opaque spec must be a string')
		self.opaques_byopaque.append(self._opaquestore(opaque,
		    ospec, time))

	def anchor_bystrength(self, strength):
		checktype(strength, Strength)

		if self.anchor is not None:
			raise PilotError('anchor already set')
		self.anchor = strength
		self.input['strength'] = strength

	def __validate_ferm(self, name, fermentable, when):
		if self.__havefermentable(fermentable.name, when):
			raise PilotError('fermentables may be specified max '
			    + 'once per stage')

		# we would throw an error here, but then again, if someone
		# want to put sugars into their mash, it's not our business
		# to tell them not to.
		#
		#if not fermentable.conversion and when == WBC.MASH:
		#	raise PilotError('fermentable "' + name + '" does not '
		#	    + 'need a mash')

	@staticmethod
	def _fermmap(name, fermentable, type, amount, when):
		return {
			'name': name,
			'fermentable' : fermentable,
			type : amount,
			'when' : when,
		}

	def fermentable_bymass(self, name, mass, when):
		checktypes([(mass, Mass), (when, Timespec)])

		fermentable = fermentables.Get(name)
		self.__validate_ferm(name, fermentable, when)

		f = self._fermmap(name, fermentable, 'mass', mass, when)
		self.fermentables_bymass.append(f)

	def fermentable_bymassvolratio(self, name, mv, when):
		checktype(when, Timespec)
		(mass, vol) = mv
		checktype(mass, Mass)
		checktype(vol, Volume)
		normmass = _Mass(mass / vol)

		fermentable = fermentables.Get(name)
		self.__validate_ferm(name, fermentable, when)

		f = self._fermmap(name, fermentable, 'massvol', normmass, when)
		self.fermentables_bymassvol.append(f)

	# percent of fermentable's mass, not extract's mass
	def fermentable_bypercent(self, name, percent, when):
		if percent is not self.THEREST and percent <= 0:
			raise PilotError('grain percentage must be positive '\
			  '(it is a fun thing!)')

		fermentable = fermentables.Get(name)
		self.__validate_ferm(name, fermentable, when)

		f = self._fermmap(name, fermentable, 'percent', percent, when)
		if percent is self.THEREST:
			self.fermentables_therest.append(f)
		else:
			self.fermentables_bypercent.append(f)
			if sum(x['percent'] \
			    for x in self.fermentables_bypercent) > 100:
				raise PilotError('captain, I cannot change the'\
				    ' laws of math; 100% fermentables max!')

	# indicate that we want to "borrow" some wort at the preboil stage
	# for e.g. building starters.
	def steal_preboil_wort(self, vol, strength):
		checktypes([(vol, Volume), (strength, Strength)])

		self.input['stolen_wort'].set_volstrength(vol, strength)

	def fermentable_percentage(self, what, theoretical=False):
		f = what['fermentable']
		percent = f.extract.cgai()
		if f.conversion and not theoretical:
			percent *= getparam('mash_efficiency')/100.0
		return percent

	def fermentable_yield(self, what, theoretical=False):
		return _Mass(what['mass']
		    * self.fermentable_percentage(what, theoretical)/100.0)

	def _fermentables_atstage(self, when):
		spec = timespec.stage2timespec[when]

		assert('fermentables' in self.results)
		return [x for x in self.results['fermentables'] \
		    if x['when'].__class__ in spec]

	def _fermentables_mass(self, fermlist):
		return _Mass(sum(x['mass'] for x in fermlist))

	def total_yield(self, stage, theoretical=False):
		assert('fermentables' in self.results)
		assert(stage in Worter.stages)

		def yield_at_stage(stage):
			return sum([self.fermentable_yield(x, theoretical) \
			    for x in self._fermentables_atstage(stage)])

		wstg = Worter.stages
		m = yield_at_stage(Timespec.MASH)
		if wstg.index(stage) > wstg.index(Worter.MASH):
			m += yield_at_stage(Timespec.POSTMASH)
		if wstg.index(stage) > wstg.index(Worter.PREBOIL):
			m += yield_at_stage(Timespec.KETTLE)
		if wstg.index(stage) > wstg.index(Worter.POSTBOIL):
			m += yield_at_stage(Timespec.FERMENTOR)
		if wstg.index(stage) > wstg.index(Worter.FERMENTOR):
			m += yield_at_stage(Timespec.PACKAGE)

		return _Mass(m - self.input['stolen_wort'].extract())

	def _sanity_check(self):
		pbs = self.results['strengths']['preboil']
		fw = self.results['mash_conversion'][100]

		if pbs > fw:
			warn("preboil strength is greater than 100% "
			    "converted mash.\n", '\n')
			warn('=> impossible mash efficiency. '
			    'adjust "mash_efficiency" parameter.\n\n')

		# XXX: more checks on lautering feasibility needed

	# turn percentages into masses
	def _dofermentables(self):

		# calculates the mass of extract required to hit the
		# target strength.

		ferms = []

		# convert massvol to mass now that we know final_volume
		for f in self.fermentables_bymassvol:
			f['mass'] = _Mass(f['massvol'] * self.__final_volume())
			self.fermentables_bymass.append(f)
		self.fermentables_bymassvol = []

		if len(self.fermentables_bymass) > 0:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute "
				    + "fermentable mass "
				    + "does not have an inherent volume")

			# if we're scaling the recipe, we need to
			# scale the grains
			for f in self.fermentables_bymass:
				n = f.copy()
				n['mass'] = self.__scale(n['mass'])
				ferms.append(n)

		def allpers(r):
			return (r.fermentables_bypercent
			    + r.fermentables_restguess)

		if len(allpers(self)) + len(self.fermentables_therest) == 0:
			self.results['fermentables'] = ferms
			return # all done already

		bmyield = _Mass(sum([self.fermentable_yield(x) for x in ferms]))

		# XXX: we probably shouldn't allow:
		# bmyield > 0 and len(therest) == 0
		#
		# it produces a "surprising" result, and there's probably
		# no reason to not force the user to pick a base fermentable

		totpers = sum(x['percent'] for x in allpers(self))
		missing = 100 - float(totpers)

		if missing > .000001:
			if len(self.fermentables_therest) > 0:
				mp = missing / len(self.fermentables_therest)
				for tr in self.fermentables_therest:
					tr['percent'] = mp
					self.fermentables_restguess.append(tr)
				self.fermentables_therest = []

				# note: by-percent fermentables are 100% here.
				# all fermentables (if by-mass are specified)
				# might be over.  we'll adjust "restguess"
				# below so that sum of fermentables is 100%.
				assert (abs(sum(x['percent'] \
				    for x in allpers(self)) - 100.0) < .000001)
			elif len(self.fermentables_restguess) == 0:
				raise PilotError('need 100% of fermentables')

		if self.anchor is None:
			raise PilotError('anchor must be set for '
			    + 'by-percent fermentables')

		# calculate extract required for strength, and derive
		# masses of fermentables from that

		w = Worter()
		w.set_volstrength(self.__volume_at_stage(Worter.POSTBOIL),
		    self.anchor)
		extract = w.extract() + self.input['stolen_wort'].extract()

		# take into account any yield we already get from
		# per-mass additions
		if bmyield > extract:
			raise PilotError('strength anchor and '
			    'by-mass addition mismatch')
		extract -= bmyield

		# produce one best-current-guess for fermentable masses.
		def guess(f_in):
			# now, solve for the total mass:
			# extract = yield1 * m1 + yield2 * m2 + ...
			# where yieldn = extract% * mash_efficiency / 100.0
			# and   mn = pn * totmass
			# and then solve: totmass = extract / (sum(yieldn*pn))
			thesum = sum([self.fermentable_percentage(x)/100.0
			    * x['percent']/100.0 for x in allpers(self)])
			totmass = _Mass(extract / thesum)

			# Note: solution isn't 100% correct when we consider
			# adding sugars into the fermentor: the same amount
			# of sugar as into the boil will increase the strength
			# more in the fermentor due to a smaller volume.
			# But the math behind the correct calculation seems to
			# get hairy fast, so we'll let it slip at least for now.

			f_out = []
			f_out += f_in

			# set the masses of each individual fermentable
			for x in allpers(self):
				# limit mass to 0.1g accuracy
				m = int(10000*(x['percent']/100.0 * totmass)) \
				    / 10000.0
				#m = round(x['percent']/100.0 * totmass, 4)
				n = x.copy()
				n['mass'] = _Mass(m)
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
		if (len(self.fermentables_bypercent) > 0
		    and len(self.fermentables_restguess) > 0):
			iters = 30
			if bmyield > 0.0001:
				self.once(notice,
				    'finding the solution for fixed '
				    'percentages and masses\n')
			for g in range(iters):
				fr = self.fermentables_restguess
				f_guess = guess(ferms)
				fp = [x for x in f_guess if 'percent' in x]

				# pick largest value to adjust against.
				# gut feeling that it'll make things more
				# accurate.  we have to pick *some* value
				# in any case, so might as well pick this one.
				f = sorted(fp, key=lambda x: x['percent'],
				   reverse=True)[0]

				f_wanted = f['percent']
				allmass = self._fermentables_mass(f_guess)
				f_actual = 100.0 * (f['mass'] / allmass)
				diff = f_wanted - f_actual
				if abs(diff) < 0.01:
					break
				nrest = len(fr)

				# scale the diff to the "rest" values we're
				# adjusting
				scale = (fr[0]['percent'] / f_wanted)
				if scale < 1:
					scale = 1/scale
				assert(scale >= 1)
				adj = scale * (diff / nrest)
				for x in fr:
					x['percent'] -= adj
					if (x['percent'] < 0.01):
						raise PilotError('cannot solve '
						    'recipe. lower bymass or '
						    'raise strength')
			if g == iters-1:
				self.once(warn,
				    'fermentable "rest" percentages did not '
				    'converge in ' + str(iters) + ' tries\n')
		else:
			f_guess = guess(ferms)

		self.results['fermentables'] = f_guess

	def _dofermentablestats(self):
		assert('fermentables' in self.results)
		allmass = self._fermentables_mass(self.results['fermentables'])
		stats = {}

		for f in self.results['fermentables']:
			when = timespec.timespec2stage[f['when'].__class__]
			f['percent'] = 100.0 * (f['mass'] / allmass)
			f['extract_predicted'] = self.fermentable_yield(f)
			f['extract_theoretical'] = self.fermentable_yield(f,
			    theoretical=True)

			stats.setdefault(when, {})
			stats[when].setdefault('percent', 0)
			stats[when].setdefault('amount', 0)
			stats[when].setdefault('extract_predicted', 0)
			stats[when].setdefault('extract_theoretical', 0)
			stats[when]['percent'] += f['percent']
			stats[when]['amount'] += f['mass']
			stats[when]['extract_predicted'] \
			    += f['extract_predicted']
			stats[when]['extract_theoretical'] \
			    += f['extract_theoretical']

		for s in stats:
			stats[s]['amount'] = _Mass(stats[s]['amount'])
			stats[s]['extract_predicted'] \
			    = _Mass(stats[s]['extract_predicted'])
			stats[s]['extract_theoretical'] \
			    = _Mass(stats[s]['extract_theoretical'])

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
		ferms = self.results['fermentables']
		ferms = sorted(ferms, key=lambda x: x['name'], reverse=True)
		ferms = sorted(ferms, key=lambda x: x['extract_predicted'])
		ferms = sorted(ferms, key=lambda x: x['mass'])
		self.results['fermentables'] = ferms[::-1]

	def _domash(self):
		prestren = self.results['strengths']['preboil']
		totvol = _Volume(self.__volume_at_stage(Worter.MASH))
		if self.input['stolen_wort'].volume() > 0.001:
			steal = {}
			ratio = self.input['stolen_wort'].strength() / prestren
			steal['strength'] = _Strength(prestren * min(1, ratio))

			steal['volume'] = _Volume(min(1, ratio)
			    * self.input['stolen_wort'].volume())
			steal['missing'] = _Volume(self.input['stolen_wort'].volume()
			    - steal['volume'])
			totvol += steal['volume']
			self.results['steal'] = steal

		mf = self._fermentables_atstage(Timespec.MASH)
		self.mash.set_fermentables(mf)

		v = self.__volume_at_stage(Worter.POSTBOIL)

		self.results['mash'] \
		    = self.mash.do_mash(getparam('ambient_temp'),
			self.__reference_temp(), totvol,
			self.__grain_absorption())

		theor_yield = self.total_yield(Worter.MASH, theoretical=True)
		# FIXXXME: actually volume, so off-by-very-little
		watermass = self.results['mash']['mashstep_water']

		self.results['mash_conversion'] = {}
		for x in range(5, 100+1, 5):
			extract = theor_yield * x/100.0
			fw = 100 * (extract / (extract + watermass))
			self.results['mash_conversion'][x] = _Strength(fw)

		mf = self._fermentables_atstage(Timespec.MASH)
		rv = _Volume(self.results['mash']['mashstep_water']
		      - (self._fermentables_mass(mf) * self.__grain_absorption()
		        + getparam('mlt_loss')))
		if rv <= 0:
			raise PilotError('mashin ratio ridiculously low')
		self.results['mash_first_runnings_max'] = rv

	def _dovolumes(self):
		res = {}
		res[Worter.MASH] = self.__volume_at_stage(Worter.MASH)
		res[Worter.FERMENTOR] = self.__volume_at_stage(Worter.FERMENTOR)
		res[Worter.PACKAGE] = self.__volume_at_stage(Worter.PACKAGE)

		def v_at_temp(name):
			v = self.__volume_at_stage(name)
			res[name] = v
			vt = brewutils.water_vol_at_temp(v,
			    self.__reference_temp(), getparam(name + '_temp'))
			res[name + '_attemp'] = vt
		v_at_temp(Worter.PREBOIL)
		v_at_temp(Worter.POSTBOIL)

		self.results['volumes'] = res

	# Solve the strength of the wort at various stages.
	# For preboil we get it from the configured mash efficiency.
	# For other stages we need to account for losses.  We assume
	# a uniform loss, i.e. if we lose 10% of the volume, we lose 10%
	# of the extract. XXX: we don't do that accounting yet, so the
	# solutions are by large inaccurate for brews with a large
	# amount of non-mash fermentables
	def _dostrengths(self):
		vols = self.results['volumes']

		strens = {}
		strens[Worter.PREBOIL] = brewutils.solve_strength(
		    self.total_yield(Worter.PREBOIL), vols[Worter.PREBOIL])
		# XXX?
		strens['final'] = brewutils.solve_strength(
		    self.total_yield(Worter.FERMENTOR), vols[Worter.FERMENTOR])
		strens[Worter.POSTBOIL] = brewutils.solve_strength(
		    self.total_yield(Worter.POSTBOIL), vols[Worter.POSTBOIL])
		self.results['strengths'] = strens

	@staticmethod
	def _hopmap(hop, mass, time, ibu):
		return {
		    'hop' : hop,
		    'mass' : mass,
		    'time' : time,
		    'ibu' : ibu,
		}
	@staticmethod
	def _hopunmap(h):
		return (h['hop'], h['mass'], h['time'], h['ibu'])

	def _dohops(self):
		allhop = []

		# ok, um, so the Tinseth formula uses postboil volume ...
		v_post = self.__volume_at_stage(Worter.POSTBOIL)

		# ... and average gravity during the boil.  *whee*
		v_pre = self.__volume_at_stage(Worter.PREBOIL)
		y = self.total_yield(Worter.POSTBOIL)
		t = brewutils.solve_strength(y, v_pre).valueas(Strength.SG) \
		    + brewutils.solve_strength(y, v_post).valueas(Strength.SG)
		sg = Strength(t/2, Strength.SG)

		# calculate IBU produced by "bymass" hops and add to printables
		for h in self.hops_bymass:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute hop "
				    + "mass does not have an inherent volume")
			mass = self.__scale(h[1])
			ibu = h[0].IBU(sg, v_post, h[2], mass)
			allhop.append(Recipe._hopmap(h[0], mass, h[2], ibu))

		for h in self.hops_bymassvolume:
			mass = _Mass(h[1] * self.__final_volume())
			ibu = h[0].IBU(sg, v_post, h[2], mass)
			allhop.append(Recipe._hopmap(h[0], mass, h[2], ibu))

		# calculate mass of "byIBU" hops and add to printables
		for h in self.hops_byIBU:
			mass = h[0].mass(sg, v_post, h[2], h[1])
			allhop.append(Recipe._hopmap(h[0], mass, h[2], h[1]))

		totibus = sum([x['ibu'] for x in allhop])
		if self.hops_recipeIBU is not None:
			h = self.hops_recipeIBU
			missibus = self.hops_recipeIBU[1] - totibus
			if missibus <= 0:
				raise PilotError('total IBUs are greater than '\
				    + 'desired total')
			mass = h[0].mass(sg, v_post, h[2], missibus)
			allhop.append(Recipe._hopmap(h[0], mass, h[2],missibus))
			totibus += missibus

		if self.hops_recipeBUGU is not None:
			h = self.hops_recipeBUGU
			bugu = self.hops_recipeBUGU[1]
			stren = self.results['strengths']['final']
			ibus = stren.valueas(stren.SG_PTS) * bugu
			missibus = ibus - totibus
			mass = h[0].mass(sg, v_post, h[2], missibus)
			allhop.append(Recipe._hopmap(h[0], mass, h[2],missibus))
			totibus += missibus

		# sort alphabetically here (generic code doesn't know how)
		allhop = sorted(allhop, key=lambda x: x['hop'].name)

		# calculate amount of wort that hops will drink
		hd = {x: 0 for x in self.hopsdrunk}
		packagedryhopvol = 0
		for h in allhop:
			(hop, mass, time, ibu) = Recipe._hopunmap(h)
			if isinstance(time, timespec.Fermentor):
				hd['fermentor'] += hop.absorption(mass)
			elif isinstance(time, timespec.Package):
				hd['package'] += hop.absorption(mass)
				packagedryhopvol += hop.volume(mass)
			else:
				hd['kettle'] += hop.absorption(mass)
		self.hopsdrunk = {x: _Volume(hd[x]) for x in hd}
		self.hopsdrunk['volume'] = _Volume(packagedryhopvol)

		self.results['hops'] = allhop

		totmass = _Mass(sum(x['mass'] for x in allhop))
		self.results['hop_stats'] = Recipe._hopmap('all',
		    totmass, None, totibus)

	def _dotimers(self):
		opaques = self.opaques_bymass + self.opaques_byvolume \
		    + self.opaques_byopaque
		for o in self.opaques_bymassvolume:
			mass = _Mass(o['amount'] * self.__final_volume())
			opaques.append(self._opaquestore(o['opaque'], mass,
			    o['time']))
		for o in self.opaques_byvolumevolume:
			volume = _Volume(o['amount'] * self.__final_volume())
			opaques.append(self._opaquestore(o['opaque'], volume,
			    o['time']))

		# sort the timerable additions
		timers = self.results['hops'] + opaques
		timers = sorted(timers, key=lambda x: x['time'], reverse=True)

		# calculate "timer" field values
		prevtype = None
		timer = 0
		boiltimer = 0
		for t in reversed(timers):
			time = t['time']
			if prevtype is None or not isinstance(time, prevtype):
				timer = 0
				prevval = None
				prevtype = time.__class__

			if isinstance(time, timespec.Mash):
				t['timer'] = str(time)
			if isinstance(time, timespec.Fermentor):
				t['timer'] = str(time)
			if isinstance(time, timespec.Package):
				t['timer'] = str(time)

			if isinstance(time, timespec.Whirlpool):
				if prevval is not None \
				    and prevval[0] == time.temp:
					if prevval[1] == time.time:
						t['timer'] = '=='
					else:
						v = time.time - prevval[1]
						t['timer'] = str(v) + ' min'
				else:
					t['timer'] = str(time.time) + ' min'
				prevval = (time.temp, time.time)

			if isinstance(time, timespec.Boil):
				cmpval = time.time
				thisval = '=='

				if time.spec == 'FWH':
					cmpval = self.boiltime

				if cmpval != timer:
					thisval = str(cmpval - timer) + ' min'
					timer = cmpval
				t['timer'] = thisval
				boiltimer = timer

		# if timers don't start from start of boil, add an opaque
		# to specify initial timer value
		if self.boiltime > 0 and boiltimer != self.boiltime:
			sb = self._opaquestore('', '',
			    timespec.Boil(self.boiltime))
			sb['timer'] = str(self.boiltime - boiltimer) + ' min'
			timers = sorted([sb] + timers,
			    key=lambda x: x['time'], reverse=True)

		self.results['timer_additions'] = timers

	def _doferment(self):
		self._doattenuate()

	def _doattenuate(self, attenuation = (60, 86, 5)):
		res = []
		fin = self.results['strengths']['final']
		for x in range(*attenuation):
			t = fin.attenuate_bypercent(x)
			res.append((x, t['ae'], t['abv']))
		self.results['attenuation'] = res

	def calculate(self):
		sysparams.checkset()

		if self._calculatestatus:
			raise PilotError("you can calculate() a recipe once")
		self._calculatestatus += 1

		if self.__final_volume() is None:
			raise PilotError("final volume is not set")

		s = self.__scale(_Mass(1))
		if abs(s - 1.0) > .0001:
			notice('Scaling recipe ingredients by a factor of '
			    + '{:.4f}'.format(s) + '\n')

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

			self._dofermentables()
			self._dovolumes()
			prevol = self.__volume_at_stage(Worter.MASH)
			self._dostrengths()
			self._domash()
			self._dohops()
			if prevol+.01 >= self.__volume_at_stage(Worter.MASH):
				break
		else:
			raise Exception('recipe failed to converge ... panic?')

		# do the volumes once more to finalize them with the
		# final hop thirst
		self._dovolumes()

		self._dotimers()

		self._dofermentablestats()
		self._doferment()

		# calculate suggested pitch rates, using 0.75mil/ml/degP for
		# ales and 1.5mil for lagers
		tmp = self.__volume_at_stage(Worter.FERMENTOR) * 1000 \
		    * self.results['strengths']['final']
		bil = 1000*1000*1000
		self.results['pitch'] = {}
		self.results['pitch']['ale']   = tmp * 0.75*1000*1000 / bil
		self.results['pitch']['lager'] = tmp * 1.50*1000*1000 / bil

		# calculate color, via MCU & Morey equation
		t = sum(f['mass'].valueas(Mass.LB) \
		    * f['fermentable'].color.valueas(Color.LOVIBOND) \
		        for f in self.results['fermentables'])
		v = self.results['volumes']['postboil'].valueas(Volume.GALLON)
		mcu = t / v
		self.results['color'] = \
		    Color(1.4922 * pow(mcu, 0.6859), Color.SRM)

		# calculate brewhouse estimated afficiency ... NO, efficiency
		maxyield = self.total_yield(Worter.FERMENTOR, theoretical=True)
		maxstren = brewutils.solve_strength(maxyield,
		    self.__final_volume())
		self.results['brewhouse_efficiency'] = \
		    self.results['strengths']['final'] / maxstren

		# this one is easy
		self.results['hopsdrunk'] = self.hopsdrunk

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
		    + '|' + str(float(self.results['volumes']['package'])))

		self.mash.printcsv()

		print('# fermentable|name|mass|when')
		for g in self.results['fermentables']:
			print('fermentable|{:}|{:}|{:}'\
			    .format(g['fermentable'].name,
			      float(g['mass']), g['when']))

		print('# hop|name|type|aa%|mass|timeclass|timespec')
		for h in self.results['hops']:
			hop = h['hop']
			time = h['time']
			timeclass = time.__class__.__name__.lower()
			timespec = str(time).replace(chr(0x00b0), "deg")
			timespec = str(timespec)

			print('hop|{:}|{:}|{:}|{:}|{:}|{:}'
			    .format(hop.name, hop.typestr, hop.aapers,
				float(h['mass']), timeclass, timespec))

	def do(self):
		self.calculate()
		self.printit()

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

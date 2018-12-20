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

import Constants
import Fermentables
from Getparam import getparam

from Utils import *
from Units import *
from Units import _Mass, _Strength, _Temperature, _Volume
from Hop import Hop
from Mash import Mash

import Brewutils

def checkconfig():
	return True

class WBC:
	MASH=		'Mash'
	STEEP=		'Steep'
	BOIL=		'Boil'
	FERMENT=	'Ferment'
	PACKAGE=	'Package'
	stages=		[ MASH, STEEP, BOIL, FERMENT, PACKAGE ]

class Recipe:
	def __init__(self, name, yeast, volume, boiltime = 60):
		# volume may be None if the recipe contains only relative units
		if volume is not None:
			checktype(volume, Volume)

		input = {}
		input['name' ] = name
		input['yeast'] = yeast

		input['water_notes'] = None
		input['notes'] = []

		self.boiltime = input['boiltime'] = boiltime
		self.input = input

		self.volume_inherent = volume
		self.volume_scaled = None

		self.hops_bymass = []
		self.hops_bymassvolume = []
		self.hops_byIBU = []
		self.hops_recipeIBU = None
		self.hops_recipeBUGU = None

		self.fermentables_bymass = []
		self.fermentables_bypercent = []
		self.fermentables_therest = []

		# final strength or mass of one fermentable
		self.anchor = None

		self.input['stolen_wort'] = {
			'volume'	: _Volume(0),
			'strength'	: _Strength(0),
			'extract'	: _Mass(0),
		}

		self.hopsdrunk = {'kettle':_Volume(0), 'fermenter':_Volume(0),
		    'package':_Volume(0)}

		self._calculatestatus = 0

		self.mash = Mash()

		Sysparams.processdefaults()

	def paramfile(self, filename):
		Sysparams.processfile(filename)

	def __havefermentable(self, fermentable, when):
		v = filter(lambda x: x['fermentable'].name == fermentable \
		    and x['when'] == when,
		    self.fermentables_bymass + self.fermentables_bypercent)
		if len(v) > 0:
			return True
		return False

	# constants must be in ascending order
	MASHWATER=	1
	PREBOIL=	2
	POSTBOIL=	3
	FERMENTER=	4
	FINAL=		5

	THEREST=	object()

	def __final_volume(self):
		assert(self._calculatestatus > 0)
		if self.volume_scaled is not None:
			return self.volume_scaled
		return self.volume_inherent

	def __grain_absorption(self):
		rv = getparam('grain_absorption')
		absorp = rv[0] / rv[1].valueas(Mass.KG)
		return absorp

	def __reference_temp(self):
		return getparam('ambient_temp')

	def __volume_at_stage(self, stage):
		assert(stage >= self.MASHWATER and stage <= self.FINAL)

		v = self.__final_volume()

		# assume 0.8l static loss in fermentor, plus fermentor dryhops
		# XXX: probably should be variable loss per fermentation size,
		#      but I don't have any data on that, so this will do
		#      for now
		if stage <= self.FERMENTER:
			v += self.hopsdrunk['fermenter']
			v += 0.8

		# assume 0.8% of boil plus 0.42l plus hop crud lost in kettle
		# (no facts were harmed in coming up with this number)
		if stage <= self.POSTBOIL:
			v += self.hopsdrunk['kettle'] + _Volume(0.42)
			v *= 1.008

		# preboil volume is postboil + boil loss
		if stage <= self.PREBOIL:
			v += getparam('boiloff_perhour') * (self.boiltime/60.0)

		if stage <= self.MASHWATER:
			# XXX: should not calculate sugar into this figure
			m = self._fermentables_allmass().valueas(Mass.KG)
			v += self.__grain_absorption()*m + getparam('mlt_loss')

		return _Volume(v)

	def __extract(self, vol, strength):
		m = Mass(vol * strength.valueas(Strength.SG), Mass.KG)
		return Mass(m.valueas(Mass.G)
		    * strength.valueas(Strength.PLATO)/100.0, Mass.G)

	def __scale(self, what):
		if self.volume_inherent is None or self.volume_scaled is None:
			return what

		assert(isinstance(what, Mass))

		scale = self.volume_scaled / self.volume_inherent
		return _Mass(scale * what)

	def set_volume_and_scale(self, volume):
		checktype(volume, Volume)
		self.volume_scaled = volume

	def set_volume(self, volume):
		checktype(volume, Volume)
		self.volume_inherent = volume

	# set opaque water notes to be printed with recipe
	def set_water_notes(self, waternotes):
		checktype(waternotes, str)
		if self.input['water_notes'] is not None:
			warn('water notes already set')
		self.input['water_notes'] = waternotes

	def add_note(self, note):
		checktype(note, str)
		self.input['notes'].append(note)

	def _hopstore(self, hop, amount, time):
		time.resolvetime(self.boiltime)
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

	def hop_recipeIBU(self, hop, IBU, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			self.hops_recipeIBU = self._hopstore(hop, IBU, time)
		else:
			raise PilotError('total IBU/BUGU specified >once')

	def hop_recipeBUGU(self, hop, bugu, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			self.hops_recipeBUGU = self._hopstore(hop, bugu, time)
		else:
			raise PilotError('total IBU/BUGU specified >once')

	def __doanchor(self, what, value):
		if not self.anchor is None:
			raise PilotError('anchor already set')
		self.anchor = {'what' : what, 'value' : value }

	def anchor_bystrength(self, strength):
		checktype(strength, Strength)

		self.__doanchor('strength', strength)

	def anchor_bymass(self, fermentable, mass):
		checktype(mass, Mass)

		f = Fermentables.get(fermentable)
		self.__doanchor('mass', {
			'fermentable' : f,
			'mass' : mass,
		})

	def __validate_ferm(self, name, fermentable, when):
		if when not in WBC.stages:
			raise PilotError('invalid fermentation stage')

		if self.__havefermentable(fermentable.name, when):
			raise PilotError('fermentables may be specified max '
			    + 'once per stage')

		if fermentable.needmash and when != WBC.MASH:
			raise PilotError('fermentable "' + name + '" needs '
			    + 'a mash')

		# we would throw an error here, but then again, if someone
		# want to put sugars into their mash, it's not our business
		# to tell them not to.
		#
		#if not fermentable.conversion and when == WBC.MASH:
		#	raise PilotError('fermentable "' + name + '" does not '
		#	    + 'need a mash')

	@staticmethod
	def _fermmap(name, fermentable, amount, when):
		return {
			'name': name,
			'fermentable' : fermentable,
			'amount' : amount,
			'when' : when,
		}

	@staticmethod
	def _fermunmap(f):
		return (f['name'], f['fermentable'], f['amount'], f['when'])

	def fermentable_bymass(self, name, mass, when=WBC.MASH):
		checktype(mass, Mass)

		fermentable = Fermentables.get(name)
		self.__validate_ferm(name, fermentable, when)

		f = self._fermmap(name, fermentable, mass, when)
		self.fermentables_bymass.append(f)

	# percent of fermentable's mass, not extract's mass
	def fermentable_bypercent(self, name, percent, when=WBC.MASH):
		if percent is not self.THEREST and percent <= 0:
			raise PilotError('grain percentage must be positive '\
			  '(it is a fun thing!)')

		fermentable = Fermentables.get(name)
		self.__validate_ferm(name, fermentable, when)

		f = self._fermmap(name, fermentable, percent, when)
		if percent is self.THEREST:
			self.fermentables_therest.append(f)
		else:
			self.fermentables_bypercent.append(f)
			if sum(x['amount'] \
			    for x in self.fermentables_bypercent) > 100:
				raise PilotError('captain, I cannot change the'\
				    ' laws of math; 100% fermentables max!')

	# indicate that we want to "borrow" some wort at the preboil stage
	# for e.g. building starters.
	def steal_preboil_wort(self, vol, strength):
		checktypes([(vol, Volume), (strength, Strength)])

		extract = self.__extract(vol, strength)
		self.input['stolen_wort'] = {
			'volume'	: vol,
			'strength'	: strength,
			'extract'	: extract
		}

	def fermentable_percentage(self, what, theoretical=False):
		f = what['fermentable']
		if f.extract_legacy is True:
			warn('fermentable "' + f.name + '" uses '
			    + 'legacy extract specification\n')
			f.extract_legacy = False
		percent = f.extract
		if f.conversion and not theoretical:
			percent *= getparam('mash_efficiency')/100.0
		return percent

	def fermentable_yield(self, what, theoretical=False):
		return _Mass(what['amount']
		    * self.fermentable_percentage(what, theoretical)/100.0)

	def _fermentables_atstage(self, when):
		assert('fermentables' in self.results)
		return filter(lambda x: x['when'] == when,
		    self.results['fermentables'])

	def _fermentables_allstage(self):
		assert('fermentables' in self.results)
		return self.results['fermentables']

	def _fermentables_mass(self, fermlist):
		return _Mass(sum(x['amount'] for x in fermlist))

	def _fermentables_allmass(self):
		assert('fermentables' in self.results)
		return _Mass(sum(x['amount'] \
		    for x in self.results['fermentables']))

	def total_yield(self, stage, theoretical=False):
		assert('fermentables' in self.results)

		def yield_at_stage(stage):
			return sum([self.fermentable_yield(x, theoretical) \
			    for x in self._fermentables_atstage(stage)])
		m = yield_at_stage(WBC.MASH)
		if stage == WBC.STEEP or stage == WBC.BOIL \
		    or stage == WBC.FERMENT:
			m += yield_at_stage(WBC.STEEP)
		if stage == WBC.BOIL or stage == WBC.FERMENT:
			m += yield_at_stage(WBC.BOIL)
		if stage == WBC.FERMENT:
			m += yield_at_stage(WBC.FERMENT)
		return _Mass(m - self.input['stolen_wort']['extract'])

	def _sanity_check(self):
		pbs = self.results['strengths']['preboil'].valueas(Strength.PLATO)
		fw = self.results['mash_first_wort_max'].valueas(Strength.PLATO)

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
		if len(self.fermentables_bymass) > 0:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute "
				    + "fermentable mass "
				    + "does not have an inherent volume")

			# if we're scaling the recipe, we need to
			# scale the grains
			for f in self.fermentables_bymass:
				n = f.copy()
				n['amount'] = self.__scale(n['amount'])
				ferms.append(n)

		if len(self.fermentables_bypercent) == 0 \
		    and len(self.fermentables_therest) == 0:
			self.results['fermentables'] = ferms
			return # all done already

		bmyield = sum([self.fermentable_yield(x) \
		    for x in self.fermentables_bymass])

		totpers = sum(x['amount'] for x in self.fermentables_bypercent)
		missing = 100 - float(totpers)
		if missing > .000001:
			# XXXTODO: nonintrusively assert we're here max once
			ltr = len(self.fermentables_therest)
			if ltr == 0:
				raise PilotError('fermentable percentages add '
				    + 'up to only ' + str(totpers)
				    + '%, need 100%')
			mp = missing / ltr
			for tr in self.fermentables_therest:
				tr['amount'] = mp
				self.fermentables_bypercent.append(tr)
		# yay for floating points
		assert (abs(sum(x['amount'] \
		    for x in self.fermentables_bypercent) - 100.0) < .000001)

		if self.anchor is None:
			raise PilotError('anchor must be set for '
			    + 'by-percent fermentables')

		if self.anchor['what'] == 'strength':
			# calculate extract required for strength, and derive
			# masses of fermentables from that

			extract = self.__extract(
			    self.__volume_at_stage(self.POSTBOIL),
			    self.anchor['value']) \
			      + self.input['stolen_wort']['extract']

			# take into account any yield we already get from
			# per-mass additions
			if bmyield > extract:
				raise PilotError('strength anchor and '
				    'by-mass addition mismatch')
			extract -= bmyield

			# now, solve for the total mass:
			# extract = yield1 * m1 + yield2 * m2 + ...
			# where yieldn = extract% * mash_efficiency / 100.0
			# and   mn = pn * totmass
			# and then solve: totmass = extract / (sum(yieldn*pn))
			thesum = sum([self.fermentable_percentage(x)/100.0
			    * x['amount']/100.0
			    for x in self.fermentables_bypercent])
			totmass = _Mass(extract / thesum)

			# Note: solution isn't 100% correct when we consider
			# adding sugars into the fermentor: the same amount
			# of sugar as into the boil will increase the strength
			# more in the fermentor due to a smaller volume.
			# But the math behind the correct calculation seems to
			# get hairy fast, so we'll let it slip at least for now.

		elif self.anchor['what'] == 'mass':
			# mass of one fermentable is set, others are
			# simply scaled to that value

			a = self.anchor['value']
			aname = a['fermentable'].name
			f = filter(lambda x: x['fermentable'].name == aname,
			    self.fermentables_bypercent)
			if len(f) == 0:
				raise PilotError("could not find anchor "
				    "fermentable: " + aname)
			anchorpers = sum(x['amount'] for x in f)
			totmass = a['mass'] / (anchorpers/100.0)

		# and finally set the masses of each individual fermentable
		for x in self.fermentables_bypercent:
			# limit mass to 0.1g accuracy
			m = int(10 * (x['amount']/100.0 * totmass)) / 10.0
			n = x.copy()
			n['amount'] = _Mass(m)
			ferms.append(n)
		self.results['fermentables'] = ferms

	def _dofermentablestats(self):
		assert('fermentables' in self.results)
		allmass = self._fermentables_allmass()
		stats = {}

		for f in self.results['fermentables']:
			when = f['when']
			f['percent'] = 100.0 * (f['amount'] / allmass)
			f['extract_predicted'] = self.fermentable_yield(f)
			f['extract_theoretical'] = self.fermentable_yield(f,
			    theoretical=True)

			stats.setdefault(when, {})
			stats[when].setdefault('percent', 0)
			stats[when].setdefault('amount', 0)
			stats[when].setdefault('extract_predicted', 0)
			stats[when].setdefault('extract_theoretical', 0)
			stats[when]['percent'] += f['percent']
			stats[when]['amount'] += f['amount']
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

	def _domash(self):
		prestren = self.results['strengths']['preboil']
		totvol = _Volume(self.__volume_at_stage(self.MASHWATER))
		if self.input['stolen_wort']['volume'] > 0.001:
			steal = {}
			ratio = self.input['stolen_wort']['strength'] / prestren
			steal['strength'] = _Strength(prestren * min(1, ratio))

			steal['volume'] = _Volume(min(1, ratio)
			    * self.input['stolen_wort']['volume'])
			steal['missing'] = _Volume(self.input['stolen_wort']['volume']
			    - steal['volume'])
			totvol += steal['volume']
			self.results['steal'] = steal

		mf = self._fermentables_atstage(WBC.MASH)
		self.mash.set_fermentables(mf)

		v = self.__volume_at_stage(self.POSTBOIL)

		self.results['mash'] \
		    = self.mash.infusion_mash(getparam('ambient_temp'),
			self.__reference_temp(), totvol,
			self.__grain_absorption())

		theor_yield = self.total_yield(WBC.MASH,
		    theoretical=True).valueas(Mass.KG)
		# FIXXXME: actually volume, so off-by-very-little
		watermass = self.results['mash']['mashstep_water']
		fw = 100 * (theor_yield / (theor_yield + watermass))
		self.results['mash_first_wort_max'] \
		    = Strength(fw, Strength.PLATO)

		mf = self._fermentables_atstage(WBC.MASH)
		rv = _Volume(self.results['mash']['mashstep_water']
		      - (self._fermentables_mass(mf).valueas(Mass.KG)
		         * self.__grain_absorption()
		        + getparam('mlt_loss')))
		if rv <= 0:
			raise PilotError('mashin ratio ridiculously low')
		self.results['mash_first_runnings_max'] = rv

	def _dovolumes(self):
		res = {}
		res['mash'] = self.__volume_at_stage(self.MASHWATER)
		res['fermentor'] = self.__volume_at_stage(self.FERMENTER)
		res['package'] = self.__volume_at_stage(self.FINAL)

		def v_at_temp(name, stage):
			v = self.__volume_at_stage(stage)
			res[name] = v
			vt = Brewutils.water_vol_at_temp(v,
			    self.__reference_temp(), getparam(name + '_temp'))
			res[name + '_attemp'] = vt
		v_at_temp('preboil', self.PREBOIL)
		v_at_temp('postboil', self.POSTBOIL)

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
		strens['preboil'] = Brewutils.solve_strength(
		    self.total_yield(WBC.STEEP), vols['preboil'])
		strens['final'] = Brewutils.solve_strength(
		    self.total_yield(WBC.FERMENT), vols['fermentor'])
		strens['postboil'] = Brewutils.solve_strength(
		    self.total_yield(WBC.BOIL), vols['postboil'])
		self.results['strengths'] = strens

	@staticmethod
	def _hopmap(hop, mass, time, ibu):
		return {
		    'hop' : hop,
		    'mass' : mass,
		    'time' : time,
		    'ibu' : ibu,
		    'timer' : '', # filled in later
		}
	@staticmethod
	def _hopunmap(h):
		return (h['hop'], h['mass'], h['time'], h['ibu'])

	def _dohops(self):
		allhop = []

		# ok, um, so the Tinseth formula uses postboil volume ...
		v_post = self.__volume_at_stage(self.POSTBOIL)

		# ... and average strength during the boil.  *whee*
		v_pre = self.__volume_at_stage(self.PREBOIL)
		y = self.total_yield(WBC.BOIL)
		sg = _Strength((Brewutils.solve_strength(y, v_pre)
		    + Brewutils.solve_strength(y, v_post)) / 2)

		# calculate IBU produced by "bymass" hops and add to printables
		for h in self.hops_bymass:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute hop "
				    + "mass does not have an inherent volume")
			mass = self.__scale(h[1])
			ibu = h[0].IBU(sg, v_post, h[2], mass)
			allhop.append(Recipe._hopmap(h[0], mass, h[2], ibu))

		for h in self.hops_bymassvolume:
			mass = _Mass(self.__scale(h[1]) * self.__final_volume())
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

		self.results['ibus'] = totibus

		# Sort the hop additions of the recipe.
		#
		# pass 1: sort boil -> steep -> dryhop
		srtmap = {
			Hop.Dryhop	: 0,
			Hop.Steep	: 1,
			Hop.Boil	: 2,
		}
		allhop = sorted(allhop, cmp=lambda x,y:
		    srtmap[x['time'].__class__] - srtmap[y['time'].__class__],
		    reverse=True)

		# pass 2: sort within classes
		allhop = sorted(allhop, key=lambda x: x['time'], reverse=True)

		# calculate amount of wort that hops will drink
		hd = {x: 0 for x in self.hopsdrunk}
		packagedryhopvol = 0
		for h in allhop:
			(hop, mass, time, ibu) = Recipe._hopunmap(h)
			if isinstance(time, Hop.Dryhop):
				if time.indays is not time.Package:
					hd['fermenter'] += hop.absorption(mass)
				else:
					hd['package'] += hop.absorption(mass)
					packagedryhopvol += hop.volume(mass)
			else:
				hd['kettle'] += hop.absorption(mass)
		self.hopsdrunk = {x: _Volume(hd[x]/1000.0) for x in hd}
		self.hopsdrunk['volume'] = _Volume(packagedryhopvol)

		# calculate "timer" field values
		prevtype = None
		timer = 0
		for h in reversed(allhop):
			(hop, _, time, _) = Recipe._hopunmap(h)
			if prevtype is None or not isinstance(time, prevtype):
				timer = 0
				prevval = None
				prevtype = time.__class__

			if isinstance(time, Hop.Dryhop):
				h['timer'] = str(time)

			if isinstance(time, Hop.Steep):
				if prevval is not None \
				    and prevval[0] == time.temp:
					if prevval[1] == time.time:
						h['timer'] = '=='
					else:
						v = time.time - prevval[1]
						h['timer'] = str(v) + ' min'
				else:
					h['timer'] = str(time.time) + ' min'
				prevval = (time.temp, time.time)

			if isinstance(time, Hop.Boil):
				cmpval = time.time
				thisval = '=='

				if time.spec is Hop.Boil.FWH:
					cmpval = self.boiltime

				if cmpval != timer:
					thisval = str(cmpval - timer) + ' min'
					timer = cmpval
				h['timer'] = thisval

		if timer != self.boiltime:
			self.results['startboil_timer'] = self.boiltime - timer
		else:
			self.results['startboil_timer'] = None

		self.results['hops'] = allhop

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
		Sysparams.checkset()

		if self._calculatestatus:
			raise PilotError("you can calculate() a recipe once")
		self._calculatestatus += 1

		if self.__final_volume() is None:
			raise PilotError("final volume is not set")

		s = float(self.__scale(_Mass(1)))
		if abs(s - 1) > .0001:
			notice('Scaling recipe ingredients by a factor of '
			    + '{:.4f}'.format(s) + '\n')

		# ok, so the problem is that the amount of hops affects the
		# kettle crud, meaning we have non-constants loss between
		# postboil and the fermenter.  that loss, in turn, affects
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
			prevol = self.__volume_at_stage(self.MASHWATER)
			self._dostrengths()
			self._domash()
			self._dohops()
			if prevol+.01 >= self.__volume_at_stage(self.MASHWATER):
				break
		else:
			raise Exception('recipe failed to converge ... panic?')

		# do the volumes once more to finalize them with the
		# final hop thirst
		self._dovolumes()

		self._dofermentablestats()
		self._doferment()

		# calculate suggested pitch rates, using 0.75mil/ml/degP for
		# ales and 1.5mil for lagers
		tmp = self.__volume_at_stage(self.FERMENTER) * 1000 \
		    * self.results['strengths']['final'].valueas(Strength.PLATO)
		bil = 1000*1000*1000
		self.results['pitch'] = {}
		self.results['pitch']['ale']   = tmp * 0.75*1000*1000 / bil
		self.results['pitch']['lager'] = tmp * 1.50*1000*1000 / bil

		# calculate color, via MCU & Morey equation
		t = sum(f['amount'].valueas(Mass.LB) \
		    * f['fermentable'].color.valueas(Color.SRM) \
		        for f in self.results['fermentables'])
		v = self.results['volumes']['postboil'].valueas(Volume.GALLON)
		mcu = t / v
		self.results['color'] = \
		    Color(1.4922 * pow(mcu, 0.6859), Color.SRM)

		# calculate brewhouse estimated afficiency ... NO, efficiency
		maxyield = self.total_yield(WBC.FERMENT, theoretical=True)
		maxstren = Brewutils.solve_strength(maxyield,
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
		print 'wbcdata|1'
		print '# recipe|name|yeast|boiltime|volume'
		print 'recipe|' + self.name + '|' + self.yeast + '|' \
		    + str(self.boiltime) \
		    + '|' + str(float(self.__final_volume()))

		self.mash.printcsv()

		print '# fermentable|name|mass|when'
		for g in self.results['fermentables']:
			print 'fermentable|{:}|{:}|{:}'\
			    .format(g['fermentable'].name,
			      float(g['amount']), g['when'])

		print '# hop|name|type|aa%|mass|timeclass|timespec'
		for h in self.results['hops']:
			hop = h['hop']
			time = h['time']
			timeclass = str(time.__class__).split('.')[-1].lower()
			timespec = unicode(time).replace(unichr(0x00b0), "deg")
			timespec = str(timespec)

			print u'hop|{:}|{:}|{:}|{:}|{:}|{:}'\
			    .format(hop.name, hop.typestr,
			      hop.aapers, float(h['mass']), timeclass, timespec)

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

		print 'Water temp:\t', \
		    self.__striketemp(mashtemp, strike_vol)

		print '1st run vol:\t', firstrun_vol
		print '1st run SG:\t', firstrun_sg
		print '2nd run vol:\t', secondrun_vol
		print '2nd run SG:\t', secondrun_sg
		print
		print 'Big beer SG:\t', bigbeer_sg
		print 'Big beer vol:\t', bigbeer_vol
		print 'Small beer SG:\t', smallbeer_sg
		print 'Small beer vol:\t', smallbeer_vol

		print
		print '\tBlend first:'
		print '1) Gather first runnings into BK1'
		print '2) Run', vb, 'from BK1 to BK2'
		print '3) Fill BK1 up to total volume using second runnings'
		print '4) Fill BK2 with remainder of the runnings'

		print
		print '\tRun first:'
		print '1) Gather first runnings into BK1'
		print '2) Run', vr, 'of second runnings into BK1'
		print '3) Fill BK2 with remainder of the runnings'
		print '4) Run', Volume((firstrun_vol+vr)-bigbeer_vol), \
		    'from BK1 to BK2'

import Sysparams

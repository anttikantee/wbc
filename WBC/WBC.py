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

import Brewutils

def checkconfig():
	return True

class Recipe:
	def __init__(self, name, yeast, volume, boiltime = 60):
		# volume may be None if the recipe contains only relative units
		# XXXTODO: not all specifications take relative units currently
		if volume is not None:
			checktype(volume, Volume)

		self.name = name
		self.yeast = yeast
		self.volume_inherent = volume
		self.volume_final = None

		self.hops_bymass = []
		self.hops_byIBU = []
		self.hops_recipeIBU = None
		self.hops_recipeBUGU = None

		self.fermentables_bymass = []
		self.fermentables_bypercent = []
		self.fermentables_therest = []

		# final strength or mass of one fermentable
		self.anchor = None

		self.stolen_wort = (_Volume(0), _Strength(0), _Mass(0))

		self.boiltime = boiltime

		self.hopsdrunk = {'kettle':_Volume(0), 'fermenter':_Volume(0),
		    'keg':_Volume(0)}

		self._calculated = False

		self.results = {}

		self.mash = Mash()

		Sysparams.processdefaults()

	def paramfile(self, filename):
		Sysparams.processfile(filename)

	def __havefermentable(self, fermentable, when):
		v = filter(lambda x: x[0] == fermentable and x[3] == when,
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

	# fermentable additions
	MASH=		object()
	STEEP=		object()
	BOIL=		object()
	FERMENT=	object()
	fermstages=	[ MASH, STEEP, BOIL, FERMENT ]
	fermstage2txt=	{
		MASH : 'mash',
		STEEP: 'steep',
		BOIL : 'boil',
		FERMENT : 'ferment'
	}

	def __final_volume(self):
		if self.volume_final is not None:
			return self.volume_final
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

	def _prtsep(self, char='='):
		print char * 78

	def __extract(self, vol, strength):
		m = Mass(vol * strength.valueas(Strength.SG), Mass.KG)
		return Mass(m.valueas(Mass.G)
		    * strength.valueas(Strength.PLATO)/100.0, Mass.G)

	def __scale(self, what):
		if self.volume_inherent is None or self.volume_final is None:
			return what

		assert(isinstance(what, Mass))

		scale = self.volume_final / self.volume_inherent
		return _Mass(scale * what)

	def set_final_volume(self, volume_final):
		checktype(volume_final, Volume)
		self.volume_final = volume_final

	def hop_bymass(self, hop, mass, time):
		checktypes([(hop, Hop), (mass, Mass)])
		self.hops_bymass.append([hop, mass, time])

	# mass per final volume
	def hop_bymassvolratio(self, hop, mass, vol, time):
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass(mass * self.__final_volume() / vol)
		self.hops_bymass.append([hop, hopmass, time])

	# alpha acid mass per final volume
	def hop_byAAvolratio(self, hop, mass, vol, time):
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass((mass / (hop.aapers/100.0))
		    * (self.__final_volume() / vol))
		self.hops_bymass.append([hop, hopmass, time])

	def hop_byIBU(self, hop, IBU, time):
		checktype(hop, Hop)
		self.hops_byIBU.append([hop, IBU, time])

	def hop_recipeIBU(self, hop, IBU, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			self.hops_recipeIBU = [hop, IBU, time]
		else:
			raise PilotError('total IBU/BUGU specified >once')

	def hop_recipeBUGU(self, hop, bugu, time):
		checktype(hop, Hop)
		if self.hops_recipeIBU is None and self.hops_recipeBUGU is None:
			self.hops_recipeBUGU = [hop, bugu, time]
		else:
			raise PilotError('total IBU/BUGU specified >once')

	def __doanchor(self, what, value):
		if not self.anchor is None:
			raise PilotError('anchor already set')
		self.anchor = ( what, value )

	def anchor_bystrength(self, strength):
		checktype(strength, Strength)

		self.__doanchor('strength', strength)

	def anchor_bymass(self, fermentable, mass):
		checktype(mass, Mass)

		# test
		Fermentables.get(fermentable)

		self.__doanchor('mass', (fermentable, mass))

	def __validate_ferm(self, name, fermentable, when):
		if when not in self.fermstages:
			raise PilotError('invalid fermentation stage')

		if self.__havefermentable(name, when):
			raise PilotError('fermentables may be specified max '
			    + 'once per stage')

		if fermentable.needmash and when != self.MASH:
			raise PilotError('fermentable "' + name + '" needs '
			    + 'a mash')

		# we would throw an error here, but then again, if someone
		# want to put sugars into their mash, it's not our business
		# to tell them not to.
		#
		#if not fermentable.conversion and when == self.MASH:
		#	raise PilotError('fermentable "' + name + '" does not '
		#	    + 'need a mash')

	def fermentable_bymass(self, name, mass, when=MASH):
		checktype(mass, Mass)

		if len(self.fermentables_bypercent) > 0:
			raise PilotError('all grains in recipe must be ' \
			    'specified by percent or mass')

		(name, fermentable) = Fermentables.get(name)
		self.__validate_ferm(name, fermentable, when)

		self.fermentables_bymass.append((name, fermentable, mass, when))

	# percent of fermentable's mass, not extract's mass
	def fermentable_bypercent(self, name, percent, when=MASH):
		if percent is not self.THEREST and percent <= 0:
			raise PilotError('grain percentage must be positive '\
			  '(it is a fun thing!)')

		if len(self.fermentables_bymass) > 0:
			raise PilotError('all grains in recipe must be ' \
			    'specified by percent or mass')

		(name, fermentable) = Fermentables.get(name)
		self.__validate_ferm(name, fermentable, when)

		if percent is self.THEREST:
			self.fermentables_therest.append((name,
			    fermentable, when))
		else:
			self.fermentables_bypercent.append((name, fermentable,
			    percent, when))
			if sum(x[2] for x in self.fermentables_bypercent) > 100:
				raise PilotError('captain, I cannot change the'\
				    ' laws of math; 100% fermentables max!')

	# indicate that we want to "borrow" some wort at the preboil stage
	# for e.g. building starters.
	def steal_preboil_wort(self, vol, strength):
		checktypes([(vol, Volume), (strength, Strength)])

		extract = self.__extract(vol, strength)
		self.stolen_wort = (vol, strength, extract)

	def fermentable_percentage(self, what, theoretical=False):
		if what[1].extract_legacy is True:
			warn('fermentable "' + what[1].name + '" uses '
			    + 'legacy extract specification\n')
			what[1].extract_legacy = False
		percent = what[1].extract
		if what[1].conversion and not theoretical:
			percent *= getparam('mash_efficiency')/100.0
		return percent

	def fermentable_yield(self, what, theoretical=False):
		return _Mass(what[2]
		    * self.fermentable_percentage(what, theoretical)/100.0)

	def _fermentables_atstage(self, when):
		assert('fermentables' in self.results)
		return filter(lambda x: x[3] == when,
		    self.results['fermentables'])

	def _fermentables_allstage(self):
		assert('fermentables' in self.results)
		return self.results['fermentables']

	def _fermentables_mass(self, fermlist):
		return _Mass(sum(x[2] for x in fermlist))

	def _fermentables_allmass(self):
		assert('fermentables' in self.results)
		return _Mass(sum(x[2] for x in self.results['fermentables']))

	def total_yield(self, stage, theoretical=False):
		assert('fermentables' in self.results)

		def yield_at_stage(stage):
			return sum([self.fermentable_yield(x, theoretical) \
			    for x in self._fermentables_atstage(stage)])
		m = yield_at_stage(self.MASH)
		if stage == self.STEEP or stage == self.BOIL \
		    or stage == self.FERMENT:
			m += yield_at_stage(self.STEEP)
		if stage == self.BOIL or stage == self.FERMENT:
			m += yield_at_stage(self.BOIL)
		if stage == self.FERMENT:
			m += yield_at_stage(self.FERMENT)
		return _Mass(m - self.stolen_wort[2])

	def _sanity_check(self):
		pbs = self.results['preboil_strength'].valueas(Strength.PLATO)
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

		if len(self.fermentables_bymass) > 0:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute "
				    + "fermentable mass "
				    + "does not have an inherent volume")

			# if we're scaling the recipe, we just need to
			# scale the grains
			self.results['fermentables'] = \
			    [(x[0], x[1], self.__scale(x[2]), x[3]) \
			      for x in self.fermentables_bymass]
			return # all done already

		totpers = sum(x[2] for x in self.fermentables_bypercent)
		missing = 100 - float(totpers)
		if missing > 0:
			ltr = len(self.fermentables_therest)
			if ltr == 0:
				raise PilotError('fermentable percentages add '
				    + 'up to only ' + str(totpers)
				    + '%, need 100%')
			mp = missing / ltr
			for tr in self.fermentables_therest:
				i = (tr[0], tr[1], mp, tr[2])
				self.fermentables_bypercent.append(i)
		assert (sum(x[2] for x in self.fermentables_bypercent) == 100)

		if self.anchor is None:
			raise PilotError('anchor must be set for '
			    + 'by-percent fermentables')

		if self.anchor[0] == 'strength':
			# calculate extract required for strength, and derive
			# masses of fermentables from that

			extract = self.__extract(
			    self.__volume_at_stage(self.POSTBOIL),
			    self.anchor[1]) + self.stolen_wort[2]

			# now, solve for the total mass:
			# extract = yield1 * m1 + yield2 * m2 + ...
			# where yieldn = extract% * mash_efficiency / 100.0
			# and   mn = pn * totmass
			# and then solve: totmass = extract / (sum(yieldn*pn))
			thesum = sum([self.fermentable_percentage(x)/100.0
			    * x[2]/100.0
			    for x in self.fermentables_bypercent])
			totmass = _Mass(extract / thesum)

			# Note: solution isn't 100% correct when we consider
			# adding sugars into the fermentor: the same amount
			# of sugar as into the boil will increase the strength
			# more in the fermentor due to a smaller volume.
			# But the math behind the correct calculation seems to
			# get hairy fast, so we'll let it slip at least for now.

		elif self.anchor[0] == 'mass':
			# mass of one fermentable is set, others are
			# simply scaled to that value

			a = self.anchor[1]
			f = filter(lambda x: x[0] == a[0],
			    self.fermentables_bypercent)
			if len(f) != 1:
				raise PilotError("could not find anchor "
				    "fermentable: " + a[0])
			totmass = a[1] / (f[0][2]/100.0)

		# and finally set the masses of each individual fermentable
		ferms = []
		for x in self.fermentables_bypercent:
			# limit mass to 0.1g accuracy
			m = int(10 * (x[2]/100.0 * totmass)) / 10.0
			i = (x[0], x[1], _Mass(m), x[3])
			ferms.append(i)
		self.results['fermentables'] = ferms

	def _domash(self):
		prevol1 = self.__volume_at_stage(self.PREBOIL)
		prevol  = Brewutils.water_vol_at_temp(prevol1,
		    self.__reference_temp(), getparam('preboil_temp'))
		self.results['preboil_volume'] = prevol
		prestren = Brewutils.solve_strength(
		    self.total_yield(self.STEEP), prevol)
		self.results['preboil_strength'] = prestren

		steal = {}
		ratio = self.stolen_wort[1] / prestren
		steal['strength'] = _Strength(prestren * min(1, ratio))

		steal['volume'] = _Volume(min(1, ratio) * self.stolen_wort[0])
		steal['missing'] = _Volume(self.stolen_wort[0]-steal['volume'])
		totvol = _Volume(self.__volume_at_stage(self.MASHWATER) \
		    + steal['volume'])
		self.results['steal'] = steal

		mf = self._fermentables_atstage(self.MASH)
		self.mash.set_fermentables(mf)

		v = self.__volume_at_stage(self.POSTBOIL)

		res = []
		for f in sorted(mf, key=lambda x: x[2], reverse=True):
			ferm = f[1]
			mass = f[2]
			ratio = mass / self._fermentables_allmass()
			ext_pred = self.fermentable_yield(f)
			ext_theor = self.fermentable_yield(f,
			    theoretical=True)

			res.append((f[0], f[2], 100*ratio, ext_theor, ext_pred))

		self.results['mashfermentables'] = res
		self.results['mash'] \
		    = self.mash.infusion_mash(getparam('ambient_temp'),
			self.__reference_temp(), totvol)

		theor_yield = self.total_yield(self.MASH,
		    theoretical=True).valueas(Mass.KG)
		# FIXXXME: actually volume, so off-by-very-little
		watermass = self.results['mash']['mashstep_water']
		fw = 100 * (theor_yield / (theor_yield + watermass))
		self.results['mash_first_wort_max'] \
		    = Strength(fw, Strength.PLATO)

		mf = self._fermentables_atstage(self.MASH)
		rv = _Volume(self.results['mash']['mashstep_water']
		      - (self._fermentables_mass(mf).valueas(Mass.KG)
		         * self.__grain_absorption()
		        + getparam('mlt_loss')))
		if rv <= 0:
			raise PilotError('mashin ratio ridiculously low')
		self.results['mash_first_runnings_max'] = rv

	def _printmash(self):
		fmtstr = u'{:32}{:>20}{:>12}{:>12}'
		print fmtstr.format("Fermentables",
		    "amount", "ext (100%)", "ext ("
		    + str(int(getparam('mash_efficiency'))) + "%)")
		self._prtsep()

		totextract = 0
		maxextract = 0

		for stage in [('mashfermentables', 'Mash'),
		    ('steepfermentables', 'Steep'),
		    ('boilfermentables', 'Boil'),
		    ('fermfermentables', 'Ferment')]:
			(what, name) = stage
			stagem = stagep = stagetote = stagemaxe = 0
			if len(self.results.get(what, [])) > 0:
				print name
				self._prtsep('-')
				for f in self.results[what]:
					pers = ' ({:5.1f}%)'.format(f[2])
					print fmtstr.format(f[0],
					    str(f[1]) + pers, str(f[3]),
					    str(f[4]))
					stagem += f[1]
					stagep += f[2]
					stagetote += f[3]
					stagemaxe += f[4]
				self._prtsep('-')
				pers = ' ({:5.1f}%)'.format(stagep)
				print fmtstr.format('',
				    str(_Mass(stagem)) + pers,
				    str(_Mass(stagetote)),
				    str(_Mass(stagemaxe)))
			totextract += stagetote
			maxextract += stagemaxe

		self._prtsep()

		print fmtstr.format('', \
		    str(self._fermentables_allmass()) + ' (100.0%)', \
		    str(_Mass(totextract)),\
		    str(_Mass(maxextract)))

		print
		print 'Mashing instructions (for ambient temperature', \
		    unicode(getparam('ambient_temp')) + ')'
		self._prtsep()

		totvol = 0
		mf = self._fermentables_atstage(self.MASH)
		mash_grainmass = self._fermentables_mass(mf)
		for i, x in enumerate(self.results['mash']['steps']):
			if getparam('mlt_heat') == 'direct' and i != 0:
				print u'{:7}'. format(unicode(x[0])) \
				    + ': apply heat'
				continue
			print u'{:7}'.format(unicode(x[0])) + ': add', x[2], \
			    'of water at', unicode(x[3]),

			# print the water/grist ratio at the step.
			#
			# XXX: I'm unsure if we should print the user
			# input for step 1, but then again, if someone
			# wants to give mashin ratios as 3.4gal/17lb,
			# maybe it's their problem, and we just support
			# printing in metric or cryptic with the denominator
			# normalized to 1
			totvol = _Volume(totvol + x[1])
			if getparam('units_output') == 'metric':
				ratio = totvol \
				    / mash_grainmass.valueas(Mass.KG)
				unit = 'l/kg'
			else:
				ratio = totvol.valueas(Volume.QUART) \
				    / mash_grainmass.valueas(Mass.LB)
				unit = 'qt/lb'
			mash_volume = _Volume(totvol
			    + mash_grainmass.valueas(Mass.KG)
			      * Constants.grain_specificvolume)
			print '({:.2f} {:}, mash vol {:})'.format(ratio,
			    unit, mash_volume)

		print u'{:23}{:}'.format('Mashstep water volume:', \
		    unicode(self.results['mash']['mashstep_water']) + ' @ ' \
		    + unicode(self.__reference_temp())),
		print '(potential first runnings: ~{:})' \
		    .format(self.results['mash_first_runnings_max'])

		print u'{:23}{:}'.format('Sparge water volume:', \
		    unicode(self.results['mash']['sparge_water']) + ' @ '
		    + unicode(getparam('sparge_temp')))

		fw = self.results['mash_first_wort_max']
		fwstrs = []
		for x in [.85, .90, .95, 1.0]:
			fwstrs.append(unicode(_Strength(fw * x)) \
			    + ' (' + str(int(100 * x)) + '%)')
		print u'{:23}{:}'. format('First wort (conv. %):', \
		    ', '.join(fwstrs))

		if self.stolen_wort[0] > 0:
			print
			steal = self.results['steal']
			print 'Steal', steal['volume'], 'of', \
			    '*well-mixed* preboil wort',
			if steal['missing'] > 0:
				print 'and blend with',steal['missing'],'water'
			else:
				print

			print '==>', self.stolen_wort[0], 'of', \
			    unicode(steal['strength']), 'stolen wort',
			if steal['strength'] < self.stolen_wort[1]:
				print '(NOTE: strength below desired!)',
			print

		self._prtsep()
		print

	def _dosteep(self):
		res = []
		for f in sorted(self._fermentables_atstage(self.STEEP),
		    key=lambda x: x[2], reverse=True):
			ferm = f[1]
			mass = f[2]
			ratio = mass / self._fermentables_allmass()
			ext_pred = self.fermentable_yield(f)
			ext_theo = self.fermentable_yield(f, theoretical=True)

			res.append((f[0], f[2], 100*ratio, ext_theo, ext_pred))

		self.results['steepfermentables'] = res

	def _doboil(self):
		res = []

		# hop calculations might need final strength
		v = self.__volume_at_stage(self.FERMENTER)
		self.results['final_strength'] \
		    = Brewutils.solve_strength(self.total_yield(self.FERMENT),v)
		v = self.__volume_at_stage(self.POSTBOIL)
		self.results['postboil_strength'] \
		    = Brewutils.solve_strength(self.total_yield(self.BOIL),v)

		for f in sorted(self._fermentables_atstage(self.BOIL),
		    key=lambda x: x[2], reverse=True):
			ferm = f[1]
			mass = f[2]
			ratio = mass / self._fermentables_allmass()
			ext_pred = self.fermentable_yield(f)
			ext_theo = self.fermentable_yield(f, theoretical=True)

			res.append((f[0], f[2], 100*ratio, ext_theo, ext_pred))

		self.results['boilfermentables'] = res
		self._dohops()

	def _unhopmap(self, h):
		return (h['hop'], h['mass'], h['time'], h['ibu'])

	def _dohops(self):
		allhop = []

		# ok, um, so the Tinseth formula uses postboil volume ...
		v_post = self.__volume_at_stage(self.POSTBOIL)

		# ... and average strength during the boil.  *whee*
		v_pre = self.__volume_at_stage(self.PREBOIL)
		y = self.total_yield(self.BOIL)
		sg = _Strength((Brewutils.solve_strength(y, v_pre)
		    + Brewutils.solve_strength(y, v_post)) / 2)

		def hopmap(hop, mass, time, ibu):
			return {
			    'hop' : hop,
			    'mass' : mass,
			    'time' : time,
			    'ibu' : ibu,
			    'timer' : '', # only for boil
			}

		# calculate IBU produced by "bymass" hops and add to printables
		for h in self.hops_bymass:
			if self.volume_inherent is None:
				raise PilotError("recipe with absolute hop "
				    + "mass does not have an inherent volume")
			time = h[2].gettime(self.boiltime)
			mass = self.__scale(h[1])
			ibu = h[0].IBU(sg, v_post, time, mass)
			allhop.append(hopmap(h[0], mass, h[2], ibu))

		# calculate mass of "byIBU" hops and add to printables
		for h in self.hops_byIBU:
			time = h[2].gettime(self.boiltime)
			mass = h[0].mass(sg, v_post, time, h[1])
			allhop.append(hopmap(h[0], mass, h[2], h[1]))

		totibus = sum([x['ibu'] for x in allhop])
		if self.hops_recipeIBU is not None:
			h = self.hops_recipeIBU
			time = h[2].gettime(self.boiltime)
			missibus = self.hops_recipeIBU[1] - totibus
			if missibus <= 0:
				raise PilotError('total IBUs are greater than '\
				    + 'desired total')
			mass = h[0].mass(sg, v_post, time,
			    missibus)
			allhop.append(hopmap(h[0], mass, h[2], missibus))
			totibus += missibus

		if self.hops_recipeBUGU is not None:
			h = self.hops_recipeBUGU
			time = h[2].gettime(self.boiltime)
			bugu = self.hops_recipeBUGU[1]
			stren = self.results['final_strength']
			ibus = stren.valueas(stren.SG_PTS) * bugu
			missibus = ibus - totibus
			mass = h[0].mass(sg, v_post, time,
			    missibus)
			allhop.append(hopmap(h[0], mass, h[2], missibus))
			totibus += missibus

		# Sort the hop additions of the recipe.
		#
		# pass 1: sort within classes
		allhop = sorted(allhop, key=lambda x: x['time'], reverse=True)

		# pass 2: sort boil -> steep -> dryhop
		srtmap = {
			Hop.Dryhop	: 0,
			Hop.Steep	: 1,
			Hop.Boil	: 2,
		}
		self.results['hops'] = sorted(allhop, cmp=lambda x,y:
		    srtmap[x['time'].__class__] - srtmap[y['time'].__class__],
		    reverse=True)
		self.ibus = totibus

		# calculate amount of wort that hops will drink
		hd = {x: 0 for x in self.hopsdrunk}
		kegdryhopvol = 0
		timer = self.boiltime
		prevval = None
		for h in allhop:
			(hop, mass, time, ibu) = self._unhopmap(h)
			if isinstance(time, Hop.Dryhop):
				if time.indays is not time.Keg:
					hd['fermenter'] += hop.absorption(mass)
				else:
					hd['keg'] += hop.absorption(mass)
					kegdryhopvol += hop.volume(mass)
			else:
				hd['kettle'] += hop.absorption(mass)

			if isinstance(time, Hop.Boil):
				cmpval = time.time
				thistime = '--'
				if cmpval is Hop.Boil.FWH:
					cmpval = self.boiltime
					if prevval != time.time:
						thistime = 'FWH'
				elif cmpval == self.boiltime:
					if prevval != time.time:
						thistime = '@ boil'
				elif cmpval != timer:
					tval = int(timer - cmpval)
					thistime = str(tval) + ' min'
				timer = cmpval
				prevval = time.time
				h['timer'] = thistime

		self.hopsdrunk = {x: _Volume(hd[x]/1000.0) for x in hd}
		self.kegdryhopvol = _Volume(kegdryhopvol)

	def _printboil(self):
		# XXX: IBU sum might not be sum of displayed hop additions
		# due to rounding.  cosmetic, but annoying.
		namelen = 26
		onefmt = u'{:' + str(namelen) + '}{:7}{:>15}{:>9}{:>10}{:>9}'
		print onefmt.format("Hops", "AA%", "time", "timer",
		    "amount", "IBUs")
		self._prtsep()
		totmass = 0

		prevstage = None
		for h in self.results['hops']:
			(hop, mass, time, ibu) = self._unhopmap(h)
			typ = ' (' + hop.typestr + ')'
			nam = hop.name
			if prevstage is not None and \
			    prevstage is not time.__class__:
				self._prtsep('-')
			maxlen = (namelen-1) - len(typ)
			if len(nam) > maxlen:
				nam = nam[0:maxlen-4] + '...'

			prevstage = time.__class__
			totmass = mass + totmass

			# printing IBUs with two decimal points, given all
			# other inaccuracy involved, is rather silly.
			# but what would we be if not silly?
			ibustr = '{:.2f}'.format(ibu)
			print onefmt.format(nam + typ, str(hop.aapers) + '%', \
			    time, h['timer'], str(mass), ibustr)
		self._prtsep()
		ibustr = '{:.2f}'.format(self.ibus)
		print onefmt.format('', '', '', '', str(_Mass(totmass)), ibustr)
		print

	def _keystats(self, miniprint):
		self._prtsep()
		onefmt = u'{:19}{:}'
		twofmt = u'{:19}{:19}{:21}{:19}'

		postvol1 = self.__volume_at_stage(self.POSTBOIL)
		postvol  = Brewutils.water_vol_at_temp(postvol1,
		    self.__reference_temp(), getparam('postboil_temp'))
		total_water = _Volume(self.results['mash']['total_water']
		    + self.results['steal']['missing'])

		# calculate color, via MCU & Morey equation
		t = sum(f[2].valueas(Mass.LB) * f[1].color.valueas(Color.SRM) \
		     for f in self.results['fermentables'])
		mcu = t / postvol1.valueas(Volume.GALLON)
		color = Color(1.4922 * pow(mcu, 0.6859), Color.SRM)
		srm = color.valueas(Color.SRM)
		ebc = color.valueas(Color.EBC)

		print onefmt.format('Name:', self.name)
		print twofmt.format('Final volume:',
		    str(self.__final_volume()),
		    'Boil:', str(self.boiltime) + ' min')
		bugu = self.ibus / self.results['final_strength']
		print twofmt.format('IBU (Tinseth):', \
		    '{:.2f}'.format(self.ibus), \
		    'BUGU:', '{:.2f}'.format(bugu))
		if srm >= 10:
			prec = '0'
		else:
			prec = '1'

		ebcprec = '{:.' + prec + 'f}'
		srmprec = '{:.' + prec + 'f}'
		print twofmt.format('Color (Morey):', \
		    ebcprec.format(ebc) \
		    + ' EBC, ' + srmprec.format(srm) + ' SRM', \
		    'Water (' + unicode(self.__reference_temp()) + '):', \
		    unicode(total_water))

		if not miniprint:
			bil = 1000*1000*1000
			unit = ' billion'
			print twofmt.format('Pitch rate, ale:',
			    str(int(self.results['pitch']['ale'] / bil)) + unit,
			    'Pitch rate, lager:',
			    str(int(self.results['pitch']['lager'] / bil))
			    + unit)
		print
		print onefmt.format('Yeast:', self.yeast)
		print onefmt.format('Water notes:', '')
		print

		print twofmt.format('Preboil  volume  :', \
		    str(self.results['preboil_volume']) \
		    + ' (' + unicode(getparam('preboil_temp')) + ')', \
		    'Measured:', '')
		print twofmt.format('Preboil  strength:', \
		    unicode(self.results['preboil_strength']), \
		    'Measured:', '')
		print twofmt.format('Postboil volume  :', str(postvol) \
		    + ' (' + unicode(getparam('postboil_temp')) + ')', \
		    'Measured:', '')
		print twofmt.format('Postboil strength:', \
		    unicode(self.results['postboil_strength']), \
		    'Measured:', '')

		# various expected losses and brewhouse efficiency
		print
		d1 = _Volume(self.__volume_at_stage(self.POSTBOIL)
		    - self.__volume_at_stage(self.FERMENTER))
		d2 = _Volume(self.__volume_at_stage(self.FERMENTER)
		    - self.__volume_at_stage(self.FINAL))

		print twofmt.format('Kettle loss (est):', str(d1),
		    'Fermenter loss (est):', str(d2))

		maxyield = self.total_yield(self.FERMENT, theoretical=True)
		maxstren = Brewutils.solve_strength(maxyield,
		    self.__final_volume())
		beff = self.results['final_strength'] / maxstren
		print twofmt.format('Mash eff (conf) :', \
		    str(getparam('mash_efficiency')) + '%',
		    'Brewhouse eff (est):', '{:.1f}%'.format(100 * beff))

		if self.hopsdrunk['keg'] > 0:
			print
			print 'NOTE: keg hops absorb: ' \
			    + str(self.hopsdrunk['keg']) \
			    + ' => effective yield: ' \
			    + str(_Volume(self.__final_volume()
				  - self.hopsdrunk['keg']))

			# warn about larger packaging volume iff keg dryhops
			# volume exceeds 1dl
			if self.kegdryhopvol > 0.1:
				print 'NOTE: keg hop volume: ~' \
				    + str(self.kegdryhopvol) \
				    + ' => packaged volume: ' \
				    + str(_Volume(self.__final_volume()
				          + self.kegdryhopvol))

		self._prtsep()
		print

	def _doferment(self):
		res = []
		v = self.__volume_at_stage(self.POSTBOIL)
		for f in sorted(self._fermentables_atstage(self.FERMENT),
		    key=lambda x: x[2], reverse=True):
			ferm = f[1]
			mass = f[2]
			ratio = mass / self._fermentables_allmass()
			ext_pred = self.fermentable_yield(f)
			ext_theo = self.fermentable_yield(f, theoretical=True)

			res.append((f[0], f[2], 100*ratio, ext_theo, ext_pred))

		self.results['fermfermentables'] = res

		self._doattenuate()

	def _doattenuate(self, attenuation = (60, 86, 5)):
		res = []
		fin = self.results['final_strength']
		for x in range(*attenuation):
			t = fin.attenuate_bypercent(x)
			res.append((x, t['ae'], t['abv']))
		self.results['attenuation'] = res

	def _printattenuate(self):
		print 'Speculative apparent attenuation and resulting ABV'
		self._prtsep()
		onefmt = u'{:^8}{:^8}{:10}'
		title = ''
		for x in range(3):
			title += onefmt.format('Str.', 'Att.', 'ABV')
		print title

		reslst = []
		for x in self.results['attenuation']:
			reslst.append((unicode(x[1]), str(x[0]) + '%', \
			    '{:.1f}%'.format(x[2])))

		for i in range(0, len(reslst)/3):
			line = onefmt.format(*reslst[i])
			line += onefmt.format(*reslst[i + len(reslst)/3])
			line += onefmt.format(*reslst[i + 2*len(reslst)/3])
			print line
		self._prtsep()
		print

	def calculate(self):
		Sysparams.checkset()

		if self._calculated:
			raise PilotError("you can calculate() a recipe once")

		if self.__final_volume() is None:
			raise PilotError("final volume is not set")

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
			self._dofermentables()
			prevol = self.__volume_at_stage(self.MASHWATER)
			self._domash()

			self._dosteep()
			self._doboil()
			if prevol+.01 >= self.__volume_at_stage(self.MASHWATER):
				break
		else:
			raise Exception('recipe failed to converge ... panic?')

		self._doferment()

		# calculate suggested pitch rates, using 0.75mil/ml/degP for
		# ales and 1.5mil for lagers
		tmp = self.__volume_at_stage(self.FERMENTER) * 1000 \
		    * self.results['final_strength'].valueas(Strength.PLATO)
		self.results['pitch'] = {}
		self.results['pitch']['ale']   = tmp * 0.75*1000*1000
		self.results['pitch']['lager'] = tmp * 1.50*1000*1000

		self._sanity_check()

		self._calculated = True

	def _assertcalculate(self):
		if not self._calculated:
			raise PilotError('must calculate recipe first')

	def printit(self, miniprint):
		self._assertcalculate()
		self._keystats(miniprint)
		self._printmash()
		self._printboil()
		if not miniprint:
			self._printattenuate()

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
			    .format(g[1].name, float(g[2]),
			      self.fermstage2txt[g[3]])

		print '# hop|name|type|aa%|mass|timeclass|timespec'
		for h in self.results['hops']:
			timeclass = str(h[2].__class__).split('.')[-1].lower()
			timespec = unicode(h[2]).replace(unichr(0x00b0), "deg")
			timespec = str(timespec)

			# XXX: silly
			if timespec == 'dryhop in keg':
				timespec = 'keg'

			print u'hop|{:}|{:}|{:}|{:}|{:}|{:}'\
			    .format(h[0].name, h[0].typestr,
			      h[0].aapers, float(h[1]), timeclass, timespec)

	def do(self):
		self.calculate()
		self.printit()

class Hop:
	Pellet	= object()
	Leaf	= object()

	class Boil:
		FWH	= object()
		def __init__(self, mins):
			if mins < 0 and mins is not self.FWH:
				raise PilotError('invalid boiltime format')
			self.time = mins

		def __str__(self):
			if self.time is self.FWH:
				return 'FWH'
			return str(int(self.time)) + ' min'

		def __cmp__(self, other):
			if isinstance(other, Hop.Boil):
				if self.time is self.FWH:
					rv = 1
				if other.time is self.FWH:
					rv = -1

				if   self.time < other.time: rv = -1
				elif self.time > other.time: rv =  1
				else:                        rv =  0
			else:
				rv = 0
			return rv

		def gettime(self, boiltime):
			if self.time is self.FWH:
				rv = boiltime + 20
			else:
				rv = self.time
				if rv > boiltime:
					raise PilotError('hop boiltime ('
					    + str(rv) + ') > wort boiltime')
			return int(rv)

	class Steep:
		def __init__(self, temp, mins):
			checktype(temp, Temperature)

			self.temp = temp
			self.mins = mins

		def __str__(self):
			return str(self.mins) + 'min @ ' + unicode(self.temp)

		def __cmp__(self, other):
			if isinstance(other, Hop.Steep):
				return self.temp - other.temp
			else:
				return 0

		def gettime(self, boiltime):
			return 0

	class Dryhop:
		Keg =	object()

		def __init__(self, indays, outdays):
			if indays == self.Keg or outdays == self.Keg:
				# I guess someone *could* put hops into
				# the fermenter for some days and transfer
				# them into the keg.  We're not going to
				# support such activities.
				if indays is not outdays:
					raise PilotError('when dryhopping in '\
					    'keg, indays and outdays must be '\
					    '"keg"')
			else:
				if indays <= outdays:
					raise PilotError('trying to take ' \
					    'dryhops out before putting ' \
					    'them in')
			self.indays = indays
			self.outdays = outdays

		def __str__(self):
			if self.indays is self.Keg:
				rv = 'in keg'
			else:
				rv = str(self.indays) \
				    + ' => ' + str(self.outdays)
			return 'dryhop ' + rv

		def __cmp__(self, other):
			if not isinstance(other, Hop.Dryhop):
				return 0

			if self.indays is self.Keg:
				return -1
			if other.indays is other.Keg:
				return 1

			if self.indays < other.indays:
				return -1
			if self.outdays < other.outdays:
				return -1
			return 1

		def gettime(self, boiltime):
			return 0

	def __init__(self, name, aapers, type = Pellet):
		aalow = 1
		aahigh = 100 # I guess some hop extracts are [close to] 100%

		self.name = name
		self.type = type
		if type is Hop.Pellet:
			self.typestr = 'p'
		elif type is Hop.Leaf:
			self.typestr = 'l'
		else:
			raise PilotError('invalid hop type: ' + type)

		if aapers < aalow or aapers > aahigh:
			raise PilotError('Alpha acid percentage must be ' \
			    + 'between ' + str(aalow) + ' and ' + str(aahigh))

		self.aapers = aapers

	#
	# Tinseth IBUs, from http://realbeer.com/hops/research.html
	#
	# XXXTODO: that formula doesn't take into account bittering from
	# whirlpool hops or dryhopping.
	#

	def __util(self, gravity, mins):
		# gravity needs to be SG, not points (because sg is great
		# for all calculations?)
		SG = gravity.valueas(gravity.SG)

		bignessfact = 1.65 * pow(0.000125, SG-1)
		boilfact = (1 - pow(math.e, -0.04 * mins)) / 4.15
		bonus = 1.0
		if self.type is self.Pellet:
			bonus = 1.1
		return bonus * bignessfact * boilfact

	def IBU(self, gravity, volume, mins, mass):
		checktypes([(gravity, Strength), (mass, Mass)])

		util = self.__util(gravity, mins)
		return util * self.aapers/100.0 * mass * 1000 / volume

	def mass(self, gravity, volume, mins, IBU):
		checktype(gravity, Strength)

		util = self.__util(gravity, mins)

		# calculate mass, limit to 0.01g granularity
		m = (IBU * volume) / (util * self.aapers/100.0 * 1000)
		return _Mass(int(100*m)/100.0)

	def absorption(self, mass):
		checktype(mass, Mass)
		if self.type is self.Pellet:
			abs_c = Constants.pellethop_absorption
		else:
			assert(self.type is self.Leaf)
			abs_c = Constants.leafhop_absorption
		return _Volume(mass * abs_c)

	def volume(self, mass):
		checktype(mass, Mass)
		if self.type is self.Pellet:
			density = Constants.pellethop_density
		else:
			assert(self.type is self.Leaf)
			density = Constants.leafhop_density
		return _Volume(mass / density)

class Mash:
	# 2.5kg water to 1kg of grain by default
	__mashin_ratio_default = 2.5

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
			    * grain_mass.valueas(Mass.KG)
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
				    + 'check mashin ratio.')

			self._setvalues(water_capa, water_temp, target_temp)

		def stepup(self, target_temp):
			_c = self._capa
			_h = self._heat

			# see how much boiling water we need to raise the
			# temp up to the new target
			boiltemp = _Temperature(100)
			nw = (target_temp \
			      * (_c('mlt') \
				  + _c('grain') + _c('water'))\
			    - (_h('mlt') + _h('grain') + _h('water')))\
			  / (boiltemp - target_temp)

			self._setvalues(nw, boiltemp, target_temp)

		def waterstats(self):
			return (_Volume(self.step_watermass),
			    _Temperature(self.step_watertemp))

	def __init__(self):
		self.mashin_ratio = None
		self.mashin_percent = None

		self.fermentables = []
		self.temperature = None

	def infusion_mash(self, ambient_temp, water_temp, watervol):
		if self.temperature is None:
			raise PilotError('trying to mash without temperature')
		mashtemps = self.temperature
		assert(len(mashtemps) >= 1)

		if len(self.fermentables) == 0:
			raise PilotError('trying to mash without fermentables')

		assert(not(self.mashin_ratio is not None
		    and self.mashin_percent is not None))
		if self.mashin_ratio is None and self.mashin_percent is None:
			self.mashin_ratio = self.__mashin_ratio_default

		fmass = _Mass(sum(x[2] for x in self.fermentables))

		res = {}
		res['steps'] = []
		res['total_water'] = watervol

		if self.mashin_ratio is not None:
			wmass = self.mashin_ratio * fmass.valueas(Mass.KG)
		else:
			wmass = (self.mashin_percent/100.0) * watervol
		step = self.__Step(fmass, ambient_temp, mashtemps[0], wmass)
		totvol = watervol

		if getparam('mlt_heat') == 'transfer':
			for i, t in enumerate(mashtemps):
				(vol, temp) = step.waterstats()
				totvol -= vol
				if totvol < 0:
					raise PilotError('cannot satisfy '
					    + 'tranfer infusion steps '
					    + ' with given parameters '
					    + '(ran out of water)')

				actualvol = Brewutils.water_vol_at_temp(vol,
				    water_temp, temp)
				res['steps'].append((t, vol, actualvol, temp))
				if i+1 < len(mashtemps):
					step.stepup(mashtemps[i+1])
		else:
			assert(getparam('mlt_heat') == 'direct')
			(vol, temp) = step.waterstats()
			totvol -= vol
			actualvol = Brewutils.water_vol_at_temp(vol,
				    water_temp, temp)
			for i, t in enumerate(mashtemps):
				res['steps'].append((t, vol, actualvol, temp))

		res['mashstep_water'] = _Volume(watervol - totvol)
		res['sparge_water'] = \
		    Brewutils.water_vol_at_temp(_Volume(totvol), \
		    water_temp, getparam('sparge_temp'))

		return res

	def printcsv(self):
		print '# mash|method|mashin ratio|mashtemp1|mashtemp2...'
		mashtemps = ''
		for t in self.temperature:
			mashtemps = mashtemps + '|infusion|' + str(float(t))
		print 'mash|' + str(self.mashin_ratio) + mashtemps

	def set_fermentables(self, fermentables):
		self.fermentables = fermentables

	def set_mash_temperature(self, mashtemps):
		if isinstance(mashtemps, Temperature):
			mashtemps = [mashtemps]
		elif mashtemps.__class__ is list:
			curtemp = 0
			if len(mashtemps) == 0:
				raise PilotError('must give at least one '
				    + 'mashing temperature')
			for x in mashtemps:
				checktype(x, Temperature)
				if x < curtemp:
					raise PilotError('mashtemps must be ' \
					    'given in ascending order')
		else:
			raise PilotError('mash temperatures must be given as ' \
			    'Temperature or list of')
		self.temperature = mashtemps

	# set ratio of strike water to grist in mash
	def set_mashin_ratio(self, mashin_vol, mashin_mass):
		if self.mashin_percent is not None:
			raise PilotError('cannot set both mashin ratio '
			    + 'and percent')

		checktype(mashin_vol, Volume)
		checktype(mashin_mass, Mass)
		self.mashin_ratio = mashin_vol / mashin_mass.valueas(Mass.KG)

	# set percentage of total water used as strike water (rest is
	# for sparging etc.)
	def set_mashin_percent(self, percent):
		if self.mashin_ratio is not None:
			raise PilotError('cannot set both mashin ratio '
			    + 'and percent')
		if percent <= 0 or percent> 100:
			raise PilotError('mashin percent must be >0 and <= 100')
		self.mashin_percent = percent

	# mostly a placeholder
	def set_method(self, m):
		if m is not Mash.INFUSION:
			raise PilotError('unsupported mash method')

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

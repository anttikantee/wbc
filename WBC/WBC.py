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

from Utils import *
from Units import *
from Units import _Mass, _Strength, _Temperature, _Volume

import Brewutils

def checkconfig():
	return True

class Recipe:
	# 2.5kg water to 1kg of grain by default
	mashin_ratio_default = 2.5

	def __init__(self, name, yeast, final_volume, mashtemps, boiltime = 60):
		checktype(final_volume, Volume)
		self.name = name
		self.yeast = yeast
		self.final_volume = final_volume
		self.mashin_ratio = Recipe.mashin_ratio_default

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

		self.fermentables_temp = _Temperature(20)

		self.hopsdrunk = {'kettle':_Volume(0), 'fermenter':_Volume(0),
		    'keg':_Volume(0)}

		self.results = {}

		if isinstance(mashtemps, Temperature):
			mashtemps = [mashtemps]
		elif mashtemps.__class__ is list:
			curtemp = 0
			for x in mashtemps:
				checktype(x, Temperature)
				if x < curtemp:
					raise PilotError('mashtemps must be ' \
					    'given in ascending order')
		else:
			raise PilotError('mashtemps must be given as ' \
			    'Temperature or list of')
		self.mashtemps = mashtemps

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
	BOIL=		object()
	FERMENT=	object()
	fermstages=	[ MASH, BOIL, FERMENT ]

	class Boil:
		def __init__(self, time):
			self = time

	def __volume_at_stage(self, stage):
		assert(stage >= self.MASHWATER and stage <= self.FINAL)

		v = self.final_volume

		# assume 1l lost in fermenter
		if stage <= self.FERMENTER:
			v += self.hopsdrunk['fermenter']
			v += 1

		# assume 2% of boil volume plus hop crud lost in kettle
		if stage <= self.POSTBOIL:
			v += self.hopsdrunk['kettle']
			v *= 1.042

		# preboil volume is postboil + boil loss
		if stage <= self.PREBOIL:
			v += getconfig('boiloff_rate') * (self.boiltime / 60.0)

		if stage <= self.MASHWATER:
			v += Constants.grain_absorption \
			    * self.grainmass().valueas(Mass.KG) \
			    + getconfig('mlt_loss')

		return _Volume(v)

	def _prtsep(self, char='='):
		print char * 78

	def __extract(self, vol, strength):
		m = Mass(vol * strength.valueas(Strength.SG), Mass.KG)
		return Mass(m.valueas(Mass.G)
		    * strength.valueas(Strength.PLATO)/100.0, Mass.G)

	def mashin_ratio_set(self, ratio):
		self.mashin_ratio = ratio

	def hop_bymass(self, hop, mass, time):
		checktypes([(hop, Hop), (mass, Mass)])
		self.hops_bymass.append([hop, mass, time])

	# mass per final volume
	def hop_bymassvolratio(self, hop, mass, vol, time):
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass(mass * self.final_volume / vol)
		self.hops_bymass.append([hop, hopmass, time])

	# alpha acid mass per final volume
	def hop_byAAvolratio(self, hop, mass, vol, time):
		checktypes([(hop, Hop), (mass, Mass), (vol, Volume)])
		hopmass = _Mass((mass / (hop.aapers/100.0))
		    * (self.final_volume / vol))
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
		if when not in [ self.MASH, self.BOIL, self.FERMENT ]:
			raise PilotError('invalid fermentation stage')

		if self.__havefermentable(name, when):
			raise PilotError('fermentables may be specified max '
			    + 'once per stage')

		if fermentable.conversion and when != self.MASH:
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

	def fermentables_settemp(self, temp):
		checktype(degc, Temperature)
		self.fermentables_temp = temp

	# indicate that we want to "borrow" some wort at the preboil stage
	# for e.g. building starters.
	def steal_preboil_wort(self, vol, strength):
		checktypes([(vol, Volume), (strength, Strength)])

		extract = self.__extract(vol, strength)
		self.stolen_wort = (vol, strength, extract)

	def grainmass(self):
		assert('fermentables' in self.results)
		return _Mass(sum(x[2] for x in self.results['fermentables']))

	def fermentable_percentage(self, what, theoretical=False):
		percent = what[1].extract
		if what[1].conversion and not theoretical:
			percent *= getconfig('mash_efficiency')
		return percent

	def fermentable_yield(self, what, theoretical=False):
		return _Mass(what[2]
		    * self.fermentable_percentage(what, theoretical)/100.0)

	def _fermentables_atstage(self, when):
		return filter(lambda x: x[3] == when,
		    self.results['fermentables'])

	def total_yield(self, stage, theoretical=False):
		assert('fermentables' in self.results)

		def yield_at_stage(stage):
			return sum([self.fermentable_yield(x, theoretical) \
			    for x in self._fermentables_atstage(stage)])
		m = yield_at_stage(self.MASH)
		if stage == self.BOIL or stage == self.FERMENT:
			m += yield_at_stage(self.BOIL)
		if stage == self.FERMENT:
			m += yield_at_stage(self.FERMENT)
		return _Mass(m - self.stolen_wort[2])

	# turn percentages into masses
	def _dofermentables(self):
		# calculates the mass of extract required to hit the
		# target strength.

		if len(self.fermentables_bymass) > 0:
			self.results['fermentables'] = self.fermentables_bymass
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
			i = (x[0], x[1], _Mass(x[2]/100.0 * totmass), x[3])
			ferms.append(i)
		self.results['fermentables'] = ferms

	def _domash(self):
		prevol1 = self.__volume_at_stage(self.PREBOIL)
		prevol  = Brewutils.water_vol_at_temp(prevol1,
		    Constants.sourcewater_temp, Constants.preboil_temp)
		self.results['preboil_volume'] = prevol
		prestren = Brewutils.solve_strength(self.total_yield(self.MASH),
		    prevol)
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
		self.mash = Mash(mf,
		    self.fermentables_temp, totvol, self.mashin_ratio)

		totmass = self.grainmass()
		v = self.__volume_at_stage(self.POSTBOIL)

		res = []
		for f in sorted(mf, key=lambda x: x[2], reverse=True):
			ferm = f[1]
			mass = f[2]
			ratio = mass / totmass
			extract = self.fermentable_yield(f)
			compext = _Mass(extract - self.stolen_wort[2] * ratio)
			strength = Brewutils.solve_strength(compext, v)

			res.append((f[0], f[2], 100*ratio, extract, strength))

		self.results['mashfermentables'] = res
		self.results['mash'] = self.mash.infusion_mash(self.mashtemps)

	def _printmash(self):
		fmtstr = u'{:36}{:>20}{:>12}{:>8}'
		print fmtstr.format("Fermentables",
		    "amount", "extract", Strength.name() + " tot")
		self._prtsep()

		totextract = 0
		totstrength = 0

		for stage in [('mashfermentables', 'Mash'),
		    ('boilfermentables', 'Boil'),
		    ('fermfermentables', 'Ferment')]:
			(what, name) = stage
			if len(self.results.get(what, [])) > 0:
				print name
				self._prtsep('-')
				for f in self.results[what]:
					pers = ' ({:5.1f}%)'.format(f[2])
					print fmtstr.format(f[0],
					    str(f[1]) + pers, str(f[3]),
					    unicode(f[4]))
					totextract += f[3]
					totstrength += f[4]
				self._prtsep('-')

		self._prtsep()

		print fmtstr.format('', \
		    str(self.grainmass()) + ' (100.0%)', \
		    str(_Mass(totextract)),\
		    unicode(_Strength(totstrength)))

		print
		print 'Mashing instructions'
		self._prtsep()

		first = True
		for x in self.results['mash']['steps']:
			print u'{:7}'.format(unicode(x[0])) + ': add', x[1], \
			    'of water at', unicode(x[2]),
			if first:
				print '(' + str(self.mashin_ratio) \
				    + ' ratio)',
				first = False
			print

		print u'{:23}{:}'.format('Mashstep water volume:', \
		    unicode(self.results['mash']['mashstep_water']) + ' @ ' \
		    + unicode(Constants.sourcewater_temp))

		print u'{:23}{:}'. format('Sparge water volume:', \
		    unicode(self.results['mash']['sparge_water']) + ' @ '
		    + unicode(Constants.spargewater_temp))

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
			ratio = mass / self.grainmass()
			extract = self.fermentable_yield(f)
			strength = Brewutils.solve_strength(extract, v)

			res.append((f[0], f[2], 100*ratio, extract, strength))

		self.results['boilfermentables'] = res
		self._dohops()

	def _dohops(self):
		allhop = []

		# ok, um, so the Tinseth formula uses postboil volume ...
		v_post = self.__volume_at_stage(self.POSTBOIL)

		# ... and average strength during the boil.  *whee*
		v_pre = self.__volume_at_stage(self.PREBOIL)
		y = self.total_yield(self.BOIL)
		sg = _Strength((Brewutils.solve_strength(y, v_pre)
		    + Brewutils.solve_strength(y, v_post)) / 2)

		def gettime(mytime):
			if mytime is Hop.FWH:
				mytime = self.boiltime + 20
			return mytime

		# calculate IBU produced by "bymass" hops and add to printables
		for h in self.hops_bymass:
			time = gettime(h[2])
			ibu = h[0].IBU(sg, v_post, time, h[1])
			allhop.append([h[0], h[1], h[2], ibu])

		# calculate mass of "byIBU" hops and add to printables
		for h in self.hops_byIBU:
			time = gettime(h[2])
			mass = h[0].mass(sg, v_post, time, h[1])
			allhop.append([h[0], mass, h[2], h[1]])

		totibus = sum([x[3] for x in allhop])
		if self.hops_recipeIBU is not None:
			h = self.hops_recipeIBU
			time = gettime(h[2])
			missibus = self.hops_recipeIBU[1] - totibus
			if missibus <= 0:
				raise PilotError('total IBUs are greater than '\
				    + 'desired total')
			mass = h[0].mass(sg, v_post, time,
			    missibus)
			allhop.append([h[0], mass, h[2], missibus])
			totibus += missibus

		if self.hops_recipeBUGU is not None:
			h = self.hops_recipeBUGU
			time = gettime(h[2])
			bugu = self.hops_recipeBUGU[1]
			stren = self.results['final_strength']
			ibus = stren.valueas(stren.SG_PTS) * bugu
			missibus = ibus - totibus
			mass = h[0].mass(sg, v_post, time,
			    missibus)
			allhop.append([h[0], mass, h[2], missibus])
			totibus += missibus

		# Sort the hop additions of the recipe.
		#
		# pass 1: sort within claases
		allhop = sorted(allhop, key=lambda x: x[2], reverse=True)

		# pass 2: sort FWH -> boil -> whirlpool -> dryhop
		srtmap = {
			Hop.Dryhop	: 0,
			Hop.Steep	: 1,
			int		: 2,
			object		: 3
		}
		self.results['hops'] = sorted(allhop, cmp=lambda x,y:
		    srtmap[x[2].__class__] - srtmap[y[2].__class__],
		    reverse=True)
		self.ibus = totibus

		# calculate amount of wort that hops will drink
		hd = {x: 0 for x in self.hopsdrunk}
		kegdryhopvol = 0
		for h in allhop:
			if isinstance(h[2], Hop.Dryhop):
				if h[2].indays is not h[2].Keg:
					hd['fermenter'] += h[0].absorption(h[1])
				else:
					hd['keg'] += h[0].absorption(h[1])
					kegdryhopvol += h[0].volume(h[1])
			else:
				hd['kettle'] += h[0].absorption(h[1])

		self.hopsdrunk = {x: _Volume(hd[x]/1000.0) for x in hd}
		self.kegdryhopvol = _Volume(kegdryhopvol)

	def _printboil(self):
		# XXX: IBU sum might not be sum of displayed hop additions
		# due to rounding.  cosmetic, but annoying.
		namelen = 34
		onefmt = u'{:' + str(namelen) + '}{:8}{:>15}{:>10}{:>9}'
		print onefmt.format("Hops", "AA%", "time", "amount", "IBUs")
		self._prtsep()
		totmass = 0

		prevstage = None
		for h in self.results['hops']:
			typ = ' (' + h[0].typestr + ')'
			nam = h[0].name
			if h[2] is Hop.FWH:
				time = 'FWH'
			elif isinstance(h[2], int):
				time = unicode(h[2]) + ' min'
			else:
				if prevstage is not None and \
				    prevstage is not h[2].__class__:
					self._prtsep('-')
				time = unicode(h[2])
			maxlen = (namelen-1) - len(typ)
			if len(nam) > maxlen:
				nam = nam[0:maxlen-4] + '...'

			prevstage = h[2].__class__
			totmass = h[1] + totmass

			# printing IBUs with two decimal points, given all
			# other inaccuracy involved, is rather silly.
			# but what would we be if not silly?
			ibustr = '{:.2f}'.format(h[3])
			print onefmt.format(nam + typ, str(h[0].aapers) + '%', \
			    time, str(h[1]), ibustr)
		self._prtsep()
		ibustr = '{:.2f}'.format(self.ibus)
		print onefmt.format('', '', '', str(_Mass(totmass)), ibustr)
		print

	def _keystats(self):
		self._prtsep()
		onefmt = u'{:19}{:}'
		twofmt = u'{:19}{:19}{:21}{:19}'

		postvol1 = self.__volume_at_stage(self.POSTBOIL)
		postvol  = Brewutils.water_vol_at_temp(postvol1,
		    Constants.sourcewater_temp, Constants.postboil_temp)
		total_water = _Volume(self.results['mash']['total_water']
		    + self.results['steal']['missing'])

		# calculate EBC color, via MCU & Morey equation
		# "European Color Units", equivalent of MCU
		ecu = sum(f[2]*f[1].ebc for f in self.results['fermentables'])
		mcu = ecu / (Constants.gramsperpound \
		    * (postvol1/Constants.literspergallon)*Constants.ebcpersrm)
		srm = 1.4922 * pow(mcu, 0.6859)
		ebc = srm * Constants.ebcpersrm

		print onefmt.format('Name:', self.name)
		print twofmt.format('Final volume:', str(self.final_volume), \
		    'Boil:', str(self.boiltime) + ' min')
		bugu = self.ibus / self.results['final_strength']
		print twofmt.format('IBU (Tinseth):', \
		    '{:.2f}'.format(self.ibus), \
		    'BUGU:', '{:.2f}'.format(bugu))
		print twofmt.format('Color (EBC / SRM):', \
		    '{:.1f}'.format(ebc) + ' / ' + '{:.1f}'.format(srm), \
		    'Water (' + unicode(Constants.sourcewater_temp) + '):', \
		    unicode(total_water))
		bil = 1000*1000*1000
		unit = ' billion'
		print twofmt.format('Pitch rate, ale:',
		    str(int(self.results['pitch']['ale'] / bil)) + unit,
		    'Pitch rate, lager:',
		    str(int(self.results['pitch']['lager'] / bil)) + unit)
		print
		print onefmt.format('Yeast:', self.yeast)
		print onefmt.format('Water notes:', '')
		print

		print twofmt.format('Preboil  volume  :', \
		    str(self.results['preboil_volume']) \
		    + ' (' + unicode(Constants.preboil_temp) + ')', \
		    'Measured:', '')
		print twofmt.format('Preboil  strength:', \
		    unicode(self.results['preboil_strength']), \
		    'Measured:', '')
		print twofmt.format('Postboil volume  :', str(postvol) \
		    + ' (' + unicode(Constants.postboil_temp) + ')', \
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
		maxstren = Brewutils.solve_strength(maxyield, self.final_volume)
		beff = self.results['final_strength'] / maxstren
		print twofmt.format('Mash eff (conf) :', \
		    str(100*getconfig('mash_efficiency')) + '%',
		    'Brewhouse eff (est):', '{:.1f}%'.format(100 * beff))

		if self.hopsdrunk['keg'] > 0:
			print
			print 'NOTE: keg hops absorb: ' \
			    + str(self.hopsdrunk['keg']) \
			    + ' => effective yield: ' \
			    + str(_Volume(self.final_volume
				  - self.hopsdrunk['keg']))

			# warn about larger packaging volume iff keg dryhops
			# volume exceeds 1dl
			if self.kegdryhopvol > 0.1:
				print 'NOTE: keg hop volume: ~' \
				    + str(self.kegdryhopvol) \
				    + ' => packaged volume: ' \
				    + str(_Volume(self.final_volume
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
			ratio = mass / self.grainmass()
			extract = self.fermentable_yield(f)
			strength = Brewutils.solve_strength(extract, v)

			res.append((f[0], f[2], 100*ratio, extract, strength))

		self.results['fermfermentables'] = res

		self._doattenuate()

	def _doattenuate(self, attenuation = (60, 86, 5)):
		res = []
		for x in range(*attenuation):
			t = self.results['final_strength'].attenuate(x/100.0)
			res.append((x, t[0], t[1]))
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

	def printit(self):
		self._keystats()
		self._printmash()
		self._printboil()
		self._printattenuate()

	def do(self):
		self.calculate()
		self.printit()

class Hop:
	FWH	= object()

	Pellet	= object()
	Leaf	= object()

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

	def __init__(self, name, aapers, type = Pellet):
		aalow = 1
		aahigh = 100 # I guess some hop extracts are [close to] 100%

		self.name = name
		self.type = type
		if type is Hop.Pellet:
			self.typestr = 'pellet'
		elif type is Hop.Leaf:
			self.typestr = 'leaf'
		else:
			raise PilotError('invalid hop type')

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

		# hopping that our current formula doesn't support
		if not isinstance(mins, int):
			return 0

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
		return _Mass((IBU * volume) / (util * self.aapers/100.0 * 1000))

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
	# grain dry volume, (pessimistic estimate, i.e. could be less)
	__grain_literperkg = 0.7

	# infusion mash step state and calculator for the next.
	#
	# In the context of this class, we use the following terminology:
	#	capa: specific heat times mass (or equivalent thereof)
	#		in relation to that of water
	#	temp: temperature
	#	heat: total heat of the component, i.e. capa * temp
	#
	class __Step:
		# MLT heat capacity is equal to given mass of water
		# XXX: should be configurable
		__mlt_capa = Mass(1.5, Mass.KG)

		# assume MLT temp is ~20degC.  if you're brewing inside,
		# it's accurate enough
		__mlt_temp = _Temperature(20)

		# relative to capa of equivalent mass of water
		__grain_relativecapa = 0.38

		def __init__(self, grain_mass, grain_temp,
		    water_volume, water_temp):
			hts = {}

			hts['mlt'] = {}
			hts['mlt']['capa'] = self.__mlt_capa.valueas(Mass.KG)
			hts['mlt']['temp'] = self.__mlt_temp

			hts['grain'] = {}
			hts['grain']['capa'] = self.__grain_relativecapa \
			    * grain_mass.valueas(Mass.KG)
			hts['grain']['temp'] = grain_temp

			hts['water'] = {}
			hts['water']['capa'] = water_volume
			hts['water']['temp'] = water_temp

			self.hts = hts

		def heat(self, what):
			ho = self.hts[what]
			return ho['temp'] * ho['capa']

		def capa(self, what):
			ho = self.hts[what]
			return ho['capa']

		def up(self, target_temp, minwater):
			def nextstep(parent, nwater_capa, nwater_temp, newtemp):
				nextstep = copy.deepcopy(parent)

				hts = nextstep.hts

				hts['water']['capa'] += nwater_capa
				hts['mlt']['temp'] = newtemp
				hts['grain']['temp'] = newtemp
				hts['water']['temp'] = newtemp

				nextstep.step_watermass = nwater_capa
				nextstep.step_watertemp = nwater_temp

				return nextstep

			# the new temperature is the existing
			# heat plus the new heat, divided by the
			# total heat capacity.

			nwater_capa = minwater
			if nwater_capa is None:
				nwater_capa = _Volume(0.1)

			capa = self.capa
			heat = self.heat

			# step 1: see if where we can go with "minwater".
			# if we reach the target with <boiling water, we're
			# done.
			nwater_temp = (target_temp \
			      * (nwater_capa + capa('mlt')		    \
				  + capa('grain') + capa('water'))	    \
			    - (heat('mlt') + heat('grain') + heat('water')))\
			  / nwater_capa

			if nwater_temp <= 100:
				return nextstep(self, nwater_capa,
				    nwater_temp, target_temp)

			# step 2: if we couldn't, set temperature to boiling
			# and see how much water we need.
			boiltemp = _Temperature(100)
			nw = (target_temp \
			      * (capa('mlt') \
				  + capa('grain') + capa('water'))\
			    - (heat('mlt')+heat('grain')+heat('water')))\
			  / (boiltemp - target_temp)

			return nextstep(self, nw, boiltemp, target_temp)

		def waterstats(self):
			return (_Volume(self.step_watermass),
			    _Temperature(self.step_watertemp))


	def __init__(self, mashfermentables, fermentable_temp, mashwater_vol,
	    mashin_ratio):
		self.mashfermentables = mashfermentables
		self.fermentable_temp = fermentable_temp
		self.mashwater_vol = mashwater_vol
		self.mashin_ratio = mashin_ratio

	def infusion_mash(self, mashtemps):
		fmass = _Mass(sum(x[2] for x in self.mashfermentables))

		res = {}
		res['steps'] = []
		res['total_water'] = self.mashwater_vol

		step = self.__Step(fmass, self.fermentable_temp, 0, 0)
		mass = self.mashin_ratio * fmass.valueas(Mass.KG)
		totvol = self.mashwater_vol

		for t in mashtemps:
			step = step.up(t, mass)
			if mass:
				mass = None
			(vol, temp) = step.waterstats()
			totvol -= vol
			if totvol < 0:
				raise PilotError('cannot satisfy infusion steps'
				    ' with given parameters (ran out of water)')

			actualvol = Brewutils.water_vol_at_temp(vol,
			    Constants.sourcewater_temp, temp)
			res['steps'].append((t, actualvol, temp))

		res['mashstep_water'] = _Volume(self.mashwater_vol - totvol)
		res['sparge_water'] = \
		    Brewutils.water_vol_at_temp(_Volume(totvol), \
		    Constants.sourcewater_temp, Constants.spargewater_temp)

		return res

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

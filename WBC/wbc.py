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

from WBC.addition import Addition, Opaque, Water, Internal, Fermadd
from WBC.utils import *
from WBC.units import *
from WBC.units import _Mass, _Strength, _Temperature, _Volume, _Duration
from WBC.hop import Hop
from WBC.nute import Nute
from WBC.mash import Mash
from WBC.worter import Worter, laterworter

from WBC import brewutils, timespec
from WBC.timespec import Timespec, Boil

def checkconfig():
	return True

def _ismass(type): return istype(type, Mass)
def _isvolume(type): return istype(type, Volume)
def _ismassvolume(type): return istupletype(type, (Mass, Volume))
def _isvolumevolume(type): return istupletype(type, (Volume, Volume))

class WBC:
	pass

class Recipe:
	STRENGTH_MAX=	"maximum"

	def __init__(self):
		input = {}
		input['notes'] = {}
		input['notes']['brewday'] = []
		input['notes']['recipe'] = []

		self.boiltime = input['boiltime'] = None
		self.volume_inherent =self.volume_set =self.volume_scaled =None

		self.input = input

		self.needinherent = []

		self.hops_in = []
		self.hops_recipeIBUBUGU = None

		self.nutes_in = []
		self.nutes_recipe = None

		self.ferms_in = []

		# the current "best guess" for additional extract needed
		# to reach final-strength target (for applicable recipes)
		self.fermentable_extadj = _Mass(0)

		# current guess for the strength, for STRENGHT_MAX recipes
		self._strengthguess = None

		# user-settable final strength
		self.final_strength = None

		# cached educated guess of the water
		# amount used in the forward calculation
		self.waterguess = None

		self.opaques = []
		self.water = []

		self.input['stolen_wort'] = Worter()
		self._boiladj = _Mass(0)

		self.hopsdrunk = {'kettle':_Volume(0), 'fermentor':_Volume(0),
		    'package':_Volume(0)}

		self._calculatestatus = 0

		self.mash = Mash()

		self._oncelst = []

	def paramdefaults(self):
		sysparams.processdefaults()

	def paramfile(self, filename):
		Sysparams.processfile(filename)

	THEREST=	'rest'

	def _error(self, msg):
		raise PilotError(msg)

	def _final_volume(self):
		assert(self._calculatestatus > 0)
		v = [self.volume_scaled, self.volume_set, self.volume_inherent ]
		return ([x for x in v if x is not None] + [None])[0]

	def _final_strength(self):
		if self._strengthguess is not None:
			return self._strengthguess
		return self.final_strength

	def _final_extract(self):
		if self.final_strength is None:
			return None

		w = Worter()
		w.set_volstrength(self._final_volume(), self._final_strength())
		return w.extract()

	def _strength_max_p(self):
		return self.final_strength is self.STRENGTH_MAX

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
	def _resolver_scale(self, what, when, opaque):
		if self.volume_inherent is None or self.volume_scaled is None:
			return what

		assert(isinstance(what, Mass) or isinstance(what, Volume))

		scale = self.volume_scaled / self.volume_inherent
		return what.__class__(scale * what, what.defaultunit)

	def _scale(self, what):
		return self._resolver_scale(what, None, None)

	def _xvol2x_fromvol(self, x, vol):
		assert(istupletype(x, (Mass, Volume))
		    or istupletype(x, (Volume, Volume)))
		return x[0].__class__(x[0]/x[1] * vol, x[0].defaultunit)

	def _resolver_xvol2x(self, x, when, opaque):
		return self._xvol2x_fromvol(x, self._final_volume())

	# scale to volume, but instead of final volume use amount of
	# water or volume "at" the current stage.  The options:
	#
	#   * mash @ mashin: mashstep water (= total mash water - sparge)
	#   * mash @ sparge: sparge water
	#
	#   * boil         : postboil volume @ reference temp
	#   * fermentor    : final volume (i.e. after sugar additions)
	#   * package      : final volume (i.e. after sugar additions)
	#
	def _resolver_xvol2x_withwater(self, x, when, opaque):
		if isinstance(when, timespec.MashSpecial):
			vol = self.results['mash']['sparge_water'].water()
		elif isinstance(when, timespec.Mash):
			vol = self.results['mash']['mashstep_water'].water()
		elif isinstance(when, timespec.Boil):
			vol = self.worter[Worter.POSTBOIL].volume()
		elif isinstance(when, timespec.Fermentor):
			vol = self.worter[Worter.FERMENTOR].volume()
		else:
			assert(isinstance(when, timespec.Package))
			vol = self.worter[Worter.PACKAGE].volume()
		return self._xvol2x_fromvol(x, vol)

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

	def _addunit(self, checkfuns, unit, fname, iswater = False):
		rv = ([x for x in checkfuns if x(unit)] + [None])[0]
		if rv is None:
			raise PilotError('invalid input type for: ' + fname)

		# XXX: ugly
		if isinstance(unit, tuple):
			if iswater:
				scale = self._resolver_xvol2x_withwater
			else:
				scale = self._resolver_xvol2x
		else:
			scale = self._resolver_scale
			self._needinherentvol(fname)
		return scale

	#
	# user interfaces
	#

	def set_inherent_volume(self, volume):
		if self.volume_inherent:
			raise PilotError('inherent volume set multiple times')
		self.volume_inherent = volume

	def set_boiltime(self, boiltime):
		if self.boiltime:
			notice('overriding already-specified boiltime '
			    + str(self.input['boiltime']) + ' with '
			    + str(boiltime) + '\n')

		self.boiltime = self.input['boiltime'] = boiltime
		timespec.set_boiltime(boiltime)

	def set_volume_and_scale(self, volume):
		checktype(volume, Volume)
		self.volume_scaled = volume

	def set_volume(self, volume):
		checktype(volume, Volume)
		self.volume_set = volume

	def _setinputstr(self, what, value):
		checktype(value, str)
		if self.input.get(what, None):
			self._error(what + ' set multiple times')
		self.input[what] = value

	def set_name(self, name):
		self._setinputstr('name', name)

	def set_yeast(self, yeast, fermentplan):
		self._setinputstr('yeast', yeast)
		if fermentplan:
			self._setinputstr('fermentplan', fermentplan)

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
		self.hops_in.append(a)
		return a

	def hop_byunit(self, name, unit, time):
		scale = self._addunit([_ismass, _ismassvolume], unit, __name__)
		self._hopstore(name, unit, scale, time, 'm')

	# alpha acid mass
	def hop_byAA(self, hop, mass, time):
		checktype(mass, Mass)
		self._needinherentvol('hop_byAA')
		amount = _Mass(mass / hop.aa)
		self._hopstore(hop, amount, self._resolver_scale, time, 'm')

	# alpha acid mass per final volume
	def hop_byAAvolratio(self, hop, mv, time):
		(mass, vol) = mv
		checktypes([(mass, Mass), (vol, Volume)])
		amount = (_Mass(mass / hop.aa), vol)
		self._hopstore(hop, amount, self._resolver_xvol2x, time, 'm')

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

	#
	# Nutrients
	#

	def _resolver_x2x_withnute(self, x, when, opaque):
		vol, yan, bxp = opaque

		rv = _Mass(bxp*x / yan)
		return rv

	def _resolver_xvol2x_withnute(self, x, when, opaque):
		vol, yan, bxp = opaque

		x1 = _Mass(self._xvol2x_fromvol(x, vol))
		return self._resolver_x2x_withnute(x1, when, opaque)

	def _nute_byindividual(self, nute, amount, time, flags):
		checktypes([(nute, Nute), (time, Timespec)])
		assert(Nute.RECIPE not in flags)

		if _ismass(amount):
			resolver = self._resolver_x2x_withnute
		elif _ismassvolume(amount):
			resolver = self._resolver_xvol2x_withnute
		else:
			raise PilotError('invalid nutrient specifier')

		if len([x for x in flags if x not in Nute.flags]) > 0:
			raise PilotError('invalid flags')

		a = Addition(nute, amount, resolver, time, cookie = flags)
		self.nutes_in.append(a)

	def _nute_byrecipe(self, nute, value, time, flags):
		checktypes([(nute, Nute), (time, Timespec)])
		assert(Nute.RECIPE in flags)

		if self.nutes_recipe is not None:
			raise PilotError('Recipe nutes specified >once')
		if Nute.GROSS in flags:
			raise PilotError('cannot specify gross recipe YAN')

		self.nutes_recipe = {
			'nute': nute,
			'time': time,
			'value': value,
			'perBx': Nute.PERBX in flags,
		}

	def nute_byunit(self, nute, unit, time, flags):
		if Nute.RECIPE in flags:
			return self._nute_byrecipe(nute, unit, time, flags)
		else:
			return self._nute_byindividual(nute, unit, time, flags)

	#
	# Opaques.
	#
	# not used for in-recipe calculations, printed out in timed additions.
	#

	def _opaquestore(self, cls, opaque, amount, resolver, time):
		checktype(time, Timespec)
		a = Addition(cls(opaque), amount, resolver, time)
		self.opaques.append(a)

	def opaque_byunit(self, name, unit, time):
		scale = self._addunit([_ismass, _isvolume,
		    _ismassvolume, _isvolumevolume], unit, __name__)
		self._opaquestore(Opaque, name, unit, scale, time)

	def opaque_byopaque(self, opaque, ospec, time):
		checktype(time, Timespec)
		if ospec.__class__ != str:
			raise PilotError('opaque spec must be a string')
		self._opaquestore(Opaque, opaque, ospec, None, time)

	#
	# Fermentables.
	#

	def anchor_bystrength(self, strength):
		strength == self.STRENGTH_MAX or checktype(strength, Strength)

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
		a = Fermadd(ferm, amount, resolver, time, cookie = cookie)
		self.ferms_in.append(a)
		return a

	# Fermentables specified by unit may be specified either as
	# mass (solid ingredients) or volume (liquid ingredients).
	def fermentable_byunit(self, name, unit, time):
		ferm = fermentables.Get(name)
		if ferm.type() == ferm.LIQUID:
			accepted = [_isvolume, _isvolumevolume]
		else:
			accepted = [_ismass, _ismassvolume]
		scale = self._addunit(accepted, unit, __name__)
		self._fermstore(name, unit, scale, time, 'm')

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

	#
	# Water.
	#

	# Addition by mass and volume is easy.  m/v and v/v additions
	# are trickier, and do not work like other m/v and v/v additions,
	# because, for example, you don't want the salts in the mash
	# scaled to the final volume but rather the water in the mash.
	#
	# see comment above resolver_xvol2x_withwater for more info.
	def water_byunit(self, what, unit, when):
		checktype(when, Timespec)

		resolver = self._addunit([_ismass, _ismassvolume, _isvolume,
		    _isvolumevolume], unit, __name__, iswater = True)
		a = Addition(Water(what), unit, resolver, when)
		self.water.append(a)

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

	def _fermentable_water(self, what):
		f = what.obj
		percent = f.extract.moisture()
		return _Mass(what.get_amount() * percent/100.0)

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

	def _fermwater_bytimespec(self, stage):
		assert(stage in Timespec.stages)

		return _Mass(sum([self._fermentable_water(x) \
		    for x in self._fermentables_bytimespec(stage)]))

	def _sanity_check(self):
		# XXX: none at the time
		pass

	# set initial guesses for fermentables
	def _dofermentables_preprocess(self):
		# have by-percent?  no?  we're done
		rlst, plst = self._fermfilter('r'), self._fermfilter('p')
		if len(rlst + plst) == 0:
			if self.final_strength is not None:
				raise PilotError("cannot satisfy strength "
				    "spec without percent-fermentables")
			return

		# Set an initial guess for the final strength in the
		# case of maxstrength.
		#
		# We don't have much calculated yet, so use the
		# amount of extract from by-mass fermentables as the
		# initial guess.  However, set it to a minimum of 11 plato
		# to get a more realistic first guess for cases where the
		# by-mass fermentables are just priming sugar.
		if self._strength_max_p():
			massfermext = _Mass(sum([self._fermentable_extract(x)
			    for x in self._fermfilter('m')]))
			stren = brewutils.solve_strength(massfermext,
			    self._final_volume())
			self._strengthguess = max(stren, _Strength(11))

		# check that we have 100% fermentables in the recipe
		ptot = sum([x.get_amount() for x in plst])
		if len(rlst) == 0:
			if abs(ptot - 100.) > .00001:
				raise PilotError('need 100% fermentables. '
				    + 'literally forgot "rest"?')
			return

		# evenly divide missing portion among "rest" fermentables
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

		assert(self._final_strength() is not None)
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


	def _dofermentables_and_worters_bymass(self):
		self._set_calcguess(self._fermfilter('m'), None)
		vl = self.vol_losses

		# With bymass, we have to guess water first,
		# because calculation goes from start to finish.
		# We guess once and refine it later.
		if self.waterguess is None:
			vol_loss = _Volume(sum(vl.values())
			    + self._boiloff()
			    + self.mash.evaporation().water())
			fermwater = sum([self._fermentable_water(x)
			    for x in self.fermentables], _Mass(0))
			self._set_waterguess(_Mass(self._final_volume()
			    + vol_loss - fermwater))

		for i in range(10):
			res = self._doworters_bymass()
			voldiff = _Mass(res[Worter.PACKAGE].volume()
			    - self._final_volume())
			if abs(voldiff) < 0.01:
				break
			self._set_waterguess(self.waterguess - voldiff)
		else:
			raise Exception('PANIC: recipe failed to converge')
		return res


	def _dofermentables_and_worters_bypercent(self):
		if self.final_strength is None:
			raise PilotError('final strength must be set for '
			    + 'by-percent fermentables')

		# account for "unknown" extract losses from stage to stage
		# ("unknown" = not solved analytically)
		for _ in range(30):
			self._dofermentables_bypercent(self._fermfilter('m'))
			extoff, watoff = self._doworters_bystrength()

			canbreak = True

			# adjust guesses.  if were shooting for a volume,
			# adjust the strength guess until our starting point
			# volume is 0.  if we're shooting for strength,
			# adjust the amount of extract we need
			if self._strength_max_p() and abs(watoff) >= 0.001:
				# We check for and adjust the water until
				# it matches.  If we have a positive water
				# offset (too much water), we need to reduce
				# the strength to bring the absolute masses
				# down.  If we have a negative water offset,
				# we need to increase the strength to
				# increase the amount of fermentables and
				# hence water going into the system.
				#
				# So how much should we adjust the strength
				# by if we want to reach "0" water offset?
				# Create the final strength worter, adjust
				# the water, and take the reading.  To avoid
				# overshooting ridiculously, adjust only by
				# half of the water offset.
				canbreak = False
				wfin = Worter()
				wfin.set_volstrength(self._final_volume(),
					self._strengthguess)
				wfin.adjust_water(-_Mass(watoff/2.0))
				self._strengthguess = wfin.strength()

			if abs(extoff) < 0.001 and canbreak:
				break

			# adjust value used in dofermentables_bypercent
			# and try again
			self.fermentable_extadj += extoff
		else:
			raise Exception('unable to calculate fermentables')

		# With by-percent we guess water last, because calculation
		# goes from finish-to-start, and we can guess only once
		# we're at the start.  Notably, the waterguess is used for
		# the final calculation with masses.
		if self.waterguess is None:
			self._set_waterguess(watoff + self._boiladj)

		# calculate now-filled masses using bymass and return
		return self._doworters_bymass()


	# turn percentages into masses, calculate expected worters
	# for each worter stage
	def _dofermentables_and_worters(self):
		if len(self._fermfilter(('r', 'p'))) == 0:
			return self._dofermentables_and_worters_bymass()
		else:
			return self._dofermentables_and_worters_bypercent()


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
		# are added as timespecs, but the total extract is
		# in worters.
		def extract_predicted(f, fermstage):
			f_ext = self._fermentable_extract(f)
			tss = Timespec.stages
			losses = self.results['losses']
			worters = self.worter

			def stageloss(stagecmp, wname):
				v = 0
				if tss.index(fermstage) <= tss.index(stagecmp):
					stageloss = losses[stagecmp].extract()
					stageext = worters[wname].extract()

					v = stageloss * (f_ext/stageext)
				return _Mass(v)

			f_ext -= stageloss(Timespec.KETTLE, Worter.POSTBOIL)
			f_ext -= stageloss(Timespec.FERMENTOR, Worter.FERMENTOR)

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


	def _domash(self, mashwort):
		#
		# Enforce that all mash additions are for a step
		#
		adds = self.fermentables + self.water + self.opaques + self.hops
		mashspecs = [x.time for x in adds
		    if x.time.__class__ == timespec.Mash
		      and x.time != timespec.Mash(timespec.Mash.MASHIN)]
		for ts in mashspecs:
			if not self.mash.has_stepwithtimespec(ts):
				raise PilotError('mash step for addition '
				   + 'does not exist: ' + str(ts))

		mf = self._fermentables_bytimespec(Timespec.MASH)
		self.mash.set_fermentables(mf)

		# The mash worter includes the moisture from the grains,
		# so we need to subtract it from the amount of water
		# that gets added into the mash
		mashwater = Worter(water = mashwort.water())
		fermwater = self._fermwater_bytimespec(Timespec.MASH)
		mashwater.adjust_water(-fermwater)

		self.results['mash'] \
		    = self.mash.do_mash(getparam('ambient_temp'),
			mashwater, self._grain_absorption())

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

		# Update volume loss caches.  Notable, these
		# are *exactly* what the say they are: volume
		# losses (no info on how much of that volume is
		# extract or water).  They also do not include
		# things which are not losses (e.g. boiloff).
		vl = {}
		def gabs(ts):
			f = f = self._fermentables_bytimespec(ts)
			m = self._fermentables_massof(f)
			return _Volume(m*self._grain_absorption())

		# If there is no mash, there is no mashtun loss either.
		if (laterworter(self.firstworter, Worter.MASH)
		    or isinstance(self.earlyferm, timespec.MashSpecial)):
			ml = _Volume(0)
		else:
			ml = getparam('mlt_loss')
		vl[Timespec.MASH] = gabs(Timespec.MASH) + ml

		vl[Timespec.POSTMASH] = gabs(Timespec.POSTMASH)

		hd = self.hopsdrunk
		# no boil => no constant kettle loss
		if laterworter(self.firstworter, Worter.POSTBOIL):
			assert(hd['kettle'] < 0.0001)
			kl = _Volume(0)
		else:
			kl = getparam('kettle_loss')

		vl[Timespec.KETTLE] = hd['kettle'] + kl
		vl[Timespec.FERMENTOR] = hd['fermentor'] \
		    + getparam('fermentor_loss')
		self.vol_losses = vl


	# set the guess for the amount of water we need to add
	def _set_waterguess(self, guess):
		# "max" strength never gets any implicit water
		if self._strength_max_p():
			self.waterguess = _Mass(0)
		else:
			self.waterguess = guess


	#
	# Adjust the extract and water contributions from the ingredients
	# into the worter, which results in the worter of the current step.
	# Make a copy of the worter.  Then remove the absorbed water, which
	# results in worter passed to the next step.
	#
	# Return the worter for the *current* step (i.e. the next step
	# is modified in the passed reference of "w").
	#
	def _mgadj(self, w, ts, dir):
		vl = self.vol_losses

		ext = self._extract_bytimespec(ts)
		w.adjust_extract(_Mass(dir*ext))
		w.adjust_water(_Mass(dir*self._fermwater_bytimespec(ts)))
		w_ret = copy.deepcopy(w)

		# We account for the extract loss already in the mash
		# efficiency as returned by _extract_bytimespec()
		# (via sysparam).  Therefore, coupled with the
		# lost volume we calculate the amount of water lost,
		# and adjust the water only.
		if ext > 0.001:
			maxext = self._extract_bytimespec(ts, theoretical=True)
			extdiff = _Mass(maxext - ext)
			stren = brewutils.solve_strength(extdiff, vl[ts])

			w_loss = Worter()
			w_loss.set_volstrength(vl[ts], stren)
			w.adjust_water(_Mass(-dir*w_loss.water()))

		return w_ret

	def _mashgrainadj_backward(self, w, ts): return self._mgadj(w, ts, -1)
	def _mashgrainadj_forward(self, w, ts): return self._mgadj(w, ts, 1)

	# bymass: calculate worters based on a mashwater input.  We use
	# this both for figuring out the strength of the wort produced
	# from a bymass-brew, and also after percentage&strength
	# has been resolved into masses.
	def _doworters_bymass(self):
		res = {}
		vl = self.vol_losses

		# Add empty worters so that if early stages are skipped,
		# the results show a zero worter.
		for s in Worter.stages:
			res[s] = Worter()

		w = Worter(water = self.waterguess - self._boiladj)

		if not laterworter(self.firstworter, Worter.MASH):
			res[Worter.MASH] = self._mashgrainadj_forward(w,
			    Timespec.MASH)
			w -= self.mash.evaporation()

		#
		# pre-and-postboil, pre-and-postboil
		# they go together like hops and turmoil
		# this, I tell you breeeewer
		# you can't have one without the other
		#
		if not laterworter(self.firstworter, Worter.PREBOIL):
			# There is no "POSTMASH" worter, hence the correct
			# result is in "w", not the returned worter
			_ = self._mashgrainadj_forward(w, Timespec.POSTMASH)
			res[Worter.PREBOIL] = copy.deepcopy(w)

			w.adjust_water(_Mass(-self._boiloff()))
			ext = self._extract_bytimespec(Timespec.KETTLE)
			water = self._fermwater_bytimespec(Timespec.KETTLE)
			w.adjust_extract(ext)
			w.adjust_water(water)

			res[Worter.POSTBOIL] = copy.deepcopy(w)

		w.adjust_volume(-vl[Timespec.KETTLE])
		w.adjust_extract(self._extract_bytimespec(Timespec.FERMENTOR))
		w.adjust_water(self._fermwater_bytimespec(Timespec.FERMENTOR))
		w.adjust_water(self._boiladj)
		res[Worter.FERMENTOR] = copy.deepcopy(w)

		w.adjust_volume(-vl[Timespec.FERMENTOR])
		w.adjust_extract(self._extract_bytimespec(Timespec.PACKAGE))
		w.adjust_water(self._fermwater_bytimespec(Timespec.PACKAGE))
		res[Worter.PACKAGE] = copy.deepcopy(w)

		return res


	# bystrength: start from final volume / strength, calculate
	# backwards
	def _doworters_bystrength(self):
		res = {}
		vl = self.vol_losses

		w = Worter()
		w.set_volstrength(self._final_volume(), self._final_strength())
		w.adjust_extract(-self._extract_bytimespec(Timespec.PACKAGE))
		w.adjust_water(-self._fermwater_bytimespec(Timespec.PACKAGE))
		w.adjust_volume(vl[Timespec.FERMENTOR])
		w.adjust_extract(-self._extract_bytimespec(Timespec.FERMENTOR))
		w.adjust_water(-self._fermwater_bytimespec(Timespec.FERMENTOR))

		if laterworter(self.firstworter, Worter.POSTBOIL):
			return w.extract(), w.water()

		w.adjust_volume(vl[Timespec.KETTLE])
		w.adjust_water(-self._boiladj)

		w.adjust_extract(-self._extract_bytimespec(Timespec.KETTLE))
		w.adjust_water(-self._fermwater_bytimespec(Timespec.KETTLE))
		w.adjust_water(_Mass(self._boiloff()))

		self._mashgrainadj_backward(w, Timespec.POSTMASH)

		if laterworter(self.firstworter, Worter.MASH):
			return w.extract(), w.water()

		w += self.mash.evaporation()
		self._mashgrainadj_backward(w, Timespec.MASH)

		return w.extract(), w.water()

	def _dohops(self, w_preboil, w_postboil, w_pkg):
		hin = self.hops_in
		allhop = []

		# Account for water added post-boil.  We assume
		# that IBUs scale linearly as a function of volume,
		# i.e. x IBUs will dilute to x * (postboil/postboil+dilution)
		#
		# I am not 100% if it holds for IBUs nearing 120, but
		# we'll call it good enough for now; a more complex
		# calculation can be added later if desirable.
		if laterworter(self.firstworter, Worter.POSTBOIL):
			scalefact = 1.0
		else:
			wrk = copy.deepcopy(w_postboil)
			wrk.adjust_water(self._boiladj)
			scalefact = w_postboil.volume() / wrk.volume()
		def ibu_dilute(ibu):
			return ibu * scalefact
		def ibu_concentrate(ibu):
			return ibu / scalefact

		# ok, um, so the Tinseth formula uses postboil volume ...
		v_post = w_postboil.volume()

		# ... and average gravity during the boil.  *whee*
		# (XXX: this isn't the average gravity in case there
		# are kettle additions.  while we could calculate the
		# average by "integrating" minute-per-minute, call this
		# good enough, especially since I'm not sure if
		# things like simple sugars have a similar effect on
		# IBU, compared to malt sugars)
		t = (w_preboil.strength().valueas(Strength.SG)
		    + w_postboil.strength().valueas(Strength.SG))
		sg = Strength(t/2, Strength.SG)

		#
		# Do the hop calculations.  We edit the original input
		# objects, but since we only use the original values on
		# all iterations.  Saves a big deepcopy.
		#
		# calculate IBU produced by "bymass" hops
		for hs, h in [(x, x.obj) for x in hin if x.cookie == 'm']:
			ibu = ibu_dilute(h.mass2IBU(sg,
			    v_post, hs.time, hs.get_amount()))
			hs.info = ibu

		# calculate mass of "byIBU" hops
		for hs, h in [(x, x.obj) for x in hin if x.cookie == 'i']:
			mass = h.IBU2mass(sg,
			    v_post, hs.time, ibu_concentrate(hs.info))
			hs.set_amount(mass)

		allhop = hin[:]
		totibus = sum([x.info for x in allhop])
		if self.hops_recipeIBUBUGU is not None:
			x = self.hops_recipeIBUBUGU
			h, t, v = x['hop'], x['time'], x['value']

			if x['type'] == 'BUGU':
				v *= w_pkg.strength().valueas(Strength.SG_PTS)
			missibus = v - totibus
			if missibus <= 0:
				raise PilotError('recipe IBU/BUGU exceeded')

			mass = h.IBU2mass(sg,
			    v_post, t, ibu_concentrate(missibus))
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

		hdold = self.hopsdrunk
		self._set_calcguess(None, hopsdrunk)

		for x in hopsdrunk:
			v1 = hdold.get(x, 0)
			v2 = hopsdrunk[x]

			if abs(v1-v2) > 0.01:
				# not stable, try again
				return True

		# we might not be re-called, so store calculated info
		self.hops = allhop
		totmass = _Mass(sum(x.get_amount() for x in allhop))
		self.hopstats = {'mass': totmass, 'ibu' : totibus}

		# result is stable
		return False

	# calculate nutes
	def _donutes(self, w_fermentor):
		nin = self.nutes_in

		bx = float(w_fermentor.strength())
		vol = w_fermentor.volume()

		allnutes = nin[:]
		for ns in allnutes:
			bxarg = bx if Nute.PERBX in ns.cookie else 1.0
			yanarg = 1.0 if Nute.GROSS in ns.cookie else ns.obj.yan
			ns.set_resolverarg((vol, yanarg, bxarg))
			ns.info = (ns.get_amount().valueas(Mass.MG)
			    * ns.obj.yan / vol)

		curyan = sum([x.info for x in allnutes]) * vol

		nr = self.nutes_recipe
		if nr:
			n, t, amt = nr['nute'], nr['time'], nr['value']

			if _ismassvolume(amt):
				amt = self._xvol2x_fromvol(amt, vol)
			if nr['perBx']:
				amt = _Mass(amt*bx)

			needyan = amt.valueas(Mass.MG) - curyan
			if needyan <= 0:
				raise PilotError('too much YAN in recipe')

			mass = Mass(needyan / n.yan, Mass.MG)
			ns = Addition(n, mass, None, t)
			ns.info = needyan / vol
			allnutes.append(ns)
		else:
			needyan = 0

		self.nutes = allnutes
		tot = needyan + curyan
		return {
			'mass'		: tot,
			'masspervol'	: tot / vol,
			'masspervolbx'	: tot / (vol * bx),
		}

	def _dotimers(self):
		# sort the timerable additions
		timers = self.hops + self.nutes + self.opaques + self.water

		# include boiltime fermentables under timers if there's a boil,
		# else include all (think e.g. step-fed meads).
		# XXX: should be user-configurable
		if laterworter(self.firstworter, Worter.POSTBOIL):
			timers += self.fermentables
		else:
			timers += [x for x in self.fermentables
			    if isinstance(x.time, timespec.Boil)]

		timers = sorted(timers, key=lambda x: x.time, reverse=True)

		if (len(timers) > 0
		    and timers[0].time.stagecmp(self.earlyferm) == -1):
			warn('Additions before fermentables.  Check recipe.\n')

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
			sb = Addition(Internal(''), '', None,
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

	def _doboiladj(self, pbwort):
		bvmax = getparam('boilvol_max')
		if bvmax is None:
			return False

		boiltemp = _Temperature(100)
		pbvol = pbwort.volume(boiltemp)
		diff = pbvol - bvmax
		if diff > 0:
			adj = brewutils.water_voltemp_to_mass(diff, boiltemp)
			self._boiladj += adj
			return True
		return False

	def _checkinputs(self):
		if self._final_volume() is None:
			raise PilotError("final volume is not set")

		if len(self.ferms_in) == 0:
			raise PilotError("no fermentables => no brew")

		for x in ['name', 'yeast']:
			if not self.input.get(x, None):
				raise PilotError(x + " is not set")

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

		# check the earlier stage we are calculating for
		s = sorted(self.ferms_in,
		    key=lambda x: x.time, reverse=True)
		assert(len(s) > 0)
		self.earlyferm = s[0].time

		# map the stage from above to a worter
		if isinstance(self.earlyferm, timespec.Package):
			raise PilotError("no fermentation. fix recipe.")
		self.firstworter = {
			Timespec.MASH:		Worter.MASH,
			Timespec.POSTMASH:	Worter.PREBOIL,
			Timespec.KETTLE:	Worter.PREBOIL,
			Timespec.FERMENTOR:	Worter.FERMENTOR,
		}[timespec.timespec2stage[self.earlyferm.__class__]]

		self.mash.preprocess()

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
			# Calculate initial guess for worters, and
			# especially resolve possible percentages into
			# masses.  We use "bymass" in this loop
			# after this call.
			wrt = self._dofermentables_and_worters()

			# if we need to adjust the boil volume, do so
			# until we reach a steady state
			if not laterworter(self.firstworter, Worter.PREBOIL):
				while self._doboiladj(wrt[Worter.PREBOIL]):
					wrt = self._doworters_bymass()

			# hops affect worters due to absorption
			while self._dohops(wrt[Worter.PREBOIL],
			    wrt[Worter.POSTBOIL],
			    wrt[Worter.PACKAGE]):
				wrt = self._doworters_bymass()

			# We need to have hit *at least* the final volume.
			# Additionally, if final strength was specified,
			# we need to hit that too.
			voldiff = self._final_volume() \
			    - wrt[Worter.PACKAGE].volume()

			if self._final_extract() is not None:
				extdiff = self._final_extract() \
				    - wrt[Worter.PACKAGE].extract()
			else:
				extdiff = _Mass(0)

			if abs(voldiff) < 0.01 and abs(extdiff) < 0.1:
				break
			self._set_waterguess(self.waterguess + _Mass(voldiff))
		else:
			raise Exception('recipe failed to converge ... panic?')

		self.results = {}

		if self._extract_bytimespec(Timespec.MASH) > 0.001:
			self._domash(wrt[Worter.MASH])

		#
		# We are committed to the calculated worters.  Set them.
		#
		self.worter = wrt
		self.results['worter'] = self.worter

		if self._boiladj > 0.001:
			assert(not laterworter(self.firstworter,
			    Worter.PREBOIL))
			tf = timespec.Fermentor
			self._opaquestore(Internal, 'WBC boil volume adj.',
			    _Volume(self._boiladj), None,
			    tf(tf.UNDEF, tf.UNDEF))

		self.results['nute_stats']=self._donutes(wrt[Worter.FERMENTOR])
		self._dotimers()

		# calculate kettle & fermentor losses
		rl = {}
		for t,s in [(Timespec.KETTLE, Worter.POSTBOIL),
		    (Timespec.FERMENTOR, Worter.FERMENTOR)]:
			w = Worter()
			w.set_volstrength(self.vol_losses[t],
			    self.worter[s].strength())
			rl[t] = w
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

		if not laterworter(self.firstworter, Worter.PREBOIL):
			# calculate color, via MCU & Morey equation
			t = sum(f.get_amount().valueas(Mass.LB) \
			    * f.obj.color.valueas(Color.LOVIBOND) \
				for f in self.fermentables)
			v = (self.worter[Worter.POSTBOIL].volume()
			    + _Volume(self._boiladj)).valueas(Volume.GALLON)
			mcu = t / v
			self.results['color'] = \
			    Color(1.4922 * pow(mcu, 0.6859), Color.SRM)
		else:
			self.results['color'] = None

		# calculate brewhouse estimated afficiency ... NO, efficiency
		maxext = sum([self._extract_bytimespec(x, theoretical=True)
		    for x in Timespec.stages])
		self.results['brewhouse_efficiency'] = \
		    self.worter[Worter.PACKAGE].extract() / maxext

		# these are easy
		self.results['hops'] = self.hops
		self.results['hop_stats'] = self.hopstats
		self.results['hopsdrunk'] = self.hopsdrunk

		self.results['fermentables'] = self.fermentables

		self.results['total_water'] = Worter(water = self.waterguess)

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

		if len(self.results['hops']) > 0:
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

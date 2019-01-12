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

from WBC import Constants
from WBC import Utils
from WBC.Utils import PilotError
from WBC.Units import Color
from WBC.Getparam import getparam

import copy

class Fermentable:
	def __init__(self, maltster, product, extract, diap, color, needmash,
	    conversion):
		Utils.checktype(color, Color)
		self.maltster = maltster
		self.product = product
		self._setname()

		# compat before all specs have been converted
		if isinstance(extract, Extract):
			self.extract_legacy = False
			self.extract = extract.cgai()
			self.extobj = extract
		else:
			self.extract_legacy = True
			self.extract = extract
			self.extobj = extract # XXX

		# compat before all specs have been converted
		if isinstance(diap, DiaP):
			self.wk = diap.valueas(diap.WK)
			self.diap = diap
		else:
			self.wk = diap
			self.diap = DiaP(diap, DiaP.WK)

		self.color = color
		self.needmash = needmash
		self.conversion = conversion

	def __repr__(self):
		return 'Fermentable object: ' + self.name

	def _setname(self):
		if self.maltster is not None:
			self.name = self.maltster + ' ' + self.product
		else:
			self.name = self.product

fermentables = []

class Extract:
	# extract figure is provided by the maltster as:
	CGDB=		object()		# coarse grind dry basis
	FGDB=		object()		# fine   grind dry basis
	CGAI=		object()		# coarse grind as-is
	FGAI=		object()		# fine   grind as-is

	FCD_UNKNOWN=	object()

	def __init__(self, percent, type, fcd, moisture):
		if percent < 0 or percent > 100:
			raise PilotError('extract percent must be >=0 && <=100')
		self.percent = percent
		self.type = type

		if fcd is self.FCD_UNKNOWN:
			fcd = Constants.fine_coarse_diff
		if fcd < 0 or fcd > 10:
			raise PilotError('invalid fine-coarse difference')

		self.fcd = fcd
		self.moisture = moisture

	# returns extract potential in "coarse grind as-is"
	def cgai(self):
		v = self.percent

		# factor out moisture
		if self.type == self.CGDB or self.type == self.FGDB:
			v *= (1 - self.moisture/100.0)

		# account for fine-coarse difference
		if self.type == self.FGDB or self.type == self.FGAI:
			v *= (1 - self.fcd/100.0)

		return v

	def __str__(self):
		return '{:.1f}%'.format(self.cgai())

# shorthand to reduce typing
CGDB=		 Extract.CGDB
FGDB=		 Extract.FGDB
CGAI=		 Extract.CGAI
FGAI=		 Extract.FGAI
FCD_UNKNOWN=	 Extract.FCD_UNKNOWN

extract_unknown75 = Extract(75, Extract.CGDB, 0, 0)

# diastatic power, accepts either degrees Windisch-Kolbach or Lintner
class DiaP(float):
	WK=	object()
	L=	object()

	def __new__(cls, value, type):
		if type is DiaP.L:
			if value != 0:
				value = value*3.5 + 16
		return super(DiaP, cls).__new__(cls, value)

	def valueas(self, unit):
		if unit is self.WK:
			return self
		elif unit is self.L:
			if self == 0:
				return 0
			else:
				return (self-16) / 3.5
		else:
			raise PilotError('invalid DiaP unit')

	def stras(self, unit):
		if unit is self.WK:
			return '{:.0f}'.format(self.valueas(self.WK)) \
			    + chr(0x00b0) + 'WK'
		elif unit is self.L:
			return '{:.0f}'.format(self.valueas(self.L)) \
			    + chr(0x00b0) + 'Lintner'
		raise PilotError('invalid DiaP unit')

	def __str__(self):
		if self.value == 0:
			return 'none'
		if getparam('units_output') == 'us':
			return self.stras(self.L)
		else:
			return self.stras(self.WK)

diap_none = DiaP(0, DiaP.WK)

# return fermentable or None
def find(name):
	# case-insensitive comparison
	res = [x for x in fermentables if x.name.lower() == name.lower()]
	if len(res) == 0:
		return None
	assert(len(res) == 1)
	return res[0]

# return fermentable or raise error
def get(name):
	f = find(name)
	if f is None:
		raise PilotError("I don't know about fermentable: " + name)
	return f

# return a list of fermentables which match maltster *AND* product
#
# XXX: get(), find() *AND* search()??  maybe we'll get a seek() next?
def search(maltster, product):
	from collections import OrderedDict
	import re

	if maltster is not None:
		l1 = [x for x in fermentables
		    if x.maltster is not None
		     and maltster.lower() in x.maltster.lower()]
	else:
		l1 = fermentables
	if product is not None:
		l2 = [x for x in fermentables
		    if product.lower() in x.product.lower()]
	else:
		l2 = fermentables

	return [x for x in l1 if x in l2]

# used by both "built-in" fermentables and user-added.  User-added
# fermentables override built-in ones with the same name.  The logic
# is to keep user recipes working even if we happen to add a fermentable
# with the same name.
def _scanexisting(name):
	f = find(name)
	if not f is None:
		Utils.warn('fermentable ' + name + ' already exists')
		fermentables.remove(f)

def add(maltster, name, extract, wk, ebc, needmash = True, conversion = True):
	_scanexisting(name)
	fermentables.append(Fermentable(maltster, name, extract, wk, ebc,
	    needmash, conversion))

def alias(maltster, product, toclone):
	c = find(toclone)
	if c is None:
		raise PilotError('trying to alias nonexisting fermentable '
		    + toclone)
	n = copy.copy(c)
	n.maltster = maltster
	n.product = product
	n._setname()
	fermentables.append(n)

##
## "builtin" fermentables
##

EBC=		Color.EBC
LOVIBOND=	Color.LOVIBOND

add('Avangard', 'Pale',
	Extract(80, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(6.5, EBC))
add('Avangard', 'Pilsner',
	Extract(81, FGDB, 2.0, 4.5),
	DiaP(220, DiaP.WK),
	Color(3.25, EBC))
add('Avangard', 'Vienna',
	Extract(80, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(11, EBC))
add('Avangard', 'Munich light',
	Extract(80.5, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(18.5, EBC))
add('Avangard', 'Munich dark',
	Extract(80.5, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(30, EBC))
add('Avangard', 'Wheat',
	Extract(83, FGDB, 2.0, 5.0),
	DiaP(150, DiaP.WK),
	Color(4.5, EBC))

add('Briess', 'Pale',
	Extract(78.5, CGDB, 1.5, 4.0),
	DiaP(85, DiaP.L),
	Color(3.5, LOVIBOND))
add('Briess', 'Aromatic Munich 20 L',
	Extract(77.0, FGDB, FCD_UNKNOWN, 2.5),
	DiaP(20, DiaP.L),
	Color(20, LOVIBOND))
add('Briess', 'Victory',
	Extract(75.0, FGDB, FCD_UNKNOWN, 2.5),
	diap_none,
	Color(28, LOVIBOND))

add('Briess', 'Carapils',
	Extract(75.0, FGDB, FCD_UNKNOWN, 6.5),
	diap_none,
	Color(1.5, LOVIBOND),
	needmash = False)

add('Briess', 'Caramel 20 L',
	Extract(76.0, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(20, LOVIBOND),
	needmash = False)
add('Briess', 'Caramel 40 L',
	Extract(77.0, FGDB, FCD_UNKNOWN, 5.5),
	diap_none,
	Color(40, LOVIBOND),
	needmash = False)
add('Briess', 'Caramel 60 L',
	Extract(77.0, FGDB, FCD_UNKNOWN, 5.0),
	diap_none,
	Color(60, LOVIBOND),
	needmash = False)
add('Briess', 'Caramel 80 L',
	Extract(76.0, FGDB, FCD_UNKNOWN, 4.5),
	diap_none,
	Color(80, LOVIBOND),
	needmash = False)
add('Briess', 'Caramel 120 L',
	Extract(75.0, FGDB, FCD_UNKNOWN, 3.0),
	diap_none,
	Color(120, LOVIBOND),
	needmash = False)

# XXX: couldn't find any indication of the extract yield for
# Briess Blackprinz or Midnight Wheat, not from the Briess site or
# anywhere else for that matter.  Guessing 50% -- it's going to be
# max 50 %-units wrong ;)
# (and in all likelyhood it's in the 50-70 range ...)
add('Briess', 'Blackprinz',
	Extract(50.0, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(500, LOVIBOND),
	needmash = False)
add('Briess', 'Midnight Wheat',
	Extract(50.0, FGDB, FCD_UNKNOWN, 6.5),
	diap_none,
	Color(550, LOVIBOND),
	needmash = False)

# Briess generic smoked malt (any of beech / cherry / mesquite)
# XXX: not sure diastatic power is correct (specs do say 140 degL)
add('Briess', 'smoked', 80.5, DiaP(90, DiaP.L), Color(14.5, EBC))

# Crisp
add('Crisp', 'Maris Otter', 81.5, 150, Color(3.5, EBC))
# well, as usual, can't find this on the maltsters page, but pretty much
# all vendors agree that it's 200-250 Lovibond, so I guess mostly correct
add('Crisp', 'Pale Chocolate', 77, 0, Color(600, EBC), needmash = False)

# have to guestimate the extract yield based on random
# internet sources.  seems like Crisp doesn't want to tell us.
# guess we should be thankful that they at least tell the color
# and moisture content.
add('Crisp', 'Brown',
	Extract(70.0, FGDB, FCD_UNKNOWN, 2.0),
	diap_none,
	Color(135, EBC))
add('Crisp', 'Roasted barley',
	Extract(70.0, FGDB, FCD_UNKNOWN, 2.0),
	diap_none,
	Color(1350, EBC),
	needmash = False)
# help legacy recipes for now
alias(None, 'Roasted Barley', 'Crisp Roasted Barley')

# XXX: probably better diastatic power, but can't figure it out
# from the datasheet at:
# http://dingemansmout.be/sites/dingemansmout.be/files/downloads/ALE_MD_0.pdf
add('Dingemans', 'Pale',
	Extract(80, FGDB, 2.0, 4.5),
	Constants.minconversion,
	Color(9, EBC))
add('Dingemans', 'Cara 120',
	Extract(74, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(120, EBC),
	needmash = False)
alias('Dingemans', 'Cara 45 L', 'Dingemans Cara 120')
add('Dingemans', 'Special B',
	Extract(72, FGDB, FCD_UNKNOWN, 5.0),
	diap_none,
	Color(310, EBC),
	needmash = False)

# found a data sheet with 81% extract min for fine grind, so
# guessing the coarse grind from that.
# you're not going to use this for a significant amount of the grainbill,
# even if the guess is a bit wrong, not the end of the world.
add('Meussdoerffer', 'Sour Malt',
	extract_unknown75,
	diap_none,
	Color(2, LOVIBOND))

# Muntons is so convenient that I have to guess half and stich the
# rest together from two sources:
# http://www.muntonsmicrobrewing.com/wp-content/uploads/2018/04/171122-Craft-Brewer-Guide-October-2017_stg-5_email.pdf
# http://www.muntonsmicrobrewing.com/products/typical-analysis/
add('Muntons', 'Black Malt',
	Extract(60, FGDB, FCD_UNKNOWN, 5.0),
	diap_none,
	Color(1300, EBC),
	needmash = False)
add('Muntons', 'Chocolate',
	Extract(65.5, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(1100, EBC),
	needmash = False)
add('Muntons', 'Crystal 150 EBC',
	Extract(75, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(150, EBC),
	needmash = False)
alias('Muntons', 'Crystal 60 L', 'Muntons Crystal 150 EBC')
add('Muntons', 'Maris Otter',
	Extract(81.5, FGDB, FCD_UNKNOWN, 3.0),
	DiaP(156, DiaP.WK),
	Color(5.8, EBC))

add('Simpsons', 'Golden Promise', 81, 140, Color(6.5, EBC))

add('Simpsons', 'Brown',
	Extract(68.7, FGDB, FCD_UNKNOWN, 4.0),
	diap_none,
	Color(515, EBC))

add('Simpsons', 'Crystal Dark',
	Extract(69.0, FGDB, FCD_UNKNOWN, 5.0),
	diap_none,
	Color(267.5, EBC),
	needmash = False)

# Hats off to Thomas Fawcett & Sons for having useful data sheets
# easily available.  I wish all maltsters were like them.  They even
# have everything in IoB, ASBC and EBC numbers!
# http://www.fawcett-maltsters.co.uk/spec.html
# (well, ok, they don't apparently supply the diastatic power, but
# until we hit base malts for them, doesn't really matter)
add('Fawcett', 'Brown',
	Extract(70, CGAI, FCD_UNKNOWN, 4.5),
	diap_none,
	Color(188, EBC))

# well, ok, Fawcett apparently has different malts for different regions.
# or at least there doesn't seem to be a naming consistency, plus the
# specs don't match exactly.  so, yea, hats back on.
add('Fawcett', 'Crystal I',
	Extract(70, FGAI, FCD_UNKNOWN, 4.5),
	diap_none,
	Color(45, LOVIBOND),
	needmash = False)
add('Fawcett', 'Crystal II',
	Extract(70, FGAI, FCD_UNKNOWN, 4.5),
	diap_none,
	Color(65, LOVIBOND),
	needmash = False)

# XXX: no idea about the extract, but since it's supposed just regular
# pale malt with lactic acid, we'll go with 75%.  it's not used in such
# high amounts that it should matter if we're off even by 50%
add('Weyermann', 'Acidulated Malt', 75, 0, Color(4.5, EBC))

add('Weyermann', 'CaraFoam',
	Extract(77.0, FGDB, FCD_UNKNOWN, 5.5),
	diap_none,
	Color(5, EBC),
	needmash = False)
add('Weyermann', 'CaraHell',
	Extract(77.0, FGDB, FCD_UNKNOWN, 7.0),
	diap_none,
	Color(25, EBC),
	needmash = False)
add('Weyermann', 'CaraRed',
	Extract(76.0, FGDB, FCD_UNKNOWN, 6.0),
	diap_none,
	Color(50, EBC),
	needmash = False)
add('Weyermann', 'CaraAroma',
	Extract(76.9, FGDB, FCD_UNKNOWN, 5.8),
	diap_none,
	Color(300, EBC),
	needmash = False)
add('Weyermann', 'CaraMunich 1',
	Extract(76.4, FGDB, FCD_UNKNOWN, 5.8),
	diap_none,
	Color(90, EBC),
	needmash = False)
add('Weyermann', 'CaraMunich 2',
	Extract(76.2, FGDB, FCD_UNKNOWN, 5.8),
	diap_none,
	Color(130, EBC),
	needmash = False)
add('Weyermann', 'CaraMunich 3',
	Extract(76.1, FGDB, FCD_UNKNOWN, 5.8),
	diap_none,
	Color(160, EBC),
	needmash = False)

add('Weyermann', 'Melanoidin',
	Extract(76.5, FGDB, FCD_UNKNOWN, 4.3),
	diap_none,
	Color(70, EBC))

# XXX: couldn't find diastatic power, so we'll just guess
# (it's self-convering for sure, so err on the low side,
# most likely is way too low)
add('Weyermann', 'Munich I',
	Extract(77.4, FGAI, FCD_UNKNOWN, 4.1),
	Constants.minconversion,
	Color(16, EBC))

add('Weyermann', 'Chocolate Rye',
	Extract(65, FGDB, FCD_UNKNOWN, 4.0),
	diap_none,
	Color(600, EBC),
	needmash = False)

add('Weyermann', 'Pale Rye',
	Extract(77, FGAI, FCD_UNKNOWN, 5.0),
	Constants.minconversion,
	Color(5, EBC))

# extract is an "average" of the lot analysis numbers
add('Weyermann', 'Carafa 1',
	Extract(70, FGAI, FCD_UNKNOWN, 3.8),
	diap_none,
	Color(900, EBC),
	needmash = False)
add('Weyermann', 'Carafa 2',
	Extract(70, FGAI, FCD_UNKNOWN, 3.8),
	diap_none,
	Color(1150, EBC),
	needmash = False)
add('Weyermann', 'Carafa 3',
	Extract(70, FGAI, FCD_UNKNOWN, 3.8),
	diap_none,
	Color(1400, EBC),
	needmash = False)
# the special versions of Carafa have the same extract/color
# specifications, so we can alias them
# (and they have completely different flavor, so we *must* alias them!)
alias('Weyermann', 'Carafa 1 Special', 'Weyermann Carafa 1')
alias('Weyermann', 'Carafa 2 Special', 'Weyermann Carafa 2')
alias('Weyermann', 'Carafa 3 Special', 'Weyermann Carafa 3')

# Extract yields for non-malts from 'How To Brew' [Palmer]
# Moisture content from BSG website
add(None, 'Flaked wheat',
	Extract(77, CGDB, FCD_UNKNOWN, 7.0),
	diap_none,
	Color(1, LOVIBOND))
add(None, 'Flaked oats',
	Extract(70, CGDB, FCD_UNKNOWN, 8.0),
	diap_none,
	Color(1, LOVIBOND))

# guess and assume
add(None, 'Flaked rye',
	Extract(70, CGDB, FCD_UNKNOWN, 12),
	diap_none,
	Color(3, LOVIBOND))

# just a guess, really (based on some random literature pieces)
add(None, 'Rice', 70, 0, Color(1, EBC))

# sugars ("self-converting")
add(None, 'Table sugar',
	Extract(100, CGDB, FCD_UNKNOWN, 0),
	Constants.minconversion,
	Color(0, EBC),
	conversion = False,
	needmash = False)

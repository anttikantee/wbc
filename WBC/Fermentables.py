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

import Constants
import Utils
from Units import Color

import copy

class Fermentable:
	def __init__(self, name, extract, diap, color, conversion):
		Utils.checktype(color, Color)
		self.name = name

		# compat before all specs have been converted
		if isinstance(extract, Extract):
			self.extract_legacy = False
			self.extract = extract.cgai()
		else:
			self.extract_legacy = True
			self.extract = extract

		# compat before all specs have been converted
		if isinstance(diap, DiaP):
			self.wk = diap.wk()
		else:
			self.wk = diap

		self.color = color
		self.conversion = conversion
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

# shorthand to reduce typing
CGDB=		 Extract.CGDB
FGDB=		 Extract.FGDB
CGAI=		 Extract.CGAI
FGAI=		 Extract.FGAI
FCD_UNKNOWN=	 Extract.FCD_UNKNOWN

extract_unknown75 = Extract(75, Extract.CGDB, 0, 0)

# diastatic power, accepts either degrees Windisch-Kolbach or Lintner
class DiaP:
	WK=	object()
	L=	object()

	def __init__(self, value, type):
		self.value = value
		self.type = type

	def wk(self):
		v = self.value
		if self.type == self.L:
			v = 3.5*v - 16
		return v

diap_none = DiaP(0, DiaP.WK)

# return fermentable or None
def find(name):
	res = filter(lambda x: x.name.lower() == name.lower(), fermentables)
	if len(res) == 0:
		return None
	assert(len(res) == 1)
	return res[0]

# return fermentable or raise error
def get(name):
	# do case-insensitive comparison
	f = find(name)
	if f is None:
		raise PilotError("I don't know about fermentable: " + name)

	# return "official" leetcapsed name
	return (name, f)

# used by both "built-in" fermentables and user-added.  User-added
# fermentables override built-in ones with the same name.  The logic
# is to keep user recipes working even if we happen to add a fermentable
# with the same name.
def _scanexisting(name):
	f = find(name)
	if not f is None:
		Utils.warn('fermentable ' + name + ' already exists')
		fermentables.remove(f)

def add(name, extract, wk, ebc, conversion = True):
	_scanexisting(name)
	fermentables.append(Fermentable(name, extract, wk, ebc, conversion))

def alias(name, toclone):
	c = find(toclone)
	if c is None:
		raise PilotError('trying to alias nonexisting fermentable '
		    + toclone)
	n = copy.copy(c)
	n.name = name
	fermentables.append(n)

##
## "builtin" fermentables
##

EBC=		Color.EBC
LOVIBOND=	Color.LOVIBOND

add('Avangard Pale',
	Extract(80, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(6.5, EBC))
add('Avangard Pilsner',
	Extract(81, FGDB, 2.0, 4.5),
	DiaP(220, DiaP.WK),
	Color(3.25, EBC))
add('Avangard Vienna',
	Extract(80.5, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(11, EBC))
add('Avangard Munich light',
	Extract(80.5, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(18.5, EBC))
add('Avangard Munich dark',
	Extract(80.5, FGDB, 2.0, 4.5),
	DiaP(200, DiaP.WK),
	Color(30, EBC))
add('Avangard Wheat',
	Extract(83, FGDB, 2.0, 5.0),
	DiaP(150, DiaP.WK),
	Color(4.5, EBC))

add('Briess pale', 78.5, 264, Color(7.8, EBC))
# Briess generic smoked malt (any of beech / cherry / mesquite)
# XXX: not sure diastatic power is correct (specs do say 140 degL)
add('Briess smoked', 80.5, 474, Color(14.5, EBC))

# Crisp
add('Crisp Maris Otter', 81.5, 150, Color(3.5, EBC))
# well, as usual, can't find this on the maltsters page, but pretty much
# all vendors agree that it's 200-250 Lovibond, so I guess mostly correct
add('Crisp Pale Chocolate', 77, 0, Color(600, EBC))

# XXX: probably better diastatic power, but can't figure it out
# from the datasheet at:
# http://dingemansmout.be/sites/dingemansmout.be/files/downloads/ALE_MD_0.pdf
add('Dingemans Pale',
	Extract(80, FGDB, 2.0, 4.5),
	Constants.minconversion,
	Color(9, EBC))

add('Dingemans Special B',
	Extract(72, FGDB, FCD_UNKNOWN, 5.0),
	diap_none,
	Color(310, EBC))

# found a data sheet with 81% extract min for fine grind, so
# guessing the coarse grind from that.
# you're not going to use this for a significant amount of the grainbill,
# even if the guess is a bit wrong, not the end of the world.
add('Meussdoerffer Sour Malt',
	extract_unknown75,
	diap_none,
	Color(2, LOVIBOND))

# XXX: extract correct?
add('Muntons Chocolate', 67, 0, Color(1000, EBC))
add('Muntons Crystal 150 EBC', 67, 0, Color(150, EBC))
alias('Muntons Crystal 60 L', 'Muntons Crystal 150 EBC')
add('Muntons Black Malt', 67, 0, Color(1300, EBC))

# XXX: I was utterly unable to find a datasheet for whatever Muntons
# "Whole Pale Malt Marris Otter" is.  So I'm just guessing it's
# more or less "ale malt" from muntons.com
add('Muntons Maris Otter', 81.5, 156, Color(5.8, EBC))

add('Simpsons Golden Promise', 81, 140, Color(6.5, EBC))

# Hats off to Thomas Fawcett & Sons for having useful data sheets
# easily available.  I wish all maltsters were like them.  They even
# have everything in IoB, ASBC and EBC numbers!
# http://www.fawcett-maltsters.co.uk/spec.html
# (well, ok, they don't apparently supply the diastatic power, but
# until we hit base malts for them, doesn't really matter)
add('Fawcett Brown', 70, 0, Color(188, EBC))

# XXX: no idea about the extract, but since it's supposed just regular
# pale malt with lactic acid, we'll go with 75%.  it's not used in such
# high amounts that it should matter if we're off even by 50%
add('Weyermann Acidulated Malt', 75, 0, Color(4.5, EBC))

add('Weyermann CaraAroma', 74, 0, Color(350, EBC))
add('Weyermann CaraMunich 1', 75, 0, Color(90, EBC))
add('Weyermann CaraMunich 3', 76, 0, Color(150, EBC))

add('Weyermann Melanoidin', 75, 0, Color(70, EBC))

# XXX: couldn't find diastatic power, so we'll just guess
# (it's self-convering for sure, so err on the low side,
# most likely is way too low)
add('Weyermann Munich I',
	Extract(77.4, FGAI, FCD_UNKNOWN, 4.1),
	Constants.minconversion,
	Color(16, EBC))

add('Weyermann Chocolate Rye', 65, 0, Color(600, EBC))

# I'm starting to hate listing malts.  It's a complete crapshoot
# between what the maltster provides and what vendors provide
add('Weyermann Pale Rye', 81, Constants.minconversion, Color(7, EBC))

# XXX: extract correct?
add('Weyermann Carafa 2', 70, 0, Color(1100, EBC))

# extract yields for non-malts (from 'How To Brew' [Palmer])
add('Flaked wheat', 77, 0, Color(0, EBC))
add('Flaked oats', 70, 0, Color(0, EBC))
add('Roasted barley', 55, 0, Color(1400, EBC))

# guess and assume
add('Flaked rye',
	Extract(70, CGDB, FCD_UNKNOWN, 12),
	diap_none,
	Color(3, LOVIBOND))

# just a guess, really (based on some random literature pieces)
add('Rice', 70, 0, Color(1, EBC))

# sugars ("self-converting")
add('Table sugar', 100, Constants.minconversion, Color(0, EBC), False)

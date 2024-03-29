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

from WBC import constants
from WBC import utils
from WBC.utils import PilotError
from WBC.units import Color, Strength
from WBC.getparam import getparam

import copy

class Fermentable:
	SOLID=	'solid'
	LIQUID=	'liquid'

	def __init__(self, maltster, product, extract, color, conversion):
		utils.checktype(color, Color)
		self.maltster = maltster
		self.product = product
		self._setname()

		assert(isinstance(extract, Extract))
		self.extract = extract

		self.color = color
		self.conversion = conversion

	def __repr__(self):
		return 'Fermentable object: ' + self.name

	def _setname(self):
		if self.maltster is not None:
			self.name = self.maltster + ' ' + self.product
		else:
			self.name = self.product

	def type(self):
		return {
		    Solid: self.SOLID,
		    Liquid: self.LIQUID
		}[self.extract.__class__]

	def namestr(self, maxlen):
		return self.name

	def infostr(self, maxlen, info):
		return ''

fermentables = []

# convert the very friendly l*deg/kg to extract %
# Since 1.001 SG is 0.257% extract by mass (*), the percentage of extract:
#   extract = 0.00257 * (1.001 * ldegkg) * 100.0
# *) https://www.asbcnet.org/Methods/Tools/Tables/Documents/TableWortBeerBrewingSugars.pdf
def HWE2ext(ldegkg):
	return 0.257 * 1.001 * ldegkg

class Extract:
	def cgai(self):
		return self.extract

	# XXX: not extract.  big revamp coming soon to a repo near you
	def moisture(self):
		return self._moisture

	def __str__(self):
		return '{:.1f}%'.format(self.cgai())

class Solid(Extract):
	# extract figure is provided by the maltster as:
	CGDB=		object()		# coarse grind dry basis
	FGDB=		object()		# fine   grind dry basis
	CGAI=		object()		# coarse grind as-is
	FGAI=		object()		# fine   grind as-is

	FCD_UNKNOWN=	object()

	def __init__(self, percent, type, fcd, moisture):
		if percent < 0 or percent > 100:
			raise PilotError('extract percent must be >=0 && <=100')
		self.type = type

		if ((type == self.FGDB or type == self.FGAI)
		    and moisture + percent > 100):
			raise PilotError('fermentable contains > 100%')

		if fcd is self.FCD_UNKNOWN:
			fcd = constants.fine_coarse_diff
		if fcd < 0 or fcd > 10:
			raise PilotError('invalid fine-coarse difference')

		self.fcd = fcd
		self._moisture = moisture

		# calculate extract coarse grind as-is
		#
		# factor out moisture
		if type == self.CGDB or type == self.FGDB:
			percent *= (1 - self._moisture/100.0)

		# account for fine-coarse difference
		if type == self.FGDB or type == self.FGAI:
			percent -= self.fcd

		self.extract = percent

class Liquid(Extract):
	def __init__(self, strength):
		self._moisture = 100 - strength
		self.extract = strength

# shorthand to reduce typing
CGDB=		 Solid.CGDB
FGDB=		 Solid.FGDB
CGAI=		 Solid.CGAI
FGAI=		 Solid.FGAI
FCD_UNKNOWN=	 Solid.FCD_UNKNOWN

extract_unknown75 = Solid(75, Solid.CGDB, 0, 0)

# return fermentable or None
def Find(name):
	# case-insensitive comparison
	res = [x for x in fermentables if x.name.lower() == name.lower()]
	if len(res) == 0:
		return None
	assert(len(res) == 1)
	return res[0]

# return fermentable or raise error
def Get(name):
	f = Find(name)
	if f is None:
		raise PilotError("I don't know about fermentable: " + name)
	return f

# return a list of fermentables which match maltster *AND* product
#
# XXX: get(), find() *AND* search()??  maybe we'll get a seek() next?
def Search(maltster, product):
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
	f = Find(name)
	if not f is None:
		Utils.warn('fermentable ' + name + ' already exists')
		fermentables.Remove(f)

def Add(maltster, name, extract, ebc, conversion = True):
	_scanexisting(name)
	fermentables.append(Fermentable(maltster, name, extract, ebc,
	    conversion))

def Alias(maltster, product, toclone):
	c = Find(toclone)
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

Add('Avangard', 'Pale',
	Solid(80, FGDB, 2.0, 4.5),
	Color(6.5, EBC))
Add('Avangard', 'Pilsner',
	Solid(81, FGDB, 2.0, 4.5),
	Color(3.25, EBC))
Add('Avangard', 'Vienna',
	Solid(80, FGDB, 2.0, 4.5),
	Color(11, EBC))
Add('Avangard', 'Munich light',
	Solid(80.5, FGDB, 2.0, 4.5),
	Color(18.5, EBC))
Add('Avangard', 'Munich dark',
	Solid(80.5, FGDB, 2.0, 4.5),
	Color(30, EBC))
Add('Avangard', 'Wheat',
	Solid(83, FGDB, 2.0, 5.0),
	Color(4.5, EBC))

#
# Bilgram
#
Add('Bilgram', 'Pilsner',
	Solid(82.80, FGDB, 1.5, 3.9),
	Color(4, EBC))

#
# Brewferm
#

# XXX: specs do not say if extract is for coarse or fine ground,
# only that it's for dry basis
Add('Brewferm', 'Biscuit',
	Solid(77, FGDB, FCD_UNKNOWN, 4.7),
	Color(50, EBC))

Add('Briess', 'Pale',
	Solid(78.5, CGDB, 1.5, 4.0),
	Color(3.5, LOVIBOND))
Add('Briess', 'Aromatic Munich 20 L',
	Solid(77.0, FGDB, FCD_UNKNOWN, 2.5),
	Color(20, LOVIBOND))
Add('Briess', 'Victory',
	Solid(75.0, FGDB, FCD_UNKNOWN, 2.5),
	Color(28, LOVIBOND))

Add('Briess', 'Carapils',
	Solid(75.0, FGDB, FCD_UNKNOWN, 6.5),
	Color(1.5, LOVIBOND))

Add('Briess', 'Caramel 20 L',
	Solid(76.0, FGDB, FCD_UNKNOWN, 6.0),
	Color(20, LOVIBOND))
Add('Briess', 'Caramel 40 L',
	Solid(77.0, FGDB, FCD_UNKNOWN, 5.5),
	Color(40, LOVIBOND))
Add('Briess', 'Caramel 60 L',
	Solid(77.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(60, LOVIBOND))
Add('Briess', 'Caramel 80 L',
	Solid(76.0, FGDB, FCD_UNKNOWN, 4.5),
	Color(80, LOVIBOND))
Add('Briess', 'Caramel 120 L',
	Solid(75.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(120, LOVIBOND))

# XXX: couldn't find any indication of the extract yield for
# Briess Blackprinz or Midnight Wheat, not from the Briess site or
# anywhere else for that matter.  Guessing 50% -- it's going to be
# max 50 %-units wrong ;)
# (and in all likelyhood it's in the 50-70 range ...)
Add('Briess', 'Blackprinz',
	Solid(50.0, FGDB, FCD_UNKNOWN, 6.0),
	Color(500, LOVIBOND))
Add('Briess', 'Midnight Wheat',
	Solid(50.0, FGDB, FCD_UNKNOWN, 6.5),
	Color(550, LOVIBOND))

# Briess generic smoked malt (any of beech / cherry / mesquite)
Add('Briess', 'apple wood smoked',
	Solid(80.5, FGDB, FCD_UNKNOWN, 6.0),
	Color(5, LOVIBOND))
Alias('Briess', 'cherry wood smoked', 'Briess apple wood smoked')
Alias('Briess', 'mesquite smoked', 'Briess apple wood smoked')

# Castle
Add('Castle', 'Black',
	Solid(73.0, FGDB, FCD_UNKNOWN, 4.5),
	Color(1275, EBC))

# Crisp
Add('Crisp', 'Maris Otter',
	Solid(82.0, FGDB, FCD_UNKNOWN, 3.5),
	Color(3.0, LOVIBOND))
# well, as usual, can't find this on the maltsters page, but pretty much
# all vendors agree that it's 200-250 Lovibond, so I guess mostly correct
Add('Crisp', 'Pale Chocolate',
	Solid(77.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(225, LOVIBOND))

# have to guestimate the extract yield based on random
# internet sources.  seems like Crisp doesn't want to tell us.
# guess we should be thankful that they at least tell the color
# and moisture content.
Add('Crisp', 'Black Malt',
	Solid(75.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(600, LOVIBOND))
Add('Crisp', 'Brown',
	Solid(70.0, FGDB, FCD_UNKNOWN, 2.0),
	Color(135, EBC))
Add('Crisp', 'Roasted barley',
	Solid(70.0, FGDB, FCD_UNKNOWN, 2.0),
	Color(1350, EBC))

Add('Crisp', 'Chocolate',
	Solid(71.0, FGDB, FCD_UNKNOWN, 3.5),
	Color(650, LOVIBOND))

# http://dingemansmout.be/sites/dingemansmout.be/files/downloads/ALE_MD_0.pdf
Add('Dingemans', 'Pale',
	Solid(80, FGDB, 2.0, 4.5),
	Color(9, EBC))
Add('Dingemans', 'Cara 120',
	Solid(74, FGDB, FCD_UNKNOWN, 6.0),
	Color(120, EBC))
Alias('Dingemans', 'Cara 45 L', 'Dingemans Cara 120')
Add('Dingemans', 'Special B',
	Solid(72, FGDB, FCD_UNKNOWN, 5.0),
	Color(310, EBC))

# malzandmore.de
Add('Hausladen', 'Pilsner',
	Solid(82.3, FGDB, 1.8, 4.5),
	Color(2.9, EBC))

# found a data sheet with 81% extract min for fine grind, so
# guessing the coarse grind from that.
# you're not going to use this for a significant amount of the grainbill,
# even if the guess is a bit wrong, not the end of the world.
Add('Meussdoerffer', 'Sour Malt',
	extract_unknown75,
	Color(2, LOVIBOND))

# Muntons is so convenient that I have to guess half and stich the
# rest together from two sources:
# http://www.muntonsmicrobrewing.com/wp-content/uploads/2018/04/171122-Craft-Brewer-Guide-October-2017_stg-5_email.pdf
# http://www.muntonsmicrobrewing.com/products/typical-analysis/
Add('Muntons', 'Black Malt',
	Solid(60, FGDB, FCD_UNKNOWN, 5.0),
	Color(1300, EBC))
Add('Muntons', 'Chocolate',
	Solid(65.5, FGDB, FCD_UNKNOWN, 6.0),
	Color(1100, EBC))
Add('Muntons', 'Crystal 150 EBC',
	Solid(75, FGDB, FCD_UNKNOWN, 6.0),
	Color(150, EBC))
Alias('Muntons', 'Crystal 60 L', 'Muntons Crystal 150 EBC')

# Maris Otters from:
# https://www.muntons.com/wp-content/uploads/2020/11/Muntons-Brewers-Guide.pdf
#
# per mill gap 0.7mm = coarse & 0.2mm = fine, the values in the
# document (dwt) are CGDB
Add('Muntons', 'Maris Otter Pale',
	Solid(HWE2ext(308), CGDB, FCD_UNKNOWN, 4.0),
	Color(5, EBC))
Add('Muntons', 'Maris Otter Extra Pale',
	Solid(HWE2ext(310), CGDB, FCD_UNKNOWN, 5.0),
	Color(4, EBC))
Add('Muntons', 'Maris Otter Pale Blend',
	Solid(HWE2ext(308), CGDB, FCD_UNKNOWN, 4.0),
	Color(5, EBC))

# Muntons DME ("spraymalt") apparently has the specs only on the
# bag.  "yay".  I'll add more as I find more.
#
# This one says "protein 7-5% maximum", probably in the spirit of
# US timestamps.  Ummmm, ok.  Anyway, assume that everything that
# was in the dry malt is soluble extract or moisture.
Add('Muntons', 'Spraymalt Light',
	Solid(100, CGDB, FCD_UNKNOWN, 5.0),
	Color(12, EBC))

#
# Rhoenmalz
#
Add('Rhoenmalz', 'Pilsner',
	Solid(80.5, FGDB, 1.5, 4.25),
	Color(3.3, EBC))

Add('Simpsons', 'Golden Promise',
	Solid(81, FGDB, FCD_UNKNOWN, 3.7),
	Color(6.5, EBC))

Add('Simpsons', 'Amber',
	Solid(69, FGDB, FCD_UNKNOWN, 5.0),
	Color(62, EBC))
Add('Simpsons', 'Brown',
	Solid(68.7, FGDB, FCD_UNKNOWN, 4.0),
	Color(450, EBC))

Add('Simpsons', 'Aromatic',
	Solid(70, FGDB, FCD_UNKNOWN, 5.0),
	Color(60, EBC))

Add('Simpsons', 'Caramalt',
	Solid(71.0, FGDB, FCD_UNKNOWN, 7.5),
	Color(36, EBC))
Add('Simpsons', 'Premium English Caramalt',
	Solid(71.0, FGDB, FCD_UNKNOWN, 3.5),
	Color(60, EBC))

Add('Simpsons', 'Crystal Light',
	Solid(69.0, FGDB, FCD_UNKNOWN, 6.0),
	Color(104, EBC))
Add('Simpsons', 'Crystal T50',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(137.5, EBC))
Add('Simpsons', 'Crystal Medium',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(178.5, EBC))
Add('Simpsons', 'Crystal Dark',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(267.5, EBC))
Add('Simpsons', 'Crystal Extra Dark',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(475, EBC))

Add('Simpsons', 'Heritage Crystal Malt',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(178.5, EBC))
Add('Simpsons', 'Double Roasted Crystal',
	Solid(69.0, FGDB, FCD_UNKNOWN, 5.0),
	Color(300, EBC))

Add('Simpsons', 'Pale Chocolate',
	Solid(68.7, FGDB, FCD_UNKNOWN, 4.0),
	Color(225, EBC))
Add('Simpsons', 'Chocolate',
	Solid(69.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(1180, EBC))
Add('Simpsons', 'Roasted Barley',
	Solid(62.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(1600, EBC))
Add('Simpsons', 'Black',
	Solid(69.0, FGDB, FCD_UNKNOWN, 3.0),
	Color(1650, EBC))

# Hats off to Thomas Fawcett & Sons for having useful data sheets
# easily available.  I wish all maltsters were like them.  They even
# have everything in IoB, ASBC and EBC numbers!
# http://www.fawcett-maltsters.co.uk/spec.html

# well, ok, Fawcett apparently has different malts for different regions.
# or at least there doesn't seem to be a naming consistency, plus the
# specs don't match exactly.  so, yea, hats back on.
Add('Fawcett', 'Crystal I',
	Solid(70, FGAI, FCD_UNKNOWN, 4.5),
	Color(45, LOVIBOND))
Add('Fawcett', 'Crystal II',
	Solid(70, FGAI, FCD_UNKNOWN, 4.5),
	Color(65, LOVIBOND))

Add('Fawcett', 'Pale Crystal',
	Solid(70, CGAI, FCD_UNKNOWN, 6.5),
	Color(75, EBC))
Add('Fawcett', 'Crystal',
	Solid(70, CGAI, FCD_UNKNOWN, 5.0),
	Color(162, EBC))
Add('Fawcett', 'Dark Crystal',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(300, EBC))
Add('Fawcett', 'Red Crystal',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(400, EBC))

Add('Fawcett', 'Amber',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(125, EBC))
Add('Fawcett', 'Brown',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(188, EBC))
Add('Fawcett', 'Pale Chocolate',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(625, EBC))
Add('Fawcett', 'Chocolate',
	Solid(70, CGAI, FCD_UNKNOWN, 4.5),
	Color(1175, EBC))
Add('Fawcett', 'Roasted Barley',
	Solid(68.5, CGAI, FCD_UNKNOWN, 4.5),
	Color(1450, EBC))


# I guess "The Swaen", strictly speaking, is the maltster, but I'll
# list these under the brandnames only, since I don't want to start
# doing 'The Swaen Goldswaen Red'
#
# http://theswaen.com/ourproducts-malt-for-beer/
Add('Swaen', 'Ale',
	Solid(81, FGDB, FCD_UNKNOWN, 4.5),
	Color(7.5, EBC))
Add('Swaen', 'Lager',
	Solid(81, FGDB, FCD_UNKNOWN, 4.5),
	Color(3.5, EBC))
Add('Swaen', 'Munich Dark',
	Solid(80, FGDB, FCD_UNKNOWN, 4.5),
	Color(20, EBC))
Add('Swaen', 'Munich Light',
	Solid(80, FGDB, FCD_UNKNOWN, 4.6),
	Color(13.5, EBC))
Add('Swaen', 'Pilsner',
	Solid(81, FGDB, FCD_UNKNOWN, 4.5),
	Color(3.75, EBC))
Add('Swaen', 'Vienna',
	Solid(80, FGDB, FCD_UNKNOWN, 4.5),
	Color(10.5, EBC))

Add('Goldswaen', 'Red',
	Solid(78, FGDB, FCD_UNKNOWN, 7.0),
	Color(50, EBC))

Add('Viking', 'Oat Malt',
	Solid(58, FGDB, FCD_UNKNOWN, 7.0), # double-checked 58
	Color(4.5, EBC))
Add('Viking', 'Rye Malt',
	Solid(81, FGDB, FCD_UNKNOWN, 6.0),
	Color(7.0, EBC))
Add('Viking', 'Wheat Malt',
	Solid(82, FGDB, FCD_UNKNOWN, 6.0),
	Color(4.2, EBC))

# XXX: Weyermann doesn't list acidulated malt extract, but since it's
# supposed just regular pale malt with lactic acid, we'll go with 75%.
# it's not used in such high amounts that it should matter if we're off
# even by 50%
Add('Weyermann', 'Acidulated Malt',
	Solid(75, FGDB, FCD_UNKNOWN, 6.0),
	Color(4.5, EBC))
Alias('Weyermann', 'Sauermalz', 'Weyermann Acidulated Malt')

Add('Weyermann', 'CaraFoam',
	Solid(77.0, FGDB, FCD_UNKNOWN, 5.5),
	Color(5, EBC))
Add('Weyermann', 'CaraHell',
	Solid(77.0, FGDB, FCD_UNKNOWN, 7.0),
	Color(25, EBC))
Add('Weyermann', 'CaraRed',
	Solid(76.0, FGDB, FCD_UNKNOWN, 6.0),
	Color(50, EBC))
Add('Weyermann', 'CaraAroma',
	Solid(76.9, FGDB, FCD_UNKNOWN, 5.8),
	Color(300, EBC))
Add('Weyermann', 'CaraMunich 1',
	Solid(76.4, FGDB, FCD_UNKNOWN, 5.8),
	Color(90, EBC))
Add('Weyermann', 'CaraMunich 2',
	Solid(76.2, FGDB, FCD_UNKNOWN, 5.8),
	Color(130, EBC))
Add('Weyermann', 'CaraMunich 3',
	Solid(76.1, FGDB, FCD_UNKNOWN, 5.8),
	Color(160, EBC))

Add('Weyermann', 'Melanoidin',
	Solid(76.5, FGDB, FCD_UNKNOWN, 4.3),
	Color(70, EBC))

Add('Weyermann', 'Pale',
	Solid(78.2, FGAI, FCD_UNKNOWN, 4.5),
	Color(7.5, EBC))
Add('Weyermann', 'Vienna',
	Solid(78.4, FGAI, FCD_UNKNOWN, 4.5),
	Color(8, EBC))
Add('Weyermann', 'Munich I',
	Solid(77.4, FGAI, FCD_UNKNOWN, 4.1),
	Color(16, EBC))

Add('Weyermann', 'Chocolate Rye',
	Solid(65, FGDB, FCD_UNKNOWN, 4.0),
	Color(600, EBC))

Add('Weyermann', 'Pale Rye',
	Solid(77, FGAI, FCD_UNKNOWN, 5.0),
	Color(5, EBC))

# extract is an "average" of the lot analysis numbers
Add('Weyermann', 'Carafa 1',
	Solid(70, FGAI, FCD_UNKNOWN, 3.8),
	Color(900, EBC))
Add('Weyermann', 'Carafa 2',
	Solid(70, FGAI, FCD_UNKNOWN, 3.8),
	Color(1150, EBC))
Add('Weyermann', 'Carafa 3',
	Solid(70, FGAI, FCD_UNKNOWN, 3.8),
	Color(1400, EBC))
# the special versions of Carafa have the same extract/color
# specifications, so we can alias them
# (and they have completely different flavor, so we *must* alias them!)
Alias('Weyermann', 'Carafa 1 Special', 'Weyermann Carafa 1')
Alias('Weyermann', 'Carafa 2 Special', 'Weyermann Carafa 2')
Alias('Weyermann', 'Carafa 3 Special', 'Weyermann Carafa 3')

# Extract yields for non-malts from 'How To Brew' [Palmer]
# Moisture content from BSG website
Add(None, 'flaked wheat',
	Solid(77, CGDB, FCD_UNKNOWN, 7.0),
	Color(1, LOVIBOND))
Add(None, 'flaked oats',
	Solid(70, CGDB, FCD_UNKNOWN, 8.0),
	Color(1, LOVIBOND))

# guess and assume
Add(None, 'flaked rye',
	Solid(70, CGDB, FCD_UNKNOWN, 12),
	Color(3, LOVIBOND))

# raw grains, as opposed to malted or flaked or torrified or whatever.
# mostly just to be able to differentiate.  extract/moisture guesses
# takes from the Briess raw red wheat datasheet, and colors mostly
# just guessed.  in the typical fashion of maltster consitency, Briess
# supplies extract only for red wheat and color only for white wheat.
Add(None, 'raw red wheat',
	Solid(80, CGDB, FCD_UNKNOWN, 12.0),
	Color(3, LOVIBOND))
Add(None, 'raw white wheat',
	Solid(80, CGDB, FCD_UNKNOWN, 12.0),
	Color(2, LOVIBOND))
# extract from Briess, color from absolutely nowhere except a hat
Add(None, 'raw rye',
	Solid(77, CGDB, FCD_UNKNOWN, 12.0),
	Color(8, LOVIBOND))
# aaaand we just guess
Add(None, 'raw oats',
	Solid(70, CGDB, FCD_UNKNOWN, 12.0),
	Color(8, LOVIBOND))

# extract on the biostore package (FCD and color [obviously] guessed)
Add(None, 'raw pearl barley',
	Solid(71, CGAI, FCD_UNKNOWN, 12.0),
	Color(8, LOVIBOND))
Add(None, 'flaked barley',
	Solid(75, FGDB, FCD_UNKNOWN, 8.0),
	Color(2, LOVIBOND))

# The rice packet I looked at contained 36g starch per 45g.  Of course,
# they don't report moisture content or fine/coarse difference, so we'll
# just guess something reasonable -- raw grains are typically 9-12% and
# definitely not more than 14%, because they start spoiling.
# Could theoretically measure moisture content by dehydrating in the
# oven, but one percent point of extract here or there doesn't matter
# too much unless you're using a lot of rice, and even if I did it,
# it wouldn't be the same for your rice.
Add(None, 'rice',
	Solid(80, FGDB, FCD_UNKNOWN, 11.0),
	Color(1, EBC))

# sugars ("self-converting")
Add(None, 'table sugar',
	Solid(100, CGDB, FCD_UNKNOWN, 0),
	Color(0, EBC),
	conversion = False)
# educatedly guess the color and extract
Add(None, 'raw sugar',
	Solid(98, CGAI, FCD_UNKNOWN, 2),
	Color(10, EBC),
	conversion = False)

# invert syrups.  really just guessing the extract content, though
# read from somewhere that syrup at 115degC (cooking temperature)
# is 85% sugar, so we'll start from that and guess a bit of moisture
# loss from cooking to obtain the color.  shouldn't matter too much if
# they're a %-point off in one direction or another.
Add(None, 'invert No1',
	Solid(100, CGDB, FCD_UNKNOWN, 14),
	Color(30, EBC),
	conversion = False)
Add(None, 'invert No2',
	Solid(100, CGDB, FCD_UNKNOWN, 13),
	Color(60, EBC),
	conversion = False)
Add(None, 'invert No3',
	Solid(100, CGDB, FCD_UNKNOWN, 12),
	Color(130, EBC),
	conversion = False)
Add(None, 'invert No4',
	Solid(100, CGDB, FCD_UNKNOWN, 11),
	Color(600, EBC),
	conversion = False)

# Cand"i" syrups.  We'll just go with the same color values and names
# as the D-foo ones.  They claim 32ppg, which is 314g/gal, which is
# roughly 70%.  Seems like they're diluted from the cooking strength.
# If making them at home, one can either be mindful of the extra ~2dl
# of water per kilo, or not.
Add(None, 'candi syrup D-45',
	Solid(70, CGAI, FCD_UNKNOWN, 30),
	Color(45, LOVIBOND),
	conversion = False)
Add(None, 'candi syrup D-90',
	Solid(70, CGAI, FCD_UNKNOWN, 30),
	Color(90, LOVIBOND),
	conversion = False)
Add(None, 'candi syrup D-180',
	Solid(70, CGAI, FCD_UNKNOWN, 30),
	Color(180, LOVIBOND),
	conversion = False)
Add(None, 'candi syrup D-240',
	Solid(70, CGAI, FCD_UNKNOWN, 30),
	Color(240, LOVIBOND),
	conversion = False)

Add(None, 'honey',
	Solid(83, CGAI, FCD_UNKNOWN, 17),
	Color(10, LOVIBOND),
	conversion = False)
Add(None, 'apple juice',
	Liquid(Strength(12, Strength.PLATO)),
	Color(10, LOVIBOND),
	conversion = False)

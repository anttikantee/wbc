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
	def __init__(self, name, extract, wk, color, conversion):
		Utils.checktype(color, Color)
		self.name = name
		self.extract = extract
		self.wk = wk
		self.color = color
		self.conversion = conversion
fermentables = []

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

# min yield for pilsner is 79% to 81%, depending on which
# barley (spring/winter 2-row or 6-row) is used for the malt.
# The bag doesn't specify the barley, so let's just average it.
add('Avangard Pilsner', 80, 250, Color(3.5, Color.EBC))

add('Avangard Vienna', 80, 200, Color(11, Color.EBC))
add('Avangard Munich light', 80.5, 250, Color(18, Color.EBC))
add('Avangard Munich dark', 80.5, 250, Color(30, Color.EBC))
add('Avangard Wheat', 83, 250, Color(4.5, Color.EBC))

add('Briess pale', 78.5, 264, Color(7.8, Color.EBC))
# Briess generic smoked malt (any of beech / cherry / mesquite)
# XXX: not sure diastatic power is correct (specs do say 140 degL)
add('Briess smoked', 80.5, 474, Color(14.5, Color.EBC))

# Crisp
add('Crisp Maris Otter', 81.5, 150, Color(3.5, Color.EBC))
# well, as usual, can't find this on the maltsters page, but pretty much
# all vendors agree that it's 200-250 Lovibond, so I guess mostly correct
add('Crisp Pale Chocolate', 77, 0, Color(600, Color.EBC))

# XXX: probably better diastatic power, but can't figure it out
# from the datasheet at:
# http://dingemansmout.be/sites/dingemansmout.be/files/downloads/ALE_MD_0.pdf
add('Dingemans Pale', 80, Constants.minconversion, Color(9, Color.EBC))

add('Dingemans Special B', 72, 0, Color(310, Color.EBC))

# found a data sheet with 81% extract min for fine grind, so
# guessing the coarse grind from that.
# you're not going to use this for a significant amount of the grainbill,
# even if the guess is a bit wrong, not the end of the world.
add('Meussdoerffer Sour Malt', 78, 0, Color(2, Color.LOVIBOND))

# XXX: extract correct?
add('Muntons Chocolate', 67, 0, Color(1000, Color.EBC))
add('Muntons Crystal 150 EBC', 67, 0, Color(150, Color.EBC))
alias('Muntons Crystal 60 L', 'Muntons Crystal 150 EBC')
add('Muntons Black Malt', 67, 0, Color(1300, Color.EBC))

# XXX: I was utterly unable to find a datasheet for whatever Muntons
# "Whole Pale Malt Marris Otter" is.  So I'm just guessing it's
# more or less "ale malt" from muntons.com
add('Muntons Maris Otter', 81.5, 156, Color(5.8, Color.EBC))

add('Simpsons Golden Promise', 81, 140, Color(6.5, Color.EBC))

# Hats off to Thomas Fawcett & Sons for having useful data sheets
# easily available.  I wish all maltsters were like them.  They even
# have everything in IoB, ASBC and EBC numbers!
# http://www.fawcett-maltsters.co.uk/spec.html
# (well, ok, they don't apparently supply the diastatic power, but
# until we hit base malts for them, doesn't really matter)
add('Fawcett Brown', 70, 0, Color(188, Color.EBC))

# XXX: no idea about the extract, but since it's supposed just regular
# pale malt with lactic acid, we'll go with 75%.  it's not used in such
# high amounts that it should matter if we're off even by 50%
add('Weyermann Acidulated Malt', 75, 0, Color(4.5, Color.EBC))

add('Weyermann CaraAroma', 74, 0, Color(350, Color.EBC))
add('Weyermann CaraMunich 1', 75, 0, Color(90, Color.EBC))
add('Weyermann CaraMunich 3', 76, 0, Color(150, Color.EBC))

add('Weyermann Melanoidin', 75, 0, Color(70, Color.EBC))

# XXX: couldn't find diastatic power, so we'll just guess
# (it's self-convering for sure, so err on the low side,
# most likely is way too low)
add('Weyermann Munich I', 78, Constants.minconversion, Color(16, Color.EBC))

add('Weyermann Chocolate Rye', 65, 0, Color(600, Color.EBC))

# I'm starting to hate listing malts.  It's a complete crapshoot
# between what the maltster provides and what vendors provide
add('Weyermann Pale Rye', 81, Constants.minconversion, Color(7, Color.EBC))

# XXX: extract correct?
add('Weyermann Carafa 2', 70, 0, Color(1100, Color.EBC))

# extract yields for non-malts (from 'How To Brew' [Palmer])
add('Flaked wheat', 77, 0, Color(0, Color.EBC))
add('Flaked oats', 70, 0, Color(0, Color.EBC))
add('Roasted barley', 55, 0, Color(1400, Color.EBC))

# just a guess, really (based on some random literature pieces)
add('Rice', 70, 0, Color(1, Color.EBC))

# sugars ("self-converting")
add('Table sugar', 100, Constants.minconversion, Color(0, Color.EBC), False)

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

class Fermentable:
	def __init__(self, name, extract, wk, ebc, conversion):
		self.name = name
		self.extract = extract
		self.wk = wk
		self.ebc = ebc
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

##
## "builtin" fermentables
##

# min yield for pilsner is 79% to 81%, depending on which
# barley (spring/winter 2-row or 6-row) is used for the malt.
# The bag doesn't specify the barley, so let's just average it.
add('Avangard Pilsner', 80, 250, 3.5)

add('Avangard Vienna', 80, 200, 11)
add('Avangard Munich light', 80.5, 250, 18)
add('Avangard Munich dark', 80.5, 250, 30)
add('Avangard Wheat', 83, 250, 4.5)

add('Briess pale', 78.5, 264, 7.8)
# Briess generic smoked malt (any of beech / cherry / mesquite)
# XXX: not sure diastatic power is correct (specs do say 140 degL)
add('Briess smoked', 80.5, 474, 14.5)

# XXX: probably better diastatic power, but can't figure it out
# from the datasheet at:
# http://dingemansmout.be/sites/dingemansmout.be/files/downloads/ALE_MD_0.pdf
add('Dingemans Pale', 80, Constants.minconversion, 9)

add('Dingemans Special B', 72, 0, 310)

add('Crisp Maris Otter', 81.5, 150, 3.5)

# XXX: extract correct?
add('Muntons Chocolate', 67, 0, 1000)
add('Muntons Crystal 150', 67, 0, 150)

# XXX: I was utterly unable to find a datasheet for whatever Muntons
# "Whole Pale Malt Marris Otter" is.  So I'm just guessing it's
# more or less "ale malt" from muntons.com
add('Muntons Maris Otter', 81.5, 156, 5.8)

add('Simpsons Golden Promise', 81, 140, 6.5)

# Hats off to Thomas Fawcett & Sons for having useful data sheets
# easily available.  I wish all maltsters were like them.  They even
# have everything in IoB, ASBC and EBC numbers!
# http://www.fawcett-maltsters.co.uk/spec.html
# (well, ok, they don't apparently supply the diastatic power, but
# until we hit base malts for them, doesn't really matter)
add('Fawcett Brown', 70, 0, 188)

add('Weyermann CaraAroma', 74, 0, 350)
add('Weyermann CaraMunich 1', 75, 0, 90)
add('Weyermann CaraMunich 3', 76, 0, 150)

add('Weyermann Melanoidin', 75, 0, 70)

add('Weyermann Chocolate Rye', 65, 0, 600)

# I'm starting to hate listing malts.  It's a complete crapshoot
# between what the maltster provides and what vendors provide
add('Weyermann Pale Rye', 81, Constants.minconversion, 7)

# XXX: extract correct?
add('Weyermann Carafa 2', 70, 0, 1100)

# extract yields for non-malts (from 'How To Brew' [Palmer])
add('Flaked wheat', 77, 0, 0)
add('Flaked oats', 70, 0, 0)
add('Roasted barley', 55, 0, 600)

# sugars ("self-converting")
add('Table sugar', 100, Constants.minconversion, 0, False)

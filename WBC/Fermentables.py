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
def add(name, extract, wk, ebc, conversion = True):
	f = find(name)
	if not f is None:
		Utils.warn('fermentable ' + name + ' already exists')
		fermentables.remove(f)
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

add('Crisp Maris Otter', 81.5, 150, 3.5)

# XXX: extract correct?
add('Muntons Chocolate', 67, 0, 1000)

add('Simpsons Golden Promise', 81, 140, 6.5)

add('Weyermann CaraAroma', 74, 0, 350)
add('Weyermann CaraMunich 1', 75, 0, 90)
add('Weyermann CaraMunich 3', 76, 0, 150)
add('Weyermann Melanoidin', 75, 0, 70)

# XXX: extract correct?
add('Weyermann Carafa 2', 70, 0, 1100)

# extract yields for non-malts (from 'How To Brew' [Palmer])
add('Flaked wheat', 77, 0, 0)
add('Flaked oats', 70, 0, 0)
add('Roasted barley', 55, 0, 0)

# sugars ("self-converting")
add('Table sugar', 100, Constants.minconversion, 0, False)

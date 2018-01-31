# -*- coding: iso-8859-15 -*-
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
	def __init__(self, extract, wk, ebc, conversion = True):
		self.extract = extract
		self.wk = wk
		self.ebc = ebc
		self.conversion = conversion
fermentables = {}

#grain(extract%, min diastatic power in WK, color in EBC)

# min yield for pilsner is 79% to 81%, depending on which
# barley (spring/winter 2-row or 6-row) is used for the malt.
# The bag doesn't specify the barley, so let's just average it.
fermentables['Avangard Pilsner'] = Fermentable(80, 250, 3.5)

fermentables['Avangard Vienna'] = Fermentable(80, 200, 11)
fermentables['Avangard Munich light'] = Fermentable(80.5, 250, 18)
fermentables['Avangard Munich dark'] = Fermentable(80.5, 250, 30)
fermentables['Avangard Wheat'] = Fermentable(83, 250, 4.5)

fermentables['Crisp Maris Otter'] = Fermentable(81.5, 150, 3.5)

# XXX: extract correct?
fermentables['Muntons Chocolate'] = Fermentable(67, 0, 1000)

fermentables['Simpsons Golden Promise'] = Fermentable(81, 140, 6.5)

fermentables['Weyermann CaraMunich 1'] = Fermentable(75, 0, 90)
fermentables['Weyermann CaraMunich 3'] = Fermentable(76, 0, 150)
fermentables['Weyermann Melanoidin'] = Fermentable(75, 0, 70)

# XXX: extract correct?
fermentables['Weyermann Carafa 2'] = Fermentable(70, 0, 1100)

# extract yields for non-malts (from 'How To Brew' [Palmer])
fermentables['Flaked wheat'] = Fermentable(77, 0, 0)
fermentables['Flaked oats'] = Fermentable(70, 0, 0)
fermentables['Roasted barley'] = Fermentable(55, 0, 0)

# sugars ("self-converting")
fermentables['Table sugar']= Fermentable(100, Constants.minconversion, 0, False)

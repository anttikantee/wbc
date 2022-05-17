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

gramsperounce	= 28.349523
gramsperpound	= 16 * gramsperounce
litersperquart	= 0.94635295
literspergallon	= 4 * litersperquart
gallonsperbarrel= 31
		  # tbsp * cup * quart * gallon
tsppergallon	= 3 * 16 * 4 * 4
		  # quart * gallon
cupspergallon	= 4 * 4

pascalsperbar	= 100000
pascalsperatm	= 101325
pascalsperpsi	= 6894.75729

absolute_zero_c	= -273.15

ebcpersrm	= 1.97

# g/l of co2 at stp
co2_stp_gl	= 1.977

# in case the maltster doesn't report a fine-coarse difference, use 1.5%
fine_coarse_diff= 1.5

# need this much conversion power in the entire recipe (WK)
minconversion	= 94

# hop absorption, milliliter of wort per gram of hops
pellethop_absorption_mlg = 6
leafhop_absorption_mlg = 10

# specific volume of grains in l/kg.
#
# don't remember where I pulled this figure from, so should
# check accuracy of it some day.
grain_specificvolume = 0.7

# hop densities, via http://www.ebc2017.com/inhalt/uploads/P023_Schuell.pdf
# used for calculating hops volumes to that we know how much wort fits
# into the keg.  frankly, the volume are so small that it doesn't matter
# that much, but let's do it just to accommodate for the pathological
# "500g leaf hops in a 5gal keg" case.
#
# Also, I'm not sure those values are for the density of the *hops*, not
# the packaging.  need to measure for myself.  Just use these numbers
# for now.
#
# in kg/m3 (or g/l)
pellethop_density_gl = 500
leafhop_density_gl = 135

datefmt="%a %d %b %Y"

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

from Units import _Temperature

gramsperpound	= 453.59237
gramsperounce	= 28.349523
literspergallon	= 3.7854118
ebcpersrm	= 1.97

# need this much conversion power in the entire recipe (WK)
minconversion	= 94

# water absortion for 1kg of grain, net (i.e. apparent absorption).
# really somewhere around 1.05, but this value seems to work better
# for grains not wrung dry
grain_absorption = 1.1

# hop absorption, milliliter of wort per gram of hops
pellethop_absorption = 6
leafhop_absorption = 10

# temperature is used for volume calculations.
# XXX: should be configurable, though it doesn't really matter if
# it's 4 or 10 or 20 or 30.
sourcewater_temp = _Temperature(20)

# should also be configurable, but doesn't matter that much
preboil_temp	 = _Temperature(70)
postboil_temp	 = _Temperature(100)

# doesn't really matter, except for "setting" preboil temp
spargewater_temp = _Temperature(82)

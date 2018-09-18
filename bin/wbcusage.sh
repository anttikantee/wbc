#!/bin/sh

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

# collate first, then print sorted info
awk -F'|' '
$1 == "fermentable" {
	fermentables[$2] += $3
}
$1 == "hop" {
	hops[$2, $3, $4] += $5
}

END {
	for (f in fermentables) {
		v = fermentables[f]
		printf("f|%s|%.2f\n", f, v)
	}

	for (h in hops) {
		split(h, ar, "\034")
		name = sprintf("%-34s %5s  %s", ar[1], ar[3] "%", ar[2])
		printf("h|%s|%.2f\n", name, hops[h])
	}
}' "$@" | sort -t'|' -k 3rn \
  | awk -F'|' '
$1 == "f" {
	fermname[++i] = $2
	fermmass[i] = $3
}
$1 == "h" {
	hopname[++j] = $2
	hopmass[j] = $3
}

# no support for funnyunits for now
function scale(v) {
	if (v > 1000.0) {
		v /= 1000.0
		sfx = "kg"
		prec = ".3"
	} else {
		sfx = " g"
		prec = ".1"
	}
	return sprintf("%8" prec "f %s", v, sfx)
}

END {
	printf("\tFermentable usage\n\n")
	for (x = 1; x <= i; x++) {
		totferm += fermmass[x]
		printf("%-60s%s\n", fermname[x], scale(fermmass[x]))
	}
	printf("=\n%-60s%s\n", "Total", scale(totferm))

	printf("\n\tHop usage\n\n")
	for (x = 1; x <= j; x++) {
		tothop += hopmass[x]
		printf("%-60s%s\n", hopname[x], scale(hopmass[x]))
	}
	printf("=\n%-60s%s\n", "Total", scale(tothop))
}'

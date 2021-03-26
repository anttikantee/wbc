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

# use GNU awk if available, for proper unicode handling
if type gawk > /dev/null; then
	AWK=gawk
else
	echo '>> gawk not found; unicode character handling may be poor' 2>&1
	echo '>> falling back to "awk"' 2>&1
	echo 2>&1
	AWK=awk
fi

# collate first, then print sorted info
${AWK} -F'|' '
$1 == "wbcdata" {
	if ($2 == 1)
		mscale = 1.0
	else if ($2 == 2)
		mscale = 1000.0
	else {
		print "unsupported wbcdata version" >"/dev/stderr"
		exit(1)
	}
}
$1 == "fermentable" {
	fermentables[$2] += mscale *$3
}
$1 == "hop" {
	hops[$2, $3, $4] += mscale *$5
}
$1 == "recipe" {
	yeast_vol[$3] += $5
	yeast_batch[$3] += 1
}

END {
	if (!mscale) {
		print "invalid file, missing wbcdata version" > "/dev/stderr"
		exit(1)
	}
	for (f in fermentables) {
		v = fermentables[f]
		printf("f|%s|%.2f\n", f, v)
	}

	for (h in hops) {
		split(h, ar, "\034")
		name = sprintf("%-34s %5s  %s", ar[1], ar[3] "%", ar[2])
		printf("h|%s|%.2f\n", name, hops[h])
	}
	for (y in yeast_vol) {
		printf("y|%s|%f|%f\n", y, yeast_vol[y], yeast_batch[y])
	}
}' "$@" | sort -t'|' -k 3rn \
  | ${AWK} -F'|' '
$1 == "f" {
	fermname[++i] = $2
	fermmass[i] = $3
}
$1 == "h" {
	hopname[++j] = $2
	hopmass[j] = $3
}
$1 == "y" {
	yeastname[++k] = $2
	yeastvol[k] = $3
	yeastbatch[k] = $4
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

	printf("\n\tYeast usage\n\n")
	for (x = 1; x <= k; x++) {
		printf("%-38s%8.1f l %14d batches\n",
		    yeastname[x], yeastvol[x], yeastbatch[x])
		totvol += yeastvol[x]
		totbatch += yeastbatch[x]
	}
	printf("\n===\n%-38s%8.1f l %14d batches\n", "Total", totvol, totbatch)
}'

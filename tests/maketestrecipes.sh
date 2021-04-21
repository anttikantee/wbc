#!/bin/sh

#-
# Copyright (c) 2021 Antti Kantee <pooka@iki.fi>
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

#
# Create test recipes out of all combinations of input files.
#

die ()
{

	echo $* 1>&2
	exit 1
}

checkinputs()
{

	name=$1
	shift
	for x in $*; do
		fname="${TL}/${name},${x}.yaml"
		[ -f "${fname}" ] || die "no ${name} lego \"${x}\""
	done
}

[ -d ${TL} ] || die 'need test lego directory'
[ -d ${TO} ] || die 'need test output directory'

TL=legos
TO=compiled-recipes

HEAD="std"
MASH="infusion,single infusion,step decoction"
FERM="mass percent,ABV percent,SG"
HOPS="basic kitchensink"

checkinputs head ${HEAD}
checkinputs mash ${MASH}
checkinputs ferm ${FERM}
checkinputs hop ${HOPS}

static=opaques,std.yaml
for head in ${HEAD}; do
	for mash in ${MASH}; do
		for ferm in ${FERM}; do
			for hop in ${HOPS}; do
				name="${TO}/${head}-${mash}-${ferm}-${hop}.yaml"
				> ${name}
				cat "${TL}/head,${head}.yaml" >> "${name}"
				cat "${TL}/mash,${mash}.yaml" >> "${name}"
				cat "${TL}/ferm,${ferm}.yaml" >> "${name}"
				cat "${TL}/hop,${hop}.yaml" >> "${name}"
				cat "${TL}/${static}" >> "${name}"
			done
		done
	done
done

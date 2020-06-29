#!/bin/sh

#-
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

die ()
{

	echo '>>' $* 1>&2
	exit 1
}

msg ()
{

	echo '>>' $* 1>&2
}

usage ()
{

	die usage: $0 prep\|test\|reset
}

# assume this is run in the top level directory
export PYTHONPATH=.

FATAL=:
while getopts 'f' opt; do
	case "$opt" in
		f) FATAL='exit 1';;
	esac
done
shift $((${OPTIND} - 1))

[ $# -eq 1 ] || usage

compordie ()
{
	if ! diff -u $1 $2; then
		failed=$((${failed} + 1))
	fi
	[ ${failed} -eq 0 ] || ${FATAL}
}

if [ "$1" = 'prep' ]; then
	mkdir -p testdata || die cannot create testdata
	for x in recipes/*.yaml; do
		echo "Processing $x ..."
		python3 ./bin/wbcrecipe.py -p WBCparams-regress $x \
		    > testdata/$(basename $x).out
		[ $? -eq 0 ] || die Failed: $(cat testdata/$(basename $x).out)
	done

	num=1
	while read line; do
		set -- ${line}
		[ $# -ne 0 ] || continue
		echo Processing "$@"
		${@} > testdata/cmdregress-${num}.cmdout
		num=$((${num} + 1))
	done < cmds-regress.txt
elif [ $1 = 'test' ]; then
	[ -n "$(ls testdata 2>/dev/null)" ] \
	    || die no testdata, did not run prep\?

	failed=0
	rm -f testdata/failed-recipes
	for x in testdata/*.out; do
		bn=$(basename ${x%.out})
		echo "Testing ${bn} ..."
		python3 ./bin/wbcrecipe.py -p WBCparams-regress recipes/${bn} \
		    > $x.cmp
		[ $? -eq 0 ] || echo ${bn} >> testdata/failed-recipes
		compordie $x $x.cmp
	done

	num=1
	while read line; do
		set -- ${line}
		[ $# -ne 0 ] || continue
		echo Testing "$@"
		${@} > testdata/cmdregress-${num}.cmp
		compordie testdata/cmdregress-${num}.cmdout \
		    testdata/cmdregress-${num}.cmp
		num=$((${num} + 1))
	done < cmds-regress.txt

	fr=testdata/failed-recipes
	[ ${failed} -eq 0 ] || msg output for ${failed} 'test(s)' differ
	[ ! -f ${fr} ] || {
	    msg Following recipes failed \(n = $(wc -l < ${fr})\):; cat ${fr}; }
	[ ${failed} -eq 0 -a ! -f ${fr} ] || die 'failed'

	echo '>> no regressions.  run "reset" if you no longer need testdata'
elif [ $1 = 'reset' ]; then
	rm -rf testdata
else
	echo ">> invalid command $1" 1>&2
	usage
fi

exit 0

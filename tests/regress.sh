#!/bin/sh

#-
# Copyright (c) 2018, 2021 Antti Kantee <pooka@iki.fi>
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

# assume this is run in the top level test directory
export PYTHONPATH=..
export PATH="../bin:${PATH}"

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

prepcmd ()
{

	descr=$1
	shift
	tn="${descr}-${num}"

	echo "=== ${tn} ==="
	echo "==> ${*}"
	${@} > testdata/${tn}.out
	echo "${@}" > testdata/${tn}.cmd
	[ $? -eq 0 ] || die Failed: $(cat testdata/${tn}).out
	num=$((${num} + 1))
}

resetcount ()
{

	num=1
}

doprep ()
{

	mkdir -p testdata || die cannot create testdata
	resetcount
	for x in compiled-recipes/*.yaml; do
		[ -f ${x} ] || die internal error: ${x}
		prepcmd recipe-std wbcrecipe -p params-std ${x}
	done

	resetcount
	for x in compiled-recipes/*infusion,step*.yaml; do
		[ -f ${x} ] || die internal error: ${x}
		prepcmd recipe-alt wbcrecipe -p params-mltdirect+sg+us ${x}
	done

	resetcount
	prepcmd vol wbcrecipe -v 30l -p params-std \
	    test-recipes/proto-byweight.yaml
	prepcmd vol wbcrecipe -V 30l -p params-std \
	    test-recipes/proto-byweight.yaml
	prepcmd vol wbcrecipe -v 40l -P bM=35L -p params-std \
	    test-recipes/proto-byweight.yaml

	resetcount
	while read line; do
		set -- ${line}
		[ $# -ne 0 ] || continue
		prepcmd cmdregress ${line}
	done < cmds-regress.txt
}

checkfails ()
{

	what=$1
	file=$2

	[ ! -f ${file} ] || { \
	    msg ; msg ${what} failed \(n = $(wc -l ${file})\):;
	    cat ${file} | while read x ; do
	    	echo -n "${x}: "
		cat testdata/${x}.cmd
	    done }
}

dotest ()
{

	[ -n "$(ls testdata 2>/dev/null)" ] \
	    || die no testdata, did not run prep\?

	ft=testdata/failed-tests
	fc=testdata/failed-comps
	rm -f ${ft} ${fc}

	for x in testdata/*.cmd; do
		bn=$(basename ${x%.cmd})
		read cmd < ${x}
		echo "==== ${cmd}"
		set -- ${cmd}
		${@} > testdata/${bn}.cmp
		if [ $? -ne 0 ]; then
			echo ${bn} >> ${ft}
			${FATAL}
		elif ! diff -u testdata/${bn}.out testdata/${bn}.cmp; then
			echo ${bn} >> ${fc}
			${FATAL}
		fi
	done

	checkfails Comparisons ${fc}
	checkfails Tests ${ft}
	[ ! -f ${ft} -a ! -f ${fc} ] || die 'failed'

	echo '>> no regressions.  run "reset" if you no longer need testdata'
}

doreset ()
{

	rm -rf testdata
}

#
# BEGIN script
#

FATAL=:
while getopts 'f' opt; do
	case "$opt" in
		f) FATAL='exit 1';;
	esac
done
shift $((${OPTIND} - 1))
[ $# -eq 1 ] || usage

if [ "$1" = 'prep' ]; then
	doprep
elif [ $1 = 'test' ]; then
	dotest
elif [ $1 = 'reset' ]; then
	doreset
else
	msg invalid command $1
	usage
fi

exit 0

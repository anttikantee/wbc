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

_prep ()
{

	isrecipe=$1
	shift

	descr=$1
	shift
	tn="${descr}-${num}"

	echo "=== ${tn} ==="
	echo "${@}" > testdata/${tn}.cmd
	if ${PREP}; then
		echo "==> ${*}"
		${@} > testdata/${tn}.out
		[ $? -eq 0 ] || die Failed: $(cat testdata/${tn}).out

		! ${isrecipe}|| echo $(eval echo \${$#}) >testdata/${tn}.recipe
	fi
	num=$((${num} + 1))
}

prepcmd ()
{

	_prep false "$@"
}

preprecipe ()
{

	_prep true "$@"
}

resetcount ()
{

	num=1
}

doprep ()
{

	! ${PREP} || [ ! -d testdata ] \
	    || die testdata already exists.  \"reset\" first
	mkdir -p testdata || die cannot create testdata

	resetcount
	# hack: make sure at least one recipe is tested first
	preprecipe 0basicrecipe wbcrecipe -p params-std \
	    test-recipes/proto-bymass.yaml

	resetcount
	for x in compiled-recipes/*.yaml; do
		[ -f ${x} ] || die internal error: ${x}
		preprecipe recipe-std wbcrecipe -p params-std ${x}
	done

	resetcount
	for x in compiled-recipes/*mish,step*.yaml; do
		[ -f ${x} ] || die internal error: ${x}
		preprecipe recipe-alt wbcrecipe -p params-mltdirect+sg+us \
		    -i mashheat.yaml ${x}
	done

	resetcount
	preprecipe vol wbcrecipe -v 30l -p params-std \
	    test-recipes/proto-bymass.yaml
	preprecipe vol wbcrecipe -V 30l -p params-std \
	    test-recipes/proto-bymass.yaml
	preprecipe vol wbcrecipe -v 40l -P bM=35L -p params-std \
	    test-recipes/proto-bymass.yaml

	resetcount
	preprecipe noboil wbcrecipe -p params-std \
	    test-recipes/proto-bymass-noboil.yaml
	preprecipe noboil wbcrecipe -p params-std \
	    test-recipes/proto-bymass-0boil.yaml

	resetcount
	preprecipe nomash-mass wbcrecipe -p params-std \
	    test-recipes/proto-bymass-nomash.yaml
	preprecipe nomash-mass wbcrecipe -p params-std \
	    test-recipes/proto-bymass-extract.yaml
	preprecipe nomash-mass wbcrecipe -p params-std \
	    test-recipes/proto-bymass-steepextract.yaml

	resetcount
	preprecipe nomash-percent wbcrecipe -p params-std \
	    test-recipes/proto-bypercent-extract.yaml
	preprecipe nomash-percent wbcrecipe -p params-std \
	    test-recipes/proto-bypercent-steepextract.yaml

	resetcount
	preprecipe pagelen wbcrecipe -p params-std -P oP=10 \
	    test-recipes/proto-bymass.yaml
	preprecipe pagelen wbcrecipe -p params-std -P oP=40 \
	    test-recipes/proto-bymass.yaml
	preprecipe pagelen wbcrecipe -p params-std -P oP=400 \
	    test-recipes/proto-bymass.yaml

	resetcount
	preprecipe liquid-maximum wbcrecipe -p params-std \
	    test-recipes/applewine.yaml
	preprecipe liquid-maximum wbcrecipe -p params-std \
	    test-recipes/cidre-fermenter.yaml

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

_onetest ()
{

	tname=$1
	storeres=$2

	read cmd < testdata/${tname}.cmd
	echo "==== ${cmd}"
	set -- ${cmd}
	rv=1
	${@} > testdata/${tname}.cmp

	if [ $? -ne 0 ]; then
		! ${storeres} || echo ${tname} >> ${ft}
	elif ! diff -u testdata/${tname}.out testdata/${tname}.cmp; then
		! ${storeres} || echo ${tname} >> ${fc}
	else
		rv=0
	fi

	return ${rv}
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
		_onetest ${bn} true

		if [ $? -ne 0 ]; then
			if ${VERBOSE} && [ -f testdata/${bn}.recipe ]; then
				echo '------ BEGIN RECIPE ------'
				cat $(cat testdata/${bn}.recipe)
				echo '------  END  RECIPE ------'
			fi
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
VERBOSE=false
while getopts 'fv' opt; do
	case "$opt" in
		f) FATAL='exit 1';;
		v) VERBOSE=true;;
	esac
done
shift $((${OPTIND} - 1))

# onetest takes two arguments
if [ "$1" = 'onetest' ]; then
	[ $# -eq 2 ] || usage
	_onetest $2 false
	[ $? -eq 0 ] || { echo 'FAILED' ; exit 1 ; }
	exit 0
fi

[ $# -eq 1 ] || usage

if [ "$1" = 'prep' ]; then
	PREP=true
	doprep
elif [ $1 = '_recmd' ]; then
	PREP=false
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

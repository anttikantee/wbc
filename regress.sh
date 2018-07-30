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

usage ()
{

	die usage: $0 prep\|test\|reset
}

# you have got to the be kidding me
export PYTHONIOENCODING=utf-8

# assume this is run in the top level directory
export PYTHONPATH=.

[ $# -eq 1 ] || usage

if [ "$1" = 'prep' ]; then
	mkdir -p testdata || die cannot create testdata
	for x in recipes/*.yaml; do
		echo "Processing $x ..."
		python ./bin/wbctool.py $x > testdata/$(basename $x).out
		[ $? -eq 0 ] || die Failed: $(cat testdata/$(basename $x).out)
	done
elif [ $1 = 'test' ]; then
	[ -n "$(ls testdata 2>/dev/null)" ] \
	    || die no testdata, did not run prep\?

	rv=0
	for x in testdata/*.out; do
		bn=$(basename ${x%.out})
		echo "Testing ${bn} ..."
		python ./bin/wbctool.py recipes/${bn} > $x.cmp
		if ! diff -u $x $x.cmp; then
			rv=1
		fi
	done

	[ ${rv} -eq 0 ] || die output differs

	echo '>> no regressions.  run "reset" if you no longer need testdata'
elif [ $1 = 'reset' ]; then
	rm -rf testdata
else
	echo ">> invalid command $1" 1>&2
	usage
fi

exit 0

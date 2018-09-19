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

global wbcparams
wbcparams = {}

needparams = \
	[ 'units_output', 'strength_output', 'mash_efficiency',
	  'boiloff_perhour', 'mlt_loss', 'mlt_heatcapacity', 'mlt_heat']
for x in needparams:
	wbcparams[x] = None

from Utils import PilotError, notice

import os, sys

def getparam(what):
	global wbcparams
	return wbcparams[what]

# XXX: should actually parse the values properly and check that they make sense
floatparams = \
	[ 'mash_efficiency', 'boiloff_perhour', 'mlt_loss', 'mlt_heatcapacity' ]
def setparam(what, value):
	global wbcparams
	if what not in wbcparams:
		raise PilotError('invalid config knob: ' + what)
	wbcparams[what] = value

def processparam(paramstr):
	ar = paramstr.split('=')
	if len(ar) != 2:
		raise PilotError('invalid sysparam: ' + paramstr)
	what = ar[0].strip()
	value = ar[1].strip()
	if what in floatparams:
		value = float(value)
	setparam(what, value)

def processfile(filename):
	pfiles = []
	if filename is not None:
		pfiles.append(filename)
	pfiles.append('./.wbcsysparams')
	pfiles.append(os.path.expanduser('~/.wbcsysparams'))

	f = None
	for pf in pfiles:
		try:
			f = open(pf, 'r')
			break
		except IOError:
			continue

	if f is None:
		raise PilotError('could not open wbcsysparams file')

	notice('Using "' + pf + '" for WBC brew system parameters\n')

	for line in f:
		line = line.strip()
		if len(line) == 0 or line[0] == '#':
			continue
		processparam(line)
	f.close()

	for p in needparams:
		if getparam(p) is None:
			raise PilotError('missing system parameter for: ' + p)

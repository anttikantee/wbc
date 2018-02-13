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

# well this config really shouldn't be here ... but for whatever reason it is
global bcconfig
bcconfig = {}
bcconfig['units_input'] = 'metric'
#bcconfig['units_input'] = 'us'

bcconfig['units_output'] = 'metric'
#bcconfig['units_output'] = 'us'

bcconfig['strength_input'] = 'sg'
#bcconfig['strength_input'] = 'plato'

#bcconfig['strength_output'] = 'sg'
bcconfig['strength_output'] = 'plato'

bcconfig['mash_efficiency'] = .88
bcconfig['boiloff_rate'] = 3
bcconfig['mlt_loss'] = 1	# liters, constant irrespective of grains

def getconfig(what):
	global bcconfig
	return bcconfig[what]

def setconfig(what, value):
	global bcconfig
	if what not in bcconfig:
		raise PilotError('invalid config knob')
	bcconfig[what] = value

class PilotError(Exception):
	pass

def checktype(type, cls):
	if not isinstance(type, cls):
		raise PilotError('invalid input type for ' + cls.__name__)

def checktypes(lst):
	for chk in lst:
		checktype(*chk)

def warn(msg):
	print 'WARNING: ' + msg

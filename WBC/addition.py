#
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
# An addition is anything that gets added to a recipe at some
# stage during the process, e.g. hops or acids.
#

class Addition:
	def __init__(self, obj, amount, resolver, time, cookie = None):
		self.obj = obj
		self._amount = amount
		self._resolver = resolver

		self.time = time
		self.cookie = cookie

		self.info = None
		self.timer = None

	def _strwrap(self, strfun, maxlen, params):
		s = strfun(maxlen, *params)
		if maxlen != None and len(s) > maxlen:
			# XXX: not a pilot error ... as usual
			raise PilotError('addition string "' + s + '" does '
			    + 'not fit in allotted space')
		return s

	def set_amount(self, amount):
		self._amount = amount

	def get_amount(self):
		if self._resolver is not None:
			return self._resolver(self._amount)
		return self._amount

	def namestr(self, maxlen):
		return self._strwrap(self.obj.namestr, maxlen, ())

	def infostr(self, maxlen):
		return self._strwrap(self.obj.infostr, maxlen, (self.info,))

	def timerstr(self, maxlen):
		return self._strwrap(lambda x,y: str(y), maxlen, (self.timer,))

class Opaque:
	def __init__(self, name):
		self.name = name

	def namestr(self, maxlen):
		#XXX don't ignore namelen
		return self.name

	def infostr(self, _, info):
		return ''

# the following is a way to differentiate between user-specified
# opaque additions and WBC-specified opaque additions
class Internal(Opaque):
	pass

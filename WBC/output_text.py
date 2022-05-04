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

from WBC.getparam import getparam

from WBC import constants, sysparams
from WBC import timespec

# XXX: should not be needed in an ideal world
from WBC.units import Strength, _Volume, _Mass, _Strength

from WBC.worter import Worter
from WBC.timespec import Timespec

global _prtsects
_prtsects = ['']
_oldprt = print
def _newsect():
	_prtsects.append('')
def print(x = '', end = '\n'):
	_prtsects[-1] += x + end

def stras_unsystem(obj):
	uo = getparam('units_output')
	return obj.stras_system({'metric':'us','us':'metric'}[uo])

# print first line with prefix and rest indented at prefixlen,
# split at whitespaces
def _prettyprint_withsugarontop(prefix, prefixlen, thestr, strmaxlen, sep=None):
	res = []
	while len(thestr) > strmaxlen:
		# this produces off-by-one lengths in a number of
		# pathological corner cases.  not going to worry about it.
		v = thestr[:strmaxlen+1].rsplit(sep, 1)
		res.append(v[0])
		thestr = thestr[len(v[0]):].lstrip()
	res.append(thestr)

	fmtstr = '{:' + str(prefixlen) + '}{:}'
	for s in res:
		print(fmtstr.format(prefix, s))
		prefix = ''

def _prtsep(char='='):
	print(char * 79)

def __reference_temp():
	return getparam('ambient_temp')

def _printfermentables(input, results):
	fmtstr = '{:34}{:>20}{:>12}{:>12}'
	print(fmtstr.format("Fermentables",
	    "amount", "ext (100%)", "ext (pkg)"))
	_prtsep()

	def handleonestage(stage, needsep):
		lst = [x for x in results['fermentables']
		    if timespec.timespec2stage[x.time.__class__] == stage]
		if len(lst) == 0:
			return needsep

		if needsep:
			_prtsep('-')
		print(stage.title())

		for f in lst:
			persstr = ' ({:5.1f}%)'.format(f.info['percent'])
			print(fmtstr.format(f.obj.name,
			    str(f.get_amount()) + persstr,
			    str(f.info['extract_theoretical']),
			    str(f.info['extract_predicted'])))

		# print stage summary only for stages with >1 fermentable
		if len(lst) > 1:
			stats = results['fermentable_stats_perstage'][stage]
			persstr = ' ({:5.1f}%)'.format(stats['percent'])
			print(fmtstr.format('',
			    str(stats['amount']) + persstr,
			    str(stats['extract_theoretical']),
			    str(stats['extract_predicted'])))
		return True

	needsep = False
	for stage in timespec.Timespec.stages:
		needsep = handleonestage(stage, needsep)
	_prtsep()

	allstats = results['fermentable_stats_all']
	print(fmtstr.format('', \
	    str(allstats['amount']) + ' (100.0%)',
	    str(allstats['extract_theoretical']),
	    str(allstats['extract_predicted'])))

def _printmash(input, results):
	if 'mash' not in results:
		return False

	spargewater = results['mash']['sparge_water']
	yesnosparge = ")"
	if spargewater.water() <= .001:
		yesnosparge = ", no-sparge)"

	stepfmt = '{:12}{:>10}{:>26}{:>16}{:>14}'

	print(stepfmt.format('Mashstep', 'Time', 'Adjustment',
	    'Ratio', 'Volume'))
	_prtsep()

	for i, x in enumerate(results['mash']['steps']):
		ms = x['step']
		steptemp = str(ms.temperature)
		if ms.time is not ms.TIME_UNSPEC:
			steptime = str(ms.time)
		else:
			steptime = 'UNS'

		water = x['water']
		temp = x['temp']

		# handle direct-heated mashtuns.
		# XXX: should probably be more rigorously structured
		# in the computation so that we don't need so much
		# logic here on the "dumb" output side
		if results['mash']['method'] == 'decoction' and i != 0:
			addition = 'decoct ' + str(x['decoction'])
		elif getparam('mlt_heat') == 'direct' and i != 0:
			addition = 'heat'
		else:
			addition = '{:>8}'.format(str(water.volume(temp)) \
			    + ' @ {:>7}'.format(str(temp)))

		# print the water/grist ratio at the step.
		if getparam('units_output') == 'metric':
			ratio = x['ratio']
			ratiounit = 'L/kg'
		else:
			ratio = (x['ratio']*constants.litersperquart) \
			    / (constants.gramsperpound / 1000.0)
			ratiounit = 'qt/lb'
		ratiostr = '{:.2f} {:}'.format(ratio, ratiounit)

		print(stepfmt.format(steptemp, steptime, addition,
		    ratiostr, str(x['mashvol'])))
	finaltemp = ms.temperature

	_prtsep('-')

	mw = results['mash']['mashstep_water'].volume(__reference_temp())
	print('{:20}{:}'.format('Mashstep water:',
	    str(mw) + ' / ' + stras_unsystem(mw)
	    + ' @ ' + str(__reference_temp())), end=' ')
	mrun = results['mash_first_runnings'].volume(finaltemp)
	print('({:} @ {:} ~run'
	    .format(str(mrun) + ' / ' + stras_unsystem(mrun), finaltemp)
	      + yesnosparge)

	if spargewater.water() > .001:
		at = getparam('ambient_temp')
		st = getparam('sparge_temp')
		print('{:20}{:} ({:} @ {:} amb.)'.format('Sparge water:',
		    str(spargewater.volume(st)) + ' / '
		    + stras_unsystem(spargewater.volume(st)) + ' @ ' + str(st),
		    str(spargewater.volume(at)) + ' / '
		    + stras_unsystem(spargewater.volume(at)), str(at)))

	fw = results['mash_conversion']
	fwstrs = []
	for x in [85, 90, 95, 100]:
		fwstrs.append(str(fw[x]) + ' (' + str(x) + '%)')
	print('{:20}{:}'. format('1st wort (conv. %):',
	    ', '.join(fwstrs)))

	if 'steal' in results:
		stolen = input['stolen_wort']
		steal = results['steal']
		print('Steal', steal['volume'], 'preboil wort', end=' ')
		if steal['missing'] > 0.05:
			print('and blend with',steal['missing'],'water', end='')

		print('==>', stolen.volume(), '@',
		    str(steal['strength']), end=' ')
		if steal['strength'] < stolen.strength():
			assert(steal['missing'] <= 0.05)
			print('(NOTE: strength < ' \
			    + str(stolen.strength())+')', end=' ')
		print()
	_prtsep()

	return True

def _printtimers(input, results):
	if len(results['timer_additions']) == 0:
		return False

	nlen = 36
	ilen = 6
	onefmt = ('{:} {:' + str(nlen) + '}{:>' + str(ilen)
	    + '}{:>12}{:>12}{:>10}')
	print(onefmt.format("T", "Additions & Hops", "IBUs",
	    "amount", "timespec", "timer"))
	_prtsep()

	prevstage = None
	for t in results['timer_additions']:
		stage = t.time.__class__
		if prevstage is not None and prevstage is not stage:
			_prtsep('-')
		prevstage = stage

		# try to pick visually different characters for the types
		c = {
			'Hop':		'-',
			'Opaque':	'o',
			'Fermentable':	'X',
			'Water':	'|',
			'Internal':	' ',
		}.get(type(t.obj).__name__, '?')

		v = (c, t.namestr(nlen), t.infostr(ilen), str(t.get_amount()))
		print(onefmt.format(*v, t.time.timespecstr(), t.timerstr(None)))
	_prtsep()

	return True

def _keystats(input, results, miniprint):
	# column widths (
	cols = [20, 19, 22, 19]
	cols_tight = [20, 19, 16, 25]

	_prtsep()
	onefmt = '{:' + str(cols[0]) + '}{:}'

	def maketwofmt(c):
		return '{:' + str(c[0]) + '}{:' + str(c[1]) \
		    + '}{:' + str(c[2]) + '}{:' + str(c[3]) + '}'
	twofmt = maketwofmt(cols)
	twofmt_tight = maketwofmt(cols_tight)

	rwort = results['worter']

	total_water = results['total_water']
	if 'steal' in results:
		total_water = _Volume(total_water
		    + results['steal']['missing'])

	print(onefmt.format('Name:', input['name']))
	pwort = rwort[Worter.PACKAGE]
	print(twofmt_tight.format('Aggregate strength:',
	    str(pwort.strength()),
	    'Package volume:',
	      str(pwort.volume()) + ' / ' + stras_unsystem(pwort.volume())))
	print(twofmt_tight.format('Total fermentables:',
	    str(results['fermentable_stats_all']['amount']),
	    'Total hops:',
	    str(results['hop_stats']['mass'])))

	totibus = results['hop_stats']['ibu']
	color = results['color']

	if totibus > 0.001 or color is not None:
		bugu = totibus \
		    / rwort[Worter.PACKAGE].strength().valueas(Strength.SG_PTS)
		if color is not None:
			cstr = (color.stras(color.EBC)
			    + ', ' + color.stras(color.SRM))
		else:
			cstr = 'n/a'

		print(twofmt_tight.format('Tinseth IBU / BUGU:',
		    '{:<3d} / {:.2f}'.format(int(round(totibus)), bugu),
		    'Color (Morey):', cstr))

	kl = results['losses'][Timespec.KETTLE]
	fl = results['losses'][Timespec.FERMENTOR]
	if not (input['boiltime'] is None and kl.volume() < 0.001):
		print(twofmt_tight.format('Kettle loss (v/e):',
		    str(kl.volume()) + ' / ' + str(kl.extract()),
		    'Boil:', str(input['boiltime'])))

	print(twofmt_tight.format("F'tor loss (v/e):",
	    str(fl.volume()) + ' / ' + str(fl.extract()),
	    'Yeast:', input['yeast']))
	Ta = getparam('ambient_temp')
	print(twofmt_tight.format(
	    'Water (' + str(Ta) + '):',
	    str(total_water.volume(Ta))
	      + ' / ' + stras_unsystem(total_water.volume(Ta)),
	    'Brewhouse eff:',
	    '{:.1f}%'.format(100 * results['brewhouse_efficiency'])))

	print()

	if len(input['notes']['recipe'] + input['notes']['brewday']) > 0:
		for n in input['notes']['recipe']:
			_prettyprint_withsugarontop('Recipe notes:',
			    cols[0], n, sum(cols) - cols[0])
		for n in input['notes']['brewday']:
			_prettyprint_withsugarontop('Brewday notes:',
			    cols[0], n, sum(cols) - cols[0])
		print()

	if rwort[Worter.PREBOIL].volume() > 0.01:
		boil_pretemp = getparam('preboil_temp')
		boil_posttemp = getparam('postboil_temp')
		print(twofmt.format('Preboil  volume  :',
		    str(rwort[Worter.PREBOIL].volume(boil_pretemp)) \
		      + ' (' + str(boil_pretemp) + ')',
		    'Measured:', ''))
		print(twofmt.format('Preboil  strength:',
		    str(rwort[Worter.PREBOIL].strength()), 'Measured:', ''))
		print(twofmt.format('Postboil volume  :',
		    str(rwort[Worter.POSTBOIL].volume(boil_posttemp)) \
		      + ' (' + str(boil_posttemp) + ')',
		    'Measured:', ''))
		print(twofmt.format('Postboil strength:',
		    str(rwort[Worter.POSTBOIL].strength()), 'Measured:', ''))
	else:
		print(twofmt.format('Fermentor volume  :',
		    str(rwort[Worter.FERMENTOR].volume()),
		    'Fermentor Strength:',
		    str(rwort[Worter.FERMENTOR].strength())))

	if not miniprint:
		print()
		unit = ' billion'
		print(twofmt.format('Pitch rate, ale:',
		    str(int(results['pitch']['ale'])) + unit,
		    'Pitch rate, lager:',
		    str(int(results['pitch']['lager'])) + unit))

	hd = results['hopsdrunk']
	if not miniprint and hd['package'] > 0:
		print()
		print('NOTE: package hops absorb: '
		    + str(hd['package'])
		    + ' => effective yield: '
		    + str(rwort[Worter.PACKAGE].volume() - hd['package']))

		# warn about larger packaging volume iff package dryhops
		# volume exceeds 1dl
		if hd['volume'] > 0.1:
			print('NOTE: package hop volume: ~'
			    + str(hd['volume']) + ' => packaged volume: '
			    + str(rwort[Worter.PACKAGE].volume()
			      + hd['volume']))

def _printattenuate(results):
	print('Speculative apparent attenuation and resulting ABV')
	_prtsep()
	onefmt = '{:^8}{:^8}{:10}'
	title = ''
	for x in range(3):
		title += onefmt.format('Str.', 'Att.', 'ABV')
	print(title)

	reslst = []
	for x in results['attenuation']:
		reslst.append((str(x[1]), str(x[0]) + '%', \
		    '{:.1f}%'.format(x[2])))
	assert(len(reslst)%3 == 0)

	for i in range(0, int(len(reslst)/3)):
		line = onefmt.format(*reslst[i])
		line += onefmt.format(*reslst[i + int(len(reslst)/3)])
		line += onefmt.format(*reslst[i + int(2*len(reslst)/3)])
		print(line)
	_prtsep()

def printit(input, results, miniprint):
	_keystats(input, results, miniprint)
	_prtsep()
	ps = sysparams.getparamshorts()
	_prettyprint_withsugarontop('', '', ps, 78, sep='|')
	_prtsep()
	_newsect()

	_printfermentables(input, results)
	_newsect()

	if _printmash(input, results):
		_newsect()

	if _printtimers(input, results):
		_newsect()

	if not miniprint:
		_printattenuate(results)
		_newsect()

	def curlines(str):
		# XXX: assert that no line is over 80 chars
		return str.count('\n')

	def doprt(str):
		nonlocal pagelines
		_oldprt(str, end='')
		pagelines += curlines(str)

	pagelen = getparam('output_text-pagelen')
	if pagelen is None: pagelen = 0
	pagelines = 0
	doprt(_prtsects[0])
	for x in _prtsects[1:]:
		if pagelen > 0 and pagelines + curlines(x) > pagelen:
			pagelines = 0
			_oldprt(end='')
		else:
			_oldprt()
			pagelines += 1
		doprt(x)

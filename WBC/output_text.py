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

from WBC.utils import prtsep, prettyprint_withsugarontop
from WBC.getparam import getparam

from WBC import constants, sysparams

from WBC.wbc import WBC

# XXX: should not be needed in an ideal world
from WBC.units import Strength, _Volume, _Mass, _Strength

def __reference_temp():
	return getparam('ambient_temp')

def _printmash(input, results):
	fmtstr = '{:34}{:>20}{:>12}{:>12}'
	print(fmtstr.format("Fermentables",
	    "amount", "ext (100%)", "ext ("
	    + str(int(getparam('mash_efficiency'))) + "%)"))
	prtsep()

	def handleonestage(stage, needsep):
		lst = [x for x in results['fermentables'] if x['when'] == stage]
		if len(lst) == 0:
			return needsep

		if needsep:
			prtsep('-')
		print(stage.title())

		for f in lst:
			persstr = ' ({:5.1f}%)'.format(f['percent'])
			print(fmtstr.format(f['name'],
			    str(f['amount']) + persstr,
			    str(f['extract_theoretical']),
			    str(f['extract_predicted'])))

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
	for stage in WBC.stages:
		needsep = handleonestage(stage, needsep)
	prtsep()

	allstats = results['fermentable_stats_all']
	print(fmtstr.format('', \
	    str(allstats['amount']) + ' (100.0%)',
	    str(allstats['extract_theoretical']),
	    str(allstats['extract_predicted'])))

	print()

	spargevol = results['mash']['sparge_water']
	yesnosparge = ")"
	if spargevol <= .001:
		yesnosparge = ", no-sparge)"

	stepfmt = '{:12}{:>10}{:>26}{:>16}{:>14}'

	print(stepfmt.format('Mashstep', 'Time', 'Addition', 'Ratio', 'Volume'))
	prtsep()

	totvol = 0
	for i, x in enumerate(results['mash']['steps']):
		ms = x[0]
		steptemp = str(ms.temperature)
		if ms.time is not ms.TIME_UNSPEC:
			steptime = str(ms.time) + ' min'
		else:
			steptime = 'UNS'

		# handle direct-heated mashtuns.
		# XXX: should probably be more rigorously structured
		# in the computation so that we don't need so much
		# logic here on the "dumb" output side
		if getparam('mlt_heat') == 'direct' and i != 0:
			addition = 'heat'
		else:
			addition = '{:>8}'.format(str(x[2])) \
			    + ' @ {:>7}'.format(str(x[3]))

		# print the water/grist ratio at the step.
		if getparam('units_output') == 'metric':
			ratio = x[4]
			ratiounit = 'l/kg'
		else:
			ratio = (x[4]*Constants.litersperquart) \
			    / (Constants.gramsperpound / 1000.0)
			ratiounit = 'qt/lb'
		ratiostr = '{:.2f} {:}'.format(ratio, ratiounit)

		print(stepfmt.format(steptemp, steptime, addition,
		    ratiostr, str(x[5])))

	prtsep('-')

	print('{:20}{:}'.format('Mashstep water:',
	    str(results['mash']['mashstep_water']) + ' @ '
	    + str(__reference_temp())), end=' ')
	print('(1st runnings: ~{:}'
	    .format(results['mash_first_runnings_max']) + yesnosparge)

	if spargevol > .001:
		print('{:20}{:}'.format('Sparge water:',
		    str(spargevol) + ' @ '
		    + str(getparam('sparge_temp'))))

	fw = results['mash_first_wort_max']
	fwstrs = []
	for x in [.85, .90, .95, 1.0]:
		fwstrs.append(str(_Strength(fw * x)) \
		    + ' (' + str(int(100 * x)) + '%)')
	print('{:20}{:}'. format('1st wort (conv. %):',
	    ', '.join(fwstrs)))

	if 'steal' in results:
		stolen = input['stolen_wort']
		steal = results['steal']
		print('Steal', steal['volume'], 'preboil wort', end=' ')
		if steal['missing'] > 0.05:
			print('and blend with',steal['missing'],'water', end='')

		print('==>', stolen['volume'], '@',
		    str(steal['strength']), end=' ')
		if steal['strength'] < stolen['strength']:
			assert(steal['missing'] <= 0.05)
			print('(NOTE: strength < ' \
			    + str(stolen['strength'])+')', end=' ')
		print()
	prtsep()
	print()

def _printboil(input, results):
	namelen = 33
	onefmt = '{:' + str(namelen) + '}{:6}{:>5}{:>12}{:>12}{:>10}'
	print(onefmt.format("Hops", "  AA%", "IBUs", "amount",
	    "timespec", "timer"))
	prtsep()
	totmass = 0

	t = results['startboil_timer']
	if t is not None:
		print(onefmt.format('', '', '', '', '@ boil', str(t) + ' min'))

	# printing IBUs with a decimal point, given all
	# other inaccuracy involved, is rather silly.
	# but what would we be if not silly?
	ibufmt = '{:.1f}'

	prevstage = None
	for h in results['hops']:
		(hop,mass,time,ibu) = (h['hop'],h['mass'],h['time'],h['ibu'])
		nam = hop.name
		typ = hop.typestr
		if len(nam) + len(typ) + len(' ()') >= namelen:
			typ = hop.typestr[0]
		typ = ' (' + typ + ')'
		if prevstage is not None and \
		    prevstage is not time.__class__:
			prtsep('-')
		maxlen = (namelen-1) - len(typ)
		if len(nam) > maxlen:
			nam = nam[0:maxlen-2] + '..'

		prevstage = time.__class__
		totmass = mass + totmass

		if time.spec == input['boiltime']:
			# XXX
			timestr = '@ boil'
		else:
			timestr = time.timespecstr()

		ibustr = ibufmt.format(ibu)
		print(onefmt.format(nam + typ, str(hop.aapers) + '%',
		    ibustr, str(mass), timestr, h['timer']))
	prtsep()
	print()

def _keystats(input, results, miniprint):
	# column widths (
	cols = [20, 19, 22, 19]
	cols_tight = [20, 19, 16, 25]

	prtsep()
	onefmt = '{:' + str(cols[0]) + '}{:}'

	def maketwofmt(c):
		return '{:' + str(c[0]) + '}{:' + str(c[1]) \
		    + '}{:' + str(c[2]) + '}{:' + str(c[3]) + '}'
	twofmt = maketwofmt(cols)
	twofmt_tight = maketwofmt(cols_tight)

	vols = results['volumes']
	strens = results['strengths']

	postvol  = vols['postboil_attemp']
	total_water = results['mash']['total_water']
	if 'steal' in results:
		total_water = _Volume(total_water
		    + results['steal']['missing'])

	totibus = results['hop_stats']['ibu']
	print(onefmt.format('Name:', input['name']))
	print(twofmt_tight.format('Aggregate strength:', 'TBD',
	    'Package volume:', str(vols['package'])))
	print(twofmt_tight.format('Total fermentables:',
	    str(results['fermentable_stats_all']['amount']),
	    'Total hops:',
	    str(results['hop_stats']['mass'])))
	bugu = totibus / strens['final'].valueas(Strength.SG_PTS)
	print(twofmt_tight.format('IBU (Tinseth):',
	    '{:.2f}'.format(totibus), 'BUGU:', '{:.2f}'.format(bugu)))

	color = results['color']
	srm = color.valueas(color.SRM)
	ebc = color.valueas(color.EBC)
	if srm >= 10:
		prec = '0'
	else:
		prec = '1'
	ebcprec = '{:.' + prec + 'f}'
	srmprec = '{:.' + prec + 'f}'
	print(twofmt_tight.format('Boil:', str(input['boiltime']) + 'min',
	    'Yeast:', input['yeast']))
	print(twofmt_tight.format(
	    'Water (' + str(getparam('ambient_temp')) + '):',
	    str(total_water),
	    'Color (Morey):', ebcprec.format(ebc) + ' EBC, '
	    + srmprec.format(srm) + ' SRM'))
	print()

	if input['water_notes'] is not None or len(input['notes']) > 0:
		if input['water_notes'] is not None:
			prettyprint_withsugarontop('Water notes:',
			    cols[0], input['water_notes'],
			    sum(cols) - cols[0])
		for n in input['notes']:
			prettyprint_withsugarontop('Brewday notes:',
			    cols[0], n, sum(cols) - cols[0])
		print()

	print(twofmt.format('Preboil  volume  :',
	    str(vols['preboil_attemp'])
	    + ' (' + str(getparam('preboil_temp')) + ')',
	    'Measured:', ''))
	print(twofmt.format('Preboil  strength:', str(strens['preboil']),
	    'Measured:', ''))
	print(twofmt.format('Postboil volume  :', str(postvol)
	    + ' (' + str(getparam('postboil_temp')) + ')',
	    'Measured:', ''))
	print(twofmt.format('Postboil strength:', str(strens['postboil']),
	    'Measured:', ''))

	# various expected losses and brewhouse efficiency
	print()
	d1 = _Volume(vols['postboil'] - vols['fermentor'])
	d2 = _Volume(vols['fermentor'] - vols['package'])
	print(twofmt.format('Kettle loss (est):', str(d1),
	    'Fermenter loss (est):', str(d2)))

	print(twofmt.format('Mash eff (conf) :',
	    str(getparam('mash_efficiency')) + '%',
	    'Brewhouse eff (est):',
	    '{:.1f}%'.format(100 * results['brewhouse_efficiency'])))

	if not miniprint:
		print()
		unit = ' billion'
		print(twofmt.format('Pitch rate, ale:',
		    str(int(results['pitch']['ale'])) + unit,
		    'Pitch rate, lager:',
		    str(int(results['pitch']['lager'])) + unit))

	hd = results['hopsdrunk']
	if hd['package'] > 0:
		print()
		print('NOTE: package hops absorb: '
		    + str(hd['package'])
		    + ' => effective yield: '
		    + str(_Volume(vols['package'] - hd['package'])))

		# warn about larger packaging volume iff package dryhops
		# volume exceeds 1dl
		if hd['volume'] > 0.1:
			print('NOTE: package hop volume: ~'
			    + str(hd['volume']) + ' => packaged volume: '
			    + str(_Volume(vols['package'] + hd['volume'])))

	prtsep()

def _printattenuate(results):
	print('Speculative apparent attenuation and resulting ABV')
	prtsep()
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
	prtsep()
	print()

def printit(input, results, miniprint):
	_keystats(input, results, miniprint)
	ps = sysparams.getparamshorts()
	prettyprint_withsugarontop('', '', ps, 78, sep='|')
	prtsep()
	print()

	_printmash(input, results)
	_printboil(input, results)
	if not miniprint:
		_printattenuate(results)

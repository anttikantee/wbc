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

from WBC.Utils import prtsep, prettyprint_withsugarontop
from WBC.Getparam import getparam

from WBC import Constants, Sysparams

from WBC.WBC import WBC

# XXX: should not be needed in an ideal world
from WBC.Units import _Volume, _Mass, _Strength

def __reference_temp():
	return getparam('ambient_temp')

def _printmash(input, results):
	fmtstr = '{:34}{:>20}{:>12}{:>12}'
	print(fmtstr.format("Fermentables",
	    "amount", "ext (100%)", "ext ("
	    + str(int(getparam('mash_efficiency'))) + "%)"))
	prtsep()

	def handleonestage(stage):
		lst = [x for x in results['fermentables'] if x['when'] == stage]
		if len(lst) == 0:
			return

		print(stage.title())
		prtsep('-')

		for f in lst:
			persstr = ' ({:5.1f}%)'.format(f['percent'])
			print(fmtstr.format(f['name'],
			    str(f['amount']) + persstr,
			    str(f['extract_theoretical']),
			    str(f['extract_predicted'])))
		prtsep('-')
		stats = results['fermentable_stats_perstage'][stage]
		persstr = ' ({:5.1f}%)'.format(stats['percent'])
		print(fmtstr.format('',
		    str(stats['amount']) + persstr,
		    str(stats['extract_theoretical']),
		    str(stats['extract_predicted'])))

	for stage in WBC.stages:
		handleonestage(stage)
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
	print('Mashing instructions (ambient',
	    str(__reference_temp()) + yesnosparge)
	prtsep()

	totvol = 0
	for i, x in enumerate(results['mash']['steps']):
		# handle direct-heated mashtuns.
		# XXX: should probably be more rigorously structured
		# in the computation so that we don't need so much
		# logic here on the "dumb" output side
		if getparam('mlt_heat') == 'direct' and i != 0:
			print('{:7}'. format(str(x[0]))
			    + ': apply heat')
			continue

		print('{:7}'.format(str(x[0])) + ': add', x[2],
		    'of water at', str(x[3]), end=' ')

		# print the water/grist ratio at the step.
		if getparam('units_output') == 'metric':
			unit = 'l/kg'
			ratio = x[4]
		else:
			ratio = (x[4]*Constants.litersperquart) \
			    / (Constants.gramsperpound / 1000.0)
			unit = 'qt/lb'
		print('({:.2f} {:}, mash vol {:})'.format(ratio, unit, x[5]))

	print('{:23}{:}'.format('Mashstep water volume:',
	    str(results['mash']['mashstep_water']) + ' @ '
	    + str(__reference_temp())), end=' ')
	print('(potential first runnings: ~{:})'
	    .format(results['mash_first_runnings_max']))

	if spargevol > .001:
		print('{:23}{:}'.format('Sparge water volume:',
		    str(spargevol) + ' @ '
		    + str(getparam('sparge_temp'))))

	fw = results['mash_first_wort_max']
	fwstrs = []
	for x in [.85, .90, .95, 1.0]:
		fwstrs.append(str(_Strength(fw * x)) \
		    + ' (' + str(int(100 * x)) + '%)')
	print('{:23}{:}'. format('First wort (conv. %):',
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
	# XXX: IBU sum might not be sum of displayed hop additions
	# due to rounding.  cosmetic, but annoying.
	namelen = 33
	onefmt = '{:' + str(namelen) + '}{:7}{:>9}{:>11}{:>10}{:>8}'
	print(onefmt.format("Hops", "AA%", "timespec", "timer",
	    "amount", "IBUs"))
	prtsep()
	totmass = 0

	t = results['startboil_timer']
	if t is not None:
		print(onefmt.format('', '', '@ boil',
		    str(t) + ' min', '', ''))

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
		    timestr, h['timer'], str(mass), ibustr))
	prtsep()
	ibustr = ibufmt.format(results['ibus'])
	print(onefmt.format('', '', '', '', str(_Mass(totmass)), ibustr))
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

	print(onefmt.format('Name:', input['name']))
	print(twofmt_tight.format('Aggregate strength:', 'TBD',
	    'Package volume:', str(vols['package'])))
	bugu = results['ibus'] / strens['final']
	print(twofmt_tight.format('IBU (Tinseth):',
	    '{:.2f}'.format(results['ibus']), 'BUGU:', '{:.2f}'.format(bugu)))

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
	ps = Sysparams.getparamshorts()
	prettyprint_withsugarontop('', '', ps, 78, sep='|')
	prtsep()
	print()

	_printmash(input, results)
	_printboil(input, results)
	if not miniprint:
		_printattenuate(results)

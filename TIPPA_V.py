from WBC.WBC import Recipe, Hop
from WBC.Units import M, T, V, S
from WBC.Utils import setconfig

if __name__ == '__main__':
	setconfig('strength_input', 'plato')
	setconfig('strength_output', 'sg')
	setconfig('units_input', 'metric')

	r = Recipe(
		'TIPPA V',
		'WLP095 + US-05 (NENEIPA yeast cake, via TIPPA IV)',
		V(19.5),
		T(67)
	)

	r.fermentable_bypercent('Avangard Vienna', 100)
	r.set_strength(S(11))
	r.steal_preboil_wort(V(1.5), S(10))

	mb = Hop('Mandarina Bavaria', 7.3)

	r.hop_recipeIBU(mb,	20,		Hop.FWH)

	r.hop_bymass(mb,	M(20, M.G),	8)
	r.hop_bymass(mb,	M(20, M.G),	0)

	r.do()

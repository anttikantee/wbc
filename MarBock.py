from WBC.WBC import Recipe, Hop
from WBC.Units import M, T, V, S
from WBC.Utils import setconfig

if __name__ == '__main__':
	setconfig('strength_input', 'plato')
	#setconfig('strength_output', 'sg')
	setconfig('units_input', 'metric')

	r = Recipe(
		'MarBock',
		'WLP833',
		V(19.5),
		T(66),
		90
	)

	r.fermentable_bypercent('Avangard Pilsner', r.THEREST)
	r.fermentable_bypercent('Avangard Vienna', 15)
	r.fermentable_bypercent('Avangard Munich light', 10)
	r.anchor_bystrength(S(16.8))

	r.steal_preboil_wort(V(0.5), S(10))

	nb = Hop('Northern Brewer', 9.9)
	ht = Hop('Hallertau', 3.8)
	saaz = Hop('Saaz', 3.1, Hop.Leaf)

	r.hop_recipeIBU(nb,	36,		90)
	r.hop_bymass(saaz,	M(20, M.G),	30)
	r.hop_bymass(ht,	M(15, M.G),	15)

	r.do()

from WBC.WBC import Recipe, Hop
from WBC.Units import M, T, V, S
from WBC.Utils import setconfig

if __name__ == '__main__':
	setconfig('strength_input', 'plato')
	#setconfig('strength_output', 'sg')
	setconfig('units_input', 'metric')

	r = Recipe(
		'Musta Olut',
		'WLP833',
		V(19),
		T(65),
		60
	)

	r.fermentable_bypercent('Avangard Munich light', 50)
	r.fermentable_bypercent('Avangard Pilsner', r.THEREST)
	r.fermentable_bypercent('Weyermann Melanoidin', 5)
	r.fermentable_bypercent('Weyermann CaraMunich 3', 3)
	r.fermentable_bypercent('Weyermann Carafa 2', 3)
	r.fermentable_bypercent('Muntons Chocolate', 2.5)
	r.anchor_bystrength(S(13))

	ht = Hop('Hallertau', 3.8)
	nb = Hop('Northern Brewer', 9.9)

	r.hop_recipeIBU(nb,	22,		60)
	r.hop_bymass(ht,	M(20, M.G),	15)

	r.do()

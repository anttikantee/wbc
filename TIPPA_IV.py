from WBC.WBC import Recipe, Hop
from WBC.Units import M, T, V

if __name__ == '__main__':
	r = Recipe(
		'TIPPA IV',
		'WLP095 + US-05 (NENEIPA yeast cake)',
		V(19.5, V.LITER),
		T(65, T.degC)
	)

	r.fermentable_bymass('Crisp Maris Otter',	M(3.2, M.KG))
	r.fermentable_bymass('Avangard Munich Light',	M(450, M.G))

	mb = Hop('Mandarina Bavaria', 7.3)

	r.hop_bymass(mb, M(20, M.G), Hop.FWH)
	r.hop_bymass(mb, M(20, M.G), 12)
	r.hop_bymass(mb, M(20, M.G), 2)

	r.do()

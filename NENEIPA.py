from WBC.WBC import Recipe, Hop

from WBC.Units import M, V, T

if __name__ == '__main__':
	r = Recipe('NENEIPA', 'WLP095 + US-05', V(19.5, V.LITER), T(65, T.degC))

	r.fermentable_bymass('Crisp Maris Otter',	M(9, M.LB))
	r.fermentable_bymass('Simpsons Golden Promise',	M(1, M.LB))

	r.fermentable_bymass('Weyermann CaraMunich 1',	M(8, M.OZ))
	r.fermentable_bymass('Flaked wheat',		M(4, M.OZ))

	amarillo = Hop('Amarillo',	8.2)
	cascade9 = Hop('Cascade',	9.3)
	cascade7 = Hop('Cascade',	7.3,		type = Hop.Leaf)
	chinook = Hop('Chinook',	11.6)
	nugget = Hop('Nugget',		12.4)
	simcoe = Hop('Simcoe',		13.6)

	r.hop_bymass(chinook,	M(0.25,	M.OZ),	Hop.FWH)
	r.hop_bymass(simcoe,	M(1,	M.OZ),	30)
	r.hop_bymass(amarillo,	M(1,	M.OZ),	12)
	r.hop_bymass(cascade9,	M(.5,	M.OZ),	8)
	r.hop_bymass(nugget,	M(.5,	M.OZ),	8)
	r.hop_bymass(cascade9,	M(.5,	M.OZ),	Hop.Steep(T(90), 10))
	r.hop_bymass(nugget,	M(.5,	M.OZ),	Hop.Steep(T(90), 10))
	r.hop_bymass(amarillo,	M(1,	M.OZ),	Hop.Dryhop(3, 0))
	r.hop_bymass(cascade7,	M(1.5,	M.OZ),	Hop.Dryhop(3, 0))

	r.do()

#!/usr/bin/env python

from WBC.WBC import Recipe
from WBC.Units import Strength

def testme(vals, fun, ifun):
	for x in vals:
		v = fun(x)
		iv = ifun(v)
		diff = abs(x - iv)
		print x, v, iv, diff

if __name__ == '__main__':
	r = [x / 1000.0 for x in range(1001, 1100)]
	print 'SG to Plato'
	v = testme(r, Strength.sg_to_plato, Strength.plato_to_sg)

	print

	r = [x / 10.0 for x in range(0, 250, 2)]
	print 'Plato to SG'
	v = testme(r, Strength.plato_to_sg, Strength.sg_to_plato)

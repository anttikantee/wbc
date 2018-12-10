#!/usr/bin/env python

from WBC.WBC import Recipe
from WBC.Units import Strength

def testme(vals, fun, ifun):
	rv = []
	for x in vals:
		v = fun(x)
		iv = ifun(v)
		diff = abs(x - iv)
		rv.append((x, v, iv, diff))
	return rv

def prt(v):
	for x in v:
		print x[0], x[1], x[2], x[3]
	sv = sorted(v, key=lambda x: x[3], reverse=True)
	print 'max diff at', sv[0][0], '(' + str(sv[0][3]) + ')'

if __name__ == '__main__':
	r = [x / 1000.0 for x in range(1001, 1140)]
	print 'SG to Plato'
	v = testme(r, Strength.sg_to_plato, Strength.plato_to_sg)
	prt(v)

	print

	r = [x / 10.0 for x in range(0, 300, 2)]
	print 'Plato to SG'
	v = testme(r, Strength.plato_to_sg, Strength.sg_to_plato)
	prt(v)

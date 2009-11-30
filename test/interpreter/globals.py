import math
import unittest
from js.interpreter import run, GlobalObject

class IsFinite(unittest.TestCase):
	def test_isFinite(self):
		self.assertEqual(run("isFinite(0)"), True)
		self.assertEqual(run("isFinite(NaN)"), False)
		self.assertEqual(run("isFinite(Infinity)"), False)
		self.assertEqual(run("isFinite(-Infinity)"), False)

class IsNaN(unittest.TestCase):
	def test_isNaN(self):
		self.assertEqual(run("isNaN(0)"), False)
		self.assertEqual(run("isNaN(NaN)"), True)
		self.assertEqual(run("isNaN(Infinity)"), False)

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(IsFinite),
		unittest.TestLoader().loadTestsFromTestCase(IsNaN),
		])
	return suite


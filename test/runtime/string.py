import math
import unittest

from js.runtime import run, GlobalObject

class CharCodeAt(unittest.TestCase):
	def test_charCodeAt(self):
		self.assert_(math.isnan(run("'test'.charCodeAt(5)")))
		self.assert_(math.isnan(run("'test'.charCodeAt(-1)")))
		self.assertEqual(run("'test'.charCodeAt(0)"), 116)
		self.assertEqual(run("'test'.charCodeAt(2)"), 115)
		self.assertEqual(run("'test'.charCodeAt()"), 116)

class Substr(unittest.TestCase):
	def test_substr(self):
		self.assertEqual(run("'test'.substr(1,2)"), "es")
		self.assertEqual(run("'test'.substr(0,6)"), "test")
		self.assertEqual(run("'test'.substr(-3,1)"), "e")
		self.assertEqual(run("'test'.substr(2,4)"), "st")
		self.assertEqual(run("'test'.substr(3)"), "t")
		self.assertEqual(run("'test'.substr()"), "test")

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(CharCodeAt),
		unittest.TestLoader().loadTestsFromTestCase(Substr),
		])
	return suite


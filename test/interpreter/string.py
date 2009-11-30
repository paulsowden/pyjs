import math
import unittest
from js.interpreter import run, GlobalObject

class String(unittest.TestCase):
	def test_String(self):
		self.assertEqual(run("String(true)"), "true")
		self.assertEqual(run("String(false)"), "false")
		self.assertEqual(run("String('test')"), "test")
		self.assertEqual(run("String(NaN)"), "NaN")
		self.assertEqual(run("String(Infinity)"), "Infinity")
		self.assertEqual(run("String(null)"), "null")
		self.assertEqual(run("String(undefined)"), "undefined")
		self.assertEqual(run("String(+0)"), "0")
		self.assertEqual(run("String(-0)"), "0")
		self.assertEqual(run("String(1)"), "1")
		self.assertEqual(run("String(-2.3)"), "-2.3")

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
		unittest.TestLoader().loadTestsFromTestCase(String),
		unittest.TestLoader().loadTestsFromTestCase(CharCodeAt),
		unittest.TestLoader().loadTestsFromTestCase(Substr),
		])
	return suite


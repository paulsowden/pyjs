import unittest
from js.parser import JavaScriptSyntaxError
from js.runtime import run, GlobalObject

class LabelledStatement(unittest.TestCase):
	def test_missing_label(self):
		self.assertRaises(JavaScriptSyntaxError, run,
			"""top: for (var i = 0; i < 10; i++) {
				for (var j in Object) {
					continue bottom;
				}
			}""")

class For(unittest.TestCase):
	def test_for_in(self):
		self.assertEqual(run(
			"""var a = {a:1,b:2,c:3}, s = '';
			for (var key in a) { s = s + key; }"""), 'abc')
		self.assertEqual(run(
			"""var a = {a:1,b:2,c:3}, s = '';
			for (key in a) { s = s + key; }"""), 'abc')

		self.assertEqual(run(
			"""var a = {}; Object.prototype.a = 1; a.b = 1;
			Object.prototype.c = 1; a.d = 1; var s = '';
			for (var key in a) { s = s + key; }"""), 'bdac')

	def test_for_loop(self):
		self.assertEqual(run(
			'for (var i = 0; i < 10; i = i + 1) ; i'), 10)

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(LabelledStatement),
		unittest.TestLoader().loadTestsFromTestCase(For),
		])
	return suite


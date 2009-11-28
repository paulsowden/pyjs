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

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(LabelledStatement),
		])
	return suite


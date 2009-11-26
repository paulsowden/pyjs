
import unittest

from js.runtime import run, GlobalObject

class FunctionNames(unittest.TestCase):

	def testNamedDecleration(self):
		global_object = GlobalObject()
		run("function a (a) { return a; }", global_object)
		function = run("a", global_object)
		self.assert_(function)
		self.assertEqual(run("a(1)", global_object), 1)
		self.assertEqual(run("a", global_object), function)

	def testNamedExpression(self):
		global_object = GlobalObject()
		run("var b = function a () { return a; }", global_object)
		#self.assertRaises(Exception, run, "a", object)
		self.assertEqual(run("b", global_object), run("b()", global_object))

	def testArguments(self):
		self.assertEqual(run("(function () {return arguments.length})(1, 2)"), 2)
		self.assertEqual(run("(function () {return arguments[1]})(1, 2)"), 2)

def suite():
	suite = unittest.TestSuite(
		unittest.TestLoader().loadTestsFromTestCase(FunctionNames)
		)
	return suite

if __name__ == '__main__':
    unittest.main()



import unittest

from js.runtime import run, global_object

class FunctionNames(unittest.TestCase):

	def testNamedDecleration(self):
		object = global_object()
		run("function a (a) { return a; }", object)
		function = run("a", object)
		self.assert_(function)
		self.assertEqual(run("a(1)", object), 1)
		self.assertEqual(run("a", object), function)

	def testNamedExpression(self):
		object = global_object()
		run("var b = function a () { return a; }", object)
		#self.assertRaises(Exception, run, "a", object)
		self.assertEqual(run("b", object), run("b()", object))

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


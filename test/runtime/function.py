
import unittest

from js.runtime import run, GlobalObject

class Names(unittest.TestCase):

	def test_decleration(self):
		global_object = GlobalObject()
		run("function a (a) { return a; }", global_object)
		function = run("a", global_object)
		self.assert_(function)
		self.assertEqual(run("a(1)", global_object), 1)
		self.assertEqual(run("a", global_object), function)

	def test_expression(self):
		global_object = GlobalObject()
		run("var b = function a () { return a; }", global_object)
		#self.assertRaises(Exception, run, "a", object)
		self.assertEqual(run("b", global_object), run("b()", global_object))

class Arguments(unittest.TestCase):
	def test_arguments(self):
		self.assertEqual(run("(function () {return arguments.length})(1, 2)"), 2)
		self.assertEqual(run("(function () {return arguments[1]})(1, 2)"), 2)
		self.assertEqual(run("Object.prototype.a = 1;(function () {return arguments})(2).a"), 1)

		global_object = GlobalObject()
		self.assertEqual(run("function a () { return arguments.callee; }; a()", global_object), run("a", global_object))

class Call(unittest.TestCase):
	def test_call(self):
		self.assertEqual(run("function a(){return 1};a.call()"), 1)
		self.assertEqual(run("function a(){return 1};a.call(a)"), 1)
		self.assertEqual(run("function a(){return 1};a.call.call(a)"), 1)
		self.assertEqual(run("function a(){return arguments.length};a.call()"), 0)
		self.assertEqual(run("function a(){return arguments.length};a.call(a)"), 0)
		self.assertEqual(run("function a(){return arguments.length};a.call(a, 2)"), 1)
		self.assertEqual(run("function a(){return arguments.length};a.call(a, 2, 4)"), 2)

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(Names),
		unittest.TestLoader().loadTestsFromTestCase(Arguments),
		unittest.TestLoader().loadTestsFromTestCase(Call),
		])
	return suite

if __name__ == '__main__':
    unittest.main()


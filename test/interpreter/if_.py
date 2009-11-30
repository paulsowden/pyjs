import unittest
from js.interpreter import run, GlobalObject

class ElsePrecedence(unittest.TestCase):

	js = """
	function a (a, b) {
		if (a) {
			if (b) { return 1; } else { return 2; }
		}
		return 3;
	}

	function b (a, b) {
		if (a) {
			if (b) { return 1; }
		} else {
			return 2;
		}
		return 3;
	}

	function c (a, b) {
		if (a)
			if (b) return 1;
			else return 2;
		return 3;
	}
	"""

	def testPrecedence(self):
		global_object = GlobalObject()
		run(self.js, global_object)

		self.assertEqual(run("a(0,0)", global_object), 3);
		self.assertEqual(run("b(0,0)", global_object), 2);
		self.assertEqual(run("c(0,0)", global_object), 3);

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(ElsePrecedence)
		])
	return suite

if __name__ == '__main__':
    unittest.main()



import unittest

from js.runtime import run, global_object

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
		object = global_object()
		run(self.js, object)

		self.assertEqual(run("a(0,0)", object), 3);
		self.assertEqual(run("b(0,0)", object), 2);
		self.assertEqual(run("c(0,0)", object), 3);

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(ElsePrecedence)
		])
	return suite

if __name__ == '__main__':
    unittest.main()


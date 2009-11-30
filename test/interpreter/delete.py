import unittest
from js.interpreter import run, GlobalObject

class Delete(unittest.TestCase):

	def testDelete(self):
		self.assertEqual(run("delete undefined"), False)
		self.assertEqual(run("delete undefined; undefined"), None)
		self.assertEqual(run("delete String"), True)
		#self.assertRaises(Exception, run, "delete String; String")
		self.assertEqual(run("a={a:1}; delete a.a; 'a' in a"), False)

def suite():
	suite = unittest.TestSuite(
		unittest.TestLoader().loadTestsFromTestCase(Delete)
		)
	return suite


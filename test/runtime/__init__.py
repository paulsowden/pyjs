
import unittest

import function, if_, delete

def suite():
	suite = unittest.TestSuite([
		function.suite(),
		if_.suite(),
		delete.suite(),
		])
	return suite

if __name__ == '__main__':
	unittest.TextTestRunner(verbosity=2).run(suite())


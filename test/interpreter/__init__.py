
import unittest

import function, if_, delete, string, globals, for_

def suite():
	suite = unittest.TestSuite([
		function.suite(),
		if_.suite(),
		delete.suite(),
		string.suite(),
		globals.suite(),
		for_.suite(),
		])
	return suite

if __name__ == '__main__':
	unittest.TextTestRunner(verbosity=2).run(suite())

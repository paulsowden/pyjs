import sys, os
# js is in the parent directory
sys.path.insert(0,
	os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import runtime

if __name__ == '__main__':
	suite = unittest.TestSuite([runtime.suite()])
	unittest.TextTestRunner(verbosity=2).run(suite)


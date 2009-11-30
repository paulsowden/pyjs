import sys, os
# js is in the parent directory
sys.path.insert(0,
	os.path.normpath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import interpreter

if __name__ == '__main__':
	suite = unittest.TestSuite([interpreter.suite()])
	unittest.TextTestRunner(verbosity=2).run(suite)


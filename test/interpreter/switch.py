import unittest
from js.parser import JavaScriptSyntaxError
from js.interpreter import run, GlobalObject

class SwitchStatement(unittest.TestCase):
	def test_switch_fallthrough(self):
		js =  """
var var1 = "match string";
var match1 = false;
var match2 = false;
var match3 = false;

switch (var1)
{
case "match string":
  match1 = true;
case "bad string 1":
  match2 = true;
  break;
case "bad string 2":
  match3 = true;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("match1", global_object), True)
		self.assertEquals(run("match2", global_object), True)
		self.assertEquals(run("match3", global_object), False)

	def test_nested_switch(self):
		js = """
var var2 = 3;

var match1 = false;
var match2 = false;
var match3 = false;
var match4 = false;
var match5 = false;

switch (var2)
{
case 1:
  switch (var1)
  {
  case "foo":
  match1 = true;
  break;
  case 3:
  match2 = true;
  break;
  }
  match3 = true;
  break;
case 2:
  match4 = true;
  break;
case 3:
  match5 = true;
  break;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("match1", global_object), False)
		self.assertEquals(run("match2", global_object), False)
		self.assertEquals(run("match3", global_object), False)
		self.assertEquals(run("match4", global_object), False)
		self.assertEquals(run("match5", global_object), True)

	def test_return_in_switch(self):
		js = """
// test defaults not at the end; regression test for a bug that
// nearly made it into 4.06
function f0(i) {
  switch(i) {
  default:
  case "a":
  case "b":
    return "ab*"
      case "c":
    return "c";
  case "d":
    return "d";
  }
  return "";
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("f0('a')", global_object), 'ab*')
		self.assertEquals(run("f0('b')", global_object), 'ab*')
		self.assertEquals(run("f0('*')", global_object), 'ab*')
		self.assertEquals(run("f0('c')", global_object), 'c')
		self.assertEquals(run("f0('d')", global_object), 'd')

	def test_return_in_switch2(self):
		js = """
function f1(i) {
  switch(i) {
  case "a":
  case "b":
  default:
    return "ab*"
      case "c":
    return "c";
  case "d":
    return "d";
  }
  return "";
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("f1('a')", global_object), 'ab*')
		self.assertEquals(run("f1('b')", global_object), 'ab*')
		self.assertEquals(run("f1('*')", global_object), 'ab*')
		self.assertEquals(run("f1('c')", global_object), 'c')
		self.assertEquals(run("f1('d')", global_object), 'd')

	def test_switch_on_integer(self):
		js = """
function f2(i) {
  switch (i) {
  case 0:
  case 1:
    return 1;
  case 2:
    return 2;
  }
  // with no default, control will fall through
  return 3;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("f2(0)", global_object), 1)
		self.assertEquals(run("f2(1)", global_object), 1)
		self.assertEquals(run("f2(2)", global_object), 2)
		self.assertEquals(run("f2(3)", global_object), 3)

	def test_empty_switch(self):
		js = """
// empty switch: make sure expression is evaluated
var se = 0;
switch (se = 1) {
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("se", global_object), 1)

	def test_only_default(self):
		js = """
// only default
se = 0;
switch (se) {
default:
  se = 1;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("se", global_object), 1)

	def test_break_for_loop(self):
		js = """
// in loop, break should only break out of switch
se = 0;
for (var i=0; i < 2; i++) {
  switch (i) {
  case 0:
  case 1:
    break;
  }
  se = 1;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("se", global_object), 1)

	def test_switch_fallthrough2(self):
		js = """
// test "fall through"
se = 0;
i = 0;
switch (i) {
case 0:
  se++;
  /* fall through */
case 1:
  se++;
  break;
}
"""
		global_object = GlobalObject()
		run(js, global_object)
		self.assertEquals(run("se", global_object), 2)

def suite():
	suite = unittest.TestSuite([
		unittest.TestLoader().loadTestsFromTestCase(SwitchStatement),
		])
	return suite


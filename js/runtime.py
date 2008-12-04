
from builtins import *

null = object()


def toPrimitive(value, preferred=None):
	if value == null or value == None or isinstance(value, float) \
			or isinstance(value, str) or isinstance(value, bool):
		return value
	return value.default_value(preferred)

def toBoolean(value):
	return not (value == null or value == None
		or isinstance(value, float) and value == 0
		or isinstance(value, str) and len(str) == 0)

def toNumber(value):
	if value == null:
		return 0
	if isinstance(value, float):
		return value
	# TODO
	return float(value)

def typeof(value):
	if value == None:
		return 'undefined'
	if value == null:
		return 'null'
	if isinstance(value, bool):
		return 'boolean'
	if isinstance(value, str):
		return 'string'
	if isinstance(value, float):
		return 'number'
	return 'object'

def toString(value):
	type = typeof(value)
	if type == 'boolean':
		return value and 'true' or 'false'
	if type == 'string':
		return value
	if type == 'number':
		return str(value) # TODO
	if type == 'object':
		return toString(toPrimitive(value, 'string'))
	return object

def toObject(value):
	if value == None or value == null:
		raise JavaScriptTypeError()
	if isinstance(value, bool):
		return JavaScriptBoolean(value)
	if isinstance(value, float):
		return JavaScriptNumber(value)
	if isinstance(value, str):
		return JavaScriptString(value)
	return value

class Reference(object):
	def __init__(self, base, property_name):
		self.base = base
		self.property_name = property_name

def getValue(v):
	if isinstance(v, Reference):
		if not v.base:
			raise JavaScriptReferenceError()
		return v.base[v.property_name]
	return v

def putValue(v, w, c):
	if not isinstance(v, Reference):
		raise JavaScriptReferenceError()
	if not v.base:
		c.top.scope.object[v.property_name] = w
	else:
		v.base[v.property_name] = w


class Scope(object):
	def __init__(self, parent=None):
		self.object = BaseObject()
		self.parent = parent


class ExecutionContext(object):

	def __init__(self, context, top=None, this=None, scope=None, parent_scope=None):
		self.scope = scope or Scope(parent_scope)
		self.top = top or self
		self.this = this or self.top.scope.object

		variables = self.scope.object
		if hasattr(context, 'params'):
			pass # add the arguments to the variables
		for name, function in context.functions.values():
			variables[name] = function
		for name in context.vars:
			if name not in variables:
				variables[name] = None


def execute(s, c):
	"executes symbol `s` in context `c`"

	if s.id == 'var':
		for var in s.first:
			if var.id == '(identifier)': continue
			execute(var, c) # assignment
		return None

	elif s.id == 'this':
		return c.this
	elif s.id == '(identifier)':
		scope = c.scope
		while scope:
			if s.value in scope.object:
				break
			scope = scope.parent
		return Reference(scope and scope.object, s.value)

	## literals
	elif s.id == '(number)':
		return float(s.value)
	elif s.id == '(string)':
		return s.value[1:-1]
	elif s.id == '(regexp)':
		pass # TODO
	elif s.id == 'null':
		return null
	elif s.id == 'undefined':
		return None

	elif s.id == '[':
		if isinstance(s.id, list): # array
			array = JavaScriptArray()
			return array
		else: # property
			l = getValue(execute(s.first, c))
			r = getValue(execute(s.second, c))
			return Reference(toObject(l), toString(r))

	elif s.id == '{':
		array = JavaScriptObject()
		return array

	elif s.id == '.':
		return Reference(toObject(getValue(execute(s.first, c))), s.second.value)

	elif s.id == 'new':
		l = getValue(execute(s.first.first, c))
		if typeof(l) != 'object':
			raise JavaScriptTypeError()
		# TODO

	elif s.id == 'typeof':
		l = execute(s.first, c)
		if isinstance(l, Reference) and l.base == None:
			return 'undefined'
		type = typeof(getValue(l))
		if type == 'object':
			pass # TODO check for functions
		return type

	elif s.id == '!':
		return not toBoolean(getValue(execute(s.first, c)))

	elif s.id == '=':
		l = execute(s.first, c)
		r = getValue(execute(s.second, c))
		putValue(l, r, c)
		return r

	elif s.id == '/':
		return getValue(execute(s.first, c)) / getValue(execute(s.second, c))
	elif s.id == '*':
		return getValue(execute(s.first, c)) * getValue(execute(s.second, c))
	elif s.id == '+':
		return getValue(execute(s.first, c)) + getValue(execute(s.second, c))
	elif s.id == '-':
		return getValue(execute(s.first, c)) - getValue(execute(s.second, c))
	elif s.id == '%':
		return getValue(execute(s.first, c)) % getValue(execute(s.second, c))

	raise RuntimeError, "unknown operation %s" % s.id


def run(context):
	v = None
	c = ExecutionContext(context)
	for s in context.first:
		v = execute(s, c)
	return getValue(v)



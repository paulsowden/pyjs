
from builtins import *


def typeof(value):
	if value is None:
		return 'undefined'
	if value is null:
		return 'null'
	if isinstance(value, bool):
		return 'boolean'
	if isinstance(value, str):
		return 'string'
	if isinstance(value, float):
		return 'number'
	return 'object'

def toPrimitive(value, preferred=None):
	if value is null or value is None or isinstance(value, float) \
			or isinstance(value, str) or isinstance(value, bool):
		return value
	return value.default_value(preferred)

def toBoolean(value):
	return not (value is null or value is None or value is False
		or isinstance(value, float) and value == 0
		or isinstance(value, str) and len(str) == 0)

def toNumber(value):
	if value is null:
		return 0
	if isinstance(value, float):
		return value
	# TODO
	return float(value)

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
	if value is None or value is null:
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
			variables.get(name).dont_delete = True
		for name in context.vars:
			if name not in variables:
				variables[name] = None
				variables.get(name).dont_delete = True


def execute(s, c):
	"executes symbol `s` in context `c`"

	if isinstance(s, list) or s.id == '{': # block statement
		if not isinstance(s, list):
			s = s.first
		if len(s) == 0:
			return ('normal', None, None)
		for statement in s:
			try:
				v = execute(statement, c)
			except BaseObject, e:
				return ('throw', e, None)
			if v[0] != 'normal':
				return v
		return v


	## Primary Expressions
	elif s.id == 'this':
		return c.this
	elif s.id == '(identifier)':
		scope = c.scope
		while scope:
			if s.value in scope.object:
				break
			scope = scope.parent
		return Reference(scope and scope.object, s.value)

	# literals
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
	elif s.id == 'true':
		return True
	elif s.id == 'false':
		return False

	elif s.id == '(array)':
		array = JavaScriptArray()
		return array

	elif s.id == '(object)':
		o = JavaScriptObject()
		for k, v in s.first:
			if k.id == '(identifier)':
				key = k.value
			elif k.id == '(number)':
				key = toString(execute(k, c))
			else: # (string)
				key = execute(k, c)
			o[key] = getValue(execute(v, c))
		return o


	## Left-Hand Expressions

	elif s.id == '.':
		return Reference(toObject(getValue(execute(s.first, c))), s.second.value)
	elif s.id == '[': # property
		l = getValue(execute(s.first, c))
		r = getValue(execute(s.second, c))
		return Reference(toObject(l), toString(r))

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


	## Statements
	if s.id == '(statement)':
		v = execute(s.first, c)
		if isinstance(v, tuple):
			return v
		else:
			return ('normal', v, None)
	if s.id == 'var':
		for var in s.first:
			if var.id == '(identifier)': continue
			execute(var, c) # assignment
		return ('normal', None, None)

	elif s.id == 'if':
		if toBoolean(getValue(execute(s.first, c))):
			return execute(s.second, c)
		elif s.third:
			return execute(s.third, c)
		else:
			return ('normal', None, None)

	elif s.id == 'do':
		t = True
		while t:
			v = execute(s.first, c)
			if v[0] == 'continue' and v[2]:
				return # TODO GOTO
			elif v[0] == 'break' and v[2]:
				return ('normal', v[1], None)
			elif v[0] != 'normal':
				return v
			t = toBoolean(getValue(execute(s.second, c)))
		return ('normal', v[1], None)

	elif s.id == 'while':
		v = None
		while toBoolean(getValue(execute(s.second, c))):
			v = execute(s.first, c)
			if v[0] == 'continue' and v[2]:
				return # TODO GOTO
			elif v[0] == 'break' and v[2]:
				return ('normal', v[1], None)
			elif v[0] != 'normal':
				return v
		return ('normal', v[1], None)
	elif s.id == 'for':
		pass

	elif s.id == 'continue':
		if s.first:
			pass
	elif s.id == 'break':
		if s.first:
			pass
	elif s.id == 'return':
		if not s.first:
			return ('return', None, None)
		return ('return', execute(s.first, c), None)
	elif s.id == 'with':
		pass
	elif s.id == 'switch':
		pass
	elif s.id == 'throw':
		pass
	elif s.id == 'try':
		pass
	elif s.id == 'function':
		f = JavaScriptFunction()

		f['length'] = len(s.params)
		f.get('length').dont_delete = True
		f.get('length').read_only = True
		f.get('length').dont_enum = True

		f['prototype'] = JavaScriptObject()
		f.get('prototype').dont_delete = True

		f['prototype']['constructor'] = f
		f['prototype'].get('constructor').dont_enum = True

		f.symbol = s
		return f

	raise RuntimeError, "unknown operation %s" % s.id


def run(context):
	v = None
	c = ExecutionContext(context)

	for s in context.first:
		v = execute(s, c)
	return getValue(v[1])



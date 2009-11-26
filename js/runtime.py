from math import isinf, isnan, copysign
from parser import parse_str

null = object()
inf = float('inf')
neginf = float('-inf')
nan = float('nan')

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
	if isinstance(value, int):
		return float(value)
	return value.default_value(preferred)

def toBoolean(value):
	return not (value is null or value is None or value is False
		or isinstance(value, float) and value == 0
		or isinstance(value, str) and len(str) == 0)

def toNumber(value):
	if value is None:
		return nan
	if value is null:
		return 0
	if isinstance(value, bool):
		return 1 if value else 0
	if isinstance(value, float):
		return value
	if isinstance(value, basestring):
		return float(value) # TODO
	return toNumber(toPrimitive(value, 'number'))

def toInteger(value):
	value = toNumber(value)
	if isnan(value) or value == 0:
		return 0
	if isinf(value):
		return value
	return int(copysign(1, value) * (abs(value) // 1))

def toString(value):
	type = typeof(value)
	if type == 'boolean':
		return value and 'true' or 'false'
	if type == 'string':
		return value
	if type == 'number':
		if isnan(value):
			return 'NaN'
		if isinf(value):
			return 'Infinity'
		return str(value if value % 1 != 0 else int(value)) # TODO
	if type == 'object':
		return toString(toPrimitive(value, 'string'))
	return type

def toRepr(value):
	type = typeof(value)
	if type == 'string':
		return '"%s"' % value
	return toString(value)

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

def lessThan(x, y):
	x, y = toPrimitive(x, 'number'), toPrimitive(y, 'number')
	if typeof(x) != 'string' or typeof(y) != 'string':
		x, y = toNumber(x), toNumber(y)
		if x == y:
			return False
		# TODO NaN, Infinity checks
		return x < y
	# string comparison
	if x.startswith(y):
		return False
	if y.startswith(x):
		return True
	for i in range(len(x)):
		if ord(x[i]) < ord(y[i]):
			return True
		elif ord(x[i]) > ord(y[i]):
			return False


class Reference(object):
	def __init__(self, base, property_name):
		self.base = base
		self.property_name = property_name
	def __repr__(self):
		return '<Reference %s %s>' % (self.base, self.property_name)

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
		c.global_object[v.property_name] = w
	else:
		v.base[v.property_name] = w


class Scope(object):
	def __init__(self, parent=None, object=None):
		self.parent = parent
		self.object = object or BaseObject()


class ExecutionContext(object):
	def __init__(self, scope, this=None, global_object=None):
		self.scope = scope
		self.this = this or global_object
		self.global_object = global_object
	def instantiate_variables(self, s, vars):
		if s.id == 'function':
			args = vars['arguments']
			for i, param in enumerate(s.params):
				name = param.value
				vars.put(param.value, args[str(i)], dont_delete=True)
		for name, function_decl in s.functions.items():
			vars.put(name.value, execute(function_decl, self),
				dont_delete=True)
		for name in s.vars:
			if name not in vars:
				vars.put(name, None, dont_delete=True)

class Property(object):
	read_only = False
	dont_enum = False
	dont_delete = False
	internal = False
	def __init__(self, value, read_only=False, dont_enum=False, dont_delete=False):
		self.value = value
		if read_only: self.read_only = True
		if dont_enum: self.dont_enum = True
		if dont_delete: self.dont_delete = True


class BaseObject(object):
	name = 'Object' # [[Class]]
	prototype = None # [[Prototype]]

	def __init__(self):
		self.properties = {}

	def __getitem__(self, key): # [[Get]]
		if key in self.properties:
			return self.properties[key].value
		if not self.prototype:
			return None
		return self.prototype[key]

	def get(self, key):
		if key in self.properties:
			return self.properties[key]
		if not self.prototype:
			return None
		return self.prototype.get(key)

	def __setitem__(self, key, value): # [[Put]]
		if not self.can_put(key):
			return False
		if key in self.properties:
			self.properties[key].value = value
		self.properties[key] = Property(value)
		return value

	def put(self, key, value, read_only=False, dont_enum=False, dont_delete=False):
		if key in self.properties:
			prop = self.properties[key]
			prop.value = value
			prop.read_only = read_only
			prop.dont_enum = dont_enum
			prop.dont_delete = dont_delete
		else:
			self.properties[key] = Property(value, read_only, dont_enum, dont_delete)
		return value

	def __delitem__(self, key): # [[Delete]]
		if key not in self.properties:
			return True
		if self.properties[key].dont_delete:
			return False
		del self.properties[key]
		return True

	def __contains__(self, key): # [[HasProperty]]
		return (key in self.properties) or self.prototype and (key in self.prototype)

	def can_put(self, key): # [[CanPut]]
		if key in self.properties:
			return not self.properties[key].read_only
		if self.prototype:
			return self.prototype.can_put(key)
		return True

	def default_value(self, hint=None): # [[DefaultValue]]
		to_string = self['toString']
		if hasattr(to_string, 'call'):
			return to_string.call(self, [], None)
		value_of = self['valueOf']
		# TODO
		return None


class Activation(BaseObject):
	pass


class BuiltinFunction(BaseObject):
	def __init__(self, fn):
		BaseObject.__init__(self)
		self.fn = fn
	def call(self, this, args, c):
		return self.fn(*[this, args, c])
	@property
	def name(self):
		return self.fn.__name__

def proto(prototype): # decorator
	def bind(fn):
		prototype[fn.__name__] = BuiltinFunction(fn)
	return bind


## Native Objects

class JavaScriptObject(BaseObject):
	name = 'Object'
	prototype = BaseObject()

	@proto(prototype)
	def toString(this, args, c):
		return '[object %s]' % this.name

class ArgumentsObject(JavaScriptObject):
	prototype = JavaScriptObject.prototype
	def __init__(self, args, callee):
		super(ArgumentsObject, self).__init__()
		self.put('length', len(args), dont_enum=True)
		self.put('callee', callee, dont_enum=True)
		for i, arg in enumerate(args):
			self.put(str(i), arg, dont_enum=True)

class JavaScriptFunction(JavaScriptObject):
	name = 'Function'
	prototype = JavaScriptObject()
	def __init__(self, s, scope):
		JavaScriptObject.__init__(self)

		self.symbol = s
		self.scope = scope

		self.put('length', float(len(s.params)), True, True, True)
		self.put('prototype', JavaScriptObject(), dont_delete=True)
		self['prototype'].put('constructor', self, dont_enum=True)

	def call(self, this, args, context):
		activation = Activation()
		activation.put('arguments', ArgumentsObject(args, self),
			dont_delete=True)
		c = ExecutionContext(
			Scope(self.scope, activation), this, context.global_object)
		c.instantiate_variables(self.symbol, activation)
		v = execute(self.symbol.block, c)
		if v[0] == 'throw':
			raise v[1]
		if v[0] == 'return':
			return v[1]
		else: # normal
			return None

	def construct(self, args, context):
		o = JavaScriptObject()
		if isinstance(self['prototype'], BaseObject):
			o.prototype = self['prototype']
		v = self.call(o, args, context)
		if typeof(v) == 'object':
			return v
		return o

	def has_instance(self, v):
		if not isinstance(v, JavaScriptObject):
			return False
		o = self['prototype']
		if not isinstance(o, JavaScriptObject):
			raise JavaScriptTypeError()
		while hasattr(v, 'prototype'):
			v = v.prototype
			if o == v:
				return True
		return False

class JavaScriptArray(JavaScriptObject):
	name = 'Array'
	prototype = JavaScriptObject()

class JavaScriptString(JavaScriptObject):
	name = 'String'
	prototype = JavaScriptObject()
	def __init__(self, value=''):
		JavaScriptObject.__init__(self)
		self.value = value
		self.put('length', float(len(value)), True, True, True)

	@proto(prototype)
	def toString(this, args, c):
		if not isinstance(this, JavaScriptString):
			raise JavaScriptTypeError()
		return this.value

	@proto(prototype)
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptString):
			raise JavaScriptTypeError()
		return this.value

	@proto(prototype)
	def charAt(this, args, c):
		s = toString(this)
		n = len(args) and toInteger(args[0]) or 0
		if n < 0 or n > len(s):
			return ''
		else:
			return s[n]

	@proto(prototype)
	def charCodeAt(this, args, c):
		s = toString(this)
		n = len(args) and toInteger(args[0]) or 0
		if n < 0 or n > len(s):
			return nan
		else:
			return float(ord(s[n]))

	@proto(prototype)
	def concat(this, args, c):
		return toString(this) + ''.join(toString(arg) for arg in args)

	@proto(prototype)
	def slice(this, args, c):
		s = toString(this)
		n1 = len(args) and toInteger(args[0]) or 0
		if n1 < 0:
			n1 = max(n1+len(s), 0)
		else:
			n1 = min(len(s), n1)
		n2 = len(args) > 1 and toInteger(args[1]) or 0
		if n2 < 0:
			n2 = max(n2+len(s), 0)
		else:
			n2 = min(len(s), n2)
		return s[n1:n1+max(n2-n1,0)]

	@proto(prototype)
	def substr(this, args, c):
		s = toString(this)
		start = toInteger(args[0] if len(args) else None)
		length = args[1] if len(args) > 1 else None
		if length is not None:
			length = toInteger(length)
		else:
			length = inf
		if start < 0:
			start = max(len(s) + start, 0)
		length = min(max(length, 0), len(s) - start)
		return s[start:start + length]

	@proto(prototype)
	def toLowerCase(this, args, c):
		return toString(this).lower()

	@proto(prototype)
	def toUpperCase(this, args, c):
		return toString(this).upper()

class JavaScriptBoolean(JavaScriptObject):
	name = 'Boolean'
	prototype = JavaScriptObject()
	def __init__(self, value=False):
		JavaScriptObject.__init__(self)
		self.value = value

	@proto(prototype)
	def toString(this, args, c):
		if not isinstance(this, JavaScriptBoolean):
			raise JavaScriptTypeError()
		return toString(this.value)

	@proto(prototype)
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptBoolean):
			raise JavaScriptTypeError()
		return this.value

class JavaScriptNumber(JavaScriptObject):
	name = 'Number'
	prototype = JavaScriptObject()
	def __init__(self, value=0.0):
		self.value = value

class JavaScriptDate(JavaScriptObject):
	name = 'Date'
	prototype = JavaScriptObject()

class JavaScriptRegExp(JavaScriptObject):
	name = 'RegExp'
	prototype = JavaScriptObject()


## Errors

class JavaScriptError(JavaScriptObject):
	name = 'Error'
	prototype = JavaScriptObject()
	def __str__(self):
		return '%s: %s' % (self.name, toString(self['message']))

class JavaScriptEvalError(JavaScriptError):
	name = 'EvalError'
	prototype = JavaScriptError()

class JavaScriptRangeError(JavaScriptError):
	name = 'RangeError'
	prototype = JavaScriptError()

class JavaScriptReferenceError(JavaScriptError):
	name = 'ReferenceError'
	prototype = JavaScriptError()

class JavaScriptSyntaxError(JavaScriptError):
	name = 'SyntaxError'
	prototype = JavaScriptError()

class JavaScriptTypeError(JavaScriptError):
	name = 'TypeError'
	prototype = JavaScriptError()

class JavaScriptURIError(JavaScriptError):
	name = 'URIError'
	prototype = JavaScriptError()


## Global Scope

class BuiltinObject(JavaScriptFunction):
	def __init__(self):
		BaseObject.__init__(self)
		self.put('prototype', JavaScriptObject.prototype, True, True, True)
		self['prototype']['constructor'] = self
	def call(self, this, args, c):
		if len(args) == 0:
			o = JavaScriptObject()
		else:
			o = args[0]
		return toObject(o)

class BuiltinString(JavaScriptFunction):
	def __init__(self):
		BaseObject.__init__(self)
		self.put('prototype', JavaScriptString.prototype, True, True, True)
		self['prototype']['constructor'] = self

		@proto(self)
		def fromCharCode(this, args, c):
			return ''.join(chr(toInteger(arg)) for arg in args)

	def call(self, this, args, c):
		if len(args) == 0:
			s = ''
		else:
			s = args[0]
		return toString(s)
	def construct(self, args, c):
		if len(args):
			s = toString(args[0])
		else:
			s = ''
		return JavaScriptString(s)

class BuiltinBoolean(JavaScriptFunction):
	def __init__(self):
		BaseObject.__init__(self)
		self.put('prototype', JavaScriptBoolean.prototype, True, True, True)
		self['prototype']['constructor'] = self
	def call(self, this, args, c):
		if len(args):
			b = toBoolean(args[0])
		else:
			b = False
		return b
	def construct(self, args, c):
		if len(args):
			b = toBoolean(args[0])
		else:
			b = False
		return JavaScriptBoolean(b)

def builtin(fn):
	return BuiltinFunction(fn)

class GlobalObject(BaseObject):
	def __init__(self):
		super(GlobalObject, self).__init__()

		self.put('NaN', nan, dont_delete=True, dont_enum=True)
		self.put('Infinity', inf, dont_delete=True, dont_enum=True)
		self.put('undefined', None, dont_delete=True, dont_enum=True)

		self.put('Object', BuiltinObject(), dont_enum=True)
		self.put('String', BuiltinString(), dont_enum=True)
		self.put('Boolean', BuiltinBoolean(), dont_enum=True)

		builtin_function = lambda fn: self.put(fn.name, fn)
		builtin_function(self.isNaN)
		builtin_function(self.isFinite)

	@builtin
	def isNaN(this, args, c):
		return isnan(toNumber(args[0] if len(args) else None))

	@builtin
	def isFinite(this, args, c):
		n = toNumber(args[0] if len(args) else None)
		return not isinf(n) and not isnan(n)

## Execute

def execute(s, c):
	"executes symbol `s` in context `c`"

	#print s
	if isinstance(s, list) or s.id == '{': # block statement
		if not isinstance(s, list):
			s = s.block
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
		return s.value
	elif s.id == '(regexp)':
		pass # TODO
	elif s.id == 'null':
		return null
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
		l = getValue(execute(s.first, c))
		if typeof(l) != 'object' or not hasattr(l, 'construct'):
			raise JavaScriptTypeError()
		if hasattr(s, 'params'):
			args = [getValue(execute(arg, c)) for arg in s.params]
		else:
			args = []
		return l.construct(args, c)

	elif s.id == '(':
		o = execute(s.first, c)
		args = [getValue(execute(arg, c)) for arg in s.params]
		f = getValue(o)
		if typeof(f) != 'object' or not hasattr(f, 'call'):
			raise JavaScriptTypeError()
		this = o.base if isinstance(o, Reference) else None
		if this and isinstance(this, Activation):
			this = None
		return f.call(this, args, c)

	## Unary Operators
	elif s.id == 'typeof':
		l = execute(s.first, c)
		if isinstance(l, Reference) and l.base == None:
			return 'undefined'
		o = getValue(l)
		type = typeof(o)
		if type == 'object' and hasattr(o, 'call'):
			return 'function'
		return type
	elif s.id == 'void':
		l = getValue(execute(s.first, c))
		return None
	elif s.id == 'delete':
		l = execute(s.first, c)
		if not isinstance(l, Reference):
			return True
		return l.base.__delitem__(l.property_name)
	elif s.id == '+' and hasattr(s, 'arity'): # unary
		return toNumber(getValue(execute(s.first, c)))
	elif s.id == '-' and hasattr(s, 'arity'): # unary
		return -toNumber(getValue(execute(s.first, c)))
	elif s.id == '~':
		pass
	elif s.id == '!':
		return not toBoolean(getValue(execute(s.first, c)))

	elif s.id == '=':
		l = execute(s.first, c)
		r = getValue(execute(s.second, c))
		putValue(l, r, c)
		return r

	## Multiplicative Operators
	elif s.id == '/':
		return toNumber(getValue(execute(s.first, c))) / toNumber(getValue(execute(s.second, c)))
	elif s.id == '*':
		return toNumber(getValue(execute(s.first, c))) * toNumber(getValue(execute(s.second, c)))
	elif s.id == '%':
		return toNumber(getValue(execute(s.first, c))) % toNumber(getValue(execute(s.second, c)))

	## Additive Operators
	elif s.id == '+':
		return getValue(execute(s.first, c)) + getValue(execute(s.second, c))
	elif s.id == '-':
		return getValue(execute(s.first, c)) - getValue(execute(s.second, c))

	## Relational Operators
	elif s.id == '<':
		r = lessThan(getValue(execute(s.first, c)), getValue(execute(s.second, c)))
		if r == None:
			return False
		return r
	elif s.id == '>':
		r = lessThan(getValue(execute(s.second, c)), getValue(execute(s.first, c)))
		if r == None:
			return False
		return r
	elif s.id == '<=':
		r = lessThan(getValue(execute(s.second, c)), getValue(execute(s.first, c)))
		if r == None:
			return False
		return not r
	elif s.id == '>=':
		r = lessThan(getValue(execute(s.first, c)), getValue(execute(s.second, c)))
		if r == None:
			return False
		return not r
	elif s.id == 'instanceof':
		l = getValue(execute(s.first, c))
		r = getValue(execute(s.second, c))
		if not isinstance(r, BaseObject):
			raise JavaScriptTypeError()
		if not hasattr(r, 'has_instance'):
			raise JavaScriptTypeError()
		return r.has_instance(l)
	elif s.id == 'in':
		l = getValue(execute(s.first, c))
		r = getValue(execute(s.second, c))
		if not isinstance(r, BaseObject):
			raise JavaScriptTypeError()
		return toString(l) in r

	## Equality Operators
	elif s.id == '==':
		pass
	elif s.id == '!=':
		pass
	elif s.id == '===':
		pass
	elif s.id == '!==':
		pass

	## Statements
	elif s.id == '(statement)':
		v = execute(s.first, c)
		if isinstance(v, tuple):
			return v
		else:
			return ('normal', v, None)
	elif s.id == 'var':
		for var in s.first:
			if var.id == '(identifier)': continue
			execute(var, c) # assignment
		return ('normal', None, None)

	elif s.id == 'if':
		if toBoolean(getValue(execute(s.first, c))):
			return execute(s.block, c)
		elif hasattr(s, 'elseblock'):
			return execute(s.elseblock, c)
		else:
			return ('normal', None, None)

	elif s.id == 'do':
		t = True
		while t:
			v = execute(s.block, c)
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
			v = execute(s.block, c)
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
		if not s.is_decl and s.name:
			scope = Scope(c.scope)
			f = JavaScriptFunction(s, scope)
			scope.object.put(s.name.value, f, dont_delete=True, read_only=True)
		else:
			f = JavaScriptFunction(s, c.scope)
		return f

	raise RuntimeError, "unknown operation %s" % s.id


def run(symbol, global_object=None):
	if isinstance(symbol, basestring):
		symbol = parse_str(symbol)
	global_object = global_object or GlobalObject()
	c = ExecutionContext(Scope(object=global_object),
		global_object, global_object)
	c.instantiate_variables(symbol, global_object)
	return getValue(execute(symbol.first, c)[1])



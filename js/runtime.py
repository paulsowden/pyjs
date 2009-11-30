import math, sys, random
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
		try:
			return float(value) # TODO
		except ValueError, e:
			return nan
	return toNumber(toPrimitive(value, 'number'))

def toInteger(value):
	value = toNumber(value)
	if isnan(value) or value == 0:
		return 0
	if isinf(value):
		return value
	return int(copysign(1, value) * (abs(value) // 1))

def toInt32(value):
	value = toNumber(value)
	if isnan(value) or isinf(value) or value == 0:
		return 0
	value = copysign(1, value) * math.floor(abs(value))
	value = value % 4294967296 # 2^32
	return value if value < 2147483648 else value - 4294967296

def toUint32(value):
	value = toNumber(value)
	if isnan(value) or isinf(value) or value == 0:
		return 0
	value = copysign(1, value) * math.floor(abs(value))
	return value % 4294967296 # 2^32

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

def toObject(value, c):
	prototype = lambda o: getattr(c.global_object, o)['prototype']
	if value is None or value is null:
		raise JavaScriptException(c.global_object.type_error.construct([], c))
	if isinstance(value, bool):
		return JavaScriptBoolean(prototype('boolean'), value)
	if isinstance(value, float):
		return JavaScriptNumber(prototype('number'), value)
	if isinstance(value, str):
		return JavaScriptString(prototype('string'), value)
	return value

## Operator Comparisons

def lessThan(x, y):
	x, y = toPrimitive(x, 'number'), toPrimitive(y, 'number')
	if typeof(x) != 'string' or typeof(y) != 'string':
		x, y = toNumber(x), toNumber(y)
		if isnan(x) or isnan(y):
			return None
		if x == y:
			return False
		if x == inf:
			return False
		if y == inf:
			return True
		if x == neginf:
			return False
		if y == neginf:
			return True
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

def strictlyEqual(x, y):
	typeof_x = typeof(x)
	if typeof_x != typeof(y):
		return False
	if x == None or x == null:
		return True
	if typeof_x == 'number':
		return not isnan(x) and not isnan(y) or x == y
	return x == y

def equal(x, y):
	typeof_x, typeof_y = typeof(x), typeof(y)
	if typeof_x == typeof_y:
		return strictlyEqual(x, y)
	if x == null and y == None or x == None and y == null:
		return True
	if typeof_x == 'number' and typeof_y == 'string':
		return equal(x, toNumber(y))
	if typeof_x == 'string' and typeof_y == 'number':
		return equal(toNumber(x), y)
	if typeof_x == 'boolean':
		return equal(toNumber(x), y)
	if typeof_y == 'boolean':
		return equal(x, toNumber(y))
	if typeof_x in ('string', 'number') and typeof_y == 'object':
		return equal(x, toPrimitive(y))
	if typeof_y in ('string', 'number') and typeof_x == 'object':
		return equal(toPrimitive(x), y)
	return False


class Reference(object):
	__slots__ = ['base', 'property_name']
	def __init__(self, base, property_name):
		self.base = base
		self.property_name = property_name
	def __repr__(self):
		return '<Reference %s %s>' % (self.base, self.property_name)

def getValue(v, c):
	if isinstance(v, Reference):
		if not v.base:
			raise JavaScriptException(
				c.global_object.reference_error.construct([], c))
		return v.base[v.property_name]
	return v

def putValue(v, w, c):
	if not isinstance(v, Reference):
		raise JavaScriptException(
			c.global_object.reference_error.construct([], c))
	if not v.base:
		c.global_object[v.property_name] = w
	else:
		v.base[v.property_name] = w

class JavaScriptException(Exception):
	def __init__(self, value):
		self.value = value

## Native Objects

class Property(object):
	__slots__ = ['value', 'read_only', 'dont_enum', 'dont_delete']
	def __init__(self,
			value, read_only=False, dont_enum=False, dont_delete=False):
		self.value = value
		self.read_only = read_only
		self.dont_enum = dont_enum
		self.dont_delete = dont_delete

class JavaScriptObject(object):
	name = 'Object' # [[Class]]

	def __init__(self, prototype=None):
		self.prototype = prototype # [[Prototype]]
		self.properties = {}
		self.ordered_keys = []

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
		else:
			self.properties[key] = Property(value)
			self.ordered_keys.append(key)
		return value

	def put(self, key, value,
			read_only=False, dont_enum=False, dont_delete=False):
		if key in self.properties:
			prop = self.properties[key]
			prop.value = value
			prop.read_only = read_only
			prop.dont_enum = dont_enum
			prop.dont_delete = dont_delete
		else:
			self.properties[key] = Property(value,
				read_only, dont_enum, dont_delete)
			self.ordered_keys.append(key)
		return value

	def __delitem__(self, key): # [[Delete]]
		if key not in self.properties:
			return True
		if self.properties[key].dont_delete:
			return False
		del self.properties[key]
		if key in self.ordered_keys:
			# arrays don't store their indexes in the ordered_keys list
			self.ordered_keys.remove(key)
		return True

	def __contains__(self, key): # [[HasProperty]]
		return (key in self.properties) \
			or self.prototype and (key in self.prototype)

	def __iter__(self):
		keys = []
		object = self
		while object:
			for key in object.ordered_keys:
				if not key in keys:
					keys.append(key)
			object = object.prototype
		for key in keys:
			property = self.get(key)
			if property and not property.dont_enum:
				yield key

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

class Scope(object):
	__slots__ = ['parent', 'object']
	def __init__(self, parent=None, object=None):
		self.parent = parent
		self.object = object or JavaScriptObject()

class ExecutionContext(object):
	__slots__ = ['scope', 'this', 'global_object']
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

class Activation(JavaScriptObject):
	pass

class ArgumentsObject(JavaScriptObject):
	def __init__(self, prototype, args, callee):
		super(ArgumentsObject, self).__init__(prototype)
		self.put('length', len(args), dont_enum=True)
		self.put('callee', callee, dont_enum=True)
		for i, arg in enumerate(args):
			self.put(str(i), arg, dont_enum=True)

class JavaScriptFunction(JavaScriptObject):
	name = 'Function'
	def __init__(self, prototype, s, scope):
		super(JavaScriptFunction, self).__init__(prototype)

		self.symbol = s
		self.scope = scope # [[Scope]]

		self.put('length', float(len(s.params)), True, True, True)
		self.put('prototype', JavaScriptObject(prototype), dont_delete=True)
		self['prototype'].put('constructor', self, dont_enum=True)

	def call(self, this, args, context):
		global_object = context.global_object
		activation = Activation()
		activation.put('arguments',
			ArgumentsObject(global_object.object['prototype'], args, self),
			dont_delete=True)
		c = ExecutionContext(Scope(self.scope, activation), this, global_object)
		c.instantiate_variables(self.symbol, activation)
		v = execute(self.symbol.block, c)
		if v[0] == 'throw':
			raise JavaScriptException(v[1])
		if v[0] == 'return':
			return v[1]
		else: # normal
			return None

	def construct(self, args, context):
		if isinstance(self['prototype'], JavaScriptObject):
			prototype = self['prototype']
		else:
			prototype = context.global_object.object['prototype']
		o = JavaScriptObject(prototype)
		v = self.call(o, args, context)
		if typeof(v) == 'object':
			return v
		return o

	def has_instance(self, v, c):
		if not isinstance(v, JavaScriptObject):
			return False
		o = self['prototype']
		if not isinstance(o, JavaScriptObject):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		while hasattr(v, 'prototype'):
			v = v.prototype
			if o == v:
				return True
		return False

class JavaScriptArray(JavaScriptObject):
	name = 'Array'
	def __init__(self, prototype):
		super(JavaScriptArray, self).__init__(prototype)
		self.put('length', 0.0, dont_enum=True, dont_delete=True)
	def __setitem__(self, key, value):
		if not self.can_put(key):
			return False
		if key != 'length':
			if key in self.properties:
				self.properties[key].value = value
			else:
				self.properties[key] = Property(value)
			i = toUint32(key)
			if toString(i) == key and self.properties['length'].value <= i:
				self.properties['length'].value = i + 1.0
			else:
				self.ordered_keys.append(key)
		else:
			i = toUint32(value)
			if i != toNumber(value):
				raise JavaScriptError() # TODO range error
			for a in range(int(i), int(self.properties['length'].value)):
				del self[str(a)]
			self.properties['length'].value = i
	# TODO implement iter over the numerical indices

class JavaScriptString(JavaScriptObject):
	name = 'String'
	def __init__(self, prototype, value=''):
		super(JavaScriptString, self).__init__(prototype)
		self.value = value
		self.put('length', float(len(value)), True, True, True)

class JavaScriptBoolean(JavaScriptObject):
	name = 'Boolean'
	def __init__(self, prototype, value=False):
		super(JavaScriptBoolean, self).__init__(prototype)
		self.value = value

class JavaScriptNumber(JavaScriptObject):
	name = 'Number'
	def __init__(self, prototype, value=0.0):
		super(JavaScriptNumber, self).__init__(prototype)
		self.value = value

class JavaScriptDate(JavaScriptObject):
	name = 'Date'

class JavaScriptRegExp(JavaScriptObject):
	name = 'RegExp'
	def __init__(self, prototype):
		super(JavaScriptRegExp, self).__init__(prototype)
		self.put('source', None, True, True, True) # TODO
		self.put('global', False, True, True, True) # TODO
		self.put('ignoreCase', False, True, True, True) # TODO
		self.put('multiline', False, True, True, True) # TODO
		self.put('lastIndex', 0, dont_delete=True, dont_enum=True) # TODO

class JavaScriptError(JavaScriptObject):
	name = 'Error'
	def __str__(self):
		return '%s: %s' % (self.name, toString(self['message']))

class JavaScriptNativeError(JavaScriptError):
	def __init__(self, name, prototype):
		super(JavaScriptNativeError, self).__init__(prototype)
		self.name = name


## Native Prototypes

class JavaScriptNativeFunctionWrapper(object):
	def __init__(self, funtion, length, name):
		self.function = funtion
		self.length = length
		self.name = name

class JavaScriptNativeFunction(JavaScriptFunction):
	def __init__(self, prototype, wrapper):
		JavaScriptObject.__init__(self, prototype)
		self.fn = wrapper.function
		self.put('length', wrapper.length, True, True, True)
	def call(self, this, args, c):
		return self.fn(this, args, c)
	def construct(self, this, args, c):
		raise JavaScriptException(c.global_object.type_error.construct([], c))

class NativeFunctions(type):
	def __new__(mcs, name, bases, dict):

		functions = {}
		for key, function in dict.items():
			if isinstance(function, JavaScriptNativeFunctionWrapper):
				del dict[key]
				functions[function.name] = function
		dict['functions'] = functions

		def bind(self, object, prototype):
			for name, function in self.functions.items():
				object.put(name, JavaScriptNativeFunction(prototype, function),
					dont_enum=True)
			return self
		dict['bind'] = bind

		return type.__new__(mcs, name, bases, dict)

def native(fn=None, length=0, name=None):
	def bind(fn):
		return JavaScriptNativeFunctionWrapper(fn, length, name or fn.__name__)
	return bind(fn) if fn else bind

class JavaScriptNativePrototype(JavaScriptObject):
	def __init__(self, prototype=None, function_prototype=None):
		super(JavaScriptNativePrototype, self).__init__(prototype)
		if function_prototype:
			self.bind(self, function_prototype)

class JavaScriptObjectPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		return '[object %s]' % this.name

	@native
	def toLocaleString(this, args, c):
		pass # TODO

	@native
	def valueOf(this, args, c):
		return this

	@native(length=1)
	def hasOwnProperty(this, args, c):
		return toString(args[0] if len(args) else None) in this.properties

	@native(length=1)
	def isPrototypeOf(this, args, c):
		if not len(args) or typeof(args[0]) != 'object':
			return False
		prototype = args[0].prototype
		while prototype and prototype != null:
			if prototype == this:
				return True
			prototype = prototype.prototype
		return False

	@native(length=1)
	def propertyIsEnumerable(this, args, c):
		property = toString(args[0] if len(args) else None)
		return not property in this.properties \
			or not this.get(property).dont_enum

class JavaScriptFunctionPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		if not hasattr(this, 'symbol'):
			return 'function () { [native code] }'
		pass # TODO

	@native(length=2)
	def apply(this, args, c):
		if not hasattr(this, 'call'):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		thisArg = args[0] if len(args) else None
		thisArg = c.global_object \
			if thisArg is None or thisArg is null else toObject(thisArg, c)
		argArray = args[1] if len(args) > 1 else None
		if argArray is None or argArray is null:
			argArray = []
		elif isinstance(argArray, ArgumentsObject):
			argArray = [] # TODO
		elif isinstance(argArray, JavaScriptArray):
			argArray = [] # TODO
		else:
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return this.call(thisArg, argArray, c)

	@native(length=1)
	def call(this, args, c):
		if not hasattr(this, 'call'):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		thisArg = args[0] if len(args) else None
		thisArg = c.global_object \
			if thisArg is None or thisArg is null else toObject(thisArg, c)
		return this.call(thisArg, args[1:], c)

class JavaScriptArrayPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		if not isintance(this, JavaScriptArray):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		# TODO return join()

	@native
	def toLocaleString(this, args, c):
		pass # TODO

	@native(length=1)
	def concat(this, args, c):
		pass # TODO

	@native(length=1)
	def join(this, args, c):
		pass # TODO

	@native
	def pop(this, args, c):
		pass # TODO

	@native(length=1)
	def push(this, args, c):
		pass # TODO

	@native
	def reverse(this, args, c):
		pass # TODO

	@native
	def shift(this, args, c):
		pass # TODO

	@native(length=2)
	def slice(this, args, c):
		pass # TODO

	@native(length=1)
	def sort(this, args, c):
		pass # TODO

	@native(length=2)
	def splice(this, args, c):
		pass # TODO

	@native(length=1)
	def unshift(this, args, c):
		pass # TODO

class JavaScriptStringPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		if not isinstance(this, JavaScriptString):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return this.value

	@native
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptString):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return this.value

	@native(length=1)
	def charAt(this, args, c):
		s = toString(this)
		n = len(args) and toInteger(args[0]) or 0
		return '' if n < 0 or n > len(s) else s[n]

	@native(length=1)
	def charCodeAt(this, args, c):
		s = toString(this)
		n = len(args) and toInteger(args[0]) or 0
		return nan if n < 0 or n > len(s) else float(ord(s[n]))

	@native(length=1)
	def concat(this, args, c):
		return toString(this) + ''.join(toString(arg) for arg in args)

	@native(length=1)
	def indexOf(this, args, c):
		pass # TODO

	@native(length=1)
	def lastIndexOf(this, args, c):
		pass # TODO

	@native(length=1)
	def localeCompare(this, args, c):
		pass # TODO

	@native(length=1)
	def match(this, args, c):
		pass # TODO

	@native(length=2)
	def replace(this, args, c):
		pass # TODO

	@native(length=1)
	def search(this, args, c):
		pass # TODO

	@native(length=2)
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

	@native(length=2)
	def split(this, args, c):
		pass # TODO

	@native(length=2)
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

	@native(length=2)
	def substring(this, args, c):
		pass # TODO

	@native
	def toLowerCase(this, args, c):
		return toString(this).lower()

	@native
	def toLocaleLowerCase(this, args, c):
		pass # TODO

	@native
	def toUpperCase(this, args, c):
		return toString(this).upper()

	@native
	def toLocaleUpperCase(this, args, c):
		pass # TODO

class JavaScriptBooleanPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		if not isinstance(this, JavaScriptBoolean):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return toString(this.value)

	@native
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptBoolean):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return this.value

class JavaScriptNumberPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native(length=1)
	def toString(this, args, c):
		pass # TODO

	@native
	def toLocaleString(this, args, c):
		pass # TODO

	@native
	def valueOf(this, args, c):
		pass # TODO

	@native(length=1)
	def toFixed(this, args, c):
		pass # TODO

	@native(length=1)
	def toExponential(this, args, c):
		pass # TODO

	@native(length=1)
	def toPrecision(this, args, c):
		pass # TODO

class JavaScriptDatePrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		pass # TODO

	@native
	def toDateString(this, args, c):
		pass # TODO

	@native
	def toTimeString(this, args, c):
		pass # TODO

	@native
	def toLocaleString(this, args, c):
		pass # TODO

	@native
	def toLocaleDateString(this, args, c):
		pass # TODO

	@native
	def toLocaleTimeString(this, args, c):
		pass # TODO

	@native
	def valueOf(this, args, c):
		pass # TODO

	@native
	def getTime(this, args, c):
		pass # TODO

	@native
	def getFullYear(this, args, c):
		pass # TODO

	@native
	def getUTCFullYear(this, args, c):
		pass # TODO

	@native
	def getMonth(this, args, c):
		pass # TODO

	@native
	def getUTCMonth(this, args, c):
		pass # TODO

	@native
	def	getDate(this, args, c):
		pass # TODO

	@native
	def getUTCDate(this, args, c):
		pass # TODO

	@native
	def getDay(this, args, c):
		pass # TODO

	@native
	def getUTCDay(this, args, c):
		pass # TODO

	@native
	def getHours(this, args, c):
		pass # TODO

	@native
	def getUTCHours(this, args, c):
		pass # TODO

	@native
	def getMinutes(this, args, c):
		pass # TODO

	@native
	def getUTCMinutes(this, args, c):
		pass # TODO

	@native
	def getSeconds(this, args, c):
		pass # TODO

	@native
	def getUTCSeconds(this, args, c):
		pass # TODO

	@native
	def getMilliseconds(this, args, c):
		pass # TODO

	@native
	def getUTCMilliseconds(this, args, c):
		pass # TODO

	@native
	def getTimezoneOffset(this, args, c):
		pass # TODO

	@native(length=1)
	def	setTime(this, args, c):
		pass # TODO

	@native(length=1)
	def setMilliseconds(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCMilliseconds(this, args, c):
		pass # TODO

	@native(length=1)
	def setSeconds(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCSeconds(this, args, c):
		pass # TODO

	@native(length=1)
	def setMinutes(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCMinutes(this, args, c):
		pass # TODO

	@native(length=1)
	def setMonth(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCMonth(this, args, c):
		pass # TODO

	@native(length=1)
	def setHours(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCHours(this, args, c):
		pass # TODO

	@native(length=1)
	def setDay(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCDay(this, args, c):
		pass # TODO

	@native(length=1)
	def	setDate(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCDate(this, args, c):
		pass # TODO

	@native(length=1)
	def setFullYear(this, args, c):
		pass # TODO

	@native(length=1)
	def setUTCFullYear(this, args, c):
		pass # TODO

	@native
	def toUTCString(this, args, c):
		pass # TODO

class JavaScriptRegExpPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native(length=1, name='exec')
	def exec_(this, args, c):
		pass # TODO

	@native(length=1)
	def test(this, args, c):
		pass # TODO

	@native
	def toString(this, args, c):
		pass # TODO

class JavaScriptErrorPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	def __init__(self, *args, **kwargs):
		super(JavaScriptErrorPrototype, self).__init__(*args, **kwargs)
		self['name'] = 'Error'
		self['message'] = 'Unknown Error'

	@native
	def toString(this, args, c):
		#message = isinstance(this, JavaScriptObject) and this['message']
		return this.name if isinstance(this, JavaScriptError) else 'Error'

class JavaScriptNativeErrorPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	def __init__(self, name, *args, **kwargs):
		super(JavaScriptNativeErrorPrototype, self).__init__(*args, **kwargs)
		self['name'] = name
		self['message'] = 'Unknown Error'


## Object Constructors

class JavaScriptObjectConstructor(JavaScriptFunction):
	def __init__(self, prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype', prototype, True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
		prototype.bind(prototype, function_prototype)
	def call(self, this, args, c):
		o = args[0] if len(args) else JavaScriptObject(self['prototype'])
		return toObject(o, c)

class JavaScriptFunctionConstructor(JavaScriptFunction):
	def __init__(self, object_prototype):
		function_prototype = JavaScriptFunctionPrototype(object_prototype)
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype', function_prototype, True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
		function_prototype.bind(function_prototype, function_prototype)
	def call(self, this, args, c):
		pass # TODO
	def construct(self, args, c):
		pass # TODO

class JavaScriptArrayConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptArrayPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
	def call(self, this, args, c):
		return self.construct(args, c)
	def construct(self, args, c):
		if len(args) == 1 and isinstance(args[0], float):
			if args[0] != toUint32(args[0]):
				raise JavaScriptException(
					c.global_object.range_error.construct([], c))
			array = JavaScriptArray(self['prototype'])
			array['length'] = args[0]
		else:
			array = JavaScriptArray(self['prototype'])
			for i, arg in enumerate(args):
				array[str(i)] = arg
		return array

class JavaScriptStringConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptStringPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
		self.JavaScriptStringFunctions().bind(self, function_prototype)
	def call(self, this, args, c):
		return toString(args[0]) if len(args) else ''
	def construct(self, args, c):
		s = toString(args[0]) if len(args) else ''
		return JavaScriptString(self['prototype'], s)

	class JavaScriptStringFunctions(object):
		__metaclass__ = NativeFunctions

		@native(length=1)
		def fromCharCode(this, args, c):
			return ''.join(chr(toInteger(arg)) for arg in args)

class JavaScriptBooleanConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptBooleanPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
	def call(self, this, args, c):
		return toBoolean(args[0]) if len(args) else False
	def construct(self, args, c):
		b = toBoolean(args[0]) if len(args) else False
		return JavaScriptBoolean(self['prototype'], b)

class JavaScriptNumberConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptNumberPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
		self.put('MAX_VALUE', sys.float_info.max, True, True, True)
		self.put('MIN_VALUE', sys.float_info.min, True, True, True)
		self.put('NaN', nan, True, True, True)
		self.put('NEGATIVE_INFINITY', neginf, True, True, True)
		self.put('POSITIVE_INFINITY', inf, True, True, True)
	def call(self, this, args, c):
		return toNumber(args[0]) if len(args) else 0
	def construct(self, args, c):
		return JavaScriptNumber(self['prototype'],
			toNumber(args[0]) if len(args) else 0)

class JavaScriptMath(JavaScriptObject):
	name = 'Math'
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)

		self.put('E', math.e, True, True, True)
		self.put('LN10', math.log(10), True, True, True)
		self.put('LN2', math.log(2), True, True, True)
		self.put('LOG2E', math.log(math.e, 2), True, True, True)
		self.put('LOG10E', math.log(math.e, 10), True, True, True)
		self.put('PI', math.pi, True, True, True)
		self.put('SQRT1_2', math.sqrt(0.5), True, True, True)
		self.put('SQRT2', math.sqrt(2), True, True, True)

		self.JavaScriptMathFunctions().bind(self, function_prototype)

	class JavaScriptMathFunctions(object):
		__metaclass__ = NativeFunctions

		@native(length=1)
		def abs(this, args, c):
			return math.fabs(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def acos(this, args, c):
			return math.acos(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def asin(this, args, c):
			return math.asin(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def atan(this, args, c):
			return math.atan(toNumber(args[0] if len(args) else None))

		@native(length=2)
		def atan2(this, args, c):
			return math.atan2(toNumber(args[0] if len(args) else None),
				toNumber(args[1] if len(args) > 1 else None))

		@native(length=1)
		def ceil(this, args, c):
			return math.ceil(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def cos(this, args, c):
			return math.cos(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def exp(this, args, c):
			return math.exp(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def floor(this, args, c):
			return math.floor(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def log(this, args, c):
			return math.log(toNumber(args[0] if len(args) else None))

		@native(length=2)
		def max(this, args, c):
			return max(toNumber(arg) for arg in args) if len(args) else nan

		@native(length=2)
		def min(this, args, c):
			return min(toNumber(arg) for arg in args) if len(args) else nan

		@native(length=2)
		def pow(this, args, c):
			return math.pow(toNumber(arg[0] if len(args) else None),
				toNumber(arg[1] if len(args) > 1 else None))

		@native
		def random(this, args, c):
			return random.random()

		@native(length=1)
		def round(this, args, c):
			return round(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def sin(this, args, c):
			return math.sin(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def sqrt(this, args, c):
			return math.sqrt(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def tan(this, args, c):
			return math.tan(toNumber(args[0] if len(args) else None))

class JavaScriptDateConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptDatePrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
		self.JavaScriptDateFunctions().bind(self, function_prototype)
	def call(self, this, args, c):
		pass # TODO
	def construct(self, args, c):
		pass # TODO

	class JavaScriptDateFunctions(object):
		__metaclass__ = NativeFunctions

		@native(length=1)
		def parse(this, args, c):
			pass # TODO

		@native(length=7)
		def UTC(this, args, c):
			pass # TODO

class JavaScriptRegExpConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptRegExpPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
	def call(self, this, args, c):
		pass # TODO
	def construct(self, args, c):
		pass # TODO

class JavaScriptErrorConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptErrorPrototype(self, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
	def call(self, this, args, c):
		return self.construct(args, c)
	def construct(self, args, c):
		error = JavaScriptError(self['prototype'])
		if len(args) and args[0] != None:
			error['message'] = toString(args[0])
		return error

class JavaScriptNativeErrorConstructor(JavaScriptErrorConstructor):
	def __init__(self, name, error_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.name = name
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptNativeErrorPrototype(
				name, error_prototype, function_prototype),
			True, True, True)
		self['prototype'].put('constructor', self, dont_enum=True)
	def construct(self, args, c):
		error = JavaScriptNativeError(self.name, self['prototype'])
		if len(args) and args[0] != None:
			error['message'] = toString(args[0])
		return error


## Global Object

class GlobalObject(JavaScriptObject):
	def __init__(self):
		super(GlobalObject, self).__init__()

		object_prototype = JavaScriptObjectPrototype()
		self.function = JavaScriptFunctionConstructor(object_prototype)
		function_prototype = self.function['prototype']

		def put(attr, name, constructor):
			o = constructor(object_prototype, function_prototype)
			setattr(self, attr, o)
			self.put(name, o, dont_enum=True)

		put('object', 'Object', JavaScriptObjectConstructor)
		put('array', 'Array', JavaScriptArrayConstructor)
		put('string', 'String', JavaScriptStringConstructor)
		put('boolean', 'Boolean', JavaScriptBooleanConstructor)
		put('number', 'Number', JavaScriptNumberConstructor)
		put('math', 'Math', JavaScriptMath)
		put('date', 'Date', JavaScriptDateConstructor)
		put('regexp', 'RegExp', JavaScriptRegExpConstructor)
		put('error', 'Error', JavaScriptErrorConstructor)

		error_prototype = self.error['prototype']
		def put_error(attr, name):
			o = JavaScriptNativeErrorConstructor(
				name, error_prototype, function_prototype)
			setattr(self, attr, o)
			self.put(name, o, dont_enum=True)
		put_error('eval_error', 'EvalError')
		put_error('range_error', 'RangeError')
		put_error('reference_error', 'ReferenceError')
		put_error('syntax_error', 'SyntaxError')
		put_error('type_error', 'TypeError')
		put_error('uri_error', 'URIError')

		self.put('Function', self.function, dont_enum=True)

		self.put('NaN', nan, dont_delete=True, dont_enum=True)
		self.put('Infinity', inf, dont_delete=True, dont_enum=True)
		self.put('undefined', None, dont_delete=True, dont_enum=True)

		self.GlobalFunctions().bind(self, function_prototype)

	class GlobalFunctions(object):
		__metaclass__ = NativeFunctions

		@native(length=1)
		def eval(this, args, c):
			if not len(args) or not isinstance(args[0], basestring):
				return args[0] if len(args) else None
			pass # TODO

		@native(length=2)
		def parseInt(this, args, c):
			pass # TODO

		@native(length=1)
		def parseFloat(this, args, c):
			pass # TODO

		@native(length=1)
		def isNaN(this, args, c):
			return isnan(toNumber(args[0] if len(args) else None))

		@native(length=1)
		def isFinite(this, args, c):
			n = toNumber(args[0] if len(args) else None)
			return not isinf(n) and not isnan(n)

		@native(length=1)
		def decodeURI(this, args, c):
			pass # TODO

		@native(length=1)
		def decodeURIComponent(this, args, c):
			pass # TODO

		@native(length=1)
		def encodeURI(this, args, c):
			pass # TODO

		@native(length=1)
		def encodeURIComponent(this, args, c):
			pass # TODO


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
			except JavaScriptException, e:
				return ('throw', e.value, None)
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
		array = c.global_object.array.construct([], c)
		for i, arg in enumerate(s.first):
			array[str(i)] = getValue(execute(arg, c), c)
		return array

	elif s.id == '(object)':
		o = c.global_object.object.construct([], c)
		for k, v in s.first:
			if k.id == '(identifier)':
				key = k.value
			elif k.id == '(number)':
				key = toString(execute(k, c))
			else: # (string)
				key = execute(k, c)
			o[key] = getValue(execute(v, c), c)
		return o


	## Left-Hand Expressions

	elif s.id == '.':
		return Reference(
			toObject(getValue(execute(s.first, c), c), c),
			s.second.value)
	elif s.id == '[': # property
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return Reference(toObject(l, c), toString(r))

	elif s.id == 'new':
		l = getValue(execute(s.first, c), c)
		args = [getValue(execute(arg, c), c)
			for arg in getattr(s, 'params', [])]
		if typeof(l) != 'object' or not hasattr(l, 'construct'):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return l.construct(args, c)

	elif s.id == '(':
		o = execute(s.first, c)
		args = [getValue(execute(arg, c), c) for arg in s.params]
		f = getValue(o, c)
		if typeof(f) != 'object' or not hasattr(f, 'call'):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		this = o.base if isinstance(o, Reference) else None
		if this and isinstance(this, Activation):
			this = None
		return f.call(this, args, c)

	## Postfix Expressions
	elif s.id == '++':
		l = execute(s.first, c)
		v = toNumber(getValue(l, c))
		if hasattr(s, 'arity'):
			v += 1.0
			putValue(l, v, c)
		else:
			putValue(l, v + 1.0, c)
		return v
	elif s.id == '--':
		l = execute(s.first, c)
		v = toNumber(getValue(l, c))
		if hasattr(s, 'arity'):
			v -= 1.0
			putValue(l, v, c)
		else:
			putValue(l, v - 1.0, c)
		return v

	## Unary Operators
	elif s.id == 'typeof':
		l = execute(s.first, c)
		if isinstance(l, Reference) and l.base == None:
			return 'undefined'
		o = getValue(l, c)
		type = typeof(o)
		if type == 'object' and hasattr(o, 'call'):
			return 'function'
		return type
	elif s.id == 'void':
		l = getValue(execute(s.first, c), c)
		return None
	elif s.id == 'delete':
		l = execute(s.first, c)
		if not isinstance(l, Reference):
			return True
		return l.base.__delitem__(l.property_name)
	elif s.id == '+' and hasattr(s, 'arity'): # unary
		return toNumber(getValue(execute(s.first, c), c))
	elif s.id == '-' and hasattr(s, 'arity'): # unary
		return -toNumber(getValue(execute(s.first, c), c))
	elif s.id == '~':
		return float(~int(toInt32(getValue(execute(s.first, c), c))))
	elif s.id == '!':
		return not toBoolean(getValue(execute(s.first, c), c))

	## Multiplicative Operators
	elif s.id == '/':
		return toNumber(getValue(execute(s.first, c), c)) / toNumber(getValue(execute(s.second, c), c))
	elif s.id == '*':
		return toNumber(getValue(execute(s.first, c), c)) * toNumber(getValue(execute(s.second, c), c))
	elif s.id == '%':
		l = toNumber(getValue(execute(s.first, c), c))
		r = toNumber(getValue(execute(s.second, c), c))
		return (l % r) - (0 if l >= 0 else r)

	## Additive Operators
	elif s.id == '+':
		return getValue(execute(s.first, c), c) + getValue(execute(s.second, c), c)
	elif s.id == '-':
		return getValue(execute(s.first, c), c) - getValue(execute(s.second, c), c)

	## Bitwise Shift Operators
	elif s.id == '<<':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return float(int(toInt32(l)) << int(toInt32(r) & 0x1f))
	elif s.id == '>>':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return float(int(toInt32(l)) >> int(toInt32(r) & 0x1f))
	elif s.id == '>>>':
		pass # TODO

	## Relational Operators
	elif s.id == '<':
		r = lessThan(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))
		return False if r == None else r
	elif s.id == '>':
		r = lessThan(getValue(execute(s.second, c), c),
			getValue(execute(s.first, c), c))
		return False if r == None else r
	elif s.id == '<=':
		r = lessThan(getValue(execute(s.second, c), c),
			getValue(execute(s.first, c), c))
		return False if r == None else not r
	elif s.id == '>=':
		r = lessThan(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))
		return False if r == None else not r
	elif s.id == 'instanceof':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		if not isinstance(r, JavaScriptObject):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		if not hasattr(r, 'has_instance'):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return r.has_instance(l, c)
	elif s.id == 'in':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		if not isinstance(r, JavaScriptObject):
			raise JavaScriptException(
				c.global_object.type_error.construct([], c))
		return toString(l) in r

	## Equality Operators
	elif s.id == '==':
		return equal(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))
	elif s.id == '!=':
		return not equal(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))
	elif s.id == '===':
		return strictlyEqual(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))
	elif s.id == '!==':
		return not strictlyEqual(getValue(execute(s.first, c), c),
			getValue(execute(s.second, c), c))

	## Binary Bitwise Operators
	elif s.id == '&':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return float(int(toInt32(l)) & int(toInt32(r)))
	elif s.id == '^':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return float(int(toInt32(l)) ^ int(toInt32(r)))
	elif s.id == '|':
		l = getValue(execute(s.first, c), c)
		r = getValue(execute(s.second, c), c)
		return float(int(toInt32(l)) | int(toInt32(r)))

	## Binary Logical Operators
	elif s.id == '&&':
		l = getValue(execute(s.first, c), c)
		if not toBoolean(l):
			return l
		return getValue(execute(s.second, c), c)
	elif s.id == '||':
		l = getValue(execute(s.first, c), c)
		if toBoolean(l):
			return l
		return getValue(execute(s.second, c), c)

	## Conditional Operator
	elif s.id == '?':
		if toBoolean(getValue(execute(s.first, c), c)):
			return getValue(execute(s.second, c), c)
		else:
			return getValue(execute(s.third, c), c)

	## Assignment Operators
	elif s.id == '=':
		l = execute(s.first, c)
		r = getValue(execute(s.second, c), c)
		putValue(l, r, c)
		return r
	elif s.id == '*=':
		pass # TODO
	elif s.id == '/=':
		pass # TODO
	elif s.id == '%=':
		pass # TODO
	elif s.id == '+=':
		pass # TODO
	elif s.id == '-=':
		pass # TODO
	elif s.id == '<<=':
		pass # TODO
	elif s.id == '>>=':
		pass # TODO
	elif s.id == '>>>=':
		pass # TODO
	elif s.id == '&=':
		pass # TODO
	elif s.id == '^=':
		pass # TODO
	elif s.id == '|=':
		pass # TODO

	## Comma Operator
	elif s.id == ',':
		pass # TODO

	## Statements
	elif s.id == '(statement)':
		v = execute(s.first, c)
		if isinstance(v, tuple):
			if v[0] == 'break' and v[2] in set(l.value for l in s.labels):
				return ('normal', v[1], None)
			return v
		else:
			return ('normal', getValue(v, c), None)
	elif s.id == 'var':
		for var in s.first:
			if var.id == '(identifier)': continue
			execute(var, c) # assignment
		return ('normal', None, None)

	elif s.id == 'if':
		if toBoolean(getValue(execute(s.first, c), c)):
			return execute(s.block, c)
		elif hasattr(s, 'elseblock'):
			return execute(s.elseblock, c)
		else:
			return ('normal', None, None)

	elif s.id == 'do':
		t = True
		while t:
			v = execute(s.block, c)
			if v[0] == 'continue' and \
					(not v[2] or v[2] in set(l.value for l in s.labels)):
				pass
			elif v[0] == 'break' and \
					(not v[2] or v[2] in set(l.value for l in s.labels)):
				return ('normal', v[1], None)
			elif v[0] != 'normal':
				return v
			t = toBoolean(getValue(execute(s.second, c), c))
		return ('normal', v[1], None)

	elif s.id == 'while':
		v = None
		while toBoolean(getValue(execute(s.second, c), c)):
			v = execute(s.block, c)
			if v[0] == 'continue' and \
					(not v[2] or v[2] in set(l.value for l in s.labels)):
				pass
			elif v[0] == 'break' and \
					(not v[2] or v[2] in set(l.value for l in s.labels)):
				return ('normal', v[1], None)
			elif v[0] != 'normal':
				return v
		return ('normal', v[1], None)
	elif s.id == 'for':
		v = None
		if hasattr(s, 'iterator'):
			o = toObject(getValue(execute(s.object, c), c), c)
			identifier = s.iterator
			if identifier.id == 'var':
				execute(identifier, c)
				identifier = identifier.first[0]
			for key in o:
				putValue(execute(identifier, c), key, c)
				result = execute(s.block, c)
				v = result[1]
				if result[0] == 'break' and (not result[2] or \
						result[2] in set(l.value for l in s.labels)):
					break
				if result[0] == 'continue' and (not result[2] or \
						result[2] in set(l.value for l in s.labels)):
					continue
				if result[0] != 'normal':
					return result
		else:
			if hasattr(s, 'initializer'):
				i = execute(s.initializer, c)
				if not s.initializer.id == 'var':
					getValue(i, c)
			while 1:
				if hasattr(s, 'condition') and \
						not toBoolean(getValue(execute(s.condition, c), c)):
					break
				result = execute(s.block, c)
				v = result[1]
				if result[0] == 'break' and (not result[2] or \
						result[2] in set(l.value for l in s.labels)):
					break
				if result[0] == 'continue' and (not result[2] or \
						result[2] in set(l.value for l in s.labels)):
					pass
				elif result[0] != 'normal':
					return result
				if hasattr(s, 'counter'):
					getValue(execute(s.counter, c), c)
		return ('normal', v, None)
	elif s.id == 'continue':
		return ('continue', None, s.first.value if s.first else None)
	elif s.id == 'break':
		return ('break', None, s.first.value if s.first else None)
	elif s.id == 'return':
		return ('return', execute(s.first, c) if s.first else None, None)
	elif s.id == 'with':
		c.scope = Scope(c.scope, toObject(getValue(execute(s.first, c), c), c))
		try:
			r = execute(s.block, c)
		except JavaScriptException, e:
			r = ('throw', e.value, None)
		c.scope = c.scope.parent
		return r
	elif s.id == 'switch':
		pass # TODO
	elif s.id == 'throw':
		return ('throw', getValue(execute(s.first, c)), None)
	elif s.id == 'try':
		result = execute(s.block, c)
		if result[0] == 'throw' and hasattr(s, 'catchblock'):
			c.scope = Scope(c.scope, c.global_object.object.construct([], c))
			c.scope.object.put(s.e.value, result[1], dont_delete=True)
			r = execute(s.catchblock, c)
			c.scope = c.scope.parent
			if not hasattr(s, 'finallyblock') or r[0] != 'normal':
				result = r
		if hasattr(s, 'finallyblock'):
			r = execute(s.finallyblock, c)
			if not hasattr(s, 'catchblock') or r[0] != 'normal':
				result = r
		return result
	elif s.id == 'function':
		prototype = c.global_object.function['prototype']
		if not s.is_decl and s.name:
			scope = Scope(c.scope, c.global_object.object.construct([], c))
			f = JavaScriptFunction(prototype, s, scope)
			scope.object.put(s.name.value, f, dont_delete=True, read_only=True)
		else:
			f = JavaScriptFunction(prototype, s, c.scope)
		return f

	raise JavaScriptException(c.global_object.error.construct(
		['unknown operation %s' % s.id], c))


def run(symbol, global_object=None):
	if isinstance(symbol, basestring):
		symbol = parse_str(symbol)
	global_object = global_object or GlobalObject()
	c = ExecutionContext(Scope(object=global_object),
		global_object, global_object)
	c.instantiate_variables(symbol, global_object)
	return execute(symbol.first, c)[1]



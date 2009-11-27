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

def toObject(value, c):
	prototype = lambda o: getattr(c.global_object, o)['prototype']
	if value is None or value is null:
		raise JavaScriptTypeError() # TODO prototype
	if isinstance(value, bool):
		return JavaScriptBoolean(prototype('boolean'), value)
	if isinstance(value, float):
		return JavaScriptNumber(prototype('number'), value)
	if isinstance(value, str):
		return JavaScriptString(prototype('string'), value)
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
		return value

	def __delitem__(self, key): # [[Delete]]
		if key not in self.properties:
			return True
		if self.properties[key].dont_delete:
			return False
		del self.properties[key]
		return True

	def __contains__(self, key): # [[HasProperty]]
		return (key in self.properties) \
			or self.prototype and (key in self.prototype)

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
		self.scope = scope

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
			raise v[1]
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

class JavaScriptMath(JavaScriptObject):
	name = 'Math'

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


## Builtin Prototypes

class JavaScriptNativeFunctionWrapper(object):
	def __init__(self, fn, length, name):
		self.fn = fn
		self.length = length
		self.name = name

class JavaScriptNativeFunction(JavaScriptFunction):
	def __init__(self, prototype, native_function):
		JavaScriptObject.__init__(self, prototype)
		self.fn = native_function.fn
		self.put('length', native_function.length, True, True, True)
	def call(self, this, args, c):
		return self.fn(this, args, c)
	def construct(self, this, args, c):
		raise JavaScriptTypeError()

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
			raise JavaScriptTypeError()
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
			raise JavaScriptTypeError()
		return this.call(thisArg, argArray, c)

	@native(length=1)
	def call(this, args, c):
		if not hasattr(this, 'call'):
			raise JavaScriptTypeError()
		thisArg = args[0] if len(args) else None
		thisArg = c.global_object \
			if thisArg is None or thisArg is null else toObject(thisArg, c)
		return this.call(thisArg, args[1:], c)

class JavaScriptArrayPrototype(JavaScriptNativePrototype):
	__metaclass__ = NativeFunctions

	@native
	def toString(this, args, c):
		if not isintance(this, JavaScriptArray):
			raise JavaScriptTypeError()
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
			raise JavaScriptTypeError()
		return this.value

	@native
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptString):
			raise JavaScriptTypeError()
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
			raise JavaScriptTypeError()
		return toString(this.value)

	@native
	def valueOf(this, args, c):
		if not isinstance(this, JavaScriptBoolean):
			raise JavaScriptTypeError()
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

## Errors

class JavaScriptError(JavaScriptObject):
	name = 'Error'
	def __str__(self):
		return '%s: %s' % (self.name, toString(self['message']))

class JavaScriptEvalError(JavaScriptError):
	name = 'EvalError'

class JavaScriptRangeError(JavaScriptError):
	name = 'RangeError'

class JavaScriptReferenceError(JavaScriptError):
	name = 'ReferenceError'

class JavaScriptSyntaxError(JavaScriptError):
	name = 'SyntaxError'

class JavaScriptTypeError(JavaScriptError):
	name = 'TypeError'

class JavaScriptURIError(JavaScriptError):
	name = 'URIError'


## Global Scope

class JavaScriptObjectConstructor(JavaScriptFunction):
	def __init__(self, prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype', prototype, True, True, True)
		self['prototype']['constructor'] = self
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
		self['prototype']['constructor'] = self
		function_prototype.bind(function_prototype, function_prototype)

class JavaScriptArrayConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptArrayPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype']['constructor'] = self
	def call(self, this, args, s):
		return self.construct(args, s)
	def construct(self, args, s):
		if len(args) == 1:
			# TODO create an array with length args[0]
			return JavaScriptArray(self['prototype'])
		else:
			# TODO create an array with elements args
			return JavaScriptArray(self['prototype'])

class JavaScriptStringConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptStringPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype']['constructor'] = self
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
		self['prototype']['constructor'] = self
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
		self['prototype']['constructor'] = self

class JavaScriptDateConstructor(JavaScriptFunction):
	def __init__(self, object_prototype, function_prototype):
		JavaScriptObject.__init__(self, function_prototype)
		self.put('length', 1, True, True, True)
		self.put('prototype',
			JavaScriptDatePrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype']['constructor'] = self

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
		self.put('prototype',
			JavaScriptRegExpPrototype(object_prototype, function_prototype),
			True, True, True)
		self['prototype']['constructor'] = self

class GlobalObject(JavaScriptObject):
	def __init__(self):
		super(GlobalObject, self).__init__()

		object_prototype = JavaScriptObjectPrototype()
		self.function = JavaScriptFunctionConstructor(object_prototype)
		function_prototype = self.function['prototype']

		op, fp = object_prototype, function_prototype
		self.object = JavaScriptObjectConstructor(op, fp)
		self.array = JavaScriptArrayConstructor(op, fp)
		self.string = JavaScriptStringConstructor(op, fp)
		self.boolean = JavaScriptBooleanConstructor(op, fp)
		self.number = JavaScriptNumberConstructor(op, fp)
		self.math = JavaScriptMath(op)
		self.date = JavaScriptDateConstructor(op, fp)
		self.regexp = JavaScriptRegExpConstructor(op, fp)

		self.put('NaN', nan, dont_delete=True, dont_enum=True)
		self.put('Infinity', inf, dont_delete=True, dont_enum=True)
		self.put('undefined', None, dont_delete=True, dont_enum=True)

		self.put('Object', self.object, dont_enum=True)
		self.put('Function', self.function, dont_enum=True)
		self.put('Array', self.array, dont_enum=True)
		self.put('String', self.string, dont_enum=True)
		self.put('Boolean', self.boolean, dont_enum=True)
		self.put('Number', self.number, dont_enum=True)
		self.put('Math', self.math, dont_enum=True)
		self.put('Date', self.date, dont_enum=True)
		self.put('RegExp', self.regexp, dont_enum=True)

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
			except JavaScriptObject, e:
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
		array = c.global_object.array.construct([], c)
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
			o[key] = getValue(execute(v, c))
		return o


	## Left-Hand Expressions

	elif s.id == '.':
		return Reference(
			toObject(getValue(execute(s.first, c)), c),
			s.second.value)
	elif s.id == '[': # property
		l = getValue(execute(s.first, c))
		r = getValue(execute(s.second, c))
		return Reference(toObject(l, c), toString(r))

	elif s.id == 'new':
		l = getValue(execute(s.first, c))
		args = [getValue(execute(arg, c)) for arg in getattr(s, 'params', [])]
		if typeof(l) != 'object' or not hasattr(l, 'construct'):
			raise JavaScriptTypeError()
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
		if not isinstance(r, JavaScriptObject):
			raise JavaScriptTypeError()
		if not hasattr(r, 'has_instance'):
			raise JavaScriptTypeError()
		return r.has_instance(l)
	elif s.id == 'in':
		l = getValue(execute(s.first, c))
		r = getValue(execute(s.second, c))
		if not isinstance(r, JavaScriptObject):
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
		prototype = c.global_object.function['prototype']
		if not s.is_decl and s.name:
			scope = Scope(c.scope)
			f = JavaScriptFunction(prototype, s, scope)
			scope.object.put(s.name.value, f, dont_delete=True, read_only=True)
		else:
			f = JavaScriptFunction(prototype, s, c.scope)
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



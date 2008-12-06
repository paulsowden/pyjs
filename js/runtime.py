
null = object()

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
		c.top.scope.object[v.property_name] = w
	else:
		v.base[v.property_name] = w


class Scope(object):
	def __init__(self, parent=None):
		self.object = BaseObject()
		self.parent = parent


class ExecutionContext(object):

	def __init__(self, context, this=None, scope=None, parent_context=None, args=None):
		self.scope = scope or Scope()
		self.top = parent_context and parent_context.top or self
		self.this = this or self.top.scope.object

		variables = self.scope.object
		if hasattr(context, 'params'):
			for i in range(len(context.params)):
				name = context.params[i]
				if len(args) > i:
					variables[name] = args[i]
				else:
					variables[name] = None
				variables.get(name).dont_delete = True
		for name, function in context.functions.items():
			variables.put(name, execute(function, self), dont_delete=True)
		for name in context.vars:
			if name not in variables:
				variables.put(name, None, dont_delete=True)


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
	name = None # [[Class]]
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
		if self.variables[key].dont_delete:
			return False
		del self.variables[key]
		return True

	def __contains__(self, key): # [[HasProperty]]
		return (key in self.properties) or self.prototype and (key in self.prototoype)

	def can_put(self, key): # [[CanPut]]
		if key in self.properties:
			return not self.properties[key].read_only
		if self.prototype:
			return self.prototype.can_put(key)
		return True

	def default_value(self, hint=None): # [[DefaultValue]]
		to_string = self['toString']
		value_of = self['valueOf']
		# TODO
		return None

	def __str__(self):
		return '[object %s]' % self.name


## Native Objects

class JavaScriptObject(BaseObject):
	name = 'Object'
	prototype = BaseObject()

class JavaScriptFunction(JavaScriptObject):
	name = 'Function'
	prototype = JavaScriptObject()
	def __init__(self, s, scope):
		JavaScriptObject.__init__(self)

		self.symbol = s
		self.scope = scope

		self.put('length', len(s.params), True, True, True)
		self.put('prototype', JavaScriptObject(), dont_delete=True)
		self['prototype'].put('constructor', self, dont_enum=True)

	def call(self, this, args, context):
		c = ExecutionContext(self.symbol, this, self.scope, context, args)
		v = execute(self.symbol.first, c)
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

class JavaScriptArray(JavaScriptObject):
	name = 'Array'
	prototype = JavaScriptObject()

class JavaScriptString(JavaScriptObject):
	name = 'String'
	prototype = JavaScriptObject()
	def __init__(self, value=''):
		self.value = value

	@classmethod
	def call(self, this, args, c):
		pass

class JavaScriptBoolean(JavaScriptObject):
	name = 'Boolean'
	prototype = JavaScriptObject()
	def __init__(self, value=False):
		self.value = value

class JavaScriptNumber(JavaScriptObject):
	name = 'Number'
	prototype = JavaScriptObject()
	def __init__(self, value=0.0):
		self.value = value

class JavaScriptMath(JavaScriptObject):
	name = 'Math'
	prototype = JavaScriptObject()

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



## Execute

def execute(s, c):
	"executes symbol `s` in context `c`"

	#print s
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
		if isinstance(o, Reference):
			this = o.base
			# TODO check for Activation object?
		else:
			this = null
		return f.call(this, args, c)

	elif s.id == 'typeof':
		l = execute(s.first, c)
		if isinstance(l, Reference) and l.base == None:
			return 'undefined'
		o = getValue(l)
		type = typeof(o)
		if type == 'object' and hasattr(o, 'call'):
			return 'function'
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
		if s.is_decl and s.name:
			scope = Scope(c.scope)
			f = JavaScriptFunction(s, scope)
			scope.object.put(s.name, f, dont_delete=True, read_only=True)
		else:
			f = JavaScriptFunction(s, c.scope)
		return f

	raise RuntimeError, "unknown operation %s" % s.id


def run(context):
	v = None
	c = ExecutionContext(context)

	for s in context.first:
		v = execute(s, c)
	return getValue(v[1])



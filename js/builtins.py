
null = object()


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


#####################################################################
# native objects
#####################################################################

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

class JavaScriptArray(JavaScriptObject):
	name = 'Array'
	prototype = JavaScriptObject()

class JavaScriptString(JavaScriptObject):
	name = 'String'
	prototype = JavaScriptObject()
	def __init__(self, value=''):
		self.value = value

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


#####################################################################
# errors
#####################################################################

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



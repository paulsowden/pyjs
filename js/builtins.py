

class Property(object):
	read_only = False
	dont_enum = False
	dont_delete = False
	internal = False
	def __init__(self, value):
		self.value = value


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
		return self.prototype.get(key).value
	
	def __setitem__(self, key, value): # [[Put]]
		if not self.can_put(key):
			return False
		if key in self.properties:
			self.properties[key].value = value
		self.properties[key] = Property(value)
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


class JavaScriptObject(BaseObject):
	name = 'Object'
	prototype = BaseObject()

class JavaScriptFunction(JavaScriptObject):
	name = 'Function'

class JavaScriptArray(JavaScriptObject):
	name = 'Array'

class JavaScriptString(JavaScriptObject):
	name = 'String'
	def __init__(self, value=''):
		self.value = value

class JavaScriptBoolean(JavaScriptObject):
	name = 'Boolean'
	def __init__(self, value=False):
		self.value = value

class JavaScriptNumber(JavaScriptObject):
	name = 'Number'
	def __init__(self, value=0.0):
		self.value = value

class JavaScriptMath(JavaScriptObject):
	name = 'Math'

class JavaScriptDate(JavaScriptObject):
	name = 'Date'

class JavaScriptRegExp(JavaScriptObject):
	name = 'RegExp'


#####################################################################
# errors
#####################################################################

class JavaScriptError(JavaScriptObject):
	pass

class JavaScriptEvalError(JavaScriptObject):
	pass

class JavaScriptRangeError(JavaScriptObject):
	pass

class JavaScriptReferenceError(JavaScriptObject):
	pass

class JavaScriptSyntaxError(JavaScriptObject):
	pass

class JavaScriptTypeError(JavaScriptObject):
	pass

class JavaScriptURIError(JavaScriptObject):
	pass



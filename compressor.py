import re

from js.parser import parse_str, parse_file, symbol_table

def block(s):
	if s.endswith(';'):
		s = s[:-1]
	return '{'+s+'}'

def paren(s, first):
	use_paren = first.lbp and first.lbp < s.lbp
	return ('(%s)' if use_paren else '%s') % compress(first)

def alphabetic_operator_righthand(s, right):
	right = right and compress(right) or ''
	return s.id + \
		(' ' if right and re.match(r'[a-zA-Z_$]', right[0]) else '') + right

def compress(s):

	if isinstance(s, list) or s.id == '{': # block statement
		if not isinstance(s, list):
			s = s.block
		return ''.join(compress(ast) for ast in s)

	## Primary Expressions
	elif s.id == 'this':
		return s.id
	elif s.id == '(identifier)':
		return s.value

	# literals
	elif s.id == '(number)':
		return s.value
	elif s.id == '(string)':
		strchar = "'" if s.value.count('"') > s.value.count("'") else '"'
		return strchar + s.value.replace(strchar, '\\' + strchar) + strchar
	elif s.id == '(regexp)':
		return s.value
	elif s.id == 'null':
		return 'null'
	elif s.id == 'undefined':
		return 'undefined'
	elif s.id == 'true':
		return 'true'
	elif s.id == 'false':
		return 'false'

	elif s.id == '(array)':
		return '[%s]' % ','.join(compress(a) for a in s.first)

	elif s.id == '(object)':
		properties = []
		for k, v in s.first:
			is_identifier = k.id == '(identifier)' or k.id == '(number)' \
				or re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', k.value)
			key = k.value if is_identifier else compress(k)
			properties.append('%s:%s' % (key, compress(v)))
		return '{%s}' % ','.join(properties)


	## Left-Hand Expressions

	elif s.id == '.':
		return paren(s, s.first) + '.' + paren(s, s.second)
	elif s.id == '[': # property
		return paren(s, s.first) + '[' + compress(s.second) + ']'

	elif s.id == 'new':
		return alphabetic_operator_righthand(s, s.first) + ('(' + \
			','.join(compress(arg) for arg in s.params) + ')'
				if hasattr(s, 'params') else '')

	elif s.id == '(':
		return paren(s, s.first) + '(' + ','.join(compress(t) for t in s.params) + ')'

	## Unary Operators
	elif s.id in ('typeof', 'void', 'delete'):
		return alphabetic_operator_righthand(s, s.first)
	elif s.id in ('+', '-', '++', '--') and hasattr(s, 'arity'): # unary
		return s.id + paren(s, s.first)
	elif s.id in ('~', '!'):
		return s.id + paren(s, s.first)

	## Assignment Operator
	elif s.id in ('=', '+=', '-=', '*=', '/='):
		return paren(s, s.first) + s.id + paren(s, s.second)

	## Comma Operator
	elif s.id == ',':
		return '%s,%s' % (compress(s.first), compress(s.second))

	## Postfix Expressions
	elif s.id in ('++', '--'):
		return paren(s, s.first) + s.id

	## Multiplicative Operators
	elif s.id in ('/', '*', '%'):
		return paren(s, s.first) + s.id + paren(s, s.second)

	## Additive Operators
	elif s.id in ('+', '-'):
		return paren(s, s.first) + s.id + paren(s, s.second)

	## Relational Operators
	elif s.id in ('<', '>', '<=', '>='):
		return paren(s, s.first) + s.id + paren(s, s.second)
	elif s.id in ('instanceof', 'in'):
		# TODO omit space if the token on the imediate left of the
		#      s.first if not an identifier
		return compress(s.first) + ' ' + \
			alphabetic_operator_righthand(s, s.second)

	## Equality Operators
	elif s.id in ('==', '!=', '!==', '!===', '||', '&&'):
		return paren(s, s.first) + s.id + paren(s, s.second)

	## Statements
	elif s.id == '(statement)':
		if not s.first:
			return ''
		stmt = compress(s.first)
		if stmt and not stmt.endswith(';') and not s.first.id in ('if', 'function', 'for', 'while', 'try', 'switch', 'do'):
			return stmt + ';'
		else:
			return stmt
	elif s.id == 'var':
		# TODO compress vars
		vars = []
		for var in s.first:
			#if var.id == '(identifier)': continue
			vars.append(compress(var)) # assignment
		return 'var ' + ','.join(vars)

	elif s.id == 'if':
		str = 'if(%s)' % compress(s.first)
		if len(s.block) > 1:
			str += block(compress(s.block))
		else:
			str += compress(s.block)
		if hasattr(s, 'elseblock'):
			str += 'else' + block(compress(s.elseblock))
		return str
	elif s.id == 'do':
		return 'do{%s}while(%s)' % (compress(s.block), compress(s.first))
	elif s.id == 'while':
		return 'while(%s)%s' % (compress(s.first), block(compress(s.block)))
	elif s.id == 'for':
		if hasattr(s, 'iterator'):
			for_loop = '%s in %s' % (compress(s.iterator), compress(s.object))
		else:
			for_loop = '%s;%s;%s' % (
				compress(s.initializer) if hasattr(s, 'initializer') else '',
				compress(s.condition) if hasattr(s, 'condition') else '',
				compress(s.counter) if hasattr(s, 'counter') else '')
		return 'for(%s)%s' % (for_loop, block(compress(s.block)))

	elif s.id in ('continue', 'break'):
		return s.id + (s.first and ' ' + s.first or '')
	elif s.id in ('return', 'throw'):
		return alphabetic_operator_righthand(s, s.first)
	elif s.id == 'with':
		return 'with(%s)%s' % (compress(s.first), block(compress(s.block)))
	elif s.id == 'switch':
		pass
	elif s.id == 'try':
		catch = 'catch(%s){%s}' % (compress(s.e), compress(s.catchblock)) \
			if hasattr(s, 'catchblock') else ''
		final = 'finally{%s}' % compress(s.finallyblock) \
			if hasattr(s, 'finallyblock') else ''
		return 'try{%s}%s%s' % (compress(s.block), catch, final)
	elif s.id == 'function':
		return 'function%s(%s)%s' % (
			' ' + compress(s.name) if s.name else '',
			','.join(compress(param) for param in s.params),
			block(compress(s.block)))
	#elif s.id == 'eval':
	#	return 'eval'

	elif s.id == '?':
		return compress(s.first) + '?' + compress(s.second) + ':' + compress(s.third)

	raise RuntimeError, "unknown operation %s" % s.id

class LexicalScope(object):
	def __init__(self, parent, vars=set(), params=[], functions={}):
		self.parent = parent
		if parent:
			parent.children.append(self)
		self.children = []
		self.vars = {}
		for name, function in functions.items():
			self.vars[name.value] = []
		for var in vars:
			self.vars[var] = []
		for param in params:
			self.vars[param.value] = []
	def get_var(self, var):
		if var in self.vars:
			return self.vars[var]
		elif self.parent:
			return self.parent.get_var(var)
		else:
			return None


def char_to_var_name(char):
	prefix_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_$'
	all_chars = prefix_chars + '0123456789'

	chars = prefix_chars
	var = ''
	while char >= 0:
		var += chars[char%len(chars)]
		char //= len(chars)
		char -= 1
		chars = all_chars
	return var

def rename_vars(ast):
	scope = LexicalScope(None)
	populate_scope(ast, ast.first, scope)

	def flatten(scope):
		vars = []
		for item in scope.vars.items():
			vars.append((scope,) + item)
		for child in scope.children:
			vars.extend(flatten(child))
		scope.vars = {}
		return vars

	vars = flatten(scope)
	vars.sort(lambda a, b: len(b[2]) - len(a[2]))
	for scope, var, identifiers in vars:
		char = 0
		# TODO when checking for name collisions we should check all scopes
		#      that references to this variable occur in for collisions
		while scope.get_var(char_to_var_name(char)):
			char += 1
		scope.vars[char_to_var_name(char)] = True
		for identifier in identifiers:
			identifier.value = char_to_var_name(char)

def populate_scope(parent, s, scope):
	if isinstance(s, list) or s.id == '{': # block statement
		if not isinstance(s, list):
			s = s.block
		for ast in s:
			populate_scope(s, ast, scope)

	elif s.id == '(identifier)':
		if parent.id != '.' or s != parent.second:
			var = scope.get_var(s.value)
			if var is not None:
				var.append(s)
	elif s.id == '(array)':
		for ast in s.first:
			populate_scope(s, ast, scope)
	elif s.id == '(object)':
		for k, v in s.first:
			populate_scope(s, v, scope)
	elif s.id in ('new', '('):
		populate_scope(s, s.first, scope)
		if hasattr(s, 'params'):
			for ast in s.params:
				populate_scope(s, ast, scope)
	elif s.id == 'var':
		for ast in s.first:
			populate_scope(s, ast, scope)
	elif s.id == 'if':
		populate_scope(s, s.first, scope)
		populate_scope(s, s.block, scope)
		if hasattr(s, 'elseblock'):
			populate_scope(s, s.elseblock, scope)
	elif s.id == 'for':
		if hasattr(s, 'iterator'):
			populate_scope(s, s.iterator, scope)
			populate_scope(s, s.object, scope)
		else:
			populate_scope(s, s.initializer, scope)
			populate_scope(s, s.condition, scope)
			populate_scope(s, s.counter, scope)
		populate_scope(s, s.block, scope)
	elif s.id == 'try':
		populate_scope(s, s.block, scope)
		if hasattr(s, 'catchblock'):
			catch_scope = LexicalScope(scope, params=[s.e])
			populate_scope(s, s.catchblock, catch_scope)
		if hasattr(s, 'finallyblock'):
			populate_scope(s, s.finallyblock, scope)
	elif s.id == 'function':
		function_scope = LexicalScope(scope, s.vars, s.params, s.functions)
		if s.name:
			populate_scope(s, s.name, s.is_decl and function_scope or scope)
		for param in s.params:
			populate_scope(s, param, function_scope)
		populate_scope(s, s.block, function_scope)
	else:
		if s.first:
			populate_scope(s, s.first, scope)
		if s.second:
			populate_scope(s, s.second, scope)
		if hasattr(s, 'block'):
			populate_scope(s, s.block, scope)

if __name__ == '__main__':
	#js = '/home/paul/code/pyjs/jslint/jslint.js'
	#js = '/home/paul/code/pyjs/narcissus.js'
	#js = '/home/paul/code/pyjs/test.js'
	js = '/home/paul/code/js/ids/json.js'
	js = '/Users/paul/Code/paulsowden.com/code/js/ids/URL.js'
	#js = '/Users/paul/Code/pyjs/test/hook.js'
	#js = '/Users/paul/Code/pyjs/test/for.js'
	#js = '/Users/paul/Code/pyjs/test/try.js'

	ast = parse_file(js)
	#print ast

	rename_vars(ast)
	print compress(ast.first)


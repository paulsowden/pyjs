import re

from js.parser import parse_str, parse_file, symbol_table

def block(s):
	if s.endswith(';'):
		s = s[:-1]
	return '{'+s+'}'

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
		return '[]'

	elif s.id == '(object)':
		properties = []
		for k, v in s.first:
			if k.id == '(identifier)' or k.id == '(number)' \
					or re.match(r'^[a-zA-Z_$][a-zA-Z0-9_$]*$', k.value):
				properties.append(k.value + ':' + compress(v))
			else: # (string)
				properties.append(compress(k) + ':' + compress(v))
		return '{' + ','.join(properties) + '}'


	## Left-Hand Expressions

	elif s.id == '.':
		return compress(s.first) + '.' + compress(s.second)
	elif s.id == '[': # property
		return compress(s.first) + '[' + compress(s.second) + ']'

	elif s.id == 'new':
		return alphabetic_operator_righthand(s, s.first) + ('(' + \
			','.join(compress(arg) for arg in s.params) + ')'
				if hasattr(s, 'params') else '')

	elif s.id == '(':
		return  compress(s.first) + '(' + ','.join(compress(t) for t in s.params) + ')'

	## Unary Operators
	elif s.id in ('typeof', 'void', 'delete'):
		return alphabetic_operator_righthand(s, s.first)
	elif s.id == '+' and hasattr(s, 'arity'): # unary
		pass
	elif s.id == '-' and hasattr(s, 'arity'): # unary
		pass
	elif s.id == '~':
		return '~' + compress(s.first)
	elif s.id == '!':
		return '!' + compress(s.first)

	elif s.id == '=':
		return compress(s.first) + '=' + compress(s.second)

	## Multiplicative Operators
	elif s.id == '/':
		return compress(s.first) + '/' + compress(s.second)
	elif s.id == '*':
		return compress(s.first) + '*' + compress(s.second)
	elif s.id == '%':
		return compress(s.first) + '%' + compress(s.second)

	## Additive Operators
	elif s.id == '+':
		return compress(s.first) + '+' + compress(s.second)
	elif s.id == '-':
		return compress(s.first) + '-' + compress(s.second)

	## Relational Operators
	elif s.id == '<':
		return compress(s.first) + '<' + compress(s.second)
	elif s.id == '>':
		return compress(s.first) + '>' + compress(s.second)
	elif s.id == '<=':
		return compress(s.first) + '<=' + compress(s.second)
	elif s.id == '>=':
		return compress(s.first) + '>=' + compress(s.second)
	elif s.id in ('instanceof', 'in'):
		# TODO omit space if the token on the imediate left of the
		#      s.first if not an identifier
		return compress(s.first) + ' ' + \
			alphabetic_operator_righthand(s, s.second)

	## Equality Operators
	elif s.id in ('==', '!=', '!==', '!===', '||', '&&', '+=', '-=', '*=', '/='):
		return compress(s.first) + s.id + compress(s.second)

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
			if var.id == '(identifier)': continue
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
		pass
	elif s.id == 'while':
		pass
	elif s.id == 'for':
		return ''#'for()'

	elif s.id in ('continue', 'break'):
		return 'break' + (s.first and ' ' + s.first or '')
	elif s.id in ('return', 'throw'):
		return alphabetic_operator_righthand(s, s.first)
	elif s.id == 'with':
		pass
	elif s.id == 'switch':
		pass
	elif s.id == 'try':
		pass
	elif s.id == 'function':
		return 'function' + (' '+s.name if s.name else '') + '('+','.join(s.params)+')' + block(compress(s.block))
	elif s.id == 'eval':
		return 'eval'

	elif s.id == '?':
		return compress(s.first) + '?' + compress(s.second) + ':' + compress(s.third)

	raise RuntimeError, "unknown operation %s" % s.id

if __name__ == '__main__':
	#js = '/home/paul/code/pyjs/jslint/jslint.js'
	#js = '/home/paul/code/pyjs/narcissus.js'
	#js = '/home/paul/code/pyjs/test.js'
	js = '/home/paul/code/js/ids/json.js'
	js = '/Users/paul/Code/paulsowden.com/code/js/ids/URL.js'
	#js = '/Users/paul/Code/paulsowden.com/code/pyjs/test/hook.js'

	ast = parse_file(js)
	#print ast

	print compress(ast.first)


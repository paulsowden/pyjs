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
		pass
	elif s.id == 'while':
		pass
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
		return 'with(%s)%s' % (compress(s.first), block(compress(s.second)))
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
			' ' + s.name if s.name else '',
			','.join(s.params),
			block(compress(s.block)))
	#elif s.id == 'eval':
	#	return 'eval'

	elif s.id == '?':
		return compress(s.first) + '?' + compress(s.second) + ':' + compress(s.third)

	raise RuntimeError, "unknown operation %s" % s.id

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

	print compress(ast.first)


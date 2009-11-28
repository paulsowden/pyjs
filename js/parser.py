
from lexer import JavaScriptLexer

class JavaScriptSyntaxError(SyntaxError):
	def __init__(self, msg, t=None):
		self.msg = msg
		if not t:
			t = nexttoken
		if t.id == '(end)':
			t = token
		self.lineno = t.lineno
		self.offset = t.offset
		self.text = lexer.lines[t.lineno]
		self.filename = lexer.filename

class Symbol(object):

	id = None
	value = None
	first = second = third = None

	reach = False
	reserved = False
	identifier = False

	def __init__(self, replace_token=None, first=None, second=None):
		if replace_token:
			self.lineno = replace_token.lineno
			self.offset = replace_token.offset
			self.start = replace_token.start
		self.first = first
		self.second = second

	def led(self, left):
		raise JavaScriptSyntaxError("Expected an operator and instead saw '%s'." %
			nexttoken.value, nexttoken)

	def nud(self):
		raise JavaScriptSyntaxError(
			"Expected an identifier and instead saw '%s'." % token.id, token)

	def __repr__(self):
		if self.id in ('(identifier)', '(number)', '(string)'):
			return "(%s %s)" % (self.id[1:-1], self.value)
		out = [self.id, self.first, self.second, self.third]
		out = map(str, filter(None, out))
		return "(" + " ".join(out) + ")"

def symbol(id, bp=0):
	try:
		s = symbol_table[id]
	except KeyError:
		class s(Symbol):
			pass
		s.__name__ = "symbol-" + id # for debugging
		s.id = id
		s.value = None
		s.lbp = bp
		symbol_table[id] = s
	else:
		s.lbp = max(bp, s.lbp)
	return s

def infix(id, bp):
	s = symbol(id, bp)
	def led(self, left):
		self.first = left
		self.second = parse(bp)
		return self
	s.led = led
	return s

def infix_r(id, bp):
	def led(self, left):
		self.first = left
		self.second = parse(bp-1)
		return self
	symbol(id, bp).led = led

def prefix(id, bp=150):
	s = symbol(id)
	def nud(self):
		self.first = parse(bp)
		self.arity = 'unary'
		return self
	s.nud = nud
	return s

def suffix(id):
	s = symbol(id, 150)
	def led(self, left):
		self.first = left
		return self
	s.led = led
	return s

def type(id, f=None):
	s = symbol(id)
	if f: s.nud = f
	return s

def reserve(id, f=None):
	s = type(id, f)
	s.identifier = s.reserved = True
	return s

def reservevar(id):
	return reserve(id, lambda self: self)

def assignop(id):
	@method(symbol(id, 20))
	def led(self, left):
		self.first = left
		if not left or left.reserved or \
				(left.id != '.' and left.id != '[' and not left.identifier):
			raise JavaScriptSyntaxError("Bad assignment.", self)
		self.second = parse(19)
		return self

def stmt(id):
	s = symbol(id)
	s.identifier = s.reserved = True
	return s

def method(s):
	# decorator
	assert issubclass(s, Symbol)
	def bind(fn):
		setattr(s, fn.__name__, fn)
	return bind


#####################################################################
# symbol table
#####################################################################


symbol_table = {}

type('(number)', lambda self: self)
type('(string)', lambda self: self)
type('(regexp)', lambda self: self)
type('(array)')
type('(object)')

symbol('(identifier)').nud = lambda self: self

symbol('(statements)'); symbol('(statement)')

# special parse tokens
symbol('(global)')
symbol('(endline)'); symbol('(begin)'); symbol('(end)').reach = True

symbol(')'); symbol(']'); symbol('}').reach = True
symbol(';'); symbol(':').reach = True

@method(symbol(',', 10))
def led(self, left):
	self.first = left
	self.second = parse(0)
	return self

reserve('else')
reserve('case').reach = True; reserve('default').reach = True
reserve('catch'); reserve('finally')

reservevar('this')
reservevar('null')
reservevar('true'); reservevar('false')

assignop('=')
assignop('+='); assignop('-='); assignop('*='); assignop('/=')
assignop('%='); assignop('&='); assignop('|='); assignop('^=')
assignop('<<='); assignop('>>='); assignop('>>>=')

@method(infix('?', 30))
def led(self, left):
	self.first = left
	self.second = parse(10)
	advance(':')
	self.third = parse(10)
	return self

infix('||', 40); infix('&&', 50)
infix('|', 70); infix('^', 80); infix('&', 90)

infix('==', 100); infix('===', 100); infix('!=', 100); infix('!==', 100)
infix('<', 100); infix('>', 100); infix('<=', 100); infix('>=', 100)

infix('<<', 120); infix('>>', 120); infix('>>>', 120)

infix('in', 120); infix('instanceof', 120)
infix('+', 130); prefix('+')
infix('-', 130); prefix('-')
infix('*', 140); infix('/', 140); infix('%', 140)

suffix('++'); prefix('++')
suffix('--'); prefix('--')

prefix('delete', 0)

prefix('~'); prefix('!'); prefix('typeof')

@method(prefix('new', 155))
def nud(self):
	self.first = parse(155)
	return self

@method(infix('.', 160))
def led(self, left):
	self.first = left
	self.second = identifier()
	return self


@method(infix('(', 155))
def led(self, left):
	if left.id == 'new':
		s = left
	else:
		s = self
		self.lbp = 160
		self.first = left
	s.params = []
	while nexttoken.id != ')':
		s.params.append(parse(10))
		if nexttoken.id == ',':
			advance(',')
	advance(')')
	return s

@method(prefix('('))
def nud(self):
	v = parse(0)
	advance(')', self)
	return v


@method(infix('[', 160))
def led(self, left):
	self.first = left
	self.second = parse(0)
	advance(']', self)
	return self

@method(prefix('['))
def nud(self):
	s = symbol_table['(array)'](self)
	s.first = []
	while nexttoken.id != ']':
		s.first.append(parse(10))
		if nexttoken.id == ',':
			advance(',')
	advance(']', s)
	return s


@method(symbol('{'))
def fud(self):
	self.block = block()
	advance('}', self)
	return self

@method(symbol('{'))
def nud(self):
	s = symbol_table['(object)'](self)
	s.first = []
	while nexttoken.id != '}':
		key = optionalidentifier()
		if not key:
			if nexttoken.id in ('(string)', '(number)'):
				advance()
				key = token
			else:
				raise JavaScriptSyntaxError(
					"Expected '}' and instead saw '%s'." % nexttoken.value, nexttoken)
		advance(':')
		s.first.append((key, parse(10)))
		if nexttoken.id == ',':
			advance(',')
	advance('}', self)
	return s


def varstatement(prefix=False):
	vars = []
	while 1:
		var = identifier()
		context.vars.add(var.value)
		if prefix:
			return [var]
		if nexttoken.id == '=':
			t = nexttoken
			advance('=')
			var = symbol_table['='](t, var, parse(19))
		vars.append(var)
		if nexttoken.id != ',':
			return vars
		advance(',')


@method(stmt('var'))
def nud(self):
	self.first = varstatement()
	return self

def functionparams():
	t = nexttoken
	p = []
	advance('(')
	while nexttoken.id != ')':
		p.append(identifier())
		if nexttoken.id == ',':
			advance(',')
	advance(')', t)
	return p

def function(s, is_decl=True):
	global context
	s.is_decl = is_decl
	s.name = optionalidentifier()
	if is_decl and s.name:
		context.functions[s.name] = s
	s.params = functionparams()
	s.functions = {}
	s.vars = set()
	s.labels = set()
	s.iteration_depth = 0
	s.switch_depth = 0
	c, context = context, s
	s.block = block()
	context = c

@method(stmt('function'))
def fud(self):
	function(self)
	if nexttoken.id == '(' and nexttoken.lineno == token.lineno:
		raise JavaScriptSyntaxError(
			"Function statements are not invocable. Wrap the function expression in parens.", self)
	return self

@method(prefix('function'))
def nud(self):
	function(self, False)
	return self

@method(stmt('if'))
def nud(self):
	t = nexttoken
	advance('(')
	self.first = parse(5)
	advance(')', t)
	self.block = block()
	if nexttoken.id == 'else':
		advance('else')
		self.elseblock = block()
	return self

@method(stmt('try'))
def nud(self):
	self.block = block()
	if nexttoken.id == 'catch':
		advance('catch')
		advance('(')
		advance('(identifier)')
		self.e = token
		advance(')')
		self.catchblock = block()
	if nexttoken.id == 'finally':
		advance('finally')
		self.finallyblock = block()
	elif not hasattr(self, 'catchblock'):
		raise JavaScriptSyntaxError(
			"Expected 'catch' and instead saw '%s'." % nexttoken.value, nexttoken)
	return self

@method(stmt('while'))
def nud(self):
	t = nexttoken
	advance('(')
	self.first = parse(5)
	advance(')', t)
	context.iteration_depth += 1
	self.block = block()
	context.iteration_depth -= 1
	return self

@method(stmt('with'))
def nud(self):
	t = nexttoken
	advance('(')
	self.first = parse(5)
	advance(')', t)
	self.block = block()
	return self

@method(stmt('switch'))
def nud(self):
	t = nexttoken
	g = False
	advance('(')
	self.condition = parse(20)
	advance(')', t)
	t = nexttoken
	context.switch_depth += 1
	advance('{')
	self.cases = []
	while 1:
		if nexttoken.id == 'case':
			advance('case')
			self.cases.append(parse(20))
			g = True
			advance(':')
		elif nexttoken.id == 'default':
			advance('default')
			g = True
			advance(':')
		elif nexttoken.id == '}':
			advance('}', t)
			context.switch_depth -= 1
			return self
		elif nexttoken.id == '(end)':
			raise JavaScriptSyntaxError("Missing '}'.", nexttoken);
		elif g:
			if token.id == ',':
				raise JavaScriptSyntacError(
					"Each value should have its own case label.", token)
			elif token.id == ':':
				statements()
			else:
				raise JavaScriptSyntaxError("Missing ':' on a case clause.", token)
		else:
			raise JavaScriptSyntaxError(
				"Expected 'case' and instead saw '%s'." % nexttoken.value, nexttoken)

stmt('debugger')

@method(stmt('do'))
def nud(self):
	context.iteration_depth += 1
	self.block = block()
	context.iteration_depth -= 1
	advance('while')
	t = nexttoken
	advance('(')
	self.second = parse(5)
	advance(')', t)
	return self

@method(stmt('for'))
def nud(self):
	t = nexttoken
	advance('(')
	if peek(nexttoken.id == 'var' and 1 or 0).id == 'in':
		if nexttoken.id == 'var':
			advance('var')
			self.iterator = symbol_table['var']()
			self.iterator.first = varstatement(True)
		else:
			self.iterator = nexttoken
			advance('(identifier)')
		advance('in')
		self.object = parse(20)
		advance(')', t)
		self.block = block()
		return self
	else:
		if nexttoken.id != ';':
			if nexttoken.id == 'var':
				advance('var')
				self.initializer = symbol_table['var']()
				self.initializer.first = varstatement()
			else:
				self.initializer = parse(0, 'for')
				while nexttoken.id == ',':
					comma = nexttoken
					advance(',')
					self.initializer = symbol_table[','](
						comma, self.initializer, parse(0, 'for'))
		advance(';')
		if nexttoken.id != ';':
			self.condition = parse(20)
			if nexttoken.id == '=':
				eq = nexttoken
				advance('=')
				self.condition = symbol_table['='](
					eq, self.condition, parse(20))
		advance(';')
		if nexttoken.id == ';':
			raise JavaScriptSyntaxError("Expected ')' and instead saw ';'.",
					nexttoken)
		if nexttoken.id != ')':
			self.counter = parse(0, 'for')
			while nexttoken.id == ',':
				comma = nexttoken
				advance(',')
				self.counter = symbol_table[','](
					comma, self.counter, parse(0, 'for'))
		advance(')', t)
		context.iteration_depth += 1
		self.block = block()
		context.iteration_depth -= 1
		return self

@method(stmt('break'))
def nud(self):
	if nexttoken.identifier and token.lineno == nexttoken.lineno:
		if nexttoken.value not in context.labels:
			raise JavaScriptSyntaxError(
				"Unrecognized label '%s'." % nexttoken.value, nexttoken)
		advance('(identifier)')
		self.first = token
	elif not context.iteration_depth and not context.switch_depth:
		raise JavaScriptSyntaxError(
			"break outside of a loop or a switch", token)
	return self

@method(stmt('continue'))
def nud(self):
	if not context.iteration_depth:
		raise JavaScriptSyntaxError(
			"continue outside of a loop", token)
	if nexttoken.identifier and token.lineno == nexttoken.lineno:
		if nexttoken.value not in context.labels:
			raise JavaScriptSyntaxError(
				"Unrecognized label '%s'." % nexttoken.value, nexttoken)
		advance('(identifier)')
		self.first = token
	return self

@method(stmt('return'))
def nud(self):
	if context.id == '(global)':
		raise JavaScriptSyntaxError("return declared in the global scope.", token)
	if nexttoken.id != ';' and not nexttoken.reach:
		self.first = parse(19)
	return self

@method(stmt('throw'))
def nud(self):
	self.first = parse(19)
	return self

reserve('void')

# Superfluous reserved words
map(reserve,
	['abstract', 'boolean', 'byte', 'char', 'class', 'const', 'debugger',
	'double', 'enum', 'export', 'extends', 'final', 'float', 'goto',
	'implements', 'import', 'int', 'interface', 'long', 'native', 'package',
	'private', 'protected', 'public', 'short', 'static', 'super',
	'synchronized', 'throws', 'transient', 'volatile'])



lookahead = []
prevtoken = token = nexttoken = symbol_table['(begin)']


def peek(p=0):
	j = 0
	while j <= p:
		if len(lookahead) < j:
			t = lookahead[j]
		else:
			t = lexer.token()
			lookahead.append(t)
		j += 1
	return t

def advance(id='', t=None):
	global token, prevtoken, nexttoken
	prevtoken, token = token, nexttoken
	while 1:
		nexttoken = len(lookahead) and lookahead.pop(0) or lexer.token()
		if nexttoken.id == '(end)':
			return
		if nexttoken.id != '(endline)':
			break


# This is the heart of JSLINT, the Pratt parser. In addition to parsing, it
# is looking for ad hoc lint patterns. We add to Pratt's model .fud, which is
# like nud except that it is only used on the first token of a statement.
# Having .fud makes it much easier to define JavaScript. I retained Pratt's
# nomenclature.

# .nud     Null denotation
# .fud     First null denotation
# .led     Left denotation
#  lbp     Left binding power
#  rbp     Right binding power

# They are key to the parsing method called Top Down Operator Precedence.

def parse(rbp, initial=False):
	if nexttoken.id == '(end)':
		raise SyntaxError("Unexpected early end of program.")
	advance()
	if initial and hasattr(token, 'fud'):
		left = token.fud()
	else:
		left = token.nud()
		while rbp < nexttoken.lbp:
			advance()
			left = token.led(left)
	return left

def statement():
	t = nexttoken
	if t.id == ';': # empty
		advance(';')
		return
	s = symbol_table['(statement)']()
	s.comments = t.comments
	s.labels = set()
	# Is this a labelled statement?
	while t.identifier and not t.reserved and peek().id == ':':
		if t.value in context.labels:
			raise JavaScriptSyntaxError(
				"Duplicate label '%s'." % t.value, t)
		context.labels.add(t.value)
		s.labels.add(t)
		advance('(identifier)')
		advance(':')
		t = nexttoken
	s.first = parse(0, True)
	for label in s.labels:
		context.labels.remove(label.value)
	if nexttoken.id == ';':
		advance(';')
	elif not nexttoken.reach and nexttoken.lineno == token.lineno:
		raise JavaScriptSyntaxError(
			"Missing ; before statement '%s'." % nexttoken.value, nexttoken)
	return s

def statements():
	statements = []
	while not nexttoken.reach and nexttoken.id != '(end)':
		s = statement()
		if s: statements.append(s)
	return statements

def block(f=False):
	t = nexttoken
	if nexttoken.id == '{':
		advance('{')
		s = statements()
		advance('}', t)
	else:
		s = statement()
		s = [s] if s else []
	return s

def optionalidentifier():
	if nexttoken.identifier:
		advance()
		return token

def identifier():
	i = optionalidentifier()
	if not i:
		raise JavaScriptSyntaxError(
			"Expected an identifier and instead saw '%s'." %
			nexttoken.value, nexttoken)
	return i


def parse_str(js, filename=""):
	global lexer, context
	lexer = JavaScriptLexer(js, symbol_table, filename)
	
	context = symbol_table['(global)']()
	context.functions = {}
	context.vars = set()
	context.labels = set()
	context.iteration_depth = 0
	context.switch_depth = 0

	advance()
	context.first = statements()
	advance('(end)')

	return context

def parse_file(filename):
	return parse_str(open(filename, 'r').read(), filename)




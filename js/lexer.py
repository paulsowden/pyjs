import re


class JavaScriptLexer(object):

	tx = re.compile(r"""\s*(
		 [(){}\[.,:;\'"~\?\]#@]
		|==?=?
		|\/(\*|=|\/)?
		|\*[\/=]?
		|\+[+=]?
		|-[\-=]?
		|%=?
		|&[&=]?
		|\|[|=]?
		|>>?>?=?
		|<(=|<=?)?
		|\^=?
		|\!=?=?
		|[a-zA-Z_$][a-zA-Z0-9_$]*
		|[0-9]+([xX][0-9a-fA-F]+|\.[0-9]*)?([eE][+\-]?[0-9]+)?
	)""", re.VERBOSE)
	lx = re.compile(r'\*\/|\/\*')

	sx = re.compile(r'^"(?:\\.|[^"])*"|^\'(?:\\.|[^\'])*\'')
	rx = re.compile(r'^/((?:\\.|\[(?:\\.|[^\]])*\]|[^\/])+)\/([gimy]*)')

	def __init__(self, source, symbol_table, filename=None):
		self.symbol_table = symbol_table
		self.filename = filename
		self.lines = source.split('\n')
		self.lineno = -1
		self.offset = 0
		self.s = None
		self.prereg = True
		self.comments = []

		self.nextLine()
		self.start = 0

	def nextLine(self):
		self.lineno += 1
		if self.lineno >= len(self.lines):
			return False
		self.offset = 0
		self.s = self.lines[self.lineno];
		return True

	def it(self, type, value):
		"""Produce a token object.  The token inherits from a syntax symbol."""

		if type == '(punctuator)' or \
				(type == '(identifier)' and value in self.symbol_table):
			t = self.symbol_table[value]
		else:
			t = self.symbol_table[type]

		t = t()
		if type == '(identifier)':
			t.identifier = True

		t.value = value
		t.lineno = self.lineno
		t.offset = self.offset
		t.start = self.start
		i = t.id
		if i != '(endline)':
			self.prereg = i and (i[-1] in '(,=:[!&|?{};' or i == 'return')
			t.comments = self.comments
			self.comments = []
		return t

	def parse_string(self, t):
		r = ''
		j = 0
		while True:
			while j >= len(self.s):
				j = 0
				if not self.nextLine():
					errorAt("Unclosed string.", line)
			c = self.s[j]
			if c == t:
				self.offset += 1
				self.s = self.s[j+1:]
				return self.it('(string)', r)
			#elif c < ' ':
			#	if c == '\n' or c == '\r':
			#		break
			#	warningAt("Control character in string: {a}.", line, offset + j, s[:j])
			elif c == '\\' and j + 1 == len(self.s):
				self.nextLine()
				j = 0
			elif c == '\\':
				j += 1
				self.offset += 1
				c = self.s[j]

				if c == 'u':
					c = unichr(int(self.s[j+1:j+5], 16))
					j += 4
					self.offset += 4
				elif c == 'x':
					c = unichr(int(self.s[j+1:j+3], 16))
					j += 2
					self.offset += 2
				else:
					c = {
						'\\': '\\',
						"'": "'",
						'"': '"',
						'/': '/',
						'b': '\b',
						'f': '\f',
						'n': '\n',
						'r': '\r',
						't': '\t',
						'v': '\v',
					}.get(c, c)
			r += c
			self.offset += 1
			j += 1

	def token(self):
		"""called by advance to get the next token."""

		while 1:
			if not self.s:
				return self.it(self.nextLine() and '(endline)' or '(end)', '')
			m = self.tx.match(self.s)
			if not m:
				self.c = ''
				while self.s and self.s < '!':
					self.s = self.s[1:]
				if self.s:
					errorAt("Unexpected '%s'.", self.lineno, self.offset, self.s[0])
				continue

			t = m.group(1)
			#print t
			self.c = t[0]
			self.s = self.s[m.end():]
			self.offset += m.end()
			self.start = self.offset - len(t)

			# identifier
			if self.c.isalpha() or self.c == '_' or self.c == '$':
				return self.it('(identifier)', t)
			# number
			if self.c.isdigit():
				return self.it('(number)', t)
			# string
			if t == '"' or t == "'":
				return self.parse_string(t)
			# // comment
			if t == '//':
				self.s = ''
				continue
			# /* comment
			if t == '/*':
				while 1:
					m = self.lx.search(self.s)
					if m:
						break
					t += self.s + '\n'
					if not self.nextLine():
						errorAt("Unclosed comment.", self.lineno, self.offset)
				t += self.s[:m.end()]
				self.comments.append(t)
				self.offset += m.end()
				if self.s[m.start()] == '/':
					errorAt("Nested comment.", self.lineno, self.offset)
				self.s = self.s[m.end():]
				continue
			if t == '':
				continue
			# /
			if (t == '/' or t == '/=') and self.prereg:
				m = self.rx.match(t + self.s)
				if m:
					l = m.end() - len(t)
					t += self.s[:l]
					self.offset += l
					self.s = self.s[l:]
					return self.it('(regexp)', t)
			# punctuator
			return self.it('(punctuator)', t)



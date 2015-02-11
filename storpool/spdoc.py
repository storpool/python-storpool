#
#-
# Copyright (c) 2014, 2015  StorPool.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import spapi as api

class Html(object):
	escapeTable = {
		"&": "&amp;",
		'"': "&quot;",
		"'": "&apos;",
		">": "&gt;",
		"<": "&lt;",
	}
	
	def __init__(self):
		self.buf = ""
	
	def add(self, fmt, *args, **kwargs):
		args = map(self.escape, args)
		kwargs = dict((k, self.escape(v)) for k, v in kwargs.iteritems())
		self.buf += fmt.format(*args, **kwargs)
		return self
	
	def back(self, count):
		self.buf = self.buf[:-count]
		return self
	
	def escape(self, text):
		return "".join(self.escapeTable.get(c,c) for c in text)
	
	def __str__(self):
		return self.buf


class Doc(object):
	""" Base documentation entity class """
	def __init__(self, name, desc):
		self.name = name.strip()
		self.desc = desc.strip()

class TypeDoc(Doc):
	def __init__(self, name, desc, deps=[]):
		super(TypeDoc, self).__init__(name, desc)
		self.deps = deps
	
	def attrList(self, html):
		if not self.deps:
			html.add('<strong><a href="#{name}">{name}</a></strong>', name=self.name)
		else:
			assert len(self.deps) == 1
			dep = self.deps[0]
			html.add('<strong>{name}(<a href="#{dep}">{dep}</a>)</strong>', name=self.name, dep=dep.name)
		api.Api.spDoc.addType(self.name, self)
	
	def toJson(self, html, pad):
		html.add('<var>{0}</var>', self.name)

class EitherDoc(TypeDoc):
	def attrList(self, html):
		html.add("{0}\n", self.desc)
		html.add('<ul><em>Subtypes:</em>\n')
		for st in self.deps:
			html.add('<li>')
			st.attrList(html)
			html.add('</li>\n')
		html.add('</ul>\n')
	
	def toJson(self, html, pad):
		html.add('Either(')
		for st in self.deps:
			st.toJson(html, pad)
			html.add(', ')
		html.back(2).add(')')

class ListDoc(TypeDoc):
	def attrList(self, html):
		valT, = self.deps
		#html.add('{0}\n', self.desc)
		html.add('<ul>Element type: ')
		valT.attrList(html)
		html.add('\n</li></ul>\n')
	
	def toJson(self, html, pad):
		valT, = self.deps
		html.add('[')
		valT.toJson(html, pad)
		html.add(', ...]')

class DictDoc(TypeDoc):
	def attrList(self, html):
		keySt, valSt = self.deps
		html.add("{0}\n", self.desc)
		html.add('<ul>\n')
		html.add('<li>Key type: ')
		keySt.attrList(html)
		html.add('</li>\n')
		html.add('<li>Value type: ')
		valSt.attrList(html)
		html.add('</li>\n')
		html.add('</ul>\n')
	
	def toJson(self, html, pad):
		keySt, valSt = self.deps
		html.add('{{\n')
		html.add('{pad}"', pad=' ' * (pad + 2))
		keySt.toJson(html, pad + 2)
		html.add('": ')
		valSt.toJson(html, pad + 2)
		html.add(', ...\n')
		html.add('{pad}}}', pad=' ' * (pad))

class JsonObjectDoc(Doc):
	def __init__(self, name, desc, attrs):
		super(JsonObjectDoc, self).__init__(name, desc)
		self.attrs = attrs
	
	def attrList(self, html):
		html.add('<strong>{name}</strong>', name=self.name)
		html.add('<ul>\n')
		for attrName, (attrType, attrDesc) in sorted(self.attrs.iteritems()):
			html.add('<li class="attribute">{0}: ', attrName)
			if type(attrType) is TypeDoc:
				html.add(' (')
				attrType.attrList(html)
				html.add(')')
				if attrDesc:
					html.add(': {0}', attrDesc)
			else:
				if attrDesc:
					html.add(' {0}', attrDesc)
				attrType.attrList(html)
			
			html.add('</li>')
		html.add('</ul>\n')
	
	def toJson(self, html, pad):
		html.add('{{\n')
		for attrName, (attrType, attrDesc) in sorted(self.attrs.iteritems()):
			html.add('{pad}"{attr}": ', pad=' ' * (pad + 2), attr=attrName)
			attrType.toJson(html, pad + 2)
			html.add(',\n')
		html.back(2).add('\n{pad}}}', pad=' ' * pad)

class ApiCallDoc(Doc):
	def __init__(self, name, desc, method, path, args, json, returns):
		if not name:
			name = "XXX Missing title."
		
		super(ApiCallDoc, self).__init__(name, desc)
		self.method = method
		self.path = path
		self.args = args
		self.json = json
		self.returns = returns
		self.query = path.split("/")[3]
	
	def index(self, html):
		html.add('<li><a href="#{query}">{name}</a></li>\n', name=self.name, query=self.query)
	
	def build(self, html):
		html.add('<h3 id="{query}">{name} (<strong>{query}</strong>)</h3>\n', name=self.name, query=self.query)
		if self.desc:
			html.add("<p>{0}</p>\n", self.desc)
		
		html.add('<ol>')
		html.add('<li>Request:\n', query=self.path.split("/")[3])
		html.add('<ul>')
		html.add('<li>Example HTTP Request:\n')
		html.add('<pre><code>')
		html.add('{method} {path} HTTP/1.0\r\n', method=self.method, path=self.path)
		html.add('Host: <var>SP_API_HOST</var>:<var>SP_API_PORT</var>\r\n')
		html.add('Authorization: Storpool v1:<var>SP_AUTH_TOKEN</var>\r\n')
		html.add('Content-Length: <var>LENGTH</var>\r\n')
		html.add('\r\n')
		if self.json:
			self.json.toJson(html, 0)
		html.add('</code></pre>')
		html.add("</li>")
		
		html.add('<li>Method: <em>{method}</em></li>\n', method=self.method)
		html.add('<li>Path: <em>{path}</em></li>\n', path=self.path)
		
		html.add('<li>Arguments: ')
		if self.args:
			html.add('\n<ul>\n')
			for argName, argType in sorted(self.args.iteritems()):
				html.add('<li>{0} - <strong>{1}</strong>: <em>{2}</em></li>\n', argName, argType.name, argType.desc)
			html.add('</ul>\n')
		else:
			html.add('<em>No arguments</em>')
		html.add('</li>\n')
		
		html.add('<li>JSON: ')
		if self.json:
			self.json.attrList(html)
		else:
			html.add('<em>Either no JSON or {{}}</em>')
		html.add('</li>\n')
		html.add('</ul>\n')
		html.add('</li>\n')
		
		html.add('<li>Response:\n')
		html.add('<ul>\n')
		html.add('<li>Example HTTP Response:\n')
		html.add('<pre><code>')
		html.add('HTTP/1.0 200 OK\r\n')
		html.add('Connection: close\r\n')
		html.add('Content-Type: application/json\r\n')
		html.add('Cache-control: private\r\n')
		html.add('Content-Length: <var>LENGTH</var>\r\n')
		html.add('\r\n')
		html.add('{{\n')
		html.add('  "generation": <var>generation</var>,\n')
		html.add('  "data": ')
		self.returns.toJson(html, 2)
		html.add('\n}}\n')
		html.add('</code></pre>')
		html.add('</li>\n')
		
		html.add('<li>Response Data:\n')
		self.returns.attrList(html)
		html.add('</li>\n')
		html.add('</ul>\n')
		html.add('</li>\n')
		
		html.add('</ol>\n')


class DocSection(Doc):
	""" Description for API and API sections"""
	def buildDesc(self, html):
		currentParagraph = []
		isCode = False
		preSpaces = 0
		for line in self.desc.split('\n'):
			#print line.strip()
			if isCode:
				if line and line.strip() == '```':
					html.add('</code></pre>\n')
					isCode = False
				else:
					html.add('{0}\n', line[preSpaces:])
			else:
				if line and line.strip() == '```':
					html.add('<p>{0}</p>\n', "\n".join(currentParagraph))
					currentParagraph = []
					html.add('<pre class="code"><code>')
					preSpaces = len(line) - 3
					isCode = True
				elif line.strip():
					currentParagraph.append(line.strip())
				else:
					html.add('<p>{0}</p>\n', "\n".join(currentParagraph))
					currentParagraph = []
		if( len(currentParagraph) > 0 ):
			html.add('<p>{0}</p>\n', "\n".join(currentParagraph))
			currentParagraph = []

class ApiSectionDoc(DocSection):
	""" Doc. section for related API calls """
	def __init__(self, name, desc):
		super(ApiSectionDoc, self).__init__(name, desc)
		self.id = name.replace(' ', '-')
		self.calls = []
	
	def index(self, html):
		html.add('<li><a href="#{0}">{1}</a></li>\n', self.id, self.name)
		html.add('<ol>\n')
		for call in self.calls:
			call.index(html)
		html.add('</ol>\n')
	
	def build(self, html):
		html.add('<h2 id="{0}">{1}</h2>\n', self.id, self.name)
		self.buildDesc(html)
		
		for call in self.calls:
			call.build(html)

class ApiDoc(DocSection):
	""" API documentation holder """
	def __init__(self, title, desc):
		super(ApiDoc, self).__init__(title, desc)
		self.sections = []
		self.currentSection = None
		self.types = {}
	
	def addType(self, name, desc):
		self.types[name] = desc
	
	def addSection(self, name, desc):
		self.currentSection = ApiSectionDoc(name, desc)
		self.sections.append(self.currentSection)
	
	def addCall(self, call):
		self.currentSection.calls.append(call)
	
	def build(self, html):
		html.add("<h1>{0}</h1>\n", self.name)
		self.buildDesc(html)
		
		html.add('<ol>\n')
		for sect in self.sections:
			sect.index(html)
		html.add('<li><a href="#types">Data Types</a></li>\n')
		html.add('</ol>\n')
		
		for sect in self.sections:
			sect.build(html)
		
		html.add('<h2 id="types">Data Types</h2>\n')
		html.add('<table>\n')
		for name, doc in sorted(self.types.iteritems()):
			if not doc.deps:
				html.add('<tr id="{n}"><td><strong>{n}</strong>:</td><td>{d}</td></tr>\n', n=name, d=doc.desc)
		html.add('</table>\n')


if __name__ == '__main__':
	from spapi import Api
	
	html = Html()
	Api.spDoc.build(html)
	
	with open('ApiDoc.html.template') as tmpl:
		for line in tmpl.read().split('\n'):
			if line == '__DOC__':
				print html
			else:
				print line

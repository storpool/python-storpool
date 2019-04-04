"""
Helper classes for creating the HTML documetation of the StorPool API.
"""
#
# Copyright (c) 2014 - 2018  StorPool.
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

import six


class Html(object):
    escape_table = {
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
        kwargs = dict((k, self.escape(v)) for k, v in six.iteritems(kwargs))
        self.buf += fmt.format(*args, **kwargs)
        return self

    def back(self, count):
        self.buf = self.buf[:-count]
        return self

    def escape(self, text):
        return "".join(self.escape_table.get(c, c) for c in text)

    def __str__(self):
        return self.buf


class Doc(object):
    """ Base documentation entity class """
    def __init__(self, name, desc):
        self.name = name.strip()
        self.desc = desc.strip()


class TypeDoc(Doc):
    types = {}

    @classmethod
    def build_types(cls, html):
        html.add('<h2 id="types">Data Types</h2>\n')
        html.add('<table>\n')
        for name, doc in sorted(TypeDoc.types.items()):
            html.add('<tr id="{n}"><td><strong>{n}</strong>:'
                     '</td><td>{d}</td></tr>\n',
                     n=name, d=doc.desc)
        html.add('</table>\n')

    def __init__(self, name, desc, deps=[]):
        super(TypeDoc, self).__init__(name, desc)
        self.deps = deps

        if not self.deps and self.name not in TypeDoc.types:
            TypeDoc.types[self.name] = self

    def attr_list(self, html):
        if self.deps:
            assert len(self.deps) == 1
            dep = self.deps[0]
            html.add('<span class="opt">{name}</span> '
                     '<strong><a href="#{dep}">{dep}</a></strong>',
                     name=self.name, dep=dep.name)
        else:
            html.add('<strong><a href="#{name}">{name}</a></strong>',
                     name=self.name)

    def to_json(self, html, pad):
        if self.deps:
            assert len(self.deps) == 1
            dep = self.deps[0]
            dep.to_json(html, pad)
            html.add(' <span class="opt">/* {0} */</span>', self.name)
        else:
            html.add('<var>{0}</var>', self.name)


class EitherDoc(TypeDoc):
    def attr_list(self, html):
        html.add("{0}\n", self.desc)
        html.add('<ul><em>Subtypes:</em>\n')
        for val_type in self.deps:
            html.add('<li>')
            val_type.attr_list(html)
            html.add('</li>\n')
        html.add('</ul>\n')

    def to_json(self, html, pad):
        html.add('Either(')
        for val_type in self.deps:
            val_type.to_json(html, pad)
            html.add(', ')
        html.back(2).add(')')


class ListDoc(TypeDoc):
    def attr_list(self, html):
        val_type, = self.deps
        html.add('<ul>Element type: ')
        val_type.attr_list(html)
        html.add('\n</li></ul>\n')

    def to_json(self, html, pad):
        val_type, = self.deps
        html.add('[')
        val_type.to_json(html, pad)
        html.add(', ...]')


class DictDoc(TypeDoc):
    def attr_list(self, html):
        key_type, val_type = self.deps
        html.add("{0}\n", self.desc)
        html.add('<ul>\n')
        html.add('<li>Key type: ')
        key_type.attr_list(html)
        html.add('</li>\n')
        html.add('<li>Value type: ')
        val_type.attr_list(html)
        html.add('</li>\n')
        html.add('</ul>\n')

    def to_json(self, html, pad):
        key_type, val_type = self.deps
        html.add('{{\n')
        html.add('{pad}"', pad=' ' * (pad + 2))
        key_type.to_json(html, pad + 2)
        html.add('": ')
        val_type.to_json(html, pad + 2)
        html.add(', ...\n')
        html.add('{pad}}}', pad=' ' * (pad))


class JsonObjectDoc(Doc):
    def __init__(self, name, desc, attrs):
        super(JsonObjectDoc, self).__init__(name, desc)
        self.attrs = attrs

    def attr_list(self, html):
        html.add('<strong>{name}</strong>', name=self.name)
        self._attr_list(html)

    def _attr_list(self, html):
        html.add('<ul>\n')
        for attr_name, (attr_type, attr_desc) in sorted(self.attrs.items()):
            html.add('<li class="attribute">{0}: ', attr_name)
            if type(attr_type) is TypeDoc:
                html.add(' (')
                attr_type.attr_list(html)
                html.add(')')
                if attr_desc:
                    html.add(': {0}', attr_desc)
            else:
                if attr_desc:
                    html.add(' {0}', attr_desc)
                if type(attr_type) is JsonObjectDoc:
                    attr_type._attr_list(html)
                else:
                    attr_type.attr_list(html)

            html.add('</li>')
        html.add('</ul>\n')

    def to_json(self, html, pad):
        html.add('{{\n')
        for attr_name, (attr_type, attr_desc) in sorted(self.attrs.items()):
            html.add('{pad}"{attr}": ', pad=' ' * (pad + 2), attr=attr_name)
            attr_type.to_json(html, pad + 2)
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
        html.add('<li><a href="#{query}">{name}</a></li>\n',
                 name=self.name, query=self.query)

    def build(self, html):
        html.add('<h3 id="{query}">{name} (<strong>{query}</strong>)</h3>\n',
                 name=self.name, query=self.query)
        if self.desc:
            html.add("<p>{0}</p>\n", self.desc)

        html.add('<ol>')
        html.add('<li>Request:\n', query=self.path.split("/")[3])
        html.add('<ul>')
        html.add('<li>Example HTTP Request:\n')
        html.add('<pre><code>')
        html.add('{method} {path} HTTP/1.0\r\n',
                 method=self.method, path=self.path)
        html.add('Host: <var>SP_API_HOST</var>:<var>SP_API_PORT</var>\r\n')
        html.add('Authorization: Storpool v1:<var>SP_AUTH_TOKEN</var>\r\n')
        html.add('Content-Length: <var>LENGTH</var>\r\n')
        html.add('\r\n')
        if self.json:
            self.json.to_json(html, 0)
        html.add('</code></pre>')
        html.add("</li>")

        html.add('<li>Method: <em>{method}</em></li>\n', method=self.method)
        html.add('<li>Path: <em>{path}</em></li>\n', path=self.path)

        html.add('<li>Arguments: ')
        if self.args:
            html.add('\n<ul>\n')
            for arg_name, arg_type in sorted(self.args.items()):
                html.add('<li>{0} - <strong>{1}</strong>: <em>{2}</em></li>\n',
                         arg_name, arg_type.name, arg_type.desc)
            html.add('</ul>\n')
        else:
            html.add('<em>No arguments</em>')
        html.add('</li>\n')

        html.add('<li>JSON: ')
        if self.json:
            self.json.attr_list(html)
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
        self.returns.to_json(html, 2)
        html.add('\n}}\n')
        html.add('</code></pre>')
        html.add('</li>\n')

        html.add('<li>Response Data:\n')
        self.returns.attr_list(html)
        html.add('</li>\n')
        html.add('</ul>\n')
        html.add('</li>\n')

        html.add('</ol>\n')


class DocSection(Doc):
    """ Description for API and API sections"""
    def build_desc(self, html):
        current_para = []
        is_code = False
        pre_spaces = 0
        for line in self.desc.split('\n'):
            if is_code:
                if line and line.strip() == '```':
                    html.add('</code></pre>\n')
                    is_code = False
                else:
                    html.add('{0}\n', line[pre_spaces:])
            else:
                if line and line.strip() == '```':
                    html.add('<p>{0}</p>\n', "\n".join(current_para))
                    current_para = []
                    html.add('<pre class="code"><code>')
                    pre_spaces = len(line) - 3
                    is_code = True
                elif line.strip():
                    current_para.append(line.strip())
                else:
                    html.add('<p>{0}</p>\n', "\n".join(current_para))
                    current_para = []
        if current_para:
            html.add('<p>{0}</p>\n', "\n".join(current_para))
            current_para = []


class ApiSectionDoc(DocSection):
    """ Doc. section for related API calls """
    def __init__(self, name, desc):
        super(ApiSectionDoc, self).__init__(name, desc)
        self.id = name.replace(' ', '-')  # pylint: disable=invalid-name
        self.calls = []

    def index(self, html):
        html.add('<li><a href="#{0}">{1}</a></li>\n', self.id, self.name)
        html.add('<ol>\n')
        for call in self.calls:
            call.index(html)
        html.add('</ol>\n')

    def build(self, html):
        html.add('<h2 id="{0}">{1}</h2>\n', self.id, self.name)
        self.build_desc(html)

        for call in self.calls:
            call.build(html)


class ApiDoc(DocSection):
    """ API documentation holder """
    def __init__(self, title, desc):
        super(ApiDoc, self).__init__(title, desc)
        self.sections = []
        self.current_sect = None

    def add_section(self, name, desc):
        self.current_sect = ApiSectionDoc(name, desc)
        self.sections.append(self.current_sect)

    def add_call(self, call):
        self.current_sect.calls.append(call)

    def build(self, html):
        html.add("<h1>{0}</h1>\n", self.name)
        self.build_desc(html)

        html.add('<ol>\n')
        for sect in self.sections:
            sect.index(html)
        html.add('<li><a href="#types">Data Types</a></li>\n')
        html.add('</ol>\n')

        for sect in self.sections:
            sect.build(html)

        TypeDoc.build_types(html)

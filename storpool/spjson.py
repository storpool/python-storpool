#
#-
# Copyright (c) 2014  StorPool.
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
try:
	import simplejson as js
except ImportError:
	from sys import stderr
	print >> stderr, 'simplejson unavailable, fall-back to standart python json'
	import json as js

from collections import defaultdict
import sputils as sp
import spdoc as dc

sort_keys = False
indent = None
separators = (',', ':')

load  = js.load
loads = js.loads

dump  = lambda obj, fp: js.dump(obj, fp, cls=JsonEncoder, sort_keys=sort_keys, indent=indent, separators=separators)
dumps = lambda obj: js.dumps(obj, cls=JsonEncoder, sort_keys=sort_keys, indent=indent, separators=separators)


class JsonEncoder(js.JSONEncoder):
	def default(self, o):
		if isinstance(o, JsonObjectImpl):
			return o.toJson()
		elif isinstance(o, set):
			return list(o)
		else:
			return super(JsonEncoder, self).default(o)


class JsonObjectImpl(object):
	def __new__(cls, json={}, **kwargs):
		if isinstance(json, cls):
			assert not kwargs, "Unsupported update on already contructed object"
			return json
		else:
			json.update(kwargs)
			
			self = super(JsonObjectImpl, cls).__new__(cls)
			object.__setattr__(self, '__jsonAttrs__', {})
			object.__setattr__(self, '__jsonCachedAttrs__', {})
			
			for key, val in json.iteritems():
				setattr(self, key, val)
			
			return self
	
	def __checkAttr(self, attr):
		if attr not in self.__jsonAttrDefs__:
			error = "'{cls}' has no attribute '{attr}'".format(cls=self.__class__.__name__, attr=attr)
			raise AttributeError(error)
	
	def __getattr__(self, attr):
		if attr not in self.__jsonAttrs__:
			self.__checkAttr(attr)
			self.__jsonAttrs__[attr] = self.__jsonAttrDefs__[attr].defaultVal()
		return self.__jsonAttrs__[attr]
	
	def __setattr__(self, attr, value):
		self.__checkAttr(attr)
		self.__jsonAttrs__[attr] = self.__jsonAttrDefs__[attr].handleVal(value)
	
	def toJson(self):
		return dict((attr, getattr(self, attr)) for attr in self.__jsonAttrDefs__)
	
	__str__ = __repr__ = lambda self: str(self.toJson())


class JsonObject(object):
	def __init__(self, **kwargs):
		self.attrDefs = dict((argName, sp.spType(argVal)) for argName, argVal in kwargs.iteritems())
	
	def __call__(self, cls):
		if issubclass(cls, JsonObjectImpl):
			attrDefs = dict(cls.__jsonAttrDefs__)
			attrDefs.update(self.attrDefs)
			docDescs = defaultdict(lambda: "", dict((attrName, attrDesc) for attrName, (attrType, attrDesc) in cls.spDoc.attrs.iteritems()))
		else:
			attrDefs = self.attrDefs
			docDescs = defaultdict(lambda: "")
		
		doc = ""
		if cls.__doc__ is not None:
			doc += cls.__doc__
		else:
			doc += "{0}.{1}".format(cls.__module__, cls.__name__)
		doc += "\n\n"
		doc += "    JSON attributes:\n"
		for attrName, attrType in sorted(attrDefs.iteritems()):
			doc += "        {name}: {type}\n".format(name=attrName, type=attrType.name)
		doc += "\n"
		
		if cls.__doc__ is not None:
			docDescs.update((k.strip(), v.strip()) for k, v in (m for m in (line.split(':') for line in cls.__doc__.split('\n')) if len(m) == 2))
		
		spDoc = dc.JsonObjectDoc(cls.__name__, cls.__doc__ or "XXX {0}.{1} not documented.".format(cls.__module__, cls.__name__), dict(
			(attrName, (attrType.spDoc, docDescs[attrName])) for attrName, attrType in attrDefs.iteritems()
		))
		
		return type(cls.__name__, (cls, JsonObjectImpl), dict(__jsonAttrDefs__=attrDefs, __module__=cls.__module__, __doc__=doc, spDoc=spDoc))


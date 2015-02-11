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
import gc
import re

from collections import Iterable, namedtuple
from inspect import isfunction, isclass
from os.path import exists, islink
from subprocess import Popen, PIPE
from time import sleep

import spdoc as doc
import spjson as js


sec  = 1.0
msec = 1.0e-3 * sec
usec = 1e-6 * sec

KB = 1024
MB = 1024 ** 2
GB = 1024 ** 3
TB = 1024 ** 4


def pr(x):
	print x
	return x

def noop(*args, **kwargs):
	pass

fTrue  = lambda *args, **kwargs: True
fFalse = lambda *args, **kwargs: False
fNone  = lambda *args, **kwargs: None
idty   = lambda x: x

fst  = lambda args: args[0]
snd  = lambda args: args[1]
trd  = lambda args: args[2]
last = lambda args: args[-1]
tail = lambda args: args[1:]
swap = lambda (x, y): (y, x)

roundUp = lambda n, k: ((n + k - 1) / k) * k
to_iter = lambda x: x if isinstance(x, Iterable) and not isinstance(x, str) else (x,)
lines   = lambda args: '\n'.join(map(str, args))


def noGC(fun):
	''' Disable garbage collection during the wrapped function '''
	def wrapper(*args, **kwargs):
		try:
			gc.disable()
			return fun(*args, **kwargs)
		finally:
			gc.enable()
			gc.collect()
	
	return wrapper

def pathPollWait(path, shouldExist, isLink, pollTime, maxTime):
	''' poll/listen for path to appear/disappear '''
	for i in xrange(int(maxTime / pollTime)):
		pathExists = exists(path)
		if pathExists and isLink:
			assert islink(devName)
		
		if pathExists == shouldExist:
			return True
		else:
			sleep(pollTime)
	else:
		return False


class InvalidArgumentException(Exception):
	def __init__(self, fmt, **kwargs):
		super(InvalidArgumentException, self).__init__()
		self.__dict__.update(**kwargs)
		self.__str = fmt.format(**kwargs)
	
	def __str__(self):
		return self.__str

def error(fmt, **kwargs):
	raise InvalidArgumentException(fmt, **kwargs)


SpType = namedtuple('SpType', ['name', 'handleVal', 'defaultVal', 'spDoc'])

def spList(lst):
	assert len(lst) == 1, "SpList :: [subType]"
	subType = spType(lst[0])
	valT = subType.handleVal
	name = "[{0}]".format(subType.name)
	_doc = doc.ListDoc(name, "A list of {0}".format(subType.name), deps=[subType.spDoc])
	return SpType(name, lambda xs: [valT(x) for x in xs], lambda: [], _doc)

def spSet(st):
	assert len(st) == 1, "SpSet :: set([subType])"
	subType = spType(list(st)[0])
	valT = subType.handleVal
	name = "{{{0}}}".format(subType.name)
	_doc = doc.ListDoc(name, "A set of {0}".format(subType.name), deps=[subType.spDoc])
	return SpType(name, lambda xs: set(valT(x) for x in xs), lambda: set(), _doc)

def spDict(dct):
	assert len(dct) == 1, "SpDict :: {keyType: valueType}"
	keySt, valSt = map(spType, dct.items()[0])
	keyT, valT = keySt.handleVal, valSt.handleVal
	name = "{{{0}: {1}}}".format(keySt.name, valSt.name)
	_doc = doc.DictDoc(name, "A dict from {0} to {1}".format(keySt.name, valSt.name), deps=[keySt.spDoc, valSt.spDoc])
	return SpType(name, lambda dct: dict((keyT(key), valT(val)) for key, val in dct.iteritems()), lambda: {}, _doc)

def maybe(val):
	subType = spType(val)
	valT = subType.handleVal
	name = "Optional({0})".format(subType.name)
	_doc = doc.TypeDoc("Optional", "If present must be of type {0}".format(subType.name), deps=[subType.spDoc])
	return SpType(name, valT, lambda: None, _doc)

def internal(val):
	subType = spType(val)
	valT = subType.handleVal
	name = "Internal({0})".format(subType.name)
	_doc = doc.TypeDoc("Internal", "An internal attribute used only for debugging. We strongly recommend that you do not use this attribute in any kind of automation.", deps=[subType.spDoc])
	return SpType(name, valT, lambda: None, _doc)

def const(constVal):
	name = js.dumps(constVal)
	_doc = doc.TypeDoc(name, "The constant value {0}.".format(name))
	return SpType(name, lambda val: val if val == constVal else error("Trying to assign a value to const val"), lambda: constVal, _doc)

def either(*types):
	types = map(spType, types)
	tpNames = ", ".join(t.name for t in types)
	name = "Either({0})".format(tpNames)
	_doc = doc.EitherDoc(name, "The value must be of one of the following types: {0}.".format(tpNames), [st.spDoc for st in types])
	
	def handleVal(val):
		for t in types:
			try:
				return t.handleVal(val)
			except:
				pass
		else:
			error("The value does not match any type")
	
	return SpType(name, handleVal, lambda: error("No default value for either type"), _doc)

eitherOr = lambda type, default: either(const(default), type)

spTypes = {
	list: spList,
	set: spSet,
	dict: spDict,
}

spDocTypes = {
	bool: doc.TypeDoc("bool", "true or false."),
	int: doc.TypeDoc("int", "An integer value."),
	long: doc.TypeDoc("long", "A long integer value."),
	str: doc.TypeDoc("string", "A string value."),
}

def spTypeVal(val):
	subType = spType(type(val))
	name = "{0}, default={1}".format(subType.name, val)
	_doc = doc.TypeDoc(name, "A value of type {0}. Default value = {1}.".format(subType.name, val))
	return SpType(name, subType.handleVal, lambda: val, _doc)

def spTypeFun(argName, validator, argDoc):
	return SpType(argName, validator, lambda: error("No default value for {argName}", argName=argName), doc.TypeDoc(argName, argDoc))

def spType(tp):
	if isinstance(tp, SpType):
		return tp
	elif isclass(tp) or isfunction(tp):
		doc = spDocTypes.get(tp, None)
		if doc is None:
			doc = tp.spDoc
		return SpType(tp.__name__, tp, lambda: error("No default value for {type}", type=tp.__name__), doc)
	else:
		for _type, _spType in spTypes.iteritems():
			if isinstance(tp, _type):
				return _spType(tp)
		else:
			return spTypeVal(tp)


#
# Copyright (c) 2014 - 2019  StorPool.
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
""" Type definition and validation functions. """

import collections
import functools
import inspect
import sys

import six

from . import spcatch
from . import spdoc as doc
from . import spjson as js


SpType = collections.namedtuple('SpType', [
    'name',
    'handleVal',
    'defaultVal',
    'spDoc',
])


def spList(lst):
    assert len(lst) == 1, "SpList :: [subType]"
    subType = spType(lst[0])
    valT = subType.handleVal
    name = "[{0}]".format(subType.name)
    _doc = doc.ListDoc(
        name, "A list of {0}".format(subType.name), deps=[subType.spDoc])

    def buildList(xs):
        lst = []
        exc = functools.reduce(
            lambda exc, x: spcatch.sp_catch(
                lambda tx: lst.append(tx),
                lambda: valT(x),
                exc),
            xs,
            None)
        spcatch.sp_caught(exc, name, lst)
        return lst

    return SpType(name, buildList, lambda: [], _doc)


def spSet(st):
    assert len(st) == 1, "SpSet :: set([subType])"
    subType = spType(list(st)[0])
    valT = subType.handleVal
    name = "{{{0}}}".format(subType.name)
    _doc = doc.ListDoc(
        name, "A set of {0}".format(subType.name), deps=[subType.spDoc])

    def buildSet(xs):
        st = set()
        exc = functools.reduce(
            lambda exc, x: spcatch.sp_catch(
                lambda tx: st.add(tx),
                lambda: valT(x),
                exc),
            xs,
            None)
        spcatch.sp_caught(exc, name, st)
        return st

    return SpType(name, buildSet, lambda: set(), _doc)


def spDict(dct):
    assert len(dct) == 1, "SpDict :: {keyType: valueType}"
    firstItem = list(dct.items())[0]
    keySt, valSt = spType(firstItem[0]), spType(firstItem[1])
    keyT, valT = keySt.handleVal, valSt.handleVal
    name = "{{{0}: {1}}}".format(keySt.name, valSt.name)
    _doc = doc.DictDoc(
        name,
        "A dict from {0} to {1}".format(keySt.name, valSt.name),
        deps=[keySt.spDoc, valSt.spDoc])

    def buildDict(xs):
        d = dict()
        exc = None
        for key, val in six.iteritems(xs):
            data = []
            exc = spcatch.sp_catch(
                lambda tx: data.append(tx),
                lambda: keyT(key),
                exc)
            if len(data) == 1:
                exc = spcatch.sp_catch(
                    lambda tx: data.append(tx),
                    lambda: valT(val),
                    exc)
                if len(data) == 2:
                    d[data[0]] = data[1]
                else:
                    d[data[0]] = None
        spcatch.sp_caught(exc, name, d)
        return d

    return SpType(name, buildDict, lambda: {}, _doc)


def maybe(val):
    subType = spType(val)

    def validate(val):
        """Validate the supplied value, possibly None."""
        if val is None:
            return None
        return subType.handleVal(val)

    name = "Optional({0})".format(subType.name)
    _doc = doc.TypeDoc(
        "Optional",
        "If present must be of type {0}".format(subType.name),
        deps=[subType.spDoc])
    return SpType(name, validate, lambda: None, _doc)


def internal(val):
    subType = spType(val)
    valT = subType.handleVal
    name = "Internal({0})".format(subType.name)
    _doc = doc.TypeDoc(
        "Internal",
        "An internal attribute used only for debugging. "
        "We strongly recommend that you do not use this attribute in "
        "any kind of automation.",
        deps=[subType.spDoc])
    return SpType(name, valT, lambda: None, _doc)


def const(constVal):
    name = js.dumps(constVal)
    _doc = doc.TypeDoc(name, "The constant value {0}.".format(name))
    return SpType(name,
                  lambda val: val if val == constVal
                  else spcatch.error("Trying to assign a value to const val"),
                  lambda: constVal, _doc)


def either(*types):
    types = [spType(tp) for tp in types]
    tpNames = ", ".join(t.name for t in types)
    name = "Either({0})".format(tpNames)
    _doc = doc.EitherDoc(
        name,
        "The value must be of one of the following types: {0}."
        .format(tpNames),
        [st.spDoc for st in types])

    def handleVal(val):
        for t in types:
            try:
                return t.handleVal(val)
            except Exception:
                pass
        else:
            spcatch.error("The value does not match any type")

    return SpType(name, handleVal,
                  lambda: spcatch.error("No default value for either type"),
                  _doc)


def eitherOr(tp, default):
    return either(const(default), tp)


spTypes = {
    list: spList,
    set: spSet,
    dict: spDict,
}

spDocTypes = {
    bool: doc.TypeDoc("bool", "true or false."),
    int: doc.TypeDoc("int", "An integer value."),
    float: doc.TypeDoc("float", "A floating point number."),
    str: doc.TypeDoc("string", "A string value."),
}


if sys.version_info[0] < 3:
    spDocTypes[long] = doc.TypeDoc(  # noqa: F821
        "long", "A long integer value.")
    longType = long  # noqa: F821
else:
    longType = int


def spTypeVal(val):
    subType = spType(type(val))
    name = "{0}, default={1}".format(subType.name, js.dumps(val))
    _doc = doc.TypeDoc(
        name, "A value of type {0}. Default value = {1}.".format(
            subType.name, val))
    return SpType(name, subType.handleVal, lambda: val, _doc)


def spTypeFun(argName, validator, argDoc):
    return SpType(argName, validator,
                  lambda: spcatch.error("No default value for {argName}",
                                        argName=argName),
                  doc.TypeDoc(argName, argDoc))


def spType(tp):
    if isinstance(tp, SpType):
        return tp
    elif inspect.isclass(tp) or inspect.isfunction(tp):
        _doc = spDocTypes.get(tp, None)
        if _doc is None:
            _doc = tp.spDoc
        return SpType(tp.__name__, tp,
                      lambda: spcatch.error("No default value for {type}",
                                            type=tp.__name__),
                      _doc)
    else:
        for _type, _spType in six.iteritems(spTypes):
            if isinstance(tp, _type):
                return _spType(tp)
        else:
            return spTypeVal(tp)


class JsonObject(object):
    def __init__(self, **kwargs):
        self.attrDefs = dict(
            (argName, spType(argVal))
            for argName, argVal in six.iteritems(kwargs))

    def __call__(self, cls):
        if issubclass(cls, js.JsonObjectImpl):
            attrDefs = dict(cls.__jsonAttrDefs__)
            attrDefs.update(self.attrDefs)
            docDescs = collections.defaultdict(lambda: "", dict(
                (attrName, attrDesc) for attrName, (attrType, attrDesc) in
                six.iteritems(cls.spDoc.attrs)))
        else:
            attrDefs = self.attrDefs
            docDescs = collections.defaultdict(lambda: "")

        _doc = ""
        if cls.__doc__ is not None:
            _doc += cls.__doc__
        else:
            _doc += "{0}.{1}".format(cls.__module__, cls.__name__)
        _doc += "\n\n"
        _doc += "    JSON attributes:\n"
        for attrName, attrType in sorted(six.iteritems(attrDefs)):
            _doc += "        {name}: {type}\n".format(
                name=attrName, type=attrType.name)
        _doc += "\n"

        if cls.__doc__ is not None:
            docDescs.update(
                (k.strip(), v.strip())
                for k, v in (
                    m for m in (
                        line.split(':') for line in cls.__doc__.split('\n')
                    ) if len(m) == 2))

        spDoc = doc.JsonObjectDoc(
            cls.__name__,
            cls.__doc__ or "XXX {0}.{1} not documented.".format(
                cls.__module__, cls.__name__),
            dict((attrName, (attrType.spDoc, docDescs[attrName]))
                 for attrName, attrType in six.iteritems(attrDefs)))

        return type(cls.__name__, (cls, js.JsonObjectImpl),
                    dict(__jsonAttrDefs__=attrDefs, __module__=cls.__module__,
                         __doc__=_doc, spDoc=spDoc))

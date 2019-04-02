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

from __future__ import print_function

import sys

import six


try:
    import simplejson as js
except ImportError:
    print('simplejson unavailable, fall-back to standard python json',
          file=sys.stderr)
    import json as js


from . import spcatch


sort_keys = False
indent = None
separators = (',', ':')

load = js.load
loads = js.loads


def dump(obj, fp):
    return js.dump(obj, fp, cls=JsonEncoder, sort_keys=sort_keys,
                   indent=indent, separators=separators)


def dumps(obj):
    return js.dumps(obj, cls=JsonEncoder, sort_keys=sort_keys,
                    indent=indent, separators=separators)


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
            assert not kwargs, \
                "Unsupported update on already contructed object"
            return json
        else:
            j = dict(json)
            j.update(kwargs)

            self = super(JsonObjectImpl, cls).__new__(cls)
            object.__setattr__(self, '__jsonAttrs__', {})

            exc = None
            for attr, attrDef in six.iteritems(self.__jsonAttrDefs__):
                data = []
                exc = spcatch.sp_catch(
                    lambda tx: data.append(tx),
                    lambda: attrDef.handleVal(j[attr]) if attr in j
                    else attrDef.defaultVal(),
                    exc)
                if data:
                    self.__jsonAttrs__[attr] = data[0]
                else:
                    self.__jsonAttrs__[attr] = None
            spcatch.sp_caught(exc, self.__class__.__name__, self)

            return self

    def __getattr__(self, attr):
        if attr not in self.__jsonAttrs__:
            error = "'{cls}' has no attribute '{attr}'".format(
                cls=self.__class__.__name__, attr=attr)
            raise AttributeError(error)

        return self.__jsonAttrs__[attr]

    def __setattr__(self, attr, value):
        if attr not in self.__jsonAttrDefs__:
            error = "'{cls}' has no attribute '{attr}'".format(
                cls=self.__class__.__name__, attr=attr)
            raise AttributeError(error)

        self.__jsonAttrs__[attr] = self.__jsonAttrDefs__[attr].handleVal(value)

    def toJson(self):
        return dict(
            (attr, getattr(self, attr)) for attr in self.__jsonAttrDefs__)

    def __iter__(self):
        return six.iteritems(self.toJson())

    _asdict = toJson
    __str__ = __repr__ = lambda self: str(self.toJson())

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
""" Low-level helpers for the StorPool JsonObject implementation. """

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


SORT_KEYS = False
INDENT = None
SEPARATORS = (',', ':')

load = js.load  # pylint: disable=invalid-name
loads = js.loads  # pylint: disable=invalid-name


def dump(obj, filep):
    """ Serialize an object with reasonable default settings. """
    return js.dump(obj, filep, cls=JsonEncoder, sort_keys=SORT_KEYS,
                   indent=INDENT, separators=SEPARATORS)


def dumps(obj):
    """ Serialize an object to a string with reasonable default settings. """
    return js.dumps(obj, cls=JsonEncoder, sort_keys=SORT_KEYS,
                    indent=INDENT, separators=SEPARATORS)


class JsonEncoder(js.JSONEncoder):
    """ Help serialize a JsonObject instance. """

    def default(self, o):
        """ Invoke a suitable serialization function. """
        # pylint: disable=method-hidden
        # (this is by design; see json.JSONEncoder.default())
        if isinstance(o, JsonObjectImpl):
            return o.to_json()
        if isinstance(o, set):
            return list(o)
        return super(JsonEncoder, self).default(o)


class JsonObjectImpl(object):
    """ Base class for a serializable value object; see JsonObject. """

    def __new__(cls, json=None, **kwargs):
        """ Construct a value object as per its __jsonAttrDefs__. """

        if isinstance(json, cls):
            assert not kwargs, \
                "Unsupported update on already contructed object"
            return json

        j = dict(json) if json is not None else {}
        j.update(kwargs)

        self = super(JsonObjectImpl, cls).__new__(cls)
        object.__setattr__(self, '__jsonAttrs__', {})

        exc = None
        for attr, attr_def in six.iteritems(self.__jsonAttrDefs__):
            data = []
            # pylint: disable=cell-var-from-loop
            # (the "handle" and "func" arguments are always
            #  evaluated immediately, never deferred)
            exc = spcatch.sp_catch(
                data.append,
                lambda: attr_def.handleVal(j[attr]) if attr in j
                else attr_def.defaultVal(),
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

    def to_json(self):
        """ Store the member fields into a dictionary. """
        return dict(
            (attr, getattr(self, attr)) for attr in self.__jsonAttrDefs__)

    def __iter__(self):
        return six.iteritems(self.to_json())

    # obsolete, will be deprecated and removed
    toJson = to_json

    _asdict = to_json
    __str__ = __repr__ = lambda self: str(self.to_json())

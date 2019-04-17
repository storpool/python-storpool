#
# Copyright (c) 2019  StorPool.
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
""" Tests for the storpool.spjson.JsonEncoder and
the storpool.sptype.JsonObject classes. """

import pytest

from storpool import spcatch
from storpool import spjson
from storpool import sptype


@sptype.JsonObject(
    number=int, name=str, flags=sptype.maybe([bool])
)  # pylint: disable=too-few-public-methods
class TrivialClass(object):
    """ A trivial class demonstrating member names and types. """


class TestJsonEncoder(object):
    # pylint: disable=no-self-use
    """ Simple tests for the JsonEncoder class. """

    def test_miniscule(self):
        """ Some truly trivial test cases. """
        assert spjson.dumps({}) == '{}'
        assert spjson.dumps([]) == '[]'
        assert spjson.dumps(set([1, 2])) in ('[1,2]', '[2,1]')
        assert spjson.dumps({'a': [{'b': 3}, "c"]}) == '{"a":[{"b":3},"c"]}'

    def test_trivial(self):
        """ Test the interplay between JsonEncoder and JsonObject. """
        obj = TrivialClass(number=3, name='whee', flags=[False, True, False])
        assert spjson.loads(spjson.dumps(obj)) == {
            'number': 3,
            'name': 'whee',
            'flags': [False, True, False],
        }

        obj = TrivialClass({
            'number': 3,
            'name': 'whee',
            'flags': [False, True, False],
        })
        assert spjson.loads(spjson.dumps(obj)) == {
            'number': 3,
            'name': 'whee',
            'flags': [False, True, False],
        }

        obj = TrivialClass({
            'number': 3,
            'name': 'whee',
        })
        assert spjson.loads(spjson.dumps(obj)) == {
            'number': 3,
            'name': 'whee',
            'flags': None,
        }

        with pytest.raises(spcatch.InvalidArgumentError) as err:
            obj = TrivialClass({
                'number': 3,
                'flags': [False, True, False],
            })
        obj = err.value.partial
        assert obj.number == 3
        assert obj.name is None
        assert obj.flags == [False, True, False]

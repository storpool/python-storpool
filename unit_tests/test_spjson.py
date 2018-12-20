"""
Tests for the storpool.spjson.JsonEncoder and
the storpool.sputils.JsonObject classes.
"""

import pytest

from storpool import spjson
from storpool import sptype
from storpool import sputils


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

        with pytest.raises(sputils.InvalidArgumentException) as err:
            obj = TrivialClass({
                'number': 3,
                'flags': [False, True, False],
            })
        obj = err.value.partial
        assert obj.number == 3
        assert obj.name is None
        assert obj.flags == [False, True, False]

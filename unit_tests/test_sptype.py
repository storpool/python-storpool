"""
Test some basic functionality of the storpool.sputils.spType() class.
It is the base of all the conversions from Python objects to JSON and
vice versa that takes place behind the scenes in the Python bindings for
the StorPool API.
"""

import pytest

from storpool import sputils, sptypes


List = sputils.spType([int])
ListList = sputils.spType([List])
Set = sputils.spType(set([int]))
Dict = sputils.spType({int: float})


testSimple = [
    {
        'type': ListList,
        'name': 'list-ok',
        'args': [[6, 5], [4, 3], [2, 1]],
        'res': ([[6, 5], [4, 3], [2, 1]], None),
    },

    {
        'type': ListList,
        'name': 'list-fail',
        'args': [[1, 2], [3, 'meow', 4], [5, 6]],
        'res': ([[1, 2], [3, 4], [5, 6]], sputils.InvalidArgumentException),
    },

    {
        'type': Set,
        'name': 'set-ok',
        'args': set([1, 2, 4]),
        'res': (set([4, 2, 1]), None),
    },

    {
        'type': Set,
        'name': 'set-fail',
        'args': set([1, 2, 'meow', 4]),
        'res': (set([4, 2, 1]), sputils.InvalidArgumentException),
    },

    {
        'type': Dict,
        'name': 'dict-ok',
        'args': {1: 1.5, 2: 2.5, 3: 3.5, 4: 4.5, 5: 5.5},
        'res': ({2: 2.5, 5: 5.5, 3: 3.5, 1: 1.5, 4: 4.5}, None),
    },

    {
        'type': Dict,
        'name': 'dict-fail',
        'args': {1: 1.5, 2: 2.5, 'three': 3.5, 4: 'four point five', 5: 5.5},
        'res': (
            {2: 2.5, 5: 5.5, 4: None, 1: 1.5},
            sputils.InvalidArgumentException
        ),
    },

    {
        'type': sputils.spType([sptypes.MacAddr]),
        'name': 'mac-list-ok',
        'args': ['00:11:22:33:44:55'],
        'res': (['00:11:22:33:44:55'], None),
    },

    {
        'type': sputils.spType([sptypes.MacAddr]),
        'name': 'mac-list-fail',
        'args': ['00:11:22:33:44:55', 'xx'],
        'res': (['00:11:22:33:44:55'], sputils.InvalidArgumentException),
    },

    {
        'type': sputils.spType([sptypes.PeerStatus]),
        'name': 'peer-status-list-ok',
        'args': ['up', 'down', 'up'],
        'res': (['up', 'down', 'up'], None),
    },

    {
        'type': sputils.spType([sptypes.PeerStatus]),
        'name': 'peer-status-list-fail',
        'args': ['up', 'meow', 'down', 'meowmeow', 'up'],
        'res': (['up', 'down', 'up'], sputils.InvalidArgumentException),
    },
]


testObject = [
    {
        'type': sputils.spType([sptypes.RdmaDesc]),
        'name': 'rdma-desc-list-ok',
        'args': [
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        'res': (
            [
                {'guid': '0xdead', 'state': 'Connected'},
                {'guid': '0xbeef', 'state': 'Idle'},
            ],
            None
        ),
    },

    {
        'type': sputils.spType([sptypes.RdmaDesc]),
        'name': 'rdma-desc-list-fail',
        'args': [
            {'guid': '0xxx', 'state': 'Idle'},
            'pfth',
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        'res': (
            [
                {'guid': None, 'state': 'Idle'},
                {'guid': '0xdead', 'state': 'Connected'},
                {'guid': '0xbeef', 'state': 'Idle'},
            ],
            sputils.InvalidArgumentException
        ),
    },
]


class TestSpType(object):
    # pylint: disable=no-self-use
    """ Test that spType.handleVal() converts data or raises errors. """

    def test_simple(self):
        """ Test with simple types: dictionaries, lists, etc. """
        for stuff in testSimple:
            exp, exp_error = stuff['res']
            tp, args = stuff['type'], stuff['args']
            if exp_error is None:
                assert tp.handleVal(args) == exp
            else:
                with pytest.raises(exp_error) as err:
                    tp.handleVal(args)
                assert err.value.partial == exp

    def test_object(self):
        """ Test with some object types defined in storpool.sptypes. """
        for stuff in testObject:
            exp, exp_error = stuff['res']
            tp, args = stuff['type'], stuff['args']
            if exp_error is None:
                res = [obj.toJson() for obj in tp.handleVal(args)]
                assert res == exp
            else:
                with pytest.raises(exp_error) as err:
                    tp.handleVal(args)
                res = [obj.toJson() for obj in err.value.partial]
                assert res == exp

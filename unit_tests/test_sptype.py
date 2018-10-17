"""
Test some basic functionality of the storpool.sputils.spType() class.
It is the base of all the conversions from Python objects to JSON and
vice versa that takes place behind the scenes in the Python bindings for
the StorPool API.
"""

import unittest

import ddt
import pytest

from storpool import sputils, sptypes


List = sputils.spType([int])
ListList = sputils.spType([List])
Set = sputils.spType(set([int]))
Dict = sputils.spType({int: float})


testSimple = [
    (
        'list-ok',
        ListList,
        [[6, 5], [4, 3], [2, 1]],
        [[6, 5], [4, 3], [2, 1]],
        None,
    ),

    (
        'list-fail',
        ListList,
        [[1, 2], [3, 'meow', 4], [5, 6]],
        [[1, 2], [3, 4], [5, 6]],
        sputils.InvalidArgumentException,
    ),

    (
        'set-ok',
        Set,
        set([1, 2, 4]),
        set([4, 2, 1]),
        None,
    ),

    (
        'set-fail',
        Set,
        set([1, 2, 'meow', 4]),
        set([4, 2, 1]),
        sputils.InvalidArgumentException,
    ),

    (
        'dict-ok',
        Dict,
        {1: 1.5, 2: 2.5, 3: 3.5, 4: 4.5, 5: 5.5},
        {2: 2.5, 5: 5.5, 3: 3.5, 1: 1.5, 4: 4.5},
        None,
    ),

    (
        'dict-fail',
        Dict,
        {1: 1.5, 2: 2.5, 'three': 3.5, 4: 'four point five', 5: 5.5},
        {2: 2.5, 5: 5.5, 4: None, 1: 1.5},
        sputils.InvalidArgumentException,
    ),

    (
        'mac-list-ok',
        sputils.spType([sptypes.MacAddr]),
        ['00:11:22:33:44:55'],
        ['00:11:22:33:44:55'],
        None,
    ),

    (
        'mac-list-fail',
        sputils.spType([sptypes.MacAddr]),
        ['00:11:22:33:44:55', 'xx'],
        ['00:11:22:33:44:55'],
        sputils.InvalidArgumentException,
    ),

    (
        'peer-status-list-ok',
        sputils.spType([sptypes.PeerStatus]),
        ['up', 'down', 'up'],
        ['up', 'down', 'up'],
        None,
    ),

    (
        'peer-status-list-fail',
        sputils.spType([sptypes.PeerStatus]),
        ['up', 'meow', 'down', 'meowmeow', 'up'],
        ['up', 'down', 'up'],
        sputils.InvalidArgumentException,
    ),
]


testObject = [
    (
        'rdma-desc-list-ok',
        sputils.spType([sptypes.RdmaDesc]),
        [
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        [
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        None
    ),

    (
        'rdma-desc-list-fail',
        sputils.spType([sptypes.RdmaDesc]),
        [
            {'guid': '0xxx', 'state': 'Idle'},
            'pfth',
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        [
            {'guid': None, 'state': 'Idle'},
            {'guid': '0xdead', 'state': 'Connected'},
            {'guid': '0xbeef', 'state': 'Idle'},
        ],
        sputils.InvalidArgumentException
    ),
]


@ddt.ddt
class TestSpType(unittest.TestCase):
    # pylint: disable=no-self-use
    """ Test that spType.handleVal() converts data or raises errors. """

    @ddt.data(*testSimple)
    @ddt.unpack
    def test_simple(self, _name, dtype, args, exp, exp_error):
        """ Test with simple types: dictionaries, lists, etc. """
        if exp_error is None:
            assert dtype.handleVal(args) == exp
        else:
            with pytest.raises(exp_error) as err:
                dtype.handleVal(args)
            assert err.value.partial == exp

    @ddt.data(*testObject)
    @ddt.unpack
    def test_object(self, _name, dtype, args, exp, exp_error):
        """ Test with some object types defined in storpool.sptypes. """
        if exp_error is None:
            res = [obj.toJson() for obj in dtype.handleVal(args)]
            assert res == exp
        else:
            with pytest.raises(exp_error) as err:
                dtype.handleVal(args)
            res = [obj.toJson() for obj in err.value.partial]
            assert res == exp

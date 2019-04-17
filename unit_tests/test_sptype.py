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
"""
Test some basic functionality of the storpool.sptype.spType() class.

It is the base of all the conversions from Python objects to JSON and
vice versa that take place behind the scenes in the Python bindings for
the StorPool API.
"""

import unittest

import ddt
import pytest

from storpool import spcatch, sptype, sptypes


List = sptype.spType([int])            # pylint: disable=invalid-name
ListList = sptype.spType([List])       # pylint: disable=invalid-name
Set = sptype.spType(set([int]))        # pylint: disable=invalid-name
Dict = sptype.spType({int: float})     # pylint: disable=invalid-name


TEST_SIMPLE = [
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
        spcatch.InvalidArgumentError,
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
        spcatch.InvalidArgumentError,
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
        spcatch.InvalidArgumentError,
    ),

    (
        'mac-list-ok',
        sptype.spType([sptypes.MacAddr]),
        ['00:11:22:33:44:55'],
        ['00:11:22:33:44:55'],
        None,
    ),

    (
        'mac-list-fail',
        sptype.spType([sptypes.MacAddr]),
        ['00:11:22:33:44:55', 'xx'],
        ['00:11:22:33:44:55'],
        spcatch.InvalidArgumentError,
    ),

    (
        'peer-status-list-ok',
        sptype.spType([sptypes.PeerStatus]),
        ['up', 'down', 'up'],
        ['up', 'down', 'up'],
        None,
    ),

    (
        'peer-status-list-fail',
        sptype.spType([sptypes.PeerStatus]),
        ['up', 'meow', 'down', 'meowmeow', 'up'],
        ['up', 'down', 'up'],
        spcatch.InvalidArgumentError,
    ),
]


TEST_OBJECT = [
    (
        'rdma-desc-list-ok',
        sptype.spType([sptypes.RdmaDesc]),
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
        sptype.spType([sptypes.RdmaDesc]),
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
        spcatch.InvalidArgumentError,
    ),
]


@ddt.ddt
class TestSpType(unittest.TestCase):
    # pylint: disable=no-self-use
    """ Test that spType.handleVal() converts data or raises errors. """

    @ddt.data(*TEST_SIMPLE)
    @ddt.unpack
    def test_simple(self, _name, dtype, args, exp, exp_error):
        """ Test with simple types: dictionaries, lists, etc. """
        if exp_error is None:
            assert dtype.handleVal(args) == exp
        else:
            with pytest.raises(exp_error) as err:
                dtype.handleVal(args)
            assert err.value.partial == exp

    @ddt.data(*TEST_OBJECT)
    @ddt.unpack
    def test_object(self, _name, dtype, args, exp, exp_error):
        """ Test with some object types defined in storpool.sptypes. """
        if exp_error is None:
            res = [obj.to_json() for obj in dtype.handleVal(args)]
            assert res == exp
        else:
            with pytest.raises(exp_error) as err:
                dtype.handleVal(args)
            res = [obj.to_json() for obj in err.value.partial]
            assert res == exp

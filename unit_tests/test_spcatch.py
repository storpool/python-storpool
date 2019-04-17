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
""" Tests for the storpool.spcatch module. """

from storpool import spcatch


def test_simple():
    """ Test the behavior of sp_catch() and sp_caught(). """

    def return_int():
        """ Return an integer value. """
        return 616

    def raise_value_error():
        """ Raise a ValueError(). """
        raise ValueError('whee')

    def return_partial_int():
        """ Return a partially-constructed integer. """
        spcatch.error('static', 42)

    result = []

    def append_to_result(obj):
        """ Append an item to the result array. """
        result.append(obj)

    exc = spcatch.sp_catch(append_to_result, return_int, None)
    assert exc is None
    assert result == [616]

    old_exc = (ValueError, ValueError('foo'), None)
    exc = spcatch.sp_catch(append_to_result, return_int, old_exc)
    assert exc is old_exc
    assert result == [616, 616]

    exc = spcatch.sp_catch(append_to_result, raise_value_error, None)
    assert exc is not None
    assert exc[0] is ValueError
    assert isinstance(exc[1], ValueError)
    assert exc[1].args == ('whee',)
    assert result == [616, 616]

    exc = spcatch.sp_catch(append_to_result, return_partial_int, None)
    assert exc is not None
    assert exc[0] is spcatch.InvalidArgumentError
    assert isinstance(exc[1], spcatch.InvalidArgumentError)
    assert str(exc[1]) == 'static'
    assert exc[1].partial == 42
    assert result == [616, 616, 42]

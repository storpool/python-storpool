#
# Copyright (c) 2019  StorPool
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
""" Return partially-constructed objects if the processing fails.

This module allows the StorPool API binding classes to handle responses
from older or newer versions of the StorPool API itself. These responses
may lack some attributes or contain others that this version of the API
bindings may not know how to handle.

The sp_catch() and sp_caught() functions are used as a wrapper around
the response handling routines. If the handler raises InvalidArgumentError,
the partially-constructed objects will still be present in the exception
object's "partial" member. """

import sys

import six


class InvalidArgumentError(Exception):
    """ An exception object containing the partially-parsed response. """

    def __init__(self, fmt, partial=None, **kwargs):
        """ Store the partially-parsed response and an error message. """
        super(InvalidArgumentError, self).__init__()
        self.partial = partial
        self.__dict__.update(**kwargs)
        self.message = fmt.format(**kwargs)

    def __str__(self):
        """ Return a human-readable error message. """
        return self.message


def error(fmt, partial=None, **kwargs):
    """ Raise an error with the specified partial response and message. """
    raise InvalidArgumentError(fmt, partial, **kwargs)


def sp_catch(handle, func, exc):
    """ Invoke a handler and return an exception object if needed. """
    try:
        handle(func())
    except InvalidArgumentError as err:
        if err.partial is not None:
            handle(err.partial)
        if exc is None or not isinstance(exc[1], InvalidArgumentError):
            return sys.exc_info()
    except Exception:  # pylint: disable=broad-except
        if exc is None:
            return sys.exc_info()

    return exc


def sp_caught(exc, name, partial):
    """ Reraise a "partially processed data" error if needed. """
    if exc is None:
        return

    if isinstance(exc[1], InvalidArgumentError):
        exc[1].message = '{name}: {msg}'.format(name=name, msg=exc[1].message)
        exc[1].partial = partial
        six.reraise(*exc)

    raise InvalidArgumentError(
        fmt='{name}: {msg}', name=name, msg=str(exc[1]), partial=partial)

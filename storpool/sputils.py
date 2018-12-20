#
#-
# Copyright (c) 2014 - 2016  StorPool.
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

from __future__ import print_function

import gc
import re
import sys

from collections import Iterable, namedtuple
from inspect import isfunction, isclass
from os.path import exists, islink
from subprocess import Popen, PIPE
from time import sleep

import spdoc as doc
import spjson as js


sec  = 1.0
msec = 1.0e-3 * sec
usec = 1e-6 * sec

KB = 1024
MB = 1024 ** 2
GB = 1024 ** 3
TB = 1024 ** 4


def pr(x):
	print(x)
	return x


def pathPollWait(path, shouldExist, isLink, pollTime, maxTime):
	''' poll/listen for path to appear/disappear '''
	for i in xrange(int(maxTime / pollTime)):
		pathExists = exists(path)
		if pathExists and isLink:
			assert islink(devName)
		
		if pathExists == shouldExist:
			return True
		else:
			sleep(pollTime)
	else:
		return False


class InvalidArgumentException(Exception):
	def __init__(self, fmt, partial=None, **kwargs):
		super(InvalidArgumentException, self).__init__()
		self.partial = partial
		self.__dict__.update(**kwargs)
		self._str = fmt.format(**kwargs)
	
	def __str__(self):
		return self._str

def error(fmt, partial=None, **kwargs):
	raise InvalidArgumentException(fmt, **kwargs)

def spCatch(handle, func, exc):
	try:
		handle(func())
	except InvalidArgumentException as e:
		if e.partial is not None:
			handle(e.partial)
		if exc is None or not isinstance(exc[1], InvalidArgumentException):
			return sys.exc_info()
	except Exception as e:
		if exc is None:
			return sys.exc_info()

	return exc

def spCaught(exc, name, partial):
	if exc is None:
		return
	elif isinstance(exc[1], InvalidArgumentException):
		exc[1]._str = '{name}: {msg}'.format(name=name, msg=exc[1]._str)
		exc[1].partial = partial
		raise exc[0], exc[1], exc[2]
	else:
		raise InvalidArgumentException(fmt='{name}: {msg}', name=name, msg=str(exc[1]), partial=partial)

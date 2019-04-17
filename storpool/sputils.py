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
""" Utility functions and constants for the StorPool API bindings. """

from __future__ import print_function

import os.path
import time

import six.moves


sec = 1.0
msec = 1.0e-3 * sec
usec = 1e-6 * sec

KB = 1024
MB = 1024 ** 2
GB = 1024 ** 3
TB = 1024 ** 4


def pr(x):
    """ Display a value and return it; useful for lambdas. """
    print(x)
    return x


def pathPollWait(path, shouldExist, isLink, pollTime, maxTime):
    """ Poll/listen for path to appear/disappear. """
    for i in six.moves.range(int(maxTime / pollTime)):
        pathExists = os.path.exists(path)
        if pathExists and isLink:
            assert os.path.islink(path)

        if pathExists == shouldExist:
            return True
        else:
            time.sleep(pollTime)
    else:
        return False

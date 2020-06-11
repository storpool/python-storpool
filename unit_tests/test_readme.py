#
# Copyright (c) 2019, 2020  StorPool.
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
""" Tests for the README file. """

import re
import sys

from storpool import spapi


RE_VERSION_HISTORY = re.compile(r'''
    .*? \n
    Version \s history \n
    =+ \n
    (?P<rest> .*)
''', re.X | re.M | re.S)

RE_SEMVER = re.compile(r'''
    .*? \n
    (?P<version>
        (?P<major> \d+ )
        \.
        (?P<minor> \d+ )
        \.
        (?P<patch> \d+ )
        (?:
            \.
            (?P<alpha> [A-Za-z0-9]+ )
        )?
    )
    \n
    (?P<rest> .* )
''', re.X | re.M | re.S)


def get_file_contents(fname, encoding='UTF-8'):
    """ Read the lines from a file. """
    if sys.version_info[0] < 3:
        with open(fname, mode='r') as infile:
            return infile.read().decode(encoding)

    with open(fname, mode='r', encoding=encoding) as infile:
        return infile.read()


def extract_version_numbers(fname, encoding='UTF-8'):
    """ Parse the list of versions in the README file. """
    full = get_file_contents(fname, encoding)
    minfo = RE_VERSION_HISTORY.match(full)
    assert minfo
    rest = minfo.group('rest')

    versions = []
    while True:
        mver = RE_SEMVER.match(rest)
        if not mver:
            break

        versions.append(mver.group('version'))
        rest = mver.group('rest')

    assert versions
    return versions


def test_version():
    """ Make sure the current version is in the README.rst file. """
    lines = extract_version_numbers('README.rst')
    assert lines[0] == spapi.VERSION

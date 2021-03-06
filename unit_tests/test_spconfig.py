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
""" Tests for the storpool.spconfig.SPConfig class. """

import collections
import itertools
import os

import mock
import pytest

from storpool import spconfig


ConfigData = collections.namedtuple('ConfigData', [
    'filename',
    'data',
])

CONFIG_DATA = (
    ConfigData(
        filename='/usr/lib/storpool/storpool-defaults.conf',
        data={'': {'a': '1'}},
    ),
    ConfigData(
        filename='/etc/storpool.conf',
        data={'beleriand': {'b': '2'}},
    ),
    ConfigData(
        filename='/etc/storpool.conf.d/local.conf',
        data={'': {'c': '3'}, 'beleriand': {'a': '4'}},
    ),
)

CONFIG_FILES = {
    item.filename: item.data for item in CONFIG_DATA
}

TEST_CONFIG_FILES = {
    "/etc/storpool.conf": True,
    "/etc/storpool-defaults.conf": False,
    "/etc/storpool.conf.d/.hidden.conf": False,
    "/etc/storpool.conf.d/local.conf": True,
    "/etc/storpool.conf.d/local.confx": False,
    "/etc/storpool.conf.d/server.conf.bak": False,
    "/etc/storpool.conf.d/storpool.conf": True,
    "/etc/storpool.conf.d/storpool.conf~": False,
    "/usr/lib/storpool/storpool.conf": False,
    "/usr/lib/storpool/storpool-defaults.conf": True,
}

TEST_CONFIG_FILES_LISTDIR = dict(
    (
        dirname,
        ["subdir", "another-subdir.conf"]
        + sorted(filename for _, filename in files)
    )
    for dirname, files in itertools.groupby(
        sorted(os.path.split(fname) for fname in TEST_CONFIG_FILES),
        lambda item: item[0],
    )
)


def fake_get_config_files(_cls):
    """ Simulate looking for the StorPool configuration files. """
    return [item.filename for item in CONFIG_DATA]


class FakeConfig(object):
    # pylint: disable=too-few-public-methods
    """ Simulate a confget.Config settings holder. """

    def __init__(self, varnames, filename='(invalid)'):
        """ Initialize a fake Config object: store the filename. """
        assert varnames == []
        assert filename in CONFIG_FILES
        self.filename = filename


class FakeINI(object):
    # pylint: disable=too-few-public-methods
    """ Simulate a confget.backend.ini.INIBackend reader. """

    def __init__(self, config):
        """ Initialize a fake INI reader: store the fake config object. """
        assert isinstance(config, FakeConfig)
        self.config = config

    def read_file(self):
        """ Simulate reading from the INI file. """
        return CONFIG_FILES[self.config.filename]


@mock.patch('storpool.spconfig.SPConfig.get_config_files',
            new=fake_get_config_files)
@mock.patch('confget.Config', new=FakeConfig)
@mock.patch('confget.BACKENDS', new={'ini': FakeINI})
def test_success():
    """ Test that a SPConfig object behaves almost like a dictionary. """
    cfg = spconfig.SPConfig(section='beleriand')

    assert cfg['b'] == '2'
    with pytest.raises(KeyError):
        assert cfg['d'] == 'we should never get here, right?'

    assert cfg.get('a', 42) == '4'
    assert cfg.get('d', 42) == 42

    assert dict(cfg.items()) == {'a': '4', 'b': '2', 'c': '3'}

    assert sorted(cfg.keys()) == ['a', 'b', 'c']

    assert sorted(cfg.iteritems()) == [('a', '4'), ('b', '2'), ('c', '3')]

    assert sorted(cfg.iterkeys()) == ['a', 'b', 'c']


def test_get_config_files():
    """Test that SPConfig.get_config_files() works properly."""

    dirs_checked = set()
    files_checked = set()

    def mock_listdir(dirname):
        """Mock os.listdir(), return our synthetic filesystem's contents."""
        return TEST_CONFIG_FILES_LISTDIR[dirname]

    def mock_is_dir(path):
        """Mock os.path.isdir(), check and record."""
        dirs_checked.add(path)
        return path in TEST_CONFIG_FILES_LISTDIR

    def mock_is_file(path):
        """Mock os.path.isfile(), check and record."""
        files_checked.add(path)
        return path in TEST_CONFIG_FILES

    with mock.patch("os.listdir", new=mock_listdir), mock.patch(
        "os.path.isdir", new=mock_is_dir
    ), mock.patch(
        "os.path.isfile", new=mock_is_file
    ):
        res = set(spconfig.SPConfig.get_config_files())

    assert dirs_checked == set(["/etc/storpool.conf.d"])
    assert files_checked == set(
        [
            "/etc/storpool.conf",
            "/etc/storpool.conf.d/local.conf",
            "/etc/storpool.conf.d/storpool.conf",
            "/etc/storpool.conf.d/another-subdir.conf",
            "/usr/lib/storpool/storpool-defaults.conf",
        ]
    )
    assert res == set(
        filename
        for filename, wanted in TEST_CONFIG_FILES.items()
        if wanted
    )

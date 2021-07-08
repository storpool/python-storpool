#
# Copyright (c) 2019 - 2021  StorPool.
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
import errno
import itertools
import os

import mock
import pytest

from storpool import spconfig


ConfigData = collections.namedtuple('ConfigData', [
    'filename',
    'exists',
    'data',
])

CONFIG_DATA = (
    ConfigData(
        filename='/etc/storpool.conf',
        exists=True,
        data={'beleriand': {'SP_CACHE_SIZE': '8192'}},
    ),
    ConfigData(
        filename='/etc/storpool.conf.d/local.conf',
        exists=True,
        data={'': {'c': '3'}, 'beleriand': {'a': '4'}},
    ),
    ConfigData(
        filename='/etc/storpool.conf.d/storpool.conf',
        exists=False,
        data={},
    ),
)

CONFIG_FILES = {
    item.filename: item for item in CONFIG_DATA
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


def fake_get_config_files(_cls, missing_ok=False):
    """ Simulate looking for the StorPool configuration files. """
    assert missing_ok is not None  # Make this do something...
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
        return CONFIG_FILES[self.config.filename].data


class FakeINICheck(object):
    # pylint: disable=too-few-public-methods
    """ Simulate a confget.backend.ini.INIBackend reader. """

    def __init__(self, config):
        """ Initialize a fake INI reader: store the fake config object. """
        assert isinstance(config, FakeConfig)
        self.config = config

    def read_file(self):
        """ Simulate reading from the INI file. """
        res = CONFIG_FILES[self.config.filename]
        if not res.exists:
            raise IOError(
                errno.ENOENT,
                "No such file or directory",
                self.config.filename,
            )

        return res.data


@mock.patch('storpool.spconfig.SPConfig.get_config_files',
            new=fake_get_config_files)
@mock.patch('confget.Config', new=FakeConfig)
@mock.patch('confget.BACKENDS', new={'ini': FakeINI})
def test_success():
    """ Test that a SPConfig object behaves almost like a dictionary. """
    cfg = spconfig.SPConfig(section='beleriand', missing_ok=True)

    assert cfg['SP_CACHE_SIZE'] == '8192'
    with pytest.raises(KeyError):
        assert cfg['d'] == 'we should never get here, right?'

    assert cfg.get('a', 42) == '4'
    assert cfg.get('d', 42) == 42

    assert dict(cfg.items()) == dict(
        set(
            item
            for item in spconfig.DEFAULTS.items()
            if item[0] != 'SP_CACHE_SIZE'
        )
        | set({'SP_CACHE_SIZE': '8192', 'a': '4', 'c': '3'}.items())
    )

    assert (
        sorted(set(cfg.keys()) - set(spconfig.DEFAULTS.keys()))
    ) == ['a', 'c']

    assert sorted(
        set(cfg.iteritems()) - set(spconfig.DEFAULTS.items())
    ) == [('SP_CACHE_SIZE', '8192'), ('a', '4'), ('c', '3')]

    assert sorted(
        set(cfg.iterkeys()) - set(spconfig.DEFAULTS.keys())
    ) == ['a', 'c']

    cfg = spconfig.SPConfig(section='beleriand')

    assert cfg['SP_CACHE_SIZE'] == '8192'
    with pytest.raises(KeyError):
        assert cfg['d'] == 'we should never get here, right?'

    assert cfg.get('a', 42) == '4'
    assert cfg.get('d', 42) == 42

    assert dict(cfg.items()) == dict(
        set(
            item
            for item in spconfig.DEFAULTS.items()
            if item[0] != 'SP_CACHE_SIZE'
        )
        | set({'SP_CACHE_SIZE': '8192', 'a': '4', 'c': '3'}.items())
    )

    assert (
        sorted(set(cfg.keys()) - set(spconfig.DEFAULTS.keys()))
    ) == ['a', 'c']

    assert sorted(
        set(cfg.iteritems()) - set(spconfig.DEFAULTS.items())
    ) == [('SP_CACHE_SIZE', '8192'), ('a', '4'), ('c', '3')]

    assert sorted(
        set(cfg.iterkeys()) - set(spconfig.DEFAULTS.keys())
    ) == ['a', 'c']


@mock.patch('storpool.spconfig.SPConfig.get_config_files',
            new=fake_get_config_files)
@mock.patch('confget.Config', new=FakeConfig)
@mock.patch('confget.BACKENDS', new={'ini': FakeINICheck})
def test_file_not_found():
    """ Test that a SPConfig object behaves almost like a dictionary. """
    with pytest.raises(spconfig.SPConfigException) as err:
        spconfig.SPConfig(section='beleriand', missing_ok=True)

    assert "/etc/storpool.conf.d/storpool.conf" in str(err.value)


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
        res = set(spconfig.SPConfig.get_config_files(missing_ok=True))

    assert dirs_checked == set(["/etc/storpool.conf.d"])
    assert files_checked == set(
        [
            "/etc/storpool.conf",
            "/etc/storpool.conf.d/local.conf",
            "/etc/storpool.conf.d/storpool.conf",
            "/etc/storpool.conf.d/another-subdir.conf",
        ]
    )
    assert res == set(
        filename
        for filename, wanted in TEST_CONFIG_FILES.items()
        if wanted
    )

    dirs_checked.clear()
    files_checked.clear()

    with mock.patch("os.listdir", new=mock_listdir), mock.patch(
        "os.path.isdir", new=mock_is_dir
    ), mock.patch(
        "os.path.isfile", new=mock_is_file
    ):
        res = set(spconfig.SPConfig.get_config_files())

    assert dirs_checked == set(["/etc/storpool.conf.d"])
    assert not files_checked
    assert res == set(
        filename
        for filename, wanted in TEST_CONFIG_FILES.items()
        if wanted
    ) | set(["/etc/storpool.conf.d/another-subdir.conf"])

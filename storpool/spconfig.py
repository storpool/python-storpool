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
""" StorPool configuration file parser. """


import os
import platform

import confget


class SPConfigException(Exception):
    """ An error that occurred during the StorPool configuration parsing. """


class SPConfig(object):
    """ A representation of the StorPool configuration settings.

    When constructed, an object of this class will look for the various
    StorPool configuration files, parse them, and store the obtained
    variables and values into its internal dictionary.
    The object may later be accessed as a dictionary. """

    PATH_DEFAULTS = '/usr/lib/storpool/storpool-defaults.conf'
    PATH_CONFIG = '/etc/storpool.conf'
    PATH_CONFIG_DIR = '/etc/storpool.conf.d'

    def __init__(self, section=None):
        self._dict = dict()
        self._section = section
        self.run_confget()

    @classmethod
    def get_config_files(cls):
        """ Return the StorPool configuration files present on the system. """
        to_check = [cls.PATH_DEFAULTS, cls.PATH_CONFIG]
        if os.path.isdir(cls.PATH_CONFIG_DIR):
            to_check.extend([
                os.path.join(cls.PATH_CONFIG_DIR, fname)
                for fname in sorted(os.listdir(cls.PATH_CONFIG_DIR))
            ])
        return [path for path in to_check if os.path.isfile(path)]

    def run_confget(self):
        """ Parse the StorPool configuration files by ourselves. """
        if self._section is not None:
            section = self._section
        else:
            section = platform.node()
        sections = ['', section]
        ini = confget.BACKENDS['ini']
        res = {}

        for fname in self.get_config_files():
            try:
                cfg = confget.Config([], filename=fname)
                raw = ini(cfg).read_file()
            except Exception as exc:
                raise SPConfigException(
                    'Could not parse the {fname} StorPool configuration '
                    'file: {exc}'
                    .format(fname=fname, exc=exc))

            for section in sections:
                res.update(raw.get(section, {}))

        self._dict = res

    def __getitem__(self, key):
        return self._dict[key]

    def get(self, key, defval):
        """ Return value of the specified configuration variable. """
        return self._dict.get(key, defval)

    def __iter__(self):
        return iter(self._dict)

    def items(self):
        """ Return a list of the configuration var/value pairs. """
        return self._dict.items()

    def keys(self):
        """ Return a list of the configuration variable names. """
        return self._dict.keys()

    def iteritems(self):
        """ Return an iterator over the configuration var/value pairs. """
        if hasattr(self._dict, 'iteritems'):
            return self._dict.iteritems()  # pylint: disable=no-member
        return iter(self._dict.items())

    def iterkeys(self):
        """ Return an iterator over the configuration variable names. """
        if hasattr(self._dict, 'iterkeys'):
            return self._dict.iterkeys()  # pylint: disable=no-member
        return iter(self._dict.keys())

    @classmethod
    def get_all_sections(cls):
        """ Return all the section names in the StorPool config files. """
        ini = confget.BACKENDS['ini']
        sections = set()

        for fname in cls.get_config_files():
            cfg = confget.Config([], filename=fname)
            try:
                raw = ini(cfg).read_file()
            except Exception as exc:
                raise SPConfigException(
                    'Could not parse the {fname} StorPool configuration '
                    'file: {exc}'
                    .format(fname=fname, exc=exc))

            sections.update([key for key in raw if key])

        return sorted(sections)

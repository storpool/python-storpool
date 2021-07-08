#
# Copyright (c) 2014 - 2021  StorPool.
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


DEFAULTS = {
    "SP_ABRTSYNC_REMOTE_ADDRESSES":
        "reports.storpool.com,reports1.storpool.com,reports2.storpool.com",
    "SP_ABRTSYNC_REMOTE_PORTS": "2266",
    "SP_DELETE_REPORTS": "1",
    "SP_WORKDIR": "/var/run/storpool",
    "SP_REPORTDIR": "/var/spool/storpool",
    "SP_REPORTS_FREE_SPACE_LIMIT": "0",
    "SP_RESTART_ON_CRASH": "1800",
    "SP_API_HTTP_HOST": "127.0.0.1",
    "SP_API_HTTP_PORT": "81",
    "SP_GUI_HTTP_HOST": "",
    "SP_GUI_HTTP_PORT": "443",
    "SP_CACHE_SIZE": "4096",
    "SP_BEACON_CGROUPS":
        "-g cpuset:storpool.slice/beacon -g memory:storpool.slice/common",
    "SP_BLOCK_CGROUPS":
        "-g cpuset:storpool.slice/block -g memory:storpool.slice/common",
    "SP_BRIDGE_CGROUPS":
        "-g cpuset:storpool.slice/bridge -g memory:storpool.slice/alloc",
    "SP_ISCSI_CGROUPS":
        "-g cpuset:storpool.slice/iscsi -g memory:storpool.slice/alloc",
    "SP_MGMT_CGROUPS":
        "-g cpuset:storpool.slice/mgmt -g memory:storpool.slice/alloc",
    "SP_RDMA_CGROUPS":
        "-g cpuset:storpool.slice/rdma -g memory:storpool.slice/common",
    "SP_SERVER_CGROUPS":
        "-g cpuset:storpool.slice/server -g memory:storpool.slice/common",
    "SP_SERVER1_CGROUPS":
        "-g cpuset:storpool.slice/server_1 -g memory:storpool.slice/common",
    "SP_SERVER2_CGROUPS":
        "-g cpuset:storpool.slice/server_2 -g memory:storpool.slice/common",
    "SP_SERVER3_CGROUPS":
        "-g cpuset:storpool.slice/server_3 -g memory:storpool.slice/common",
    "SP_SERVER4_CGROUPS":
        "-g cpuset:storpool.slice/server_4 -g memory:storpool.slice/common",
    "SP_SERVER5_CGROUPS":
        "-g cpuset:storpool.slice/server_5 -g memory:storpool.slice/common",
    "SP_SERVER6_CGROUPS":
        "-g cpuset:storpool.slice/server_6 -g memory:storpool.slice/common",
    "SP_NVMED_CGROUPS":
        "-g cpuset:storpool.slice/beacon -g memory:storpool.slice/common",
    "SP_CONTROLLER_CGROUPS": "-g cpuset:system.slice -g memory:system.slice",
    "SP_STAT_CGROUPS": "-g cpuset:system.slice -g memory:system.slice",
    "SP_ABRTSYNC_CGROUPS": "-g cpuset:system.slice -g memory:system.slice",
    "SP_KUBCSI_CGROUPS": "-g cpuset:system.slice -g memory:system.slice",
    "SP_USE_CGROUPS": "1",
    "SP_CPU_DMA_LATENCY": "5",
    "SP_DEREGISTER_TIMEOUT_SECONDS": "60",
    "SP_NORMAL_RECOVERY_PARALLEL_REQUESTS_PER_DISK": "1",
    "SP_REMOTE_RECOVERY_PARALLEL_REQUESTS_PER_DISK": "2",
    "SP_IFACE1_ETHTOOLOPTS_TEMPLATE": (
        "__ETHTOOL__ -A __IFACE__ autoneg off tx off rx on ; "
        "__ETHTOOL__ -C __IFACE__ adaptive-rx off adaptive-tx off "
        "rx-usecs 5 ; "
        "__ETHTOOL__ -G __IFACE__ rx 4096 tx 512"
    ),
    "SP_IFACE2_ETHTOOLOPTS_TEMPLATE": (
        "__ETHTOOL__ -A __IFACE__ autoneg off tx off rx on ; "
        "__ETHTOOL__ -C __IFACE__ adaptive-rx off adaptive-tx off "
        "rx-usecs 5 ; "
        "__ETHTOOL__ -G __IFACE__ rx 4096 tx 512"
    ),
    "SP_PREFERRED_PORT": "0",
    "SP_NVME_PCI_DRIVER": "storpool_pci",
}


class SPConfigException(Exception):
    """ An error that occurred during the StorPool configuration parsing. """


class SPConfig(object):
    """ A representation of the StorPool configuration settings.

    When constructed, an object of this class will look for the various
    StorPool configuration files, parse them, and store the obtained
    variables and values into its internal dictionary.
    The object may later be accessed as a dictionary. """

    PATH_CONFIG = '/etc/storpool.conf'
    PATH_CONFIG_DIR = '/etc/storpool.conf.d'

    def __init__(self, section=None, missing_ok=False):
        self._dict = dict()
        self._section = section
        self.run_confget(missing_ok=missing_ok)

    @classmethod
    def get_config_files(cls, missing_ok=False):
        """ Return the StorPool configuration files present on the system. """
        to_check = [cls.PATH_CONFIG]
        if os.path.isdir(cls.PATH_CONFIG_DIR):
            to_check.extend([
                os.path.join(cls.PATH_CONFIG_DIR, fname)
                for fname in sorted(os.listdir(cls.PATH_CONFIG_DIR))
                if fname.endswith(".conf") and not fname.startswith(".")
            ])

        if not missing_ok:
            return to_check
        return [path for path in to_check if os.path.isfile(path)]

    def run_confget(self, missing_ok=False):
        """ Parse the StorPool configuration files by ourselves. """
        if self._section is not None:
            section = self._section
        else:
            section = platform.node()
        sections = ['', section]
        ini = confget.BACKENDS['ini']
        res = dict(DEFAULTS)

        for fname in self.get_config_files(missing_ok=missing_ok):
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

    def get(self, key, defval=None):
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

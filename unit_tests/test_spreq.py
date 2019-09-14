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
""" Tests for the storpool.spreq classes. """

import collections
import unittest

import ddt
import mock
import pytest

from storpool import spreq
from storpool import sptypes


STATUS_JSON = sptypes.ClusterStatus(
    clusterStatus='running',
    mgmt={
        1: sptypes.Mgmt(
            id=1,
            nodeId=11,
            version='18.01.15.3cff5d7',
            startTime=17000038,
            status='running',
            prio=0,
            active=False,
        ),
        2: sptypes.Mgmt(
            id=2,
            nodeId=13,
            version='18.02.17.dd18d43',
            startTime=None,
            status='down',
            prio=1,
            active=False,
        ),
        3: sptypes.Mgmt(
            id=3,
            nodeId=3,
            version='18.03',
            startTime=37000038,
            status='running',
            prio=42,
            active=True,
        ),
    },
    clients={},
    servers={
        1: sptypes.Server(
            id=1,
            nodeId=1,
            version='18.02',
            startTime=1,
            status='booting',
            missingDisks=[301, 411],
            pendingDisks=[105],
        ),
        2: sptypes.Server(
            id=2,
            nodeId=2,
            version='18.02',
            startTime=10,
            status='running',
            missingDisks=[],
            pendingDisks=[],
        ),
    },
    bridges={},
)

STATUS_PYTHON = {
    'clusterStatus': 'running',
    'mgmt': {
        1: {
            'id': 1,
            'nodeId': 11,
            'version': '18.01.15.3cff5d7',
            'startTime': 17000038,
            'status': 'running',
            'prio': 0,
            'active': False,
        },
        2: {
            'id': 2,
            'nodeId': 13,
            'version': '18.02.17.dd18d43',
            'startTime': None,
            'status': 'down',
            'prio': 1,
            'active': False,
        },
        3: {
            'id': 3,
            'nodeId': 3,
            'version': '18.03',
            'startTime': 37000038,
            'status': 'running',
            'prio': 42,
            'active': True,
        },
    },
    'clients': {},
    'servers': {
        1: {
            'id': 1,
            'nodeId': 1,
            'version': '18.02',
            'startTime': 1,
            'status': 'booting',
            'missingDisks': [301, 411],
            'pendingDisks': [105],
        },
        2: {
            'id': 2,
            'nodeId': 2,
            'version': '18.02',
            'startTime': 10,
            'status': 'running',
            'missingDisks': [],
            'pendingDisks': [],
        },
    },
    'bridges': {},
}

ArgsType = collections.namedtuple('ArgType', [
    'args',
    'json',
    'multicluster',
    'is_multicluster',
    'post',
    'query',
])

GET_API_METHOD_TESTS = [
    (
        'servicesList',
        ArgsType(
            args=[],
            json=None,
            multicluster=False,
            is_multicluster=False,
            post=False,
            query='ServicesList',
        ),
    ),
    (
        None,
        ArgsType(
            args=[1],
            json=None,
            multicluster=False,
            is_multicluster=False,
            post=False,
            query='ServicesList',
        ),
    ),
    (
        None,
        ArgsType(
            args=[1],
            json=None,
            multicluster=False,
            is_multicluster=False,
            post=True,
            query='ServicesList',
        ),
    ),
    (
        'volumeDescribe',
        ArgsType(
            args=['beleriand'],
            json=None,
            multicluster=False,
            is_multicluster=True,
            post=False,
            query='VolumeDescribe',
        ),
    ),
    (
        'volumeBalancerGetStatus',
        ArgsType(
            args=[],
            json=None,
            multicluster=False,
            is_multicluster=False,
            post=False,
            query='VolumeBalancerStatus',
        ),
    ),
    (
        'volumeBalancerSetStatus',
        ArgsType(
            args=[],
            json={'cmd': 'stop'},
            multicluster=False,
            is_multicluster=False,
            post=True,
            query='VolumeBalancerStatus',
        ),
    ),
    (
        'volumeDelete',
        ArgsType(
            args=['no-name'],
            json=None,
            multicluster=False,
            is_multicluster=True,
            post=True,
            query='VolumeDelete',
        ),
    ),
    (
        'volumeDelete',
        ArgsType(
            args=['no-name'],
            json=None,
            multicluster=True,
            is_multicluster=True,
            post=True,
            query='VolumeDelete',
        ),
    ),
]


@ddt.ddt
class TestRequests(unittest.TestCase):
    # pylint: disable=no-self-use
    """ Simple tests for the command-line request tool classes. """

    def test_deep_to_json(self):
        """ Test the JsonObject-to-Python conversion method. """
        conv = spreq.deep_to_json(STATUS_JSON)
        assert conv == STATUS_PYTHON

        twice = spreq.deep_to_json(conv)
        assert twice == conv

    @mock.patch('storpool.spconfig.SPConfig', spec=['__call__'])
    @mock.patch('storpool.spapi.Api', spec=['__call__'])
    def test_from_config_with_overrides(self, sp_api, sp_cfg):
        """ Test environment configuration overrides. """
        sp_cfg.return_value = {
            'SP_API_HTTP_HOST': 'bad.hostname',
            'SP_API_HTTP_PORT': 8000,
            'SP_AUTH_TOKEN': 'good token',
            'SP_SOMETHING': 'else',
        }
        overrides = {
            'SP_API_HTTP_HOST': 'good.hostname',
            'SP_API_HTTP_PORT': 443,
            'SP_ANOTHER': 'thing',
        }

        def construct_api(host, port, auth, timeout=616, yet='another thing'):
            """ Make sure the spapi.Api object is constructed correctly. """
            assert host == 'good.hostname'
            assert port == 443
            assert auth == 'good token'
            assert timeout == 42
            assert yet == 'another thing'
            return 'ok'

        sp_api.side_effect = construct_api
        with mock.patch('os.environ.get', spec=['__call__'],
                        new=overrides.get):
            api = spreq.from_config_with_overrides(timeout=42)

        assert api == 'ok'

    @mock.patch('storpool.spconfig.SPConfig', spec=['__call__'])
    @ddt.data(*GET_API_METHOD_TESTS)
    @ddt.unpack
    def test_get_api_method(self, name, args, sp_cfg):
        """ Make sure that API methods are looked up correctly. """
        sp_cfg.return_value = {
            'SP_API_HTTP_HOST': 'hostname',
            'SP_API_HTTP_PORT': 8000,
            'SP_AUTH_TOKEN': 'token',
        }

        with mock.patch('os.environ.get', spec=['__call__'],
                        new=lambda _var, _default: None):
            if name is None:
                with pytest.raises(SystemExit):
                    spreq.get_api_method(args)
                return

            meth = spreq.get_api_method(args)

        assert meth.__name__ == name

    @mock.patch('storpool.spconfig.SPConfig', spec=['__call__'])
    @ddt.data(*GET_API_METHOD_TESTS)
    @ddt.unpack
    def test_multicluster(self, name, args, sp_cfg):
        """ Make sure that API methods are looked up correctly. """
        sp_cfg.return_value = {
            'SP_API_HTTP_HOST': 'hostname',
            'SP_API_HTTP_PORT': 8000,
            'SP_AUTH_TOKEN': 'token',
        }

        with mock.patch('os.environ.get', spec=['__call__'],
                        new=lambda _var, _default: None):
            if name is None:
                with pytest.raises(SystemExit):
                    spreq.get_api_method(args)
                return

            meth = spreq.get_api_method(args)

        assert meth.__name__ == name
        assert ('/MultiCluster/' in meth.spDoc.path) == args.is_multicluster

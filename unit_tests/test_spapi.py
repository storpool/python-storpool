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
""" Tests for the storpool.spapi classes. """

import collections
import errno
import itertools
import json
import re
import socket
import types
import unittest

import ddt
import mock
import pytest

from six.moves import http_client

from storpool import spapi
from storpool import spcatch
from storpool import sptype
from storpool import sptypes


RE_API_CASE = re.compile('''
    ^
    [a-z]
    [a-zA-Z]*
    [a-z]
    $
''', re.X)

ApiArgTestCase = collections.namedtuple('ApiArgTestCase', [
    'sptype',
    'valid',
    'invalid',
])

API_ARG_DATA = [
    ApiArgTestCase(
        sptype=spapi.DiskId,
        valid=[1, 616, 3128],
        invalid=['meow', -3, 8086, unittest.TestCase],
    ),
    ApiArgTestCase(
        sptype=spapi.ServerId,
        valid=[1, 63, 4095, 32767],
        invalid=[-1, 0, 32768],
    ),
    ApiArgTestCase(
        sptype=spapi.ClientId,
        valid=[1, 63, 4095],
        invalid=[-1, 0, 4096, 32768],
    ),
    ApiArgTestCase(
        sptype=spapi.VolumeName,
        valid=['Volume', '0.-volume', 'v0l.ume', '_0', '#:'],
        invalid=['Volu"me', '*vol', 'volume#', 'volume*'],
    ),
    ApiArgTestCase(
        sptype=spapi.SnapshotName,
        valid=['Volume', '0.-volume', 'v0l.ume', '_0', '*:'],
        invalid=['Volu"me', '#vol', 'volume#', 'volume*'],
    ),
    ApiArgTestCase(
        sptype=spapi.VolumeTemplateName,
        valid=['Volume', 'v0l_ume', '_0'],
        invalid=[
            'Volu"me', '#vol', 'volume#', 'volume*',
            '0.-volume', 'v0l.ume', '#:', '*:', '#_', '*_',
        ],
    ),
    ApiArgTestCase(
        sptype=spapi.PlacementGroupName,
        valid=['Volume', 'v0l_ume', '_0'],
        invalid=[
            'Volu"me', '#vol', 'volume#', 'volume*',
            '0.-volume', 'v0l.ume', '#:', '*:', '#_', '*_',
        ],
    ),
    ApiArgTestCase(
        sptype=spapi.GlobalVolumeId,
        valid=['a.a.a', 'f00.b4r.quuxquuxqu8x'],
        invalid=['a', 'a.a', 'a.a.a.a', '.a.a', 'a.a.', 'a.a.a!', 'a.a.a a'],
    ),
]

API_ARG_DATA_EXPLODED = itertools.chain(
    # The valid values
    itertools.chain(*(
        [
            ApiArgTestCase(
                sptype=type_case.sptype,
                valid=[value],
                invalid=[],
            ) for value in type_case.valid
        ] for type_case in API_ARG_DATA
    )),

    # The invalid values
    itertools.chain(*(
        [
            ApiArgTestCase(
                sptype=type_case.sptype,
                valid=[],
                invalid=[value],
            ) for value in type_case.invalid
        ] for type_case in API_ARG_DATA
    )),
)

ApiMethodTestCase = collections.namedtuple('ApiMethodTestCase', [
    'method',
    'multicluster',
    'query',
    'args',
    'json',
    'returns',
    'params',
    'kwparams',
    'return_value',
    'call_query',
    'call_json',
])

ApiErrorTestCase = collections.namedtuple('ApiErrorTestCase', [
    'method',
    'error',
    'transient',
    'result',
    'message',
])


@ddt.ddt
class TestAPI(unittest.TestCase):
    # pylint: disable=no-self-use
    """ Simple tests for the actual API call dispatcher. """

    @ddt.data(*API_ARG_DATA_EXPLODED)
    def test_api_arg(self, case):
        # pylint: disable=protected-access
        """ Make sure _API_ARG defines the correct class handler. """
        assert isinstance(case.sptype, spapi._API_ARG)
        assert RE_API_CASE.match(case.sptype._name)

        for value in case.valid:
            nval = case.sptype._type.handleVal(value)
            assert nval is not None

        for value in case.invalid:
            with pytest.raises(Exception) as err:
                case.sptype._type.handleVal(value)
            assert issubclass(err.type, spcatch.InvalidArgumentError) or \
                issubclass(err.type, TypeError)

    @ddt.data(
        ApiMethodTestCase(
            method='GET',
            multicluster=False,
            query='Query/{name}',
            args=[('name', str)],
            json=None,
            returns=int,
            params=['test'],
            kwparams={},
            return_value=616,
            call_query='Query/test',
            call_json=None,
        ),
        ApiMethodTestCase(
            method='GET',
            multicluster=False,
            query='Query/{name}',
            args=[('name', str)],
            json=None,
            returns=int,
            params=['test'],
            kwparams={'clusterName': 'elsewhere'},
            return_value=616,
            call_query='Query/test',
            call_json=None,
        ),
        ApiMethodTestCase(
            method='GET',
            multicluster=False,
            query='Query/{name}',
            args=[('name', str)],
            json={sptypes.SnapshotName: sptypes.ServerId},
            returns=int,
            params=['test', {'shibboleth': 616}],
            kwparams={'clusterName': 'elsewhere'},
            return_value=616,
            call_query='Query/test',
            call_json={'shibboleth': 616},
        ),
        ApiMethodTestCase(
            method='POST',
            multicluster=False,
            query='AnotherQuery/{id}',
            args=[('id', int)],
            json={sptypes.DiskId: sptypes.ServerId},
            returns=int,
            params=[42, {616: 6}],
            kwparams={},
            return_value=616,
            call_query='AnotherQuery/42',
            call_json={616: 6},
        ),
        ApiMethodTestCase(
            method='POST',
            multicluster=False,
            query='AnotherQuery/{id}',
            args=[('id', int)],
            json={sptypes.DiskId: sptypes.ServerId},
            returns=int,
            params=[42, {616: 6}],
            kwparams={'clusterName': 'remote'},
            return_value=616,
            call_query='AnotherQuery/42',
            call_json={616: 6},
        ),
        ApiMethodTestCase(
            method='POST',
            multicluster=True,
            query='AnotherQuery/{id}',
            args=[('id', int)],
            json={sptypes.DiskId: sptypes.ServerId},
            returns=int,
            params=[42, {616: 6}],
            kwparams={},
            return_value=616,
            call_query='AnotherQuery/42',
            call_json={616: 6},
        ),
        ApiMethodTestCase(
            method='POST',
            multicluster=True,
            query='AnotherQuery/{id}',
            args=[('id', int)],
            json={sptypes.DiskId: sptypes.ServerId},
            returns=int,
            params=[42, {616: 6}],
            kwparams={'clusterName': 'backup'},
            return_value=616,
            call_query='AnotherQuery/42',
            call_json={616: 6},
        ),
    )
    def test_api_method(self, data):
        """ Make sure _API_METHOD.compile() returns a sensible function. """
        # pylint: disable=protected-access
        args = [spapi._API_ARG(aname, atype) for aname, atype in data.args]
        meth = spapi._API_METHOD(
            data.method, data.multicluster, data.query, args,
            data.json, data.returns)
        assert meth.method == data.method
        multi = "MultiCluster/" if data.multicluster else ""
        assert meth.path == '/ctrl/1.0/' + multi + data.query
        assert meth.args == args
        if data.json is None:
            assert meth.json is None
        else:
            assert isinstance(meth.json, sptype.SpType)
        assert meth.types == {}
        assert getattr(meth, 'spDoc', None) is None

        meth.doc('QueryQuery', 'QueryDesc')
        assert getattr(meth, 'spDoc', None) is not None

        func = meth.compile()
        assert isinstance(func, types.FunctionType)

        mock_api = mock.Mock(spec=['__call__'])
        mock_api.return_value = data.return_value

        res = func(mock_api, *data.params, **data.kwparams)
        assert res == data.return_value
        mock_api.assert_called_once_with(
            data.method, data.multicluster, data.call_query, data.call_json,
            clusterName=data.kwparams.get("clusterName"))

    @mock.patch('six.moves.http_client.HTTPConnection', spec=['__call__'])
    def test_api_disks_list(self, http):
        """ Test the way the Api class sends out queries. """
        api = spapi.Api(host='1.2.3.4', port=8080, auth='123')
        assert http.call_count == 0

        resp = mock.Mock(spec=['status', 'read'])
        resp.status = http_client.OK
        resp.read.return_value = '''
{
    "data": {
        "616": {
            "generationLeft": 1,
            "id": 616,
            "serverId": 6,
            "ssd": false,
            "model": "whee",
            "serial": "none",
            "description": "",
            "softEject": "off"
        },
        "676": {
            "generationLeft": -1,
            "id": 676,
            "serverId": 6,

            "agAllocated" : 5,
            "agCount" : 18,
            "agFree" : 13,
            "agFreeNotTrimmed" : 0,
            "agFreeing" : 0,
            "agFull" : 0,
            "agMaxSizeFull" : 0,
            "agMaxSizePartial" : 1,
            "agPartial" : 0,
            "aggregateScore" : {
               "entries" : 0,
               "space" : 0,
               "total" : 0
            },
            "description" : "",
            "device" : "/dev/sdb",
            "empty" : false,
            "entriesAllocated" : 10,
            "entriesCount" : 30000,
            "entriesFree" : 29990,
            "isWbc" : false,
            "journaled" : false,
            "lastScrubCompleted" : 1553071249,
            "model" : "QEMU_HARDDISK",
            "noFlush" : false,
            "noFua" : false,
            "noTrim" : false,
            "objectsAllocated" : 17,
            "objectsCount" : 30000,
            "objectsFree" : 29983,
            "objectsOnDiskSize" : 184320,
            "pendingErrorRecoveries" : 0,
            "scrubbedBytes" : 0,
            "scrubbing" : false,
            "scrubbingBW" : 0,
            "scrubbingFinishAfter" : 0,
            "scrubbingPaused" : false,
            "scrubbingPausedFor" : 0,
            "scrubbingStartedBefore" : 0,
            "sectorsCount" : 20971520,
            "serial" : "n/a",
            "softEject" : "off",
            "ssd" : false,
            "totalErrorsDetected" : 0,
            "wbc" : null
        }
    }
}
'''

        conn = mock.Mock(spec=['request', 'getresponse', 'close'])
        conn.getresponse.return_value = resp

        http.return_value = conn

        res = api.disksList()  # pylint: disable=not-callable

        http.assert_called_once_with('1.2.3.4', 8080, timeout=300)
        conn.request.assert_called_once_with(
            'GET', '/ctrl/1.0/DisksList', None,
            {'Authorization': 'Storpool v1:123'}
        )
        conn.getresponse.assert_called_once_with()

        assert isinstance(res, dict)
        assert sorted(res.keys()) == [616, 676]

        assert isinstance(res[616], sptypes.DownDiskSummary)
        assert res[616].to_json()['id'] == 616
        assert not res[616].up
        assert not hasattr(res[616], 'agCount')
        assert 'aggregateScore' not in res[616].to_json()

        assert isinstance(res[676], sptypes.UpDiskSummary)
        assert res[676].id == 676
        assert res[676].up
        assert res[676].to_json()['serverId'] == 6
        assert res[676].agCount == 18
        assert isinstance(res[676].aggregateScore, sptypes.DiskAggregateScores)
        assert isinstance(res[676].aggregateScore.to_json()['entries'], int)

    @mock.patch('six.moves.http_client.HTTPConnection', spec=['__call__'])
    def test_api_placement_group_update(self, http):
        """ Test the way the Api class sends out queries. """
        api = spapi.Api(host='4.3.2.1', port=6502, auth='456')
        assert http.call_count == 0

        resp = mock.Mock(spec=['status', 'read'])
        resp.status = http_client.OK
        resp.read.return_value = '''
{
   "data" : {
      "generation" : 10436,
      "ok" : true
   },
   "generation" : 10436
}
'''

        conn = mock.Mock(spec=['request', 'getresponse', 'close'])
        conn.getresponse.return_value = resp

        http.return_value = conn

        res = api.placementGroupUpdate(  # pylint: disable=not-callable
            'weirdgroup',
            json={'addDisks': set([101])}
        )

        http.assert_called_once_with('4.3.2.1', 6502, timeout=300)
        calls = conn.request.call_args_list
        assert len(calls) == 1
        assert len(calls[0][0]) == 4
        assert calls[0][0][0] == 'POST'
        assert calls[0][0][1] == '/ctrl/1.0/PlacementGroupUpdate/weirdgroup'
        assert calls[0][0][3] == {'Authorization': 'Storpool v1:456'}

        body = json.loads(calls[0][0][2])
        assert body == {'addDisks': [101], 'rmDisks': []}

        assert isinstance(res, spapi.ApiOk)

    @mock.patch('six.moves.http_client.HTTPConnection', spec=['__call__'])
    def test_api_iscsi_sessions_info(self, http):
        """ Test the way the Api class sends out queries. """
        api = spapi.Api(host='4.3.2.1', port=6502, auth='456')
        assert http.call_count == 0

        resp = mock.Mock(spec=['status', 'read'])
        resp.status = http_client.OK
        resp.read.return_value = '''
{
   "data" : {
      "sessions" : [
         {
            "status": "timeout",
            "controllerId": 1
         }
      ]
   },
   "generation" : 10436
}
'''

        conn = mock.Mock(spec=['request', 'getresponse', 'close'])
        conn.getresponse.return_value = resp

        http.return_value = conn

        res = api.iSCSISessionsInfo()  # pylint: disable=not-callable

        http.assert_called_once_with('4.3.2.1', 6502, timeout=300)
        calls = conn.request.call_args_list
        assert len(calls) == 1
        assert list(calls[0][0]) == [
            'GET',
            '/ctrl/1.0/iSCSISessionsInfo',
            None,
            {'Authorization': 'Storpool v1:456'},
        ]

        assert isinstance(res, sptypes.iSCSISessionsInfo)
        assert len(res.sessions) == 1
        assert isinstance(res.sessions[0], sptypes.iSCSISessionInfo)
        assert spapi.clear_none(res.sessions[0].to_json()) == {
            "status": "timeout",
            "controllerId": 1,
        }

        res = api.iSCSISessionsInfo(  # pylint: disable=not-callable
            json=sptypes.iSCSIControllersQuery(controllerIds=[42])
        )

        assert http.call_count == 2
        calls = conn.request.call_args_list
        assert len(calls) == 2
        assert list(calls[1][0]) == [
            'GET',
            (
                '/ctrl/1.0/iSCSISessionsInfo?json='
                '%7B%22controllerIds%22%3A%5B42%5D%7D'
            ),
            None,
            {'Authorization': 'Storpool v1:456'},
        ]

    def test_api_error(self):
        """ Test the way the Api class sends out queries. """
        resp = mock.Mock(spec=['status', 'read'])
        resp.status = http_client.OK
        resp.read.return_value = '''
{
    "error": {
        "name": "WeirdError",
        "descr": "A weird error occurred; for more information please reread"
    }
}
'''

        conn_called = []
        req_called = []
        get_resp_called = []

        # This seems a bit crazy; the goal here is to make sure that
        # HTTPConnection is mocked yet it has an __init__() method that
        # has the "source_address" named argument.
        #
        class MockHTTPConnection(object):
            """ Mock an HTTPConnection. """

            def __init__(self, host, port=None, strict=None, timeout=None,
                         source_address=None):
                # pylint: disable=too-many-arguments
                """ Mock an HTTPConnection() constructor. """
                assert host == "1.1.1.1"
                assert port == 8000
                assert strict is None
                assert timeout == 300
                assert source_address == ("2.3.4.5", 0)

                assert conn_called.count(1) == 0
                conn_called.append(1)

            def request(self, method, url, body=None, headers=None):
                """ Mock a request. """
                assert method == "GET"
                assert url == "/ctrl/1.0/DisksList"
                assert body is None
                assert headers == {'Authorization': 'Storpool v1:456'}

                assert req_called.count(1) == 0
                req_called.append(1)

            def close(self):
                """ Mock a connection close, nothing to do. """

            def getresponse(self):
                """ Mock the retrieval of a response. """
                assert req_called.count(1) == 1

                assert get_resp_called.count(1) == 0
                get_resp_called.append(1)

                return resp

        with pytest.raises(spapi.ApiError) as err:
            with mock.patch('six.moves.http_client.HTTPConnection',
                            new=MockHTTPConnection):
                api = spapi.Api(host='1.1.1.1', port=8000, auth='456',
                                source='2.3.4.5')
                assert not conn_called
                assert not req_called
                assert not get_resp_called

                api.disksList()  # pylint: disable=not-callable

        assert conn_called == [1]
        assert req_called == [1]
        assert get_resp_called == [1]

        assert err.value.name == 'WeirdError'
        assert err.value.desc.endswith('please reread')

    @ddt.data(
        ApiErrorTestCase(
            method="init",
            error=socket.error(errno.ECONNREFUSED, "refused"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [],
                "response": [],
            },
            message="refused",
        ),
        ApiErrorTestCase(
            method="init",
            error=socket.error(errno.EBADF, "badfile"),
            transient=False,
            result={
                "conn": [1],
                "request": [],
                "response": [],
            },
            message="badfile",
        ),
        ApiErrorTestCase(
            method="init",
            error=http_client.CannotSendHeader("no reason"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [],
                "response": [],
            },
            message="no reason",
        ),

        ApiErrorTestCase(
            method="request",
            error=socket.error(errno.ECONNREFUSED, "refused"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [1, 1, 1, 1, 1, 1],
                "response": [],
            },
            message="refused",
        ),
        ApiErrorTestCase(
            method="request",
            error=socket.error(errno.EBADF, "badfile"),
            transient=False,
            result={
                "conn": [1],
                "request": [1],
                "response": [],
            },
            message="badfile",
        ),
        ApiErrorTestCase(
            method="request",
            error=http_client.BadStatusLine("this-line"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [1, 1, 1, 1, 1, 1],
                "response": [],
            },
            message="this-line",
        ),

        ApiErrorTestCase(
            method="response",
            error=socket.error(errno.ECONNREFUSED, "refused"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [1, 1, 1, 1, 1, 1],
                "response": [1, 1, 1, 1, 1, 1],
            },
            message="refused",
        ),
        ApiErrorTestCase(
            method="response",
            error=socket.error(errno.EBADF, "badfile"),
            transient=False,
            result={
                "conn": [1],
                "request": [1],
                "response": [1],
            },
            message="badfile",
        ),
        ApiErrorTestCase(
            method="response",
            error=http_client.CannotSendRequest("some reason"),
            transient=True,
            result={
                "conn": [1, 1, 1, 1, 1, 1],
                "request": [1, 1, 1, 1, 1, 1],
                "response": [1, 1, 1, 1, 1, 1],
            },
            message="some reason",
        ),
    )
    def test_api_network_error(self, data):
        """ Test the way the Api class sends out queries. """
        called = {"conn": [], "request": [], "response": []}

        def check_transient_calls(name):
            count = called[name].count(1)
            if data.transient:
                assert count <= 5
            else:
                assert count == 0

        # This seems a bit crazy; the goal here is to make sure that
        # HTTPConnection is mocked yet it has an __init__() method that
        # has the "source_address" named argument.
        #
        class MockHTTPConnection(object):
            """ Mock an HTTPConnection. """

            def __init__(self, host, port=None, strict=None, timeout=None,
                         source_address=None):
                # pylint: disable=too-many-arguments
                """ Mock an HTTPConnection() constructor. """
                assert host == "1.1.1.1"
                assert port == 8000
                assert strict is None
                assert timeout == 300
                assert source_address == ("2.3.4.5", 0)

                check_transient_calls("conn")
                called["conn"].append(1)

                if data.method == "init":
                    raise data.error

            def request(self, method, url, body=None, headers=None):
                """ Mock a request. """
                assert method == "GET"
                assert url == "/ctrl/1.0/DisksList"
                assert body is None
                assert headers == {'Authorization': 'Storpool v1:456'}

                check_transient_calls("request")
                called["request"].append(1)

                assert data.method in ("request", "response")
                if data.method == "request":
                    raise data.error

            def close(self):
                """ Mock a connection close, nothing to do. """

            def getresponse(self):
                """ Mock the retrieval of a response. """
                assert called["request"].count(1) > 0

                check_transient_calls("response")
                called["response"].append(1)

                assert data.method == "response"
                raise data.error

        with pytest.raises(type(data.error)) as err:
            with mock.patch('six.moves.http_client.HTTPConnection',
                            new=MockHTTPConnection):
                api = spapi.Api(host='1.1.1.1', port=8000, auth='456',
                                source='2.3.4.5', transientSleep=lambda _: 0)
                assert called == {"conn": [], "request": [], "response": []}
                api.disksList()  # pylint: disable=not-callable

        assert called == data.result

        if isinstance(err.value, socket.error):
            assert err.value.errno == data.error.errno
            assert data.message in err.value.strerror
        else:
            assert data.message == err.value.args[0]

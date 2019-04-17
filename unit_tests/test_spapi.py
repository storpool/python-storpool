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
""" Tests for the storpool.spapi classes. """

import collections
import itertools
import re
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
    'path',
    'args',
    'json',
    'returns',
    'params',
    'return_value',
    'call_path',
    'call_json',
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
            path='Query/{name}',
            args=[('name', str)],
            json=None,
            returns=int,
            params=['test'],
            return_value=616,
            call_path='/ctrl/1.0/Query/test',
            call_json=None,
        ),
        ApiMethodTestCase(
            method='POST',
            path='AnotherQuery/{id}',
            args=[('id', int)],
            json={sptypes.DiskId: sptypes.ServerId},
            returns=int,
            params=[42, {616: 6}],
            return_value=616,
            call_path='/ctrl/1.0/AnotherQuery/42',
            call_json={616: 6},
        ),
    )
    def test_api_method(self, data):
        """ Make sure _API_METHOD.compile() returns a sensible function. """
        # pylint: disable=protected-access
        args = [spapi._API_ARG(aname, atype) for aname, atype in data.args]
        meth = spapi._API_METHOD(data.method, data.path, args,
                                 data.json, data.returns)
        assert meth.method == data.method
        assert meth.path == '/ctrl/1.0/' + data.path
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

        res = func(mock_api, *data.params)
        assert res == data.return_value
        mock_api.assert_called_once_with(data.method, data.call_path,
                                         data.call_json)

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

        http.assert_called_once_with('1.2.3.4', 8080, 10)
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
    def test_api_error(self, http):
        """ Test the way the Api class sends out queries. """
        api = spapi.Api(host='1.1.1.1', port=8000, auth='456')
        assert http.call_count == 0

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

        conn = mock.Mock(spec=['request', 'getresponse', 'close'])
        conn.getresponse.return_value = resp

        http.return_value = conn

        with pytest.raises(spapi.ApiError) as err:
            api.disksList()  # pylint: disable=not-callable

        http.assert_called_once_with('1.1.1.1', 8000, 10)
        conn.request.assert_called_once_with(
            'GET', '/ctrl/1.0/DisksList', None,
            {'Authorization': 'Storpool v1:456'}
        )
        conn.getresponse.assert_called_once_with()

        assert err.value.name == 'WeirdError'
        assert err.value.desc.endswith('please reread')

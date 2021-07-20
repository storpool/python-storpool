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
""" Classes for accessing the StorPool API over an HTTP connection.

The Api class provides methods corresponding to the StorPool API calls.
The most common way to initialize it is to use the Api.fromConfig()
class method that will parse the StorPool configuration and set up
the connection parameters; see the apidoc.html reference documentation
for more information.
"""

import errno
import inspect
import socket as sock
import sys
import time as time

import six

from six.moves import http_client as http

from . import spjson as js
from . import sptypes as sp

from .spcatch import InvalidArgumentError
from .spconfig import SPConfig
from .sptype import JsonObject, spType, either, const, maybe, longType
from .sputils import msec, sec, pathPollWait
from .spdoc import ApiDoc, ApiCallDoc

if sys.version_info[0] < 3:
    import urllib as uquote
else:
    import urllib.parse as uquote


VERSION = '6.0.0'


SP_DEV_PATH = '/dev/storpool/'
SP_API_PREFIX = '/ctrl/1.0'


def _format_path(query, multiCluster, clusterName=None):
    """ Return the HTTP path to send an actual query to. """
    return "{pref}/{remote}{multi}{query}".format(
        pref=SP_API_PREFIX,
        remote="RemoteCommand/{name}/".format(name=clusterName) if clusterName is not None else "",
        multi="MultiCluster/" if multiCluster else "",
        query=query)


class _API_ARG(object):
    def __init__(self, name, validate):
        self._name = name
        self._type = spType(validate)

    def defstr(self):
        if self._type.spDoc.name == "Optional":
            return "{name}=None".format(name=self._name)
        else:
            return self._name


DiskId = _API_ARG('diskId', sp.DiskId)
ServerId = _API_ARG('serverId', sp.ServerId)
ClientId = _API_ARG('clientId', sp.ClientId)
VolumeName = _API_ARG('volumeName', sp.VolumeNameOrGlobalId)
SnapshotName = _API_ARG('snapshotName', sp.SnapshotNameOrGlobalId)
PlacementGroupName = _API_ARG('placementGroupName', sp.PlacementGroupName)
VolumeTemplateName = _API_ARG('templateName', sp.VolumeTemplateName)
GlobalVolumeId = _API_ARG('globalVolumeId', sp.GlobalVolumeId)


class _API_METHOD(object):
    def __init__(self, method, multiCluster, query, args, json, returns):
        self.method = method
        self.multiCluster = multiCluster
        self.query = query
        self.path = _format_path(query, multiCluster)
        self.args = args
        self.json = spType(json) if json is not None else None
        self.returns = spType(returns)
        self.types = {}

    def addType(self, name, desc):
        self.types.update({name: desc})

    def doc(self, name, desc):
        self.spDoc = ApiCallDoc(name, desc, self.method, self.query, self.path, dict((arg._name, arg._type.spDoc) for arg in self.args), self.json.spDoc if self.json else None, self.returns.spDoc)
        return self

    def compile(self):
        def commas(xs):
            return ", ".join(xs)

        def fmtEq(x):
            return "{x}={x}".format(x=x)

        method, query, args, json, returns = self.method, self.query, self.args, self.json, self.returns

        args = list(args)
        if json is not None:
            args.append(_API_ARG('json', json))

        ftext = 'def func(self, {args}clusterName=None):\n'.format(
            args=''.join(arg.defstr() + ", " for arg in args))
        for arg in args:
            ftext += '    {arg} = _validate_{arg}({arg})\n'.format(arg=arg._name)

        ftext += '    query = "{query}"'.format(query=query)
        if args:
            ftext += '.format({args})\n'.format(args=commas(fmtEq(arg._name) for arg in args))
        ftext += '\n'

        ftext += '    res = self("{method}", {multiCluster}, query, {json}, clusterName=clusterName)\n'.format(method=method, multiCluster=repr(self.multiCluster), json=None if json is None else 'json')
        ftext += '    try:\n'
        ftext += '        return returns(res)\n'
        ftext += '    except InvalidArgumentError as e:\n'
        ftext += '        if e.partial is not None:\n'
        ftext += '            return e.partial\n'
        ftext += '        else:\n'
        ftext += '            raise\n'

        globalz = dict(("_validate_{0}".format(arg._name), arg._type.handleVal) for arg in args)
        globalz['InvalidArgumentError'] = InvalidArgumentError
        globalz['returns'] = returns.handleVal

        six.exec_(ftext, globalz)
        func = globalz['func']
        del globalz['func']

        doc = "HTTP: {method} {path}\n\n".format(method=method, path=self.path)

        if args:
            doc += "    Arguments:\n"
            for arg in args:
                doc += "        {argName}: {argType}\n".format(argName=arg._name, argType=arg._type.name)
            doc += "\n"

        if returns is not None:
            doc += "    Returns: {res}\n".format(res=returns.name)

        func.__doc__ = doc
        func.spDoc = self.spDoc

        return func


def GET(query, *args, **kwargs):
    assert 'returns' in kwargs, 'GET requests must specify a return type'
    return _API_METHOD('GET', kwargs.get('multiCluster', False), query, args, kwargs.get('json', None), kwargs['returns'])


def POST(query, *args, **kwargs):
    return _API_METHOD('POST', kwargs.get('multiCluster', False), query, args, kwargs.get('json', None), kwargs.get('returns', ApiOk))


@JsonObject(ok=const(True), generation=longType, info=maybe(str))
class ApiOk(object):
    '''
    ok: Always returns true. If something goes wrong, an ApiError is returned instead.
    generation: The cluster generation based on the number of configuration changes since the cluster was created.
    info: May contain additional information about the request.
    '''


@JsonObject(autoName=sp.maybe(sp.SnapshotName))
class ApiOkVolumeCreate(ApiOk):
    '''
    autoName: The name of the transient snapshot used during the creation of the volume.
    '''


@JsonObject(remoteId=sp.maybe(sp.GlobalVolumeId))
class ApiOkVolumeBackup(ApiOkVolumeCreate):
    '''
    remoteId: The globally unique id of the backup
    '''


@JsonObject(backups={sp.VolumeName: sp.VolumesGroupBackupSingle})
class ApiOkVolumesGroupBackup(ApiOk):
    '''
    backups: The mapping of volume names to backup id.
    '''


@JsonObject(
    autoName=sp.maybe(sp.SnapshotName),
    snapshotGlobalId=sp.maybe(sp.GlobalVolumeId),
    snapshotVisibleVolumeId=sp.maybe(sp.longType)
)
class ApiOkSnapshotCreate(ApiOk):
    '''
    autoName: The name of the transient snapshot used during the creation of the volume.
    snapshotGlobalId: The global snapshot identifier.
    snapshotVisibleVolumeId: The ID by which the volume/snapshot was created.
    '''


class ApiError(Exception):
    def __init__(self, status, json):
        super(ApiError, self).__init__()
        self.status = status
        self.json = json
        self.name = json['error'].get('name', "<Missing error name>")
        self.desc = json['error'].get('descr', "<Missing error description>")
        self.transient = json['error'].get('transient', False)

    def __str__(self):
        return "{0}: {1}".format(self.name, self.desc)


class ApiMeta(type):
    def spDocSection(cls, name, desc):
        cls.spDoc.add_section(name, desc)

    def __setattr__(cls, name, func):
        cls.spDoc.add_call(func.spDoc)

        func = func.compile()
        func.__name__ = func.func_name = name
        func.__module__ = __name__
        type.__setattr__(cls, name, func)


def clear_none(data):
    """ Recursively remove any NoneType values. """
    if getattr(data, 'to_json', None) is not None:
        data = data.to_json()

    if isinstance(data, dict):
        return dict([
            (item[0], clear_none(item[1]))
            for item in data.items()
            if item[1] is not None
        ])

    if isinstance(data, list) or isinstance(data, set):
        return [clear_none(item) for item in data if item is not None]

    return data


@six.add_metaclass(ApiMeta)
class Api(object):
    '''StorPool API abstraction'''
    spDoc = ApiDoc(
        """StorPool API Reference""",
        """
        Copyright (c) 2014 - 2021  StorPool. All rights reserved.

        This reference document describes the StorPool API version 19.01 and
        the supported API calls.
        """)

    def __init__(self, host='127.0.0.1', port=80, auth='', timeout=300, transientRetries=5, transientSleep=lambda retry: 2 ** retry, source=None, multiCluster=False):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._transientRetries = transientRetries
        self._transientSleep = transientSleep
        self._authHeader = {"Authorization": "Storpool v1:" + str(auth)}
        self._multiCluster = multiCluster

        if source is not None:
            hinit = http.HTTPConnection.__init__
            if getattr(inspect, 'getfullargspec', None) is None:
                hargs = inspect.getargspec(hinit).args
            else:
                hargs = inspect.getfullargspec(hinit).args
            if "source_address" not in hargs:
                raise NotImplementedError(
                    "HTTP connection source not supported with "
                    "this Python version")
            self._source = {"source_address": (source, 0)}
        else:
            self._source = {}

    @classmethod
    def fromConfig(klass, cfg=None, **kwargs):
        if cfg is None:
            cfg = SPConfig()
        return klass(host=cfg['SP_API_HTTP_HOST'], port=int(cfg['SP_API_HTTP_PORT']), auth=cfg['SP_AUTH_TOKEN'], **kwargs)

    def __call__(self, method, multiCluster, query, json=None, clusterName=None):
        if json is not None:
            json = js.dumps(clear_none(json))

        def is_transient_error(err):
            if isinstance(err, http.HTTPException):
                return True
            assert isinstance(err, sock.error)
            return err.errno in (errno.ECONNREFUSED, errno.ECONNRESET)

        retry, lastErr = 0, None
        while True:
            conn = None
            try:
                conn = http.HTTPConnection(self._host, self._port, timeout=self._timeout, **self._source)
                path = _format_path(query, multiCluster and self._multiCluster, clusterName=clusterName)
                if method == "GET" and json:
                    path += "?json=" + uquote.quote(json, safe='')
                    json = None
                conn.request(method, path, json, self._authHeader)
                response = conn.getresponse()
                status, jres = response.status, js.load(response)

                if status != http.OK or 'error' in jres:
                    err = ApiError(status, jres)
                    if self._transientRetries and err.transient:
                        lastErr = err
                    else:
                        raise err
                else:
                    return jres['data']
            except (sock.error, http.HTTPException) as err:
                if self._transientRetries and is_transient_error(err):
                    lastErr = err
                else:
                    raise
            finally:
                if conn:
                    conn.close()

            if retry < self._transientRetries:
                retrySleep = self._transientSleep(retry)
                time.sleep(retrySleep)
                retry += 1
            else:
                raise lastErr

    def volumeDevLinkWait(self, volumeName, attach, pollTime=200 * msec, maxTime=60 * sec):
        return pathPollWait(SP_DEV_PATH + volumeName, attach, True, pollTime, maxTime)


Api.spDocSection("General",
    """
    The StorPool API can be used with any tool that can generate HTTP requests with the GET and POST methods.
    The only requirement is to supply the Authorization header and, if required by the request, valid JSON data.

    For each call there is an explanation of the HTTP request and response
    and an example in raw format as it should be sent to the StorPool management service.

    Here are two examples using curl using the GET and POST methods respectively and their counterparts as issued by the StorPool CLI:

    ```
    curl -H "Authorization: Storpool v1:1556129910218014736" 192.168.42.208:81/ctrl/1.0/DisksList
    storpool disk list
    ```

    ```
    curl -d '{"addDisks":["1"]}' -H "Authorization: Storpool v1:1556129910218014736" 192.168.42.208:81/ctrl/1.0/PlacementGroupUpdate/hdd
    storpool placementGroup hdd addDisk 1
    ```

    Python programs may use the API by importing the Python StorPool bindings (use 'pypi install storpool' to install them):

    ```
    # Use the default StorPool configuration settings

    >>> from storpool import spapi
    >>> api=spapi.Api.fromConfig()

    # Use an already-created spconfig.SPConfig object
    >>> api=spapi.Api.fromConfig(cfg=cfg)

    # Explicitly specify the hostname, port, and authentication string
    >>> api=spapi.Api(host='192.168.0.5', port=80, auth='1556560560218011653')

    # Use the default StorPool configuration settings but explicitly specify the source address as a string

    >>> from storpool import spapi
    >>> api=spapi.Api.fromConfig(source='192.168.0.2')

    # Use the created API access object
    >>> api.peersList()

    {
      1: {
           'networks': {
             0: {
              'mac': '00:4A:E6:5F:34:C3'
             }
           }
      },
      2: {
           'networks': {
             0: {
              'mac': '52:54:E6:5F:34:DF'
             }
           }
      },
      3: {
            'networks': {
              0: {
               'mac': '52:57:5F:54:E6:3A'
              }
            }
      }
    }
    ```

    The calls that may be used may be found in the file spapi.py.  As a rule of
    thumb, the name of the call is the name of the HTTP query with the first
    letter in lowercase (as above: "peersList()" for the "PeersList" query).
    To view them all once the StorPool bindings are installed, run a Python
    interpreter and then:


    ```
    >>> from storpool import spapi
    >>> help(spapi)
    ```

    Note: Requests will sometimes use GET instead of POST and consequently,
    will not require JSON. Responses on the other hand always produce JSON content.

    Some of the API calls may be used in a StorPool multicluster environment to
    reference and modify volumes and snapshots in a different (but connected)
    StorPool cluster. These have a "MultiCluster/" component in their URL path.
    When using the Python StorPool bindings, multicluster feature is enabled by
    adding a "multiCluster=True" parameter to the Api constructor invocation.

    In a StorPool multicluster environment an instance of the StorPool API may
    be used to forward a command to the API instance of another cluster by
    adding a "RemoteCommand/<clusterName>/" path component immediately after
    the API version prefix:

    ```
    curl -H "Authorization: Storpool v1:1556129910218014736" 192.168.42.208:81/ctrl/1.0/RemoteCommand/backup/DisksList
    ```

    When using the Python StorPool bindings, this is done by adding
    a "clusterName=clusterName" parameter to the API method invocation:

    ```
    api.disksList(clusterName="backup")
    ```
    """)

Api.spDocSection("Peers", """ """)
Api.peersList = GET('NetworkPeersList', returns={sp.PeerId: sp.PeerDesc}).doc("List the network peers",
    """
    List the network nodes running the StorPool beacon including information
    such as the ID of the node,
    the networks it communicates through and the corresponding MAC addresses.
    """)

Api.spDocSection("Tasks", """ """)
Api.tasksList = GET('TasksList', returns=[sp.Task]).doc("List tasks",
    """
    List the currently active recovery tasks. This call will return JSON
    data only when there is a relocation in progress. Under normal operation
    of the cluster it will return no data.
    """)

Api.spDocSection("Services", """ """)
Api.servicesList = GET('ServicesList', returns=sp.ClusterStatus).doc("List all StorPool services",
    """
    List all the services in the cluster (StorPool servers, clients, management, etc).
    If the whole cluster is
    not operational this call will return an error.
    """)
Api.serversListBlocked = GET('ServersListBlocked', returns=sp.ClusterStatus).doc("List all blocked StorPool servers",
    """
    List the currently active StorPool servers even before the cluster has become
    operational, along with information about any missing disks that the cluster
    is waiting for.
    """)

Api.spDocSection("Active requests", """ """)
Api.allPeersActiveRequests = GET('AllPeersActiveRequests', json=maybe(sp.AllPeersActiveRequestsQuery), returns=sp.AllPeersActiveRequests).doc("Query all peers for their status and active requests", """ """)

Api.spDocSection("Servers", """ """)
Api.serversList = GET('ServersList', returns=sp.ClusterStatus).doc("List all Storpool servers",
   """
   Returns the the same output as ServicesList but ommits clients. Returns
   an error if the whole cluster is not operational.
   """)
Api.serverDisksList = GET('ServerDisksList/{serverId}', ServerId, returns={sp.DiskId: sp.DiskSummary}).doc("List all disks on a server",
    """
    Return detailed information about each disk on the given server.
    """)
Api.serverDiskDescribe = GET('ServerDiskDescribe/{serverId}/{diskId}', ServerId, DiskId, returns=sp.Disk).doc("Describe a disk on a server",
    """
    Return detailed information about a disk on the given server and the
    objects on it.
    """)

Api.spDocSection("Clients", """ """)
Api.clientsConfigDump = GET('ClientsConfigDump', returns=[sp.ClientConfigStatus]).doc("Get the current status of all the clients",
    """
    Return the status of each client including its current generation and
    generation update status.
    """)
Api.clientConfigWait = GET('ClientConfigWait/{clientId}', ClientId, returns=[sp.ClientConfigStatus]).doc("Wait until a client updates to the current configuration",
    """
    Return the same JSON as ClientsConfigDump but block until the client
    has updated its configuration information to the current generation at
    the time of the request.
    """)
Api.clientActiveRequests = GET('ClientActiveRequests/{clientId}', ClientId, returns=sp.ClientActiveRequests).doc("List all the active requests on a client",
    """
    List detailed information about the requests being currently processed on
    the given client.
    """)

Api.spDocSection("Disks", """ """)
Api.disksList = GET('DisksList', returns={sp.DiskId: sp.DiskSummary}).doc("List all disks", """ """)
Api.diskDescribe = GET('DiskDescribe/{diskId}', DiskId, returns=sp.Disk).doc("Describe a disk",
    """
    List all disks including detailed information about the objects on each disk.
    """)
Api.diskInfo = GET('DiskGetInfo/{diskId}', DiskId, returns=sp.DiskInfo).doc("Get disk info",
    """
    List all disks including information about the volumes stored on each disk.
    """)
Api.diskEject = POST('DiskEject/{diskId}', DiskId).doc("Eject a disk",
    """ Stop operations on the given disk even if it is not empty. """)
Api.diskForget = POST('DiskForget/{diskId}', DiskId).doc("Forget a disk",
    """ Remove the disk from any placement groups or volumes that it is used in. """)
Api.diskIgnore = POST('DiskIgnore/{diskId}', DiskId).doc("Ignore a disk",
    """ Try to boot the cluster by ignoring this disk. """)
Api.diskSoftEject = POST('DiskSoftEject/{diskId}', DiskId).doc("Soft-eject a disk",
    """ Stop writes to the given disk and start relocating all the data stored on it to other disks. """)
Api.diskSoftEjectPause = POST('DiskSoftEjectPause/{diskId}', DiskId).doc("Pause a disk's soft-eject operation",
    """ Temporarily pause the relocation tasks for the disk. This can be helpful in heavy load situations. """)
Api.diskSoftEjectCancel = POST('DiskSoftEjectCancel/{diskId}', DiskId).doc("Cancel a disk's soft-eject operation",
    """ Stop the relocation tasks for the disk and mark it as usable again. After this operation data will be moved back to the disk. """)
Api.diskSetDesc = POST('DiskSetDescription/{diskId}', DiskId, json=sp.DiskDescUpdate).doc("Set a disk's description", """ """)
Api.diskActiveRequests = GET('DiskActiveRequests/{diskId}', DiskId, returns=sp.DiskActiveRequests).doc("List all the active requests on a disk",
    """
    List detailed information about the requests being currently processed
    on the given disk.
    """)

Api.diskScrubStart = POST("DiskScrubStart/{diskId}", DiskId).doc("Start scrubbing process", """ """)
Api.diskScrubPause = POST("DiskScrubPause/{diskId}", DiskId).doc("Pause scrubbing process", """ """)
Api.diskScrubContinue = POST("DiskScrubContinue/{diskId}", DiskId).doc("Continue paused scrubbing process", """ """)
Api.diskRetrim = POST("DiskRetrim/{diskId}", DiskId).doc("Retrim disk", """ """)

Api.spDocSection("Volumes", """ """)
Api.volumesList = GET('VolumesList', returns=[sp.VolumeSummary], multiCluster=True).doc("List all volumes",
    """ Return configuration information about all the volumes. """)
Api.volumesStatus = GET('VolumesGetStatus', returns={either(sp.VolumeName, sp.SnapshotName): sp.VolumeStatus}, multiCluster=True).doc("Get volume and snapshot status",
    """ Return the status of each volume and snapshot. """)
Api.volumesSpace = GET('VolumesSpace', returns=[sp.VolumeSpace], multiCluster=True).doc("List total used space by each volume",
    """
    List estimated total virtual space used by each volume.
    """)
Api.volumeList = GET('Volume/{volumeName}', VolumeName, returns=[sp.VolumeSummary], multiCluster=True).doc("List a single volume",
    """ Same as VolumeList but only return information about a given volume. """)
Api.volumeDescribe = GET('VolumeDescribe/{volumeName}', VolumeName, returns=sp.Volume, multiCluster=True).doc("Describe a volume",
    """
    Return detailed information about the distribution of the volume's data on
    the disks.
    """)
Api.volumeInfo = GET('VolumeGetInfo/{volumeName}', VolumeName, returns=sp.VolumeInfo, multiCluster=True).doc("Get volume info",
    """
    Return general information about the distribution of the volume's data on
    the disks.
    """)
Api.volumeListSnapshots = GET('VolumeListSnapshots/{volumeName}', VolumeName, returns=[sp.SnapshotSummary]).doc("List the parent snapshots of a volume",
    """
    List a volume's parent snapshots in the same format as
    VolumeList
    """)
Api.volumeCreate = POST('VolumeCreate', json=sp.VolumeCreateDesc, returns=ApiOkVolumeCreate, multiCluster=True).doc("Create a new volume", """ """)
Api.volumeUpdate = POST('VolumeUpdate/{volumeName}', VolumeName, json=sp.VolumeUpdateDesc, multiCluster=True).doc("Update a volume",
    """ Alter the configuration of an existing volume. """)
Api.volumeFreeze = POST('VolumeFreeze/{volumeName}', VolumeName, json=maybe(sp.VolumeFreezeDesc), multiCluster=True).doc("Freeze a volume",
    """ Convert the volume to a snapshot """)
Api.volumeRebase = POST('VolumeRebase/{volumeName}', VolumeName, json=sp.VolumeRebaseDesc).doc("Rebase a volume",
    """
    Change the parent of the volume by choosing from the ones higher in
    the hierarchy or by rebasing it to no parent.
    """)
Api.volumeAbandonDisk = POST('VolumeAbandonDisk/{volumeName}', VolumeName, json=sp.AbandonDiskDesc).doc("Abandon disk",
    """
    """)
Api.volumeDelete = POST('VolumeDelete/{volumeName}', VolumeName, multiCluster=True).doc("Delete a volume", """ """)
Api.volumeBackup = POST('VolumeBackup', json=sp.VolumeBackupDesc, returns=ApiOkVolumeBackup, multiCluster=True).doc("Backup a volume to a remote location",
    """
    """)
Api.volumesGroupBackup = POST('VolumesGroupBackup', json=sp.VolumesGroupBackupDesc, returns=ApiOkVolumesGroupBackup, multiCluster=True).doc("Backup a group of volumes to a remote location",
    """
    """)

Api.volumeMoveToRemote = POST('VolumeMoveToRemote/{volumeName}', VolumeName, json=sp.VolumeMoveToRemoteDesc).doc("Move a volume from local cluster to a remote cluster",
   """
   """)

Api.volumeExport = POST('VolumeExport/{volumeName}', VolumeName, json=sp.VolumeExportDesc).doc("Export a volume to another cluster, so it can be attached when allowRemoteExports is true",
   """
   """)

Api.volumeAcquire = POST('VolumeAcquire/{volumeName}', VolumeName, json=sp.VolumeAcquireDesc, multiCluster=True).doc("Move the volume from its current remote cluster to the local one. Noop if already here. Multicluster only call",
   """
   """)

Api.volumeFromRemote = POST('VolumeFromRemote', json=sp.VolumeFromRemoteDesc).doc("Create a volume from a snapshot from a remote location",
  """
  """)

Api.volumeRevert = POST("VolumeRevert/{volumeName}", VolumeName, json=sp.VolumeRevertDesc, multiCluster=True).doc("Revert volume to a snapshot discarding all its current data", """ """)

Api.spDocSection("Snapshots",
    """
    Snapshots in their essence are very similar to volumes in the sense
    that many operations supported by volumes are also supported by
    snapshots (all except write-related operations). They can not be
    modified and play an essential role in copy-on-write scenarios.
    """)
Api.snapshotsList = GET('SnapshotsList', returns=[sp.SnapshotSummary], multiCluster=True).doc("List all snapshots",
    """
    List all the snapshots in the cluster in the same
    format as VolumeList.
    """)
Api.snapshotsSpace = GET('SnapshotsSpace', returns=[sp.SnapshotSpace], multiCluster=True).doc("List snapshots space estimations",
    """
    List estimated virtual space used by each snapshot.
    """)
Api.snapshotList = GET('Snapshot/{snapshotName}', SnapshotName, returns=[sp.SnapshotSummary], multiCluster=True).doc("List a single snapshot",
    """ Same as SnapshotList but only return information about a given snapshot. """)
Api.snapshotDescribe = GET('SnapshotDescribe/{snapshotName}', SnapshotName, returns=sp.Snapshot, multiCluster=True).doc("Describe a snapshot",
    """
    Return detailed information about the distribution of the snapshot's data on the
    disks.
    """)
Api.snapshotInfo = GET('SnapshotGetInfo/{snapshotName}', SnapshotName, returns=sp.SnapshotInfo, multiCluster=True).doc("Get snapshot info",
    """
    Return general information about the distribution of the snapshot's data on the
    disks.
    """)
Api.snapshotCreate = POST('VolumeSnapshot/{volumeName}', VolumeName, json=sp.VolumeSnapshotDesc, returns=ApiOkSnapshotCreate, multiCluster=True).doc("Snapshot a volume",
    """
    Create a snapshot of the given volume; the snapshot becomes the parent of
    the volume.
    """)
Api.snapshotUpdate = POST('SnapshotUpdate/{snapshotName}', SnapshotName, json=sp.SnapshotUpdateDesc).doc("Update a snapshot",
    """ Alter the configuration of an existing snapshot. """)
Api.snapshotRebase = POST('SnapshotRebase/{snapshotName}', SnapshotName, json=sp.VolumeRebaseDesc).doc("Rebase a snapshot",
    """
    Change the parent of the snapshot by choosing from the ones higher in
    the hierarchy or by rebasing it to no parent.
    """)
Api.snapshotAbandonDisk = POST('VolumeAbandonDisk/{snapshotName}', SnapshotName, json=sp.AbandonDiskDesc).doc("Abandon disk",
    """
    """)
Api.snapshotDelete = POST('SnapshotDelete/{snapshotName}', SnapshotName, multiCluster=True).doc("Delete a snapshot", """ """)

Api.snapshotDeleteById = POST('SnapshotDeleteById/{globalVolumeId}', GlobalVolumeId).doc("Delete a snapshot by global id", """ """)

Api.snapshotCreateGroup = POST('VolumesGroupSnapshot', json=sp.GroupSnapshotsSpec, returns=sp.GroupSnapshotsResult, multiCluster=True).doc("Create consistent snapshots of a group of volumes",
    """
    """)

Api.snapshotFromRemote = POST('SnapshotFromRemote', json=sp.SnapshotFromRemoteDesc).doc("Copy a snapshot from a remote location",
    """
    """)
Api.snapshotExport = POST('SnapshotExport', json=sp.SnapshotExportDesc).doc("Allow a remote location to access a local snapshot",
    """
    """)
Api.snapshotUnexport = POST('SnapshotUnexport', json=sp.SnapshotUnexportDesc).doc("Revoke a remote location's access to a local snapshot",
    """
    """)

Api.exportsList = GET('ExportsList', returns={'exports': [sp.Export]}).doc("List exported snapshots",
    """
    """)

Api.volumeExportsList = GET('VolumeExportsList', returns={'exports': [sp.Export]}).doc("List exported volumes",
    """
    """)

Api.snapshotsRemoteList = GET('SnapshotsRemoteList', returns={'snapshots': [sp.RemoteSnapshot]}).doc("List the available remote snapshots",
    """
    """)

Api.volumesRemoteList = GET('VolumesRemoteList', returns={'volumes': [sp.RemoteSnapshot]}).doc("List the available remote volumes",
    """
    """)

Api.snapshotsRemoteUnexport = POST('SnapshotsRemoteUnexport', json=sp.SnapshotsRemoteUnexport).doc("Instruct the remote location that we will no longer use those snapshots",
    """
    """)

Api.spDocSection("Attachments", """""")
Api.attachmentsList = GET('AttachmentsList', returns=[sp.AttachmentDesc], multiCluster=True).doc("List all attachments",
    """
    List the volumes and snapshots currently attached to clients along with
    the read/write rights of each attachment.
    """)
Api.volumesReassign = POST('VolumesReassign', json=[either(sp.VolumeReassignDesc, sp.SnapshotReassignDesc)], multiCluster=True).doc("Reassign volumes and/or snapshots",
    """ Perform bulk attach/detach and attachment rights modification. """)

Api.volumesReassignWait = POST('VolumesReassignWait', json=sp.VolumesReassignWaitDesc, multiCluster=True).doc("Reassign volumes and/or snapshots with confirmation from the clients",
    """ Perform bulk attach/detach and attachment rights modification and waits for the clients to catch up. """)

Api.spDocSection("Placement Groups",
    """
    Placement groups provide a way to specify the disks on which a volume's data
    should be stored.
    """)
Api.placementGroupsList = GET('PlacementGroupsList', returns={sp.PlacementGroupName: sp.PlacementGroup}).doc("List all placement groups", """ """)
Api.placementGroupDescribe = GET('PlacementGroupDescribe/{placementGroupName}', PlacementGroupName, returns=sp.PlacementGroup).doc("Describe a single placement group",
    """
    Same as PlacementGroupsList but only return information about a given group.
    """)
Api.placementGroupUpdate = POST('PlacementGroupUpdate/{placementGroupName}', PlacementGroupName, json=sp.PlacementGroupUpdateDesc).doc("Create and/or update a placement group",
    """
    If a group by the specified name does not exist, it will be created.
    """)
Api.placementGroupDelete = POST('PlacementGroupDelete/{placementGroupName}', PlacementGroupName).doc("Delete a placement group", """ """)

Api.faultSetsList = GET('FaultSetsList', returns={sp.FaultSetName: sp.FaultSet}).doc("List all fault sets", """ """)


Api.spDocSection("Volume Templates",
    """ Templates are a set of rules used for creating many similar volumes. """)
Api.volumeTemplatesList = GET('VolumeTemplatesList', returns=[sp.VolumeTemplateDesc]).doc("List all volume templates", """ """)
Api.volumeTemplatesStatus = GET('VolumeTemplatesStatus', returns=[sp.VolumeTemplateStatusDesc]).doc("List the status of all volume templates", """ """)
Api.volumeTemplateDescribe = GET('VolumeTemplateDescribe/{templateName}', VolumeTemplateName, returns=sp.VolumeTemplateDesc).doc("Describe a single volume template",
    """
    Same as VolumeTemplatesList but only return information about a given template.
    """)
Api.volumeTemplateCreate = POST('VolumeTemplateCreate', json=sp.VolumeTemplateCreateDesc).doc("Create a volume template", """ """)
Api.volumeTemplateUpdate = POST('VolumeTemplateUpdate/{templateName}', VolumeTemplateName, json=sp.VolumeTemplateUpdateDesc).doc("Update a volume template",
    """ Alter the configuration of an existing volume template. """)
Api.volumeTemplateDelete = POST('VolumeTemplateDelete/{templateName}', VolumeTemplateName).doc("Delete a volume template", """ """)

Api.spDocSection("Volume Relocator",
    """
    This is a service that moves data when needed, e.g. when
    removing or adding disks.
    """)
Api.volumeRelocatorStatus = GET('VolumeRelocatorStatus', returns=sp.VolumeRelocatorStatus).doc("Get the relocator's status", """ """)
Api.volumeRelocatorDisks = GET('VolumeRelocatorDisksList', returns={sp.DiskId: sp.DiskTarget}).doc("List total per disk relocation estimates",
    """
    """)
Api.volumeRelocatorVolumeDisks = GET('VolumeRelocatorVolumeDisks/{volumeName}', VolumeName, returns={sp.DiskId: sp.DiskTarget}).doc("List per disk relocation estimates for a given volume", """ """)
Api.volumeRelocatorSnapshotDisks = GET('VolumeRelocatorSnapshotDisks/{snapshotName}', SnapshotName, returns={sp.DiskId: sp.DiskTarget}).doc("List per disk relocation estimates for a given snapshot", """ """)

Api.spDocSection("Balancer",
    """ This is a service that decides when it is a good time to move data. """)
Api.volumeBalancerGetStatus = GET('VolumeBalancerStatus', returns=sp.VolumeBalancerStatus).doc("Get the balancer's status", """ """)
Api.volumeBalancerSetStatus = POST('VolumeBalancerStatus', json=sp.VolumeBalancerCommand).doc("Set the balancer's status", """ """)
Api.volumeBalancerVolumesStatus = GET('VolumeBalancerVolumesStatus', returns=[sp.VolumeBalancerVolumeStatus]).doc("List balancer volume and snapshot status",
    """
    Show which volumes and snapshots will be reallocated by the
    current balancer run.
    """)
Api.volumeBalancerDisks = GET('VolumeBalancerDisksList', returns={sp.DiskId: sp.DiskTarget}).doc("List total per disk rebalancing estimates", """ """)
Api.volumeBalancerVolumeDisks = GET('VolumeBalancerVolumeDisks/{volumeName}', VolumeName, returns={sp.DiskId: sp.DiskTarget}).doc("List per disk rebalancing estimated for a given volume", """ """)
Api.volumeBalancerSnapshotDisks = GET('VolumeBalancerSnapshotDisks/{snapshotName}', SnapshotName, returns={sp.DiskId: sp.DiskTarget}).doc("List per disk rebalancing estimates for a given snapshot", """ """)
Api.volumeBalancerVolumeDiskSets = GET('VolumeBalancerVolumeDiskSets/{volumeName}', VolumeName, returns=sp.VolumeBalancerVolumeDiskSets).doc("Get the disk sets computed by the balancer for a given volume", """ """)
Api.volumeBalancerSnapshotDiskSets = GET('VolumeBalancerSnapshotDiskSets/{snapshotName}', SnapshotName, returns=sp.VolumeBalancerVolumeDiskSets).doc("Get the disk sets computed by the balancer for a given snapshot", """ """)
Api.volumeBalancerGroups = GET('VolumeBalancerGroups', returns=[sp.VolumeBalancerAllocationGroup]).doc("List balancer allocation groups", """ """)

Api.spDocSection("iSCSI", "")

Api.iSCSIConfig = GET('iSCSIConfig', returns=sp.iSCSIConfig).doc("Get the StorPool iSCSI configuration", """ """)
Api.iSCSIConfigChange = POST('iSCSIConfig', json=sp.iSCSIConfigChange).doc("Modify the StorPool iSCSI configuration", """ """)

Api.iSCSISessionsInfo = GET('iSCSISessionsInfo', json=maybe(sp.iSCSIControllersQuery), returns=sp.iSCSISessionsInfo).doc("Query iSCSI controllers for active sessions", """ """)
Api.iSCSInterfacesInfo = GET('iSCSInterfacesInfo', json=maybe(sp.iSCSIControllersQuery), returns=sp.iSCSIControllersIntefacesInfo).doc("Query iSCSI controllers for interfaces state", """ """)

Api.spDocSection("Remote", "")

Api.locationsList = GET("LocationsList", returns={'locations': [sp.RemoteLocation]}).doc("List the registered remote locations", "")
Api.locationAdd = POST("LocationAdd", json=sp.RemoteLocationBase).doc("Register a new remote location", """ """)
Api.locationRemove = POST("LocationRemove", json={'location': sp.RemoteLocationName}).doc("Remove a remote location", """ """)
Api.locationUpdate = POST("LocationUpdate", json=sp.RemoteLocationUpdateDesc).doc("Update a remote location", """ """)
Api.locationRename = POST("LocationRename", json=sp.RemoteLocationRenameDesc).doc("Rename a remote location", """ """)

Api.clustersList = GET("ClustersList", returns={'clusters': [sp.RemoteCluster]}).doc("List the registered remote clusters", "")
Api.clusterAdd = POST("ClusterAdd", json=sp.RemoteClusterAddDesc).doc("Register a new remote cluster", """ """)
Api.clusterRemove = POST("ClusterRemove", json=sp.RemoteClusterRemoveDesc).doc("Remove a remote cluster", """ """)
Api.clusterRename = POST("ClusterRename", json=sp.RemoteClusterRenameDesc).doc("Rename a remote cluster", """ """)

Api.remoteBridgesList = GET("RemoteBridgesList", returns={'remoteBridges': [sp.RemoteBridge]}).doc("List the registered remote bridges", "")
Api.remoteBridgeAdd = POST("RemoteBridgeAdd", json=sp.RemoteBridgeAddDesc).doc("Register a new remote bridge", """ """)
Api.remoteBridgeRemove = POST("RemoteBridgeRemove", json=sp.RemoteBridgeRemoveDesc).doc("Deregister a remote bridge", """ """)

Api.spDocSection("Nodes in maintenance", "")

Api.maintenanceList = GET("MaintenanceList", returns=sp.MaintenanceNodesList).doc("List the nodes in maintenance", "")
Api.maintenanceSet = POST("MaintenanceSet", json=sp.MaintenanceSetDesc).doc("Set node in maintenance", "")
Api.maintenanceComplete = POST("MaintenanceComplete", json=sp.MaintenanceCompleteDesc).doc("Complete node's maintenance.", "")

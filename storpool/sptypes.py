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
""" Utility type definitions for the StorPool API bindings. """

import re
import time

from .spcatch import error
from .sptype import JsonObject, spTypeFun, maybe, const, either, eitherOr, internal, longType
from .spjson import dumps


# Simple validator functions
def regex(argName, regex):
    _regex = re.compile(regex)

    def validator(string):
        if string is None:
            error('No {argName} specified', argName=argName)

        try:
            string = str(string)

            if not _regex.match(string):
                error('Invalid {argName} "{argVal}". Must match {regex}', argName=argName, argVal=string, regex=regex)

            return string
        except ValueError:
            error('Invalid {argName}. Must be string', argName=argName)

    return spTypeFun(argName, validator, '''string, regex {regex}'''.format(regex=regex))


def oneOf(argName, *accepted):
    accepted = list(accepted)
    _accepted = frozenset(accepted)

    def validator(value):
        if value not in _accepted:
            error("Invalid {argName}: {value}. Must be one of {accepted}", argName=argName, value=value, accepted=accepted)
        else:
            return value

    return spTypeFun(argName, validator, '''One of {{{accepted}}}'''.format(accepted=", ".join(map(dumps, accepted))))


def intRange(argName, min, max):
    def validator(i):
        try:
            i = int(i)

            if i < min or i > max:
                error('Invalid {argName}. Must be between {min} and {max}', argName=argName, min=min, max=max)

            return i
        except ValueError:
            error('Invalid {argName}. Must be an integer', argName=argName)

    return spTypeFun(argName, validator, '''integer, {min} <= value <= {max}'''.format(min=min, max=max))


def namedEnum(argName, names, first=0):
    names = list(names)
    end = first + len(names)

    for name in names:
        assert name not in globals(), "{name} = {val} already defined in globals()".format(name=name, val=globals()[name])
        globals()[name] = name

    def validator(val):
        try:
            val = int(val)
            if val < first or val >= end:
                error("Invalid {argName} value {val}. Must be between {first} and {last}", argName=argName, val=val, first=first, last=end - 1)

            return names[val - first]
        except ValueError:
            error("Invalid {argName}. Must be an integer")

    return spTypeFun(argName, validator, '''{argName}, enumeration from {first} to {last}'''.format(argName=argName, first=first, last=end - 1))


def unlimitedInt(argName, min, unlimited):
    def validator(val):
        if val is None:
            error('No {argName} specified', argName=argName)
        elif val == unlimited:
            return val

        try:
            val = int(val)
            if val < min:
                error('Ivalid {argName}. Must be at least {min}', argName=argName, min=min)
            else:
                return val
        except ValueError:
            error('Non-numeric {argName}: {value}', argName=argName, value=val)

    return spTypeFun(argName, validator, '''a positive integer or '{unlimited}' for unlimited'''.format(unlimited=unlimited))


def nameValidator(argName, regex, size, *blacklisted):
    _regex = re.compile(regex)
    blacklisted = list(blacklisted)
    _blacklisted = frozenset(blacklisted)

    def validator(name):
        if name is None:
            error('No {argName} specified', argName=argName)

        try:
            name = str(name)

            if not _regex.match(name):
                error('Invalid {argName} "{argVal}". Must match {regex}', argName=argName, argVal=name, regex=regex)
            elif name in _blacklisted:
                error('{argName} must not be in {blacklisted}', argName=argName, blacklisted=blacklisted)
            elif len(name) >= size:
                error('{argName} is too long. Max allowed is {max}', argName=argName, max=size - 1)
            else:
                return name
        except ValueError:
            error('Invalid {argName}. Must be a string', argName=argName)

    return spTypeFun(argName, validator, '''a string({size}), matching {regex}, except {{{blacklisted}}}'''.format(size=size, regex=regex, blacklisted=", ".join(map(str, blacklisted))))


def volumeSizeValidator(argName):
    def validator(size):
        try:
            size = int(size)
            if size < 1:
                error('Invalid {argName} {size}. Must be positive', argName=argName, size=size)
            elif size % SECTOR_SIZE:
                error('Invalid {argName} {size}. Must be a multiple of {sectorSize}', argName=argName, size=size, sectorSize=SECTOR_SIZE)
            else:
                return size
        except ValueError:
            error('Non-numeric {argName}: {size}', argName=argName, size=size)

    return spTypeFun(argName, validator, '''a positive integer divisible by {sectorSize}'''.format(sectorSize=SECTOR_SIZE))


# Common constants
VOLUME_NAME_SIZE = 200
PLACEMENT_GROUP_NAME_SIZE = 128
VOLUME_NAME_REGEX = r'^\#?[A-Za-z0-9_\-.:]+$'
SNAPSHOT_NAME_REGEX = r'^\*?[A-Za-z0-9_\-.:@]+$'
PLACEMENT_GROUP_NAME_REGEX = r'^[A-Za-z0-9_\-]+$'
VOLUME_TEMPLATE_NAME_REGEX = r'^[A-Za-z0-9_\-]+$'
DISK_DESC_REGEX = r'^[A-Za-z0-9_\- ]{,30}$'
REMOTE_LOCATION_NAME_SIZE = 64
REMOTE_LOCATION_NAME_REGEX = VOLUME_NAME_REGEX
VOLUME_TAG_NAME_REGEX = r'^[A-Za-z0-9_\-.:]+$'
VOLUME_TAG_VALUE_REGEX = r'^[A-Za-z0-9_\-.:]*$'

SECTOR_SIZE = 512
MAX_CHAIN_LENGTH = 6

MAX_CLIENT_DISKS = 1024
MAX_CLIENT_DISK = MAX_CLIENT_DISKS - 1
MAX_CLUSTER_DISKS = 4096
MAX_DISK_ID = MAX_CLUSTER_DISKS - 1

MAX_NET_ID = 3
MAX_NODE_ID = 63
MAX_PEER_ID = 0xffff
PEER_SUBTYPE_BRIDGE = 0x7000
PEER_TYPE_CLIENT = 0x8000
PEER_SUBTYPE_MGMT = 0xf000
MAX_PEERS_PER_SUBTYPE = 0x1000
MAX_SERVER_ID = PEER_TYPE_CLIENT - 1
MAX_BRIDGE_ID = MAX_PEERS_PER_SUBTYPE - 1
MAX_CLIENT_ID = MAX_PEERS_PER_SUBTYPE - 1
MAX_MGMT_ID = MAX_PEERS_PER_SUBTYPE - 1

GENERATION_NONE = longType(-1)

# Simple type validators
MacAddr = regex('MAC Address', r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
BeaconNodeStatus = oneOf('BeaconNodeStatus', 'NODE_DOWN', 'NODE_UP')
BeaconClusterStatus = oneOf('BeaconClusterStatus', 'CNODE_DOWN', 'CNODE_DAMPING', 'CNODE_UP')
PeerStatus = oneOf('PeerStatus', 'up', 'down')
ClientStatus = oneOf('ClientStatus', 'running', 'down')
ServerStatus = oneOf('ServerStatus', 'running', 'waiting', 'booting', 'down')
BridgeStatus = oneOf('BridgeStatus', 'running', 'joining', 'down')
ClusterStatus = oneOf('ClusterStatus', 'running', 'waiting', 'down')
GUID = regex('GUID', r'^0x[0-9a-fA-F]{2,16}$')

NetId = intRange('NetID', 0, MAX_NET_ID)
NodeId = intRange('NodeID', 0, MAX_NODE_ID)
PeerId = intRange('PeerID', 0, MAX_PEER_ID)
ClientId = intRange('ClientID', 1, MAX_CLIENT_ID)
ServerId = intRange('ServerID', 1, MAX_SERVER_ID)
MgmtId = intRange('MgmtID', 1, MAX_MGMT_ID)
BridgeId = intRange('BridgeId', 1, MAX_BRIDGE_ID)

DiskId = intRange('DiskID', 0, MAX_DISK_ID)
DiskDescription = regex('DiskDescritpion', DISK_DESC_REGEX)

SnapshotName = nameValidator("SnapshotName", SNAPSHOT_NAME_REGEX, VOLUME_NAME_SIZE, 'list', 'status')

VolumeName = nameValidator("VolumeName", VOLUME_NAME_REGEX, VOLUME_NAME_SIZE, 'list', 'status')
VolumeReplication = intRange('Replication', 1, 3)
VolumeSize = volumeSizeValidator("Size")
VolumeResize = volumeSizeValidator("SizeAdd")

VolumeTagName = nameValidator("VolumeTagName", VOLUME_TAG_NAME_REGEX, VOLUME_NAME_SIZE)
VolumeTagValue = nameValidator("VolumeTagValue", VOLUME_TAG_VALUE_REGEX, VOLUME_NAME_SIZE)

PlacementGroupName = nameValidator("PlacementGroupName", PLACEMENT_GROUP_NAME_REGEX, PLACEMENT_GROUP_NAME_SIZE, 'list')
FaultSetName = PlacementGroupName
VolumeTemplateName = nameValidator("VolumeTemplateName", VOLUME_TEMPLATE_NAME_REGEX, VOLUME_NAME_SIZE, 'list')

Bandwidth = unlimitedInt('Bandwidth', 0, '-')
IOPS = unlimitedInt('IOPS', 0, '-')
AttachmentRights = oneOf('AttachmentRights', 'rw', 'ro')

ObjectState = namedEnum("ObjectState", "OBJECT_UNDEF OBJECT_OK OBJECT_OUTDATED OBJECT_IN_RECOVERY OBJECT_WAITING_FOR_VERSION OBJECT_WAITING_FOR_DISK OBJECT_DATA_NOT_PRESENT OBJECT_DATA_LOST OBJECT_WAINING_FOR_CHAIN OBJECT_WAIT_IDLE".split(' '))

RemoteLocationName = nameValidator("RemoteLocationName", REMOTE_LOCATION_NAME_REGEX, REMOTE_LOCATION_NAME_SIZE, 'list')
GlobalVolumeId = regex('Global Volume Id', r'[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+$')
LocationId = regex('Global Location Id', r'[a-z0-9]+$')

iSCSIId = intRange('iSCSIId', 0, 0x0fff)
iSCSIName = r'^[a-z0-9\-.:]+$'
iSCSIPGName = r'^[A-Za-z0-9_\-.:]+$'


# NETWORK
@JsonObject(mac=MacAddr)
class NetDesc(object):
    pass


RdmaState = oneOf('RdmaState', 'Idle', 'GidReceived', 'Connecting', 'Connected', 'pendingError', 'Error')


@JsonObject(guid=GUID, state=RdmaState)
class RdmaDesc(object):
    pass


@JsonObject(beaconStatus=BeaconNodeStatus, clusterStatus=BeaconClusterStatus, joined=bool, networks=maybe({NetId: NetDesc}), rdma=({NetId: RdmaDesc}), nonVoting=bool)
class PeerDesc(object):
    '''
    beaconStatus: Whether a beacon is running at all on this node.
    clusterStatus: Whether we consider this node a part of the cluster quorum.
    joined: Whether the node considers itself a part of the cluster quorum.
    networks: List of the Ethernet networks that StorPool communicates through on this node.
    rdma: List of the RDMA networks that StorPool communicates through on this node.
    nonVoting: Whether this is a non-voting StorPool node (e.g. client only).
    '''


# SERVER
@JsonObject(nodeId=NodeId, version=str, startTime=eitherOr(int, None))
class Service(object):
    '''
    nodeId: The ID of the node on which the service is running.
    version: The version of the running StorPool service.
    startTime: The start time of this service (UNIX timestamp).
    '''

    @property
    def running(self):
        return self.status == 'running'

    @property
    def uptime(self):
        if self.startTime is None:
            return None
        else:
            now = int(time.time())
            return now - min(self.startTime, now)


@JsonObject(id=ServerId, status=ServerStatus, missingDisks=[DiskId], pendingDisks=[DiskId])
class Server(Service):
    '''
    id: The ID of the service. Currently this is the same as the ID of the node.
    status: down - There is no storpool_server daemon running or it is still recovering its drives from a crashed state. waiting - storpool_server is running but waiting for some disks to appear to prevent split-brain situations. booting - No missing disks; the server is in the process of joining the cluster ...
    missingDisks: The cluster will remain down until these disks are seen again. This happens in the case of simultaneous failure of the whole cluster (power failure); the servers keep track of where the most recent configuration and data was stored.
    pendingDisks: Similar to missingDisks, these are the disks that are ready and waiting for the missing ones.
    '''


@JsonObject(id=ClientId, status=ClientStatus)
class Client(Service):
    '''
    id: The ID of the service. Currently this is the same as the ID of the node.
    status: The current status of the client.
    '''


@JsonObject(id=MgmtId, status=ClientStatus, prio=internal(int), active=bool)
class Mgmt(Service):
    '''
    id: The ID of the service.
    status: The current status of the mgmt instance.
    active: If the instance is currently active. For a given cluster one mgmt instance will be active at any given time.
    '''


@JsonObject(id=BridgeId, status=BridgeStatus)
class Bridge(Service):
    '''
    id: The ID of the service.
    status: The current status of the remote cluster bridge.
    '''


@JsonObject(clusterStatus=ClusterStatus, mgmt={MgmtId: Mgmt}, clients={ClientId: Client}, servers={ServerId: Server}, bridges={BridgeId: Bridge})
class ClusterStatus(object):
    '''
    clusterStatus: The current status of the whole cluster. running - At least one running server; a cluster is formed. waiting - In quorum but negotiations between servers are not over yet. down - No quorum; most likely because more beacons are needed.
    '''


# CLIENT
@JsonObject(id=ClientId, generation=longType, clientGeneration=longType, configStatus=oneOf("client status", 'ok', 'updating', 'down'), delay=int)
class ClientConfigStatus(object):
    '''
    generation: The cluster generation based on the number of configuration changes since the cluster was created.
    clientGeneration: The generation of the specific client.
    configStatus: Whether there is an update of the configuration in progress.
    delay: The time it took for the client generation to reach the cluster generation. Only applicable to ClientConfigWait. Always 0 in ClientsConfigDump.
    '''


# TASK
@JsonObject(diskId=DiskId, transactionId=longType, allObjects=int, completedObjects=int, dispatchedObjects=int, unresolvedObjects=internal(int))
class Task(object):
    '''
    diskId: The disk ID this task is on.
    transactionId: An ID associated with the currently running task. This ID is the same for all the tasks running on different disks but initiated by the same action (e.g. when reallocating a volume, all tasks associated with that volume will have the same ID).
    allObjects: The number of all the objects that the task is performing actions on.
    completedObjects: The number of objects that the task has finished working on.
    dispatchedObjects: Objects that the task has started working on.
    '''


# DISK
@JsonObject(objectId=internal(int), generation=longType, version=longType, volume=str, parentVolume=str, onDiskSize=int, storedSize=int, state=ObjectState,
    volumeId=internal(longType))
class DiskObject(object):
    '''
    parentVolume: The name of the parent snapshot.
    generation: The generation when the last write to this object occurred.
    onDiskSize: The space allocated on the disk for the object. This can go up to 32MB.
    storedSize: The size of the actual data in that object (<= onDiskSize).
    volume: The name of the volume for which the object contains data.
    version: With each write the version is increased.
    '''

    @property
    def ok(self):
        return self.state == OBJECT_OK  # noqa: F821


@JsonObject(name=str, storedSize=longType, onDiskSize=longType, objectsCount=longType, objectStates={ObjectState: int})
class DiskVolumeInfo(object):
    '''
    objectsCount: The number of objects of the volume stored on this disk.
    objectStates: For each state, the number of objects that are in that state. 0-undefined 1-ok 2-outdated 3-in_recovery 4-waiting_for_version 5-waiting_for_disk 6-data_not_present 7-data_lost 8-waiting_for_chain 9-wait_idle
    onDiskSize: The space allocated on the disk for the object. This can go up to 32MB.
    storedSize: The size of the actual data in that object (<= onDiskSize).
    '''


@JsonObject(pages=int, pagesPending=int, maxPages=int)
class DiskWbcStats(object):
    pass


@JsonObject(entries=int, space=int, total=int)
class DiskAggregateScores(object):
    pass


@JsonObject(id=DiskId, serverId=ServerId, ssd=bool, generationLeft=longType, model=str, serial=str, description=DiskDescription, softEject=oneOf('DiskSoftEjectStatus', "on", "off", "paused"))
class DiskSummaryBase(object):
    '''
    id: The ID of this disk. It is set when the disk is formatted to work with StorPool.
    serverId: The ID of the server this disk is currently on. In case the disk is currently down, the last known server ID is reported.
    ssd: Whether the device is an SSD.
    generationLeft: The last cluster generation when the disk was active on a running server, or -1 if the disk is currently active.
    softEject: The status of the soft-eject process.
    description: A user-defined description of the disk for easier identification of the device.
    model: The drive's model.
    serial: The drive's serial.
    '''


@JsonObject()
class DownDiskSummary(DiskSummaryBase):
    up = False


@JsonObject(generationLeft=const(GENERATION_NONE), sectorsCount=longType, empty=bool, noFua=bool, noFlush=bool, noTrim=bool, isWbc=bool, journaled=bool, device=str,
    agCount=internal(int), agAllocated=internal(int), agFree=internal(int), agFull=internal(int), agPartial=internal(int), agFreeing=internal(int), agMaxSizeFull=internal(int), agMaxSizePartial=internal(int),
    entriesCount=int, entriesAllocated=int, entriesFree=int,
    objectsCount=int, objectsAllocated=int, objectsFree=int, objectsOnDiskSize=longType,
    wbc=internal(eitherOr(DiskWbcStats, None)), aggregateScore=internal(DiskAggregateScores),
    scrubbingStartedBefore=int, scrubbedBytes=int, scrubbingBW=int, scrubbingFinishAfter=int,
    scrubbingPausedFor=int, scrubbingPaused=bool, lastScrubCompleted=int)
class UpDiskSummary(DiskSummaryBase):
    '''
    sectorsCount: The amount of 512-byte sectors on the disk.
    noFua: Whether to issue FUA writes to this device.
    noFlush: Whether write-back cache flushing is disabled for this device.
    noTrim: Whether trim-below is disabled for this device.
    isWbc: Whether write-back cache is enabled for this device.
    journaled: Whether StorPool journaling is enabled for this device.
    device: The name of the physical disk device on the server.
    entriesAllocated: Used entries of the disk.
    objectsAllocated: Used objects of the disk.
    entriesFree: The remaining number of entries that can be stored on the disk.
    objectsFree: The remaining number of objects that can be stored on the disk.
    entriesCount: The maximum amount of entries that can exists on the disk.
    objectsCount: The maximum amount of object that can exists on the disk.
    empty: True if no volumes or snapshots are on this disk.
    objectsOnDiskSize: Total size occupied by objects. In essence, this is the estimated disk usage by StorPool.
    scrubbingStartedBefore: In seconds.
    scrubbedBytes: For current scrubbing job run.
    scrubbingBW: Estimate of the disk BS used for scrubbing B/s.
    scrubbingFinishAfter: Extimate of when the scrubbing job is expected to finish based on scrubbingBW and current disk usage.
    scrubbingPausedFor: How many seconds has the current scrubbing job been paused.
    scrubbingPaused: Is scrubbing currently paused
    lastScrubCompleted: Unix time in seconds when last scrubbing job was completed.
    '''

    up = True


DiskSummary = either(UpDiskSummary, DownDiskSummary)


@JsonObject(objectStates={ObjectState: int}, volumeInfos={str: DiskVolumeInfo})
class DiskInfo(UpDiskSummary):
    '''
    For each state, the number of objects that are in that state. 0-undefined 1-ok 2-outdated 3-in_recovery 4-waiting_for_version 5-waiting_for_disk 6-data_not_present 7-data_lost 8-waiting_for_chain 9-wait_idle
    volumeInfos: Detailed information about the volumes that have data stored on the disk.
    '''


@JsonObject(objects={int: DiskObject})
class Disk(UpDiskSummary):
    '''
    objects: Detailed information about each object on the disk.
    '''


@JsonObject(description=DiskDescription)
class DiskDescUpdate(object):
    '''
    description: A user-defined description of the disk for easier identification of the device.
    '''


# ACTIVE REQUESTS
@JsonObject(requestId=str, requestIdx=int, volume=either(VolumeName, SnapshotName), address=longType, size=int,
    op=oneOf('RequestOp', "read", "write", "merge", "system", "entries flush", "#bad_state", "#bad_drOp"), state=internal(str), prevState=internal(str), drOp=internal(str), msecActive=int)
class ActiveRequestDesc(object):
    '''
    requestId: A unique request ID that may be matched between clients and disks.
    requestIdx: A temporary local request identifier for this request on this client or disk.
    address: The offset in bytes within the logical volume.
    size: The size of the request in bytes.
    op: The type of the requested operation; one of read, write, system, merge, entries flush, #bad_state, #bad_drOp
    state: An internal attribute used only for debugging. We strongly recommend that you do not use this attribute in any kind of automation.
    prevState: An internal attribute used only for debugging. We strongly recommend that you do not use this attribute in any kind of automation.
    drOp: An internal attribute used only for debugging. We strongly recommend that you do not use this attribute in any kind of automation.
    msecActive: Time in microseconds since the request was submitted.
    '''


@JsonObject(clientId=ClientId, requests=[ActiveRequestDesc])
class ClientActiveRequests(object):
    '''
    requests: A detailed listing of all the requests associated with the given client.
    '''


@JsonObject(diskId=DiskId, requests=[ActiveRequestDesc])
class DiskActiveRequests(object):
    '''
    requests: A detailed listing of all the requests associated with the given disk.
    '''


# PLACEMENT GROUP
@JsonObject(id=internal(int), name=PlacementGroupName, disks=set([DiskId]))
class PlacementGroup(object):
    '''
    disks: IDs of the participating disks.
    '''


@JsonObject(rename=maybe(PlacementGroupName), addDisks=set([DiskId]), rmDisks=set([DiskId]))
class PlacementGroupUpdateDesc(object):
    '''
    rename: The new name of the placement group.
    addDisks: IDs of the disks to add to this group.
    rmDisks: IDs of the disks to be removed from this group.
    '''


# FAULT SETS
@JsonObject(name=FaultSetName, servers=set([ServerId]))
class FaultSet(object):
    '''
    servers: List of servers in one fault set
    '''


# VOLUME and SNAPSHOT
@JsonObject(bw=Bandwidth, iops=IOPS)
class VolumeLimits(object):
    '''
    bw: Bandwidth limit in KB.
    iops: iops limit.
    '''


@JsonObject(id=internal(longType), parentName=eitherOr(SnapshotName, ""), templateName=eitherOr(VolumeTemplateName, ""),
    size=VolumeSize, replication=VolumeReplication,
    placeAll=PlacementGroupName, placeTail=PlacementGroupName, placeHead=PlacementGroupName,
    parentVolumeId=internal(longType), originalParentVolumeId=internal(longType), visibleVolumeId=longType, templateId=internal(longType),
    objectsCount=int, creationTimestamp=longType, flags=internal(int), tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumeSummaryBase(VolumeLimits):
    '''
    parentName: The volume/snapshot's parent snapshot.
    templateName: The template that the volume/snapshot's settings are taken from.
    size: The volume/snapshots's size in bytes.
    replication: The number of copies/replicas kept.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    parentVolumeId: The ID of the parent snapshot.
    visibleVolumeId: The ID by which the volume/snapshot was created.
    objectsCount: The number of objects that the volume/snapshot is comprised of.
    creationTimestamp: The volume's creation timestamp (UNIX timestamp)
    tags: Arbitrary short name/value pairs stored with the volume.
    '''


@JsonObject(name=VolumeName)
class VolumeSummary(VolumeSummaryBase):
    '''
    name: The name of this volume.
    '''


@JsonObject(name=SnapshotName, onVolume=VolumeName,
    autoName=bool, bound=bool, deleted=bool, transient=bool, targetDeleteDate=maybe(int), globalId=GlobalVolumeId,
    recoveringFromRemote=bool)
class SnapshotSummary(VolumeSummaryBase):
    '''
    name: The name of this snapshot
    onVolume: The name of the volume that this is a parent of.
    autoName: Is this snapshot anonymous.
    bound: Is this a bound snapshot. Bound snapshots are garbage-collected as soon as they remain childless and are no longer attached.
    deleted: Is this snapshot currently being deleted.
    transient: Is this a transient snapshot. Transient snapshots are internally created when cloning a volume. They cannot be attached as they may be garbage-collected at any time.
    targetDeleteDate: Scheduled date for the snapshot to be deleted. Unix timestamp
    globalId: The global snapshot identifier.
    recoveringFromRemote: Is this snapshot's data currently being transferred from a remote location.
    '''


@JsonObject(storedSize=longType, spaceUsed=longType)
class SnapshotSpace(SnapshotSummary):
    '''
    storedSize: The number of bytes of client data on this snapshot. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
    spaceUsed: The number of bytes of client data that will be freed if this snapshot is deleted.
    '''


@JsonObject(storedSize=longType, spaceUsed=longType)
class VolumeSpace(VolumeSummary):
    '''
    storedSize: The number of bytes of client data on this volume. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
    spaceUsed: The total number of bytes of client data that on this volume. This includes data that is stored in all the volume's parents
    '''


@JsonObject(disks=[DiskId], count=int)
class VolumeChainStat(object):
    '''
    disks: IDs of the disks.
    count: The number of objects on the disks.
    '''


@JsonObject(disksCount=int, objectsPerDisk={DiskId: int}, objectsPerChain=[VolumeChainStat], objectsPerDiskSet=[VolumeChainStat])
class VolumeInfo(VolumeSummary):
    pass


@JsonObject(disksCount=int, objectsPerDisk={DiskId: int}, objectsPerChain=[VolumeChainStat], objectsPerDiskSet=[VolumeChainStat])
class SnapshotInfo(SnapshotSummary):
    pass


@JsonObject(name=either(VolumeName, SnapshotName), size=VolumeSize, replication=VolumeReplication,
    status=oneOf("VolumeCurentStatus", "up", "up soon", "data lost", "down"), snapshot=bool, migrating=bool, decreasedRedundancy=bool, balancerBlocked=bool,
    storedSize=int, onDiskSize=int, syncingDataBytes=int, syncingMetaObjects=int, downBytes=int,
    downDrives=[DiskId], missingDrives=[DiskId], missingTargetDrives=[DiskId], softEjectingDrives=[DiskId],
    tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumeStatus(object):
    '''
    name: The volume's name.
    size: The volume's size in bytes.
    replication: The number of copies/replicas kept.
    status: up - The volume is operational. up soon - Synchronizing versions of objects after a disk has come back up. data lost - The last copy of some of the data in the volume has been lost. down - Some or all of the objects of the volume are missing and the volume is not in a state to continue serving operations.
    snapshot: True if this response describes a snapshot instead of a volume.
    migrating: True if there are tasks for reallocation of the volume.
    decreasedRedundancy: True if any of the replicas of the volume are missing.
    balancerBlocked: Can this volume be rebalanced, or is rebalancing impossible with the current placement policy due to for example missing or soft-ejecting drives.
    storedSize: The number of bytes of client data on the volume. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
    onDiskSize: The actual size that the objects of this volume occupy on the disks.
    syncingDataBytes: The total number of bytes in objects currently being synchronized (degraded objects or objects with not yet known version)
    syncingMetaObjects: The number of objects currently being synchronized (degraded objects or objects with not yet known version)
    downBytes: The number of bytes of the volume that are not accessible at the moment.
    downDrives: The IDs of the drives that are not accessible at the moment but needed by this volume. The volume will be in the 'down' status until all or some of these drives reappear.
    missingDrives: The IDs of the drives that are not accessible at the moment. The volume has all the needed data on the rest of the disks and can continue serving requests but it is in the 'degraded' status.
    tags: Arbitrary short name/value pairs stored with the volume.
    '''


@JsonObject(targetDiskSets=[[DiskId]], objects=[[DiskId]])
class Snapshot(SnapshotSummary):
    '''
    targetDiskSets: Sets of disks that the volume's data should be stored on.
    objects: Where each object is actually stored.
    '''


@JsonObject(targetDiskSets=[[DiskId]], objects=[[DiskId]])
class Volume(VolumeSummary):
    '''
    targetDiskSets: Sets of disks that the volume's data should be stored on.
    objects: Where each object is actually stored.
    '''


@JsonObject(placeAll=maybe(PlacementGroupName), placeTail=maybe(PlacementGroupName), placeHead=maybe(PlacementGroupName), replication=maybe(VolumeReplication), bw=maybe(Bandwidth), iops=maybe(IOPS), reuseServer=maybe(bool), tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumePolicyDesc(object):
    '''
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    bw: Bandwidth limit in KB.
    iops: iops limit.
    replication: The number of copies/replicas kept.
    reuseServer: allow placement of replicas on same server.
    tags: Optional name=value tags.
    '''


@JsonObject(name=VolumeName, size=maybe(VolumeSize), parent=maybe(SnapshotName), template=maybe(VolumeTemplateName), baseOn=maybe(VolumeName))
class VolumeCreateDesc(VolumePolicyDesc):
    '''
    name: The name of the volume to be created.
    size: The volume's size in bytes.
    parent: The name of the snapshot that the new volume is based on.
    template: The name of the template that the settings of the new volume are based on.
    baseOn: The name of an already existing volume that the new volume is to be a copy of.
    '''


@JsonObject(rename=maybe(VolumeName), size=maybe(VolumeSize), sizeAdd=maybe(VolumeResize), template=maybe(VolumeTemplateName), shrinkOk=maybe(bool))
class VolumeUpdateDesc(VolumePolicyDesc):
    '''
    rename: The new name to be set.
    size: The new size in bytes.
    sizeAdd: The number of bytes that the volume's size should be increased by.
    template: The new template that the volume's settings should be based on.
    '''


@JsonObject(name=maybe(VolumeName), bind=maybe(bool), targetDeleteDate=maybe(int), deleteAfter=maybe(int), tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumeSnapshotDesc(object):
    '''
    name: The name of the newly created snapshot. If not specified, a name will be auto-generated by the StorPool management service.
    bind: If true, the lifetime of the newly created snapshot will be bound to the lifetime of its children. As soon as it remains childless the snapshot will be garbage-collected.
    targetDeleteDate: If not 0 set absolute targetDeleteDate for the new snapshot. Unix timestamp. targetDeleteDate can not be set in the past
    deleteAfter: If not 0 set targetDeleteDate relative to the current time on the mgmt node. This value will be added to the current time as seconds and set as targetDeleteDate.
    tags: Arbitrary short name/value pairs stored with the snapshot.
    '''


@JsonObject(rename=maybe(VolumeName), bind=maybe(bool), targetDeleteDate=maybe(int), deleteAfter=maybe(int), tags=maybe({VolumeTagName: VolumeTagValue}))
class SnapshotUpdateDesc(VolumePolicyDesc):
    '''
    rename: The new name to be set.
    bind: When true bind this snapshot, when false - unbind it. If not set or missing - no change.
    targetDeleteDate: set absolute targetDeleteDate, or 0 to disable automatic deleting. Unix timestamp. targetDeleteDate can not be set in the past
    deleteAfter: set targetDeleteDate relative to the current time on the mgmt node. If not 0 this value will be added to the current time as seconds and set as targetDeleteDate. If 0 it will discard previous targetDeleteDate
    tags: Arbitrary short name/value pairs stored with the snapshot.
    '''


@JsonObject(parentName=maybe(SnapshotName))
class VolumeRebaseDesc(object):
    '''
    parentName: The name of one of the volume's parents on which to re-base. If left out, it will be re-based to base.
    '''


@JsonObject(diskId=DiskId)
class AbandonDiskDesc(object):
    '''
    diskId: the disk to abandon.
    '''


@JsonObject(targetDeleteDate=maybe(int), deleteAfter=maybe(int))
class VolumeFreezeDesc(object):
    '''
    targetDeleteDate: If not 0 set absolute targetDeleteDate for the freezed snapshot. Unix timestamp. targetDeleteDate can not be set in the past
    deleteAfter: If not 0 set targetDeleteDate relative to the current time on the mgmt node. This value will be added as to the current time as seconds and set as targetDeleteDate.
    '''


# VOLUME RIGHTS
DetachClientsList = eitherOr([ClientId], "all")
AttachmentPos = intRange('AttachmentPos', 0, MAX_CLIENT_DISK)


@JsonObject(volume=VolumeName, detach=maybe(DetachClientsList), ro=maybe([ClientId]), rw=maybe([ClientId]), force=False)
class VolumeReassignDesc(object):
    '''
    volume: The name of the volume to be reassigned.
    detach: The clients from which to detach the given volume.
    ro: The clients on which to attach the volume as read only.
    rw: The clients on which to attach the volume as read/write.
    force: Whether to force detaching of open volumes.
    '''


@JsonObject(snapshot=SnapshotName, detach=maybe(DetachClientsList), ro=maybe([ClientId]), force=False)
class SnapshotReassignDesc(object):
    '''
    snapshot: The name of the snapshot which should be reassigned.
    detach: The clients from which to detach the given snapshot.
    ro: The clients on which to attach the snapshot.
    force: Whether to force detaching of open snapshots.
    '''


@JsonObject(reassign=[either(VolumeReassignDesc, SnapshotReassignDesc)], attachTimeout=maybe(int))
class VolumesReassignWaitDesc(object):
    '''
    reassign: The list of volumes and snapshots to modify the attachment settings for.
    attachTimeout: The number of seconds to wait for missing clients to appear when attaching to them.  If not specified, wait indefinitely.  If explicitly set to 0, immediately return successfully even if any clients are missing.
    '''


@JsonObject(volume=VolumeName, snapshot=bool, client=ClientId, rights=AttachmentRights, pos=AttachmentPos)
class AttachmentDesc(object):
    '''
    snapshot: Whether it is a snapshot or a volume.
    client: The ID of the client on which it is attached.
    volume: The name of the attached volume.
    rights: Whether the volume is attached as read only or read/write; always ro for snapshots.
    pos: The attachment position on the client; used by the StorPool client to form the name of the internal /dev/spN device node.
    '''


# VOLUME TEMPLATES
@JsonObject(id=internal(int), name=VolumeTemplateName, parentName=eitherOr(SnapshotName, ""), placeAll=PlacementGroupName, placeTail=PlacementGroupName, placeHead=PlacementGroupName,
    size=eitherOr(VolumeSize, "-"), replication=eitherOr(VolumeReplication, "-"), reuseServer=maybe(bool))
class VolumeTemplateDesc(VolumeLimits):
    '''
    name: The name of the template.
    parentName: The name of the snapshot on which volumes will be based.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    size: A default size for the volumes (in bytes).
    replication: A default number of copies to be kept by StorPool.
    reuseServer: allow placement of replicas on same server.
    '''


@JsonObject(u1=int, u2=int, u3=int)
class VolumeTemplateSpaceEstInternal(object):
    pass


@JsonObject(free=int, capacity=int, internal=internal(VolumeTemplateSpaceEstInternal))
class VolumeTemplateSpaceEstEntry(object):
    '''
    capacity: Estimated total client data capacity.
    free: Estimated free space remaining.
    '''


@JsonObject(placeAll=VolumeTemplateSpaceEstEntry, placeTail=VolumeTemplateSpaceEstEntry, placeHead=VolumeTemplateSpaceEstEntry)
class VolumeTemplateSpaceEst(VolumeTemplateSpaceEstEntry):
    '''
    placeAll: placeAll placement group estimations.
    placeTail: placeTail placement group estimations.
    placeHead: placeHead placement group estimations.
    '''


@JsonObject(id=internal(int), name=VolumeTemplateName, placeAll=PlacementGroupName, placeTail=PlacementGroupName, placeHead=PlacementGroupName, replication=eitherOr(VolumeReplication, "-"),
    volumesCount=int, snapshotsCount=int, removingSnapshotsCount=int,
    size=eitherOr(VolumeSize, 0), totalSize=eitherOr(VolumeSize, 0), onDiskSize=longType, storedSize=longType,
    availablePlaceAll=longType, availablePlaceTail=longType, availablePlaceHead=longType, capacityPlaceAll=longType, capacityPlaceTail=longType, capacityPlaceHead=longType,
    stored=VolumeTemplateSpaceEst)
class VolumeTemplateStatusDesc(object):
    '''
    name: The name of the template.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    replication: The number of copies to be kept by StorPool if defined for this template, otherwise "-".
    volumesCount: The number of volumes based on this template.
    snapshotsCount: The number of snapshots based on this template (incl. snapshots currently being deleted).
    removingSnapshotsCount: The number of snapshots based on this template currently being deleted.
    size: The number of bytes of all volumes based on this template, not counting the StorPool replication and checksums overhead.
    totalSize: The number of bytes of all volumes based on this template, including the StorPool replication overhead.
    storedSize: The number of bytes of client data on all the volumes based on this template. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
    onDiskSize: The actual on-disk number of bytes occupied by all the volumes based on this template.
    availablePlaceAll: An estimate of the available space on all the disks in this template's placeAll placement group.
    availablePlaceTail: An estimate of the available space on all the disks in this template's placeTail placement group.
    availablePlaceHead: An estimate of the available space on all the disks in this template's placeHead placement group.
    capacityPlaceAll: An estimate of the total physical space on all the disks in this template's placeAll placement group.
    capacityPlaceTail: An estimate of the total physical space on all the disks in this template's placeTail placement group.
    capacityPlaceHead: An estimate of the total physical space on all the disks in this template's placeHead placement group.
    stored: Estimated client data capacity and free space.
    '''


@JsonObject(name=VolumeTemplateName, parent=maybe(SnapshotName), size=maybe(VolumeSize))
class VolumeTemplateCreateDesc(VolumePolicyDesc):
    '''
    name: The name of the new template.
    parent: The name of the snapshot on which to base volumes created by this template.
    size: A default size for the volumes (in bytes).
    '''


@JsonObject(rename=maybe(VolumeTemplateName), parent=maybe(SnapshotName), size=maybe(VolumeSize), propagate=maybe(bool))
class VolumeTemplateUpdateDesc(VolumePolicyDesc):
    '''
    rename: The new name of the template.
    parent: The name of the snapshot on which to base volumes created by this template.
    size: A default size for the volumes (in bytes).
    propagate: Whether to propagate this change to all the volumes and snapshots using this template.
    '''


# VOLUME RELOCATOR and BALANCER
@JsonObject(status=oneOf("RelocatorStatus", 'on', 'off', 'blocked'), volumesToRelocate=int)
class VolumeRelocatorStatus(object):
    '''
    status: 'off' - relocator is currently turned off. 'on' - relocator is on. 'blocked' - relocation is blocked, most likely due to missing drives.
    volumesToRelocate: Number of volumes currently being relocated.
    '''


@JsonObject(status=oneOf("BalancerStatus", 'nothing to do', 'blocked', 'waiting', 'working', 'ready', 'commiting'), auto=bool)
class VolumeBalancerStatus(object):
    '''
    status: The current balancer status.
    auto: Is balancer running in automatic mode.
    '''


@JsonObject(cmd=oneOf("BalancerCommand", 'start', 'stop', 'commit'))
class VolumeBalancerCommand(object):
    '''
    cmd: The command for the balacer to execute. 'start' - run the balancer. 'stop' - abort current run. 'commit' - commit volume allocation changes.
    '''


@JsonObject(name=either(VolumeName, SnapshotName),
    placeAll=PlacementGroupName, placeTail=PlacementGroupName, placeHead=PlacementGroupName, replication=VolumeReplication,
    size=longType, objectsCount=int,
    snapshot=bool, reallocated=bool, blocked=bool)
class VolumeBalancerVolumeStatus(object):
    '''
    name: The volume's name.
    size: The volume's size in bytes.
    replication: The number of copies/replicas kept.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    objectsCount: The number of objects that the volume/snapshot is comprised of.
    snapshot: True if this response describes a snapshot instead of a volume.
    reallocated: is this volume/snapshot going to reallocated by the balancing procedure.
    blocked: Can this volume be rebalanced, or is rebalancing impossible with the current placement policy due to for example missing or soft-ejecting drives.
    '''


@JsonObject(currentDiskSets=[[DiskId]], balancerDiskSets=[[DiskId]])
class VolumeBalancerVolumeDiskSets(VolumeBalancerVolumeStatus):
    '''
    currentDiskSets: The current sets of disks that the volume's data should be stored on.
    balancerDiskSets: The new sets of disks that the volume's data should be stored on according to the rebalancing algorithm.
    '''


@JsonObject(current=int, target=int, delta=int, toRecover=int)
class TargetDesc(object):
    '''
    current: The current value.
    target: The target value.
    delta: The difference between the target and current values.
    toRecover: The amount that will have to be recovered to get from the current to the target state.
    '''


@JsonObject(id=DiskId, serverId=ServerId, generationLeft=longType)
class DownDiskTarget(object):
    '''
    id: The ID of this disk.
    serverId: The ID of the server this disk was last on.
    generationLeft: The last cluster generation when the disk was active on a running server.
    '''


@JsonObject(id=DiskId, serverId=ServerId, generationLeft=const(GENERATION_NONE),
    objectsAllocated=TargetDesc, objectsCount=int,
    storedSize=TargetDesc, onDiskSize=TargetDesc)
class UpDiskTarget(object):
    '''
    id: The ID of this disk.
    serverId: The ID of the server this disk was last on.
    generationLeft: The last cluster generation when the disk was active on a running server. -1 since the disk is currently up.
    objectsCount: The maximum amount of object that can exists on the disk.
    objectsAllocated: Statistics about the amount of objects to be allocated on this disk.
    storedSize: Statistics about the amount of cilent data to be stored on this disk.
    onDiskSize: Statistics about the total amount of space occupied by the objects on this disk.
    '''


DiskTarget = either(UpDiskTarget, DownDiskTarget)


@JsonObject(storedSize=int, objectsCount=int)
class VolumeBalancerSlot(object):
    '''
    storedSize: Number of bytes of client data stored on the corresponding disk set.
    objectsCount: Number of objects on the corresponding disk set.
    '''


@JsonObject(placeAll=PlacementGroupName, placeTail=PlacementGroupName, placeHead=PlacementGroupName, replication=VolumeReplication,
    feasible=bool, blocked=bool,
    size=int, storedSize=int, objectsCount=int,
    root=either(VolumeName, SnapshotName), volumes=[either(VolumeName, SnapshotName)],
    targetDiskSets=[[DiskId]], slots=[VolumeBalancerSlot], reuseServer=maybe(bool))
class VolumeBalancerAllocationGroup(object):
    '''
    root: The name of this group's root volume or snapshot
    volumes: The names of all volumes and snapshots in this group.
    size: The total size of all volumes and snapshots in the group.
    storedSize: The total number of bytes of client data on all volumes and  snapshots in this group.
    objectsCount: The total number of objects of all volumes and snapshots in the group.
    replication: The number of copies/replicas kept.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    feasible: Can new volumes be allocated with the current placement policy and redundancy constraints.
    blocked: Can this volume be rebalanced, or is rebalancing impossible with the current placement policy due to for example missing or soft-ejecting drives.
    targetDiskSets: The current sets of disks that the volume's data should be stored on.
    slots: Statistics about each of the current disk sets.
    reuseServer: allow placement of replicas on same server
    '''


@JsonObject(remoteLocation=RemoteLocationName, remoteId=GlobalVolumeId, name=maybe(VolumeName), placeAll=maybe(PlacementGroupName), placeTail=maybe(PlacementGroupName), placeHead=maybe(PlacementGroupName), replication=maybe(VolumeReplication), template=maybe(VolumeTemplateName), export=maybe(bool), tags=maybe({VolumeTagName: VolumeTagValue}))
class SnapshotFromRemoteDesc(object):
    '''
    remoteLocation: The name of the remote location to fetch the snapshot from.
    remoteId: The global snapshot identifier.
    name: The name of the new snapshot.
    placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
    placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
    placeHead: The name of a placement group which describes the disks to be used for the first replica.
    export: Auto-export the snapshot after creating it. e.g. for backup.
    tags: Arbitrary short name/value pairs stored with the snapshot.
    '''


@JsonObject(snapshot=SnapshotName, location=RemoteLocationName)
class SnapshotExportDesc(object):
    '''
    snapshot: The name of the snapshot.
    location: The name of the remote location to grant access to.
    '''


@JsonObject(snapshot=SnapshotName, location=maybe(RemoteLocationName), all=maybe(bool), force=maybe(bool))
class SnapshotUnexportDesc(object):
    '''
    snapshot: The name of the snapshot.
    location: The name of the remote location to revoke access from.
    all: Revoke access from all locations.
    force: Don't check if the snapshot is still recovering in the remote location.
    '''


@JsonObject(volume=VolumeName, location=RemoteLocationName, tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumeBackupDesc(object):
    '''
    volume: The name of the volume to backup.
    location: The remote location to backup to.
    tags: Arbitrary short name/value pairs stored with the volume.
    '''


@JsonObject(remoteId=GlobalVolumeId)
class VolumesGroupBackupSingle(object):
    '''
    remoteId: the globally unique id of the backup.
    '''


@JsonObject(location=RemoteLocationName, volumes=[VolumeName], tags=maybe({VolumeTagName: VolumeTagValue}))
class VolumesGroupBackupDesc(object):
    '''
    volumes: The names of the volumes to backup.
    location: The remote location to backup to.
    tags: Arbitrary short name/value pairs stored with the volume.
    '''


@JsonObject(name=VolumeName, location=RemoteLocationName, creationTimestamp=longType, size=VolumeSize, remoteId=GlobalVolumeId, onVolume=maybe(VolumeName), localSnapshot=maybe(SnapshotName))
class RemoteSnapshot(object):
    '''
    name: The name of the snapshot.
    location: Where the snapshot is located.
    creationTimestamp: The snapshot's creation timestamp (UNIX timestamp).
    size: The snapshots's size in bytes.
    remoteId: The global snapshot identifier.
    onVolume: The name of the local volume (if any) on which the snapshot was created.
    localSnapshot: The name of the local snapshot (if any) which is a copy of the remote snapshot.
    '''


@JsonObject(id=LocationId, name=RemoteLocationName)
class RemoteLocation(object):
    '''
    id: A StorPool-provided unique location id.
    name: The human-readable location name.
    '''


@JsonObject(snapshot=SnapshotName, location=RemoteLocationName, globalId=GlobalVolumeId, backingUp=maybe(bool), volumeId=internal(longType), visibleVolumeId=internal(longType))
class Export(object):
    '''
    snapshot: The name of the snapshot.
    location: Name of the location the snapshot is exported to
    globalId: The global snapshot identifier.
    backingUp: Is this a backup in making
    '''


@JsonObject(location=RemoteLocationName, globalSnapshotId=GlobalVolumeId, targetDeleteDate=maybe(int), deleteAfter=maybe(int))
class SnapshotRemoteUnexportDesc(object):
    '''
    location: name of the location to unexport from
    globalSnapshotId: the id of the snapshot to be unexported
    targetDeleteDate: if not 0 instruct the remote location to delete the snapshot at the specified date. Remote side may not allow this due to configuration or the snapshot beeeing used
    deleteAfter: same as targetDeleteDate, but time in secs relative to current time on the mgmt node
    '''


@JsonObject(remoteSnapshots=[SnapshotRemoteUnexportDesc])
class SnapshotsRemoteUnexport(object):
    '''
    remoteSnapshots: list of SnapshotRemoteUnexportDesc
    '''


@JsonObject(volume=VolumeName, name=maybe(SnapshotName))
class GroupSnapshotSpec(object):
    '''
    volume: The name of the volume to create a snapshot of.
    name: The name of the snapshot to create.
    '''


@JsonObject(volumes=[GroupSnapshotSpec])
class GroupSnapshotsSpec(object):
    '''
    volumes: The volumes to create snapshots of.
    '''


@JsonObject(volume=VolumeName, snapshot=maybe(SnapshotName), remoteId=GlobalVolumeId)
class GroupSnapshotResult(object):
    '''
    volume: The name of the source volume.
    snapshot: The name of the created snapshot.
    remoteId: The globally unique id of the created snapshot.
    '''


@JsonObject(volumes=[GroupSnapshotResult])
class GroupSnapshotsResult(object):
    '''
    volumes: The volumes to create snapshots of.
    '''


@JsonObject(portalGroup=iSCSIPGName, target=iSCSIName)
class iSCSIExport(object):
    '''
    portalGroup: The portal group exporting this volume.
    target: The target exporting this volume.
    '''


@JsonObject(name=iSCSIName, username=str, secret=str, nets=[str], exports=[iSCSIExport])
class iSCSIInitiator(object):
    '''
    name: The iSCSI initiator's IQN.
    user: The username to authenticate the initiator by.
    secret: The password to authenticate the initiator with.
    nets: The networks this initiator will contact the iSCSI cluster on.
    '''


@JsonObject(address=str, prefix=int)
class iSCSIPGNetwork(object):
    '''
    address: The dotted-quad network address.
    prefix: The network's CIDR prefix length.
    '''


@JsonObject(controller=iSCSIId, ip=str, port=str)
class iSCSIPortal(object):
    '''
    controller: The StorPool iSCSI target service handling this portal.
    ip: The IP address for the portal.
    port: The TCP port for the portal.
    '''


@JsonObject(name=iSCSIPGName, networks=[iSCSIPGNetwork], portals=[iSCSIPortal])
class iSCSIPortalGroup(object):
    '''
    name: The iSCSI portal group name.
    networks: The networks this portal group is accessible on.
    portals: The list of portals defined in this group.
    '''


@JsonObject(currentControllerId=int, name=iSCSIName, volume=VolumeName)
class iSCSITarget(object):
    '''
    currentControllerId: the StorPool iSCSI target service handling this target.
    name: The iSCSI name that the target is exposed as.
    volume: The name of the StorPool volume being exposed.
    '''


@JsonObject(baseName=iSCSIName, initiators={iSCSIId: iSCSIInitiator}, portalGroups={int: iSCSIPortalGroup}, targets={int: iSCSITarget})
class iSCSIConfigData(object):
    '''
    baseName: The StorPool cluster's iSCSI base name.
    initiators: The iSCSI initiators allowed to access the cluster.
    portalGroups: The iSCSI portal groups defined for the cluster.
    '''


@JsonObject(iscsi=iSCSIConfigData)
class iSCSIConfig(object):
    '''
    iscsi: The actual configuration data
    '''


@JsonObject(name=iSCSIName)
class iSCSICommandSetBaseName(object):
    '''
    name: The new StorPool cluster iSCSI base name.
    '''


@JsonObject(name=iSCSIPGName)
class iSCSICommandCreatePortalGroup(object):
    '''
    name: The name of the iSCSI portal group to create.
    '''


@JsonObject(name=iSCSIPGName)
class iSCSICommandDeletePortalGroup(object):
    '''
    name: The name of the iSCSI portal group to delete.
    '''


@JsonObject(portalGroup=iSCSIPGName, net=str)
class iSCSICommandPortalGroupAddNetwork(object):
    '''
    portalGroup: The name of the iSCSI portal group to modify.
    net: the x.x.x.x/n CIDR definition of the network to add.
    '''


@JsonObject(portalGroup=iSCSIPGName, controller=iSCSIId, ip=str, port=maybe(int))
class iSCSICommandCreatePortal(object):
    '''
    portalGroup: The name of the iSCSI portal group to modify.
    controller: the StorPool iSCSI target service to handle this portal.
    ip: The IP address for the portal.
    port: The TCP port for the portal (default: 3260).
    '''


@JsonObject(ip=str, port=maybe(int))
class iSCSICommandDeletePortal(object):
    '''
    ip: The IP address for the portal to remove.
    port: The TCP port for the portal (default: 3260).
    '''


@JsonObject(volumeName=VolumeName)
class iSCSICommandCreateTarget(object):
    '''
    volumeName: The StorPool volume name to create an iSCSI target for.
    '''


@JsonObject(volumeName=VolumeName)
class iSCSICommandDeleteTarget(object):
    '''
    volumeName: The StorPool volume name to delete the iSCSI target for.
    '''


@JsonObject(name=iSCSIName, username=str, secret=str)
class iSCSICommandCreateInitiator(object):
    '''
    name: The name the initiator will use to connect.
    username: The username the initiator will authenticate as.
    secret: The password the initiator will authenticate with.
    '''


@JsonObject(name=iSCSIName)
class iSCSICommandDeleteInitiator(object):
    '''
    name: The name of the iSCSI initiator to delete.
    '''


@JsonObject(initiator=iSCSIName, net=str)
class iSCSICommandInitiatorAddNetwork(object):
    '''
    initiator: The name of the iSCSI initiator to modify.
    net: The CIDR x.x.x.x/n definition of the network to add.
    '''


@JsonObject(initiator=iSCSIName, portalGroup=iSCSIPGName, volumeName=VolumeName)
class iSCSICommandExport(object):
    '''
    initiator: The name of the iSCSI initiator to allow access to the volume.
    portalGroup: The name of the iSCSI portal group to export the volume in.
    volumeName: The name of the volume to export.
    '''


@JsonObject(initiator=iSCSIName, portalGroup=iSCSIPGName, volumeName=VolumeName)
class iSCSICommandExportDelete(object):
    '''
    initiator: The name of the iSCSI initiator to revoke access to the volume from.
    portalGroup: The name of the iSCSI portal group to stop exporting the volume in.
    volumeName: The name of the volume to export.
    '''


# TODO: figure out a way to validate that exactly one property is set
@JsonObject(
    setBaseName=maybe(iSCSICommandSetBaseName),
    createPortalGroup=maybe(iSCSICommandCreatePortalGroup),
    deletePortalGroup=maybe(iSCSICommandDeletePortalGroup),
    portalGroupAddNetwork=maybe(iSCSICommandPortalGroupAddNetwork),
    createPortal=maybe(iSCSICommandCreatePortal),
    deletePortal=maybe(iSCSICommandDeletePortal),
    createTarget=maybe(iSCSICommandCreateTarget),
    deleteTarget=maybe(iSCSICommandDeleteTarget),
    createInitiator=maybe(iSCSICommandCreateInitiator),
    deleteInitiator=maybe(iSCSICommandDeleteInitiator),
    initiatorAddNetwork=maybe(iSCSICommandInitiatorAddNetwork),
    export=maybe(iSCSICommandExport),
    exportDelete=maybe(iSCSICommandExportDelete),
)
class iSCSIConfigCommand(object):
    '''
    setBaseName: Set the StorPool cluster's iSCSI base name.
    createPortalGroup: Create an iSCSI portal group.
    deletePortalGroup: Delete a previously created iSCSI portal group.
    portalGroupAddNetwork: Add a CIDR network specification to a portal group.
    createPortal: Create an iSCSI portal.
    deletePortal: Delete a previously created iSCSI portal.
    createTarget: Create an iSCSI target for a StorPool volume.
    deleteTarget: Delete the iSCSI target for a StorPool volume.
    createInitiator: Define an iSCSI initiator that will connect to the cluster.
    deleteInitiator: Delete an iSCSI initiator definition.
    initiatorAddNetwork: Define a network that an iSCSI initiator will connect to the cluster on.
    export: Export a StorPool volume (with an already created target) via iSCSI.
    exportDelete: Stop exporting a StorPool volume via iSCSI.
    '''


@JsonObject(commands=[iSCSIConfigCommand])
class iSCSIConfigChange(object):
    '''
    commands: The actual iSCSI configuration commands.
    '''

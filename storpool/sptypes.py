#
#-
# Copyright (c) 2014, 2015  StorPool.
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
import re
from sputils import error, spTypeFun, maybe, const, either, eitherOr, internal
from spjson import JsonObject, dumps


### Simple validator functions ###
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
	
	return spTypeFun(argName, validator, '''{argName}, enumeration from {first} to {last}'''.format(argName=argName, first=first, last=end-1))

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
				error('{argName} is too long. Max allowed is {max}', argName=argName, max=size-1)
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


### Common constants ###
VOLUME_NAME_SIZE = 200
PLACEMENT_GROUP_NAME_SIZE = 128
VOLUME_NAME_REGEX = r'^\#?[A-Za-z0-9_\-.:]+$'
SNAPSHOT_NAME_REGEX = r'^\*?[A-Za-z0-9_\-.:@]+$'
PLACEMENT_GROUP_NAME_REGEX = r'^[A-Za-z0-9_\-]+$'
VOLUME_TEMPLATE_NAME_REGEX = r'^[A-Za-z0-9_\-]+$'
DISK_DESC_REGEX = r'^[A-Za-z0-9_\- ]{,30}$'

SECTOR_SIZE = 512
MAX_CHAIN_LENGTH = 6

MAX_CLIENT_DISKS = 1024
MAX_CLIENT_DISK = MAX_CLIENT_DISKS - 1
MAX_CLUSTER_DISKS = 4096
MAX_DISK_ID = MAX_CLUSTER_DISKS - 1

MAX_NET_ID = 3
MAX_NODE_ID = 63
MAX_PEER_ID = 0xffff
PEER_TYPE_CLIENT = 0x8000
PEER_SUBTYPE_CLIENT_AOE = 0xe000
PEER_SUBTYPE_MGMT = 0xf000
MAX_SERVER_ID = PEER_TYPE_CLIENT - 1
MAX_CLIENT_ID = PEER_SUBTYPE_CLIENT_AOE - PEER_TYPE_CLIENT - 1
MAX_AOE_TARGET_ID = PEER_SUBTYPE_MGMT - PEER_SUBTYPE_CLIENT_AOE - 1
MAX_MGMT_ID = MAX_PEER_ID - PEER_SUBTYPE_MGMT


### Simple type validators ###
MacAddr = regex('MAC Address', r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
PeerStatus = oneOf('PeerStatus', 'up', 'down')
ClientStatus = oneOf('ClientStatus', 'running', 'down')
ServerStatus = oneOf('ServerStatus', 'running', 'waiting', 'booting', 'down')
ClusterStatus = oneOf('ClusterStatus', 'running', 'waiting', 'down')

NetId = intRange('NetID', 0, MAX_NET_ID)
NodeId = intRange('NodeID', 0, MAX_NODE_ID)
PeerId = intRange('PeerID', 0, MAX_PEER_ID)
ClientId = intRange('ClientID', 1, MAX_CLIENT_ID)
ServerId = intRange('ServerID', 1, MAX_SERVER_ID)
MgmtId = intRange('MgmtID', 1, MAX_MGMT_ID)
AoeTargetId = intRange("AoeTargetID", 1, MAX_AOE_TARGET_ID)

DiskId = intRange('DiskID', 0, MAX_DISK_ID)
DiskDescription = regex('DiskDescritpion', DISK_DESC_REGEX)

SnapshotName = nameValidator("SnapshotName", SNAPSHOT_NAME_REGEX, VOLUME_NAME_SIZE, 'list', 'status')

VolumeName = nameValidator("VolumeName", VOLUME_NAME_REGEX, VOLUME_NAME_SIZE, 'list', 'status')
VolumeReplication = intRange('Replication', 1, 3)
VolumeSize = volumeSizeValidator("Size")
VolumeResize = volumeSizeValidator("SizeAdd")

PlacementGroupName = nameValidator("PlacementGroupName", PLACEMENT_GROUP_NAME_REGEX, PLACEMENT_GROUP_NAME_SIZE, 'list')
VolumeTemplateName = nameValidator("VolumeTemplateName", VOLUME_TEMPLATE_NAME_REGEX, VOLUME_NAME_SIZE, 'list')

Bandwidth = unlimitedInt('Bandwidth', 0, '-')
IOPS = unlimitedInt('IOPS', 0, '-')
AttachmentRights = oneOf('AttachmentRights', 'rw', 'ro')

ObjectState = namedEnum("ObjectState", "OBJECT_UNDEF OBJECT_OK OBJECT_OUTDATED OBJECT_IN_RECOVERY OBJECT_WAITING_FOR_VERSION OBJECT_WAITING_FOR_DISK OBJECT_DATA_NOT_PRESENT OBJECT_DATA_LOST OBJECT_WAINING_FOR_CHAIN OBJECT_WAIT_IDLE".split(' '))


### NETWORK ###
@JsonObject(mac=MacAddr)
class NetDesc(object):
	pass

@JsonObject(networks={NetId: NetDesc})
class PeerDesc(object):
	'''
	networks: List of the networks that StorPool communicates through on this node.
	'''


### SERVER ###
@JsonObject(nodeId=NodeId, version=str)
class Service(object):
	'''
	nodeId: The ID of the node on which the service is running.
	version: The version of the running StorPool service.
	'''
	@property
	def running(self):
		return self.status == 'running'

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

@JsonObject(id=AoeTargetId, status=ClientStatus)
class AoeTarget(Service):
	'''
	id: The ID of the service.
	status: The current status of the AoE target.
	'''

@JsonObject(clusterStatus=ClusterStatus, mgmt={MgmtId: Mgmt}, clients={ClientId: Client}, servers={ServerId: Server}, aoeTargets={AoeTargetId: AoeTarget})
class ClusterStatus(object):
	'''
	clusterStatus: The current status of the whole cluster. running - At least one running server; a cluster is formed. waiting - In quorum but negotiations between servers are not over yet. down - No quorum; most likely because more beacons are needed.
	'''
	pass


### CLIENT ###
@JsonObject(id=ClientId, generation=long, clientGeneration=long, configStatus=oneOf("client status", 'ok', 'updating', 'down'), delay=int)
class ClientConfigStatus(object):
	'''
	generation: The cluster generation based on the number of configuration changes since the cluster was created.
	clientGeneration: The generation of the specific client.
	configStatus: Whether there is an update of the configuration in progress.
	delay: The time it took for the client generation to reach the cluster generation. Only applicable to ClientConfigWait. Always 0 in ClientsConfigDump.
	'''


### AOE ###
AoeExportStatus = oneOf('AoeExportStatus', "OK", "down")

@JsonObject(name=either(VolumeName, SnapshotName), snapshot=bool, aoeId=str, target=eitherOr(AoeTargetId, None), status=AoeExportStatus)
class AoeExport(object):
	'''
	A single StorPool volume or snapshot exported over AoE.
	
	name: The name of the StorPool volume.
	snapshot: True if this entry describes a snapshot instead of a volume.
	aoeId: The AoE identifier that the volume is exported as.
	target: The StorPool node that serves as an AoE target to export this volume.
	status: The status of the StorPool AoE target node if target is set.
	'''

### TASK ###
@JsonObject(diskId=DiskId, transactionId=long, allObjects=int, completedObjects=int, dispatchedObjects=int, unresolvedObjects=internal(int))
class Task(object):
	'''
	diskId: The disk ID this task is on.
	transactionId: An ID associated with the currently running task. This ID is the same for all the tasks running on different disks but initiated by the same action (e.g. when reallocating a volume, all tasks associated with that volume will have the same ID).
	allObjects: The number of all the objects that the task is performing actions on.
	completedObjects: The number of objects that the task has finished working on.
	dispatchedObjects: Objects that the task has started working on.
	'''


### DISK ###
@JsonObject(objectId=internal(int), generation=long, version=long, volume=str, parentVolume=str, onDiskSize=int, storedSize=int, state=ObjectState,
	volumeId=internal(long))
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
		return self.state == OBJECT_OK

@JsonObject(name=str, storedSize=long, onDiskSize=long, objectsCount=long, objectStates={ObjectState:int})
class DiskVolumeInfo(object):
	'''
	objectsCount: The number of objects of the volume stored on this disk.
	objectStates: For each state, the number of objects that are in that state. 0-undefined 1-ok 2-outdated 3-in_recovery 4-waiting_for_version 5-waiting_for_disk 6-data_not_present 7-data_lost 8-waiting_for_chain 9-wait_idle
	onDiskSize: The space allocated on the disk for the object. This can go up to 32MB.
	storedSize: The size of the actual data in that object (<= onDiskSize).
	'''

@JsonObject(pages=int, pagesPending=int, maxPages=int, ios=int, bandwidth=eitherOr(int, None))
class DiskWbcStats(object):
	pass

@JsonObject(entries=int, space=int, total=int)
class DiskAggregateScores(object):
	pass

@JsonObject(id=DiskId, serverId=ServerId, generationLeft=long, model=str, serial=str, description=DiskDescription, softEject=oneOf('DiskSoftEjectStatus', "on", "off", "paused"))
class DiskSummaryBase(object):
	'''
	id: The ID of this disk. It is set when the disk is formatted to work with StorPool.
	serverId: The ID of the server this disk is currently on. In case the disk is currently down, the last known server ID is reported.
	generationLeft: The last cluster generation when the disk was active on a running server, or -1 if the disk is currently active.
	softEject: The status of the soft-eject process.
	description: A user-defined description of the disk for easier identification of the device.
	'''

class DownDiskSummary(DiskSummaryBase):
	up = False

@JsonObject(generationLeft=const(-1L), sectorsCount=long, empty=bool, ssd=bool, noFua=bool, isWbc=bool, device=str,
	agCount=internal(int), agAllocated=internal(int), agFree=internal(int), agFull=internal(int), agPartial=internal(int), agFreeing=internal(int), agMaxSizeFull=internal(int), agMaxSizePartial=internal(int),
	entriesCount=int, entriesAllocated=int, entriesFree=int,
	objectsCount=int, objectsAllocated=int, objectsFree=int, objectsOnDiskSize=long,
	wbc=eitherOr(DiskWbcStats, None), aggregateScore=DiskAggregateScores)
class UpDiskSummary(DiskSummaryBase):
	'''
	sectorsCount: The amount of 512-byte sectors on the disk.
	ssd: Whether the device is an SSD.
	noFua: Whether to issue FUA writes to this device.
	isWbc: Whether write-back cache is enabled for this device.
	device: The name of the physical disk device on the server.
	entriesAllocated: Used entries of the disk.
	objectsAllocated: Used objects of the disk.
	entriesFree: The remaining number of entries that can be stored on the disk.
	objectsFree: The remaining number of objects that can be stored on the disk.
	entriesCount: The maximum amount of entries that can exists on the disk.
	objectsCount: The maximum amount of object that can exists on the disk.
	empty: True if no volumes or snapshots are on this disk.
	objectsOnDiskSize: Total size occupied by objects. In essence, this is the estimated disk usage by StorPool.
	'''
	up = True

DiskSummary = either(UpDiskSummary, DownDiskSummary)


@JsonObject(objectStates={ObjectState:int}, volumeInfos={str:DiskVolumeInfo})
class DiskInfo(UpDiskSummary):
	'''
	For each state, the number of objects that are in that state. 0-undefined 1-ok 2-outdated 3-in_recovery 4-waiting_for_version 5-waiting_for_disk 6-data_not_present 7-data_lost 8-waiting_for_chain 9-wait_idle
	volumeInfos: Detailed information about the volumes that have data stored on the disk.
	'''

@JsonObject(objects={int:DiskObject})
class Disk(UpDiskSummary):
	'''
	objects: Detailed information about each object on the disk.
	'''

@JsonObject(description=DiskDescription)
class DiskDescUpdate(object):
	'''
	description: A user-defined description of the disk for easier identification of the device.
	'''


### ACTIVE REQUESTS ###
@JsonObject(requestId=str, requestIdx=int, volume=either(VolumeName, SnapshotName), address=long, size=int,
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

@JsonObject(aoeTargetId=AoeTargetId, requests=[ActiveRequestDesc])
class AoeTargetActiveRequests(object):
	'''
	requests: A detailed listing of all the requests associated with the given AoE target.
	'''


### PLACEMENT GROUP ###
@JsonObject(id=internal(int), name=PlacementGroupName, disks=set([DiskId]), servers=set([ServerId]))
class PlacementGroup(object):
	'''
	disks: IDs of the participating disks.
	servers: IDs of the participating servers.
	'''

@JsonObject(rename=maybe(PlacementGroupName), addServers=set([ServerId]), addDisks=set([DiskId]), rmServers=set([ServerId]), rmDisks=set([DiskId]))
class PlacementGroupUpdateDesc(object):
	'''
	rename: The new name of the placement group.
	addServers: IDs of the servers to add to this group. (This will add all the accessible disks of these servers)
	addDisks: IDs of the disks to add to this group.
	rmServers: IDs of the servers to be removed from this group.
	rmDisks: IDs of the disks to be removed from this group.
	'''


### VOLUME and SNAPSHOT ###
@JsonObject(bw=Bandwidth, iops=IOPS)
class VolumeLimits(object):
	'''
	bw: Bandwidth limit in KB.
	iops: iops limit.
	'''

@JsonObject(id=internal(long), parentName=eitherOr(SnapshotName, ""), templateName=eitherOr(VolumeTemplateName, ""),
	size=VolumeSize, replication=VolumeReplication,
	placeAll=PlacementGroupName, placeTail=PlacementGroupName,
	parentVolumeId=internal(long), originalParentVolumeId=internal(long), visibleVolumeId=long, templateId=internal(long),
	objectsCount=int, creationTimestamp=long, flags=internal(int))
class VolumeSummaryBase(VolumeLimits):
	'''
	parentName: The volume/snapshot's parent snapshot.
	templateName: The template that the volume/snapshot's settings are taken from.
	size: The volume/snapshots's size in bytes.
	replication: The number of copies/replicas kept.
	placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
	placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
	parentVolumeId: The ID of the parent snapshot.
	visibleVolumeId: The ID by which the volume/snapshot was created.
	objectsCount: The number of objects that the volume/snapshot is comprised of.
	'''

@JsonObject(name=VolumeName)
class VolumeSummary(VolumeSummaryBase):
	'''
	name: The name of this volume.
	'''

@JsonObject(name=SnapshotName, onVolume=VolumeName,
	autoName=bool, bound=bool, deleted=bool, transient=bool)
class SnapshotSummary(VolumeSummaryBase):
	'''
	name: The name of this snapshot
	onVolume: The name of the volume that this is a parent of.
	autoName: Is this snapshot anonymous.
	bound: Is this a bound snapshot. Bound snapshots are garbage-collected as soon as they remain childless and are no longer attached.
	deleted: Is this snapshot currently being deleted.
	transient: Is this a transient snapshot. Transient snapshots are internally created when cloning a volume. They cannot be attached as they may be garbage-collected at any time.
	'''

@JsonObject(storedSize=long, spaceUsed=long)
class SnapshotSpace(SnapshotSummary):
	'''
	storedSize: The number of bytes of client data on this snapshot. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
	spaceUsed: The number of bytes of client data that will be freed if this snapshot is deleted.
	'''

@JsonObject(disks=[DiskId], count=int)
class VolumeChainStat(object):
	'''
	disks: IDs of the disks.
	count: The number of objects on the disks.
	'''

@JsonObject(disksCount=int, objectsPerDisk={DiskId:int}, objectsPerChain=[VolumeChainStat], objectsPerDiskSet=[VolumeChainStat])
class VolumeInfo(VolumeSummary):
	pass

@JsonObject(disksCount=int, objectsPerDisk={DiskId:int}, objectsPerChain=[VolumeChainStat], objectsPerDiskSet=[VolumeChainStat])
class SnapshotInfo(SnapshotSummary):
	pass

@JsonObject(name=either(VolumeName, SnapshotName), size=VolumeSize, replication=VolumeReplication,
	status=oneOf("VolumeCurentStatus", "up", "up soon", "data lost", "down"), snapshot=bool, migrating=bool, decreasedRedundancy=bool, balancerBlocked=bool,
	storedSize=int, onDiskSize=int, syncingDataBytes=int, syncingMetaObjects=int, downBytes=int,
	downDrives=[DiskId], missingDrives=[DiskId], missingTargetDrives=[DiskId], softEjectingDrives=[DiskId])
class VolumeStatus(object):
	'''
	size: The volume's size in bytes.
	replication: The number of copies/replicas kept.
	status: up - The volume is operational. up soon - Synchronizing versions of objects after a disk has come back up. data lost - The last copy of some of the data in the volume has been lost. down - Some or all of the objects of the volume are missing and the volume is not in a state to continue serving operations.
	snapshot: True if this response describes a snapshot instead of a volume.
	migrating: True if there are tasks for reallocation of the volume.
	decreasedRedundancy: True if any of the replicas of the volume are missing.
	storedSize: The number of bytes of client data on the volume. This does not take into account the StorPool replication and overhead, thus it is never larger than the volume size.
	onDiskSize: The actual size that the objects of this volume occupy on the disks.
	syncingDataBytes: The total number of bytes in objects currently being synchronized (degraded objects or objects with not yet known version)
	syncingMetaObjects: The number of objects currently being synchronized (degraded objects or objects with not yet known version)
	downBytes: The number of bytes of the volume that are not accessible at the moment.
	downDrives: The IDs of the drives that are not accessible at the moment but needed by this volume. The volume will be in the 'down' status until all or some of these drives reappear.
	missingDrives: The IDs of the drives that are not accessible at the moment. The volume has all the needed data on the rest of the disks and can continue serving requests but it is in the 'degraded' status.
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

@JsonObject(placeAll=maybe(PlacementGroupName), placeTail=maybe(PlacementGroupName), replication=maybe(VolumeReplication), bw=maybe(Bandwidth), iops=maybe(IOPS))
class VolumePolicyDesc(object):
	'''
	placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
	placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
	bw: Bandwidth limit in KB.
	iops: iops limit.
	replication: The number of copies/replicas kept.
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

@JsonObject(name=maybe(VolumeName), bind=maybe(bool))
class VolumeSnapshotDesc(object):
	'''
	name: The name of the newly created snapshot. If not specified, a name will be auto-generated by the StorPool management service.
	bind: If true, the lifetime of the newly created snapshot will be bound to the lifetime of its children. As soon as it remains childless the snapshot will be garbage-collected.
	'''

@JsonObject(rename=maybe(VolumeName), bind=maybe(bool))
class SnapshotUpdateDesc(VolumePolicyDesc):
	'''
	rename: The new name to be set.
	bind: When true bind this snapshot, when false - unbind it. If not set or missing - no change.
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


### VOLUME RIGHTS ###
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

@JsonObject(volume=VolumeName, snapshot=bool, client=ClientId, rights=AttachmentRights, pos=AttachmentPos)
class AttachmentDesc(object):
	'''
	snapshot: Whether it is a snapshot or a volume.
	client: The ID of the client on which it is attached.
	rights: Whether the volume is attached as read only or read/write; always ro for snapshots.
	pos: The attachment position on the client; used by the StorPool client to form the name of the internal /dev/spN device node.
	'''


### VOLUME TEMPLATES ###
@JsonObject(id=internal(int), name=VolumeTemplateName, parentName=eitherOr(SnapshotName, ""), placeAll=PlacementGroupName, placeTail=PlacementGroupName,
	size=eitherOr(VolumeSize, "-"), replication=eitherOr(VolumeReplication, "-"))
class VolumeTemplateDesc(VolumeLimits):
	'''
	name: The name of the template.
	parentName: The name of the snapshot on which volumes will be based.
	placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
	placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
	size: A default size for the volumes (in bytes).
	replication: A default number of copies to be kept by StorPool.
	'''

@JsonObject(id=internal(int), name=VolumeTemplateName, placeAll=PlacementGroupName, placeTail=PlacementGroupName, replication=eitherOr(VolumeReplication, "-"),
	volumesCount=int, snapshotsCount=int, removingSnapshotsCount=int,
	size=eitherOr(VolumeSize, 0), totalSize=eitherOr(VolumeSize, 0), onDiskSize=long, storedSize=long,
	availablePlaceAll=long, availablePlaceTail=long)
class VolumeTemplateStatusDesc(object):
	'''
	name: The name of the template.
	placeAll: The name of a placement group which describes the disks to be used for all but the last replica.
	placeTail: The name of a placement group which describes the disks to be used for the last replica, the one used for reading.
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
	'''

@JsonObject(name=VolumeTemplateName, parent=maybe(SnapshotName), size=maybe(VolumeSize))
class VolumeTemplateCreateDesc(VolumePolicyDesc):
	'''
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


### VOLUME RELOCATOR and BALANCER ###
@JsonObject(status=oneOf("RelocatorStatus", 'on', 'off', 'blocked'))
class VolumeRelocatorStatus(object):
	pass

@JsonObject(status=oneOf("BalancerStatus", 'nothing to do', 'blocked', 'waiting', 'working', 'ready', 'commiting'), auto=bool)
class VolumeBalancerStatus(object):
	pass

@JsonObject(cmd=oneOf("BalancerCommand", 'start', 'stop', 'commit', 'auto'))
class VolumeBalancerCommand(object):
	pass

@JsonObject(name=either(VolumeName, SnapshotName),
	placeAll=PlacementGroupName, placeTail=PlacementGroupName, replication=VolumeReplication,
	size=long, objectsCount=int,
	snapshot=bool, reallocated=bool, blocked=bool)
class VolumaBalancerVolumeStatus(object):
	pass

@JsonObject(currentDiskSets=[[DiskId]], balancerDiskSets=[[DiskId]])
class VolumeBalancerVolumeDiskSets(VolumaBalancerVolumeStatus):
	pass

@JsonObject(current=int, target=int, delta=int)
class TargetDesc(object):
	pass

@JsonObject(id=DiskId, serverId=ServerId, generationLeft=long)
class DownDiskTarget(object):
	pass

@JsonObject(id=DiskId, serverId=ServerId, generationLeft=const(-1L),
	objectsAllocated=TargetDesc, objectsCount=int, objectsToRecover=int,
	storedSize=TargetDesc, onDiskSize=TargetDesc)
class UpDiskTarget(object):
	pass

DiskTarget = either(UpDiskTarget, DownDiskTarget)

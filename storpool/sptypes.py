#
#-
# Copyright (c) 2014  StorPool.
# All rights reserved.
#
import re
from sputils import error, spTypeFun, maybe, const, either, eitherOr
from spjson import JsonObject


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
			error("Invalid {argName}: {value}. Must be on of {accepted}", argName=argName, value=value, accepted=accepted)
		else:
			return value
	
	return spTypeFun(argName, validator, '''One of {{{accepted}}}'''.format(accepted=", ".join(map(str, accepted))))

def intRange(argName, min, max):
	def validator(i):
		try:
			i = int(i)
			
			if i < min or i > max:
				error('Ivalid {argName}. Must be between {min} and {max}', argName=argName, min=min, max=max)
			
			return i
		except ValueError:
			error('Invalid {argName}. Must be integer', argName=argName)
	
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
			error("Invalid {argName}. Must be integer")
	
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
	
	return spTypeFun(argName, validator, '''positive integer or '{unlimited}' for unlimited'''.format(unlimited=unlimited))

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
			error('Invalid {argName}. Must be string', argName=argName)
	
	return spTypeFun(argName, validator, '''string({size}), matching {regex}, except {{{blacklisted}}}'''.format(size=size, regex=regex, blacklisted=", ".join(map(str, blacklisted))))

def volumeSizeValidator(argName):
	def validator(size):
		try:
			size = int(size)
			if size < 1:
				error('Invalid {argName} {size}. Must be positive', argName=argName, size=size)
			elif size % SECTOR_SIZE:
				error('Invalid {argName} {size}. Must be multiple of {sectorSize}', argName=argName, size=size, sectorSize=SECTOR_SIZE)
			else:
				return size
		except ValueError:
			error('Non-numeric {argName}: {size}', argName=argName, size=size)
	
	return spTypeFun(argName, validator, '''positive integer, divisible by {sectorSize}'''.format(sectorSize=SECTOR_SIZE))


### Common constants ###
VOLUME_NAME_SIZE = 200
PLACEMENT_GROUP_NAME_SIZE = 128
VOLUME_NAME_REGEX = r'^[A-Za-z0-9_\-.:]+$'
SNAPSHOT_NAME_REGEX = r'^[A-Za-z0-9_\-.@:]+$'
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
MAX_PEER_ID = 65535
MAX_SERVER_ID = 0x8000
MAX_CLIENT_ID = 0x8000
PEER_CTL = 0xffff


### Simple type validators ###
MacAddr = regex('MAC Address', r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$')
PeerStatus = oneOf('PeerStatus', 'up', 'down')
ClientStatus = oneOf('ClientStatus', 'running', 'down')
ServerStatus = oneOf('ServerStatus', 'running', 'waiting', 'booting', 'down')

NetId = intRange('NetID', 0, MAX_NET_ID)
NodeId = intRange('NodeID', 0, MAX_NODE_ID)
PeerId = intRange('PeerID', 0, MAX_PEER_ID)
ClientId = intRange('CientID', 1, MAX_CLIENT_ID)
ServerId = intRange('ServerID', 1, MAX_SERVER_ID)
MgmtId = const(PEER_CTL)

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
	pass


### SERVER ###
@JsonObject(nodeId=NodeId, version=str)
class Service(object):
	@property
	def running(self):
		return self.status == 'running'

@JsonObject(id=ServerId, status=ServerStatus, missingDisks=[DiskId], pendingDisks=[DiskId])
class Server(Service):
	pass

@JsonObject(id=ClientId, status=ClientStatus)
class Client(Service):
	pass

@JsonObject(id=MgmtId, status=ClientStatus)
class Mgmt(Service):
	pass

@JsonObject(mgmt=Mgmt, clients={ClientId: Client}, servers={ServerId: Server})
class ClusterStatus(object):
	pass


### CLIENT ###
@JsonObject(id=ClientId, generation=long, clientGeneration=long, configStatus=oneOf("client status", 'ok', 'updating', 'down'), delay=int)
class ClientConfigStatus(object):
	pass


### TASK ###
@JsonObject(diskId=DiskId, transactionId=long, allObjects=int, completedObjects=int, dispatchedObjects=int, unresolvedObjects=int)
class Task(object):
	pass


### DISK ###
@JsonObject(objectId=int, generation=long, version=long, volume=str, parentVolume=str, onDiskSize=int, storedSize=int, state=ObjectState,
	volumeId=long)
class DiskObject(object):
	@property
	def ok(self):
		return self.state == OBJECT_OK

@JsonObject(name=str, storedSize=long, onDiskSize=long, objectsCount=long, objectStates={ObjectState:int})
class DiskVolumeInfo(object):
	pass

@JsonObject(id=DiskId, serverId=ServerId, generationLeft=long, sectorsCount=long, empty=bool, ssd=bool, softEject=oneOf('DiskSoftEjectStatus', "on", "off", "paused"),
	device=str, model=str, serial=str, description=DiskDescription,
	agCount=int, agAllocated=int, agFree=int, agFull=int, agPartial=int, agFreeing=int, agMaxSizeFull=int, agMaxSizePartial=int,
	entriesCount=int, entriesAllocated=int, entriesFree=int,
	objectsCount=int, objectsAllocated=int, objectsFree=int, objectsOnDiskSize=long)
class DiskSummary(object):
	@property
	def ok(self):
		return self.generationLeft == -1

@JsonObject(objectStates={ObjectState:int}, volumeInfos={str:DiskVolumeInfo})
class DiskInfo(DiskSummary):
	pass

@JsonObject(objects={int:DiskObject})
class Disk(DiskSummary):
	pass

@JsonObject(description=DiskDescription)
class DiskDescUpdate(object):
	pass


### ACTIVE REQUESTS ###
@JsonObject(requestId=str, requestIdx=int, volumeId=long, address=long, size=int,
	op=oneOf('RequestOp', "read", "write", "merge", "system", "entries flush", "#bad_state", "#bad_drOp"), state=str, prevState=str, drOp=str, msecActive=int)
class ActiveRequestDesc(object):
	pass

@JsonObject(clientId=ClientId, requests=[ActiveRequestDesc])
class ClientActiveRequests(object):
	pass

@JsonObject(diskId=DiskId, requests=[ActiveRequestDesc])
class DiskActiveRequests(object):
	pass


### PLACEMENT GROUP ###
@JsonObject(id=int, name=PlacementGroupName, disks=set([DiskId]), servers=set([ServerId]))
class PlacementGroup(object):
	pass

@JsonObject(rename=maybe(PlacementGroupName), addServers=set([ServerId]), addDisks=set([DiskId]), rmServers=set([ServerId]), rmDisks=set([DiskId]))
class PlacementGroupUpdateDesc(object):
	pass


### VOLUME and SNAPSHOT ###
@JsonObject(bw=Bandwidth, iops=IOPS)
class VolumeLimits(object):
	pass

@JsonObject(id=long, name=VolumeName, parentName=eitherOr(SnapshotName, ""), templateName=eitherOr(VolumeTemplateName, ""),
	size=VolumeSize, replication=VolumeReplication,
	placeAll=PlacementGroupName, placeTail=PlacementGroupName,
	parentVolumeId=long, originalParentVolumeId=long, visibleVolumeId=long,
	objectsCount=int, creationTimestamp=long, flags=int)
class VolumeSummary(VolumeLimits):
	pass

@JsonObject(onVolume=VolumeName)
class SnapshotSummary(VolumeSummary):
	pass

@JsonObject(disks=[DiskId], count=int)
class VolumeChainStat(object):
	pass

@JsonObject(disksCount=int, objectsPerDisk={DiskId:int}, objectsPerChain=[VolumeChainStat], objectsPerDiskSet=[VolumeChainStat])
class VolumeInfo(VolumeSummary):
	pass

@JsonObject(name=VolumeName, size=VolumeSize, replication=VolumeReplication,
	status=str, migrating=bool, decreasedRedundancy=bool, balancerBlocked=bool,
	storedSize=int, onDiskSize=int, syncingDataBytes=int, syncingMetaObjects=int, downBytes=int,
	downDrives=[DiskId], missingDrives=[DiskId], missingTargetDrives=[DiskId], softEjectingDrives=[DiskId])
class VolumeStatus(object):
	pass

@JsonObject(targetDiskSets=[[DiskId]], objects=[[DiskId]])
class Volume(VolumeSummary):
	pass

@JsonObject(placeAll=maybe(PlacementGroupName), placeTail=maybe(PlacementGroupName), replication=maybe(VolumeReplication), bw=maybe(Bandwidth), iops=maybe(IOPS))
class VolumePolicyDesc(object):
	pass

@JsonObject(name=VolumeName, size=VolumeSize, parent=maybe(SnapshotName), template=maybe(VolumeTemplateName))
class VolumeCreateDesc(VolumePolicyDesc):
	pass

@JsonObject(rename=maybe(VolumeName), size=maybe(VolumeSize), sizeAdd=maybe(VolumeResize), template=maybe(VolumeTemplateName))
class VolumeUpdateDesc(VolumePolicyDesc):
	pass

@JsonObject(name=maybe(VolumeName))
class VolumeSnapshotDesc(object):
	pass

@JsonObject(parentName=maybe(SnapshotName))
class VolumeRebaseDesc(object):
	pass


### VOLUME RIGHTS ###
DetachClientsList = eitherOr([ClientId], "all")
AttachmentPos = intRange('AttachmentPos', 0, MAX_CLIENT_DISK)

@JsonObject(volume=VolumeName, detach=maybe(DetachClientsList), ro=maybe([ClientId]), rw=maybe([ClientId]), force=False)
class VolumeReassignDesc(object):
	pass

@JsonObject(snapshot=SnapshotName, detach=maybe(DetachClientsList), ro=maybe([ClientId]), force=False)
class SnapshotReassignDesc(object):
	pass

@JsonObject(volume=VolumeName, snapshot=bool, client=ClientId, rights=AttachmentRights, pos=AttachmentPos)
class AttachmentDesc(object):
	pass


### VOLUME TEMPLATES ###
@JsonObject(name=VolumeTemplateName, parentName=eitherOr(SnapshotName, ""), placeAll=PlacementGroupName, placeTail=PlacementGroupName,
	size=eitherOr(VolumeSize, "-"), replication=eitherOr(VolumeReplication, "-"))
class VolumeTemplateDesc(VolumeLimits):
	pass

@JsonObject(name=VolumeTemplateName, parent=maybe(SnapshotName), size=maybe(VolumeSize))
class VolumeTemplateCreateDesc(VolumePolicyDesc):
	pass

@JsonObject(rename=maybe(VolumeTemplateName), parent=maybe(SnapshotName), size=maybe(VolumeSize))
class VolumeTemplateUpdateDesc(VolumePolicyDesc):
	pass


### VOLUME RELOCATOR ###
@JsonObject(status=oneOf("RelocatorStatus", 'on', 'off', 'blocked'))
class VolumeRelocatorStatus(object):
	pass

### VOLUME BALANCER ###
@JsonObject(status=oneOf("BalancerStatus", 'on', 'off', 'blocked'))
class VolumeBalancerStatus(object):
	pass

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
import httplib as http
import json as js

import spjson as js
import sptypes as sp

from sputils import msec, sec, pathPollWait, spType, either, const
from spdoc import ApiDoc, ApiCallDoc


SP_DEV_PATH   = '/dev/storpool/'
SP_API_PREFIX = '/ctrl/1.0'


class _API_ARG(object):
	def __init__(self, name, validate):
		self._name = name
		self._type = spType(validate)

DiskId = _API_ARG('diskId', sp.DiskId)
ServerId = _API_ARG('serverId', sp.ServerId)
ClientId = _API_ARG('clientId', sp.ClientId)
AoeTargetId = _API_ARG('aoeTargetId', sp.AoeTargetId)
VolumeName = _API_ARG('volumeName', sp.VolumeName)
SnapshotName = _API_ARG('snapshotName', sp.SnapshotName)
PlacementGroupName = _API_ARG('placementGroupName', sp.PlacementGroupName)
VolumeTemplateName = _API_ARG('templateName', sp.VolumeTemplateName)


class _API_METHOD(object):
	def __init__(self, method, query, args, json, returns):
		self.method = method
		self.path = "{pref}/{query}".format(pref=SP_API_PREFIX, query=query)
		self.args = args
		self.json = spType(json) if json is not None else None
		self.returns = spType(returns)
		self.types = {}
	
	def addType(self, name, desc):
		self.types.update({name: desc})
	
	def doc(self, name, desc):
		self.spDoc = ApiCallDoc(name, desc, self.method, self.path, dict((arg._name, arg._type.spDoc) for arg in self.args), self.json.spDoc if self.json else None, self.returns.spDoc)
		return self
	
	def compile(self):
		method, path, args, json, returns = self.method, self.path, self.args, self.json, self.returns
		
		args = list(args)
		if json is not None:
			args.append(_API_ARG('json', json))
		
		commas = lambda xs: ", ".join(xs)
		fmtEq = lambda x: "{x}={x}".format(x=x)
		
		ftext  = 'def func(self, {args}):\n'.format(args=commas(arg._name for arg in args))
		for arg in args:
			ftext += '    {arg} = _validate_{arg}({arg})\n'.format(arg=arg._name)
		
		ftext += '    path = "{path}"'.format(path=path)
		if args:
			ftext += '.format({args})\n'.format(args=commas(fmtEq(arg._name) for arg in args))
		ftext += '\n'
		
#		ftext += '    print "Query: {0}".format(path)\n'
		ftext += '    res = self("{method}", path, {json})\n'.format(method=method, json=None if json is None else 'json')
		ftext += '    return returns(res)'
#		print ftext
		
		globalz = dict(("_validate_{0}".format(arg._name), arg._type.handleVal) for arg in args)
		globalz['returns'] = returns.handleVal
		
		exec ftext in globalz
		func = globalz['func']
		del globalz['func']
		
		
		doc = "HTTP: {method} {path}\n\n".format(method=method, path=path)
		
		if args:
			doc += "    Arguments:\n"
			for arg in args:
				doc += "        {argName}: {argType}\n".format(argName=arg._name, argType=arg._type.name)
			doc += "\n"
		
		if returns is not None:
			doc += "    Returns: {res}\n".format(res=returns.name)
		
#		print doc
		func.__doc__ = doc
		func.spDoc = self.spDoc
		
		return func

def GET(query, *args, **kwargs):
	assert 'json' not in kwargs, 'GET requests currently do not accept JSON objects'
	assert 'returns' in kwargs, 'GET requests must specify a return type'
	return _API_METHOD('GET', query, args, None, kwargs['returns'])

def POST(query, *args, **kwargs):
	return _API_METHOD('POST', query, args, kwargs.get('json', None), kwargs.get('returns', ApiOk))


@js.JsonObject(ok=const(True), generation=long)
class ApiOk(object):
	'''
	ok: Always returns true. If something goes wrong, an ApiError is returned instead.
	generation: The cluster generation based on the number of configuration changes since the cluster was created.
	'''

@js.JsonObject(autoName=sp.maybe(sp.SnapshotName))
class ApiOkVolumeCreate(ApiOk):
	'''
	autoName: The name of the transient snapshot used during the creation of the volume.
	'''

class ApiError(Exception):
	def __init__(self, status, json):
		super(ApiError, self).__init__()
		self.status = status
		self.json = json
		self.name = json['error'].get('name', "<Missing error name>")
		self.desc = json['error'].get('descr', "<Missing error description>")
	
	def __str__(self):
		return "{0}: {1}".format(self.name, self.desc)

class ApiMeta(type):
	def spDocSection(cls, name, desc):
		cls.spDoc.addSection(name, desc)
	
	def __setattr__(cls, name, func):
		cls.spDoc.addCall(func.spDoc)
		
		func = func.compile()
		func.__name__ = func.func_name = name
		func.__module__ = __name__
		type.__setattr__(cls, name, func)

class Api(object):
	'''StorPool API abstraction'''
	__metaclass__ = ApiMeta
	spDoc = ApiDoc(
		"""StorPool API Reference""",
		"""
		Copyright (c) 2014-2015 StorPool. All rights reserved.
		
		This reference document describes the StorPool API version 15.02 and
		the supported API calls.
		"""
	)
	
	def __init__(self, host='127.0.0.1', port=80, auth='', timeout=10):
#		print host, port, auth
		self._host = host
		self._port = port
		self._timeout = timeout
		self._authHeader = {"Authorization": "Storpool v1:" + str(auth)}
	
	def __call__(self, method, path, json=None):
		if json is not None:
			json = js.dumps(json)
		
		try:
			conn = http.HTTPConnection(self._host, self._port, self._timeout)
			request = conn.request(method, path, json, self._authHeader)
			response = conn.getresponse()
			status, json = response.status, js.load(response)
			
			if status != http.OK or 'error' in json:
#				print status, json
				raise ApiError(status, json)
			else:
#				print json
				return json['data']
		finally:
			conn.close()
	
	def volumeDevLinkWait(self, volumeName, attach, pollTime=200*msec, maxTime=60*sec):
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
	>>>import spapi
	>>>api=spapi.Api('192.168.0.5', 80, '1556560560218011653')
	>>>a.peersList()
	
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
	
	The calls that may be used may be found in the file spapi.py
	
	Note: Requests will sometimes use GET instead of POST and consequently,
	will not require JSON. Responses on the other hand always produce JSON content.
	"""
	)

Api.spDocSection("Peers", """ """)
Api.peersList = GET('NetworkPeersList', returns={sp.PeerId: sp.PeerDesc}).doc("List the network peers",
	"""
	List the network nodes running the StorPool beacon including information
	such as the ID of the node,
	the networks it communicates through and the corresponding MAC addresses.
	"""
	)

Api.spDocSection("Tasks", """ """)
Api.tasksList = GET('TasksList', returns=[sp.Task]).doc("List tasks",
	"""
	List the currently active recovery tasks. This call will return JSON
	data only when there is a relocation in progress. Under normal operation
	of the cluster it will return no data.
	"""
	)

Api.spDocSection("Services", """ """)
Api.servicesList = GET('ServicesList', returns=sp.ClusterStatus).doc("List all StorPool services",
	"""
	List all the services in the cluster (StorPool servers, clients, management, etc).
	If the whole cluster is
	not operational this call will return an error.
	"""
	)
Api.serversListBlocked = GET('ServersListBlocked', returns=sp.ClusterStatus).doc("List all blocked StorPool servers",
	"""
	List the currently active StorPool servers even before the cluster has become
	operational, along with information about any missing disks that the cluster
	is waiting for.
	"""
	)

Api.spDocSection("Servers", """ """)
#Api.serversList = GET('ServersList', returns=sp.ClusterStatus).doc("List all Storpool servers",
#	"""
#	Returns the the same output as ServicesList but ommits clients. Returns
#	an error if the whole cluster is not operational.
#	"""
#	)
Api.serverDisksList = GET('ServerDisksList/{serverId}', ServerId, returns={sp.DiskId: sp.DiskSummary}).doc("List all disks on a server",
	"""
	Return detailed information about each disk on the given server.
	"""
	)
Api.serverDiskDescribe = GET('ServerDiskDescribe/{serverId}/{diskId}', ServerId, DiskId, returns=sp.Disk).doc("Describe a disk on a server",
	"""
	Return detailed information about a disk on the given server and the
	objects on it.
	"""
	)

Api.spDocSection("Clients", """ """)
Api.clientsConfigDump = GET('ClientsConfigDump', returns=[sp.ClientConfigStatus]).doc("Get the current status of all the clients",
	"""
	Return the status of each client including its current generation and
	generation update status.
	"""
	)
Api.clientConfigWait = GET('ClientConfigWait/{clientId}', ClientId, returns=[sp.ClientConfigStatus]).doc("Wait until a client updates to the current configuration",
	"""
	Return the same JSON as ClientsConfigDump but block until the client
	has updated its configuration information to the current generation at
	the time of the request.
	"""
	)
Api.clientActiveRequests = GET('ClientActiveRequests/{clientId}', ClientId, returns=sp.ClientActiveRequests).doc("List all the active requests on a client",
	"""
	List detailed information about the requests being currently processed on
	the given client.
	"""
	)

Api.spDocSection("AoE Targets", """ """)
Api.aoeStatus = GET('AoeStatus', returns=[sp.AoeExport]).doc("Display AoE status",
	"""
	List the StorPool volumes and snapshots exported over AoE.
	"""
	)
Api.aoeExportVolume = POST('AoeExportVolume/{volumeName}', VolumeName).doc("Export a volume",
	"""
	Export the specified volume over AoE.
	"""
	)
Api.aoeExportSnapshot = POST('AoeExportSnapshot/{snapshotName}', SnapshotName).doc("Unexport a volume",
	"""
	Export the specified snapshot over AoE.
	"""
	)
Api.aoeUnexportVolume = POST('AoeUnexportVolume/{volumeName}', VolumeName).doc("Export a snapshot",
	"""
	Stop exporting the specified volume over AoE.
	"""
	)
Api.aoeUnexportSnapshot = POST('AoeUnexportSnapshot/{snapshotName}', SnapshotName).doc("Unexport a snaphot",
	"""
	Stop exporting the specified snapshot over AoE.
	"""
	)
Api.aoeTargetActiveRequests = GET('AoeTargetActiveRequests/{aoeTargetId}', AoeTargetId, returns=sp.AoeTargetActiveRequests).doc("List all active requests on an AoE target",
	"""
	List detailed information about the requests being currently processed on
	the given AoE target
	"""
	)

Api.spDocSection("Disks", """ """)
Api.disksList = GET('DisksList', returns={sp.DiskId: sp.DiskSummary}).doc("List all disks", """ """)
Api.diskDescribe = GET('DiskDescribe/{diskId}', DiskId, returns=sp.Disk).doc("Describe a disk",
	"""
	List all disks including detailed information about the objects on each disk.
	"""
	)
Api.diskInfo = GET('DiskGetInfo/{diskId}', DiskId, returns=sp.DiskInfo).doc("Get disk info",
	"""
	List all disks including information about the volumes stored on each disk.
	"""
	)
Api.diskEject = POST('DiskEject/{diskId}', DiskId).doc("Eject a disk",
	""" Stop operations on the given disk even if it is not empty. """
	)
Api.diskForget = POST('DiskForget/{diskId}', DiskId).doc("Forget a disk",
	""" Remove the disk from any placement groups or volumes that it is used in. """
	)
Api.diskIgnore = POST('DiskIgnore/{diskId}', DiskId).doc("Ignore a disk",
	""" Try to boot the cluster by ignoring this disk. """
	)
Api.diskSoftEject = POST('DiskSoftEject/{diskId}', DiskId).doc("Soft-eject a disk",
	""" Stop writes to the given disk and start relocating all the data stored on it to other disks. """
	)
Api.diskSoftEjectPause = POST('DiskSoftEjectPause/{diskId}', DiskId).doc("Pause a disk's soft-eject operation",
	""" Temporarily pause the relocation tasks for the disk. This can be helpful in heavy load situations. """
	)
Api.diskSoftEjectCancel = POST('DiskSoftEjectCancel/{diskId}', DiskId).doc("Cancel a disk's soft-eject operation",
	""" Stop the relocation tasks for the disk and mark it as usable again. After this operation data will be moved back to the disk. """
	)
Api.diskSetDesc = POST('DiskSetDescription/{diskId}', DiskId, json=sp.DiskDescUpdate).doc("Set a disk's description", """ """)
Api.diskActiveRequests = GET('DiskActiveRequests/{diskId}', DiskId, returns=sp.DiskActiveRequests).doc("List all the active requests on a disk",
	"""
	List detailed information about the requests being currently processed
	on the given disk.
	"""
	)

Api.spDocSection("Volumes", """ """)
Api.volumesList = GET('VolumesList', returns=[sp.VolumeSummary]).doc("List all volumes",
	""" Return configuration information about all the volumes. """
	)
Api.volumesStatus = GET('VolumesGetStatus', returns={either(sp.VolumeName, sp.SnapshotName): sp.VolumeStatus}).doc("Get volume and snapshot status",
	""" Return the status of each volume and snapshot. """
	)
Api.volumeList = GET('Volume/{volumeName}', VolumeName, returns=[sp.VolumeSummary]).doc("List a single volume",
	""" Same as VolumeList but only return information about a given volume. """
	)
Api.volumeDescribe = GET('VolumeDescribe/{volumeName}', VolumeName, returns=sp.Volume).doc("Describe a volume",
	"""
	Return detailed information about the distribution of the volume's data on
	the disks.
	"""
	)
Api.volumeInfo = GET('VolumeGetInfo/{volumeName}', VolumeName, returns=sp.VolumeInfo).doc("Get volume info",
	"""
	Return general information about the distribution of the volume's data on
	the disks.
	"""
	)
Api.volumeListSnapshots = GET('VolumeListSnapshots/{volumeName}', VolumeName, returns=[sp.SnapshotSummary]).doc("List the parent snapshots of a volume",
	"""
	List a volume's parent snapshots in the same format as
	VolumeList
	"""
	)
Api.volumeCreate = POST('VolumeCreate', json=sp.VolumeCreateDesc, returns=ApiOkVolumeCreate).doc("Create a new volume", """ """)
Api.volumeUpdate = POST('VolumeUpdate/{volumeName}', VolumeName, json=sp.VolumeUpdateDesc).doc("Update a volume",
	""" Alter the configuration of an existing volume. """
	)
Api.volumeFreeze = POST('VolumeFreeze/{volumeName}', VolumeName).doc("Freeze a volume",
	""" Convert the volume to a snapshot """
	)
Api.volumeRebase = POST('VolumeRebase/{volumeName}', VolumeName, json=sp.VolumeRebaseDesc).doc("Rebase a volume",
	"""
	Change the parent of the volume by choosing from the ones higher in
	the hierarchy or by rebasing it to no parent.
	"""
	)
Api.volumeAbandonDisk = POST('VolumeAbandonDisk/{volumeName}', VolumeName, json=sp.AbandonDiskDesc).doc("Abandon disk",
	"""
	"""
	)
Api.volumeDelete = POST('VolumeDelete/{volumeName}', VolumeName).doc("Delete a volume", """ """)

Api.spDocSection("Snapshots",
	"""
	Snapshots in their essence are very similar to volumes in the sense
	that many operations supported by volumes are also supported by
	snapshots (all except write-related operations). They can not be
	modified and play an essential role in copy-on-write scenarios.
	"""
	)
Api.snapshotsList = GET('SnapshotsList', returns=[sp.SnapshotSummary]).doc("List all snapshots",
	"""
	List all the snapshots in the cluster in the same
	format as VolumeList.
	"""
	)
Api.snapshotsSpace = GET('SnapshotsSpace', returns=[sp.SnapshotSpace]).doc("List snapshots space estimations",
	"""
	List estimated virtual space used by each snapshot.
	"""
	)
Api.snapshotList = GET('Snapshot/{snapshotName}', SnapshotName, returns=[sp.SnapshotSummary]).doc("List a single snapshot",
	""" Same as SnapshotList but only return information about a given snapshot. """
	)
Api.snapshotDescribe = GET('SnapshotDescribe/{snapshotName}', SnapshotName, returns=sp.Snapshot).doc("Describe a snapshot",
	"""
	Return detailed information about the distribution of the snapshot's data on the
	disks.
	"""
	)
Api.snapshotInfo = GET('SnapshotGetInfo/{snapshotName}', SnapshotName, returns=sp.SnapshotInfo).doc("Get snapshot info",
	"""
	Return general information about the distribution of the snapshot's data on the
	disks.
	"""
	)
Api.snapshotCreate = POST('VolumeSnapshot/{volumeName}', VolumeName, json=sp.VolumeSnapshotDesc, returns=ApiOkVolumeCreate).doc("Snapshot a volume",
	"""
	Create a snapshot of the given volume; the snapshot becomes the parent of
	the volume.
	"""
	)
Api.snapshotUpdate = POST('SnapshotUpdate/{snapshotName}', SnapshotName, json=sp.SnapshotUpdateDesc).doc("Update a snapshot",
	""" Alter the configuration of an existing snapshot. """
	)
Api.snapshotRebase = POST('SnapshotRebase/{snapshotName}', SnapshotName, json=sp.VolumeRebaseDesc).doc("Rebase a snapshot",
	"""
	Change the parent of the snapshot by choosing from the ones higher in
	the hierarchy or by rebasing it to no parent.
	"""
	)
Api.snapshotAbandonDisk = POST('VolumeAbandonDisk/{snapshotName}', SnapshotName, json=sp.AbandonDiskDesc).doc("Abandon disk",
	"""
	"""
	)
Api.snapshotDelete = POST('SnapshotDelete/{snapshotName}', SnapshotName).doc("Delete a snapshot", """ """)

Api.spDocSection("Attachments", """""")
Api.attachmentsList = GET('AttachmentsList', returns=[sp.AttachmentDesc]).doc("List all attachments",
	"""
	List the volumes and snapshots currently attached to clients along with
	the read/write rights of each attachment.
	"""
	)
Api.volumesReassign = POST('VolumesReassign', json=[either(sp.VolumeReassignDesc, sp.SnapshotReassignDesc)]).doc("Reassign volumes and/or snapshots",
	""" Perform bulk attach/detach and attachment rights modification. """
	)

Api.spDocSection("Placement Groups",
	"""
	Placement groups provide a way to specify the disks on which a volume's data
	should be stored.
	"""
	)
Api.placementGroupsList = GET('PlacementGroupsList', returns={sp.PlacementGroupName: sp.PlacementGroup}).doc("List all placement groups", """ """)
Api.placementGroupDescribe = GET('PlacementGroupDescribe/{placementGroupName}', PlacementGroupName, returns=sp.PlacementGroup).doc("Describe a single placement group",
	"""
	Same as PlacementGroupsList but only return information about a given group.
	"""
	)
Api.placementGroupUpdate = POST('PlacementGroupUpdate/{placementGroupName}', PlacementGroupName, json=sp.PlacementGroupUpdateDesc).doc("Create and/or update a placement group",
	"""
	If a group by the specified name does not exist, it will be created.
	"""
	)
Api.placementGroupDelete = POST('PlacementGroupDelete/{placementGroupName}', PlacementGroupName).doc("Delete a placement group", """ """)

Api.spDocSection("Volume Templates",
	""" Templates are a set of rules used for creating many similar volumes. """
	)
Api.volumeTemplatesList = GET('VolumeTemplatesList', returns=[sp.VolumeTemplateDesc]).doc("List all volume templates", """ """)
Api.volumeTemplatesStatus = GET('VolumeTemplatesStatus', returns=[sp.VolumeTemplateStatusDesc]).doc("List the status of all volume templates", """ """)
Api.volumeTemplateDescribe = GET('VolumeTemplateDescribe/{templateName}', VolumeTemplateName, returns=sp.VolumeTemplateDesc).doc("Describe a single volume template",
	"""
	Same as VolumeTemplatesList but only return information about a given template.
	""")
Api.volumeTemplateCreate = POST('VolumeTemplateCreate', json=sp.VolumeTemplateCreateDesc).doc("Create a volume template", """ """)
Api.volumeTemplateUpdate = POST('VolumeTemplateUpdate/{templateName}', VolumeTemplateName, json=sp.VolumeTemplateUpdateDesc).doc("Update a volume template",
	""" Alter the configuration of an existing volume template. """
	)
Api.volumeTemplateDelete = POST('VolumeTemplateDelete/{templateName}', VolumeTemplateName).doc("Delete a volume template", """ """)

Api.spDocSection("Volume Relocator",
	"""
	This is a service that moves data when needed, e.g. when
	removing or adding disks.
	"""
	)
Api.volumeRelocatorOn = POST('VolumeRelocatorOn').doc("Turn the relocator on", """ """)
Api.volumeRelocatorOff = POST('VolumeRelocatorOff').doc("Turn the relocator off", """ """)
Api.volumeRelocatorStatus = GET('VolumeRelocatorStatus', returns=sp.VolumeRelocatorStatus).doc("Get the relocator's status", """ """)
Api.volumeRelocatorDisks = GET('VolumeRelocatorDisksList', returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)
Api.volumeRelocatorVolumeDisks = GET('VolumeRelocatorVolumeDisks/{volumeName}', VolumeName, returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)
Api.volumeRelocatorSnapshotDisks = GET('VolumeRelocatorSnapshotDisks/{snapshotName}', SnapshotName, returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)

Api.spDocSection("Balancer",
	""" This is a service that decides when it is a good time to move data. """
	)
Api.volumeBalancerGetStatus = GET('VolumeBalancerStatus', returns=sp.VolumeBalancerStatus).doc("Get the balancer's status", """ """)
Api.volumeBalancerSetStatus = POST('VolumeBalancerStatus', json=sp.VolumeBalancerCommand).doc("Set the balancer's status", """ """)
Api.volumeBalancerVolumesStatus = GET('VolumeBalancerVolumesStatus', returns=[sp.VolumaBalancerVolumeStatus]).doc("", """ """)
Api.volumeBalancerDisks = GET('VolumeBalancerDisksList', returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)
Api.volumeBalancerVolumeDisks = GET('VolumeBalancerVolumeDisks/{volumeName}', VolumeName, returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)
Api.volumeBalancerSnapshotDisks = GET('VolumeBalancerSnapshotDisks/{snapshotName}', SnapshotName, returns={sp.DiskId: sp.DiskTarget}).doc("", """ """)
Api.volumeBalancerVolumeDiskSets = GET('VolumeBalancerVolumeDiskSets/{volumeName}', VolumeName, returns=sp.VolumeBalancerVolumeDiskSets).doc("", """ """)
Api.volumeBalancerSnapshotDiskSets = GET('VolumeBalancerSnapshotDiskSets/{snapshotName}', SnapshotName, returns=sp.VolumeBalancerVolumeDiskSets).doc("", """ """)

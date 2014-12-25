#
#-
# Copyright (c) 2014  StorPool.
# All rights reserved.
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
	assert 'returns' not in kwargs, 'POST requests currently return the same result type'
	return _API_METHOD('POST', query, args, kwargs.get('json', None), ApiOk)


@js.JsonObject(ok=const(True), generation=long)
class ApiOk(object):
	pass

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
		"""Storpool API Reference""",
		"""XXX Put general API description here"""
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
		
		with http.HTTPConnection(self._host, self._port, self._timeout) as conn:
			request = conn.request(method, path, json, self._authHeader)
			response = conn.getresponse()
			status, json = response.status, js.load(response)
			
			if status != http.OK or 'error' in json:
#				print status, json
				raise ApiError(status, json)
			else:
#				print json
				return json['data']
	
	def volumeDevLinkWait(self, volumeName, attach, pollTime=200*msec, maxTime=60*sec):
		return pathPollWait(SP_DEV_PATH + volumeName, attach, True, pollTime, maxTime)

Api.spDocSection("Peers", """ """)
Api.peersList = GET('NetworkPeersList', returns={sp.PeerId: sp.PeerDesc}).doc("List Peers", """ """)

Api.spDocSection("Tasks", """ """)
Api.tasksList = GET('TasksList', returns=[sp.Task]).doc("List tasks", """List currently active recovery tasks.""")

Api.spDocSection("Services", """ """)
Api.servicesList = GET('ServicesList', returns=sp.ClusterStatus).doc("List all Storpool services", """ """)
Api.serversListBlocked = GET('ServersListBlocked', returns=sp.ClusterStatus).doc("List all blocked Storpool servers", """ """)

Api.spDocSection("Servers", """ """)
Api.serversList = GET('ServersList', returns=sp.ClusterStatus).doc("List all Storpool servers", """ """)
Api.serverDisksList = GET('ServerDisksList/{serverId}', ServerId, returns={sp.DiskId: sp.DiskSummary}).doc("List all disks on server", """ """)
Api.serverDiskDescribe = GET('ServerDiskDescribe/{serverId}/{diskId}', ServerId, DiskId, returns=sp.Disk).doc("Describe a disk on server", """ """)

Api.spDocSection("Clients", """ """)
Api.clientsConfigDump = GET('ClientsConfigDump', returns=[sp.ClientConfigStatus]).doc("Get current configuration for all clients", """ """)
Api.clientConfigWait = GET('ClientConfigWait/{clientId}', ClientId, returns=[sp.ClientConfigStatus]).doc("Wait until client updates to current configuration", """ """)
Api.clientActiveRequests = GET('ClientActiveRequests/{clientId}', ClientId, returns=sp.ClientActiveRequests).doc("List all active requests on client", """ """)

Api.spDocSection("Disks", """ """)
Api.disksList = GET('DisksList', returns={sp.DiskId: sp.DiskSummary}).doc("List all disks", """ """)
Api.diskDescribe = GET('DiskDescribe/{diskId}', DiskId, returns=sp.Disk).doc("Describe a disk", """ """)
Api.diskInfo = GET('DiskGetInfo/{diskId}', DiskId, returns=sp.DiskInfo).doc("Get disk info", """ """)
Api.diskEject = POST('DiskEject/{diskId}', DiskId).doc("Eject a disk", """ """)
Api.diskForget = POST('DiskForget/{diskId}', DiskId).doc("Foget a disk", """ """)
Api.diskSoftEject = POST('DiskSoftEject/{diskId}', DiskId).doc("Soft-eject a disk", """ """)
Api.diskSoftEjectPause = POST('DiskSoftEjectPause/{diskId}', DiskId).doc("Pause disk soft-eject", """ """)
Api.diskSoftEjectCancel = POST('DiskSoftEjectCancel/{diskId}', DiskId).doc("Cancel disk soft-eject", """ """)
Api.diskSetDesc = POST('DiskSetDescription/{diskId}', DiskId, json=sp.DiskDescUpdate).doc("Set a disk's description", """ """)
Api.diskActiveRequests = GET('DiskActiveRequests/{diskId}', DiskId, returns=sp.DiskActiveRequests).doc("List all active requests on disk", """ """)

Api.spDocSection("Volumes", """ """)
Api.volumesList = GET('VolumesList', returns=[sp.VolumeSummary]).doc("List all volumes", """ """)
Api.volumesStatus = GET('VolumesGetStatus', returns={sp.VolumeName: sp.VolumeStatus}).doc("Get volume and snapshot status", """ """)
Api.volumeList = GET('Volume/{volumeName}', VolumeName, returns=[sp.VolumeSummary]).doc("List a single volume", """ """)
Api.volumeDescribe = GET('VolumeDescribe/{volumeName}', VolumeName, returns=sp.Volume).doc("Describe a volume", """ """)
Api.volumeInfo = GET('VolumeGetInfo/{volumeName}', VolumeName, returns=sp.VolumeInfo).doc("Get volume info", """ """)
Api.volumeListSnapshots = GET('VolumeListSnapshots/{volumeName}', VolumeName, returns=[sp.SnapshotSummary]).doc("List parent snapshots for volume", """ """)
Api.volumeCreate = POST('VolumeCreate', json=sp.VolumeCreateDesc).doc("Create a new volume", """ """)
Api.volumeUpdate = POST('VolumeUpdate/{volumeName}', VolumeName, json=sp.VolumeUpdateDesc).doc("Update a volume", """ """)
Api.volumeFreeze = POST('VolumeFreeze/{volumeName}', VolumeName).doc("Freeze a volume", """ """)
Api.volumeRebase = POST('VolumeRebase/{volumeName}', VolumeName, json=sp.VolumeRebaseDesc).doc("Rebase a volume", """ """)
Api.volumeDelete = POST('VolumeDelete/{volumeName}', VolumeName).doc("Delete a volume", """ """)

Api.spDocSection("Snapshots", """ """)
Api.snapshotsList = GET('SnapshotsList', returns=[sp.SnapshotSummary]).doc("List all snapshots", """ """)
Api.snapshotList = GET('Snapshot/{snapshotName}', SnapshotName, returns=[sp.SnapshotSummary]).doc("List a single snapshots", """ """)
Api.snapshotDescribe = GET('SnapshotDescribe/{snapshotName}', SnapshotName, returns=sp.Volume).doc("Describe a snapshot", """ """)
Api.snapshotInfo = GET('SnapshotGetInfo/{snapshotName}', SnapshotName, returns=sp.VolumeInfo).doc("Get snapshot info", """ """)
Api.snapshotCreate = POST('VolumeSnapshot/{volumeName}', VolumeName, json=sp.VolumeSnapshotDesc).doc("Snapshot a volume", """ """)
Api.snapshotUpdate = POST('SnapshotUpdate/{snapshotName}', SnapshotName, json=sp.VolumeUpdateDesc).doc("Update snapshot", """ """)
Api.snapshotRebase = POST('SnapshotRebase/{snapshotName}', SnapshotName, json=sp.VolumeRebaseDesc).doc("Rebase snapshot", """ """)
Api.snapshotDelete = POST('SnapshotDelete/{snapshotName}', SnapshotName).doc("Delete snapshot", """ """)

Api.spDocSection("Volume Rights", """ """)
Api.attachmentsList = GET('AttachmentsList', returns=[sp.AttachmentDesc]).doc("List all Attachments",""" """)
Api.volumesReassign = POST('VolumesReassign', json=[either(sp.VolumeReassignDesc, sp.SnapshotReassignDesc)]).doc("Reassign volumes and/or snapshots", """ """)

Api.spDocSection("Placement Groups", """ """)
Api.placementGroupsList = GET('PlacementGroupsList', returns={sp.PlacementGroupName: sp.PlacementGroup}).doc("List all placement groups", """ """)
Api.placementGroupDescribe = GET('PlacementGroupDescribe/{placementGroupName}', PlacementGroupName, returns=sp.PlacementGroup).doc("Describe single placement group", """ """)
Api.placementGroupUpdate = POST('PlacementGroupUpdate/{placementGroupName}', PlacementGroupName, json=sp.PlacementGroupUpdateDesc).doc("Create and/or update placement group", """ """)
Api.placementGroupDelete = POST('PlacementGroupDelete/{placementGroupName}', PlacementGroupName).doc("Delete placement group", """ """)

Api.spDocSection("Volume Templates", """ """)
Api.volumeTemplatesList = GET('VolumeTemplatesList', returns=[sp.VolumeTemplateDesc]).doc("List all volume templates", """ """)
Api.volumeTemplateDescribe = GET('VolumeTemplateDescribe/{templateName}', VolumeTemplateName, returns=sp.VolumeTemplateDesc).doc("Describe single volume template", """ """)
Api.volumeTemplateCreate = POST('VolumeTemplateCreate', json=sp.VolumeTemplateCreateDesc).doc("Create volume template", """ """)
Api.volumeTemplateUpdate = POST('VolumeTemplateUpdate/{templateName}', VolumeTemplateName, json=sp.VolumeTemplateUpdateDesc).doc("Update volume template", """ """)
Api.volumeTemplateDelete = POST('VolumeTemplateDelete/{templateName}', VolumeTemplateName).doc("Delete volume template", """ """)

Api.spDocSection("Volume Relocator", """ """)
Api.volumeRelocatorOn = POST('VolumeRelocatorOn').doc("Turn-ON relocator", """ """)
Api.volumeRelocatorOff = POST('VolumeRelocatorOff').doc("Turn-OFF relocator", """ """)
Api.volumeRelocatorStatus = GET('VolumeRelocatorStatus', returns=sp.VolumeRelocatorStatus).doc("Get relocator status", """ """)

Api.spDocSection("Balancer", """ """)
Api.volumeRelocatorOn = POST('VolumeBalancerOn').doc("Turn-ON balancer", """ """)
Api.volumeRelocatorOff = POST('VolumeBalancerOff').doc("Turn-OFF balancer", """ """)
Api.volumeRelocatorStatus = GET('VolumeBalancerStatus', returns=sp.VolumeBalancerStatus).doc("Get balancer status", """ """)


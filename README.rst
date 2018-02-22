Description
===========

This package contains Python bindings to the JSON-over-HTTP API of the StorPool
distributed storage software.

For more information about the available API functions please see
the apidoc.html file.

StorPool is distributed data storage software running on standard x86 servers.
StorPool aggregates the performance and capacity of all drives into a shared
pool of storage distributed among the servers.  Within this storage pool the
user creates thin-provisioned volumes that are exposed to the clients as block
devices.  StorPool consists of two parts wrapped in one package - a server and
a client.  The StorPool server allows a hypervisor to act as a storage node,
while the StorPool client allows a hypervisor node to access the storage pool
and act as a compute node.

Version history
===============

4.1.0
-----

- fix the documentation example for instantiating an Api object
- add the SnapshotSummary.recoveringFromRemote member

4.0.0
-----

- drop support for the removed StorPool AoE target
- drop support for servers in volume placement groups
- add support for StorPool remote snapshots, volumes, and backups:
    - API methods:
        - exportsList()
        - locationsList()
        - snapshotDeleteById()
        - snapshotExport()
        - snapshotFromRemote()
        - snapshotRemoteList()
        - snapshotUnexport()
        - snapshotsRemoteList()
        - snapshotsRemoteUnexport()
        - volumeBackup()
        - volumesGroupBackup()
    - types:
        - BridgeId
        - BridgeStatus
        - GlobalVolumeId
        - LocationId
        - RemoteLocationName
    - classes:
        - ApiOkVolumeBackup
        - ApiOkVolumesGroupBackup
        - Bridge
        - Export
        - SnapshotExportDesc
        - SnapshotFromRemoteDesc
        - SnapshotRemoteUnexportDesc
        - SnapshotUnexportDesc
        - SnapshotsRemoteUnexport
        - RemoteLocation
        - RemoteSnapshot
        - VolumeBackupDesc
        - VolumeFreezeDesc
        - VolumesGroupBackupSingle
        - VolumesGroupBackupDesc
    - class members:
        - SnapshotSummary.globalId
        - SnapshotSummary.targetDeleteDate
        - SnapshotUpdateDesc.targetDeleteDate
        - SnapshotUpdateDesc.deleteAfter
        - VolumeSnapshotDesc.targetDeleteDate
        - VolumeSnapshotDesc.deleteAfter
- add support for StorPool transport over InfiniBand:
    - types:
        - GUID
        - RdmaState
    - classes:
        - RdmaDesc
    - members:
        - PeerDesc.networks
        - PeerDesc.rdma
- drop the bandwidth and iops members of the DiskWbcStats class
- add the journaled member to the UpDiskSummary class
- add support for creating a set of consistent snapshots for
  a group of volumes:
    - API methods:
        - snapshotCreateGroup()
    - classes:
        - GroupSnapshotSpec
        - GroupSnapshotsSpec
        - GroupSnapshotResult
        - GroupSnapshotsResult
- add support for listing the server fault sets:
    - API methods:
        - faultSetsList()
    - types:
        - FaultSetName
    - classes:
        - FaultSet
- add support for placeHead:
    - members:
        - SnapshotFromRemoteDesc.placeHead
        - VolumeBalancerAllocationGroup.placeHead
        - VolumeBalancerVolumeStatus.placeHead
        - VolumePolicyDesc.placeHead
        - VolumeSummaryBase.placeHead
        - VolumeTemplateDesc.placeHead
        - VolumeTemplateSpaceEst.placeHead
        - VolumeTemplateStatusDesc.availablePlaceHead
        - VolumeTemplateStatusDesc.capacityPlaceHead
        - VolumeTemplateStatusDesc.placeHead
- add the Api.fromConfig() method to configure a new Api object by
  reading the standard StorPool configuration files
- let the requests to the StorPool API succeed and return partial data
  even if the API returns JSON data that does not represent valid
  expected objects
- fix the regular expression for the remote location name
- note that this documents version 18.01 of the StorPool API
- add support for reuseServer:
    - members:
        - VolumePolicyDesc.reuseServer
        - VolumeTemplateDesc.reuseServer
        - VolumeBalancerAllocationGroup.reuseServer

3.0.1
-----

- note that this documents version 16.01 of the StorPool API
- fix a typo in the VolumeBalancerVolumeStatus class name
- document a lot of classes and fields

3.0.0
-----

- add volumesSpace() and the VolumeSpace type
- add the volumesToRelocate member of the VolumeRelocatorStatus type
- add the VolumeTemplateSpaceEstInternal, VolumeTemplateSpaceEst, and
  VolumeTemplateSpaceEstEntry types for the new phys and stored members of
  the VolumeTemplateStatusDesc type
- retry the query to the StorPool API if a transient error is returned;
  add the transientRetries and transientSleep parameters to the Api()
  constructor
- move the ssd member from the UpDiskSummary to the DiskSummaryBase type
- add the optional info member to the ApiOk type
- add the beaconStatus, clusterStatus, and joined members to
  the PeerDesc type
- add diskScrubStart(), diskScrubPause(), and diskScrubContinue() and
  several scrubbing-related members to the DownDiskSummary and
  UpDiskSummary types
- add the noFlush and noTrim members to the UpDiskSummary type
- add diskRetrim()
- add the startTime member and the uptime() method to the Service type
- document the float property type
- remove volumeRelocatorOn() and volumeRelocatorOff(); this functionality
  will be exposed in a better way later
- add volumesReassignWait() and its VolumesReassignWaitDesc type;
  volumesReassign() is now deprecated

2.0.0
-----

- add the capacityPlaceAll and capacityPlaceTail template properties
- add volumeBalancerGroups() and the VolumeBalancerSlot and
  VolumeBalancerAllocationGroup types
- replace UpDiskTarget's objectsToRecover attribute with a toRecover
  attribute for the target's storedSize and onDiskSize members;
  accordingly, bump the storpool module's version to 2.0.0 for
  a backwards-incompatible change
- add the _asdict() method to JsonObject to fix the breakage in newer
  versions of simplejson when they try to look for this method using
  getattr(), triggering an unknown attribute JsonObject exception
- add some omitted documentation titles for some rarely-used internal
  relocator/balancer commands
- mark the disk wbc and aggregateScore properties as internal
- add the missing documentation for the AttachmentDesc.volume attribute

1.3.1
-----

- fix a typo in a DiskWbcStats member name: ios -> iops

1.3.0
-----

- remove an unused internal Python object attribute
- only check the defined attributes in JsonObject, ignore any additional
  members received in a JSON message
- add snapshotsSpace() for the snapshot reverse space estimation
- reflect the fact that volumeStatus() may also return an anonymous
  snapshot, thus the name may also be a SnapshotName
- drop the "name" attribute of VolumeSummaryBase since it is always
  overridden in its child classes (either a volume or a snapshot name)
- fix the return types of snapshotInfo() and snapshotDescribe()
- add the "autoName", "bound", "deleted", and "transient" snapshot flags
- add the "noFua" and "isWbc" disk flags, the "wbc" write-back cache info,
  and the "aggregateScore" aggregation info
- flesh out the volume balancer and relocator support

1.2.0
-----

- fix the return type of volumeCreate() and snapshotCreate() - a new type,
  ApiOkVolumeCreate, that extends ApiOk to add the optinal "autoName"
  autogenerated snapshot name
- note that this documents version 15.02 of the StorPool API
- fix a bug in a very rarely used initialization mode of JsonObject
- add a "section" parameter to the SPConfig constructor to be able to fetch
  information about another host in the cluster

1.1.0
-----

- add the get() method with a default value to SPConfig objects

1.0.5
-----

- add the SnapshotUpdateDesc type, since snapshotUpdate() only accepts a subset
  of volumeUpdate()'s parameters
- add the volumeTemplateStatus(), diskIgnore(), volumeAbandonDisk() and
  snapshotAbandonDisk() commands
- add the "bind" parameter to volumeUpdate() and snapshotUpdate()
- add the "baseOn" parameter to volumeCreate()
- add some internal templateId attributes; they are returned by the StorPool
  management service, but they should not really be used by consumers
- fix the validation of snapshot names to accept the anonymous snapshots that
  may be returned by the various "list snapshots" commands
- properly return information about missing/down disks in disksList() and
  serverDisksList() - introduce a separate type for them
- make the objects returned by the API calls iterable - "for i in obj" is now
  similar to a dictionary's iteritems() method
- make volumeCreate()'s "size" parameter optional, since the size may be
  defined in a volume template

1.0.4
-----

- rename Disk.ok to Disk.up
- fix typo: CientID => ClientID
- clean-up/fix peer ID types
- mark a bunch of attributes as internal
- use js.dumps and not str when printing values in the documentation
- generate better json for optional and internal values in the documentation
- export changes to ClusterStatus due to AoE and mgmt failover
- add AoE commands
- add the optional "propagate" parameter to volumeTemplateUpdate()
- extend the validation regular expressions for the names of volumes and
  snapshots to support the special notation for system volumes and
  snapshots currently being deleted
- fix the ActiveRequestDesc "name" parameter to also support snapshot names
- add the "snapshot" flag to the volumeStatus() result to signify that this
  entry represents a snapshot and not a volume

1.0.3
-----

- update the API documentation
- fix a HTTPConnection usage bug

1.0.2
-----

- fix the author e-mail address in setup.py
- fix the README file's Markdown format

1.0.1
-----

- relicense under the Apache 2.0 License
- switch the README file to Markdown format
- remove a leftover OpenStack reference from the README file

1.0.0
-----

- first public release

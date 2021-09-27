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

7.0.0
-----

- INCOMPATIBLE CHANGES: spconfig.SPConfig:
  - the default behavior has changed to allow the `SP_AUTH_TOKEN`,
    `SP_API_HTTP_HOST`, and `SP_API_HTTP_PORT` environment variables to
    override the values obtained from the configuration
  - the old behavior is available if `use_env=False` is passed to
    the SPConfig constructor

- INCOMPATIBLE CHANGES: spapi.Api:
  - the default behavior of the `Api.fromConfig()` method has changed to
    allow environment variable overrides as per the above SPConfig change
  - the old behavior is available if `use_env=False` is passed to
    the `fromConfig()` method

- add some new SPConfig default values:
  - `SP_BD_LOG_OPEN_CLOSE`
  - `SP_ABRTSYNC_ALTERNATIVE_SENDER`
  - `SP_ABRTSYNC_ALTERNATIVE_SENDER_HTTPS`
  - `SP_ABRTSYNC_NEW_REMOTE_ADDRESSES`
  - `SP_ABRTSYNC_NEW_REMOTE_PORTS`
- add some new fields:
  - AttachmentDesc.globalId
- spconfig.SPConfig: use a `{}` literal instead of `dict()` in the constructor
- use `io.open()` instead of `open()` in various places
- ignore pylint's "consider-using-f-string" diagnostic for Python 2.x code

6.0.0
-----

- INCOMPATIBLE CHANGES: spconfig.SPConfig:
  - raise an exception if /etc/storpool.conf is missing
  - no longer look for /usr/lib/storpool/storpool-defaults.conf,
    use a static list of default values instead

- allow spconfig.SPConfig.get() to be invoked with a single argument,
  using None as a default value
- add the year 2021 to the copyright notice of the generated documentation

5.5.0
-----

- allow the "json" argument to be optional for some specific API calls
- allow arguments defined as maybe() to actually accept None passed in
  explicitly as a value
- support passing a "json" argument to GET for some specific API calls
- support StorPool multicluster mode for the snapshotsList query
- correct a member field name for GroupSnapshotsResult
- let some API calls also accept StorPool global ID volume/snapshot
  identifiers instead of names
- move the VERSION constant from the storpool module to storpool.spapi,
  since the top-level storpool module may not contain anything - it is
  a namespace package
- minor test infrastructure improvements
- add some new API methods:
  - allPeersActiveRequests
  - clusterAdd
  - clusterRemove
  - clusterRename
  - clustersList
  - iSCSInterfacesInfo
  - iSCSISessionsInfo
  - locationAdd
  - locationRemove
  - locationRename
  - locationUpdate
  - maintenanceComplete
  - maintenanceList
  - maintenanceSet
  - remoteBridgeAdd
  - remoteBridgeRemove
  - remoteBridgesList
  - volumeExportsList
  - volumeFromRemote
  - volumeRevert
  - volumesRemoteList
- add some new types:
  - AllPeersActiveRequests
  - AllPeersActiveRequestsDiskExpected
  - AllPeersActiveRequestsDiskStatus
  - AllPeersActiveRequestsPeerDesc
  - AllPeersActiveRequestsQuery
  - AllPeersActiveRequestsRequest
  - AllPeersActiveRequestsRequestPeer
  - AllPeersActiveRequestsServiceDesc
  - AllPeersActiveRequestsSimpleStats
  - ApiOkSnapshotCreate
  - iSCSIControllerInterfaceInfo
  - iSCSIControllerIntefacesInfo
  - iSCSIControllersQuery
  - iSCSIControllersIntefacesInfo
  - iSCSISessionInfo
  - iSCSISessionStats
  - iSCSISessionTasks
  - iSCSISessionTcp
  - iSCSISessionTcpStats
  - iSCSISessionsInfo
  - MaintenanceCompleteDesc
  - MaintenanceNodeDesc
  - MaintenanceNodesList
  - MaintenanceSetDesc
  - RemoteBridge
  - RemoteBridgeAddClusterDesc
  - RemoteBridgeAddDesc
  - RemoteBridgeAddLocationDesc
  - RemoteBridgeBase
  - RemoteBridgeRemoveDesc
  - RemoteCluster
  - RemoteClusterAddDesc
  - RemoteClusterBase
  - RemoteClusterName
  - RemoteClusterRemoveDesc
  - RemoteClusterRenameDesc
  - RemoteLocationBase
  - RemoteLocationRenameDesc
  - RemoteLocationUpdateDesc
  - SubClusterId
  - VolumeFromRemoteDesc
  - VolumeRevertDesc
- add some new member fields:
  - GroupSnapshotResult.snapshotGlobalId
  - GroupSnapshotResult.volumeGlobalId
  - GroupSnapshotSpec.tags
  - RemoteLocation.sendBufferSize
  - RemoteLocation.recvBufferSize
  - RemoteSnapshot.createdFromGlobalId
  - RemoteSnapshot.createdFromVisibleVolumeId
  - SnapshotFromRemoteDesc.replication
  - SnapshotFromRemoteDesc.template
  - VolumeSummaryBase.globalId
  - VolumesGroupBackupSingle.snapshotGlobalId
- add more disk request operation types to the ActiveRequestDesc.op enum

5.4.0
-----

- all the volume- and snapshot-related API calls now accept a GlobalID in
  place of a VolumeName or SnapshotName
- blacklist pylint-2.5.0 in the test requirements, see
  https://github.com/PyCQA/pylint/issues/3527
- add a unit test for `spconfig.SPConfig.get_config_files()`
- align the operation of `spconfig.SPConfig.get_config_files()` with
  the `storpool_confget` utility that it is meant to mimic: when looking
  for config files in the `/etc/storpool.conf.d/` directory, only use
  files with names ending in ".conf" and not starting with a dot

5.3.1
-----

- fix the type of the VolumeReassignDesc.allowRemoteExported field so that
  the Python bindings do not always send a value to the StorPool API,
  thus improving backwards compatibility

5.3.0
-----

- correct the newly-added snapshot backup-related fields
- allow setup.py to not build the documentation if `SP_NO_DOC_BUILD` is
  defined in the environment

5.2.0
-----

- document that this library interfaces with StorPool 19.01
- add the "source" parameter to the spapi.Api constructor to specify
  the source address to make the HTTP connection to the StorPool API from
- fix a bug in setting the timeout for the HTTP query to the API
- raise the HTTP query timeout to 300 seconds
- treat HTTP library exceptions as transient errors
- add the RemoteSnapshot.tags field
- accept StorPool snapshot global IDs prefixed by a "~" character as
  valid names for volumes and snapshots in most places
- add StorPool multicluster support: add the cluster name and
  multicluster flag parameters to the spapi.Api constructor and mark
  some of the API queries as supporting a multicluster path
- add some multicluster-related API queries

5.1.2
-----

- fix the check for treating an HTTPException as a transient error

5.1.1
-----

- treat an HTTPException as a transient API communication error

5.1.0
-----

- add the storpool.VERSION string constant and let setup.py use it
- when sending JSON-encoded objects to the StorPool API, omit any
  JSON null values: the API will ignore them anyway, but there are some
  cases when it may reject them as unknown before ignoring them
- add the "tags" field to the GroupSnapshotsSpec class for
  the snapshotCreateGroup() call

5.0.0
-----

- document that this library interfaces with StorPool 18.02
- do not use the deprecated `message` field of the BaseException class
- add the SPConfig.get_all_sections() method and a dependency on
  the feature_check Python library
- use the Python confget library instead of the StorPool-specific
  command-line parser tool
- add a tox/pytest unit testing framework, convert some existing test
  scripts to use it, and add new tests
- adapt the source code for compatibility with Python 3.x
- correct some limits and regular expressions used for validating
  service IDs and object names

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

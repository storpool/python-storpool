#!/usr/bin/python
#
# Copyright (c) 2015 - 2019  StorPool.
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
""" Basic sanity-checks for StorPool's API python bindings.

We presuppose that there is a running cluster, with at least
THREE servers and at least ONE SSD per server.

All objects (templates, placement groups, volumes, and snapshots)
created by this test are prefixed with 'sptest_' in order not to
collide with any pre-existing setup.

@TODO:
 - Missing disk eject/forget as these are destructive
 - Missing most BLOCK client related commands
 - Missing balancer commit
"""

from __future__ import print_function

import argparse
import time

from storpool import spapi


SP_TEST_PREFIX = "sptest_"


def sp_name(fmt, *args, **kwargs):
    """ Format a StorPool test volume's name. """
    return SP_TEST_PREFIX + fmt.format(*args, **kwargs)


def sp_name_check(name):
    """ Check whether a StorPool volume was created by us. """
    return name.startswith(SP_TEST_PREFIX)


api = spapi.Api.fromConfig()

reassignIndex = 0
reassignHandler = [
    lambda data: api.volumesReassign(data),
    lambda data: api.volumesReassignWait({'reassign': data}),
    lambda data: api.volumesReassignWait({
        'reassign': data, 'attachTimeout': 1}),
    lambda data: api.volumesReassignWait({
        'reassign': data, 'attachTimeout': 0}),
]


def reassign(data):
    """ Pick the (round-robin) next volume reassign parameter set. """
    global reassignIndex
    handler = reassignHandler[reassignIndex]
    reassignIndex = (reassignIndex + 1) % len(reassignHandler)
    return handler(data)


def showState():
    """ Display the current cluster state: servers, clients, volumes, etc. """
    ss = api.servicesList()
    print("CLUSTER STATUS:", ss.clusterStatus)
    print("SERVERS:", [sId for sId in ss.servers])
    print("CLIENTS:", [cId for cId in ss.clients])
    print("MGMT:", [mId for mId in ss.mgmt])
    print("DISKS:", [diskId for diskId in api.disksList()])
    print("PLACEMENT GROUPS:",
          [pgName for pgName in api.placementGroupsList()])
    print("TEMPLATES:", [t.name for t in api.volumeTemplatesList()])
    print("VOLUMES:", [v.name for v in api.volumesList()])
    print("SNAPSHOTS:", [s.name for s in api.snapshotsList()])


def cleanup():
    """ Remove any volumes, snapshots, placement groups, ... created by us. """
    for vol in api.volumesList():
        if not sp_name_check(vol.name):
            continue

        print('- detach and remove volume {name}'.format(name=vol.name))
        print(reassign([{'volume': vol.name, 'detach': "all"}]))
        print(api.volumeDelete(vol.name))

    for snap in api.snapshotsList():
        if not sp_name_check(snap.name):
            continue

        print('- detach and remove snapshot {name}'.format(name=snap.name))
        if not snap.autoName:
            print(reassign([{'snapshot': snap.name, 'detach': "all"}]))

        print(api.snapshotDelete(snap.name))

    while True:
        snaps = [snap.name for snap in api.snapshotsList() if snap.deleted]
        if not snaps:
            break

        print("waiting for", snaps)
        time.sleep(1)

    for tmpl in api.volumeTemplatesList():
        if not sp_name_check(tmpl.name):
            continue

        print('- remove template {name}'.format(name=tmpl.name))
        print(api.volumeTemplateDelete(tmpl.name))

    for pgName in api.placementGroupsList():
        if not sp_name_check(pgName):
            continue

        print('- remove placement group {name}'.format(name=pgName))
        print(api.placementGroupDelete(pgName))

    showState()


def setup(no_ssd=False):
    """ Select disks and create placement groups and templates. """
    print('- disksList()')
    disks = api.disksList().values()
    print('- placementGroup create hdd')
    print(api.placementGroupUpdate(
        sp_name("hdd"),
        {'addDisks': [disk.id for disk in disks if not disk.ssd]}))
    if no_ssd:
        print('- placementGroup create ssd with all the disks')
        print(api.placementGroupUpdate(
            sp_name("ssd"),
            {'addDisks': [disk.id for disk in disks]}))
    else:
        print('- placementGroup create ssd')
        print(api.placementGroupUpdate(
            sp_name("ssd"),
            {'addDisks': [disk.id for disk in disks if disk.ssd]}))

    print('- template create 1')
    print(api.volumeTemplateCreate({
        'name': sp_name("tmpl_1"),
        'size': 10 * 1024 ** 3,
        'replication': 1,
        'placeAll': sp_name("hdd"),
        'placeTail': sp_name("ssd"),
    }))
    print('- template create 2')
    print(api.volumeTemplateCreate({
        'name': sp_name("tmpl_2"),
        'size': 10 * 1024 ** 3,
        'replication': 2,
        'placeAll': sp_name("hdd"),
        'placeTail': sp_name("ssd"),
    }))
    print('- template create 3')
    print(api.volumeTemplateCreate({
        'name': sp_name("tmpl_3"),
        'size': 10 * 1024 ** 3,
        'replication': 3,
        'placeAll': sp_name("hdd"),
        'placeTail': sp_name("ssd"),
    }))

    for v in range(5):
        for r in range(1, 4):
            print('- volume {v} template {r}'.format(v=v, r=r))
            volName = sp_name("volume_{v}_{r}", v=v, r=r)
            print(api.volumeCreate({
                'name': volName,
                'template': sp_name("tmpl_{r}", r=r),
            }))
            print(reassign([{'volume': volName, 'rw': [1]}]))

    print('- volumes list')
    for vol in api.volumesList():
        if not sp_name_check(vol.name):
            continue

        print("Snapshot volume:", vol.name)
        print(api.snapshotCreate(vol.name, {}))

        snapName = vol.name + "_snapshot"
        print(api.snapshotCreate(vol.name, {'name': snapName}))
        print(api.snapshotUpdate(snapName, {'iops': 1000}))
        print(reassign([{'snapshot': snapName, 'ro': [1]}]))

    print('- volumes list')
    for vol in api.volumesList():
        if not sp_name_check(vol.name):
            continue

        print('  - volume clone {name}'.format(name=vol.name))
        print(api.volumeCreate({
            'name': vol.name + "_clone",
            'baseOn': vol.name,
        }))

    print("Wait for transient snapshot deletion")
    while True:
        snaps = [snap.name for snap in api.snapshotsList() if snap.transient]
        if not snaps:
            break

        print("waiting for:", snaps)
        time.sleep(1)

    print('- done with setting things up')
    showState()


def config():
    """ Dump Storpool cluster and policy configuration info. """
    print(api.peersList())
    print(api.servicesList())
    print(api.serversListBlocked())
    print(api.tasksList())
    print(api.clientsConfigDump())

    disks = api.disksList()
    print(disks)

    for diskId in disks:
        print(api.diskDescribe(diskId))
        print(api.diskInfo(diskId))
        print(api.diskActiveRequests(diskId))

        print(api.diskSoftEject(diskId))
        print(api.diskSoftEjectPause(diskId))
        print(api.diskSoftEjectCancel(diskId))

    pgs = api.placementGroupsList()
    print(pgs)
    for pgName in pgs:
        print(api.placementGroupDescribe(pgName))

    ts = api.volumeTemplatesList()
    print(ts)
    print(api.volumeTemplatesStatus())
    for t in ts:
        print(api.volumeTemplateDescribe(t.name))


def volumes():
    """ Dump Storpool volumes and snapshots info. """
    print(api.volumesStatus())
    print(api.snapshotsSpace())

    vols = api.volumesList()
    print(vols)
    for vol in vols:
        print(vol.name)
        print(api.volumeList(vol.name))
        print(api.volumeDescribe(vol.name))
        print(api.volumeInfo(vol.name))
        print(api.volumeListSnapshots(vol.name))

    snaps = api.snapshotsList()
    print(snaps)
    for snap in snaps:
        print(snap.name)
        print(api.snapshotList(snap.name))
        print(api.snapshotDescribe(snap.name))
        print(api.snapshotInfo(snap.name))


def relocator():
    """ Dump relocator state info. """
    print(api.volumeRelocatorStatus())
    print(api.volumeRelocatorDisks())

    for vol in api.volumesList():
        print(api.volumeRelocatorVolumeDisks(vol.name))

    for snap in api.snapshotsList():
        print(api.volumeRelocatorSnapshotDisks(snap.name))


def scrubbing():
    """ Test the start/stop/status of the disk scrubbing subsystem. """
    diskId = list(api.disksList().values())[0].id

    print(api.diskScrubPause(diskId))
    assert api.disksList()[diskId].scrubbingPaused

    print(api.diskScrubStart(diskId))
    d = api.disksList()[diskId]
    assert d.scrubbingPaused
    assert d.scrubbingStartedBefore == d.scrubbingPausedFor

    print(api.diskScrubContinue(diskId))
    assert not api.disksList()[diskId].scrubbingPaused


def remote():
    """ Test the export and transfer of data between StorPool clusters. """
    locations = api.locationsList()['locations']
    if not locations:
        print("no remote location. skipping test")
        return
    loc = locations[0]

    for vol in api.volumesList():
        if not sp_name_check(vol.name):
            continue

        api.volumeBackup({'volume': vol.name, 'location': loc.name})
        break

    print(api.snapshotsRemoteList())

    while True:
        r = [r for r in api.snapshotsRemoteList()['snapshots']
             if r.name == vol.name]
        if r:
            break
        print("waiting for remote", vol.name)
        time.sleep(1)

    rem = r[0]
    api.snapshotFromRemote({
        'name': "restoredSnapshot",
        'remoteId': rem.remoteId,
        'remoteLocation': loc.name,
        'template': "sptest_tmpl_1",
    })
    api.snapshotExport({'snapshot': "restoredSnapshot", 'location': loc.name})
    api.snapshotUnexport({
        'snapshot': "restoredSnapshot",
        'location': loc.name,
    })
    api.snapshotDelete("restoredSnapshot")


def main():
    """ Main program: parse the command line, run the test steps. """
    parser = argparse.ArgumentParser(
        prog='sptest',
        usage='''
    sptest [--no-ssd] [phase...]''')
    parser.add_argument('--no-ssd', action='store_true',
                        help='run on HDDs only')
    parser.add_argument('phases', nargs='*')

    args = parser.parse_args()
    if not args.phases:
        args.phases = [
            'cleanup', 'setup', 'config', 'volumes', 'relocator',
            'cleanup', 'scrubbing', 'remote',
        ]
    phases = []
    for phase in args.phases:
        ph = globals().get(phase, None)
        if ph is None:
            exit('UNKNOWN COMMAND: {}'.format(phase))
        phases.append(ph)
    for phase in phases:
        print('RUNNING {}'.format(phase.__name__))
        if phase == setup:
            phase(no_ssd=args.no_ssd)
        else:
            phase()


if __name__ == '__main__':
    main()

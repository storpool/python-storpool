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
""" Simple StorPool API example script. """

from __future__ import print_function

from os import environ

from storpool import spapi, spcatch, sptypes, sputils


api = spapi.Api(
    host=environ.get('SP_API_HTTP_HOST', "127.0.0.1"),
    port=environ.get('SP_API_HTTP_PORT', 80),
    auth=environ.get('SP_AUTH_TOKEN', "")
)


for diskId, disk in api.disksList().iteritems():
    assert disk.id == diskId
    print("Disk {disk.id:3}: serverId={disk.serverId}, "
          "objectsCount={disk.objectsCount}"
          .format(disk=disk))

for pgName, pgDesc in api.placementGroupsList().iteritems():
    assert pgName == pgDesc.name
    print("Placement group {pg.name}: servers={pg.servers}, disks={pg.disks}"
          .format(pg=pgDesc))

for volume in api.volumesList():
    print("Volume {volume.name}: size={volume.size}, "
          "replication={volume.replication}, "
          "objectsCount={volume.objectsCount}"
          .format(volume=volume))


api.volumeCreate({
    'name': 'myTestVol1',
    'size': 10 * sputils.GB,
    'replication': 2,
    'placeAll': 'hdd',
    'placeTail': 'ssd',
})
api.volumeDelete('myTestVol1')

desc = sptypes.VolumeCreateDesc()
desc.name = 'myTestVol2'
try:
    desc.size = 1234
except spcatch.InvalidArgumentError as e:
    print("Invalid argument:", e)
    desc.size = 10 * sputils.GB
desc.replication = 2
desc.placeAll = 'hdd'
desc.placeTail = 'ssd'

api.volumeCreate(desc)

vols = api.volumeList(desc.name)
assert len(vols) == 1

vol = vols[0]
assert vol.name == desc.name
assert vol.size == desc.size
assert vol.replication == desc.replication
assert vol.placeAll == desc.placeAll
assert vol.placeTail == desc.placeTail

api.volumeDelete(desc.name)

try:
    vols = api.volumeList(desc.name)
except spapi.ApiError as e:
    print("API Error:", e)

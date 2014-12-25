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

Version 1.0.2:
- fix the author e-mail address in setup.py

Version 1.0.1:
- relicense under the Apache 2.0 License
- switch the README file to Markdown format
- remove a leftover OpenStack reference from the README file

Version 1.0.0:
- first public release

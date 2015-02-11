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

from distutils import cmd
import os
import setuptools
from setuptools.command import build_py
import subprocess
import sys

class APIDocCommand(cmd.Command):
	"""A custom command to generate the StorPool API documentation."""

	description = 'Generate the StorPool API documentation.'
	user_options = []

	def initialize_options(self):
		pass

	def finalize_options(self):
		pass

	def run(self):
		command = (sys.executable, 'spdoc.py')
		apifile = 'storpool/apidoc.html'

		with open(apifile, 'w') as apidoc:
			try:
				subprocess.check_call(command, cwd='storpool', stdout=apidoc)
			except subprocess.CalledProcessError:
				try:
					os.unlink(apifile)
				except OSError as e:
					if e.errno != 2:
						raise
				raise

class BuildPyCommand(build_py.build_py):
	"""Custom build command, also invoking 'apidoc'."""
	
	def run(self):
		self.run_command('apidoc')
		build_py.build_py.run(self)

setuptools.setup(
	name = 'storpool',
	version = '1.0.3',
	packages = ('storpool',),
	namespace_packages = ('storpool',),

	author = 'Peter Pentchev',
	author_email = 'openstack-dev@storpool.com',
	description = 'Bindings for the StorPool distributed storage API',
	license = 'Apache License 2.0',
	keywords = 'storpool StorPool',
	url = 'http://www.storpool.com/',

	zip_safe = True,

	cmdclass = {
		'apidoc':	APIDocCommand,
		'build_py':	BuildPyCommand,
	},

	data_files = [('/usr/share/doc/python-storpool', ['storpool/apidoc.html'])],
)

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
""" Distribution definitions for the StorPool Python bindings. """


from distutils import cmd
import os
import subprocess
import sys

import setuptools

from setuptools.command import build_py


class APIDocCommand(cmd.Command):
    """A custom command to generate the StorPool API documentation."""

    description = 'Generate the StorPool API documentation.'
    user_options = []

    def initialize_options(self):
        """ No options to initialize. """

    def finalize_options(self):
        """ No options to finalize. """

    def run(self):
        # pylint: disable=no-self-use
        """ Autogenerate the API documentation reference. """
        command = (sys.executable, '-m', 'storpool.spdocbuild')
        apifile = 'storpool/apidoc.html'

        with open(apifile, 'w') as apidoc:
            try:
                subprocess.check_call(command, stdout=apidoc)
            except subprocess.CalledProcessError:
                try:
                    os.unlink(apifile)
                except OSError as exc:
                    if exc.errno != 2:
                        raise
                raise


class BuildPyCommand(build_py.build_py):
    """Custom build command, also invoking 'apidoc'."""

    def run(self):
        self.run_command('apidoc')
        build_py.build_py.run(self)


setuptools.setup(
    name='storpool',
    version='5.0.0',
    packages=('storpool',),
    namespace_packages=('storpool',),

    author='Peter Pentchev',
    author_email='openstack-dev@storpool.com',
    description='Bindings for the StorPool distributed storage API',
    license='Apache License 2.0',
    keywords='storpool StorPool',
    url='http://www.storpool.com/',

    install_requires=[
        'confget',
    ],

    zip_safe=True,

    cmdclass={
        'apidoc':    APIDocCommand,
        'build_py':    BuildPyCommand,
    },

    entry_points={
        'console_scripts': [
            'storpool_req=storpool.spreq:main',
        ],
    },

    data_files=[('/usr/share/doc/python-storpool', ['storpool/apidoc.html'])],
)

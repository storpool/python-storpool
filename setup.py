#
# Copyright (c) 2014 - 2020  StorPool.
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
import re
import subprocess
import sys

import setuptools

from setuptools.command import build_py


RE_VERSION = r'''^
    \s* VERSION \s* = \s* '
    (?P<version>
           (?: 0 | [1-9][0-9]* )    # major
        \. (?: 0 | [1-9][0-9]* )    # minor
        \. (?: 0 | [1-9][0-9]* )    # patchlevel
    (?: \. [a-zA-Z0-9]+ )?          # optional addendum (dev1, beta3, etc.)
    )
    ' \s*
    $'''

BUILD_DOC = os.environ.get("SP_NO_DOC_BUILD") != "1"


def get_version():
    """ Get the version string from the module's __init__ file. """
    found = None
    re_semver = re.compile(RE_VERSION, re.X)
    with open('storpool/spapi.py') as init:
        for line in init.readlines():
            match = re_semver.match(line)
            if not match:
                continue
            assert found is None
            found = match.group('version')

    assert found is not None
    return found


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
        if BUILD_DOC:
            self.run_command('apidoc')
        build_py.build_py.run(self)


setuptools.setup(
    name='storpool',
    version=get_version(),
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
        'apidoc': APIDocCommand,
        'build_py': BuildPyCommand,
    },

    entry_points={
        'console_scripts': [
            'storpool_req=storpool.spreq:main',
        ],
    },

    data_files=[('/usr/share/doc/python-storpool', ['storpool/apidoc.html'])]
    if BUILD_DOC else [],
)

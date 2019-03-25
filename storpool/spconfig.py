#
# Copyright (c) 2014 - 2016  StorPool.
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
""" StorPool configuration file parser """


import os
import subprocess

import feature_check
import feature_check.obtain


class SPConfigException(Exception):
    """ An error that occurred during the StorPool configuration parsing. """

    pass


class SPConfig(object):
    def __init__(self, confget='/usr/sbin/storpool_confget', section=None):
        self._confget = confget
        self._dict = dict()
        self._section = section
        self.confget()

    def confget(self):
        args = (self._confget,) \
            if self._section is None \
            else (self._confget, '-s', self._section)
        confget = str.join(' ', args)
        try:
            p = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=4096)
            out = p.communicate()
            wres = p.wait()
        except OSError as ose:
            raise SPConfigException(
                'Could not read the StorPool configuration using {c}: {e}'
                .format(c=confget, e=ose.strerror))
        except Exception as e:
            raise SPConfigException(
                'Could not read the StorPool configuration using {c}: '
                'unexpected exception {t}: {e}'
                .format(c=confget, t=type(e).__name__, e=e))

        if out[1]:
            out = out[1]
            err = True
        else:
            out = out[0]
            err = False
        out = out.decode('UTF-8').replace("\\\n", "")
        out = filter(lambda s: len(s) > 0, out.split("\n"))

        if wres > 0:
            if err:
                raise SPConfigException(
                    'The StorPool configuration helper {c} exited with '
                    'non-zero code {r}, error messages: {out}'
                    .format(c=confget, r=wres, out=out))
            else:
                raise SPConfigException(
                    'The StorPool configuration helper {c} exited with '
                    'non-zero code {r}'
                    .format(c=confget, r=wres))
        elif wres < 0:
            if err:
                raise SPConfigException(
                    'The StorPool configuration helper {c} was killed by '
                    'signal {s}, error messages: {out}'
                    .format(c=confget, s=-wres, out=out))
            else:
                raise SPConfigException(
                    'The StorPool configuration helper {c} was killed by '
                    'signal {s}'
                    .format(c=confget, s=-wres))
        elif err:
            raise SPConfigException(
                'The StorPool configuration helper {c} reported errors: {out}'
                .format(c=confget, out=out))

        d = {}
        for s in out:
            (key, val) = s.split('=', 1)
            d[key] = val
        self._dict = d

    def __getitem__(self, key):
        return self._dict[key]

    def get(self, key, defval):
        return self._dict.get(key, defval)

    def __iter__(self):
        return iter(self._dict)

    def items(self):
        return self._dict.items()

    def keys(self):
        return self._dict.keys()

    def iteritems(self):
        if hasattr(self._dict, 'iteritems'):
            return self._dict.iteritems()
        else:
            return iter(self._dict.items())

    def iterkeys(self):
        if hasattr(self._dict, 'iterkeys'):
            return self._dict.iterkeys()
        else:
            return iter(self._dict.keys())

    @staticmethod
    def _get_output_lines(cmd):
        explist = [IOError, OSError]
        if hasattr(subprocess, 'CalledProcessError'):
            explist.append(subprocess.CalledProcessError)
        expected = tuple(explist)

        cmdstr = ' '.join(cmd)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
            output = proc.communicate()
            code = proc.returncode
        except expected as exp:
            raise SPConfigException(
                'Could not run "{cmd}": {exp}'
                .format(cmd=cmdstr, exp=exp))
        except Exception as unexp:
            raise SPConfigException(
                'Could not run "{cmd}": unexpected error: {unexp}'
                .format(cmd=cmdstr, unexp=unexp))
        if code != 0:
            raise SPConfigException(
                'Could not run "{cmd}": it exited with code {code}'
                .format(cmd=cmdstr, code=code))

        decoded = output[0].decode('UTF-8')
        if decoded.endswith('\n'):
            decoded = decoded[:-1]
        return decoded.split('\n')

    @staticmethod
    def _fallback_get_all_sections():
        for confget in ('/usr/lib/storpool/confget', '/usr/bin/confget'):
            if os.path.isfile(confget):
                break
        else:
            return []
        return sorted(SPConfig._get_output_lines([
            confget, '-f', '/etc/storpool.conf',
            '-q', 'sections'
        ]))

    @staticmethod
    def get_all_sections():
        fallback = False
        try:
            data = feature_check.obtain_features('/usr/sbin/storpool_confget')
            fallback = 'query-sections' not in data
        except feature_check.obtain.ObtainError:
            fallback = True

        if fallback:
            return SPConfig._fallback_get_all_sections()

        return sorted(SPConfig._get_output_lines([
            '/usr/sbin/storpool_confget', '-q', 'sections'
        ]))

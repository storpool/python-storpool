#
#-
# Copyright (c) 2013, 2014  StorPool.
# All rights reserved.
#
""" StorPool configuration file parser """
import os
import subprocess


class SPConfigException(Exception):
    """ An error that occurred during the StorPool configuration parsing. """

class SPConfig(object):
    def __init__(self, confget='/usr/sbin/storpool_confget'):
        self._confget = confget
        self._dict = dict()
        self.confget()

    def confget(self):
        confget = self._confget
        try:
            p = subprocess.Popen((confget,), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=4096)
            out = p.communicate()
            wres = p.wait()
        except OSError as ose:
            raise SPConfigException('Could not read the StorPool configuration using {c}: {e}'.format(c=confget, e=ose.strerror))
        except Exception as e:
            raise SPConfigException('Could not read the StorPool configuration using {c}: unexpected exception {t}: {e}'.format(c=confget, t=type(e).__name__, e=e))

        if out[1]:
            out = out[1]
            err = True
        else:
            out = out[0]
            err = False
        out = out.replace("\\\n", "")
        out = filter(lambda s: len(s) > 0, out.split("\n"))

        if wres > 0:
            if err:
                raise SPConfigException('The StorPool configuration helper {c} exited with non-zero code {r}, error messages: {out}'.format(c=confget, r=wres, out=out))
            else:
                raise SPConfigException('The StorPool configuration helper {c} exited with non-zero code {r}'.format(c=confget, r=wres))
        elif wres < 0:
            if err:
                raise SPConfigException('The StorPool configuration helper {c} was killed by signal {s}, error messages: {out}'.format(c=confget, s=-wres, out=out))
            else:
                raise SPConfigException('The StorPool configuration helper {c} was killed by signal {s}'.format(c=confget, s=-wres))
        elif err:
            raise SPConfigException('The StorPool configuration helper {c} reported errors: {out}'.format(c=confget, out=out))

        d = {}
        for s in out:
            (key, val) = s.split('=', 1)
            d[key] = val
        self._dict = d

    def __getitem__(self, key):
        return self._dict[key]

    def __iter__(self):
        return self.iterkeys()

    def items(self):
        return self._dict.items()

    def keys(self):
        return self._dict.keys()

    def iteritems(self):
        return self._dict.iteritems()

    def iterkeys(self):
        return self._dict.iterkeys()

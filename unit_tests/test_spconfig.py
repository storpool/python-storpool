"""
Tests for the storpool.spconfig.SPConfig class.
"""

import unittest

import ddt
import mock
import pytest

from storpool import spconfig


@ddt.ddt
class TestConfig(unittest.TestCase):
    # pylint: disable=no-self-use
    """ Simple tests for the configuration parser. """

    @ddt.data(
        {
            'popen': {
                'raise': 'os_error',
            },
            'errors': set(['config']),
        },
        {
            'popen': {
                'raise': 'weird_error',
            },
            'errors': set(['config', 'weird']),
        },
        {
            'popen': {
                'comm_raise': 'os_error',
            },
            'errors': set(['config']),
        },
        {
            'popen': {
                'comm_raise': 'weird_error',
            },
            'errors': set(['config', 'weird']),
        },
        {
            'popen': {
                'return': ('', None),
                'code': 42,
            },
            'errors': set(['fortytwo']),
        },
        {
            'popen': {
                'return': ('', 'well hello there!'),
                'code': 42,
            },
            'errors': set(['fortytwo', 'errmsg']),
        },
        {
            'popen': {
                'return': ('', 'well hello there!'),
                'code': 0,
            },
            'errors': set(['report']),
        },
    )
    @mock.patch('subprocess.Popen')
    def test_fail(self, data, popen):
        """ Simulate failures during the execution of storpool_confget. """
        class WeirdError(Exception):
            """ An exception meant to be raised and detected. """

        def raise_os_error(*_args, **_kwargs):
            """  Simulate subprocess.Popen() but fail with an OSError. """
            raise OSError()

        def raise_weird_error(*_args, **_kwargs):
            """  Simulate subprocess.Popen() but fail with a WeirdError. """
            raise WeirdError()

        raisers = {
            'os_error': raise_os_error,
            'weird_error': raise_weird_error,
        }

        mock_popen = mock.Mock()
        popen.return_value = mock_popen
        if 'popen' in data:
            if 'raise' in data['popen']:
                popen.side_effect = raisers[data['popen']['raise']]
            elif 'comm_raise' in data['popen']:
                mock_popen.communicate.side_effect = \
                    raisers[data['popen']['comm_raise']]
            else:
                mock_popen.communicate.return_value = data['popen']['return']
                mock_popen.wait.return_value = data['popen']['code']

        with pytest.raises(spconfig.SPConfigException) as err:
            spconfig.SPConfig()
        as_str = str(err.value)
        error_defs = {
            'config': 'the StorPool configuration',
            'weird': ': unexpected exception',
            'fortytwo': 'with non-zero code 42',
            'errmsg': ', error messages: ',
            'report': 'reported errors: ',
        }
        errors = set([item[0] for item in error_defs.items()
                      if item[1] in as_str])
        assert errors == data['errors']

    @mock.patch('subprocess.Popen')
    def test_success(self, popen):
        """ Test that a SPConfig object behaves almost like a dictionary. """
        mock_popen = mock.Mock()
        mock_popen.wait.return_value = 0
        popen.return_value = mock_popen

        mock_popen.communicate.return_value = ('a=1\nb=2\nc=3\na=4', None)
        cfg = spconfig.SPConfig()

        assert cfg['b'] == '2'
        with pytest.raises(KeyError):
            assert cfg['d'] == 'we should never get here, right?'

        assert cfg.get('a', 42) == '4'
        assert cfg.get('d', 42) == 42

        assert dict(cfg.items()) == {'a': '4', 'b': '2', 'c': '3'}

        assert sorted(cfg.keys()) == ['a', 'b', 'c']

        assert sorted(cfg.iteritems()) == [('a', '4'), ('b', '2'), ('c', '3')]

        assert sorted(cfg.iterkeys()) == ['a', 'b', 'c']

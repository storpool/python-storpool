#
# Copyright (c) 2019  StorPool.
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
""" A non-interactive command-line interface to the StorPool API. """

from __future__ import print_function

import argparse
import json
import os
import re
import sys

import six.moves

from storpool import spapi, spconfig


def deep_to_json(data):
    """ Convert an API reply to serializable data. """
    if getattr(data, 'to_json', None) is not None:
        return deep_to_json(data.to_json())
    if isinstance(data, list):
        return [deep_to_json(obj) for obj in data]
    if isinstance(data, dict):
        # Bah, we cannot use dict comprehension on CentOS 6, can we...
        return dict([(name, deep_to_json(value))
                     for name, value in data.items()])
    return data


def from_config_with_overrides(**kwargs):
    """ Create an API object with access credentials taken from the StorPool
    configuration files and overridden by environment variables. """
    cfg = spconfig.SPConfig()
    data = {}
    for name in ('SP_API_HTTP_HOST', 'SP_API_HTTP_PORT', 'SP_AUTH_TOKEN'):
        value = os.environ.get(name, None)
        if value is None:
            value = cfg[name]
        data[name] = value

    return spapi.Api(host=data['SP_API_HTTP_HOST'],
                     port=int(data['SP_API_HTTP_PORT']),
                     auth=data['SP_AUTH_TOKEN'],
                     **kwargs)


def err_exit(name, descr, **args):
    """ Output an error in JSON form to the standard error stream and exit. """
    err = {
        'error': {
            'transient': False,
            'name': name,
            'descr': descr,
        },
    }
    err['error'].update(args)
    sys.exit(json.dumps(err, indent=2))


def parse_args():
    """ Parse the command-line arguments, going through some weird contortions
    to not allow the ArgumentParser to output anything to the standard error
    stream, since we want to report all errors in JSON form. """
    parser = argparse.ArgumentParser(
        prog='pycli',
        description='StorPool non-interactive CLI and stuff',
    )
    parser.add_argument('-N', '--noop', action='store_true',
                        help='No-operation mode')
    parser.add_argument('--json', type=str,
                        help='JSON arguments to send to the API')
    parser.add_argument('-C', '--clustername', type=str,
                        help='Name of a remote cluster to send the command to')
    parser.add_argument('-M', '--multicluster', action='store_true',
                        help='Enable multicluster mode')
    parser.add_argument('-P', '--post', action='store_true',
                        help='Use a POST query instead of a GET one')
    parser.add_argument('query', type=str,
                        help='The HTTP query to send')
    parser.add_argument('args', type=str, nargs='*',
                        help='Arguments to pass to the API')

    # OK, so this is a bit weird...
    errbuf = six.moves.StringIO()
    orig_stderr = sys.stderr
    sys.stderr = errbuf
    try:
        args = parser.parse_args()
    except SystemExit as ex_err:
        sys.stderr = orig_stderr
        if ex_err.code == 0:
            sys.exit(0)
        err_exit('cliParseArgs',
                 'Could not parse the command-line arguments',
                 parser_errors=errbuf.getvalue())
    except BaseException as err:  # pylint: disable=broad-except
        sys.stderr = orig_stderr
        err_exit('cliParseArgs', str(err),
                 parser_errors=errbuf.getvalue())

    sys.stderr = orig_stderr
    return args


def get_api_method(args):
    """ Find the API method with the specified name and HTTP method.

    Validate the number of arguments passed. """
    http_method = 'POST' if args.post else 'GET'

    try:
        api = from_config_with_overrides(multiCluster=args.multicluster)
    except KeyError as k_err:
        err_exit('cliMissingConfigVariable',
                 'Missing CLI configuration variable',
                 missing=k_err.args[0])
    except BaseException as err:  # pylint: disable=broad-except
        err_exit('cliInitAPI', str(err))

    for name in dir(api):
        method = getattr(api, name, None)
        if method is None:
            continue
        doc = getattr(method, 'spDoc', None)
        if doc is None:
            continue
        query = getattr(doc, 'query', None)
        if query == args.query and doc.method == http_method:
            break
    else:
        err_exit('cliUnknownQuery', 'Unknown API query',
                 method=http_method, query=args.query)

    args_req = getattr(method.spDoc, 'args', {}).keys()
    if len(args_req) != len(args.args):
        re_arg = re.compile('[{] (?P<name> [^}]+) [}]', re.X)
        arg_names = re_arg.findall(method.spDoc.path)
        err_exit('cliInvalidNumberOfArguments',
                 'Invalid number of arguments supplied',
                 supplied_count=len(args.args),
                 required_count=len(args_req),
                 required_names=arg_names)

    json_req = getattr(method.spDoc, 'json', None) is not None
    if json_req and args.json is None:
        err_exit('cliJSONRequired',
                 'This method requires JSON data')
    elif args.json is not None and not json_req:
        err_exit('cliNoJSONRequired',
                 'This method does not require any JSON data')

    return method


def main():
    """ Main function: parse the arguments, make the call, report. """
    args = parse_args()
    method = get_api_method(args)
    method_args = args.args
    if args.json is not None:
        method_args.append(json.loads(args.json))
    method_kwargs = {"clusterName": args.clustername}

    if args.noop:
        print('About to invoke {method} with {args}, {kwargs}'
              .format(method=repr(method), args=repr(method_args),
                      kwargs=repr(method_kwargs)))
        return

    try:
        res = method(*method_args, **method_kwargs)
        print(json.dumps(deep_to_json(res), indent=2))
    except spapi.ApiError as err:
        print(json.dumps(err.json, indent=2), file=sys.stderr)
        sys.exit(3 if err.name == 'objectDoesNotExist' else 2)


if __name__ == '__main__':
    main()

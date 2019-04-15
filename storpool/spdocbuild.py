"""
Build the StorPool API documentation.
"""
#
# Copyright (c) 2014 - 2018  StorPool.
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

from __future__ import print_function

from . import spapi
from . import spdoc


def main():
    """ Main function: generate and output the documentation. """
    html = spdoc.Html()
    spapi.Api.spDoc.build(html)

    with open('storpool/ApiDoc.html.template') as tmpl:
        for line in tmpl.read().split('\n'):
            if line == '__DOC__':
                print(html)
            else:
                print(line)


if __name__ == '__main__':
    main()
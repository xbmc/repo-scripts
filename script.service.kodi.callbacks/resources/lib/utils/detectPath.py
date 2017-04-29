#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2016 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import shlex
import sys
from resources.lib.utils.kodipathtools import translatepath

def process_cmdline(cmd):
    posspaths = []
    parts = shlex.split(cmd, posix= not sys.platform.startswith('win'))
    for i in xrange(0, len(parts)):
        found=-1
        for j in xrange(i+1, len(parts)+1):
            t = ' '.join(parts[i:j])
            t = translatepath(t)
            t = t.strip('"')
            if os.path.exists(t):
                if j > found:
                    found = j
        if found != -1:
            posspaths.append([i, found])
    paths = []
    args = []
    if len(posspaths) > 0:
        for i, path in enumerate(posspaths):  # Check for overlaps
            if i > 0:
                if path[0] < posspaths[i-1][1]:
                    pass  # If possible paths overlap, treat the first as a path and treat the rest of the overlap as non-path
                else:
                    paths.append(path)
            else:
                paths.append(path)
        for i in xrange(0, len(parts)):
            for j in xrange(0, len(paths)):
                if i == paths[j][0]:
                    t = ' '.join(parts[i:paths[j][1]])
                    t = translatepath(t)
                    t = t.strip('"')
                    parts[i] = t
                    for k in xrange(i+1, paths[j][1]):
                        parts[k]=''
        for i in xrange(0, len(parts)):
            if parts[i] != '':
                args.append(parts[i])
    else:
        args = parts
    return args

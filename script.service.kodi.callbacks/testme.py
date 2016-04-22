#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 KenV99
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

######################################################################
#
#  Use to test scripts and arguments
#
######################################################################

import sys



def stripquotes(st):
    if st.startswith('"') and st.endswith('"'):
        return st[1:-1].strip()
    else:
        return st.strip()

def showNotification(args, kwargs):
    # Note that using execfile will not allow for module level imports!
    try:
        import xbmcgui
    except ImportError:
        pass
    else:
        mdialog = xbmcgui.Dialog()
        argmsg = ", ".join(args)
        kwargmsg = []
        for key in kwargs.keys():
            kwargmsg.append('%s:%s' % (key, kwargs[key]))
        mdialog.ok('Test', 'args: %s\nkwargs:: %s' % (argmsg, ', '.join(kwargmsg)))

def processargs(args, kwargs):
    nargs = []
    if isinstance(args, str):
        kwargs = {}
        args = args.split(' ')
        nargs = []
        for arg in args:
            if ":" in arg:
                tmp = arg.split(":", 1)
                try:
                    key = tmp[0]
                    val = tmp[1]
                    val2 = stripquotes(val)
                    kwargs[key] = val2
                except (KeyError, LookupError):
                    pass
            else:
                nargs.append(stripquotes(arg))
    elif isinstance(args, list):
        nargs = args
    if kwargs is None:
        kwargs = {}
    return nargs, kwargs

def run(args=None, kwargs=None):
    args, kwargs = processargs(args, kwargs)
    showNotification(args, kwargs)

if __name__ == '__main__' or __name__ == 'Tasks':
    xargs = []
    kwargs = {}
    if __name__ == '__main__':
        sysargv = sys.argv[1:]
    else:
        sysargv = locals()['args'].strip().split(' ')
    for i, xarg in enumerate(sysargv):
        if ":" in xarg:
            key, entry = xarg.split(':', 1)
            kwargs[key] = stripquotes(entry)
        else:
            xargs.append(stripquotes(xarg))
    run(xargs, kwargs)



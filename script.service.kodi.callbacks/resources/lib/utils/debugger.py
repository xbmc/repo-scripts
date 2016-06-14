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
import sys
import xbmc

class pydevd_dummy(object):
    @staticmethod
    def settrace(*args, **kwargs):
        pass

def startdebugger():
    debugegg = ''
    if sys.platform.lower().startswith('win'):
        debugegg = os.path.expandvars('%programfiles(x86)%\\JetBrains\\PyCharm 2016.1\\debug-eggs\\pycharm-debug.egg')
    elif sys.platform.lower().startswith('darwin'):
        debugegg = '/Applications/PyCharm.app/Contents/debug-eggs/pycharm-debug.egg'
    elif sys.platform.lower().startswith('linux'):
        debugegg = os.path.expandvars(os.path.expanduser('~/Applications/pycharm-2016.1.4/debug-eggs/pycharm-debug.egg'))
    if os.path.exists(debugegg):
        sys.path.append(debugegg)
        try:
            import pydevd
        except ImportError:
            xbmc.log(msg = 'Debugger import error @: "%s"' % debugegg)
            pydevd = pydevd_dummy
        pydevd.settrace('localhost', port=51234, stdoutToServer=True, stderrToServer=True, suspend=False)
    else:
        xbmc.log(msg='Debugger not found @: "%s"' % debugegg)


#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
#
import os
import sys
import traceback as tb
import datetime
import urllib2
import simplejson
import random
import platform

import xbmc
import xbmcgui
import xbmcaddon

#   The full URL to where the gathered data should be posted.
SUBMIT_URL = None

EXTRA_DATA = dict()

def addExtraData(key, value):
    EXTRA_DATA[key] = value

def getRandomHeading():
    """
    Get a random heading for use in dialogs, etc.
    The heading contains a random movie quote from the English strings.xml
    """
    return getLocalizedString(random.randint(90000, 90005))


def getLocalizedString(id):
    """
    Same as Addon.getLocalizedString() but retrieves data from this module's strings.xml
    """
    buggaloAddon = xbmcaddon.Addon(id = 'script.module.buggalo')
    return buggaloAddon.getLocalizedString(id)


def buggalo_try_except(extraData = None):
    """
    @buggalo_try_except function decorator wraps a function in a try..except clause and invokes onExceptionRaised()
    in case an exception is raised. Provide extraData to specific function specific extraData.

    @param extraData: str or dict
    """
    def decorator(fn):
        def wrap_in_try_except(*args, **kwargs):
            try:
                fn(*args, **kwargs)
            except Exception:
                onExceptionRaised(extraData)
        return wrap_in_try_except
    return decorator

def onExceptionRaised(extraData = None):
    """
    Invoke this method in an except clause to allow the user to submit
    a bug report with stacktrace, system information, etc.

    This also avoids the 'Script error' popup in XBMC, unless of course
    an exception is thrown in this code :-)

    @param extraData: str or dict
    """
    # start by logging the usual info to stderr
    (type, value, traceback) = sys.exc_info()
    tb.print_exception(type, value, traceback)

    heading = getRandomHeading()
    line1 = getLocalizedString(91000)
    line2 = getLocalizedString(91001)
    line3 = getLocalizedString(91002)
    yes = getLocalizedString(91003)
    no = getLocalizedString(91004)
    thanks = getLocalizedString(91005)

    if xbmcgui.Dialog().yesno(heading, line1, line2, line3, no, yes):
        data = _gatherData(type, value, traceback, extraData)
        _submitData(data)
        xbmcgui.Dialog().ok(heading, thanks)


def _gatherData(type, value, traceback, extraData):
    data = dict()
    data['version'] = 3
    data['timestamp'] = datetime.datetime.now().isoformat()

    system = dict()
    try:
        if hasattr(os, 'uname'):
            # Works on recent unix flavors
            (sysname, nodename, release, version, machine) = os.uname()
        else:
            # Works on Windows (and others?)
            (sysname, nodename, release, version, machine, processor) = platform.uname()

        system['nodename'] = nodename
        system['sysname'] = sysname
        system['release'] = release
        system['version'] = version
        system['machine'] = machine
    except Exception, ex:
        system['sysname'] = sys.platform
        system['exception'] = str(ex)
    data['system'] = system

    addon = xbmcaddon.Addon()
    addonInfo = dict()
    addonInfo['id'] = addon.getAddonInfo('id')
    addonInfo['name'] = addon.getAddonInfo('name')
    addonInfo['version'] = addon.getAddonInfo('version')
    addonInfo['path'] = addon.getAddonInfo('path')
    addonInfo['profile'] = addon.getAddonInfo('profile')
    data['addon'] = addonInfo

    xbmcInfo = dict()
    xbmcInfo['buildVersion'] = xbmc.getInfoLabel('System.BuildVersion')
    xbmcInfo['buildDate'] = xbmc.getInfoLabel('System.BuildDate')
    xbmcInfo['skin'] = xbmc.getSkinDir()
    xbmcInfo['language'] = xbmc.getInfoLabel('System.Language')
    data['xbmc'] = xbmcInfo

    execution = dict()
    execution['python'] = sys.version
    execution['sys.argv'] = sys.argv
    data['execution'] = execution

    exception = dict()
    exception['type'] = str(type)
    exception['value'] = str(value)
    exception['stacktrace'] = tb.format_tb(traceback)
    data['exception'] = exception

    extraDataInfo = dict()
    try:
        for (key, value) in EXTRA_DATA.items():
            extraDataInfo[key] = str(value)

        if type(extraData) == dict:
            for (key, value) in extraData.items():
                extraDataInfo[key] = str(value)
        elif extraData is not None:
            extraDataInfo[''] = str(extraData)
    except Exception, ex:
        extraDataInfo['exception'] = str(ex)
    data['extraData'] = extraDataInfo

    return simplejson.dumps(data)


def _submitData(data):
    for attempt in range(0, 3):
        try:
            req = urllib2.Request(SUBMIT_URL, data)
            req.add_header('Content-Type', 'text/json')
            u = urllib2.urlopen(req)
            u.read()
            u.close()
            break # success; no further attempts
        except Exception:
            pass # probably timeout; retry




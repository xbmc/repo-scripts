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
import datetime
import os
import platform
import simplejson
import sys
import traceback
import urllib2

import xbmc
import xbmcaddon

import buggalo_userflow as userflow

def gatherData(type, value, tracebackInfo, extraData, globalExtraData):
    data = dict()
    data['version'] = 4
    data['timestamp'] = datetime.datetime.now().isoformat()

    exception = dict()
    exception['stacktrace'] = traceback.format_tb(tracebackInfo)
    exception['type'] = str(type)
    exception['value'] = str(value)
    data['exception'] = exception

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

    data['userflow'] = userflow.loadUserFlow()

    extraDataInfo = dict()
    try:

        for (key, value) in globalExtraData.items():
            if isinstance(extraData, str):
                extraDataInfo[key] = value.decode('utf-8', 'ignore')
            elif isinstance(extraData, unicode):
                extraDataInfo[key] = value
            else:
                extraDataInfo[key] = str(value)

        if isinstance(extraData, dict):
            for (key, value) in extraData.items():
                if isinstance(extraData, str):
                    extraDataInfo[key] = value.decode('utf-8', 'ignore')
                elif isinstance(extraData, unicode):
                    extraDataInfo[key] = value
                else:
                    extraDataInfo[key] = str(value)
        elif extraData is not None:
            extraDataInfo[''] = str(extraData)
    except Exception, ex:
        (type, value, tb) = sys.exc_info()
        traceback.print_exception(type, value, tb)
        extraDataInfo['exception'] = str(ex)
    data['extraData'] = extraDataInfo

    return data


def submitData(serviceUrl, data):
    for attempt in range(0, 3):
        try:
            json = simplejson.dumps(data)
            req = urllib2.Request(serviceUrl, json)
            req.add_header('Content-Type', 'text/json')
            u = urllib2.urlopen(req)
            u.read()
            u.close()
            break # success; no further attempts
        except Exception:
            pass # probably timeout; retry



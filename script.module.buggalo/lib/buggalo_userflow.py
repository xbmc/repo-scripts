#
#      Copyright (C) 2014 Tommy Winther
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
import simplejson

import xbmc
import xbmcaddon

BUGGALO_ADDON = xbmcaddon.Addon('script.module.buggalo')
try:
    ADDON = xbmcaddon.Addon()
except RuntimeError:
    ADDON = None  # Catch and ignore 'No valid addon id could be obtained'


def trackUserFlow(value):
    """
    Registers an entry in the user's flow through the addon.
    The values is stored in a dict with the current time as key and the provided value as the value.

    @param value: the value indicating the user's flow.
    @type value: str
    """
    userFlow = loadUserFlow()
    key = datetime.datetime.now().isoformat()

    userFlow[key] = value
    saveUserFlow(userFlow)


def loadUserFlow():
    if not ADDON:
        return

    path = xbmc.translatePath(BUGGALO_ADDON.getAddonInfo('profile'))
    file = os.path.join(path, '%s.json' % ADDON.getAddonInfo('id'))

    if os.path.exists(file):
        try:
            userFlow = simplejson.load(open(file))
        except Exception:
            userFlow = dict()
    else:
        userFlow = dict()
    return userFlow


def saveUserFlow(userFlow):
    if not ADDON:
        return

    path = xbmc.translatePath(BUGGALO_ADDON.getAddonInfo('profile'))
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            print "unable to create directory for saving userflow; userflow will not be saveds"
            return  # ignore

    try:
        file = os.path.join(path, '%s.json' % ADDON.getAddonInfo('id'))

        # remove entries older than 24 hours
        # we compare strings rather the datetimes (a little hackish though)
        # but datetime.datetime.strptime() often fail for no apparent reason
        # see http://forum.xbmc.org/showthread.php?tid=112916
        oneDayAgo = datetime.datetime.now() - datetime.timedelta(days=1)
        oneDayAgoStr = oneDayAgo.isoformat()
        for dateStr in userFlow.keys():
            if dateStr < oneDayAgoStr:
                del userFlow[dateStr]

        simplejson.dump(userFlow, open(file, 'w'))
    except Exception:
        print "problem saving userflow json file"


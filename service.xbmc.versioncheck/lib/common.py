# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Team-XBMC
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
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonname__    = __addon__.getAddonInfo('name')
__addonpath__    = __addon__.getAddonInfo('path').decode('utf-8')
__addonprofile__ = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode('utf-8')
__icon__         = __addon__.getAddonInfo('icon')

def localise(id):
    string = __addon__.getLocalizedString(id).encode( 'utf-8', 'ignore' )
    return string

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % ("XBMC Version Check", txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def get_password_from_user():
    keyboard = xbmc.Keyboard("", __addonname__ + "," +localise(32022), True)
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        pwd = keyboard.getText()
    return pwd

def message_upgrade_success():
    xbmc.executebuiltin("XBMC.Notification(%s, %s, %d, %s)" %(__addonname__,
                                                              localise(32013),
                                                              15000,
                                                              __icon__))

def message_restart():
    if dialog_yesno(32014):
        xbmc.executebuiltin("RestartApp")

def dialog_yesno(line1 = 0, line2 = 0):
    return xbmcgui.Dialog().yesno(__addonname__,
                                  localise(line1),
                                  localise(line2))

def upgrade_message(msg, oldversion, upgrade):
    # Don't show while watching a video
    while(xbmc.Player().isPlayingVideo() and not xbmc.abortRequested):
        xbmc.sleep(1000)
    i = 0
    while(i < 5 and not xbmc.abortRequested):
        xbmc.sleep(1000)
        i += 1
    # Detect if it's first run and only show OK dialog + ask to disable on that
    firstrun = __addon__.getSetting("versioncheck_firstrun") != 'false'
    if firstrun and not xbmc.abortRequested:
        xbmcgui.Dialog().ok(__addonname__,
                            localise(msg),
                            localise(32001),
                            localise(32002))
        # sets check to false which is checked on startup
        if oldversion == "stable" and dialog_yesno(32009, 32010):
            __addon__.setSetting("versioncheck_enable", 'false')
        # set first run to false to only show a popup next startup / every two days
        __addon__.setSetting("versioncheck_firstrun", 'false')

    # Show notification after firstrun
    elif __addon__.getSetting("versioncheck_enable") == 'true':
        if upgrade:
            return dialog_yesno(msg)
        else:
            xbmc.executebuiltin("XBMC.Notification(%s, %s, %d, %s)" %(__addonname__,
                                                                  localise(32001) + '' + localise(32002),
                                                                  15000,
                                                                  __icon__))
    else:
        pass
    # tells users to upgrade to nightlies as there are no more monthlies
    if oldversion == "monthly":
        upgrademessage = __addon__.getSetting("versioncheck_gotham_alpha_notice") != 'false'
        if upgrademessage:
            __addon__.setSetting("versioncheck_gotham_alpha_notice", 'false')
            runcmd = os.path.join(__addonpath__, 'lib/viewer.py')
            xbmc.executebuiltin('XBMC.RunScript (%s,%s) '%(runcmd, 'gotham-alpha_notice'))

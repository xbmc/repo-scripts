# -*- coding: utf-8 -*-
'''
    screensaver.atv4
    Copyright (C) 2015 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmcaddon
import xbmcgui
import xbmc
import sys
import os
import urllib
from resources.lib import playlist
from resources.lib import atvplayer
from resources.lib import offline as off
from resources.lib.commonatv import *

class Screensaver(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs ):
        pass

    def onInit(self):
        self.getControl(4).setLabel(translate(32008))
        xbmc.executebuiltin("SetProperty(loading,1,home)")
        atvPlaylist = playlist.AtvPlaylist()
        self.videoplaylist = atvPlaylist.getPlaylist()
        if self.videoplaylist:
            xbmc.executebuiltin("ClearProperty(loading,Home)")
            self.atv4player = atvplayer.ATVPlayer()
            self.blackbackground()
            self.atv4player.play(self.videoplaylist,windowed=True)
        else:
            self.novideos()            

    def blackbackground(self):
        self.getControl(1).setImage("black.jpg")
        return

    def novideos(self):
        xbmc.executebuiltin("ClearProperty(loading,Home)")
        self.getControl(3).setLabel(translate(32007))

    def onAction(self,action):
        try: xbmc.PlayList(1).clear()
        except: pass
        xbmc.executebuiltin("PlayerControl(RepeatOff)", True)
        xbmc.executebuiltin("PlayerControl(Stop)")
        try: self.close()
        except: pass

class ScreensaverExitMonitor(xbmc.Monitor):
    def __init__(self):
        self.stopScreensaver = False

    def onScreensaverDeactivated(self):
        self.stopScreensaver = True

    def onScreensaverActivated(self):
        self.stopScreensaver = False

    def isStopScreensaver(self):
        return self.stopScreensaver


def get_params():
    param=[]
    try: paramstring=sys.argv[2]
    except: paramstring = ''
    if len(paramstring)>=2:
        params=sys.argv[2]
        if (params[len(params)-1]=='/'):
            params=params[0:len(params)-2]
        pairsofparams=params.split('/')
        for parm in pairsofparams:
            if parm == '':
                pairsofparams.remove(parm)      
    return pairsofparams

try: params=get_params()
except: params = []


if not params:
    
    exitMon = ScreensaverExitMonitor()
    #Thanks to videoscreensaver. Hit a key, wait for monitor.onDeactivate, start the "screensaver" after that.
    xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ContextMenu", "id": 1}')
    if addon.getSetting("show-notifications") == "true":
        xbmc.executebuiltin("Notification(%s,%s,%i,%s)" % (translate(32000), translate(32017),1,os.path.join(addon_path,"icon.png")))

    
    maxWait = 30

    if not xbmc.getCondVisibility("Player.HasMedia"):
        start_screensaver = True
    else:
        start_screensaver = False

    while not exitMon.isStopScreensaver():
        if (maxWait > 0):
            xbmc.sleep(100)
            maxWait = maxWait - 1
        else:
            start_screensaver = False
            break

    if start_screensaver:
        screensaver = Screensaver(
            'screensaver-atv4.xml',
            addon_path,
            'default',
            '',
        )
        screensaver.doModal()
        xbmc.sleep(100)
        del screensaver
else:
    if params[0] == "offline":
        off.offline()

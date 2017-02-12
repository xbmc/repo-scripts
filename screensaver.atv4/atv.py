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
import json
from resources.lib import playlist
from resources.lib import atvplayer
from resources.lib import offline as off
from trans import ScreensaverTrans
from resources.lib.commonatv import *

class Screensaver(xbmcgui.WindowXML):
    
    def __init__( self, *args, **kwargs ):
        self.DPMStime = json.loads(xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Settings.GetSettingValue","params":{"setting":"powermanagement.displaysoff"},"id":2}'))['result']['value']*60
        self.isDPMSactive = bool(self.DPMStime>0)
        self.active = True
        xbmc.log(msg="kodi dpms time:" + str(self.DPMStime) ,level=xbmc.LOGDEBUG)
        xbmc.log(msg="kodi dpms active:" + str(self.isDPMSactive) ,level=xbmc.LOGDEBUG)


    def onInit(self):
        self.getControl(32502).setLabel(translate(32008))
        xbmc.executebuiltin("SetProperty(screensaver-atv4-loading,1,home)")
        atvPlaylist = playlist.AtvPlaylist()
        self.videoplaylist = atvPlaylist.getPlaylist()
        
        if self.videoplaylist:
            xbmc.executebuiltin("ClearProperty(screensaver-atv4-loading,Home)")
            self.atv4player = atvplayer.ATVPlayer()
            #self.nobackground()
            self.atv4player.play(self.videoplaylist,windowed=True)

            #DPMS logic
            self.max_allowed_time = None

            if self.isDPMSactive and addon.getSetting("check-dpms") == "1":
                self.max_allowed_time = self.DPMStime

            elif addon.getSetting("check-dpms") == "2":
                self.max_allowed_time = int(addon.getSetting("manual-dpms"))*60

            xbmc.log(msg="check dpms:" + str(addon.getSetting("check-dpms")), level=xbmc.LOGDEBUG)
            xbmc.log(msg="before supervision:" + str(self.max_allowed_time) ,level=xbmc.LOGDEBUG)
            if self.max_allowed_time:
                delta = 0
                while self.active:
                    if delta >= self.max_allowed_time:
                        self.activateDPMS()
                        break
                    xbmc.sleep(1000)
                    delta += 1             
        else:
            self.novideos() 

    def activateDPMS(self):
        xbmc.log(msg="[Aerial Screensaver] Manually activating DPMS!",level=xbmc.LOGDEBUG)
        self.active = False

        #take action on the video
        enable_window_placeholder = False
        if addon.getSetting("dpms-action") == "0":
            self.atv4player.pause()
        else:
            self.clearAll()
            enable_window_placeholder = True
        
        if addon.getSetting("toggle-displayoff") == "true" or addon.getSetting("toggle-cecoff") == "true":
            xbmc.sleep(1000)

        if addon.getSetting("toggle-displayoff") == "true":
            try: xbmc.executebuiltin('ToggleDPMS')
            except Exception, e: xbmc.log(msg="[Aerial Screensaver] Failed to toggle DPMS: %s" % (str(e)),level=xbmc.LOGDEBUG)

        if addon.getSetting("toggle-cecoff") == "true":
            try: xbmc.executebuiltin('CECStandby')
            except Exception, e: xbmc.log(msg="[Aerial Screensaver] Failed to toggle device off via CEC: %s" % (str(e)),level=xbmc.LOGDEBUG) 

        #enable placeholder window
        if enable_window_placeholder:
            self.toTransparent()
        
        return          

    #def nobackground(self):
    #    control_list = [self.getControl(32500),self.getControl(32501),self.getControl(32502)]
    #    self.removeControls(control_list)
    #    return

    def novideos(self):
        xbmc.executebuiltin("ClearProperty(screensaver-atv4-loading,Home)")
        self.getControl(32503).setVisible(True)
        self.getControl(32503).setLabel(translate(32007))
        return

    def toTransparent(self):
        trans = ScreensaverTrans(
            'screensaver-atv4-trans.xml',
            addon_path,
            'default',
            '',
        )
        trans.doModal()
        xbmc.sleep(100)
        del trans

    def clearAll(self,close=True):
        self.active = False
        try: xbmc.PlayList(1).clear()
        except: pass
        xbmc.executebuiltin("PlayerControl(RepeatOff)", True)
        xbmc.executebuiltin("PlayerControl(Stop)")
        try: self.close()
        except: pass
        return

    def onAction(self,action):
        addon.setSetting("is_locked","false")
        self.clearAll()


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
    addon.setSetting("is_locked","true")
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

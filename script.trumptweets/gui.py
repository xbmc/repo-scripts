#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Trump Tweets.
#
# Trump Tweets is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Trump Tweets is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Trump Tweets.  If not, see <http://www.gnu.org/licenses/>.

import random, threading
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'script.trumptweets'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
CLOSE_TIME     = [2.0,5.0,10.0,15.0][int(REAL_SETTINGS.getSetting('Close_Time'))]

## GLOBALS ##
ID_LIST        = [30100,30200,30300]
IMG_LIST       = {30101:'TrumpSign_%d.png'  %random.randint(1,4),
                  30201:'TrumpTweet_%d.png' %random.randint(1,5),
                  30301:'TrumpSpeech_%d.png'%random.randint(1,7)}

class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs ):
        random.seed()
        self.closeTimer = threading.Timer(CLOSE_TIME, self.close)
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
            
    def onInit(self):
        select = random.choice(ID_LIST)
        for id in ID_LIST:
            if id != select:
                self.getControl(id).setVisible(False)
        self.getControl(select + 1).setImage(IMG_LIST[select + 1])
        xpos, ypos = self.getControl(select).getPosition()
        width = self.getControl(select + 1).getWidth()
        xmax = 1920 - width
        self.getControl(select).setPosition(random.randrange(xpos,xmax,int(width//4)), ypos)
        self.getControl(select).setVisible(True)
        self.closeTimer.start()

        
    def onAction(self, action):
        self.close()
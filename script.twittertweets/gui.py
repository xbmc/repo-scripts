#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Twitter Tweets.
#
# Twitter Tweets is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Twitter Tweets is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Twitter Tweets.  If not, see <http://www.gnu.org/licenses/>.

import threading
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'script.twittertweets'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')

## GLOBALS ##
DEBUG      = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
CLOSE_TIME = [2.0,5.0,10.0,15.0][int(REAL_SETTINGS.getSetting('Close_Time'))]

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == True:
        if level == xbmc.LOGERROR:
            msg += ' ,' + traceback.format_exc()
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)
         
class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs ):
        self.params     = kwargs['params']
        self.lockAction = False
        self.closeTimer = threading.Timer(CLOSE_TIME, self.close)
    
    
    def onInit(self):
        log('onInit')
        self.lockAction = True
        replies  = (int(filter(str.isdigit, str(self.params['stats'][0])))  or 0)
        retweets = (int(filter(str.isdigit, str(self.params['stats'][1])))  or 0)
        likes    = (int(filter(str.isdigit, str(self.params['stats'][2])))  or 0)
        self.getControl(30111).setLabel('%s'%(' ' if likes    == 0 else str(likes)))
        self.getControl(30110).setLabel('%s'%(' ' if retweets == 0 else str(retweets)))
        self.getControl(30109).setLabel('%s'%(' ' if replies  == 0 else str(replies)))
        self.getControl(30108).setLabel(self.params['time'])
        self.getControl(30107).setText(self.params['title'])
        self.getControl(30106).setLabel('@%s'%self.params['user'])
        self.getControl(30105).setLabel('[B]%s[/B]'%self.params['username'])
        self.getControl(30104).setColorDiffuse('FFdd044d' if likes    > 0 else 'FF999999')
        self.getControl(30103).setColorDiffuse('FF00ff7d' if retweets > 0 else 'FF999999')
        self.getControl(30102).setColorDiffuse('FF1dcaff' if replies  > 0 else 'FF999999')
        self.getControl(30101).setImage(self.params['icon'])
        xbmc.sleep(10)   #give image time to cache.
        self.getControl(30100).setVisible(True)
        self.closeTimer.start()
        xbmc.sleep(1500) #lock action.
        self.lockAction = False
        
        
    def onAction(self, action):
        if self.lockAction == False:
            self.close()
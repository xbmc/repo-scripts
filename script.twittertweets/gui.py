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

import threading, json
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

# Plugin Info
ADDON_ID       = 'script.twittertweets'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')

## GLOBALS ##
CLOSE_TIME = [2.0,5.0,10.0,15.0][int(REAL_SETTINGS.getSetting('Close_Time'))]
              
def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
      
def stringify(string):
    if isinstance(string, list):
        string = (string[0])
    elif isinstance(string, (int, float, long, complex, bool)):
        string = str(string) 
    
    if isinstance(string, basestring):
        if not isinstance(string, unicode):
            string = unicode(string, 'utf-8')
        elif isinstance(string, unicode):
            string = string.encode('ascii', 'ignore')
        else:
            string = string.encode('utf-8', 'ignore')
    return string
    
def getProperty(str):
    try:
        return xbmcgui.Window(10000).getProperty(stringify(str))
    except Exception,e:
        log("getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
def setProperty(str1, str2):
    try:
        xbmcgui.Window(10000).setProperty(stringify(str1), stringify(str2))
    except Exception,e:
        log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(str):
    xbmcgui.Window(10000).clearProperty(stringify(str))
         
class GUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs ):
        self.params     = json.loads(kwargs['params'])
        self.closeTimer = threading.Timer(CLOSE_TIME, self.close)
    
    
    def onInit(self):
        log('onInit')
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
        self.getControl(30100).setVisible(True)
        self.closeTimer.start()
        
        
    def onAction(self, action):
        self.close()
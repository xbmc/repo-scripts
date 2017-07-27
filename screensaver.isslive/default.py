#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Earth View Live in HD Screensaver.
#
# Earth View Live in HD Screensaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Earth View Live in HD Screensaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Earth View Live in HD Screensaver.  If not, see <http://www.gnu.org/licenses/>.

import urllib2, json
import xbmc, xbmcaddon, xbmcgui, traceback

from bs4 import BeautifulSoup

# Plugin Info
ADDON_ID      = 'screensaver.isslive'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')

## GLOBALS ##
BASE_URL = 'http://www.ustream.tv/channel/iss-hdev-payload'

class BackgroundWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)


    def onAction(self, act):
        xbmc.Player().stop()
        self.close()

class ISS():
    def __init__(self):
        self.background = BackgroundWindow('%s.background.xml'%ADDON_ID, ADDON_PATH, "Default")
        self.buildItem(BASE_URL)
          
    def log(self, msg, level=xbmc.LOGDEBUG):
        if level == xbmc.LOGERROR:
            msg += ' ,' + traceback.format_exc()
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg), level)
            
    def buildItem(self, url):
        try:
            soup = BeautifulSoup(urllib2.urlopen(url).read())
            data = json.loads((soup.find(id="UstreamExposedVariables").text.split(';ustream.vars.channelData=')[1]).split(';ustream.vars.videoData')[0])
            url = data['stream']['hls']
            label = data['title']
            thumb = data['picture']['192x192']
            liz = xbmcgui.ListItem(label, url)
            liz.setInfo(type="Video", infoLabels={"mediatype":'video',"label":label,"title":label})
            liz.setArt({"thumb":thumb,"poster":thumb,"fanart":FANART,"logo":data['thumbnail']['live']})
            liz.setProperty("IsPlayable","true")
            liz.setProperty("IsInternetStream","true")
            # live = data['status']
            xbmc.Player().play(url, liz)
            self.background.doModal()
        except Exception,e:
            self.log('buildItem failed ' + str(e),xbmc.LOGERROR)
            
if __name__ == '__main__':
    ISS()

#   Copyright (C) 2017 Lunatixz
#
#
# This file is part of Earth View ScreenSaver.
#
# Earth View ScreenSaver is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Earth View ScreenSaver is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Earth View ScreenSaver.  If not, see <http://www.gnu.org/licenses/>.

import json, os, threading, urllib2, datetime
import xbmc, xbmcaddon, xbmcvfs, xbmcgui

from bs4 import BeautifulSoup

# Plugin Info
ADDON_ID       = 'screensaver.google.earth'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = (REAL_SETTINGS.getAddonInfo('path').decode('utf-8'))
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile').decode('utf-8')
ICON           = REAL_SETTINGS.getAddonInfo('icon').decode('utf-8')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# Global Info
KODI_MONITOR   = xbmc.Monitor()
JSON_FILE      = xbmc.translatePath(os.path.join(SETTINGS_LOC,'earthview.json'))

class Update():
    def __init__(self):
        self.results = []
        
        
    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)
            
        
    def notificationDialog(self, message, header=ADDON_NAME, sound=False, time=1000, icon=ICON):
        try: 
            xbmcgui.Dialog().notification(header, message, icon, time, sound=False)
        except Exception,e:
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (header, message, time, icon))
        
        
    def chkThreads(self):
        self.log('chkThreads')
        for thread in threading.enumerate():
            if thread.isAlive():
                return True
        return False
        
        
    def endThreads(self):
        self.log('endThreads')
        for thread in threading.enumerate():
            if thread.isAlive():
                thread.cancel()
            
            
    def startUpdate(self):
        self.log('startUpdate')
        self.notificationDialog(LANGUAGE(32005))
        urls = []
        for x in xrange(1000, 7030):
            urls.append(str(x))
        threads = [threading.Thread(target=self.updateJson, args=(url,)) for url in urls]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        while not KODI_MONITOR.abortRequested() and not self.chkThreads():
            self.log('startUpdate, abortRequested')
            if KODI_MONITOR.waitForAbort(1) == True:
                self.endThreads()
                break
        self.writeJson()
        
       
    def openURL(self, url):
        self.log('openURL, url = ' + url)
        try:
            response = urllib2.urlopen(url)
            return response.read()
        except urllib2.HTTPError, e:
            return 'null'
        
        
    def updateJson(self, x):
        try:
            response = self.openURL('https://earthview.withgoogle.com/%s'%x)
            if response == 'null':
                raise Exception()
            html = BeautifulSoup(response, "html.parser")
            Region = str((html.find("div", class_="content__location__region")).text.encode('utf-8'))
            Country = str((html.find("div", class_="content__location__country")).text.encode('utf-8'))
            Everything = html.find("a", id="globe", href=True)
            GMapsURL = Everything['href']
            Image = 'https://www.gstatic.com/prettyearth/assets/full/%s.jpg'%x
            self.results.append({'region': Region, 'country': Country, 'map': GMapsURL, 'image': Image})
        except Exception,e:
            pass

            
    def writeJson(self):
        self.log('writeJson')
        if xbmcvfs.exists(JSON_FILE):
            xbmcvfs.delete(JSON_FILE)
        file = open(JSON_FILE,'a')
        now = 'Last Updated - %s'%datetime.datetime.now().strftime('%Y/%m/%d')
        REAL_SETTINGS.setSetting("Update",now)
        file.write(json.dumps(self.results))
        file.close()
        self.notificationDialog(LANGUAGE(32006))
        
        
if __name__ == '__main__':
    Update().startUpdate()
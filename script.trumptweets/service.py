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

import os, gui, feedparser, datetime, random
import xbmc, xbmcaddon, xbmcgui, traceback

# Plugin Info
ADDON_ID       = 'script.trumptweets'
REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME    = REAL_SETTINGS.getAddonInfo('name')
SETTINGS_LOC  = REAL_SETTINGS.getAddonInfo('profile')
ADDON_PATH    = REAL_SETTINGS.getAddonInfo('path').decode('utf-8')
ADDON_VERSION = REAL_SETTINGS.getAddonInfo('version')
ICON          = REAL_SETTINGS.getAddonInfo('icon')
FANART        = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE      = REAL_SETTINGS.getLocalizedString

## GLOBALS ##
DEBUG       = REAL_SETTINGS.getSetting('Enable_Debugging') == 'true'
BASE_FEED   = 'https://twitrss.me/twitter_user_to_rss/?user=realDonaldTrump'

def log(msg, level=xbmc.LOGDEBUG):
    if DEBUG == True:
        if level == xbmc.LOGERROR:
            msg += ' ,' + traceback.format_exc()
        xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + stringify(msg), level)
        
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
        log("Utils: getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
def setProperty(str1, str2):
    try:
        xbmcgui.Window(10000).setProperty(stringify(str1), stringify(str2))
    except Exception,e:
        log("Utils: setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(str):
    xbmcgui.Window(10000).clearProperty(stringify(str))
   
class Service():
    def __init__(self):
        log('__init__')
        random.seed()
        self.myService = xbmc.Monitor()
        while not self.myService.abortRequested():
            WAIT_TIME = [300,600,900,1800][int(REAL_SETTINGS.getSetting('Wait_Time'))]
            IGNORE = REAL_SETTINGS.getSetting('Not_While_Playing') == 'true'
            if xbmc.Player().isPlayingVideo() == True and IGNORE == True:
                self.myService.waitForAbort(WAIT_TIME)
                continue
            self.chkFEED()
            if self.myService.waitForAbort(WAIT_TIME) == True:
                break

                
    def testString(self):
        ''' 
        gen. 140char mock sentence for skin test
        '''
        a = ''
        for i in range(1,141):
            a += 'W%s'%random.choice(['',' '])
        return a[:140]
        

    def chkFEED(self):
        log('chkFEED')
        feed   = feedparser.parse(BASE_FEED)
        items  = feed['entries']
        index  = {True:random.randint(0,(len(items)-1)),False:0}[int(REAL_SETTINGS.getSetting('Enable_Random')) == 1]
        item   = items[index]
        if item and 'summary_detail' in item:
            title = (stringify(item['title']).replace('\n','').replace('\t','').replace('\r','').rstrip())
            pdate = item.get('published','').split('+')[0].rstrip()
            if getProperty('%s.pdate' %ADDON_ID) != pdate:
                setProperty('%s.title'%ADDON_ID,title)
                setProperty('%s.pdate'%ADDON_ID,pdate)
                ui = gui.GUI("default.xml", ADDON_PATH, "default")
                ui.doModal()
                del ui
    
if __name__ == '__main__':
    Service()
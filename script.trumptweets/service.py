#   Copyright (C) 2018 Lunatixz
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

import os, gui, time, datetime, random, urllib2, re
import xbmc, xbmcaddon, xbmcgui, traceback, feedparser

# Plugin Info
ADDON_ID      = 'script.trumptweets'
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
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + msg, level)

def getProperty(string1, cntrl=10000):
    return xbmcgui.Window(cntrl).getProperty(string1)
          
def setProperty(string1, value, cntrl=10000):
    try: xbmcgui.Window(cntrl).setProperty(string1, value)
    except Exception as e: log("setProperty, failed! " + str(e), xbmc.LOGERROR)

def clearProperty(string1, cntrl=10000):
    xbmcgui.Window(cntrl).clearProperty(string1)

class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.pendingChange = True

        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        self.pendingChange = True
        
class Service(object):
    def __init__(self):
        random.seed()
        self.myMonitor = Monitor()
        self.startService()
        
        
    def startService(self):
        while not self.myMonitor.abortRequested():
            if self.myMonitor.pendingChange == True:
                self.myMonitor.pendingChange = False
                REAL_SETTINGS = xbmcaddon.Addon(id=ADDON_ID)
                waitTime   = [300,600,900,1800][int(REAL_SETTINGS.getSetting('Wait_Time'))]
                ignorePlay = REAL_SETTINGS.getSetting('Not_While_Playing') == 'true'
            
            # Don't run while playing.
            if xbmc.Player().isPlayingVideo() == True and ignorePlay == True:
                log('startService, ignore during playback')
                continue

            # Don't run while setting menu is opened.
            if xbmcgui.getCurrentWindowDialogId() in [10140,10103]:
                log('startService, settings dialog opened')
                continue
        
            self.chkFEED()
            
            # Sleep
            if self.myMonitor.waitForAbort(waitTime) == True:
                log('startService, waitForAbort/pendingChange')
                break
    

    def testString(self):
        #gen. 140char mock sentence for skin test
        a = ''
        for i in range(1,281): a += 'W%s'%random.choice(['',' '])
        return a[:280]
        
        
    def correctTime(self, tweetTime):
        log('correctTime, IN tweetTime = '+ tweetTime)
        tweetTime  = datetime.datetime.strptime(tweetTime, '%a, %d %b %Y %H:%M:%S')
        td_local   = tweetTime - datetime.timedelta(seconds=3600)
        tweetTime  = td_local.strftime('%a, %d %b %Y %I:%M:%S %p').lstrip('0')
        log('correctTime, OUT tweetTime = '+ tweetTime)
        return tweetTime
        
        
    def chkFEED(self):
        log('chkFEED')
        try:
            isRandom = int(REAL_SETTINGS.getSetting('Enable_Random')) == 1
            feed     = feedparser.parse(BASE_FEED)
            items    = feed['entries']
            index    = {True:random.randint(0,(len(items)-1)),False:0}[isRandom]
            item     = items[index]
            title    = ((item['title']).replace('\n','').replace('\t','').replace('\r','').rstrip())
            pdate    = self.correctTime(item.get('published','').split('+')[0].rstrip())
            if getProperty('%s.pdate' %ADDON_ID) == pdate: return
            setProperty('%s.title'%ADDON_ID,title)
            setProperty('%s.pdate'%ADDON_ID,pdate)
            ui = gui.GUI("default.xml", ADDON_PATH, "default")
            ui.doModal()
            del ui
        except: pass
                
if __name__ == '__main__': Service()
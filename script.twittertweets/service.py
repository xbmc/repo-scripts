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

import os, gui, datetime, random, urllib2, json
import xbmc, xbmcaddon, xbmcgui, traceback

from bs4 import BeautifulSoup

# Plugin Info
ADDON_ID       = 'script.twittertweets'
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
BASE_URL    = 'http://twitter.com/'

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
   
class Service():
    def __init__(self):
        log('__init__')
        random.seed()
        self.myService = xbmc.Monitor()
        while not self.myService.abortRequested():
            self.userList = []
            for i in range(1,51):
                self.userList.append((REAL_SETTINGS.getSetting('FEED%d'%i)).replace('@',''))
            self.userList = filter(None, self.userList)
            log('userList = ' + str(self.userList))

            WAIT_TIME = [300,600,900,1800][int(REAL_SETTINGS.getSetting('Wait_Time'))]
            IGNORE    = REAL_SETTINGS.getSetting('Not_While_Playing') == 'true'
            if xbmc.Player().isPlayingVideo() == True and IGNORE == True:
                self.myService.waitForAbort(WAIT_TIME)
                continue
                
            for user in self.userList:
                self.chkFEED(user)
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
        

    def chkFEED(self, user):
        log('chkFEED, user='+user)
        try:
            soup       = BeautifulSoup(urllib2.urlopen(BASE_URL+user).read())
            twitterPic = soup('img' , {'class': 'ProfileAvatar-image'})[0].attrs['src']
            twitterAlt = soup('img' , {'class': 'ProfileAvatar-image'})[0].attrs['alt']
            tweetTimes = soup('a'   , {'class': 'tweet-timestamp js-permalink js-nav js-tooltip'})
            tweetMsgs  = soup('p'   , {'class': 'TweetTextSize TweetTextSize--normal js-tweet-text tweet-text'})
            tweetStats = soup('span', {'class': 'ProfileTweet-actionCountForAria'})

            #find latest tweet from user, ignore retweets.
            for idx, item in enumerate(tweetTimes):
                if user.lower() in item.attrs['href'].lower():
                    break
                    
            tweetTime  = tweetTimes[idx]["title"]
            tweetMsg   = tweetMsgs[idx].get_text()
            tweetStats = [stat.get_text() for stat in tweetStats]
            tweetStats = [tweetStats[x:x+3] for x in xrange(0, len(tweetStats), 3)]
            tweetStats = tweetStats[idx]
        except Exception,e:
            log('chkFEED, failed! ' + str(e))
            return
            
        if REAL_SETTINGS.getSetting('%s.%s.time' %(ADDON_ID,user)) != tweetTime:
            REAL_SETTINGS.setSetting('%s.%s.time'%(ADDON_ID,user),tweetTime)
            ui = gui.GUI("%s.default.xml" %ADDON_ID,ADDON_PATH,"default",params=json.dumps({'user':user,'icon':twitterPic,'username':twitterAlt,'title':tweetMsg,'time':tweetTime,'stats':tweetStats}))
            ui.doModal()
            del ui

if __name__ == '__main__':
    Service()
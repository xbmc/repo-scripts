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

import os, gui, time, datetime, random, urllib2, re
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
    if DEBUG == False and level != xbmc.LOGERROR: return
    if level == xbmc.LOGERROR: msg += ' ,' + traceback.format_exc()
    xbmc.log(ADDON_ID + '-' + ADDON_VERSION + '-' + (msg.encode("utf-8")), level)
     
def getProperty(str):
    try: return xbmcgui.Window(10000).getProperty((str))
    except Exception as e:
        log("getProperty, Failed! " + str(e), xbmc.LOGERROR)
        return ''
          
def setProperty(str1, str2):
    try: xbmcgui.Window(10000).setProperty((str1), (str2))
    except Exception as e:
        log("setProperty, Failed! " + str(e), xbmc.LOGERROR)

def clearProperty(str):
    xbmcgui.Window(10000).clearProperty((str))
   
   
class Monitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        self.pendingChange = False

        
    def onSettingsChanged(self):
        log('onSettingsChanged')
        self.pendingChange = True

        
class Service(object):
    def __init__(self):
        log('__init__')
        self.myMonitor = Monitor()
        self.startService()
        
        
    def startService(self):
        log('startService')
        self.checkSettings()
        while not self.myMonitor.abortRequested():
            for user in self.userList:
                # Don't run while pending changes and wait two seconds between each chkfeed.
                if self.myMonitor.pendingChange == True or self.myMonitor.waitForAbort(2) == True: 
                    log('startService, waitForAbort/pendingChange')
                    continue
                                    
                # Don't run while playing.
                if xbmc.Player().isPlayingVideo() == True and self.ignore == True:
                    log('startService, ignore during playback')
                    continue

                # Don't run while setting menu is opened.
                if xbmcgui.getCurrentWindowDialogId() in [10140,10103]:
                    log('startService, settings dialog opened')
                    continue

                self.chkFEED(user)
                
            if self.myMonitor.pendingChange == True or self.myMonitor.waitForAbort(self.wait) == True:
                log('startService, waitForAbort/pendingChange')
                break

        if self.myMonitor.pendingChange == True:
            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, LANGUAGE(30012), 4000, ICON))
            self.restartService()
            
        
    def restartService(self):
        log('restartService')
        #adapted from advised method https://forum.kodi.tv/showthread.php?tid=248758
        xbmc.sleep(500)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":false}, "id": 1}'%(ADDON_ID))
        xbmc.sleep(500)
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method":"Addons.SetAddonEnabled","params":{"addonid":"%s","enabled":true}, "id": 1}'%(ADDON_ID))
            
                
    def checkSettings(self):
        self.wait        = [60,120,240,360,480,600][int(REAL_SETTINGS.getSetting('Wait_Time'))]
        self.ignore      = REAL_SETTINGS.getSetting('Not_While_Playing') == 'true'
        self.incRetweets = REAL_SETTINGS.getSetting('Include_Retweets') == 'true'
        userList = []
        for i in range(1,51): userList.append((REAL_SETTINGS.getSetting('FEED%d'%i)).replace('@',''))
        self.userList = filter(None, userList)
        self.myMonitor.pendingChange = False
        log('checkSettings, ignore = '   + str(self.ignore))
        log('checkSettings, wait = '     + str(self.wait))
        log('checkSettings, userList = ' + str(self.userList))
        

    def testString(self):
        #gen. 140char mock sentence for skin test
        a = ''
        for i in range(1,141): a += 'W%s'%random.choice(['',' '])
        return a[:140]
        

    def cleanString(self, string):
        string = re.sub(r"http\S+", "", string)
        string = re.sub(r"pic.twitter.com", "", string)
        return string
        
        
    def correctTime(self, tweetTime):
        log('correctTime, IN tweetTime = '+ tweetTime)
        tweetTime  = datetime.datetime.strptime(tweetTime, '%I:%M %p - %d %b %Y')
        is_dst     = time.daylight and time.localtime().tm_isdst > 0
        utc_offset = + (time.altzone if is_dst else time.timezone)
        td_local   = tweetTime + datetime.timedelta(seconds=utc_offset-3600)
        tweetTime  = td_local.strftime('%I:%M %p - %d %b %Y').lstrip('0')
        log('correctTime, OUT tweetTime = '+ tweetTime)
        return tweetTime
        
        
    def chkFEED(self, user):
        log('chkFEED, user = '+user)
        try:
            soup        = BeautifulSoup(urllib2.urlopen(BASE_URL+user).read(), "html.parser")
            twitterPic  = soup('img' , {'class': 'ProfileAvatar-image'})[0].attrs['src']
            twitterAlt  = soup('img' , {'class': 'ProfileAvatar-image'})[0].attrs['alt']
            twitterVer  = True if soup.find(href='/help/verified') else False
            tweetTimes  = soup('a'   , {'class': 'tweet-timestamp js-permalink js-nav js-tooltip'})
            tweetMsgs   = soup('div' , {'class': 'js-tweet-text-container'})
            tweetAtts   = soup('div' , {'class': 'AdaptiveMediaOuterContainer'})
            tweetStats  = soup('span', {'class': 'ProfileTweet-actionCountForAria'})
            twitterPin  = len(soup('span' , {'class': 'js-pinned-text'})) > 0
            tmpThumb    = None
            tmpVideo    = None
            tmpImage    = None
            
            for idx, item in enumerate(tweetTimes):
                if idx == 0 and twitterPin == True and user.lower() in item.attrs['href'].lower(): continue
                elif self.incRetweets == True: break
                elif user.lower() in item.attrs['href'].lower(): break
            
            try:                 
                tmpAttach = tweetMsgs[idx]('a', {'class': 'twitter-timeline-link u-hidden'})[0].get_text()
                tmpImage = tweetAtts[idx].find('img').attrs['src'] if tmpAttach.startswith('pic.twitter.com') else None
            except: tmpImage = None

            try:
                tmpThumb    = tweetAtts[idx]('div', {'class': 'PlayableMedia-container'})
                tmpThumb    = tmpThumb[0]('div', {'class': 'PlayableMedia-player'})[0]
                tmpThumb    = re.findall("background-image:url(.*)'", str(tmpThumb))[0].replace("('",'')
            except: tmpThumb = None
            
            if tmpThumb is not None:
                tmpVideo    = tmpThumb.replace('pbs.twimg.com/tweet_video_thumb/','video.twimg.com/tweet_video/').replace('.jpg','.mp4')
            
            tmpImage    = tmpImage if tmpThumb is None else tmpThumb
            tweetTime   = self.correctTime(tweetTimes[idx]["title"].encode("utf-8"))
            tweetMsg    = self.cleanString((tweetMsgs[idx]('p' , {'class': 'TweetTextSize TweetTextSize--normal js-tweet-text tweet-text'})[0].get_text()).encode("utf-8"))
            tweetStats  = [stat.get_text().encode("utf-8") for stat in tweetStats]
            tweetStats  = [tweetStats[x:x+3] for x in xrange(0, len(tweetStats), 3)]
            tweetStats = tweetStats[idx]
            if len(tweetMsg) == 0: return
            
            # test
            # tmpImage = 'https://pbs.twimg.com/tweet_video_thumb/DOubaqGWAAEBPWn.jpg'
            # tmpVideo = 'https://video.twimg.com/tweet_video/DOubaqGWAAEBPWn.mp4'
            # test
            
            if getProperty('%s.%s.time' %(ADDON_ID,user)) != tweetTime:
                setProperty('%s.%s.time'%(ADDON_ID,user),tweetTime)
                ui = gui.GUI("%s.default.xml" %ADDON_ID,ADDON_PATH,"default",params=({'user':user,'video':tmpVideo,'image':tmpImage,'icon':twitterPic,'username':twitterAlt,'title':tweetMsg,'time':tweetTime,'stats':tweetStats,'verified':twitterVer}))
                ui.doModal()
        except Exception as e: log('chkFEED, failed! ' + str(e))
            
if __name__ == '__main__':
    Service()
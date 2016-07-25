#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon
import unicodedata
import json

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo('icon')
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')
__notifications__ = __addon__.getSetting('notifications')

from resources.lib.tvshowtime import FindEpisode
from resources.lib.tvshowtime import MarkAsWatched
from resources.lib.tvshowtime import MarkAsUnWatched
from resources.lib.tvshowtime import GetUserInformations
from resources.lib.tvshowtime import SaveProgress
from resources.lib.tvshowtime import SetEmotion

class Monitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']
        self._total_time = 999999
        self._last_pos = 0
        self._tracker = None
        self._playback_lock = threading.Event()

    def _trackPosition(self):
        while self._playback_lock.isSet() and not xbmc.abortRequested:
            try:
                self._last_pos = player.getTime()
            except:
                self._playback_lock.clear()
            log('Inside Player. Tracker time = %s' % self._last_pos)
            xbmc.sleep(250)
        log('Position tracker ending with last_pos = %s' % self._last_pos)

    def _setUp(self):
        self._playback_lock.set()
        self._tracker = threading.Thread(target=self._trackPosition)

    def _tearDown(self):
        if hasattr(self, '_playback_lock'):
            self._playback_lock.clear()
        self._monitor = None
        if not hasattr(self, '_tracker'):
            return
        if self._tracker is None:
            return
        if self._tracker.isAlive():
            self._tracker.join()
        self._tracker = None

    def onSettingsChanged( self ):
        log('onSettingsChanged')
        self.action()
        
    def onNotification(self, sender, method, data):
        log('onNotification')
        log('method=%s' % method)
        if (method == 'Player.OnPlay'):
            self._setUp()
            self._total_time = player.getTotalTime()
            self._tracker.start()
            log('Player.OnPlay')
            if player.http == 'true' and player.getPlayingFile()[:4] == 'http' and re.search(r'[sS][0-9]*[eE][0-9]*', os.path.basename(player.getPlayingFile()), flags=0) :
                player.http_playing = True
                player.filename = os.path.basename(player.getPlayingFile())
                self.startcut = player.filename.find("%5B")
                self.endcut = player.filename.find("%5D")
                self.tocut = player.filename[self.startcut:self.endcut]
                player.filename = player.filename.replace(self.tocut, "")
                player.filename = player.filename.replace("%5B", "")
                player.filename = player.filename.replace("%5D", "")
                player.filename = player.filename.replace("%20", ".")
                log('tvshowtitle=%s' % player.filename)
                player.episode = FindEpisode(player.token, 0, player.filename)
                log('episode.is_found=%s' % player.episode.is_found)
                if player.episode.is_found:
                    if player.notifications == 'true':                        
                        if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                            return
                        if player.notif_scrobbling == 'false':
                            return
                        notif('%s %s %sx%s' % (__language__(32904), player.episode.showname, player.episode.season_number, player.episode.number), time=2500)
                else:
                    if player.notifications == 'true':
                        if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                            return
                        notif(__language__(32905), time=2500)
            else:
                player.http_playing = False
                response = json.loads(data) 
                log('%s' % response)
                if response.get('item').get('type') == 'episode':
                    xbmc_id = response.get('item').get('id')
                    item = self.getEpisodeTVDB(xbmc_id)    
                    log('showtitle=%s' % item['showtitle'])
                    log('season=%s' % item['season'])
                    log('episode=%s' % item['episode'])
                    log('episode_id=%s' % item['episode_id'])
                    if len(item['showtitle']) > 0 and item['season'] > 0 and item['episode'] > 0 and item['episode_id'] > 0:                   
                        player.filename = '%s.S%.2dE%.2d' % (formatName(item['showtitle']), float(item['season']), float(item['episode']))
                        log('tvshowtitle=%s' % player.filename)
                        player.episode = FindEpisode(player.token, item['episode_id'])
                        log('episode.is_found=%s' % player.episode.is_found)
                        if player.episode.is_found:
                            if player.notifications == 'true':                        
                                if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                    return
                                if player.notif_scrobbling == 'false':
                                    return
                                notif('%s %s %sx%s' % (__language__(32904), player.episode.showname, player.episode.season_number, player.episode.number), time=2500)
                        else:
                            if player.notifications == 'true':
                                if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                    return
                                notif(__language__(32905), time=2500)
                    else:
                        if player.notifications == 'true':
                            if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                return
                            notif(__language__(32905), time=2500)              
        if (method == 'Player.OnStop'): 
            self._tearDown()
            actual_percent = (self._last_pos/self._total_time)*100
            log('last_pos / total_time : %s / %s = %s %%' % (self._last_pos, self._total_time, actual_percent)) 
            log('Player.OnStop') 
            if player.http == 'true' and player.http_playing == True :
                if player.progress == 'true':
                    player.episode = FindEpisode(player.token, 0, player.filename)
                    log('episode.is_found=%s' % player.episode.is_found)
                    if player.episode.is_found:
                        log('progress=%s' % self._last_pos)
                        self.progress = SaveProgress(player.token, player.episode.id, self._last_pos)   
                        log('progress.is_set:=%s' % self.progress.is_set)  
                        if actual_percent > 90:
                            log('MarkAsWatched(*, %s, %s, %s)' % (player.filename, player.facebook, player.twitter))
                            checkin = MarkAsWatched(player.token, player.episode.id, player.facebook, player.twitter)
                            log('checkin.is_marked:=%s' % checkin.is_marked)
                            if checkin.is_marked:
                                if player.emotion == 'true':
                                    self.emotion = xbmcgui.Dialog().select('%s: %s %sx%s' % (__language__(33909), player.episode.showname, player.episode.season_number, player.episode.number), [__language__(35311), __language__(35312), __language__(35313), __language__(35314), __language__(35316), __language__(35317)])
                                    if self.emotion < 0: return
                                    if self.emotion == 0:
                                        self.emotion = 1
                                    elif self.emotion == 1:
                                        self.emotion = 2
                                    elif self.emotion == 2:
                                        self.emotion = 3
                                    elif self.emotion == 3:
                                        self.emotion = 4
                                    elif self.emotion == 4:
                                        self.emotion = 6
                                    elif self.emotion == 5:
                                        self.emotion = 7
                                    SetEmotion(player.token, player.episode.id, self.emotion)
                                if player.notifications == 'true':
                                    if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                        return
                                    if player.notif_scrobbling == 'false':
                                        return
                                    notif('%s %s %sx%s' % (__language__(32906), player.episode.showname, player.episode.season_number, player.episode.number), time=2500) 
            else:       
                response = json.loads(data) 
                log('%s' % response)
                if player.progress == 'true':
                    if response.get('item').get('type') == 'episode':
                        xbmc_id = response.get('item').get('id')
                        item = self.getEpisodeTVDB(xbmc_id)    
                        log('showtitle=%s' % item['showtitle'])
                        log('season=%s' % item['season'])
                        log('episode=%s' % item['episode'])
                        log('episode_id=%s' % item['episode_id'])
                        if len(item['showtitle']) > 0 and item['season'] > 0 and item['episode'] > 0 and item['episode_id'] > 0:                   
                            player.filename = '%s.S%.2dE%.2d' % (formatName(item['showtitle']), float(item['season']), float(item['episode']))
                            log('tvshowtitle=%s' % player.filename)
                        log('progress=%s' % self._last_pos)
                        self.progress = SaveProgress(player.token, item['episode_id'], self._last_pos)   
                        log('progress.is_set:=%s' % self.progress.is_set)                                
        if (method == 'VideoLibrary.OnUpdate'):
            log('VideoLibrary.OnUpdate')
            response = json.loads(data) 
            log('%s' % response)
            if response.get('item').get('type') == 'episode':
                xbmc_id = response.get('item').get('id')
                playcount = response.get('playcount') 
                log('playcount=%s' % playcount)
                item = self.getEpisodeTVDB(xbmc_id)    
                log('showtitle=%s' % item['showtitle'])
                log('season=%s' % item['season'])
                log('episode=%s' % item['episode'])
                log('episode_id=%s' % item['episode_id'])
                log('playcount=%s' % playcount)
                if len(item['showtitle']) > 0 and item['season'] > 0 and item['episode'] > 0 and item['episode_id'] > 0:
                    self.filename = '%s.S%.2dE%.2d' % (formatName(item['showtitle']), float(item['season']), float(item['episode']))
                    log('tvshowtitle=%s' % self.filename)
                    self.episode = FindEpisode(player.token, item['episode_id'])
                    log('episode.is_found=%s' % self.episode.is_found)
                    if self.episode.is_found:
                        if playcount is 1:
                            log('MarkAsWatched(*, %s, %s, %s)' % (self.filename, player.facebook, player.twitter))
                            checkin = MarkAsWatched(player.token, item['episode_id'], player.facebook, player.twitter)
                            log('checkin.is_marked:=%s' % checkin.is_marked)
                            if checkin.is_marked:
                                if player.emotion == 'true':
                                    self.emotion = xbmcgui.Dialog().select('%s: %s' % (__language__(33909), self.filename), [__language__(35311), __language__(35312), __language__(35313), __language__(35314), __language__(35316), __language__(35317)])
                                    if self.emotion < 0: return
                                    if self.emotion == 0:
                                        self.emotion = 1
                                    elif self.emotion == 1:
                                        self.emotion = 2
                                    elif self.emotion == 2:
                                        self.emotion = 3
                                    elif self.emotion == 3:
                                        self.emotion = 4
                                    elif self.emotion == 4:
                                        self.emotion = 6
                                    elif self.emotion == 5:
                                        self.emotion = 7
                                    SetEmotion(player.token, item['episode_id'], self.emotion)
                                if player.notifications == 'true':
                                    if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                        return
                                    if player.notif_scrobbling == 'false':
                                        return
                                    notif('%s %s %sx%s' % (__language__(32906), self.episode.showname, self.episode.season_number, self.episode.number), time=2500)
                            else:
                                if player.notifications == 'true':
                                    if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                        return
                                    notif(__language__(32907), time=2500)
                        if playcount is 0:
                            log('MarkAsUnWatched(*, %s)' % (self.filename))
                            checkin = MarkAsUnWatched(player.token, item['episode_id'])
                            log('checkin.is_unmarked:=%s' % checkin.is_unmarked)
                            if checkin.is_unmarked:
                                if player.notifications == 'true':
                                    if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                        return
                                    if player.notif_scrobbling == 'false':
                                        return
                                    notif('%s %s %sx%s' % (__language__(32908), self.episode.showname, self.episode.season_number, self.episode.number), time=2500)
                            else:
                                if player.notifications == 'true':
                                    if player.notif_during_playback == 'false' and player.isPlaying() == 1:
                                        return
                                    notif(__language__(32907), time=2500)

    def getEpisodeTVDB(self, xbmc_id):
        rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params': {"episodeid": int(xbmc_id), 'properties': ['season', 'episode', 'tvshowid', 'showtitle', 'uniqueid']}, 'id': 1}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)        
        log('result=%s' % result)    
        log('episode_id=%s' % result['result']['episodedetails']['uniqueid']['unknown'])
        
        try:
            item = {}
            item['season'] = result['result']['episodedetails']['season']
            item['tvshowid'] = result['result']['episodedetails']['tvshowid']
            item['episode'] = result['result']['episodedetails']['episode']
            item['showtitle'] = result['result']['episodedetails']['showtitle']
            item['episode_id'] = result['result']['episodedetails']['uniqueid']['unknown']
            return item
        except:
            return False
            
    def getAllEpisodes(self, xbmc_id):
        rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {"tvshowid": int(xbmc_id), 'properties': ['season', 'episode', 'showtitle', 'playcount']}, 'id': 1}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
        return result

class Player(xbmc.Player):

    def __init__ (self):
        xbmc.Player.__init__(self)
        log('Player - init')
        self.token = __addon__.getSetting('token')
        self.facebook = __addon__.getSetting('facebook')
        self.twitter = __addon__.getSetting('twitter')
        self.welcome = __addon__.getSetting('welcome')
        self.notifications = __addon__.getSetting('notifications')
        self.notif_during_playback = __addon__.getSetting('notif_during_playback')
        self.notif_scrobbling = __addon__.getSetting('notif_scrobbling')
        self.progress = __addon__.getSetting('progress')
        self.http = __addon__.getSetting('http')
        self.http_playing = False
        self.emotion = __addon__.getSetting('emotion')
        self.defaultemotion = __addon__.getSetting('defaultemotion')
        if self.token is '':
            log(__language__(32901))
            if self.notifications == 'true':
                notif(__language__(32901), time=2500)
            return
        self.user = self._GetUser()
        if not self.user.is_authenticated:
            return
        self._monitor = Monitor(action = self._reset)
        log('Player - monitor')
        
    def _reset(self):
        self.__init__()
                                  
    def _GetUser(self):
        log('_GetUser')
        user = GetUserInformations(self.token)
        if user.is_authenticated:
            __addon__.setSetting('user', user.username)
            if self.notifications == 'true':
                if self.welcome == 'true':
                    notif('%s %s' % (__language__(32902), user.username), time=2500)
        else:
            __addon__.setSetting('user', '')
            if self.notifications == 'true':
                notif(__language__(32903), time=2500)
        return user

def formatNumber(number):
    if len(number) < 2:
         number = '0%s' % number
    return number
     
def formatName(filename):
    filename = filename.strip()
    filename = filename.replace(' ', '.')
    return normalizeString(filename)
    
def notif(msg, time=5000):
    xbmcgui.Dialog().notification(encode(__scriptname__), encode(msg), time=time, icon=__icon__)

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, encode(msg), ),
            level=xbmc.LOGDEBUG) #100 #xbmc.LOGDEBUG

def encode(string):
    result = ''
    try:
        result = string.encode('UTF-8','replace')
    except UnicodeDecodeError:
        result = 'UTF-8 Error'
    return result

def normalizeString(str):
    return unicodedata.normalize('NFKD', str).encode('ascii','ignore').encode('UTF-8','replace')

if ( __name__ == "__main__" ):
    player = Player()
    log("[%s] - Version: %s Started" % (__scriptname__, __version__))
    while not xbmc.abortRequested:
        xbmc.sleep(100)
    player._monitor = None
    log("sys.exit(0)")
    sys.exit(0)
    

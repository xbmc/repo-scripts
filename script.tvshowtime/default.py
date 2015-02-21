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
__icon__          = __addon__.getAddonInfo("icon")
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

from resources.lib.tvshowtime import FindEpisode
from resources.lib.tvshowtime import MarkAsWatched
from resources.lib.tvshowtime import MarkAsUnWatched
from resources.lib.tvshowtime import GetUserInformations

class Monitor(xbmc.Monitor):
    def __init__( self, *args, **kwargs ):
        xbmc.Monitor.__init__( self )
        self.action = kwargs['action']

    def onSettingsChanged( self ):
        log('onSettingsChanged')
        self.action()
        
    def onNotification(self, sender, method, data):
        log('onNotification')
        log('method=%s' % method)
        if (method == 'Player.OnPlay'):
            log('Player.OnPlay')
            response = json.loads(data) 
            log('%s' % response)
            if response.get('item').get('type') == 'episode':
                xbmc_id = response.get('item').get('id')
                item = self.getEpisodeTVDB(xbmc_id)    
                log('showtitle=%s' % item['showtitle'])
                log('season=%s' % item['season'])
                log('episode=%s' % item['episode'])
                if len(item['showtitle']) > 0 and item['season'] > 0 and item['episode'] > 0:                   
                    player.filename = '%s.S%sE%s' % (formatName(item['showtitle']), item['season'], item['episode'])
                    log('tvshowtitle=%s' % player.filename)
                    player.episode = FindEpisode(player.token, player.filename)
                    log('episode.is_found=%s' % player.episode.is_found)
                    if player.episode.is_found:
                        if player.notifications:            
                            notif('%s %s %sx%s' % (__language__(32904), player.episode.showname, player.episode.season_number, player.episode.number), time=2500)
                    else:
                        if player.notifications:
                            notif(__language__(32905), time=2500)
                else:
                    if player.notifications:
                        notif(__language__(32905), time=2500)
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
                log('playcount=%s' % playcount)
                if len(item['showtitle']) > 0 and item['season'] > 0 and item['episode'] > 0:
                    self.filename = '%s.S%sE%s' % (formatName(item['showtitle']), item['season'], item['episode'])
                    log('tvshowtitle=%s' % self.filename)
                    self.episode = FindEpisode(player.token, self.filename)
                    log('episode.is_found=%s' % self.episode.is_found)
                    if self.episode.is_found:
                        if playcount is 1:
                            log('MarkAsWatched(*, %s, %s, %s)' % (self.filename, player.facebook, player.twitter))
                            checkin = MarkAsWatched(player.token, self.filename, player.facebook, player.twitter)
                            log('checkin.is_marked:=%s' % checkin.is_marked)
                            if checkin.is_marked:
                                if player.notifications:
                                    notif('%s %s %sx%s' % (__language__(32906), self.episode.showname, self.episode.season_number, self.episode.number), time=2500)
                                else:
                                    if player.notifications:
                                        notif(__language__(32907), time=2500)
                        if playcount is 0:
                            log('MarkAsUnWatched(*, %s)' % (self.filename))
                            checkin = MarkAsUnWatched(player.token, self.filename)
                            log('checkin.is_unmarked:=%s' % checkin.is_unmarked)
                            if checkin.is_unmarked:
                                if player.notifications:
                                    notif('%s %s %sx%s' % (__language__(32908), self.episode.showname, self.episode.season_number, self.episode.number), time=2500)
                                else:
                                    if player.notifications:
                                        notif(__language__(32907), time=2500)

    def getEpisodeTVDB(self, xbmc_id):
        rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodeDetails', 'params': {"episodeid": int(xbmc_id), 'properties': ['season', 'episode', 'tvshowid', 'showtitle']}, 'id': 1}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        result = json.loads(result)
        
        try:
            item = {}
            item['season'] = result['result']['episodedetails']['season']
            item['tvshowid'] = result['result']['episodedetails']['tvshowid']
            item['episode'] = result['result']['episodedetails']['episode']
            item['showtitle'] = result['result']['episodedetails']['showtitle']
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
        self.notifications = __addon__.getSetting('notifications')
        if self.token is '':
            log(__language__(32901))
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
            if self.notifications:
                notif('%s %s' % (__language__(32902), user.username), time=2500)
        else:
            notif(__language__(32903), time=2500)
        return user

def formatNumber(number):
    if len(number) < 2:
         number = '0%s' % number
    return number
	 
def formatName(filename):
    filename = filename.strip()
    filename = filename.replace(' ', '.')
    return filename	 
    
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
        result = 'Unicode Error'
    return result

if ( __name__ == "__main__" ):
    player = Player()
    log("[%s] - Version: %s Started" % (__scriptname__, __version__))
    while not xbmc.abortRequested:
        xbmc.sleep(100)
    player._monitor = None
    log("sys.exit(0)")
    sys.exit(0)
    
'''
    Bookmarking playbackengine Module
    Copyright (C) 2012 XBMCHUB.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os
import sys
import threading
import time
import xbmc
import xbmcgui
from t0mm0.common.addon import Addon

SLEEP_MILLIS = 250
addon = Addon('script.module.playbackengine', sys.argv)
PROFILE_PATH = addon.get_profile()
DB_PATH = os.path.join(PROFILE_PATH, 'playbackengine.db')

if not os.path.isdir(PROFILE_PATH):
    os.makedirs(PROFILE_PATH)

try:
    from sqlite3 import dbapi2 as sqlite
    addon.log('Loading sqlite3 as DB engine')
except:
    from pysqlite2 import dbapi2 as sqlite
    addon.log('Loading pysqlite2 as DB engine')

def format_time(seconds):
    minutes,seconds = divmod(seconds, 60)
    if minutes > 60:
        hours,minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)
        
class Player(xbmc.Player):
    '''
    This class provides a wrapper around the xbmc.Player object that allows for bookmarking capability.
    
    When starting playback, the class will check with a database to see if the show has been
    watched before, and if so whether we've watched more than 30 seconds. If so, we will ask
    the user if they want to jump to the last watched point or start the video over.
    
    Usage (typical):
    
    import playbackengine
    
    def WatchedCallback():
        addon.log('Video completely watched.')
        
    ...
    title = 'My video title'
    stream_url = 'http://www.youtube.com/whatever....'
    
    
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    listitem = xbmcgui.ListItem(title)
    playlist.add(url=stream_url, listitem=listitem)
    
    player = playbackengine.Player(plugin='plugin.video.youtube', video_type='tvshow', title=title,
                        season='1', episode='1', year='2009', watch_percent=0.85,
                        watchedCallback=WatchedCallback)
                        
    player.play(playlist)
    while player._playbackLock.isSet():
        addon.log('Playback lock set. Sleeping for 250.')
        xbmc.sleep(250)
                        
                           
    
    '''
    
    def __init__(self, plugin, video_type, title, season, episode, year, watch_percent=0.9, watchedCallback=None):
        '''
        Args:
            plugin (str):           Your addon's id (eg. 'plugin.video.youtube')
            video_type (str):       What kind of video being watched (eg. 'movie' or 'tvshow')
            title (str):            The video's title
            season (str):           The video's season (if video_type == 'tvshow')
            episode (str):          The video's episode number (if video_type == 'tvshow')
            year (str):             The year for the video
            
        Kwargs:
            watch_percent (float):  The percentage at which the video is considered "watched".
                                    This can be adjusted by the calling plugin. (90% = 0.9)
            watchedCallback (function):  This is a function that will be called when watch_percent
                                    is reached. This allows your plugin to do some specific action
                                    (such as update the UI) when the video is considered "watched"   
        '''
        xbmc.Player.__init__(self, xbmc.PLAYER_CORE_AUTO)
        self._playbackLock = threading.Event()
        self._playbackLock.set()
        self._totalTime = 999999
        self._lastPos = 0
        self._sought = False
        self.plugin = plugin
        self.video_type = video_type
        self.title = title
        self.season = season
        self.episode = episode
        self.year = year
        self.watch_percent = watch_percent
        self.watchedCallback = watchedCallback
        self._initDatabase()
        addon.log('Created player')
        
    def __del__(self):
        addon.log("GC'ing player")
        
    def _initDatabase(self):
        '''
        Initializes the database
        '''
        db = sqlite.connect(DB_PATH)
        db.execute('CREATE TABLE IF NOT EXISTS bookmarks (plugin, video_type, title, season, episode, year, bookmark)')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS unique_bmk ON bookmarks (plugin, video_type, title, season, episode, year)')
        db.commit()
        db.close()
        
    def onPlayBackStarted(self):
        '''
        Called when playback started. Checks database to see if video has been watched before.
        
        If video has been viewed before and it has been viewed for longer than 30 seconds, ask
        the user if they want to jump to the last viewed place or to start the video over.
        '''
        addon.log('Beginning Playback')
        self._totalTime = self.getTotalTime()
        self._tracker = threading.Thread(target=self._trackPosition)
        self._tracker.start()
        db = sqlite.connect(DB_PATH)
        bookmark = db.execute('SELECT bookmark FROM bookmarks WHERE plugin=? AND video_type=? AND title=? AND season=? AND episode=? AND year=?', (self.plugin, self.video_type, self.title, self.season, self.episode, self.year)).fetchone()
        db.close()
        if not self._sought and bookmark and bookmark[0] and bookmark[0]-30 > 0:
            question = xbmc.getLocalizedString(12022) % format_time(bookmark[0])   # 12022 = Resume from %s
            resume = xbmcgui.Dialog()
            resume = resume.yesno(self.title, '', question, '', xbmc.getLocalizedString(20132), xbmc.getLocalizedString(13404))  # 20132 = Restart Video 13404 = Resume
            if resume: self.seekTime(bookmark[0])
            self._sought = True
            
    def onPlayBackStopped(self):
        '''
        Called when playback is stopped (normal or otherwise)
        
        Checks to see if we've watched more than watch_percent. If so, then the bookmark is deleted and 
        watchedCallback is called if it exists.
        If we didn't play at all, raises a playback failed exception.
        Otherwise, save a new bookmark at the furthest watched spot.
        '''
        addon.log('> onPlayBackStopped')
        self._playbackLock.clear()
        
        playedTime = self._lastPos
        addon.log('playedTime / totalTime : %s / %s = %s' % (playedTime, self._totalTime, playedTime/self._totalTime))
        if playedTime == 0 and self._totalTime == 999999:
            raise PlaybackFailed('XBMC silently failed to start playback')
        elif (((playedTime/self._totalTime) > self.watch_percent) and (self.video_type == 'movie' or (self.season and self.episode))):
            addon.log('Threshold met.')
            if self.watchedCallback: self.watchedCallback()
            db = sqlite.connect(DB_PATH)
            db.execute('DELETE FROM bookmarks WHERE plugin=? AND video_type=? AND title=? AND season=? AND episode=? AND year=?', (self.plugin, self.video_type, self.title, self.season, self.episode, self.year))
            db.commit()
            db.close()
        else:
            addon.log('Threshold not met. Saving bookmark')
            db = sqlite.connect(DB_PATH)
            db.execute('INSERT OR REPLACE INTO bookmarks (plugin, video_type, title, season, episode, year, bookmark) VALUES(?,?,?,?,?,?,?)',
                      (self.plugin, self.video_type, self.title, self.season, self.episode, self.year, playedTime))
            db.commit()
            db.close()
            
    def onPlayBackEnded(self):
        '''
        Calls onPlayBackStopped
        '''
        self.onPlayBackStopped()
        addon.log('onPlayBackEnded')
        
    def _trackPosition(self):
        '''
        Keeps track of where in the video we currently are.
        '''
        while self._playbackLock.isSet():
            try:
                self._lastPos = self.getTime()
            except:
                addon.log_debug('Error while trying to set playback time')
            addon.log_debug('Inside player. Tracker time = %s' % self._lastPos)
            xbmc.sleep(SLEEP_MILLIS)
        addon.log('Position tracker ending with lastPos = %s' % self._lastPos)
        
class PlaybackFailed(Exception):
    '''Raised to indicate that xbmc silently failed to play the stream'''
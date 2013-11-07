'''
    universal XBMC module
    Copyright (C) 2013 the-one @ XUNITYTALK.COM
    
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
import xbmcplugin
import hashlib

from t0mm0.common.addon import Addon

from universal import _common as common

SLEEP_MILLIS = 250

HELPER = 'playbackengine'

try:
    if  common.use_remote_db=='true' and   \
        common.db_address is not None and  \
        common.db_user is not None and     \
        common.db_pass is not None and     \
        common.db_name is not None:
        import mysql.connector as database
        common.addon.log('-' + HELPER + '- -' +'Loading MySQLdb as DB engine', 2)
        DB = 'mysql'
    else:
        raise ValueError('MySQL not enabled or not setup correctly')
except:
    try: 
        import sqlite3
        from sqlite3 import dbapi2 as database
        common.addon.log('-' + HELPER + '- -' +'Loading sqlite3 as DB engine version: %s' % database.sqlite_version, 2)
    except Exception, e:
        from pysqlite2 import dbapi2 as database
        common.addon.log('-' + HELPER + '- -' +'pysqlite2 as DB engine', 2)
    DB = 'sqlite'
    
def format_time(seconds):
    minutes,seconds = divmod(seconds, 60)
    if minutes > 60:
        hours,minutes = divmod(minutes, 60)
        return "%02d:%02d:%02d" % (hours, minutes, seconds)
    else:
        return "%02d:%02d" % (minutes, seconds)

class Player(xbmc.Player):
    
    local_db_name = 'playbackengine.db'
    
    '''
    This class provides a wrapper around the xbmc.Player object that allows for bookmarking capability.
    
    When starting playback, the class will check with a database to see if the show has been
    watched before, and if so whether we've watched more than 30 seconds. If so, we will ask
    the user if they want to jump to the last watched point or start the video over.
    
    Usage (typical):
    
    import playbackengine
    
    def WatchedCallback():
        common.addon.log('-' + HELPER + '- -' +'Video completely watched.')
        
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
        common.addon.log('-' + HELPER + '- -' +'Playback lock set. Sleeping for 250.')
        xbmc.sleep(250)
    '''    
    
    def __init__(self, *args, **kwargs):
        #Check if a path has been set in the addon settings
        if common.db_path:
            self.path = xbmc.translatePath(common.db_path)
        else:
            self.path = xbmc.translatePath(common.default_path)
            
        xbmc.Player.__init__(self, *args, **kwargs)
        
        self._playbackLock = threading.Event()
        self._playbackLock.set()
        self._totalTime = 999999
        self._lastPos = 0
        self._sought = False
        
        self.cache_path = common.make_dir(self.path, '')
        
        self.db = os.path.join(self.cache_path, self.local_db_name)
                
        self._create_playbackengine_tables()
        
        common.addon.log('-' + HELPER + '- -' +'Created player', 2)
    
    def set(self, addon_id, video_type, title, season, episode, year, watch_percent=0.9, watchedCallback=None, watchedCallbackwithParams=None, imdb_id=''):
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
            
        self._reset()
        
        win = xbmcgui.Window(10000)
        while win.getProperty('pbe.playing.playbackstopped') == 'false':
            xbmc.sleep(SLEEP_MILLIS)
        
        win.setProperty('pbe.playing.addon_id', addon_id)
        win.setProperty('pbe.playing.video_type', video_type)
        win.setProperty('pbe.playing.title', title)
        win.setProperty('pbe.playing.season', str(season))
        win.setProperty('pbe.playing.episode', str(episode))
        win.setProperty('pbe.playing.year', str(year))
        win.setProperty('pbe.playing.hash', hashlib.md5(addon_id+video_type+title+str(season)+str(episode)+str(year)).hexdigest())
        win.setProperty('pbe.playing.imdb', str(imdb_id))
                
        self.watch_percent = watch_percent
        self.watchedCallback = watchedCallback
        self.watchedCallbackwithParams = watchedCallbackwithParams

        common.addon.log('-' + HELPER + '- -' +'Set player', 2)
        
    def _reset(self):
        xbmc.log('1Channel: Service: Resetting...')
        win = xbmcgui.Window(10000)
        win.clearProperty('pbe.playing.addon_id')
        win.clearProperty('pbe.playing.video_type')
        win.clearProperty('pbe.playing.title')
        win.clearProperty('pbe.playing.year')
        win.clearProperty('pbe.playing.season')
        win.clearProperty('pbe.playing.episode')
        win.clearProperty('pbe.playing.hash')
        win.clearProperty('pbe.playing.imdb')

        self._totalTime = 999999
        self._lastPos = 0
        self._sought = False
        self.addon_id = ''
        self.video_type = ''
        self.title = ''
        self.season = ''
        self.episode = ''
        self.year = ''
        
    def _connect_to_db(self):
        # connect to db at class init and use it globally
        if DB == 'mysql':
            class MySQLCursorDict(database.cursor.MySQLCursor):
                def _row_to_python(self, rowdata, desc=None):
                    row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
                    if row:
                        return dict(zip(self.column_names, row))
                    return None
            self.dbcon = database.connect(common.db_name, common.db_user, common.db_pass, common.db_address, buffered=True, charset='utf8')
            self.dbcur = self.dbcon.cursor(cursor_class=MySQLCursorDict, buffered=True)
        else:
            self.dbcon = database.connect(self.db)
            self.dbcon.row_factory = database.Row # return results indexed by field names and not numbers so we can convert to dict
            self.dbcon.text_factory = str
            self.dbcur = self.dbcon.cursor()
            
    def _close_db(self):
        try:
            self.dbcur.close()
            self.dbcon.close()
        except: pass
        
    def __del__(self):
        ''' Cleanup db when object destroyed '''
        self._close_db()
        common.addon.log('-' + HELPER + '- -' +"GC'ing player")
               
    def _create_playbackengine_tables(self):
        self._connect_to_db()
        sql_create = "CREATE TABLE IF NOT EXISTS bookmarks ("\
                            "hash,"\
                            "addon_id,"\
                            "video_type,"\
                            "title,"\
                            "season,"\
                            "episode,"\
                            "year,"\
                            "bookmark"\
                            ");"
                            
        if DB == 'mysql':
            sql_create = sql_create.replace("hash", "hash VARCHAR(32)")
            sql_create = sql_create.replace("addon_id", "addon_id VARCHAR(100)")
            sql_create = sql_create.replace("video_type"  ,"video_type VARCHAR(10)")
            sql_create = sql_create.replace("title"  ,"title VARCHAR(200)")
            sql_create = sql_create.replace("season"  ,"season INTEGER")
            sql_create = sql_create.replace("episode"  ,"episode INTEGER")
            sql_create = sql_create.replace("year"  ,"year VARCHAR(10)")
            sql_create = sql_create.replace(",bookmark"  ,",bookmark VARCHAR(10)")
            self.dbcur.execute(sql_create)
            try: self.dbcur.execute('CREATE UNIQUE INDEX uniquebmk on bookmarks (hash);')
            except: pass
            try: self.dbcur.execute('CREATE INDEX bmkindex on bookmarks (addon_id, video_type, title, season, episode, year);')
            except: pass
        else:
            self.dbcur.execute(sql_create)
            self.dbcur.execute('CREATE UNIQUE INDEX IF NOT EXISTS uniquebmk on bookmarks (hash);')
            self.dbcur.execute('CREATE INDEX IF NOT EXISTS bmkindex on bookmarks (addon_id, video_type, title, season, episode, year);')
            
        self._close_db()
        
    def onPlayBackStarted(self):
        '''
        Called when playback started. Checks database to see if video has been watched before.
        
        If video has been viewed before and it has been viewed for longer than 30 seconds, ask
        the user if they want to jump to the last viewed place or to start the video over.
        '''
        win = xbmcgui.Window(10000)
        win.setProperty('pbe.playing.playbackstopped', 'false')
        self.addon_id = win.getProperty('pbe.playing.addon_id')
        self.video_type = win.getProperty('pbe.playing.video_type')
        self.title = common.str_conv(win.getProperty('pbe.playing.title'))
        self.season = win.getProperty('pbe.playing.season')
        self.year = win.getProperty('pbe.playing.year')
        self.episode = win.getProperty('pbe.playing.episode')
        self.hash = win.getProperty('pbe.playing.hash')
        self.imdb_id = win.getProperty('pbe.playing.imdb')
        
        common.addon.log('-' + HELPER + '- -' +'Beginning Playback: addon: %s, title: %s, year: %s, season: %s, episode: %s' % (
            self.addon_id, self.title, self.year, self.season, self.episode) )
            
        self._totalTime = self.getTotalTime()
        self._tracker = threading.Thread(target=self._trackPosition)
        self._tracker.start()
        
        self._connect_to_db()
        sql_select = "SELECT bookmark FROM bookmarks WHERE hash='%s'" % self.hash
        common.addon.log('-' + HELPER + '- -' +sql_select, 2)
        self.dbcur.execute(sql_select)            
        bookmark = self.dbcur.fetchone()
        self._close_db()
        if bookmark:
            bookmark = float(bookmark['bookmark'])
            if not self._sought and bookmark-30 > 0:
                common.addon.log('-' + HELPER + '- -' +'Showing Dialog')
                question = xbmc.getLocalizedString(12022) % format_time(bookmark)   # 12022 = Resume from %s
                resume = xbmcgui.Dialog()
                resume = resume.yesno(self.title, '', question, '', xbmc.getLocalizedString(20132), xbmc.getLocalizedString(13404))  # 20132 = Restart Video 13404 = Resume
                if resume: self.seekTime(bookmark)
                self._sought = True
            
    def onPlayBackStopped(self):
        '''
        Called when playback is stopped (normal or otherwise)
        
        Checks to see if we've watched more than watch_percent. If so, then the bookmark is deleted and 
        watchedCallback is called if it exists.
        If we didn't play at all, raises a playback failed exception.
        Otherwise, save a new bookmark at the furthest watched spot.
        '''
        common.addon.log('-' + HELPER + '- -' +'> Playback Stopped: addon: %s, title: %s, year: %s, season: %s, episode: %s' % (
            self.addon_id, self.title, self.year, self.season, self.episode) )

        xbmcgui.Window(10000).setProperty('pbe.playing.playbackstopped', 'true')
        self._playbackLock.clear()
        
        playedTime = self._lastPos
        common.addon.log('-' + HELPER + '- -' +'playedTime / totalTime : %s / %s = %s' % (playedTime, self._totalTime, playedTime/self._totalTime))
        if playedTime == 0 and self._totalTime == 999999:
            raise PlaybackFailed('XBMC silently failed to start playback')
        elif (((playedTime/self._totalTime) > self.watch_percent) and (self.video_type != 'live')):
            common.addon.log('-' + HELPER + '- -' +'Threshold met.')
            if self.watchedCallback: self.watchedCallback()
            if self.watchedCallbackwithParams: self.watchedCallbackwithParams(self.video_type, self.title, self.imdb_id, self.season, self.episode, self.year)

            self._connect_to_db()
            sql_delete = "DELETE FROM bookmarks WHERE hash='%s'" % self.hash
            self.dbcur.execute(sql_delete) 
            self.dbcon.commit()
            self._close_db()
            
        elif self.video_type != 'live':
            common.addon.log('-' + HELPER + '- -' +'Threshold not met. Saving bookmark')
            
            sql_insert_or_replace = ''
            if DB == 'mysql':
                sql_insert_or_replace = 'REPLACE INTO bookmarks (hash, addon_id, video_type, title, season, episode, year, bookmark) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)'
            else:
                sql_insert_or_replace = 'INSERT or REPLACE INTO bookmarks (hash, addon_id, video_type, title, season, episode, year, bookmark) VALUES(?,?,?,?,?,?,?,?)'
            
            self._connect_to_db()
            self.dbcur.execute(sql_insert_or_replace, (self.hash, self.addon_id, self.video_type, self.title, self.season, self.episode, self.year, playedTime)) 
            self.dbcon.commit()
            self._close_db()
            
    def onPlayBackEnded(self):
        '''
        Calls onPlayBackStopped
        '''
        self.onPlayBackStopped()
        common.addon.log('-' + HELPER + '- -' +'onPlayBackEnded')
        
    def KeepAlive(self):
        while self._playbackLock.isSet():
            common.addon.log('-' + HELPER + '- -' +'Playback lock set. Sleeping for 250.')
            xbmc.sleep(SLEEP_MILLIS)
        
    def _trackPosition(self):
        '''
        Keeps track of where in the video we currently are.
        '''
        win = xbmcgui.Window(10000)
        while self._playbackLock.isSet():
            try:                
                if self.hash == win.getProperty('pbe.playing.hash'):
                    self._lastPos = self.getTime()
                else:
                    self.onPlayBackStopped()
            except:
                common.addon.log_debug('Error while trying to set playback time')
            common.addon.log_debug('Inside player. Tracker time = %s' % self._lastPos)
            xbmc.sleep(SLEEP_MILLIS)
        common.addon.log('-' + HELPER + '- -' +'Position tracker ending with lastPos = %s' % self._lastPos)

class PlaybackFailed(Exception):
    '''Raised to indicate that xbmc silently failed to play the stream'''
    
def QueueItem(addon_id, title, url, is_resolved=False,img='', fanart='', infolabels=''):
    script_path = os.path.join(common.addon.get_path(), 'lib', 'universal', 'playbackengine.py')
    pbe_infolabels = ''
    if infolabels:
        pbe_infolabels = str(common.encode_dict(infolabels))
    
    item_url = url
    if is_resolved == False:
        item_url = item_url + '&queued=true'
    
    pbe_params = {
        'pbe_mode' : 'queueitem',
        'pbe_addon_id': addon_id,
        'pbe_title' : title,
        'pbe_url' : item_url,
        'pbe_img' : img,
        'pbe_fanart' : fanart,
        'pbe_infolabels' : pbe_infolabels
    }
    pbe_script = 'XBMC.RunScript(%s, %s, %s, "%s")' % (script_path, sys.argv[1], '?' + common.dict_to_paramstr(pbe_params), 'script.module.universal.playbackengine')
    
    return pbe_script

def AddToPL(title, url='', img='', fanart='', infolabels=None):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    
    if fanart:
        listitem.setProperty('fanart_image', fanart)    
    
    if infolabels:
        listitem.setInfo("Video", infolabels)
    
    item_url = url
    if url=='' or not url:
        item_url = sys.argv[0]+sys.argv[2]+'&queued=true'
    
    playlist.add(url=item_url, listitem=listitem)
    
def PlayInPL(title, url='', img='', fanart='', infolabels=None):  
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()    
    listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    
    if fanart:
        listitem.setProperty('fanart_image', fanart)    
    
    if infolabels:
        listitem.setInfo("Video", infolabels)
    
    item_url = url
    if url=='' or not url:
        item_url = sys.argv[0]+sys.argv[2]+'&queued=true'
        
    playlist.add(url=item_url, listitem=listitem)
    Player().play(playlist)
    
def Play(resolved_url, addon_id, video_type, title, season, episode, year, watch_percent=0.9, watchedCallback=None, watchedCallbackwithParams=None, imdb_id=None):
    player = Player()    
    common.addon.log('-' + HELPER + '- -' + resolved_url)
    player.set(addon_id, video_type, title, season, episode, year, watch_percent, watchedCallback, watchedCallbackwithParams, imdb_id)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, xbmcgui.ListItem(path=resolved_url))
    return player
    
def PlayWithoutQueueSupport(resolved_url, addon_id, video_type, title, season, episode, year, watch_percent=0.9, watchedCallback=None, watchedCallbackwithParams=None, imdb_id=None, img='', fanart='', infolabels=None):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()    
    listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
    
    if fanart:
        listitem.setProperty('fanart_image', fanart)
    
    if infolabels:
        listitem.setInfo("Video", infolabels)
    
    playlist.add(url=resolved_url, listitem=listitem)
    
    player = Player()
    player.set(addon_id, video_type, title, season, episode, year, watch_percent, watchedCallback, watchedCallbackwithParams, imdb_id)
    
    player.play(playlist)
    
    return player

    
if sys.argv and len(sys.argv) >= 4 and sys.argv[3] == 'script.module.universal.playbackengine':        
    
    sys.argv[0] = 'script.module.universal'
    addon_pbe= Addon('script.module.universal', sys.argv)
    
    pbe_mode = addon_pbe.queries.pop('pbe_mode')
    addon_id_tmp = addon_pbe.queries.pop('pbe_addon_id')
    title = addon_pbe.queries.pop('pbe_title')
    url = addon_pbe.queries.pop('pbe_url')
    img = addon_pbe.queries.pop('pbe_img', '')
    fanart = addon_pbe.queries.pop('pbe_fanart', '')
    infolabels = addon_pbe.queries.pop('pbe_infolabels', '')
    if infolabels:
        import re
        try:
            import json
        except:
            import simplejson as json
        infolabels = json.loads(re.sub(r",\s*(\w+)", r", '\1'", re.sub(r"\{(\w+)", r"{'\1'", infolabels.replace('\\','\\\\'))).replace("'", '"'))
        infolabels = common.decode_dict(infolabels)
    
    if pbe_mode == 'queueitem':
        try:
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            
            item_already_in_PL = False
            playlist_item_count = len(playlist)
            playlist_item_loop = playlist_item_count
            for x in range(0, playlist_item_loop):
                if playlist[x].getfilename() == url:
                    item_already_in_PL = True
                    common.notify(addon_id_tmp, 'small', '', 'Item: ' + title + ' - already in Queue.', '8000')
                    break
            if item_already_in_PL == False:
                
                listitem = xbmcgui.ListItem(title, iconImage=img, thumbnailImage=img)
                
                if fanart:
                    listitem.setProperty('fanart_image', fanart)
    
                if infolabels:
                    listitem.setInfo("Video", infolabels)
                
                playlist.add(url=url, listitem=listitem)
                common.notify(addon_id_tmp, 'small', '', 'Item: ' + title + ' - added successfully to Queue.', '8000')
        except:
            common.notify(addon_id_tmp, 'small', '', 'Item: ' + title + ' - unable to add to Queue.', '8000')

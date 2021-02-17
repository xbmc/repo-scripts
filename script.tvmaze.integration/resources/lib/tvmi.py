# -*- coding: utf-8 -*-
# *  Credits:
# *
# *  original TV Maze Integration code by pkscout

from kodi_six import xbmc, xbmcgui
import json, os, re, sys
from contextlib import contextmanager
from resources.lib.apis import tvmaze
from resources.lib.fileops import readFile, writeFile
from resources.lib.xlogger import Logger
from resources.lib.tvmisettings import loadSettings


def _upgrade():
    settings = loadSettings()
    if settings['version_upgrade'] != settings['ADDONVERSION']:
        settings['ADDON'].setSetting( 'version_upgrade', settings['ADDONVERSION'] )

def _logsafe_settings( settings ):
    show_in_log = settings.copy()
    show_in_log.pop( 'tvmaze_user', '' )
    show_in_log.pop( 'tvmaze_apikey', '' )
    return show_in_log

def _manage_followed( showname, action, tvmazeapi, lw ):
    success, loglines, result = tvmazeapi.findSingleShow( showname )
    lw.log( loglines )
    if success:
        showid = result.get( 'id', 0 )
        if showid:
            if action == 'follow':
                success, loglines, result = tvmazeapi.followShow( showid )
            else:
                success, loglines, result = tvmazeapi.unFollowShow( showid )
            lw.log( loglines )
    return showid

def _mark_one( show_info, mark_type, add_followed, tvmcache, tvmcachefile, tvmazeapi, lw ):
    lw.log( ['starting process to mark show'] )
    tvmazeid = ''
    if show_info:
        lw.log( ['show info found, trying to match with cached TV Maze information first'] )
        tvmazeid = _match_from_followed_shows( show_info, tvmcache, lw )
        if not tvmazeid:
            lw.log( ['no match, loading cache file from disk and trying again'] )
            loglines, results = readFile( tvmcachefile )
            lw.log( loglines )
            if results:
                tvmcache = json.loads( results )
            else:
                tvmcache = []
            tvmazeid = _match_from_followed_shows( show_info, tvmcache, lw )
        if not tvmazeid:
            lw.log( ['no match, getting updated followed shows from TV Maze and trying again'] )
            if add_followed:
                showname = show_info['name']
            else:
                showname = ''
            tvmcache = _update_followed_cache( tvmcachefile, tvmazeapi, lw, showname=showname )
            tvmazeid = _match_from_followed_shows( show_info, tvmcache, lw )
        if tvmazeid:
            lw.log( ['found tvmazeid of %s' % tvmazeid, 'attempting to get episode id'] )
            params = {'season':show_info['season'], 'number':show_info['episode']}
            success, loglines, results = tvmazeapi.getEpisodeBySeasonEpNumber( tvmazeid, params )
            lw.log( loglines )
            if not success:
                lw.log( ['no valid response returned from TV Maze, aborting'] )
                return
            try:
                episodeid = results['id']
            except KeyError:
                episodeid = ''
            if episodeid:
                lw.log( ['got back episode id of %s' % episodeid, 'marking episode on TV Maze'] )
                success, loglines, results = tvmazeapi.markEpisode( episodeid, marked_as=mark_type )
                lw.log( loglines )
                if not success:
                    lw.log( ['no valid response returned from TV Maze, show was not marked'] )
            else:
                lw.log( ['no episode id found'] )
        else:
            lw.log( ['no tvmazeid found'] )
    else:
        lw.log( ['no show information from Kodi'] )
    return tvmcache

def _match_from_followed_shows( show_info, tvmcache, lw ):
    tvmazeid = ''
    lw.log( ['using show name of %s' % show_info['name']], xbmc.LOGNOTICE )
    if not tvmcache:
        return ''
    for followed_show in tvmcache:
        followed_name = followed_show['_embedded']['show']['name']
        lw.log( ['checking for %s matching %s' % (show_info['name'], followed_name)] )
        if followed_name == show_info['name']:
            lw.log( ['found match for %s' % show_info['name'] ], xbmc.LOGNOTICE )
            tvmazeid = followed_show['show_id']
            break
    return tvmazeid

def _build_tag_list( tvmazeapi, lw ):
    lw.log( ['building tag list'] )
    taglist = []
    tagmap = {}
    success, loglines, results = tvmazeapi.getTags()
    lw.log( loglines )
    if not success or not results:
        return [], {}
    items = sorted( results, key=lambda x:x['name'] )
    for item in items:
        taglist.append( item['name'] )
        tagmap[item['name']] = item['id']
    return taglist, tagmap

def _update_followed_cache( tvmcachefile, tvmazeapi, lw, showname='' ):
    if showname:
        _manage_followed( showname, 'follow', tvmazeapi, lw )
    success, loglines, results = tvmazeapi.getFollowedShows( params={'embed':'show'} )
    lw.log( loglines )
    if success:
        tvmcache = results
    else:
        lw.log( ['no valid response returned from TV Maze'] )
        tvmcache = []
    if tvmcache:
        success, loglines = writeFile( json.dumps( tvmcache ), tvmcachefile, wtype='w' )
        lw.log( loglines )
    return tvmcache

def _get_json( method, params, lw ):
    json_call = '{"jsonrpc":"2.0", "method":"%s", "params":%s, "id":1}' % (method, params)
    lw.log( ['sending: %s' % json_call ])
    response = xbmc.executeJSONRPC( json_call )
    lw.log( ['the response was:', response] )
    try:
        r_dict = json.loads( response )
    except ValueError:
        r_dict = {}
    return r_dict.get( 'result', {} )

def _startup( lw, settings, dialog ):
    lw.log( ['script version %s started' % settings['ADDONVERSION']], xbmc.LOGNOTICE )
    lw.log( ['debug logging set to %s' % settings['debug']], xbmc.LOGNOTICE )
    if not (settings['tvmaze_user'] and settings['tvmaze_apikey']):
        dialog.ok( settings['ADDONLANGUAGE']( 32200 ), settings['ADDONLANGUAGE']( 32301 ) )
        settings['ADDON'].openSettings()

@contextmanager
def busyDialog():
    xbmc.executebuiltin( 'ActivateWindow(busydialognocancel)' )
    yield
    xbmc.executebuiltin( 'Dialog.Close(busydialognocancel)' )



class tvmContext:

    def __init__( self, action ):
        """Allows access to TV Maze from context menu."""
        self._init_vars()
        _startup( self.LW, self.SETTINGS, self.DIALOG )
        self.LW.log( ['list item label: %s' % sys.listitem.getLabel()] )
        self.LW.log( ['list item path: %s' % sys.listitem.getPath()] )
        if 'follow' in action:
            self._manage_show_follow( action )
        elif 'tag' in action:
            self._manage_show_tag( action )
        elif 'mark' in action:
            self._manage_show_mark( action )


    def _init_vars( self ):
        self.SETTINGS = loadSettings()
        self.LW = Logger( preamble='[TVMI Context]', logdebug=self.SETTINGS['debug'] )
        self.LW.log( ['loaded settings', _logsafe_settings( self.SETTINGS )] )
        self.TVMAZE = tvmaze.API( user=self.SETTINGS['tvmaze_user'], apikey=self.SETTINGS['tvmaze_apikey'] )
        self.DIALOG = xbmcgui.Dialog()
        self.KODIMONITOR = xbmc.Monitor()
        self.TVMCACHEFILE = os.path.join( self.SETTINGS['ADDONDATAPATH'], 'tvm_followed_cache.json' )


    def _get_details_from_path( self, thepath ):
        showid = re.findall( 'tvshowid=(.*)', thepath )[0]
        self.LW.log( ['showid is: %s' % showid] )
        method = 'VideoLibrary.GetTVShowDetails'
        params = '{"tvshowid":%s}' % str( showid )
        results = _get_json( method, params, self.LW )
        self.LW.log( ['the show details are:', results] )
        showname = results.get( 'tvshowdetails', {} ).get( 'label', '' )
        method = 'VideoLibrary.GetEpisodeDetails'
        epid = re.findall( '\/titles\/[0-9].*[0-9]\/.*\/([0-9].*[0-9])\?season', thepath )[0]
        self.LW.log( ['epid is: %s' % epid] )
        params = '{"episodeid":%s, "properties":["season", "episode"]}' % epid
        results = _get_json( method, params, self.LW )
        self.LW.log( ['the episode details are:', results] )
        season = results.get( 'episodedetails', {} ).get( 'season', 0 )
        episode = results.get( 'episodedetails', {} ).get( 'episode', 0 )
        self.LW.log( ['returning showname of %s, season of %s, and episode of %s' % (showname, str( season ), str( episode ))]  )
        return {'name':showname, 'season':season, 'episode':episode}


    def _manage_show_follow( self, action ):
        with busyDialog():
            _manage_followed( sys.listitem.getLabel(), action, self.TVMAZE, self.LW )


    def _manage_show_tag( self, action ):
        with busyDialog():
            taglist, tagmap = _build_tag_list( self.TVMAZE, self.LW )
        ret = self.DIALOG.select( self.SETTINGS['ADDONLANGUAGE']( 32204 ), taglist )
        if ret == -1:
            return
        tagid = tagmap[taglist[ret]]
        with busyDialog():
            showid = _manage_followed( re.sub( r' \([0-9]{4}\)', '', sys.listitem.getLabel() ), 'follow', self.TVMAZE, self.LW )
            if action == 'tag':
                success, loglines, result = self.TVMAZE.tagShow( showid, tagid )
            else:
                success, loglines, result = self.TVMAZE.unTagShow( showid, tagid )
            self.LW.log( loglines )


    def _manage_show_mark( self, action ):
        show_info = self._get_details_from_path( sys.listitem.getPath() )
        if action == 'mark_watched':
            mark_type = 0
        elif action == 'mark_acquired':
            mark_type = 1
        elif action == 'mark_skipped':
            mark_type = 2
        else:
            mark_type = -1
        with busyDialog():
            _mark_one( show_info, mark_type, self.SETTINGS['add_followed'], [], self.TVMCACHEFILE, self.TVMAZE, self.LW )



class tvmManual:

    def __init__( self ):
        """Runs some manual functions for following and tagging shows on TV Maze."""
        self._init_vars()
        _startup( self.LW, self.SETTINGS, self.DIALOG )
        options = [ self.SETTINGS['ADDONLANGUAGE']( 32202 ),
                    self.SETTINGS['ADDONLANGUAGE']( 32203 ),
                    self.SETTINGS['ADDONLANGUAGE']( 32205 ),
                    self.SETTINGS['ADDONLANGUAGE']( 32206 ),
                    self.SETTINGS['ADDONLANGUAGE']( 32302 ) ]
        ret = self.DIALOG.select( self.SETTINGS['ADDONLANGUAGE']( 32201 ), options )
        self.LW.log( ['got back %s from the dialog box' % str( ret )] )
        if ret == -1:
            return
        if ret == 0:
            self._option_follow_shows()
        elif ret == 1:
            self._option_unfollow_shows()
        elif ret == 2:
            self._option_tag_shows()
        elif ret == 3:
            self._option_untag_shows()
        elif ret == 4:
            self.SETTINGS['ADDON'].openSettings()
        self.LW.log( ['script version %s stopped' % self.SETTINGS['ADDONVERSION']], xbmc.LOGNOTICE )


    def _init_vars( self ):
        self.SETTINGS = loadSettings()
        self.LW = Logger( preamble='[TVMI Manual]', logdebug=self.SETTINGS['debug'] )
        self.LW.log( ['loaded settings', _logsafe_settings( self.SETTINGS )] )
        self.TVMAZE = tvmaze.API( user=self.SETTINGS['tvmaze_user'], apikey=self.SETTINGS['tvmaze_apikey'] )
        self.TVMCACHEFILE = os.path.join( self.SETTINGS['ADDONDATAPATH'], 'tvm_followed_cache.json' )
        self.DIALOG = xbmcgui.Dialog()
        self.KODIMONITOR = xbmc.Monitor()


    def _option_follow_shows( self ):
        showlist = self._build_show_list()
        ret = self._select_shows_dialog( self.SETTINGS['ADDONLANGUAGE']( 32202 ), showlist )
        if not ret:
            return
        else:
            with busyDialog():
                self._add_shows( ret, showlist )


    def _option_unfollow_shows( self ):
        with busyDialog():
            followedlist, followedmap = self._build_tvmaze_list()
        ret = self._select_shows_dialog( self.SETTINGS['ADDONLANGUAGE']( 32203 ), followedlist )
        if not ret:
            return
        else:
            with busyDialog():
                self._unfollow_shows( ret, followedlist, followedmap )


    def _option_tag_shows( self ):
        with busyDialog():
            taglist, tagmap = _build_tag_list( self.TVMAZE, self.LW )
        ret = self.DIALOG.select( self.SETTINGS['ADDONLANGUAGE']( 32204 ), taglist )
        if ret == -1:
            return
        tagid = tagmap[taglist[ret]]
        showlist = self._build_show_list()
        ret = self._select_shows_dialog( self.SETTINGS['ADDONLANGUAGE']( 32205 ), showlist )
        if not ret:
            return
        else:
            with busyDialog():
                self._add_shows( ret, showlist, tagid=tagid )


    def _option_untag_shows( self ):
        with busyDialog():
            taglist, tagmap = _build_tag_list( self.TVMAZE, self.LW )
        ret = self.DIALOG.select( self.SETTINGS['ADDONLANGUAGE']( 32204 ), taglist )
        if ret == -1:
            return
        tagid = tagmap[taglist[ret]]
        with busyDialog():
            taggedlist, taggedmap = self._build_tvmaze_list( tagid=tagid )
        ret = self._select_shows_dialog( self.SETTINGS['ADDONLANGUAGE']( 32206 ), taggedlist )
        if not ret:
            return
        else:
            with busyDialog():
                self._unfollow_shows( ret, taggedlist, taggedmap, tagid=tagid )
        return


    def _select_shows_dialog( self, header, options ):
        firstitem = self.SETTINGS['ADDONLANGUAGE']( 32303 )
        response = False
        while not response:
            if firstitem == self.SETTINGS['ADDONLANGUAGE']( 32303 ):
                preselect = []
            else:
                preselect = []
                for i in range( 1,len( options ) ):
                    preselect.append( i )
            options[0] = firstitem
            ret = self.DIALOG.multiselect( header, options, preselect=preselect )
            self.LW.log( ['got back a response of:', ret] )
            if not ret:
                response = True
            elif ret[0] == 0:
                if firstitem == self.SETTINGS['ADDONLANGUAGE']( 32303 ):
                    firstitem = self.SETTINGS['ADDONLANGUAGE']( 32304 )
                else:
                    firstitem = self.SETTINGS['ADDONLANGUAGE']( 32303 )
            else:
                response = True
        return ret


    def _build_show_list( self ):
        self.LW.log( ['building show list'] )
        showlist = ['']
        method = 'VideoLibrary.GetTVShows'
        params = '{"properties":["title"]}'
        items = sorted( _get_json( method, params, self.LW ).get( 'tvshows', [] ), key=lambda x:x['label'] )
        for item in items:
            showlist.append( item['label'] )
        return showlist


    def _build_tvmaze_list( self, tagid = '' ):
        if tagid:
            self.LW.log( ['building tagged list'] )
        else:
            self.LW.log( ['building followed list'] )
        tvmazelist = ['']
        tvmazemap = {}
        if tagid:
            success, loglines, results = self.TVMAZE.getTaggedShows( tagid, params={'embed':'show'} )
        else:
            results = _update_followed_cache( self.TVMCACHEFILE, self.TVMAZE, self.LW )
        if not results:
            return [], {}
        items = sorted( results, key=lambda x:x['_embedded']['show']['name'] )
        for item in items:
            tvmazelist.append( item['_embedded']['show']['name'] )
            tvmazemap[item['_embedded']['show']['name']] = item['show_id']
        return tvmazelist, tvmazemap


    def _add_shows( self, showchoices, showlist, tagid = '' ):
        if tagid:
            self.LW.log( ['tagging shows'] )
        else:
            self.LW.log( ['following shows'] )
        for showchoice in showchoices:
            if showchoice == 0:
                continue
            showid = _manage_followed( re.sub( r' \([0-9]{4}\)', '', showlist[showchoice] ), 'follow', self.TVMAZE, self.LW )
            if showid and tagid:
                self.KODIMONITOR.waitForAbort( 0.12 )
                success, loglines, result = self.TVMAZE.tagShow( showid, tagid )
                self.LW.log( loglines )
            self.KODIMONITOR.waitForAbort( 0.12 )


    def _unfollow_shows( self, showchoices, showlist, showmap, tagid='' ):
        if tagid:
            self.LW.log( 'untagging shows' )
        else:
            self.LW.log( 'unfollowing shows' )
        for showchoice in showchoices:
            if showchoice == 0:
                continue
            if tagid:
                success, loglines, result = self.TVMAZE.unTagShow( showmap.get( showlist[showchoice], 0 ), tagid )
            else:
                success, loglines, result = self.TVMAZE.unFollowShow( showmap.get( showlist[showchoice], 0 ) )
            self.LW.log( loglines )
            self.KODIMONITOR.waitForAbort( 0.12 )



class tvmMonitor( xbmc.Monitor ):

    def __init__( self ):
        """Starts the background process for automatic marking of played TV shows."""
        xbmc.Monitor.__init__( self )
        _upgrade()
        self.WINDOW = xbmcgui.Window(10000)
        self._init_vars()
        self.LW.log( ['background monitor version %s started' % self.SETTINGS['ADDONVERSION']], xbmc.LOGNOTICE )
        self.LW.log( ['debug logging set to %s' % self.SETTINGS['debug']], xbmc.LOGNOTICE )
        while not self.abortRequested():
            if self.waitForAbort( 10 ):
                break
            if self.PLAYINGEPISODE:
                try:
                    self.PLAYINGEPISODETIME = self.KODIPLAYER.getTime()
                except RuntimeError:
                    self.PLAYINGEPISODETIME = self.PLAYINGEPISODETIME
        self._set_property('script.tvmi.hidemenu', '' )
        self.LW.log( ['background monitor version %s stopped' % self.SETTINGS['ADDONVERSION']], xbmc.LOGNOTICE )


    def onNotification( self, sender, method, data ):
        if 'Player.OnPlay' in method:
            self.waitForAbort( 1 )
            if self.KODIPLAYER.isPlayingVideo():
                data = json.loads( data )
                is_an_episode = data.get( 'item', {} ).get( 'type', '' ) == 'episode'
                if is_an_episode:
                    self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
                    self.PLAYINGEPISODE = True
                    self.PLAYINGEPISODETOTALTIME = self.KODIPLAYER.getTotalTime()
                    self._get_show_ep_info( 'playing', data )
        elif 'Player.OnStop' in method and self.PLAYINGEPISODE:
            if self.PLAYINGEPISODE:
                self.PLAYINGEPISODE = False
                data = json.loads( data )
                self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
                played_percentage = (self.PLAYINGEPISODETIME / self.PLAYINGEPISODETOTALTIME) * 100
                self.LW.log( ['got played percentage of %s' % str( played_percentage )], xbmc.LOGNOTICE )
                if played_percentage >= float( self.SETTINGS['percent_watched'] ):
                    self.LW.log( ['item was played for the minimum percentage in settings, trying to mark'], xbmc.LOGNOTICE )
                    self._mark_episodes( 'playing' )
                else:
                    self.LW.log( ['item was not played long enough to be marked, skipping'], xbmc.LOGNOTICE )
                self._reset_playing()
        elif 'VideoLibrary.OnScanStarted' in method:
            data = json.loads( data )
            self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
            self.SCANSTARTED = True
        elif 'VideoLibrary.OnUpdate' in method and self.SCANSTARTED:
            data = json.loads( data )
            self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
            self.SCANNEDDATA.append( data )
        elif 'VideoLibrary.OnScanFinished' in method and self.SCANSTARTED:
            data = json.loads( data )
            self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
            for item in self.SCANNEDDATA:
                self._get_show_ep_info( 'scanned', item )
                if self.abortRequested():
                    break
            if self.SETTINGS['mark_on_remove']:
                self._update_episode_cache( items=self.SCANNEDITEMS )
            self._mark_episodes( 'scanned' )
            self._reset_scanned()
        elif 'VideoLibrary.OnRemove' in method and self.SETTINGS['mark_on_remove']:
            data = json.loads( data )
            self.LW.log( ['MONITOR METHOD: %s DATA: %s' % (str( method ), str( data ))] )
            self._get_show_ep_info( 'removed', data )
            self._mark_episodes( 'removed' )
            self.REMOVEDITEMS = []


    def onSettingsChanged( self ):
        self._init_vars()


    def _init_vars( self ):
        self.SETTINGS = loadSettings()
        self.LW = Logger( preamble='[TVMI Monitor]', logdebug=self.SETTINGS['debug'] )
        self.LW.log( ['the settings are:', _logsafe_settings( self.SETTINGS )] )
        self._set_property('script.tvmi.hidemenu', str( self.SETTINGS['hidemenu']).lower() )
        self.TVMCACHEFILE = os.path.join( self.SETTINGS['ADDONDATAPATH'], 'tvm_followed_cache.json' )
        self.EPISODECACHE = os.path.join( self.SETTINGS['ADDONDATAPATH'], 'episode_cache.json' )
        self.KODIPLAYER = xbmc.Player()
        self.TVMAZE = tvmaze.API( user=self.SETTINGS['tvmaze_user'], apikey=self.SETTINGS['tvmaze_apikey'] )
        self.TVMCACHE = _update_followed_cache( self.TVMCACHEFILE, self.TVMAZE, self.LW )
        self.REMOVEDITEMS = []
        self._reset_playing()
        self._reset_scanned()
        self.LW.log( ['initialized variables'] )


    def _reset_playing( self ):
        self.PLAYINGEPISODE = False
        self.PLAYINGITEMS = []
        self.PLAYINGEPISODETIME = 0
        self.PLAYINGEPISODETOTALTIME = 0


    def _reset_scanned( self ):
        self.SCANSTARTED = False
        self.SCANNEDITEMS = []
        self.SCANNEDDATA = []


    def _get_show_ep_info( self, thetype, data ):
        showid = 0
        epid = 0
        showname = ''
        if data.get( 'item', {} ).get( 'type', '' ) == 'episode':
            epid = data['item'].get( 'id', 0 )
        if epid:
            method = 'VideoLibrary.GetEpisodeDetails'
            params = '{"episodeid":%s, "properties":["season", "episode", "tvshowid"]}' % str( epid )
            r_dict = _get_json( method, params, self.LW )
            season = r_dict.get( 'episodedetails', {} ).get( 'season', 0 )
            episode = r_dict.get( 'episodedetails', {} ).get( 'episode', 0 )
            showid = r_dict.get( 'episodedetails', {} ).get( 'tvshowid', 0 )
            self.LW.log( ['moving on with season of %s, episode of %s, and showid of %s' % (str(season), str(episode), str(showid))] )
            if showid:
                method = 'VideoLibrary.GetTVShowDetails'
                params = '{"tvshowid":%s}' % str( showid )
                r_dict = _get_json( method, params, self.LW )
                showname = r_dict.get( 'tvshowdetails', {} ).get( 'label', '' )
                self.LW.log( ['moving on with TV show name of %s' % showname] )
        elif thetype == 'removed':
            epid = data.get( 'id', 0 )
            loglines, episode_cache = readFile( self.EPISODECACHE )
            self.LW.log( loglines )
            if episode_cache:
                self.LW.log( ['checking in cache for epid of %s' % str( epid )] )
                ep_info = json.loads( episode_cache ).get( str( epid ), {} )
            else:
                ep_info = {}
            showname = ep_info.get( 'name', '' )
            season = ep_info.get( 'season', 0 )
            episode = ep_info.get( 'episode', 0 )
        if showname and season and episode:
            item = {'epid': epid, 'name':showname, 'season':season, 'episode':episode}
        else:
            item = {}
        if item:
            self.LW.log( ['storing item data of:', item] )
            if thetype == 'scanned':
                self.SCANNEDITEMS.append( item )
            elif thetype == 'playing':
                self.PLAYINGITEMS.append( item )
            elif thetype == 'removed':
                self.REMOVEDITEMS.append( item )
                self._update_episode_cache( epid=epid )


    def _set_property( self, property_name, value='' ):
        try:
          self.WINDOW.setProperty( property_name, value )
          self.LW.log( ['%s set to %s' % (property_name, value)] )
        except Exception as e:
          self.LW.log( ['Exception: Could not set property %s to value %s' % (property_name, value), e])


    def _update_episode_cache( self, epid=None, item=None, items=None ):
        loglines, episode_cache = readFile( self.EPISODECACHE )
        self.LW.log( loglines )
        cache_changed = True
        if episode_cache:
            epcache_json = json.loads( episode_cache )
        else:
            epcache_json = {}
        if epid:
            try:
                del epcache_json[str( epid )]
            except KeyError:
                cache_changed = False
        elif item:
            epcache_json[str( item['epid'] )] = item
        elif items:
            for item in items:
                epcache_json[str( item['epid'] )] = item
        if cache_changed:
            success, loglines = writeFile( json.dumps( epcache_json ), self.EPISODECACHE, 'w' )
            self.LW.log( loglines )


    def _mark_episodes( self, thetype ):
        items = []
        if thetype == 'playing':
            mark_type = 0
            items = self.PLAYINGITEMS
        elif thetype == 'scanned':
            mark_type = 1
            items = self.SCANNEDITEMS
        elif thetype == 'removed':
            mark_type = 0
            items = self.REMOVEDITEMS
        for item in items:
            if self.SETTINGS['mark_on_remove'] and not thetype == 'scanned':
                self._update_episode_cache( epid=item.get( 'epid', 0 ) )
            self.TVMCACHE = _mark_one( item, mark_type, self.SETTINGS['add_followed'], self.TVMCACHE, self.TVMCACHEFILE, self.TVMAZE, self.LW )
            if self.abortRequested():
                break



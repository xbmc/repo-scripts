import sys, datetime, re
import xbmc, xbmcgui
import infodialog
import json
import operator

ADDON        = sys.modules[ "__main__" ].ADDON
ADDONID      = sys.modules[ "__main__" ].ADDONID
ADDONVERSION = sys.modules[ "__main__" ].ADDONVERSION
LANGUAGE     = sys.modules[ "__main__" ].LANGUAGE
CWD          = sys.modules[ "__main__" ].CWD

ACTION_CANCEL_DIALOG = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_CONTEXT_MENU = ( 117, )
ACTION_OSD = ( 107, 163, )
ACTION_SHOW_GUI = ( 18, )
ACTION_SHOW_INFO = ( 11, )

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        # some sanitize work for search string: strip the input and replace some chars
        self.searchstring = kwargs[ "searchstring" ].replace('(', '[(]').replace(')', '[)]').replace('+', '[+]').strip()
        self.params = kwargs[ "params" ]
        log('script version %s started' % ADDONVERSION)
        self.nextsearch = False
        self.selectaction = self._getSelect_Action()

    def onInit( self ):
        if self.searchstring == '':
            self._close()
        else:
            self.window_id = xbmcgui.getCurrentWindowDialogId()
            xbmcgui.Window(self.window_id).setProperty('GlobalSearch.SearchString', self.searchstring)
            self.ACTORSUPPORT = True
            self.DIRECTORSUPPORT = True
            self.EPGSUPPORT = True
            self._hide_controls()
            if not self.nextsearch:
                self._parse_argv()
                if self.params == {}:
                    self._load_settings()
            self._reset_variables()
            self._init_variables()
            self._fetch_items()

    def _fetch_items( self ):
        if self.movies == 'true':
            self._fetch_movies('title', 342, 111)
        if self.tvshows == 'true':
            self._fetch_tvshows()
        if self.episodes == 'true':
            self._fetch_episodes()
        if self.musicvideos == 'true':
            self._fetch_musicvideos()
        if self.artists == 'true':
            self._fetch_artists()
        if self.albums == 'true':
            self._fetch_albums()
        if self.songs == 'true':
            self._fetch_songs()
        if self.actors == 'true' and self.ACTORSUPPORT:
            self._fetch_movies('actor', 344, 211)
        if self.epg == 'true' and self.EPGSUPPORT:
            self._fetch_channelgroups()
        if self.directors == 'true' and self.DIRECTORSUPPORT:
            self._fetch_movies('director', 20348, 231)
        self._check_focus()

    def _hide_controls( self ):
        self.getControl( 119 ).setVisible( False )
        self.getControl( 129 ).setVisible( False )
        self.getControl( 139 ).setVisible( False )
        self.getControl( 149 ).setVisible( False )
        self.getControl( 159 ).setVisible( False )
        self.getControl( 169 ).setVisible( False )
        self.getControl( 179 ).setVisible( False )
        self.getControl( 189 ).setVisible( False )
        try:
            self.getControl( 219 ).setVisible( False )
        except:
            self.ACTORSUPPORT = False
        try:
            self.getControl( 229 ).setVisible( False )
        except:
            self.EPGSUPPORT = False
        try:
            self.getControl( 239 ).setVisible( False )
        except:
            self.DIRECTORSUPPORT = False
        self.getControl( 198 ).setVisible( False )
        self.getControl( 199 ).setVisible( False )

    def _reset_controls( self ):
        self.getControl( 111 ).reset()
        self.getControl( 121 ).reset()
        self.getControl( 131 ).reset()
        self.getControl( 141 ).reset()
        self.getControl( 151 ).reset()
        self.getControl( 161 ).reset()
        self.getControl( 171 ).reset()
        self.getControl( 181 ).reset()
        if self.ACTORSUPPORT:
            self.getControl( 211 ).reset()
        if self.EPGSUPPORT:
            self.getControl( 221 ).reset()
        if self.DIRECTORSUPPORT:
            self.getControl( 231 ).reset()

    def _parse_argv( self ):
        self.movies = self.params.get( "movies", "" )
        self.tvshows = self.params.get( "tvshows", "" )
        self.episodes = self.params.get( "episodes", "" )
        self.musicvideos = self.params.get( "musicvideos", "" )
        self.artists = self.params.get( "artists", "" )
        self.albums = self.params.get( "albums", "" )
        self.songs = self.params.get( "songs", "" )
        self.actors = self.params.get( "actors", "" )
        self.directors = self.params.get( "directors", "" )
        self.epg = self.params.get( "epg", "" )

    def _load_settings( self ):
        self.movies = ADDON.getSetting( "movies" )
        self.tvshows = ADDON.getSetting( "tvshows" )
        self.episodes = ADDON.getSetting( "episodes" )
        self.musicvideos = ADDON.getSetting( "musicvideos" )
        self.artists = ADDON.getSetting( "artists" )
        self.albums = ADDON.getSetting( "albums" )
        self.songs = ADDON.getSetting( "songs" )
        self.actors = ADDON.getSetting( "actors" )
        self.directors = ADDON.getSetting( "directors" )
        self.epg = ADDON.getSetting( "epg" )

    def _reset_variables( self ):
        self.focusset= 'false'
        self.getControl( 190 ).setLabel( xbmc.getLocalizedString(194) )

    def _init_variables( self ):
        self.fetch_seasonepisodes = 'false'
        self.fetch_albumssongs = 'false'
        self.fetch_songalbum = 'false'
        self.playingtrailer = 'false'
        self.getControl( 198 ).setLabel( LANGUAGE(32299) )
        self.Player = MyPlayer()
        self.Player.gui = self

    def _fetch_movies( self, query, label, control ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(label) )
        count = 0
        if query == 'movies':
            rule = '{"or": [{"field": "title", "operator": "contains", "value": "%s"}, {"field": "originaltitle", "operator": "contains", "value": "%s"}]}' % (self.searchstring, self.searchstring) 
        else:
            rule = '{"field":"%s", "operator":"contains", "value":"%s"}' % (query, self.searchstring)
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "streamdetails", "genre", "studio", "year", "tagline", "plot", "plotoutline", "runtime", "fanart", "thumbnail", "file", "trailer", "playcount", "rating", "userrating", "mpaa", "director", "writer", "originaltitle", "resume","art"], "sort": { "method": "label" }, "filter": %s }, "id": 1}' % rule)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('movies'):
            for item in json_response['result']['movies']:
                movieid = str(item['movieid'])
                movie = item['title']
                count = count + 1
                director = " / ".join(item['director'])
                writer = " / ".join(item['writer'])
                path = item['file']
                genre = " / ".join(item['genre'])
                mpaa = item['mpaa']
                playcount = str(item['playcount'])
                plot = item['plot']
                outline = item['plotoutline']
                rating = str(round(float(item['rating']),1))
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                runtime = str(int((item['runtime'] / 60.0) + 0.5))
                studio = " / ".join(item['studio'])
                tagline = item['tagline']
                thumb = item['thumbnail']
                fanart = item['fanart']
                poster = item['art'].get('poster', '')
                clearart = item['art'].get('clearart', '')
                clearlogo = item['art'].get('clearlogo', '')
                disc = item['art'].get('disc', '')
                banner = item['art'].get('banner', '')
                landscape = item['art'].get('landscape', '')
                trailer = item['trailer']
                originaltitle = item['originaltitle']
                year = str(item['year'])
                resume = str(item['resume']['position'])
                if item['streamdetails']['audio'] != []:
                    audiochannels = str(item['streamdetails']['audio'][0]['channels'])
                    audiocodec = str(item['streamdetails']['audio'][0]['codec'])
                else:
                    audiochannels = ''
                    audiocodec = ''
                if item['streamdetails']['video'] != []:
                    videocodec = str(item['streamdetails']['video'][0]['codec'])
                    videoaspect = float(item['streamdetails']['video'][0]['aspect'])
                    if videoaspect <= 1.4859:
                        videoaspect = '1.33'
                    elif videoaspect <= 1.7190:
                        videoaspect = '1.66'
                    elif videoaspect <= 1.8147:
                        videoaspect = '1.78'
                    elif videoaspect <= 2.0174:
                        videoaspect = '1.85'
                    elif videoaspect <= 2.2738:
                        videoaspect = '2.20'
                    else:
                        videoaspect = '2.35'
                    videowidth = item['streamdetails']['video'][0]['width']
                    videoheight = item['streamdetails']['video'][0]['height']
                    if videowidth <= 720 and videoheight <= 480:
                        videoresolution = '480'
                    elif videowidth <= 768 and videoheight <= 576:
                        videoresolution = '576'
                    elif videowidth <= 960 and videoheight <= 544:
                        videoresolution = '540'
                    elif videowidth <= 1280 and videoheight <= 720:
                        videoresolution = '720'
                    else:
                        videoresolution = '1080'
                else:
                    videocodec = ''
                    videoaspect = ''
                    videoresolution = ''

                listitem = xbmcgui.ListItem(label=movie, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "art(fanart)", fanart )
                listitem.setProperty( "art(clearart)", clearart )
                listitem.setProperty( "art(clearlogo)", clearlogo )
                listitem.setProperty( "art(disc)", disc )
                listitem.setProperty( "art(banner)", banner )
                listitem.setProperty( "art(landscape)", landscape )
                listitem.setProperty( "originaltitle", originaltitle )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "plotoutline", outline )
                listitem.setProperty( "duration", runtime )
                listitem.setProperty( "studio", studio )
                listitem.setProperty( "tagline", tagline )
                listitem.setProperty( "year", year )
                listitem.setProperty( "trailer", trailer )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "mpaa", mpaa )
                listitem.setProperty( "writer", writer )
                listitem.setProperty( "director", director )
                listitem.setProperty( "videoresolution", videoresolution )
                listitem.setProperty( "videocodec", videocodec )
                listitem.setProperty( "videoaspect", videoaspect )
                listitem.setProperty( "audiocodec", audiocodec )
                listitem.setProperty( "audiochannels", audiochannels )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", movieid )
                listitem.setProperty( "resume", resume )
                listitem.setProperty( "title", movie )
                listitems.append(listitem)
        self.getControl( control ).addItems( listitems )
        if count > 0:
            self.getControl( control - 1 ).setLabel( str(count) )
            self.getControl( control + 8 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( control ) )
                self.focusset = 'true'

    def _fetch_tvshows( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(20343) )
        count = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "genre", "studio", "premiered", "plot", "fanart", "thumbnail", "playcount", "year", "mpaa", "episode", "rating", "userrating", "art"], "sort": { "method": "label" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('tvshows'):
            for item in json_response['result']['tvshows']:
                tvshow = item['title']
                count = count + 1
                episode = str(item['episode'])
                genre = " / ".join(item['genre'])
                mpaa = item['mpaa']
                playcount = str(item['playcount'])
                plot = item['plot']
                premiered = item['premiered']
                rating = str(round(float(item['rating']),1))
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                studio = " / ".join(item['studio'])
                thumb = item['thumbnail']
                fanart = item['fanart']
                poster = item['art'].get('poster', '')
                clearart = item['art'].get('clearart', '')
                clearlogo = item['art'].get('clearlogo', '')
                banner = item['art'].get('banner', '')
                landscape = item['art'].get('landscape', '')
                tvshowid = str(item['tvshowid'])
                path = path = 'videodb://tvshows/titles/' + tvshowid + '/'
                year = str(item['year'])
                listitem = xbmcgui.ListItem(label=tvshow, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "art(fanart)", fanart )
                listitem.setProperty( "art(clearart)", clearart )
                listitem.setProperty( "art(clearlogo)", clearlogo )
                listitem.setProperty( "art(banner)", banner )
                listitem.setProperty( "art(landscape)", landscape )
                listitem.setProperty( "episode", episode )
                listitem.setProperty( "mpaa", mpaa )
                listitem.setProperty( "year", year )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "premiered", premiered )
                listitem.setProperty( "studio", studio )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", tvshowid )
                listitems.append(listitem)
        self.getControl( 121 ).addItems( listitems )
        if count > 0:
            self.getControl( 120 ).setLabel( str(count) )
            self.getControl( 129 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 121 ) )
                self.focusset = 'true'

    def _fetch_seasons( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(20343) )
        count = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["showtitle", "season", "fanart", "thumbnail", "playcount", "episode", "userrating", "art"], "sort": { "method": "label" }, "tvshowid":%s }, "id": 1}' % self.tvshowid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('seasons'):
            for item in json_response['result']['seasons']:
                tvshow = item['showtitle']
                count = count + 1
                episode = str(item['episode'])
                fanart = item['fanart']
                poster = item['art'].get('tvshow.poster', '')
                clearart = item['art'].get('tvshow.clearart', '')
                clearlogo = item['art'].get('tvshow.clearlogo', '')
                banner = item['art'].get('tvshow.banner', '')
                landscape = item['art'].get('tvshow.landscape', '')
                sPoster = item['art'].get('season.poster', '')
                path = 'videodb://tvshows/titles/' + self.tvshowid + '/' + str(item['season']) + '/'
                season = item['label']
                playcount = str(item['playcount'])
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                thumb = item['thumbnail']
                listitem = xbmcgui.ListItem(label=season, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "art(fanart)", fanart )
                listitem.setProperty( "art(clearart)", clearart )
                listitem.setProperty( "art(clearlogo)", clearlogo )
                listitem.setProperty( "art(banner)", banner )
                listitem.setProperty( "art(landscape)", landscape )
                listitem.setProperty( "art(season.poster)", sPoster )
                listitem.setProperty( "episode", episode )
                listitem.setProperty( "tvshowtitle", tvshow )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", str(self.tvshowid) )
                listitems.append(listitem)
        self.getControl( 131 ).addItems( listitems )
        if count > 0:
            self.foundseasons= 'true'
            self.getControl( 130 ).setLabel( str(count) )
            self.getControl( 139 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 131 ) )
                self.focusset = 'true'

    def _fetch_episodes( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(20360) )
        count = 0
        if self.fetch_seasonepisodes == 'true':
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "streamdetails", "plot", "firstaired", "runtime", "season", "episode", "showtitle", "thumbnail", "fanart", "file", "playcount", "director", "rating", "userrating", "resume", "art"], "sort": { "method": "title" }, "tvshowid":%s }, "id": 1}' % self.tvshowid)
        else:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "streamdetails", "plot", "firstaired", "runtime", "season", "episode", "showtitle", "thumbnail", "fanart", "file", "playcount", "director", "rating", "userrating", "resume", "art"], "sort": { "method": "title" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('episodes'):
            for item in json_response['result']['episodes']:
                if self.fetch_seasonepisodes == 'true':
                    episode = item['showtitle']
                else:
                    episode = item['title']
                count = count + 1
                if self.fetch_seasonepisodes == 'true':
                    tvshowname = episode
                    episode = item['title']
                else:
                    tvshowname = item['showtitle']
                director = " / ".join(item['director'])
                fanart = item['fanart']
                episodeid = str(item['episodeid'])
                episodenumber = "%.2d" % float(item['episode'])
                path = item['file']
                plot = item['plot']
                runtime = str(int((item['runtime'] / 60.0) + 0.5))
                premiered = item['firstaired']
                rating = str(round(float(item['rating']),1))
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                seasonnumber = '%.2d' % float(item['season'])
                playcount = str(item['playcount'])
                thumb = item['thumbnail']
                fanart = item['fanart']
                poster = item['art'].get('tvshow.poster', '')
                clearart = item['art'].get('tvshow.clearart', '')
                clearlogo = item['art'].get('tvshow.clearlogo', '')
                banner = item['art'].get('tvshow.banner', '')
                landscape = item['art'].get('tvshow.landscape', '')
                sPoster = item['art'].get('season.poster', '')
                resume = str(item['resume']['position'])
                if item['streamdetails']['audio'] != []:
                    audiochannels = str(item['streamdetails']['audio'][0]['channels'])
                    audiocodec = str(item['streamdetails']['audio'][0]['codec'])
                else:
                    audiochannels = ''
                    audiocodec = ''
                if item['streamdetails']['video'] != []:
                    videocodec = str(item['streamdetails']['video'][0]['codec'])
                    videoaspect = float(item['streamdetails']['video'][0]['aspect'])
                    if videoaspect <= 1.4859:
                        videoaspect = '1.33'
                    elif videoaspect <= 1.7190:
                        videoaspect = '1.66'
                    elif videoaspect <= 1.8147:
                        videoaspect = '1.78'
                    elif videoaspect <= 2.0174:
                        videoaspect = '1.85'
                    elif videoaspect <= 2.2738:
                        videoaspect = '2.20'
                    else:
                        videoaspect = '2.35'
                    videowidth = item['streamdetails']['video'][0]['width']
                    videoheight = item['streamdetails']['video'][0]['height']
                    if videowidth <= 720 and videoheight <= 480:
                        videoresolution = '480'
                    elif videowidth <= 768 and videoheight <= 576:
                        videoresolution = '576'
                    elif videowidth <= 960 and videoheight <= 544:
                        videoresolution = '540'
                    elif videowidth <= 1280 and videoheight <= 720:
                        videoresolution = '720'
                    else:
                        videoresolution = '1080'
                else:
                    videocodec = ''
                    videoaspect = ''
                    videoresolution = ''
                listitem = xbmcgui.ListItem(label=episode, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "art(fanart)", fanart )
                listitem.setProperty( "art(clearart)", clearart )
                listitem.setProperty( "art(clearlogo)", clearlogo )
                listitem.setProperty( "art(banner)", banner )
                listitem.setProperty( "art(landscape)", landscape )
                listitem.setProperty( "art(season.poster)", sPoster )
                listitem.setProperty( "episode", episodenumber )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "director", director )
                listitem.setProperty( "season", seasonnumber )
                listitem.setProperty( "duration", runtime )
                listitem.setProperty( "tvshowtitle", tvshowname )
                listitem.setProperty( "premiered", premiered )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "videoresolution", videoresolution )
                listitem.setProperty( "videocodec", videocodec )
                listitem.setProperty( "videoaspect", videoaspect )
                listitem.setProperty( "audiocodec", audiocodec )
                listitem.setProperty( "audiochannels", audiochannels )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", episodeid )
                listitem.setProperty( "resume", resume )
                listitem.setProperty( "title", episode )
                listitems.append(listitem)
        self.getControl( 141 ).addItems( listitems )
        if count > 0:
            self.getControl( 140 ).setLabel( str(count) )
            self.getControl( 149 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 141 ) )
                self.focusset = 'true'

    def _fetch_musicvideos( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(20389) )
        count = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["title", "streamdetails", "runtime", "genre", "studio", "artist", "album", "year", "plot", "fanart", "thumbnail", "file", "playcount", "director", "rating", "userrating", "art"], "sort": { "method": "label" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('musicvideos'):
            for item in json_response['result']['musicvideos']:
                musicvideoid = str(item['musicvideoid'])
                musicvideo = item['title']
                count = count + 1
                album = item['album']
                artist = " / ".join(item['artist'])
                director = " / ".join(item['director'])
                fanart = item['fanart']
                poster = item['art'].get('poster', '')
                clearart = item['art'].get('clearart', '')
                clearlogo = item['art'].get('clearlogo', '')
                disc = item['art'].get('disc', '')
                path = item['file']
                genre = " / ".join(item['genre'])
                plot = item['plot']
                rating = str(round(float(item['rating']),1))
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                studio = " / ".join(item['studio'])
                thumb = item['thumbnail']
                playcount = str(item['playcount'])
                year = str(item['year'])
                if year == '0':
                    year = ''
                if item['streamdetails']['audio'] != []:
                    audiochannels = str(item['streamdetails']['audio'][0]['channels'])
                    audiocodec = str(item['streamdetails']['audio'][0]['codec'])
                else:
                    audiochannels = ''
                    audiocodec = ''
                if item['streamdetails']['video'] != []:
                    videocodec = str(item['streamdetails']['video'][0]['codec'])
                    videoaspect = float(item['streamdetails']['video'][0]['aspect'])
                    if videoaspect <= 1.4859:
                        videoaspect = '1.33'
                    elif videoaspect <= 1.7190:
                        videoaspect = '1.66'
                    elif videoaspect <= 1.8147:
                        videoaspect = '1.78'
                    elif videoaspect <= 2.0174:
                        videoaspect = '1.85'
                    elif videoaspect <= 2.2738:
                        videoaspect = '2.20'
                    else:
                        videoaspect = '2.35'
                    videowidth = item['streamdetails']['video'][0]['width']
                    videoheight = item['streamdetails']['video'][0]['height']
                    if videowidth <= 720 and videoheight <= 480:
                        videoresolution = '480'
                    elif videowidth <= 768 and videoheight <= 576:
                        videoresolution = '576'
                    elif videowidth <= 960 and videoheight <= 544:
                        videoresolution = '540'
                    elif videowidth <= 1280 and videoheight <= 720:
                        videoresolution = '720'
                    else:
                        videoresolution = '1080'
                    duration = str(datetime.timedelta(seconds=int(item['streamdetails']['video'][0]['duration'])))
                    if duration[0] == '0':
                        duration = duration[2:]
                else:
                    videocodec = ''
                    videoaspect = ''
                    videoresolution = ''
                    duration = ''
                listitem = xbmcgui.ListItem(label=musicvideo, iconImage='DefaultVideo.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "art(poster)", poster )
                listitem.setProperty( "art(fanart)", fanart )
                listitem.setProperty( "art(clearart)", clearart )
                listitem.setProperty( "art(clearlogo)", clearlogo )
                listitem.setProperty( "art(disc)", disc )
                listitem.setProperty( "album", album )
                listitem.setProperty( "artist", artist )
                listitem.setProperty( "director", director )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "plot", plot )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "duration", duration )
                listitem.setProperty( "studio", studio )
                listitem.setProperty( "year", year )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "videoresolution", videoresolution )
                listitem.setProperty( "videocodec", videocodec )
                listitem.setProperty( "videoaspect", videoaspect )
                listitem.setProperty( "audiocodec", audiocodec )
                listitem.setProperty( "audiochannels", audiochannels )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", musicvideoid )
                listitems.append(listitem)
        self.getControl( 151 ).addItems( listitems )
        if count > 0:
            self.getControl( 150 ).setLabel( str(count) )
            self.getControl( 159 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 151 ) )
                self.focusset = 'true'

    def _fetch_artists( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(133) )
        count = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["genre", "description", "fanart", "thumbnail", "formed", "disbanded", "born", "yearsactive", "died", "mood", "style"], "sort": { "method": "label" }, "filter": {"field": "artist", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('artists'):
            for item in json_response['result']['artists']:
                artist = item['label']
                count = count + 1
                artistid = str(item['artistid'])
                path = 'musicdb://artists/' + artistid + '/'
                born = item['born']
                description = item['description']
                died = item['died']
                disbanded = item['disbanded']
                fanart = item['fanart']
                formed = item['formed']
                genre = " / ".join(item['genre'])
                mood = " / ".join(item['mood'])
                style = " / ".join(item['style'])
                thumb = item['thumbnail']
                yearsactive = " / ".join(item['yearsactive'])
                listitem = xbmcgui.ListItem(label=artist, iconImage='DefaultArtist.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "artist_born", born )
                listitem.setProperty( "artist_died", died )
                listitem.setProperty( "artist_formed", formed )
                listitem.setProperty( "artist_disbanded", disbanded )
                listitem.setProperty( "artist_yearsactive", yearsactive )
                listitem.setProperty( "artist_mood", mood )
                listitem.setProperty( "artist_style", style )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "artist_genre", genre )
                listitem.setProperty( "artist_description", description )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", artistid )
                listitems.append(listitem)
        self.getControl( 161 ).addItems( listitems )
        if count > 0:
            self.getControl( 160 ).setLabel( str(count) )
            self.getControl( 169 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 161 ) )
                self.focusset = 'true'

    def _fetch_albums( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(132) )
        count = 0
        if self.fetch_albumssongs == 'true':
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "artist", "genre", "year", "thumbnail", "fanart", "theme", "type", "mood", "style", "rating", "userrating"], "sort": { "method": "label" }, "filter": {"artistid": %s} }, "id": 1}' % self.artistid)
        else:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "albumlabel", "artist", "genre", "year", "thumbnail", "fanart", "theme", "type", "mood", "style", "rating", "userrating"], "sort": { "method": "label" }, "filter": {"field": "album", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('albums'):
            for item in json_response['result']['albums']:
                if self.fetch_albumssongs == 'true':
                    album = " / ".join(item['artist'])
                else:
                    album = item['title']
                count = count + 1
                if self.fetch_albumssongs == 'true':
                    artist = album
                    album = item['title']
                else:
                    artist = " / ".join(item['artist'])
                    if self.fetch_songalbum == 'true':
                        if not artist == self.artistname:
                            count = count - 1
                            return
                albumid = str(item['albumid'])
                path = 'musicdb://albums/' + albumid + '/'
                label = item['albumlabel']
                description = item['description']
                fanart = item['fanart']
                genre = " / ".join(item['genre'])
                mood = " / ".join(item['mood'])
                rating = str(item['rating'])
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                style = " / ".join(item['style'])
                theme = " / ".join(item['theme'])
                albumtype = item['type']
                thumb = item['thumbnail']
                year = str(item['year'])
                listitem = xbmcgui.ListItem(label=album, iconImage='DefaultAlbumCover.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "artist", artist )
                listitem.setProperty( "album_label", label )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "album_description", description )
                listitem.setProperty( "album_theme", theme )
                listitem.setProperty( "album_style", style )
                listitem.setProperty( "album_rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "album_type", albumtype )
                listitem.setProperty( "album_mood", mood )
                listitem.setProperty( "year", year )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", albumid )
                listitems.append(listitem)
        self.getControl( 171 ).addItems( listitems )
        if count > 0:
            self.getControl( 170 ).setLabel( str(count) )
            self.getControl( 179 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 171 ) )
                self.focusset = 'true'

    def _fetch_songs( self ):
        listitems = []
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(134) )
        count = 0
        if self.fetch_albumssongs == 'true':
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "artist", "album", "genre", "duration", "year", "file", "thumbnail", "fanart", "comment", "rating", "userrating", "track", "playcount"], "sort": { "method": "title" }, "filter": {"artistid": %s} }, "id": 1}' % self.artistid)
        else:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "artist", "album", "genre", "duration", "year", "file", "thumbnail", "fanart", "comment", "rating", "userrating", "track", "playcount"], "sort": { "method": "title" }, "filter": {"field": "title", "operator": "contains", "value": "%s"} }, "id": 1}' % self.searchstring)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('songs'):
            for item in json_response['result']['songs']:
                if self.fetch_albumssongs == 'true':
                    song = " / ".join(item['artist'])
                else:
                    song = item['title']
                count = count + 1
                if self.fetch_albumssongs == 'true':
                    artist = song
                    song = item['label']
                else:
                    artist = " / ".join(item['artist'])
                songid = str(item['songid'])
                album = item['album']
                comment = item['comment']
                duration = str(datetime.timedelta(seconds=int(item['duration'])))
                if duration[0] == '0':
                    duration = duration[2:]
                fanart = item['fanart']
                path = item['file']
                genre = " / ".join(item['genre'])
                thumb = item['thumbnail']
                track = str(item['track'])
                playcount = str(item['playcount'])
                rating = str(item['rating'])
                userrating = str(item['userrating'])
                if userrating == '0':
                    userrating = ''
                year = str(item['year'])
                listitem = xbmcgui.ListItem(label=song, iconImage='DefaultAlbumCover.png', thumbnailImage=thumb)
                listitem.setProperty( "icon", thumb )
                listitem.setProperty( "artist", artist )
                listitem.setProperty( "album", album )
                listitem.setProperty( "genre", genre )
                listitem.setProperty( "comment", comment )
                listitem.setProperty( "track", track )
                listitem.setProperty( "rating", rating )
                listitem.setProperty( "userrating", userrating )
                listitem.setProperty( "playcount", playcount )
                listitem.setProperty( "duration", duration )
                listitem.setProperty( "fanart", fanart )
                listitem.setProperty( "year", year )
                listitem.setProperty( "path", path )
                listitem.setProperty( "dbid", songid )
                listitems.append(listitem)
        self.getControl( 181 ).addItems( listitems )
        if count > 0:
            self.getControl( 180 ).setLabel( str(count) )
            self.getControl( 189 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 181 ) )
                self.focusset = 'true'

    def _fetch_channelgroups( self ):
        self.getControl( 191 ).setLabel( xbmc.getLocalizedString(19069) )
        channelgrouplist = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetChannelGroups", "params": {"channeltype": "tv"}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if (json_response.has_key('result')) and (json_response['result'] != None) and (json_response['result'].has_key('channelgroups')):
            for item in json_response['result']['channelgroups']:
                channelgrouplist.append(item['channelgroupid'])
            if channelgrouplist:
                self._fetch_channels(channelgrouplist)

    def _fetch_channels( self, channelgrouplist ):
        # get all channel id's
        channellist = []
        for channelgroupid in channelgrouplist:
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetChannels", "params": {"channelgroupid": %i, "properties": ["channel", "thumbnail"]}, "id": 1}' % channelgroupid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = json.loads(json_query)
            if (json_response.has_key('result')) and (json_response['result'] != None) and (json_response['result'].has_key('channels')):
                for item in json_response['result']['channels']:
                    channellist.append(item)
        if channellist:
            # remove duplicates
            channels = [dict(tuples) for tuples in set(tuple(item.items()) for item in channellist)]
            # sort
            channels.sort(key=operator.itemgetter('channelid'))
            self._fetch_epg(channels)

    def _fetch_epg( self, channels ):
        listitems = []
        count = 0
        # get all programs for every channel id
        for channel in channels:
            channelid = channel['channelid']
            channelname = channel['label']
            channelthumb = channel['thumbnail']
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetBroadcasts", "params": {"channelid": %i, "properties": ["starttime", "endtime", "runtime", "genre", "plot"]}, "id": 1}' % channelid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = json.loads(json_query)
            if (json_response.has_key('result')) and (json_response['result'] != None) and (json_response['result'].has_key('broadcasts')):
                for item in json_response['result']['broadcasts']:
                    broadcastname = item['label']
                    epgmatch = re.search( '.*' + self.searchstring + '.*', broadcastname, re.I )
                    if epgmatch:
                        count = count + 1
                        broadcastid = item['broadcastid']
                        duration = item['runtime']
                        genre = item['genre'][0]
                        plot = item['plot']
                        starttime = item['starttime']
                        endtime = item['endtime']
                        listitem = xbmcgui.ListItem(label=broadcastname, iconImage='DefaultFolder.png', thumbnailImage=channelthumb)
                        listitem.setProperty( "icon", channelthumb )
                        listitem.setProperty( "genre", genre )
                        listitem.setProperty( "plot", plot )
                        listitem.setProperty( "starttime", starttime )
                        listitem.setProperty( "endtime", endtime )
                        listitem.setProperty( "duration", str(duration) )
                        listitem.setProperty( "channelname", channelname )
                        listitem.setProperty( "dbid", str(channelid) )
                        listitems.append(listitem)
        self.getControl( 221 ).addItems( listitems )
        if count > 0:
            self.getControl( 220 ).setLabel( str(count) )
            self.getControl( 229 ).setVisible( True )
            if self.focusset == 'false':
                xbmc.sleep(100)
                self.setFocus( self.getControl( 221 ) )
                self.focusset = 'true'

    def _getTvshow_Seasons( self ):
        self.fetch_seasonepisodes = 'true'
        listitem = self.getControl( 121 ).getSelectedItem()
        self.tvshowid = listitem.getProperty('dbid')
        self.searchstring = listitem.getLabel().replace('(','[(]').replace(')','[)]').replace('+','[+]')
        self._reset_variables()
        self._hide_controls()
        self._reset_controls()
        self._fetch_seasons()
        self._check_focus()
        self.fetch_seasonepisodes = 'false'

    def _getTvshow_Episodes( self ):
        self.fetch_seasonepisodes = 'true'
        listitem = self.getControl( 121 ).getSelectedItem()
        self.tvshowid = listitem.getProperty('dbid')
        self.searchstring = listitem.getLabel().replace('(','[(]').replace(')','[)]').replace('+','[+]')
        self._reset_variables()
        self._hide_controls()
        self._reset_controls()
        self._fetch_episodes()
        self._check_focus()
        self.fetch_seasonepisodes = 'false'

    def _getArtist_Albums( self ):
        self.fetch_albumssongs = 'true'
        listitem = self.getControl( 161 ).getSelectedItem()
        self.artistid = listitem.getProperty('dbid')
        self.searchstring = listitem.getLabel().replace('(','[(]').replace(')','[)]').replace('+','[+]')
        self._reset_variables()
        self._hide_controls()
        self._reset_controls()
        self._fetch_albums()
        self._check_focus()
        self.fetch_albumssongs = 'false'

    def _getArtist_Songs( self ):
        self.fetch_albumssongs = 'true'
        listitem = self.getControl( 161 ).getSelectedItem()
        self.artistid = listitem.getProperty('dbid')
        self.searchstring = listitem.getLabel().replace('(','[(]').replace(')','[)]').replace('+','[+]')
        self._reset_variables()
        self._hide_controls()
        self._reset_controls()
        self._fetch_songs()
        self._check_focus()
        self.fetch_albumssongs = 'false'

    def _getSong_Album( self ):
        self.fetch_songalbum = 'true'
        listitem = self.getControl( 181 ).getSelectedItem()
        self.artistname = listitem.getProperty('artist')
        self.searchstring = listitem.getProperty('album').replace('(','[(]').replace(')','[)]').replace('+','[+]')
        self._reset_variables()
        self._hide_controls()
        self._reset_controls()
        self._fetch_albums()
        self._check_focus()
        self.fetch_songalbum = 'false'

    def _getSelect_Action( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue","params":{"setting":"myvideos.selectaction"}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = json.loads(json_query)
        if json_response.has_key('result') and (json_response['result'] != None) and json_response['result'].has_key('value'):
            return {0: 'choose', 1: 'play', 2: 'resume',3: 'info'}[json_response['result']['value']]
   
    def _play_video( self, path , title='' , resume=0 ):
        if resume > 0:
            if self.selectaction == 'choose':
                minutes, seconds = divmod(resume, 60) ; hours, minutes = divmod( minutes , 60 )
                if xbmcgui.Dialog().yesno( title , '' , '' , '%s %02d:%02d:%02d' % ( LANGUAGE(32212), hours, minutes, seconds ) , LANGUAGE(32213) , LANGUAGE(32214) ) == True:
                    resume = 0
            elif self.selectaction == 'play':
                resume = 0
            elif self.selectaction == 'info':
                return
        self.Player.resume = resume
        xbmc.Player().play( path )
        self.close()

    def _play_audio( self, path, listitem ):
        self._close()
        xbmc.Player().play( path, listitem )

    def _play_trailer( self ):
        self.playingtrailer = 'true'
        self.getControl( 100 ).setVisible( False )
        self.Player.play( self.trailer )

    def _trailerstopped( self ):
        self.getControl( 100 ).setVisible( True )
        self.playingtrailer = 'false'

    def _play_album( self ):
        self._close()
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(self.albumid))

    def _browse_video( self, path ):
        self._close()
        xbmc.executebuiltin('ActivateWindow(Videos,' + path + ',return)')

    def _browse_audio( self, path ):
        self._close()
        xbmc.executebuiltin('ActivateWindow(Music,' + path + ',return)')

    def _browse_album( self ):
        listitem = self.getControl( 171 ).getSelectedItem()
        path = listitem.getProperty('path')
        self._close()
        xbmc.executebuiltin('ActivateWindow(Music,' + path + ',return)')

    def _check_focus( self ):
        self.getControl( 190 ).setLabel( '' )
        self.getControl( 191 ).setLabel( '' )
        self.getControl( 198 ).setVisible( True )
        if self.focusset == 'false':
            self.getControl( 199 ).setVisible( True )
            self.setFocus( self.getControl( 198 ) )
            dialog = xbmcgui.Dialog()
            ret = dialog.yesno(xbmc.getLocalizedString(284), LANGUAGE(32298))
            if ret:
                self._newSearch()

    def _showContextMenu( self ):
        labels = ()
        functions = ()
        controlId = self.getFocusId()
        if controlId == 111:
            labels += ( xbmc.getLocalizedString(13346), )
            functions += ( self._showInfo, )
            listitem = self.getControl( 111 ).getSelectedItem()
            self.trailer = listitem.getProperty('trailer')
            if self.trailer:
                labels += ( LANGUAGE(32205), )
                functions += ( self._play_trailer, )
        elif controlId == 121:
            labels += ( xbmc.getLocalizedString(20351), LANGUAGE(32207), LANGUAGE(32208), )
            functions += ( self._showInfo, self._getTvshow_Seasons, self._getTvshow_Episodes, )
        elif controlId == 131:
            labels += ( LANGUAGE(32204), )
            functions += ( self._showInfo, )
        elif controlId == 141:
            labels += ( xbmc.getLocalizedString(20352), )
            functions += ( self._showInfo, )
        elif controlId == 151:
            labels += ( xbmc.getLocalizedString(20393), )
            functions += ( self._showInfo, )
        elif controlId == 161:
            labels += ( xbmc.getLocalizedString(21891), LANGUAGE(32209), LANGUAGE(32210), )
            functions += ( self._showInfo, self._getArtist_Albums, self._getArtist_Songs, )
        elif controlId == 171:
            labels += ( xbmc.getLocalizedString(13351), LANGUAGE(32203), )
            functions += ( self._showInfo, self._browse_album, )
        elif controlId == 181:
            labels += ( xbmc.getLocalizedString(658), LANGUAGE(32206), )
            functions += ( self._showInfo, self._getSong_Album, )
        elif controlId == 211:
            labels += ( xbmc.getLocalizedString(13346), )
            functions += ( self._showInfo, )
            listitem = self.getControl( 211 ).getSelectedItem()
            self.trailer = listitem.getProperty('trailer')
            if self.trailer:
                labels += ( LANGUAGE(32205), )
                functions += ( self._play_trailer, )
        elif controlId == 221:
            labels += ( xbmc.getLocalizedString(19047), )
            functions += ( self._showInfo, )
        elif controlId == 231:
            labels += ( xbmc.getLocalizedString(13346), )
            functions += ( self._showInfo, )
            listitem = self.getControl( 231 ).getSelectedItem()
            self.trailer = listitem.getProperty('trailer')
            if self.trailer:
                labels += ( LANGUAGE(32205), )
                functions += ( self._play_trailer, )
        if labels:
            selection = xbmcgui.Dialog().contextmenu(labels)
            if selection >= 0:
                functions[ selection ]()

    def _showInfo( self ):
        items = []
        controlId = self.getFocusId()
        if controlId == 111:
            content = "movies"
        elif controlId == 121:
            content = "tvshows"
        elif controlId == 131:
            content = "seasons"
        elif controlId == 141:
            content = "episodes"
        elif controlId == 151:
            content = "musicvideos"
        elif controlId == 161:
            content = "artists"
        elif controlId == 171:
            content = "albums"
        elif controlId == 181:
            content = "songs"
        elif controlId == 211:
            content = "actors"
        elif controlId == 221:
            content = "epg"
        elif controlId == 231:
            content = "directors"
        listitem = self.getControl( controlId ).getSelectedItem()
        info_dialog = infodialog.GUI( "script-globalsearch-infodialog.xml" , CWD, "default", listitem=listitem, content=content )
        info_dialog.doModal()
        if info_dialog.action is not None:
            if info_dialog.action == 'play_programme':
                listitem = self.getControl( 221 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._play_video(path)
            elif info_dialog.action == 'play_movie':
                listitem = self.getControl( 111 ).getSelectedItem()
                path = listitem.getProperty('path')
                title = listitem.getProperty('title')
                resume = int(float(listitem.getProperty('resume')))
                self._play_video(path, title, resume)
            elif info_dialog.action == 'play_trailer':
                listitem = self.getControl( 111 ).getSelectedItem()
                self.trailer = listitem.getProperty('trailer')
                self._play_trailer()
            elif info_dialog.action == 'browse_tvshow':
                listitem = self.getControl( 121 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._browse_video(path)
            elif info_dialog.action == 'browse_season':
                listitem = self.getControl( 131 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._browse_video(path)
            elif info_dialog.action == 'play_episode':
                listitem = self.getControl( 141 ).getSelectedItem()
                path = listitem.getProperty('path')
                title = listitem.getProperty('title')
                resume = int(float(listitem.getProperty('resume')))
                self._play_video(path, title, resume)
            elif info_dialog.action == 'play_musicvideo':
                listitem = self.getControl( 151 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._play_video(path)
            elif info_dialog.action == 'browse_artist':
                listitem = self.getControl( 161 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._browse_audio(path)
            elif info_dialog.action == 'play_album':
                listitem = self.getControl( 171 ).getSelectedItem()
                self.albumid = listitem.getProperty('dbid')
                self._play_album()
            elif info_dialog.action == 'browse_album':
                listitem = self.getControl( 171 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._browse_audio(path)
            elif info_dialog.action == 'play_song':
                listitem = self.getControl( 181 ).getSelectedItem()
                path = listitem.getProperty('path')
            elif info_dialog.action == 'play_movie_actors':
                listitem = self.getControl( 211 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._play_video(path)
                self._play_audio(path, listitem)
            elif info_dialog.action == 'play_trailer_actors':
                listitem = self.getControl( 211 ).getSelectedItem()
                self.trailer = listitem.getProperty('trailer')
                self._play_trailer()
            elif info_dialog.action == 'play_movie_directors':
                listitem = self.getControl( 231 ).getSelectedItem()
                path = listitem.getProperty('path')
                self._play_video(path)
                self._play_audio(path, listitem)
            elif info_dialog.action == 'play_trailer_directors':
                listitem = self.getControl( 231 ).getSelectedItem()
                self.trailer = listitem.getProperty('trailer')
                self._play_trailer()
        del info_dialog

    def _newSearch( self ):
        keyboard = xbmc.Keyboard( '', LANGUAGE(32101), False )
        keyboard.doModal()
        if ( keyboard.isConfirmed() ):
            self.searchstring = keyboard.getText()
            self._reset_controls()
            self.onInit()

    def onClick( self, controlId ):
        if controlId == 111:
            listitem = self.getControl( 111 ).getSelectedItem()
            path = listitem.getProperty('path')
            title = listitem.getProperty('title')
            resume = int(float(listitem.getProperty('resume')))
            self._play_video(path, title, resume)
        elif controlId == 121:
            listitem = self.getControl( 121 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._browse_video(path)
        elif controlId == 131:
            listitem = self.getControl( 131 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._browse_video(path)
        elif controlId == 141:
            listitem = self.getControl( 141 ).getSelectedItem()
            path = listitem.getProperty('path')
            title = listitem.getProperty('title')
            resume = int(float(listitem.getProperty('resume')))
            self._play_video(path, title, resume)
        elif controlId == 151:
            listitem = self.getControl( 151 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._play_video(path)
        elif controlId == 161:
            listitem = self.getControl( 161 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._browse_audio(path)
        elif controlId == 171:
            listitem = self.getControl( 171 ).getSelectedItem()
            self.albumid = listitem.getProperty('dbid')
            self._play_album()
        elif controlId == 181:
            listitem = self.getControl( 181 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._play_audio(path, listitem)
        if controlId == 211:
            listitem = self.getControl( 211 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._play_video(path)
        elif controlId == 231:
            listitem = self.getControl( 231 ).getSelectedItem()
            path = listitem.getProperty('path')
            self._play_video(path)
        elif controlId == 198:
            self._newSearch()

    def onAction( self, action ):
        if action.getId() in ACTION_CANCEL_DIALOG:
            if self.playingtrailer == 'false':
                self._close()
            else:
                self.Player.stop()
                self._trailerstopped()
        elif action.getId() in ACTION_CONTEXT_MENU:
            self._showContextMenu()
        elif action.getId() in ACTION_OSD:
            if self.playingtrailer == 'true' and xbmc.getCondVisibility('videoplayer.isfullscreen'):
                xbmc.executebuiltin("ActivateWindow(12901)")
        elif action.getId() in ACTION_SHOW_GUI:
            if self.playingtrailer == 'true':
                self.Player.stop()
                self._trailerstopped()
        elif action.getId() in ACTION_SHOW_INFO:
            if self.playingtrailer == 'true' and xbmc.getCondVisibility('videoplayer.isfullscreen'):
                xbmc.executebuiltin("ActivateWindow(142)")
            else:
                self._showInfo()

    def _close( self ):
            log('script stopped')
            self.close()
            xbmc.sleep(300)
            xbmcgui.Window(self.window_id).clearProperty('GlobalSearch.SearchString')

class MyPlayer(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__( self )
        self.resume = 0

    def onPlayBackEnded( self ):
        self.gui._trailerstopped()

    def onPlayBackStopped( self ):
        self.gui._trailerstopped()

    def onPlayBackStarted( self ):   
        self.seekTime( float( self.resume ) )

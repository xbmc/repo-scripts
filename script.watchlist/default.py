from time import strptime, mktime
from operator import itemgetter
import simplejson
import xbmc, xbmcgui, xbmcaddon
# http://mail.python.org/pipermail/python-list/2009-June/596197.html
import _strptime

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__cwd__          = __addon__.getAddonInfo('path')

def log(txt):
    message = 'script.watchlist: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_vars()
        # check how we were executed
        if self.ALBUMID:
            self._play_album( self.ALBUMID )
        else:
            # clear our property, if another instance is already running it should stop now
            self.WINDOW.clearProperty('WatchList_Running')
            self._fetch_info()
            # give a possible other instance some time to notice the empty property
            xbmc.sleep(2000)
            self.WINDOW.setProperty('WatchList_Running', 'True')
            self._daemon()

    def _parse_argv( self ):
        try:
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            params = {}
        self.MOVIES = params.get( "movies", "" )
        self.EPISODES = params.get( "episodes", "" )
        self.ALBUMS = params.get( "albums", "" )
        self.LIMIT = params.get( "limit", "25" )
        self.ALBUMID = params.get( "albumid", "" )

    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( 10000 )
        self.Player = MyPlayer( action = self._update )

    def _fetch_info( self ):
        if self.MOVIES == 'true':
            self._fetch_movies()
        if self.EPISODES == 'true':
            self._fetch_tvshows()
            self._fetch_episodes()
        if self.ALBUMS == 'true':
            self._fetch_songs()
            self._fetch_albums()
        if self.MOVIES == 'true':
            self._clear_movie_properties()
            self._set_movie_properties()
        if self.EPISODES == 'true':
            self._clear_episode_properties()
            self._set_episode_properties()
        if self.ALBUMS == 'true':
            self._clear_album_properties()
            self._set_album_properties()

    def _fetch_movies( self ):
        self.movies = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["resume", "genre", "studio", "tagline", "runtime", "fanart", "thumbnail", "file", "plot", "plotoutline", "year", "lastplayed", "rating"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response['result'].has_key('movies'):
            for item in json_response['result']['movies']:
                if item['resume']['position'] > 0:
                    # this item has a resume point
                    label = item['label']
                    year = str(item['year'])
                    genre = item['genre']
                    studio = item['studio']
                    plot = item['plot']
                    plotoutline = item['plotoutline']
                    tagline = item['tagline']
                    runtime = item['runtime']
                    fanart = item['fanart']
                    thumbnail = item['thumbnail']
                    path = item['file']
                    rating = str(round(float(item['rating']),1))
                    if item.has_key('resume'):
                        # catch exceptions where the lastplayed isn't returned by json-rpc (bug?)
                        lastplayed = item['lastplayed']
                    else:
                        lastplayed = ''
                    if lastplayed == '':
                        # catch exceptions where the item has been partially played, but playdate wasn't stored in the db
                        lastplayed = '0'
                    else:
                        datetime = strptime(lastplayed, "%Y-%m-%d %H:%M:%S")
                        lastplayed = str(mktime(datetime))
                    self.movies.append((lastplayed, label, year, genre, studio, plot, plotoutline, tagline, runtime, fanart, thumbnail, path, rating))
        self.movies.sort(reverse=True)
        log("movie list: %s items" % len(self.movies))

    def _fetch_tvshows( self ):
        self.tvshows = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["studio", "thumbnail"]}, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response['result'].has_key('tvshows'):
            for item in json_response['result']['tvshows']:
                tvshowid = item['tvshowid']
                thumbnail = item['thumbnail']
                studio = item['studio']
                self.tvshows.append((tvshowid, thumbnail, studio))
        log("tv show list: %s items" % len(self.tvshows))

    def _fetch_seasonthumb( self, tvshowid, seasonnumber ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "thumbnail"], "tvshowid":%s }, "id": 1}' % tvshowid)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if json_response['result'].has_key('seasons'):
            for item in json_response['result']['seasons']:
                season = "%.2d" % float(item['season'])
                if season == seasonnumber:
                    thumbnail = item['thumbnail']
                    return thumbnail

    def _fetch_episodes( self ):
        self.episodes = []
        for tvshow in self.tvshows:
            lastplayed = ""
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["playcount", "plot", "season", "episode", "showtitle", "thumbnail", "fanart", "file", "lastplayed", "rating"], "sort": {"method": "episode"}, "tvshowid":%s}, "id": 1}' % tvshow[0])
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            if json_response['result'].has_key('episodes'):
                for item in json_response['result']['episodes']:
                    playcount = item['playcount']
                    if playcount != 0:
                        # this episode has been watched, record play date (we need it for sorting the final list) and continue to next episode
                        lastplayed = item['lastplayed']
                        if lastplayed == '':
                            # catch exceptions where the episode has been played, but playdate wasn't stored in the db
                            lastplayed = '0'
                        else:
                            datetime = strptime(lastplayed, "%Y-%m-%d %H:%M:%S")
                            lastplayed = str(mktime(datetime))
                        continue
                    else:
                        # this is the first unwatched episode, check if the episode is partially watched
                        playdate = item['lastplayed']
                        if (lastplayed == "") and (playdate == ""):
                            # it's a tv show with 0 watched episodes, continue to the next tv show
                            break
                        else:
                            # this is the episode we need
                            label = item['label']
                            fanart = item['fanart']
                            episode = "%.2d" % float(item['episode'])
                            path = item['file']
                            plot = item['plot']
                            season = "%.2d" % float(item['season'])
                            thumbnail = item['thumbnail']
                            showtitle = item['showtitle']
                            rating = str(round(float(item['rating']),1))
                            episodeno = "s%se%s" % ( season,  episode, )
                            if not playdate == '':
                                # if the episode is partially watched, use it's playdate for sorting
                                datetime = strptime(playdate, "%Y-%m-%d %H:%M:%S")
                                lastplayed = str(mktime(datetime))
                                resumable = "True"
                            else:
                                resumable = "False"
                            showthumb = tvshow[1]
                            studio = tvshow[2]
                            seasonthumb = self._fetch_seasonthumb(tvshow[0], season)
                            self.episodes.append((lastplayed, label, episode, season, plot, showtitle, path, thumbnail, fanart, episodeno, studio, showthumb, seasonthumb, resumable, rating))
                            # we have found our episode, collected all data, so continue to next tv show
                            break
        self.episodes.sort(reverse=True)
        log("episode list: %s items" % len(self.episodes))

    def _fetch_songs( self ):
        self.albumsids = {}
        previousid = ''
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["playcount", "albumid"], "sort": { "method": "album" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        if (json_response['result'] != None) and (json_response['result'].has_key('songs')):
            for item in json_response['result']['songs']:
                albumid = item['albumid']
                if albumid != '':
                    # ignore single tracks that do not belong to an album
                    if albumid != previousid:
                        # new album
                        albumplaycount = 0
                        playcount = item['playcount']
                        albumplaycount = albumplaycount + playcount
                        previousid = albumid
                    else:
                        # song from the same album
                        playcount = item['playcount']
                        albumplaycount = albumplaycount + playcount
                    if playcount != 0:
                        # don't add unplayed items
                        self.albumsids.update({albumid: albumplaycount})
        self.albumsids = sorted(self.albumsids.items(), key=itemgetter(1))
        self.albumsids.reverse()
        log("album list: %s items" % len(self.albumsids))

    def _fetch_albums( self ):
        self.albums = []
        for count, albumid in enumerate( self.albumsids ):
            count += 1
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["description", "albumlabel", "artist", "genre", "year", "thumbnail", "fanart", "rating"], "albumid":%s }, "id": 1}' % albumid[0])
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            if json_response['result'].has_key('albumdetails'):
                item = json_response['result']['albumdetails']
                description = item['description']
                album = item['label']
                albumlabel = item['albumlabel']
                artist = item['artist']
                genre = item['genre']
                year = str(item['year'])
                thumbnail = item['thumbnail']
                fanart = item['fanart']
                rating = str(item['rating'])
                if rating == '48':
                    rating = ''
                path = 'XBMC.RunScript(' + __addonid__ + ',albumid=' + str(albumid[0]) + ')'
                self.albums.append((album, artist, genre, year, albumlabel, description, rating, thumbnail, fanart, path))
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _play_album( self, ID ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["file", "fanart"], "albumid":%s }, "id": 1}' % ID)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        # create a playlist
        playlist = xbmc.PlayList(0)
        # clear the playlist
        playlist.clear()
        if json_response['result'].has_key('songs'):
            for item in json_response['result']['songs']:
                song = item['file']
                fanart = item['fanart']
                # create playlist item
                listitem = xbmcgui.ListItem()
                # add fanart image to the playlist item
                listitem.setProperty( "fanart_image", fanart )
                # add item to the playlist
                playlist.add( url=song, listitem=listitem )
            # play the playlist
            xbmc.Player().play( playlist )

    def _daemon( self ):
        # keep running until xbmc exits or another instance is started
        while (not xbmc.abortRequested) and self.WINDOW.getProperty('WatchList_Running') == 'True':
            xbmc.sleep(1000)
        if xbmc.abortRequested:
            log('script stopped: xbmc quit')
        else:
            log('script stopped: new script instance started')

    def _clear_movie_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Movie.%d.Label" % ( count ) )

    def _clear_episode_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Episode.%d.Label" % ( count ) )

    def _clear_album_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Album.%d.Label" % ( count ) )

    def _set_movie_properties( self ):
        for count, movie in enumerate( self.movies ):
            count += 1
            self.WINDOW.setProperty( "WatchList_Movie.%d.Label" % ( count ), movie[1] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Year" % ( count ), movie[2] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Genre" % ( count ), movie[3] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Studio" % ( count ), movie[4] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Plot" % ( count ), movie[5] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.PlotOutline" % ( count ), movie[6] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Tagline" % ( count ), movie[7] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Runtime" % ( count ), movie[8] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Fanart" % ( count ), movie[9] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Thumb" % ( count ), movie[10] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Path" % ( count ), movie[11] )
            self.WINDOW.setProperty( "WatchList_Movie.%d.Rating" % ( count ), movie[12] )
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _set_episode_properties( self ):
        for count, episode in enumerate( self.episodes ):
            count += 1
            self.WINDOW.setProperty( "WatchList_Episode.%d.Label" % ( count ), episode[1] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Episode" % ( count ), episode[2] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Season" % ( count ), episode[3] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Plot" % ( count ), episode[4] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.TVShowTitle" % ( count ), episode[5] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Path" % ( count ), episode[6] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Thumb" % ( count ), episode[7] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Fanart" % ( count ), episode[8] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.EpisodeNo" % ( count ), episode[9] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Studio" % ( count ), episode[10] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.TvshowThumb" % ( count ), episode[11] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.SeasonThumb" % ( count ), episode[12] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.IsResumable" % ( count ), episode[13] )
            self.WINDOW.setProperty( "WatchList_Episode.%d.Rating" % ( count ), episode[14] )
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _set_album_properties( self ):
        for count, album in enumerate( self.albums ):
            count += 1
            self.WINDOW.setProperty( "WatchList_Album.%d.Label" % ( count ), album[0] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Artist" % ( count ), album[1] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Genre" % ( count ), album[2] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Year" % ( count ), album[3] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Album_Label" % ( count ), album[4] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Album_Description" % ( count ), album[5] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Rating" % ( count ), album[6] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Thumb" % ( count ), album[7] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Fanart" % ( count ), album[8] )
            self.WINDOW.setProperty( "WatchList_Album.%d.Path" % ( count ), album[9] )
            if count == int(self.LIMIT):
                # stop here if our list contains more items
                break

    def _update( self ):
        log('playback stopped')
        xbmc.sleep(500)
        self._fetch_info()


class MyPlayer(xbmc.Player):
    def __init__( self, *args, **kwargs ):
        xbmc.Player.__init__( self )
        self.action = kwargs[ "action" ]

    def onPlayBackEnded( self ):
        self.action()

    def onPlayBackStopped( self ):
        self.action()

if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()

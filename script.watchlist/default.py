from time import strptime, mktime
import simplejson
import xbmc, xbmcgui, xbmcaddon
# http://mail.python.org/pipermail/python-list/2009-June/596197.html
import _strptime

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path')

def log(txt):
    message = 'script.watchlist: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    def __init__( self ):
        self._parse_argv()
        self._init_vars()
        if self.MOVIES == 'true':
            self._fetch_movies()
        if self.EPISODES == 'true':
            self._fetch_tvshows()
            self._fetch_episodes()
        if self.MOVIES == 'true':
            self._clear_movie_properties()
            self._set_movie_properties()
        if self.EPISODES == 'true':
            self._clear_episode_properties()
            self._set_episode_properties()

    def _parse_argv( self ):
        try:
            self.params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            self.params = {}
        self.MOVIES = self.params.get( "movies", "" )
        self.EPISODES = self.params.get( "episodes", "" )
        self.LIMIT = self.params.get( "limit", "25" )

    def _init_vars( self ):
        self.WINDOW = xbmcgui.Window( 10000 )

    def _fetch_movies( self ):
        self.movies = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["resume", "genre", "studio", "tagline", "runtime", "fanart", "thumbnail", "file", "plot", "plotoutline", "year", "lastplayed", "rating"]}, "id": 1}')
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
                        # catch exceptions where the lastplayed isn't returned
                        lastplayed = item['lastplayed']
                    else:
                        lastplayed = ''
                    if not lastplayed == "":
                        # catch exceptions where the item has been partially played, but playdate wasn't stored in the db
                        datetime = strptime(lastplayed, "%Y-%m-%d %H:%M:%S")
                        lastplayed = str(mktime(datetime))
                    self.movies.append((lastplayed, label, year, genre, studio, plot, plotoutline, tagline, runtime, fanart, thumbnail, path, rating))
        self.movies.sort(reverse=True)
        log("movie list: %s items" % len(self.movies))

    def _fetch_tvshows( self ):
        self.tvshows = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["studio", "thumbnail"]}, "id": 1}')
        json_response = simplejson.loads(json_query)
        if json_response['result'].has_key('tvshows'):
            for item in json_response['result']['tvshows']:
                tvshowid = item['tvshowid']
                thumbnail = item['thumbnail']
                studio = item['studio']
                self.tvshows.append((tvshowid, thumbnail, studio))
        log("tv show list: %s items" % len(self.tvshows))
        log("tv show list: %s" % self.tvshows)

    def _fetch_seasonthumb( self, tvshowid, seasonnumber ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["season", "thumbnail"], "tvshowid":%s }, "id": 1}' % tvshowid)
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
            json_response = simplejson.loads(json_query)
            if json_response['result'].has_key('episodes'):
                for item in json_response['result']['episodes']:
                    log("### item: %s" % item)
                    playcount = item['playcount']
                    if playcount != 0:
                        log("item has been played")
                        # this item has been watched, record play date (we need it for sorting the final list) and continue to next item
                        lastplayed = item['lastplayed']
                        if not lastplayed == "":
                            log("item has been played, but no playdate was found")
                            # catch exceptions where the item has been played, but playdate wasn't stored in the db
                            datetime = strptime(lastplayed, "%Y-%m-%d %H:%M:%S")
                            lastplayed = str(mktime(datetime))
                        continue
                    else:
                        log("item has not been played")
                        # this is the first unwatched item, check if it's partially watched
                        playdate = item['lastplayed']
                        if (lastplayed == "") and (playdate == ""):
                            log("item has not been played and it's the first episode of a show")
                            # it's a tv show with 0 watched episodes, continue to the next tv show
                            break
                        else:
                            log("item has not been played and we have a previous episode")
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
                            if not playdate == "":
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

    def _clear_movie_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Movie.%d.Label" % ( count ) )

    def _clear_episode_properties( self ):
        for count in range( int(self.LIMIT) ):
            count += 1
            self.WINDOW.clearProperty( "WatchList_Episode.%d.Label" % ( count ) )

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

if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()
log('script stopped')

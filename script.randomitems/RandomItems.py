# *  Thanks to:
# *
# *  Nuka for the original RecentlyAdded.py on which this is based
# *
# *  ppic, Hitcher,ronie & phil65, Martijn for the updates

import xbmc, xbmcgui, xbmcaddon
import re, sys, os, random
from elementtree import ElementTree as xmltree
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')

def log(txt):
    message = '%s: %s' % (__addonid__, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

class Main:
    # grab the home window
    WINDOW = xbmcgui.Window( 10000 )

    def _clear_properties( self ):
        # reset totals property for visible condition
        self.WINDOW.clearProperty( "RandomMovie.Count" )
        self.WINDOW.clearProperty( "RandomEpisode.Count" )
        self.WINDOW.clearProperty( "RandomMusicVideo.Count" )
        self.WINDOW.clearProperty( "RandomSong.Count" )
        self.WINDOW.clearProperty( "RandomAlbum.Count" )
        self.WINDOW.clearProperty( "RandomAddon.Count" )
        # we clear title for visible condition
        for count in range( self.LIMIT ):
            self.WINDOW.clearProperty( "RandomMovie.%d.Title"      % ( count + 1 ) )
            self.WINDOW.clearProperty( "RandomEpisode.%d.Title"    % ( count + 1 ) )
            self.WINDOW.clearProperty( "RandomMusicVideo.%d.Title" % ( count + 1 ) )
            self.WINDOW.clearProperty( "RandomSong.%d.Title"       % ( count + 1 ) )
            self.WINDOW.clearProperty( "RandomAlbum.%d.Title"      % ( count + 1 ) )
            self.WINDOW.clearProperty( "RandomAddon.%d.Name"       % ( count + 1 ) )

    def _parse_argv( self ):
        try:
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            # no params passed
            params = {}
        # set our preferences
        self.LIMIT = int( params.get( "limit", "5" ) )
        self.UNPLAYED = params.get( "unplayed", "False" )
        self.PLAY_TRAILER = params.get( "trailer", "False" )
        self.ALARM = int( params.get( "alarm", "0" ) )
        self.ALBUMID = params.get( "albumid", "" )

    def _set_alarm( self ):
        # only run if user/skinner preference
        if ( not self.ALARM ): return
        # set the alarms command
        command = "XBMC.RunScript(%s,limit=%d&unplayed=%s&trailer=%s&alarm=%d)" % ( __addonid__, self.LIMIT, str( self.UNPLAYED ), str( self.PLAY_TRAILER ), self.ALARM, )
        xbmc.executebuiltin( "AlarmClock(RandomItems,%s,%d,true)" % ( command, self.ALARM, ) )

    def __init__( self ):
        # parse argv for any preferences
        self._parse_argv()
        # check if we were executed internally
        if self.ALBUMID:
            self._Play_Album( self.ALBUMID )
        else:
            # clear properties
            self._clear_properties()
            # set any alarm
            self._set_alarm()
            # fetch media info
            self._fetch_movie_info()
            self._fetch_episode_info()
            self._fetch_musicvideo_info()
            self._fetch_album_info()
            self._fetch_artist_info()
            self._fetch_song_info()
            self._fetch_addon_info()

    def _fetch_movie_info( self ):
        # query the database
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "playcount", "year", "plot", "runtime", "fanart", "thumbnail", "file", "trailer", "rating"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('movies'):
            json_response = json_response['result']['movies']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                if self.UNPLAYED == "True":
                    playcount = item['playcount']
                    if playcount > 0:
                        count = count - 1
                        continue
                title = item['title']
                rating = str(round(float(item['rating']),1))
                year = str(item['year'])
                plot = item['plot']
                runtime = item['runtime']
                path = item['file']
                thumb = item['thumbnail']
                trailer = item['trailer']
                fanart = item['fanart']
                # set our properties
                self.WINDOW.setProperty( "RandomMovie.%d.Title"       % ( count ), title )
                self.WINDOW.setProperty( "RandomMovie.%d.Rating"      % ( count ), rating )
                self.WINDOW.setProperty( "RandomMovie.%d.Year"        % ( count ), year)
                self.WINDOW.setProperty( "RandomMovie.%d.Plot"        % ( count ), plot )
                self.WINDOW.setProperty( "RandomMovie.%d.RunningTime" % ( count ), runtime )
                self.WINDOW.setProperty( "RandomMovie.%d.Path"        % ( count ), path )
                self.WINDOW.setProperty( "RandomMovie.%d.Trailer"     % ( count ), trailer )
                self.WINDOW.setProperty( "RandomMovie.%d.Fanart"      % ( count ), fanart )
                self.WINDOW.setProperty( "RandomMovie.%d.Thumb"       % ( count ), thumb )
                self.WINDOW.setProperty( "RandomMovie.Count"          , total )

    def _fetch_episode_info( self ):
        # query the database
        tvshowid = 2
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('episodes'):
            json_response = json_response['result']['episodes']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                if self.UNPLAYED == "True":
                    playcount = item['playcount']
                    if playcount > 0:
                        count = count - 1
                        continue
                title = item['title']
                showtitle = item['showtitle']
                season = "%.2d" % float(item['season'])
                episode = "%.2d" % float(item['episode'])
                rating = str(round(float(item['rating']),1))
                plot = item['plot']
                path = item['file']
                thumb = item['thumbnail']
                fanart = item['fanart']
                episodeno = "s%se%s" % ( season,  episode, )
                # set our properties
                self.WINDOW.setProperty( "RandomEpisode.%d.ShowTitle"     % ( count ), showtitle )
                self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeTitle"  % ( count ), title )
                self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNo"     % ( count ), episodeno )
                self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeSeason" % ( count ), season )
                self.WINDOW.setProperty( "RandomEpisode.%d.EpisodeNumber" % ( count ), episode )
                self.WINDOW.setProperty( "RandomEpisode.%d.Rating"        % ( count ), rating )
                self.WINDOW.setProperty( "RandomEpisode.%d.Plot"          % ( count ), plot )
                self.WINDOW.setProperty( "RandomEpisode.%d.Path"          % ( count ), path )
                self.WINDOW.setProperty( "RandomEpisode.%d.Fanart"        % ( count ), fanart )
                self.WINDOW.setProperty( "RandomEpisode.%d.Thumb"         % ( count ), thumb )
                self.WINDOW.setProperty( "RandomEpisode.Count"            , total )

    def _fetch_musicvideo_info( self ):
        # query the database
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["title", "artist", "playcount", "year", "plot", "runtime", "fanart", "thumbnail", "file"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('musicvideos'):
            json_response = json_response['result']['musicvideos']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                if self.UNPLAYED == "True":
                    playcount = item['playcount']
                    if playcount > 0:
                        count = count - 1
                        continue
                title = item['title']
                year = str(item['year'])
                plot = item['plot']
                runtime = item['runtime']
                path = item['file']
                artist = item['artist']
                thumb = item['thumbnail']
                fanart = item['fanart']
                # set our properties
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Title"       % ( count ), title )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Year"        % ( count ), year)
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Plot"        % ( count ), plot )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.RunningTime" % ( count ), runtime )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Path"        % ( count ), path )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Fanart"      % ( count ), fanart )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Artist"      % ( count ), artist )
                self.WINDOW.setProperty( "RandomMusicVideo.%d.Thumb"       % ( count ), thumb )
                self.WINDOW.setProperty( "RandomMusicVideo.Count"          , total )

    def _fetch_album_info( self ):
        # query the database
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "description", "artist", "year", "thumbnail", "fanart", "rating"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)

        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('albums'):
            json_response = json_response['result']['albums']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                title = item['title']
                description = item['description']
                rating = str(item['rating'])
                if rating == '48':
                    rating = ""
                year = str(item['year'])
                artist = item['artist']
                path = 'XBMC.RunScript(' + __addonid__ + ',albumid=' + str(item['albumid']) + ')'
                fanart = item['fanart']
                thumb = item['thumbnail']
                # set our properties
                self.WINDOW.setProperty( "RandomAlbum.%d.Title"  % ( count ), title )
                self.WINDOW.setProperty( "RandomAlbum.%d.Rating" % ( count ), rating )
                self.WINDOW.setProperty( "RandomAlbum.%d.Year"   % ( count ), year )
                self.WINDOW.setProperty( "RandomAlbum.%d.Artist" % ( count ), artist )
                self.WINDOW.setProperty( "RandomAlbum.%d.Path"   % ( count ), path )
                self.WINDOW.setProperty( "RandomAlbum.%d.Fanart" % ( count ), fanart )
                self.WINDOW.setProperty( "RandomAlbum.%d.Thumb"  % ( count ), thumb )
                self.WINDOW.setProperty( "RandomAlbum.%d.Album_Description"  % ( count ), description )
                self.WINDOW.setProperty( "RandomAlbum.Count"     , total )

    def _fetch_artist_info( self ):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["genre", "description", "fanart", "thumbnail"], "sort": { "method": "label" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)

        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('artists'):
            json_response = json_response['result']['artists']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                description = item['description']
                genre = str(item['genre'])
                artist = item['label']
                path = 'musicdb://2/' + str(item['artistid']) + '/'
                fanart = item['fanart']
                thumb = item['thumbnail']
                # set our properties
                self.WINDOW.setProperty( "RandomArtist.%d.Title"  % ( count ), artist )
                self.WINDOW.setProperty( "RandomArtist.%d.Genre" % ( count ), genre )
                self.WINDOW.setProperty( "RandomArtist.%d.Path"   % ( count ), path )
                self.WINDOW.setProperty( "RandomArtist.%d.Fanart" % ( count ), fanart )
                self.WINDOW.setProperty( "RandomArtist.%d.Thumb"  % ( count ), thumb )
                self.WINDOW.setProperty( "RandomArtist.%d.Artist_Description"  % ( count ), description )
                self.WINDOW.setProperty( "RandomArtist.Count"     , total )

    def _fetch_song_info( self ):
        # query the database
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "playcount", "artist", "album", "year", "file", "thumbnail", "fanart", "rating"] }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('songs'):
            json_response = json_response['result']['songs']
            # get total value
            total = str( len( json_response ) )
            # enumerate thru our records
            count = 0
            while count < self.LIMIT:
                count += 1
                # check if we don't run out of items before LIMIT is reached
                if len( json_response ) == 0:
                    return
                # select a random item
                item = random.choice( json_response )
                # remove the item from our list
                json_response.remove( item )
                # find values
                if self.UNPLAYED == "True":
                    playcount = item['playcount']
                    if playcount > 0:
                        count = count - 1
                        continue
                title = item['title']
                rating = str(int(item['rating'])-48)
                year = str(item['year'])
                artist = item['artist']
                album = item['album']
                path = item['file']
                fanart = item['fanart']
                thumb = item['thumbnail']
                # set our properties
                self.WINDOW.setProperty( "RandomSong.%d.Title"  % ( count ), title )
                self.WINDOW.setProperty( "RandomSong.%d.Rating" % ( count ), rating )
                self.WINDOW.setProperty( "RandomSong.%d.Year"   % ( count ), year )
                self.WINDOW.setProperty( "RandomSong.%d.Artist" % ( count ), artist )
                self.WINDOW.setProperty( "RandomSong.%d.Album"  % ( count ), album )
                self.WINDOW.setProperty( "RandomSong.%d.Path"   % ( count ), path )
                self.WINDOW.setProperty( "RandomSong.%d.Fanart" % ( count ), fanart )
                self.WINDOW.setProperty( "RandomSong.%d.Thumb"  % ( count ), thumb )
                self.WINDOW.setProperty( "RandomSong.Count"     , total )

    def _fetch_addon_info( self ):
        # initialize our list
        addonlist = []
        # list the contents of the addons folder
        addonpath = xbmc.translatePath( 'special://home/addons/' )
        addons = os.listdir(addonpath)
        # find directories in the addons folder
        for item in addons:
            if os.path.isdir(os.path.join(addonpath, item)):
                # find addon.xml in the addon folder
                addonfile = os.path.join(addonpath, item, 'addon.xml')
                if os.path.exists(addonfile):
                    # find addon id
                    try:
                        addonfilecontents = xmltree.parse(addonfile).getroot()
                    except:
                        # don't error on invalid addon.xml files
                        continue
                    for element in addonfilecontents.getiterator():
                       if element.tag == "addon":
                           addonid = element.attrib.get('id')
                       elif element.tag == "provides":
                           addonprovides = element.text
                    # find plugins and scripts
                    try:
                        addontype = xbmcaddon.Addon(id=addonid).getAddonInfo('type')
                        if (addontype == 'xbmc.python.script') or (addontype == 'xbmc.python.pluginsource'):
                            addonlist.append( (addonid, addonprovides) )
                    except:
                        pass
        # get total value
        total = str( len( addonlist ) )
        # count thru our addons
        count = 0
        while count < self.LIMIT:
            count += 1
            # check if we don't run out of items before LIMIT is reached
            if len(addonlist) == 0:
                return
            # select a random item
            addonid = random.choice(addonlist)
            # remove the item from our list
            addonlist.remove(addonid)
            # set properties
            self.WINDOW.setProperty( "RandomAddon.%d.Name"    % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('name') )
            self.WINDOW.setProperty( "RandomAddon.%d.Author"  % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('author') )
            self.WINDOW.setProperty( "RandomAddon.%d.Summary" % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('summary') )
            self.WINDOW.setProperty( "RandomAddon.%d.Version" % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('version') )
            self.WINDOW.setProperty( "RandomAddon.%d.Path"    % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('id') )
            self.WINDOW.setProperty( "RandomAddon.%d.Fanart"  % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('fanart') )
            self.WINDOW.setProperty( "RandomAddon.%d.Thumb"   % ( count ), xbmcaddon.Addon(id=addonid[0]).getAddonInfo('icon') )
            self.WINDOW.setProperty( "RandomAddon.%d.Type"    % ( count ), addonid[1] )
            self.WINDOW.setProperty( "RandomAddon.Count"      , total )

    def _Play_Album( self, ID ):
        # create a playlist
        playlist = xbmc.PlayList(0)
        # clear the playlist
        playlist.clear()
        # query the database
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["file", "fanart"], "albumid":%s }, "id": 1}' % ID)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        # separate the records
        json_response = simplejson.loads(json_query)
        # enumerate thru our records
        if json_response.has_key('result') and json_response['result'] != None and json_response['result'].has_key('songs'):
            for item in json_response['result']['songs']:
                song = item['file']
                fanart = item['fanart']
                listitem = xbmcgui.ListItem()
                listitem.setProperty( "fanart_image", fanart )
                playlist.add( url=song, listitem=listitem )
        # play the playlist
        xbmc.Player().play( playlist )

if ( __name__ == "__main__" ):
        log('script version %s started' % __addonversion__)
        Main()
log('script stopped')

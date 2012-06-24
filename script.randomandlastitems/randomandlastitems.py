import xbmc, xbmcgui, xbmcaddon
import re, sys, os, random, time
try:
    import json as simplejson
    # test json has not loads, call error
    if not hasattr( simplejson, "loads" ):
        raise Exception( "Hmmm! Error with json %r" % dir( simplejson ) )
except Exception, e:
    print "[RandomAndLastItems] %s" % str( e )
    import simplejson
from xbmcgui import Window
from xml.dom.minidom import parse

# Define global variables
LIMIT = 10
METHOD = "Random"
MENU = ""
PLAYLIST = ""
PROPERTIE = ""
RESUME = 'False'
START_TIME = time.time()
TYPE = ''
UNWATCHED = 'False'
WINDOW = xbmcgui.Window( 10000 )

def _videoResolution( _width, _height ):
    if ( _width == 0 or _height == 0 ):
        return ""
    elif ( _width <= 720 and _height <= 480 ):
        return "480"
    # 720x576 (PAL) (768 when rescaled for square pixels)
    elif ( _width <= 768 and _height <= 576 ):
        return "576"
    # 960x540 (sometimes 544 which is multiple of 16)
    elif ( _width <= 960 and _height <= 544 ):
        return "540"
    # 1280x720
    elif ( _width <= 1280 and _height <= 720 ):
        return "720"
    # 1920x1080
    else:
        return "1080"

def _getPlaylistType ():
    global PLAYLIST
    global TYPE
    _doc = parse(xbmc.translatePath(PLAYLIST))
    _type = _doc.getElementsByTagName('smartplaylist')[0].attributes.item(0).value
    if _type == 'movies':
       TYPE = 'Movie'
    if _type == 'episodes' or _type == 'tvshows':
       TYPE = 'Episode'
    if _type == 'songs' or _type == 'albums':
       TYPE = 'Music'

def _timeTook( t ):
    t = ( time.time() - t )
    if t >= 60: return "%.3fm" % ( t / 60.0 )
    return "%.3fs" % ( t )

def _multiKeySort(_items, _columns):
    from operator import itemgetter
    _comparers = [ ((itemgetter(_col[1:].strip()), -1) if _col.startswith('-') else (itemgetter(_col.strip()), 1)) for _col in _columns]  
    def _comparer(_left, _right):
        for _fn, _mult in _comparers:
            _result = cmp(_fn(_left), _fn(_right))
            if _result:
                return _mult * _result
        else:
            return 0
    return sorted(_items, cmp=_comparer)

def _watchedOrResume ( _total, _watched, _unwatched, _result, _file ):
    global RESUME
    global UNWATCHED
    _total += 1
    _playcount = _file['playcount']
    if RESUME == 'True':
        _resume = _file['resume']['position']
    if _playcount == 0:
        _unwatched += 1
    else:
        _watched += 1
    if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0):
        _result.append(_file)
    return _total, _watched, _unwatched, _result

def _getMovies ( ):
    global LIMIT
    global METHOD
    global MENU
    global PLAYLIST
    global PROPERTIE
    global RESUME
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    # Request database using JSON
    if PLAYLIST == "":
        PLAYLIST = "videodb://1/2/"
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["year", "runtime", "file", "playcount", "rating", "plot", "fanart", "thumbnail", "trailer", "streamdetails"]}, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = simplejson.loads(_json_query)
    # If request return some results
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _item in _files:
            if _item['filetype'] == 'directory':
                _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["year", "runtime", "file", "playcount", "rating", "plot", "fanart", "thumbnail", "trailer", "streamdetails"]}, "id": 1}' %(_item['file']))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_set_response = simplejson.loads(_json_query)
                _movies = _json_set_response.get( "result", {} ).get( "files" ) or []
                if not _movies:
                    print("[RandomAndLastItems] ## MOVIESET %s COULD NOT BE LOADED ##" %(_item['file']))
                    print("[RandomAndLastItems] JSON RESULT ", _json_set_response)
                for _movie in _movies:
                    _playcount = _movie['playcount']
                    if RESUME == 'True':
                        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": %s, "properties": ["resume"]}, "id": 1}' %(_movie['id']))
                        _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                        _json_detail_response = simplejson.loads(_json_query)
                        _detail = _json_detail_response.get( "result", {} ).get( "moviedetails" ) or []
                        _resume = _detail['resume']['position']
                    else:
                        _resume = 0
                    _total += 1
                    if _playcount == 0:
                        _unwatched += 1
                    else:
                        _watched += 1
                    if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0):
                        _result.append(_movie)
            else:
                _playcount = _item['playcount']
                if RESUME == 'True':
                    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": %s, "properties": ["resume"]}, "id": 1}' %(_item['id']))
                    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                    _json_detail_response = simplejson.loads(_json_query)
                    _detail = _json_detail_response.get( "result", {} ).get( "moviedetails" ) or []
                    _resume = _detail['resume']['position']
                else:
                    _resume = 0
                _total += 1
                if _playcount == 0:
                    _unwatched += 1
                else:
                    _watched += 1
                if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0):
                    _result.append(_item)
        if METHOD == 'Last':
            _result = _multiKeySort(_result, ['-id'])
        _setVideoProperties ( _total, _watched, _unwatched )
        _count = 0
        while _count < LIMIT:
            # Check if we don't run out of items before LIMIT is reached
            if len( _result ) == 0:
                break
            # Select a random or the last item
            if METHOD == 'Random':
                _movie = random.choice( _result )
            else:
                _movie = _result[0]
            # Remove item from JSON list
            _result.remove( _movie )
            _count += 1
            title = _movie['label']
            rating = str(round(float(_movie['rating']),1))
            year = str(_movie['year'])
            trailer = _movie['trailer']
            plot = _movie['plot']
            runtime = _movie['runtime']
            path = _movie['file']
            file = os.path.split(path)[1]
            pos = path.find(file)
            rootpath = path[:pos]
            thumb = _movie['thumbnail']
            fanart = _movie['fanart']
            try: height = _movie.get("streamdetails", [ {} ]).get( "video", [ {} ] )[0].get( "height",0 )
            except: height = 0
            try: width = _movie.get("streamdetails", [ {} ]).get( "video", [ {} ] )[0].get( "width",0 )
            except: width = 0
            resolution = _videoResolution( width, height )
            # Set window properties
            _setProperty( "%s.%d.Path"        % ( PROPERTIE, _count ), path )
            _setProperty( "%s.%d.Thumb"       % ( PROPERTIE, _count ), thumb)
            _setProperty( "%s.%d.Fanart"      % ( PROPERTIE, _count ), fanart)
            _setProperty( "%s.%d.Plot"        % ( PROPERTIE, _count ), plot)
            _setProperty( "%s.%d.Rating"      % ( PROPERTIE, _count ), rating)
            _setProperty( "%s.%d.RunningTime" % ( PROPERTIE, _count ), runtime)
            _setProperty( "%s.%d.Rootpath"    % ( PROPERTIE, _count ), rootpath )
            _setProperty( "%s.%d.Title"       % ( PROPERTIE, _count ), title )
            _setProperty( "%s.%d.Year"        % ( PROPERTIE, _count ), year)
            _setProperty( "%s.%d.Trailer"     % ( PROPERTIE, _count ), trailer)
            _setProperty( "%s.%d.Resolution"  % ( PROPERTIE, _count ), resolution)
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setProperty( "%s.%d.Path"        % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Thumb"       % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Fanart"      % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Plot"        % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Rating"      % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.RunningTime" % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Rootpath"    % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Title"       % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Year"        % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Trailer"     % ( PROPERTIE, _count ), "" )
                _setProperty( "%s.%d.Resolution"  % ( PROPERTIE, _count ), "" )
    else:
        print("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        print("[RandomAndLastItems] JSON RESULT ", _json_pl_response)

def _getEpisodesFromPlaylist ( ):
    global LIMIT
    global METHOD
    global PLAYLIST
    global RESUME
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    _tvshows = 0
    _tvshowid = []
    # Request database using JSON
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["tvshowid", "runtime", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating", "title"] }, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = simplejson.loads(_json_query)
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _file in _files:
            if _file['type'] == 'tvshow':
                _tvshows += 1
                # La playlist fournie retourne des series il faut retrouver les episodes
                if RESUME == 'True':
                    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %s, "properties": ["resume", "runtime", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating", "title"] }, "id": 1}' %(_file['id']))
                else:
                    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %s, "properties": ["runtime", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating", "title"] }, "id": 1}' %(_file['id']))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_response = simplejson.loads(_json_query)
                _episodes = _json_response.get( "result", {} ).get( "episodes" )
                if _episodes:
                    for _episode in _episodes:
                        _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _episode )
                else:
                    print("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
                    print("[RandomAndLastItems] JSON RESULT ", _json_response)
            if _file['type'] == 'episode':
                _id = _file['tvshowid']
                if _id not in _tvshowid:
                    _tvshows += 1
                    _tvshowid.append(_id)
                # La playlist fournie retourne des episodes
                _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _file )
        if METHOD == 'Last':
            if _tvshowid:
                _result = _multiKeySort(_result, ['-id'])
            else:
                _result = _multiKeySort(_result, ['-episodeid'])
        _setVideoProperties ( _total, _watched, _unwatched )
        _setTvShowsProperties ( _tvshows )
        _count = 0
        while _count < LIMIT:
            # Check if we don't run out of items before LIMIT is reached
            if len( _result ) == 0:
                break
            # Select a random or the last item
            if METHOD == 'Random':
                _episode = random.choice( _result )
            else:
                _episode = _result[0]
            # Remove item from JSON list
            _result.remove( _episode )
            _count += 1
            _setEpisodeProperties ( _episode, _count )
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setEpisodeProperties ( None, _count )
    else:
        print("[RandomAndLastItems] # 01 # PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        print("[RandomAndLastItems] JSON RESULT ", _json_pl_response)

def _getEpisodes ( ):
    global LIMIT
    global METHOD
    global RESUME
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    _tvshows = 0
    _tvshowid = []
    # Request database using JSON
    if RESUME == 'True':
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["tvshowid", "resume", "runtime", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating", "title"] }, "id": 1}')
    else:
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["tvshowid", "runtime", "playcount", "season", "episode", "showtitle", "plot", "fanart", "thumbnail", "file", "rating", "title"] }, "id": 1}')
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = simplejson.loads(_json_query)
    # If request return some results
    _episodes = _json_pl_response.get( "result", {} ).get( "episodes" )
    if _episodes:
        for _item in _episodes:
            _id = _item['tvshowid']
            if _id not in _tvshowid:
                _tvshows += 1
                _tvshowid.append(_id)
            _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _item )
        if METHOD == 'Last':
            _result = _multiKeySort(_result, ['-episodeid'])
        _setVideoProperties ( _total, _watched, _unwatched )
        _setTvShowsProperties ( _tvshows )
        _count = 0
        while _count < LIMIT:
            # Check if we don't run out of items before LIMIT is reached
            if len( _result ) == 0:
                break
            # Select a random or the last item
            if METHOD == 'Random':
                _episode = random.choice( _result )
            else:
                _episode = _result[0]
            # Remove item from JSON list
            _result.remove( _episode )
            _count += 1
            _setEpisodeProperties ( _episode, _count )
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setEpisodeProperties ( None, _count )
    else:
        print("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        print("[RandomAndLastItems] JSON RESULT ", _json_pl_response)

def _getAlbumsFromPlaylist ( ):
    global LIMIT
    global METHOD
    global PLAYLIST
    _result = []
    _artists = 0
    _artistsid = []
    _albums = []
    _albumsid = []
    _songs = 0
    # Request database using JSON
    if PLAYLIST == "":
        PLAYLIST = "musicdb://4/"
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["title", "album", "albumid", "artist", "artistid", "file", "year", "thumbnail", "fanart"]}, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = simplejson.loads(_json_query)
    # If request return some results
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _file in _files:
            if _file['type'] == 'album':
                _albumid = _file['id']
                # Album playlist so get path from songs
                _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"albumid": %s, "properties": ["file"]}, "id": 1}' %(_albumid))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_pl_response = simplejson.loads(_json_query)
                _result = _json_pl_response.get( "result", {} ).get( "songs" )
                _songs += len(_result)
                if _result:
                    _albumpath = os.path.split(_result[0]['file'])[0]
                    _artistpath = os.path.split(_albumpath)[0]
            else:
                _albumid = _file['albumid']
                _albumpath = os.path.split(_file['file'])[0]
                _artistpath = os.path.split(_albumpath)[0]
                _songs += 1
            if _albumid not in _albumsid:
                _structure = {}
                _structure["id"] = _albumid
                _structure["album"] = _file['album']
                _structure["artist"] = _file['artist']
                _structure["year"] = _file['year']
                _structure["thumbnail"] = _file['thumbnail']
                _structure["fanart"] = _file['fanart']
                _structure["albumPath"] = _albumpath
                _structure["artistPath"] = _artistpath
                _albums.append(_structure)
                _albumsid.append(_albumid)
            _artistid = _file['artistid']
            if _artistid not in _artistsid:
                _artists += 1
                _artistsid.append(_artistid)
        if METHOD == 'Last':
            _albums = _multiKeySort(_albums, ['-id'])
        _setMusicProperties ( _artists, len(_albums), _songs )
        _count = 0
        while _count < LIMIT:
            # Check if we don't run out of items before LIMIT is reached
            if len( _albums ) == 0:
                break
            # Select a random or the last item
            if METHOD == 'Random':
                _album = random.choice( _albums )
            else:
                _album = _albums[0]
            # Remove item from JSON list
            _albums.remove( _album )
            _count += 1
            # Get album description
            _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params": {"albumid": %s, "properties": ["description"]}, "id": 1}' %(_albumid))
            _json_query = unicode(_json_query, 'utf-8', errors='ignore')
            _json_pl_response = simplejson.loads(_json_query)
            _result = _json_pl_response.get( "result", {} ).get( "albumdetails" )
            _albumdesc = _result.get ("description")
            _album["albumDesc"] = _albumdesc
            _setAlbumProperties ( _album, _count )
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setAlbumProperties ( None, _count )
    else:
        print("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        print("[RandomAndLastItems] JSON RESULT ", _json_pl_response)

def _clearProperties ( ):
    global LIMIT
    global METHOD
    global MENU
    global TYPE
    global WINDOW
    # Reset window properties
    if TYPE == "Movie" or TYPE == "Episode":
        WINDOW.clearProperty( "%s.Count" % ( PROPERTIE ) )
        WINDOW.clearProperty( "%s.Watched" % ( PROPERTIE ) )
        WINDOW.clearProperty( "%s.Unwatched" % ( PROPERTIE ) )
    if TYPE == "Album" or TYPE == "Song":
        WINDOW.clearProperty( "%s.Artists" % ( PROPERTIE ) )
        WINDOW.clearProperty( "%s.Albums" % ( PROPERTIE ) )
        WINDOW.clearProperty( "%s.Songs" % ( PROPERTIE ) )
    for _count in range( LIMIT ):
        WINDOW.clearProperty( "%s.%d.Path" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.Rootpath" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.Thumb" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.Fanart" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.Plot" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.Rating" % ( PROPERTIE, _count + 1 ) )
        WINDOW.clearProperty( "%s.%d.RunningTime" % ( PROPERTIE, _count + 1 ) )
        if TYPE == "Movie":
            WINDOW.clearProperty( "%s.%d.Title" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.Year" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.Trailer" % ( PROPERTIE, _count + 1 ) )
        if TYPE == "Episode":
            WINDOW.clearProperty( "%s.%d.ShowTitle" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.EpisodeTitle" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.EpisodeNo" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.EpisodeSeason" % ( PROPERTIE, _count + 1 ) )
            WINDOW.clearProperty( "%s.%d.EpisodeNumber" % ( PROPERTIE, _count + 1 ) )

def _setMusicProperties ( _artists, _albums, _songs ):
    global PROPERTIE
    global WINDOW
    global TYPE
    # Set window properties
    _setProperty ( "%s.Artists" % ( PROPERTIE ), str( _artists ) )
    _setProperty ( "%s.Albums" % ( PROPERTIE ), str( _albums ) )
    _setProperty ( "%s.Songs" % ( PROPERTIE ), str( _songs ) )
    _setProperty ( "%s.Type" % ( PROPERTIE ), TYPE )

def _setVideoProperties ( _total, _watched, _unwatched ):
    global PROPERTIE
    global WINDOW
    global TYPE
    # Set window properties
    _setProperty ( "%s.Count" % ( PROPERTIE ), str( _total ) )
    _setProperty ( "%s.Watched" % ( PROPERTIE ), str( _watched ) )
    _setProperty ( "%s.Unwatched" % ( PROPERTIE ), str( _unwatched ) )
    _setProperty ( "%s.Type" % ( PROPERTIE ), TYPE )

def _setTvShowsProperties ( _tvshows ):
    global PROPERTIE
    global WINDOW
    # Set window properties
    _setProperty ( "%s.TvShows" % ( PROPERTIE ), str( _tvshows ) )

def _setEpisodeProperties ( _episode, _count ):
    global PROPERTIE
    if _episode:
        title = _episode['title']
        rating = str(round(float(_episode['rating']),1))
        plot = _episode['plot']
        runtime = _episode['runtime']
        path = _episode['file']
        file = os.path.split(path)[1]
        pos = path.find(file)
        rootpath = path[:pos]
        long=len(rootpath)
        rootpath=rootpath[:long-1]
        file = os.path.split(rootpath)[1]
        pos = rootpath.find(file)
        rootpath = rootpath[:pos]
        showtitle = _episode['showtitle']
        season = str(_episode['season'])
        seasonXX = "%.2d" % float(_episode['season'])
        episode = "%.2d" % float(_episode['episode'])
        episodeno = "s%se%s" % ( seasonXX,  episode, )
        thumb = _episode['thumbnail']
        fanart = _episode['fanart']
    else:
        title = ""
        rating = ""
        plot = ""
        runtime = ""
        path = ""
        rootpath = ""
        showtitle = ""
        season = ""
        episode = ""
        episodeno = ""
        thumb = ""
        fanart = ""
    # Set window properties
    _setProperty( "%s.%d.Path"          % ( PROPERTIE, _count ), path )
    _setProperty( "%s.%d.Thumb"         % ( PROPERTIE, _count ), thumb)
    _setProperty( "%s.%d.Fanart"        % ( PROPERTIE, _count ), fanart)
    _setProperty( "%s.%d.Plot"          % ( PROPERTIE, _count ), plot)
    _setProperty( "%s.%d.Rating"        % ( PROPERTIE, _count ), rating)
    _setProperty( "%s.%d.RunningTime"   % ( PROPERTIE, _count ), runtime)
    _setProperty( "%s.%d.Rootpath"      % ( PROPERTIE, _count ), rootpath )
    _setProperty( "%s.%d.ShowTitle"     % ( PROPERTIE, _count ), showtitle )
    _setProperty( "%s.%d.EpisodeTitle"  % ( PROPERTIE, _count ), title )
    _setProperty( "%s.%d.EpisodeNo"     % ( PROPERTIE, _count ), episodeno )
    _setProperty( "%s.%d.EpisodeSeason" % ( PROPERTIE, _count ), season )
    _setProperty( "%s.%d.EpisodeNumber" % ( PROPERTIE, _count ), episode )

def _setAlbumProperties ( _album, _count ):
    global PROPERTIE
    if _album:
        album = _album['album']
        artist = _album['artist']
        year = _album['year']
        thumb = _album['thumbnail']
        fanart = _album['fanart']
        artistPath = _album['artistPath']
        albumPath = _album['albumPath']
        albumDesc = _album['albumDesc']
        playPath = "musicdb://3/%s/" %(_album['id'])
    else:
        album = ""
        artist = ""
        year = ""
        thumb = ""
        fanart = ""
        artistPath = ""
        albumPath = ""
        albumDesc = ""
        playPath = ""
    # Set window properties
    _setProperty( "%s.%d.Album"      % ( PROPERTIE, _count ), album )
    _setProperty( "%s.%d.Artist"     % ( PROPERTIE, _count ), artist )
    _setProperty( "%s.%d.Year"       % ( PROPERTIE, _count ), str(year) )
    _setProperty( "%s.%d.Thumb"      % ( PROPERTIE, _count ), thumb)
    _setProperty( "%s.%d.Fanart"     % ( PROPERTIE, _count ), fanart)
    _setProperty( "%s.%d.ArtistPath" % ( PROPERTIE, _count ), artistPath)
    _setProperty( "%s.%d.AlbumPath"  % ( PROPERTIE, _count ), albumPath)
    _setProperty( "%s.%d.AlbumDesc"  % ( PROPERTIE, _count ), albumDesc)
    _setProperty( "%s.%d.PlayPath"   % ( PROPERTIE, _count ), playPath)

def _setProperty ( _property, _value ):
    global WINDOW
    # Set window properties
    WINDOW.setProperty ( _property, _value )

def _parse_argv ( ):
    global METHOD
    global MENU
    global LIMIT
    global PLAYLIST
    global PROPERTIE
    global RESUME
    global TYPE
    global UNWATCHED
    # Extract parameters
    for arg in sys.argv:
        param = str(arg)
        if 'limit=' in param:
            LIMIT = int(param.replace('limit=', ''))
        elif 'menu=' in param:
            MENU = param.replace('menu=', '')
        elif 'method=' in param:
            METHOD = param.replace('method=', '')
        elif 'playlist=' in param:
            PLAYLIST = param.replace('playlist=', '')
        elif 'propertie=' in param:
            PROPERTIE = param.replace('propertie=', '')
        elif 'type=' in param:
            TYPE = param.replace('type=', '')
        elif 'unwatched=' in param:
            UNWATCHED = param.replace('unwatched=', '')
        elif 'resume=' in param:
            RESUME = param.replace('resume=', '')
    # If playlist= parameter is set and not type= get type= from playlist
    if TYPE == '' and PLAYLIST != '':
        _getPlaylistType ();
    if PROPERTIE == "":
        PROPERTIE = "Playlist%s%s%s" % ( METHOD, TYPE, MENU )


# Parse argv for any preferences
_parse_argv()
# Clear properties
#_clearProperties()
# Get movies and fill properties
if TYPE == 'Movie':
    _getMovies()
elif TYPE == 'Episode':
    if PLAYLIST == '':
        _getEpisodes()
    else:
        _getEpisodesFromPlaylist()
elif TYPE == 'Music':
    _getAlbumsFromPlaylist()
print( "Loading Playlist%sMovie%s started at %s and take %s" %( METHOD, MENU, time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( START_TIME ) ), _timeTook( START_TIME ) ) )


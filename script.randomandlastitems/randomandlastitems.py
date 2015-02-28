import xbmc, xbmcgui, xbmcaddon
import re, sys, os, time
import random
import urllib
from operator import itemgetter
if sys.version_info >=  (2, 7):
    import json
else:
    import simplejson as json
from xbmcgui import Window
from xml.dom.minidom import parse

# Define global variables
LIMIT = 20
METHOD = "Random"
REVERSE = False
MENU = ""
PLAYLIST = ""
PROPERTY = ""
RESUME = 'False'
SORTBY = ""
START_TIME = time.time()
TYPE = ''
UNWATCHED = 'False'
WINDOW = xbmcgui.Window( 10000 )

__addon__        = xbmcaddon.Addon()
__addonversion__ = __addon__.getAddonInfo('version')
__addonid__      = __addon__.getAddonInfo('id')
__addonname__    = __addon__.getAddonInfo('name')

def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)

def _getPlaylistType ():
    global METHOD
    global PLAYLIST
    global REVERSE
    global SORTBY
    global TYPE
    _doc = parse(xbmc.translatePath(PLAYLIST))
    _type = _doc.getElementsByTagName('smartplaylist')[0].attributes.item(0).value
    if _type == 'movies':
       TYPE = 'Movie'
    if _type == 'musicvideos':
       TYPE = 'MusicVideo'
    if _type == 'episodes' or _type == 'tvshows':
       TYPE = 'Episode'
    if _type == 'songs' or _type == 'albums':
       TYPE = 'Music'
    # get playlist name
    _name = ""
    if _doc.getElementsByTagName('name'):
        try:
            _name = _doc.getElementsByTagName('name')[0].firstChild.nodeValue.encode('utf-8')
        except:
            _name = ""
    _setProperty( "%s.Name" % PROPERTY, str( _name ) )
    # get playlist order
    if METHOD == 'Playlist':
        if _doc.getElementsByTagName('order'):
            SORTBY = _doc.getElementsByTagName('order')[0].firstChild.nodeValue
            if _doc.getElementsByTagName('order')[0].attributes.item(0).value == "descending":
                REVERSE = True
        else:
            METHOD = ""

def _timeTook( t ):
    t = ( time.time() - t )
    if t >= 60: return "%.3fm" % ( t / 60.0 )
    return "%.3fs" % ( t )

def _watchedOrResume ( _total, _watched, _unwatched, _result, _file ):
    global RESUME
    global UNWATCHED
    _total += 1
    _playcount = _file['playcount']
    _resume = _file['resume']['position']
    # Add Watched flag and counter for episodes
    if _playcount == 0:
        _file['watched']='False'
        _unwatched += 1
    else:
        _file['watched']='True'
        _watched += 1
    if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0) and _file.get('dateadded'):
        _result.append(_file)
    return _total, _watched, _unwatched, _result

def _getMovies ( ):
    global LIMIT
    global METHOD
    global MENU
    global PLAYLIST
    global PROPERTY
    global RESUME
    global REVERSE
    global SORTBY
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    # Request database using JSON
    if PLAYLIST == "":
        PLAYLIST = "videodb://movies/titles/"
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["title", "originaltitle", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "dateadded"]}, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = json.loads(_json_query)
    # If request return some results
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _item in _files:
            if xbmc.abortRequested:
                break
            if _item['filetype'] == 'directory':
                _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["title", "originaltitle", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "dateadded"]}, "id": 1}' %(_item['file']))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_set_response = json.loads(_json_query)
                _movies = _json_set_response.get( "result", {} ).get( "files" ) or []
                if not _movies:
                    log("[RandomAndLastItems] ## MOVIESET %s COULD NOT BE LOADED ##" %(_item['file']))
                    log("[RandomAndLastItems] JSON RESULT %s" %_json_set_response)
                for _movie in _movies:
                    if xbmc.abortRequested:
                        break
                    _playcount = _movie['playcount']
                    if RESUME == 'True':
                        _resume = _movie['resume']['position']
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
                    _resume = _item['resume']['position']
                else:
                    _resume = 0
                _total += 1
                if _playcount == 0:
                    _unwatched += 1
                else:
                    _watched += 1
                if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0):
                    _result.append(_item)
        _setVideoProperties ( _total, _watched, _unwatched )
        _count = 0
        if METHOD == 'Last':
            _result = sorted(_result, key=itemgetter('dateadded'), reverse=True)
        elif METHOD == 'Playlist':
            _result = sorted(_result, key=itemgetter(SORTBY), reverse=REVERSE)
        else:
            random.shuffle(_result, random.random)
        for _movie in _result:
            if xbmc.abortRequested or _count == LIMIT:
                break
            _count += 1
            _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails"], "movieid":%s }, "id": 1}' %(_movie['id']))
            _json_query = unicode(_json_query, 'utf-8', errors='ignore')
            _json_query = json.loads(_json_query)
            if _json_query.has_key('result') and _json_query['result'].has_key('moviedetails'):
                item = _json_query['result']['moviedetails']
                _movie['streamdetails'] = item['streamdetails']
            if _movie['resume']['position'] > 0:
                resume = "true"
                played = '%s%%'%int((float(_movie['resume']['position']) / float(_movie['resume']['total'])) * 100)
            else:
                resume = "false"
                played = '0%'
            if _movie['playcount'] >= 1:
                watched = "true"
            else:
                watched = "false"
            path = media_path(_movie['file'])
            play = 'XBMC.RunScript(' + __addonid__ + ',movieid=' + str(_movie.get('id')) + ')'
            art = _movie['art']
            streaminfo = media_streamdetails(_movie['file'].encode('utf-8').lower(),
                                       _movie['streamdetails'])
            # Get runtime from streamdetails or from NFO
            if streaminfo['duration'] != 0:
                runtime = str(int((streaminfo['duration'] / 60) + 0.5))
            else:
                if isinstance(_movie['runtime'],int):
                    runtime = str(int((_movie['runtime'] / 60) + 0.5))
                else:
                    runtime = _movie['runtime']
            # Set window properties
            _setProperty( "%s.%d.DBID"            % ( PROPERTY, _count ), str(_movie.get('id','')))
            _setProperty( "%s.%d.Title"           % ( PROPERTY, _count ), _movie.get('title',''))
            _setProperty( "%s.%d.OriginalTitle"   % ( PROPERTY, _count ), _movie.get('originaltitle',''))
            _setProperty( "%s.%d.Year"            % ( PROPERTY, _count ), str(_movie.get('year','')))
            _setProperty( "%s.%d.Genre"           % ( PROPERTY, _count ), " / ".join(_movie.get('genre','')))
            _setProperty( "%s.%d.Studio"          % ( PROPERTY, _count ), " / ".join(_movie.get('studio','')))
            _setProperty( "%s.%d.Country"         % ( PROPERTY, _count ), " / ".join(_movie.get('country','')))
            _setProperty( "%s.%d.Plot"            % ( PROPERTY, _count ), _movie.get('plot',''))
            _setProperty( "%s.%d.PlotOutline"     % ( PROPERTY, _count ), _movie.get('plotoutline',''))
            _setProperty( "%s.%d.Tagline"         % ( PROPERTY, _count ), _movie.get('tagline',''))
            _setProperty( "%s.%d.Runtime"         % ( PROPERTY, _count ), runtime)
            _setProperty( "%s.%d.Rating"          % ( PROPERTY, _count ), str(round(float(_movie.get('rating','0')),1)))
            _setProperty( "%s.%d.Trailer"         % ( PROPERTY, _count ), _movie.get('trailer',''))
            _setProperty( "%s.%d.MPAA"            % ( PROPERTY, _count ), _movie.get('mpaa',''))
            _setProperty( "%s.%d.Director"        % ( PROPERTY, _count ), " / ".join(_movie.get('director','')))
            _setProperty( "%s.%d.Art(thumb)"      % ( PROPERTY, _count ), art.get('poster',''))
            _setProperty( "%s.%d.Art(poster)"     % ( PROPERTY, _count ), art.get('poster',''))
            _setProperty( "%s.%d.Art(fanart)"     % ( PROPERTY, _count ), art.get('fanart',''))
            _setProperty( "%s.%d.Art(clearlogo)"  % ( PROPERTY, _count ), art.get('clearlogo',''))
            _setProperty( "%s.%d.Art(clearart)"   % ( PROPERTY, _count ), art.get('clearart',''))
            _setProperty( "%s.%d.Art(landscape)"  % ( PROPERTY, _count ), art.get('landscape',''))
            _setProperty( "%s.%d.Art(banner)"     % ( PROPERTY, _count ), art.get('banner',''))
            _setProperty( "%s.%d.Art(discart)"    % ( PROPERTY, _count ), art.get('discart',''))                
            _setProperty( "%s.%d.Resume"          % ( PROPERTY, _count ), resume)
            _setProperty( "%s.%d.PercentPlayed"   % ( PROPERTY, _count ), played)
            _setProperty( "%s.%d.Watched"         % ( PROPERTY, _count ), watched)
            _setProperty( "%s.%d.File"            % ( PROPERTY, _count ), _movie.get('file',''))
            _setProperty( "%s.%d.Path"            % ( PROPERTY, _count ), path)
            _setProperty( "%s.%d.Play"            % ( PROPERTY, _count ), play)
            _setProperty( "%s.%d.VideoCodec"      % ( PROPERTY, _count ), streaminfo['videocodec'])
            _setProperty( "%s.%d.VideoResolution" % ( PROPERTY, _count ), streaminfo['videoresolution'])
            _setProperty( "%s.%d.VideoAspect"     % ( PROPERTY, _count ), streaminfo['videoaspect'])
            _setProperty( "%s.%d.AudioCodec"      % ( PROPERTY, _count ), streaminfo['audiocodec'])
            _setProperty( "%s.%d.AudioChannels"   % ( PROPERTY, _count ), str(streaminfo['audiochannels']))
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setProperty( "%s.%d.Title"       % ( PROPERTY, _count ), "" )
    else:
        log("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        log("[RandomAndLastItems] JSON RESULT %s" %_json_pl_response)

def _getMusicVideosFromPlaylist ( ):
    global LIMIT
    global METHOD
    global MENU
    global PLAYLIST
    global PROPERTY
    global RESUME
    global REVERSE
    global SORTBY
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    # Request database using JSON
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["title", "playcount", "year", "genre", "studio", "album", "artist", "track", "plot", "tag", "runtime", "file", "lastplayed", "resume", "art", "streamdetails", "director", "dateadded"]}, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = json.loads(_json_query)
    # If request return some results
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _item in _files:
            if xbmc.abortRequested:
                break
            _playcount = _item['playcount']
            if RESUME == 'True':
                _resume = _item['resume']['position']
            else:
                _resume = 0
            _total += 1
            if _playcount == 0:
                _unwatched += 1
            else:
                _watched += 1
            if (UNWATCHED == 'False' and RESUME == 'False') or (UNWATCHED == 'True' and _playcount == 0) or (RESUME == 'True' and _resume != 0):
                _result.append(_item)
        _setVideoProperties ( _total, _watched, _unwatched )
        _count = 0
        if METHOD == 'Last':
            _result = sorted(_result, key=itemgetter('dateadded'), reverse=True)
        elif METHOD == 'Playlist':
            _result = sorted(_result, key=itemgetter(SORTBY), reverse=REVERSE)
        else:
            random.shuffle(_result, random.random)
        for _musicvid in _result:
            if xbmc.abortRequested or _count == LIMIT:
                break
            _count += 1
            _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideoDetails", "params": {"properties": ["streamdetails"], "musicvideoid":%s }, "id": 1}' %(_musicvid['id']))
            _json_query = unicode(_json_query, 'utf-8', errors='ignore')
            _json_query = json.loads(_json_query)
            if _json_query['result'].has_key('musicvideodetails'):
                item = _json_query['result']['musicvideodetails']
                _musicvid['streamdetails'] = item['streamdetails']
            if _musicvid['resume']['position'] > 0:
                resume = "true"
                played = '%s%%'%int((float(_musicvid['resume']['position']) / float(_musicvid['resume']['total'])) * 100)
            else:
                resume = "false"
                played = '0%'
            if _musicvid['playcount'] >= 1:
                watched = "true"
            else:
                watched = "false"
            path = media_path(_musicvid['file'])
            play = 'XBMC.RunScript(' + __addonid__ + ',musicvideoid=' + str(_musicvid.get('id')) + ')'
            art = _musicvid['art']
            streaminfo = media_streamdetails(_musicvid['file'].encode('utf-8').lower(),
                                             _musicvid['streamdetails'])
            # Get runtime from streamdetails or from NFO
            if streaminfo['duration'] != 0:
                runtime = str(int((streaminfo['duration'] / 60) + 0.5))
            else:
                if isinstance(_musicvid['runtime'],int):
                    runtime = str(int((_musicvid['runtime'] / 60) + 0.5))
                else:
                    runtime = _musicvid['runtime']
            # Set window properties
            _setProperty( "%s.%d.DBID"            % ( PROPERTY, _count ), str(_musicvid.get('id')))
            _setProperty( "%s.%d.Title"           % ( PROPERTY, _count ), _musicvid.get('title',''))
            _setProperty( "%s.%d.Year"            % ( PROPERTY, _count ), str(_musicvid.get('year','')))
            _setProperty( "%s.%d.Genre"           % ( PROPERTY, _count ), " / ".join(_musicvid.get('genre','')))
            _setProperty( "%s.%d.Studio"          % ( PROPERTY, _count ), " / ".join(_musicvid.get('studio','')))
            _setProperty( "%s.%d.Artist"          % ( PROPERTY, _count ), " / ".join(_musicvid.get('artist','')))
            _setProperty( "%s.%d.Album"           % ( PROPERTY, _count ), _musicvid.get('album',''))
            _setProperty( "%s.%d.Track"           % ( PROPERTY, _count ), str(_musicvid.get('track','')))
            _setProperty( "%s.%d.Plot"            % ( PROPERTY, _count ), _musicvid.get('plot',''))
            _setProperty( "%s.%d.Tag"             % ( PROPERTY, _count ), " / ".join(_musicvid.get('tag','')))
            _setProperty( "%s.%d.Runtime"         % ( PROPERTY, _count ), runtime)
            _setProperty( "%s.%d.Director"        % ( PROPERTY, _count ), " / ".join(_musicvid.get('director','')))
            _setProperty( "%s.%d.Art(thumb)"      % ( PROPERTY, _count ), art.get('poster',''))
            _setProperty( "%s.%d.Art(poster)"     % ( PROPERTY, _count ), art.get('poster',''))
            _setProperty( "%s.%d.Art(fanart)"     % ( PROPERTY, _count ), art.get('fanart',''))
            _setProperty( "%s.%d.Art(clearlogo)"  % ( PROPERTY, _count ), art.get('clearlogo',''))
            _setProperty( "%s.%d.Art(clearart)"   % ( PROPERTY, _count ), art.get('clearart',''))
            _setProperty( "%s.%d.Art(landscape)"  % ( PROPERTY, _count ), art.get('landscape',''))
            _setProperty( "%s.%d.Art(banner)"     % ( PROPERTY, _count ), art.get('banner',''))
            _setProperty( "%s.%d.Art(discart)"    % ( PROPERTY, _count ), art.get('discart',''))                
            _setProperty( "%s.%d.Resume"          % ( PROPERTY, _count ), resume)
            _setProperty( "%s.%d.PercentPlayed"   % ( PROPERTY, _count ), played)
            _setProperty( "%s.%d.Watched"         % ( PROPERTY, _count ), watched)
            _setProperty( "%s.%d.File"            % ( PROPERTY, _count ), _musicvid.get('file',''))
            _setProperty( "%s.%d.Path"            % ( PROPERTY, _count ), path)
            _setProperty( "%s.%d.Play"            % ( PROPERTY, _count ), play)
            _setProperty( "%s.%d.VideoCodec"      % ( PROPERTY, _count ), streaminfo['videocodec'])
            _setProperty( "%s.%d.VideoResolution" % ( PROPERTY, _count ), streaminfo['videoresolution'])
            _setProperty( "%s.%d.VideoAspect"     % ( PROPERTY, _count ), streaminfo['videoaspect'])
            _setProperty( "%s.%d.AudioCodec"      % ( PROPERTY, _count ), streaminfo['audiocodec'])
            _setProperty( "%s.%d.AudioChannels"   % ( PROPERTY, _count ), str(streaminfo['audiochannels']))
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setProperty( "%s.%d.Title"       % ( PROPERTY, _count ), "" )
    else:
        log("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        log("[RandomAndLastItems] JSON RESULT %s" %_json_pl_response)

def _getEpisodesFromPlaylist ( ):
    global LIMIT
    global METHOD
    global PLAYLIST
    global RESUME
    global REVERSE
    global SORTBY
    global UNWATCHED
    global PROPERTY
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    _tvshows = 0
    _tvshowid = []
    # Request database using JSON
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "video", "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "studio", "mpaa", "rating", "resume", "runtime", "tvshowid", "art", "streamdetails", "firstaired", "dateadded"] }, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = json.loads(_json_query)
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _file in _files:
            if xbmc.abortRequested:
                break
            if _file['type'] == 'tvshow':
                _tvshows += 1
                # Playlist return TV Shows - Need to get episodes
                _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "tvshowid": %s, "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "rating", "resume", "runtime", "tvshowid", "art", "streamdetails", "firstaired", "dateadded"] }, "id": 1}' %(_file['id']))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_response = json.loads(_json_query)
                _episodes = _json_response.get( "result", {} ).get( "episodes" )
                if _episodes:
                    for _episode in _episodes:
                        if xbmc.abortRequested:
                            break
                        # Add TV Show fanart and thumbnail for each episode
                        art = _episode['art']
                        # Add episode ID when playlist type is TVShow
                        _episode["id"]=_episode['episodeid']
                        _episode["tvshowfanart"]=art.get('tvshow.fanart')
                        _episode["tvshowthumb"]=art.get('thumb')
                        # Set MPAA and studio for all episodes
                        _episode["mpaa"]=_file['mpaa']
                        _episode["studio"]=_file['studio']
                        _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _episode )
                else:
                    log("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
                    log("[RandomAndLastItems] JSON RESULT %s" %_json_response)
            if _file['type'] == 'episode':
                _id = _file['tvshowid']
                if _id not in _tvshowid:
                    _tvshows += 1
                    _tvshowid.append(_id)
                # Playlist return TV Shows - Nothing else to do
                _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _file )
        _setVideoProperties ( _total, _watched, _unwatched )
        _setTvShowsProperties ( _tvshows )
        _count = 0
        if METHOD == 'Last':
            _result = sorted(_result, key=itemgetter('dateadded'), reverse=True)
        elif METHOD == 'Playlist':
            _result = sorted(_result, key=itemgetter(SORTBY), reverse=REVERSE)
        else:
            random.shuffle(_result, random.random)
        for _episode in _result:
            if xbmc.abortRequested or _count == LIMIT:
                break
            _count += 1
            '''
            if _episode.get("tvshowid"):
                _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": { "tvshowid": %s, "properties": ["title", "fanart", "thumbnail"] }, "id": 1}' %(_episode['tvshowid']))
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_pl_response = json.loads(_json_query)
                _tvshow = _json_pl_response.get( "result", {} ).get( "tvshowdetails" )
            '''
            _setEpisodeProperties ( _episode, _count )
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setEpisodeProperties ( None, _count )
    else:
        log("[RandomAndLastItems] # 01 # PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        log("[RandomAndLastItems] JSON RESULT %s" %_json_pl_response)

def _getEpisodes ( ):
    global LIMIT
    global METHOD
    global RESUME
    global REVERSE
    global SORTBY
    global UNWATCHED
    _result = []
    _total = 0
    _unwatched = 0
    _watched = 0
    _tvshows = 0
    _tvshowid = []
    # Request database using JSON
    _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": { "properties": ["title", "playcount", "season", "episode", "showtitle", "plot", "file", "studio", "mpaa", "rating", "resume", "runtime", "tvshowid", "art", "streamdetails", "firstaired", "dateadded"]}, "id": 1}')
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = json.loads(_json_query)
    # If request return some results
    _episodes = _json_pl_response.get( "result", {} ).get( "episodes" )
    if _episodes:
        for _item in _episodes:
            if xbmc.abortRequested:
                break
            _id = _item['tvshowid']
            if _id not in _tvshowid:
                _tvshows += 1
                _tvshowid.append(_id)
            # Add episode ID
            _item["id"]=_item['episodeid']
            _total, _watched, _unwatched, _result = _watchedOrResume ( _total, _watched, _unwatched, _result, _item )
        _setVideoProperties ( _total, _watched, _unwatched )
        _setTvShowsProperties ( _tvshows )
        _count = 0
        if METHOD == 'Last':
            _result = sorted(_result, key=itemgetter('dateadded'), reverse=True)
        elif METHOD == 'Playlist':
            _result = sorted(_result, key=itemgetter(SORTBY), reverse=REVERSE)
        else:
            random.shuffle(_result, random.random)
        for _episode in _result:
            if xbmc.abortRequested or _count == LIMIT:
                break
            _count += 1
            _setEpisodeProperties ( _episode, _count )
        if _count != LIMIT:
            while _count < LIMIT:
                _count += 1
                _setEpisodeProperties ( None, _count )
    else:
        log("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        log("[RandomAndLastItems] JSON RESULT %s" %_json_pl_response)

def _getAlbumsFromPlaylist ( ):
    global LIMIT
    global METHOD
    global PLAYLIST
    global REVERSE
    global SORTBY
    _result = []
    _artists = 0
    _artistsid = []
    _albums = []
    _albumsid = []
    _songs = 0
    # Request database using JSON
    if PLAYLIST == "":
        PLAYLIST = "musicdb://songs/"
    #_json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["title", "description", "albumlabel", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount", "dateadded"]}, "id": 1}' %(PLAYLIST))
    if METHOD == 'Random':
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["dateadded"], "sort": {"method": "random"}}, "id": 1}' %(PLAYLIST))
    elif METHOD == 'Last':
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["dateadded"], "sort": {"order": "descending", "method": "dateadded"}}, "id": 1}' %(PLAYLIST))
    elif METHOD == 'Playlist':
        order = "ascending"
        if REVERSE:
            order = "descending"
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["dateadded"], "sort": {"order": "%s", "method": "%s"}}, "id": 1}' %(PLAYLIST, order, SORTBY))
    else:
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "%s", "media": "music", "properties": ["dateadded"]}, "id": 1}' %(PLAYLIST))
    _json_query = unicode(_json_query, 'utf-8', errors='ignore')
    _json_pl_response = json.loads(_json_query)
    # If request return some results
    _files = _json_pl_response.get( "result", {} ).get( "files" )
    if _files:
        for _file in _files:
            if xbmc.abortRequested:
                break
            if _file['type'] == 'album':
                _albums.append(_file)
                _albumid = _file['id']
                # Album playlist so get path from songs
                _json_query = xbmc.executeJSONRPC('{"id":1, "jsonrpc":"2.0", "method":"AudioLibrary.GetSongs", "params":{"filter":{"albumid": %s}, "properties":["artistid"]}}' %_albumid)
                _json_query = unicode(_json_query, 'utf-8', errors='ignore')
                _json_pl_response = json.loads(_json_query)
                _result = _json_pl_response.get( "result", {} ).get( "songs" )
                if _result:
                    _songs += len(_result)
                    _artistid = _result[0]['artistid']
                    if _artistid not in _artistsid:
                        _artists += 1
                        _artistsid.append(_artistid)
            #_albumid = _file.get('albumid', _file.get('id'))
            #_albumpath = os.path.split(_file['file'])[0]
            #_artistpath = os.path.split(_albumpath)[0]
            #_songs += 1
            '''
            if _albumid not in _albumsid:
                _file["id"] = _albumid
                _file["albumPath"] = _albumpath
                _file["artistPath"] = _artistpath
                _albums.append(_file)
                _albumsid.append(_albumid)
            '''
        _setMusicProperties ( _artists, len(_files), _songs )
        '''
        # This doesn't work atm because Files.GetDirectory doesn't retrieve dateadded for albums
        if METHOD == 'Last':
            _result = sorted(_result, key=itemgetter('dateadded'), reverse=True)
        else:
            random.shuffle(_result, random.random)
        '''
        _count = 0
        for _album in _albums:
            if xbmc.abortRequested or _count == LIMIT:
                break
            _count += 1
            _albumid = _album['id'];
            _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbumDetails", "params":{"albumid": %s, "properties":["title", "description", "albumlabel", "theme", "mood", "style", "type", "artist", "genre", "year", "thumbnail", "fanart", "rating", "playcount"]}, "id": 1}' %_albumid )
            _json_query = unicode(_json_query, 'utf-8', errors='ignore')
            _json_pl_response = json.loads(_json_query)
            # If request return some results
            _album = _json_pl_response.get( "result", {} ).get( "albumdetails" )
            _setAlbumPROPERTIES ( _album, _count )
        if _count <= LIMIT:
            while _count < LIMIT:
                _count += 1
                _setAlbumPROPERTIES ( None, _count )
    else:
        log("[RandomAndLastItems] ## PLAYLIST %s COULD NOT BE LOADED ##" %(PLAYLIST))
        log("[RandomAndLastItems] JSON RESULT %s" %_json_pl_response)

def _clearProperties ( ):
    global WINDOW
    # Reset window Properties
    WINDOW.clearProperty( "%s.Loaded" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Count" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Watched" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Unwatched" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Artists" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Albums" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Songs" % ( PROPERTY ) )
    WINDOW.clearProperty( "%s.Type" % ( PROPERTY ) )

def _setMusicProperties ( _artists, _albums, _songs ):
    global PROPERTY
    global WINDOW
    global TYPE
    # Set window Properties
    _setProperty ( "%s.Artists" % ( PROPERTY ), str( _artists ) )
    _setProperty ( "%s.Albums" % ( PROPERTY ), str( _albums ) )
    _setProperty ( "%s.Songs" % ( PROPERTY ), str( _songs ) )
    _setProperty ( "%s.Type" % ( PROPERTY ), TYPE )

def _setVideoProperties ( _total, _watched, _unwatched ):
    global PROPERTY
    global WINDOW
    global TYPE
    # Set window Properties
    _setProperty ( "%s.Count" % ( PROPERTY ), str( _total ) )
    _setProperty ( "%s.Watched" % ( PROPERTY ), str( _watched ) )
    _setProperty ( "%s.Unwatched" % ( PROPERTY ), str( _unwatched ) )
    _setProperty ( "%s.Type" % ( PROPERTY ), TYPE )

def _setTvShowsProperties ( _tvshows ):
    global PROPERTY
    global WINDOW
    # Set window Properties
    _setProperty ( "%s.TvShows" % ( PROPERTY ), str( _tvshows ) )

def _setEpisodeProperties ( _episode, _count ):
    if _episode:
        _json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["streamdetails"], "episodeid":%s }, "id": 1}' %(_episode['id']))
        _json_query = unicode(_json_query, 'utf-8', errors='ignore')
        _json_query = json.loads(_json_query)
        if _json_query['result'].has_key('episodedetails'):
            item = _json_query['result']['episodedetails']
            _episode['streamdetails'] = item['streamdetails']
        episode = ("%.2d" % float(_episode['episode']))
        season = "%.2d" % float(_episode['season'])
        episodeno = "s%se%s" %(season,episode)
        rating = str(round(float(_episode['rating']),1))
        if _episode['resume']['position'] > 0:
            resume = "true"
            played = '%s%%'%int((float(_episode['resume']['position']) / float(_episode['resume']['total'])) * 100)
        else:
            resume = "false"
            played = '0%'
        art = _episode['art']
        path = media_path(_episode['file'])
        play = 'XBMC.RunScript(' + __addonid__ + ',episodeid=' + str(_episode.get('id')) + ')'
        runtime = str(int((_episode['runtime'] / 60) + 0.5))
        streaminfo = media_streamdetails(_episode['file'].encode('utf-8').lower(),
                                         _episode['streamdetails'])
        _setProperty("%s.%d.DBID"                  % ( PROPERTY, _count ), str(_episode.get('id')))
        _setProperty("%s.%d.Title"                 % ( PROPERTY, _count ), _episode.get('title',''))
        _setProperty("%s.%d.Episode"               % ( PROPERTY, _count ), episode)
        _setProperty("%s.%d.EpisodeNo"             % ( PROPERTY, _count ), episodeno)
        _setProperty("%s.%d.Season"                % ( PROPERTY, _count ), season)
        _setProperty("%s.%d.Plot"                  % ( PROPERTY, _count ), _episode.get('plot',''))
        _setProperty("%s.%d.TVshowTitle"           % ( PROPERTY, _count ), _episode.get('showtitle',''))
        _setProperty("%s.%d.Rating"                % ( PROPERTY, _count ), rating)
        _setProperty("%s.%d.Art(thumb)"            % ( PROPERTY, _count ), art.get('thumb',''))
        _setProperty("%s.%d.Art(tvshow.fanart)"    % ( PROPERTY, _count ), art.get('tvshow.fanart',''))
        _setProperty("%s.%d.Art(tvshow.poster)"    % ( PROPERTY, _count ), art.get('tvshow.poster',''))
        _setProperty("%s.%d.Art(tvshow.banner)"    % ( PROPERTY, _count ), art.get('tvshow.banner',''))
        _setProperty("%s.%d.Art(tvshow.clearlogo)" % ( PROPERTY, _count ), art.get('tvshow.clearlogo',''))
        _setProperty("%s.%d.Art(tvshow.clearart)"  % ( PROPERTY, _count ), art.get('tvshow.clearart',''))
        _setProperty("%s.%d.Art(tvshow.landscape)" % ( PROPERTY, _count ), art.get('tvshow.landscape',''))
        _setProperty("%s.%d.Art(fanart)"           % ( PROPERTY, _count ), art.get('tvshow.fanart',''))
        _setProperty("%s.%d.Art(poster)"           % ( PROPERTY, _count ), art.get('tvshow.poster',''))
        _setProperty("%s.%d.Art(banner)"           % ( PROPERTY, _count ), art.get('tvshow.banner',''))
        _setProperty("%s.%d.Art(clearlogo)"        % ( PROPERTY, _count ), art.get('tvshow.clearlogo',''))
        _setProperty("%s.%d.Art(clearart)"         % ( PROPERTY, _count ), art.get('tvshow.clearart',''))
        _setProperty("%s.%d.Art(landscape)"        % ( PROPERTY, _count ), art.get('tvshow.landscape',''))
        _setProperty("%s.%d.Resume"                % ( PROPERTY, _count ), resume)
        _setProperty("%s.%d.Watched"               % ( PROPERTY, _count ), _episode.get('watched',''))
        _setProperty("%s.%d.Runtime"               % ( PROPERTY, _count ), runtime)
        _setProperty("%s.%d.Premiered"             % ( PROPERTY, _count ), _episode.get('firstaired',''))
        _setProperty("%s.%d.PercentPlayed"         % ( PROPERTY, _count ), played)
        _setProperty("%s.%d.File"                  % ( PROPERTY, _count ), _episode.get('file',''))
        _setProperty("%s.%d.MPAA"                  % ( PROPERTY, _count ), _episode.get('mpaa',''))
        _setProperty("%s.%d.Studio"                % ( PROPERTY, _count ), " / ".join(_episode.get('studio','')))
        _setProperty("%s.%d.Path"                  % ( PROPERTY, _count ), path)
        _setProperty("%s.%d.Play"                  % ( PROPERTY, _count ), play)
        _setProperty("%s.%d.VideoCodec"            % ( PROPERTY, _count ), streaminfo['videocodec'])
        _setProperty("%s.%d.VideoResolution"       % ( PROPERTY, _count ), streaminfo['videoresolution'])
        _setProperty("%s.%d.VideoAspect"           % ( PROPERTY, _count ), streaminfo['videoaspect'])
        _setProperty("%s.%d.AudioCodec"            % ( PROPERTY, _count ), streaminfo['audiocodec'])
        _setProperty("%s.%d.AudioChannels"         % ( PROPERTY, _count ), str(streaminfo['audiochannels']))
    else:
        _setProperty("%s.%d.Title"               % ( PROPERTY, _count ), '')
    

def _setAlbumPROPERTIES ( _album, _count ):
    global PROPERTY
    if _album:
        # Set window Properties
        _rating = str(_album['rating'])
        if _rating == '48':
            _rating = ''
        play = 'XBMC.RunScript(' + __addonid__ + ',albumid=' + str(_album.get('albumid')) + ')'
        path = 'musicdb://albums/' + str(_album.get('albumid')) + '/'
        _setProperty("%s.%d.Title"       % ( PROPERTY, _count ), _album.get('title',''))
        _setProperty("%s.%d.Artist"      % ( PROPERTY, _count ), " / ".join(_album.get('artist','')))
        _setProperty("%s.%d.Genre"       % ( PROPERTY, _count ), " / ".join(_album.get('genre','')))
        _setProperty("%s.%d.Theme"       % ( PROPERTY, _count ), " / ".join(_album.get('theme','')))
        _setProperty("%s.%d.Mood"        % ( PROPERTY, _count ), " / ".join(_album.get('mood','')))
        _setProperty("%s.%d.Style"       % ( PROPERTY, _count ), " / ".join(_album.get('style','')))
        _setProperty("%s.%d.Type"        % ( PROPERTY, _count ), _album.get('type',''))
        _setProperty("%s.%d.Year"        % ( PROPERTY, _count ), str(_album.get('year','')))
        _setProperty("%s.%d.RecordLabel" % ( PROPERTY, _count ), _album.get('albumlabel',''))
        _setProperty("%s.%d.Description" % ( PROPERTY, _count ), _album.get('description',''))
        _setProperty("%s.%d.Rating"      % ( PROPERTY, _count ), _rating)
        _setProperty("%s.%d.Art(thumb)"  % ( PROPERTY, _count ), _album.get('thumbnail',''))
        _setProperty("%s.%d.Art(fanart)" % ( PROPERTY, _count ), _album.get('fanart',''))
        _setProperty("%s.%d.Play"        % ( PROPERTY, _count ), play)
        _setProperty("%s.%d.LibraryPath" % ( PROPERTY, _count ), path)
    else:
        _setProperty("%s.%d.Title"       % ( PROPERTY, _count ), '')
    
def _setProperty ( _property, _value ):
    global WINDOW
    # Set window Properties
    WINDOW.setProperty ( _property, _value )

def _parse_argv ( ):
    try:
        params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        params = {}
    if params.get("movieid"):
        #xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %d }, "options":{ "resume": true } }, "id": 1 }' % int(params.get("movieid")))
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "movieid": %d }, "options":{ "resume": %s } }, "id": 1 }' % (int(params.get("movieid","")), params.get("resume","true")))
    elif params.get("episodeid"):
        #xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": true }  }, "id": 1 }' % int(params.get("episodeid")))
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "episodeid": %d }, "options":{ "resume": %s }  }, "id": 1 }' % (int(params.get("episodeid","")), params.get("resume","true")))
    elif params.get("musicvideoid"):
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "musicvideoid": %d } }, "id": 1 }' % int(params.get("musicvideoid")))
    elif params.get("albumid"):
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "albumid": %d } }, "id": 1 }' % int(params.get("albumid")))
    elif params.get("songid"):
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.Open", "params": { "item": { "songid": %d } }, "id": 1 }' % int(params.get("songid")))
    else:
        global METHOD
        global MENU
        global LIMIT
        global PLAYLIST
        global PROPERTY
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
                PLAYLIST = PLAYLIST.replace('"', '')
            elif 'property=' in param:
                PROPERTY = param.replace('property=', '')
            elif 'type=' in param:
                TYPE = param.replace('type=', '')
            elif 'unwatched=' in param:
                UNWATCHED = param.replace('unwatched=', '')
                if UNWATCHED == '':
                    UNWATCHED = 'False'
            elif 'resume=' in param:
                RESUME = param.replace('resume=', '')
        # If playlist= parameter is set then get type= from playlist
        if PLAYLIST != '':
            _getPlaylistType ();
        if PROPERTY == "":
            PROPERTY = "Playlist%s%s%s" % ( METHOD, TYPE, MENU )

def media_streamdetails(filename, streamdetails):
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    if '3d' in filename:
        info['videoresolution'] = '3d'
    elif video:
        videowidth = video[0]['width']
        videoheight = video[0]['height']
        if (video[0]['width'] <= 720 and video[0]['height'] <= 480):
            info['videoresolution'] = "480"
        elif (video[0]['width'] <= 768 and video[0]['height'] <= 576):
            info['videoresolution'] = "576"
        elif (video[0]['width'] <= 960 and video[0]['height'] <= 544):
            info['videoresolution'] = "540"
        elif (video[0]['width'] <= 1280 and video[0]['height'] <= 720):
            info['videoresolution'] = "720"
        elif (video[0]['width'] >= 1281 and video[0]['height'] >= 721):
            info['videoresolution'] = "1080"
        else:
            info['videoresolution'] = ""
    elif (('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename) or (filename.endswith('.vob' or '.ifo')):
        info['videoresolution'] = '576'
    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd') in filename):
        info['videoresolution'] = '1080'
    else:
        info['videoresolution'] = '1080'
    if video and 'duration' in video[0]:
        info['duration'] = video[0]['duration']
    else:
        info['duration'] = 0
    if video:
        info['videocodec'] = video[0]['codec']
        if (video[0]['aspect'] < 1.4859):
            info['videoaspect'] = "1.33"
        elif (video[0]['aspect'] < 1.7190):
            info['videoaspect'] = "1.66"
        elif (video[0]['aspect'] < 1.8147):
            info['videoaspect'] = "1.78"
        elif (video[0]['aspect'] < 2.0174):
            info['videoaspect'] = "1.85"
        elif (video[0]['aspect'] < 2.2738):
            info['videoaspect'] = "2.20"
        else:
            info['videoaspect'] = "2.35"
    else:
        info['videocodec'] = ''
        info['videoaspect'] = ''
    if audio:
        info['audiocodec'] = audio[0]['codec']
        info['audiochannels'] = audio[0]['channels']
    else:
        info['audiocodec'] = ''
        info['audiochannels'] = ''
    return info

def media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,",",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        path = [os.path.split(urllib.url2pathname(path.replace("rar://","")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://","").split('%2f/')
        path = []
        for item in temp_path:
            path.append(urllib.url2pathname(item))
    else:
        path = [path]
    return path[0]

# Parse argv for any preferences
_parse_argv()
# Clear Properties
_clearProperties()
# Get movies and fill Properties
if TYPE == 'Movie':
    _getMovies()
elif TYPE == 'Episode':
    if PLAYLIST == '':
        _getEpisodes()
    else:
        _getEpisodesFromPlaylist()
elif TYPE == 'Music':
    _getAlbumsFromPlaylist()
elif TYPE == 'MusicVideo':
    _getMusicVideosFromPlaylist()
WINDOW.setProperty( "%s.Loaded" % PROPERTY, "true" )
log( "Loading Playlist%s%s%s started at %s and take %s" %( METHOD, TYPE, MENU, time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime( START_TIME ) ), _timeTook( START_TIME ) ) )

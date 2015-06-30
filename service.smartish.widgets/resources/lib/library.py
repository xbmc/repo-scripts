# coding=utf-8
import os
import sys
from datetime import datetime
import xbmc
import xbmcgui
import xbmcaddon
from traceback import print_exc
import hashlib

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

import sql

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__cwd__          = __addon__.getAddonInfo('path').decode("utf-8")
__datapath__     = os.path.join( xbmc.translatePath( "special://profile/addon_data/" ).decode('utf-8'), __addonid__ )
__datapathalt__  = os.path.join( "special://profile/", "addon_data", __addonid__ )
__skinpath__     = xbmc.translatePath( "special://skin/shortcuts/" ).decode('utf-8')
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]
__defaultpath__  = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'shortcuts').encode("utf-8") ).decode("utf-8")
__xbmcversion__  = xbmc.getInfoLabel( "System.BuildVersion" ).split(".")[0]

# Used to make sure we don't display currently playing
lastplayedType = None
lastplayedID = None
nowPlaying = {}

# Used to try and save lots of processing for episodes
tvshowInformation = {}
tvshowNextUnwatched = {}
tvshowNewest = {}

movieScores = {}

def log(txt):
    try:
        if isinstance (txt,str):
            txt = txt.decode('utf-8')
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode('utf-8'), level=xbmc.LOGDEBUG)
    except:
        pass

def getMedia( mediaType, habits, freshness ):
    items = {}
    weighted = {}
    logged = {}

    if mediaType == "pvr":
        # Perform a JSON query to get all recordings (Do we want/can we filter?)
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetRecordings", "params": {"properties": [ "title", "plot", "plotoutline", "genre", "playcount", "resume", "channel", "starttime", "endtime",	"runtime", "lifetime", "icon", "art", "streamurl", "file", "directory" ]}}' )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('recordings'):
            for item in json_query['result']['recordings']:
                processRecorded( habits, items, weighted, item, freshness )
                if xbmc.abortRequested:
                    return None, None

        # Perform a JSON query to get all tv channel groups
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannelGroups", "params": {"channeltype": "tv"}}' )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)

        if json_query.has_key('result') and json_query['result'].has_key('channelgroups'):
            for group in json_query['result']['channelgroups']:
                # Perform a JSON query to get all channels
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannels", "params": {"channelgroupid": %d, "properties": [ "thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed" ]}}' %( group[ "channelgroupid" ] ) )
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_query = simplejson.loads(json_query)
                if json_query.has_key('result') and json_query['result'].has_key('channels'):
                    for item in json_query['result']['channels']:
                        # Get next two shows for the channel
                        json_query = xbmc.executeJSONRPC( '{ "jsonrpc": "2.0",  "id": 1, "method": "PVR.GetBroadcasts", "params": {"channelid": %d, "properties": [ "title", "plot", "plotoutline", "starttime", "endtime", "runtime", "progress", "progresspercentage", "genre", "episodename", "episodenum", "episodepart", "firstaired", "hastimer", "isactive", "parentalrating", "wasactive", "thumbnail" ], "limits": {"end": 2} } }' %( item[ "channelid" ] ) )
                        json_query = unicode(json_query, 'utf-8', errors='ignore')
                        json_query = simplejson.loads(json_query)
                        if json_query.has_key( "result" ) and json_query[ "result" ].has_key( "broadcasts" ):
                            processLive( habits, items, weighted, item, json_query[ "result" ][ "broadcasts" ], freshness )
                        if xbmc.abortRequested:
                            return None, None

        # Perform a JSON query to get all radio channel groups
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannelGroups", "params": {"channeltype": "radio"}}' )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)

        if json_query.has_key('result') and json_query['result'].has_key('channelgroups'):
            for group in json_query['result']['channelgroups']:
                # Perform a JSON query to get all channels
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0",  "id": 1, "method": "PVR.GetChannels", "params": {"channelgroupid": %d, "properties": [ "thumbnail", "channeltype", "hidden", "locked", "channel", "lastplayed" ]}}' %( group[ "channelgroupid" ] ) )
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_query = simplejson.loads(json_query)
                if json_query.has_key('result') and json_query['result'].has_key('channels'):
                    for item in json_query['result']['channels']:
                        json_query = xbmc.executeJSONRPC( '{ "jsonrpc": "2.0",  "id": 1, "method": "PVR.GetBroadcasts", "params": {"channelid": %d, "properties": [ "title", "plot", "plotoutline", "starttime", "endtime", "runtime", "progress", "progresspercentage", "genre", "episodename", "episodenum", "episodepart", "firstaired", "hastimer", "isactive", "parentalrating", "wasactive", "thumbnail" ], "limits": {"end": 2} } }' %( item[ "channelid" ] ) )
                        json_query = unicode(json_query, 'utf-8', errors='ignore')
                        json_query = simplejson.loads(json_query)
                        if json_query.has_key( "result" ) and json_query[ "result" ].has_key( "broadcasts" ):
                            processLive( habits, items, weighted, item, json_query[ "result" ][ "broadcasts" ], freshness )
                        if xbmc.abortRequested:
                            return None, None

    elif mediaType == "movie":
        # Perform a JSON to get all the movies
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded", "tag", "imdbnumber" ] }, "filter": {"field": "playcount", "operator": "lessthan", "value": "1"} }'
        json_query = xbmc.executeJSONRPC( '%s' %( json_string ) )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('movies'):
            for item in json_query['result']['movies']:
                processMovie( habits, items, weighted, item, freshness )
                if xbmc.abortRequested:
                    return None, None

    elif mediaType == "episode":
        # Perform a JSON to get all TV Shows
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "VideoLibrary.GetTVShows", "params": {"properties": [ "title", "mpaa", "studio", "genre", "cast", "tag", "playcount", "lastplayed", "episode", "season", "watchedepisodes", "imdbnumber", "premiered" ] }} '
        json_query = xbmc.executeJSONRPC('%s' %( json_string ) )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('tvshows'):
            for item in json_query['result']['tvshows']:
                processTvshows( habits, items, weighted, logged, item, freshness )
                if xbmc.abortRequested:
                    return None, None

    elif mediaType == "album":
        # Perform a JSON to get all albums
        json_string = '{"jsonrpc": "2.0",  "id": 1, "method": "AudioLibrary.GetAlbums", "params": {"properties": [ "title", "description", "artist", "genre", "theme", "mood", "style", "type", "albumlabel", "rating", "year", "musicbrainzalbumid", "musicbrainzalbumartistid", "fanart", "thumbnail", "playcount", "genreid", "artistid", "displayartist" ] }} '
        json_query = xbmc.executeJSONRPC('%s' %( json_string ) )
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if json_query.has_key('result') and json_query['result'].has_key('albums'):
            for item in json_query['result']['albums']:
                processAlbum( habits, items, weighted, item, freshness )
                if xbmc.abortRequested:
                    return None, None

    return weighted, items

def getWeighting( type, key ):
    weighting = 0

    # Retrieve the weighting the user has given the key
    if type == "movies":
        if key == "mpaa":
            weighting = float( __addon__.getSetting( "movieRating" ) )
        elif key == "tag":
            weighting = float( __addon__.getSetting( "movieTag" ) )
        elif key == "director":
            weighting = float( __addon__.getSetting( "movieDirector" ) )
        elif key == "writer":
            weighting = float( __addon__.getSetting( "movieWriter" ) )
        elif key == "studio":
            weighting = float( __addon__.getSetting( "movieStudio" ) )
        elif key == "genre":
            weighting = float( __addon__.getSetting( "movieGenre" ) )
        elif key == "actor":
            weighting = float( __addon__.getSetting( "movieActor" ) )
        elif key == "keyword":
            weighting = float( __addon__.getSetting( "movieKeyword" ) )
        elif key == "related":
            weighting = float( __addon__.getSetting( "movieRelated" ) )
    if type == "episodes":
        if key == "mpaa":
            weighting = float( __addon__.getSetting( "tvRating" ) )
        elif key == "tag":
            weighting = float( __addon__.getSetting( "tvTag" ) )
        elif key == "studio":
            weighting = float( __addon__.getSetting( "tvStudio" ) )
        elif key == "genre":
            weighting = float( __addon__.getSetting( "tvGenre" ) )
        elif key == "actor":
            weighting = float( __addon__.getSetting( "tvActor" ) )
        elif key == "keyword":
            weighting = float( __addon__.getSetting( "tvKeyword" ) )
        elif key == "related":
            weighting = float( __addon__.getSetting( "tvRelated" ) )
    if type == "album":
        if key == "artist":
            weighting = float( __addon__.getSetting( "albumArtist" ) )
        if key == "style":
            weighting = float( __addon__.getSetting( "albumStyle" ) )
        if key == "theme":
            weighting = float( __addon__.getSetting( "albumTheme" ) )
        if key == "genre":
            weighting = float( __addon__.getSetting( "albumGenre" ) )
        if key == "mood":
            weighting = float( __addon__.getSetting( "albumMood" ) )
        if key == "label":
            weighting = float( __addon__.getSetting( "albumLabel" ) )
    if type == "pvr":
        if key == "channel":
            weighting = float( __addon__.getSetting( "pvrChannel" ) )
        if key == "genre":
            weighting = float( __addon__.getSetting( "pvrGenre" ) )

    return weighting

def processRecorded( habits, recordedshows, weighted, item, freshness ):
    # If this show has already been processed, pass
    if "R" + str( item['recordingid'] ) in recordedshows.keys():
        return

    # Save the show
    recordedshows[ "R" + str( item['recordingid'] ) ] = item

    # If the show is current being watched, pass
    if _playingNow( "recorded", int( item[ "recordingid" ] ) ):
        return
    #if lastplayedID is not None and lastplayedType == "recorded":
    #    if int( item[ "recordingid" ] ) == int( lastplayedID ):
    #        return

    # If this show has been watched, pass
    if item[ 'playcount' ] >= 1:
        return

    # Split genres
    genres = []
    for genre in item[ "genre" ]:
        for splitGenre in genre.split( "/" ):
            genres.append( splitGenre )

    # Work out the weighting
    weight = 0
    scores = []
    for key in habits.keys():
        weighting = getWeighting( "pvr", key )
        for percentage, habit in habits[ key ]:
            for value in habit:
                value = value.decode( "utf-8" )
                if key == "genre":
                    # List
                    for genre in genres:
                        if genre == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( genres ) )

                if key == "channel":
                    if item[ "channel" ] == value:
                        weight += ( weighting / 100 ) * percentage

    # Convert endtime to a DateTime object
    dateadded = datetime.now() - datetime.strptime( item[ "endtime" ], "%Y-%m-%d %H:%M:%S" )
    freshnessAddition = 0.00

    # Add weighting dependant on fresh/recent
    if dateadded.days <= 2:
        if freshness[ 0 ] != 0 and weight != 0:
            freshnessAddition += ( weight / 100.00 ) * freshness[ 0 ]
    elif dateadded.days <= 7:
        if freshness[ 1 ] != 0 and weight != 0:
            freshnessAddition += ( weight / 100.00 ) * freshness[ 1 ]

    weight += int( freshnessAddition )

    if weight not in weighted.keys():
        weighted[ weight ] = [ "R" + str( item[ "recordingid" ] ) ]
    else:
        weighted[ weight ].append( "R" + str( item[ "recordingid" ] ) )

def processLive( habits, liveshows, weighted, item, nownext, freshness, addition = "L" ):
    # If there is no 'broadcastnow' or 'broadcastnext', we aint gonna process is

    # If this show has already been processed, pass
    if addition + str( item['channelid'] ) in liveshows.keys():
        return

    # Save the show
    liveshows[ addition + str( item['channelid'] ) ] = item

    # If the show is current being watched, pass
    if _playingNow( "pvr", int( item[ "channelid" ] ) ):
        return
    #if lastplayedID is not None and lastplayedType == "pvr":
    #    if int( item[ "channelid" ] ) == int( lastplayedID ):
    #        return

    showtoWeight = nownext[ 0 ]

    # Work out percent complete (json value appears incorrect
    showLength = datetime.strptime( showtoWeight[ "endtime" ], "%Y-%m-%d %H:%M:%S" ) - datetime.strptime( showtoWeight[ "starttime" ], "%Y-%m-%d %H:%M:%S" )
    showLength = showLength.seconds / 60.0

    timeStarted = datetime.now() - datetime.strptime( showtoWeight[ "starttime" ], "%Y-%m-%d %H:%M:%S" )
    minutesRun = timeStarted.seconds / 60.0

    percentRun = int( ( minutesRun / showLength ) * 100.0 )

    # If progresspercentage is over 80%, and the next program starts within 30 minutes
    # we'll base on the next show, not the current one
    if percentRun > 80 and len( nownext ) == 2:
        # Convert the starttime of the next show to a DateTime object
        nextStart = datetime.strptime( nownext[ 1 ][ "starttime" ], "%Y-%m-%d %H:%M:%S" ) - datetime.now()
        nextMinutes = int( nextStart.seconds / 60.0 )
        if nextMinutes < 30:
            showtoWeight = nownext[ 1 ]

    # Add broadcastnow and broadcastnext to item
    item[ "broadcastnow" ] = nownext[ 0 ]
    if len( nownext ) == 2:
        item[ "broadcastnext" ] = nownext[ 1 ]

    # Split genres
    genres = []
    for genre in showtoWeight[ "genre" ]:
        for splitGenre in genre.split( "/" ):
            genres.append( splitGenre )

    # Work out the weighting
    weight = 0
    for key in habits.keys():
        weighting = getWeighting( "pvr", key )
        for percentage, habit in habits[ key ]:
            for value in habit:
                value = value.decode( "utf-8" )
                if key == "genre":
                    # List
                    for genre in genres:
                        if genre == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( genres ) )

                if key == "channel":
                    if item[ "channel" ] == value:
                        weight += ( weighting / 100 ) * percentage

    # Add weighting dependant on normality of watching live
    freshnessAddition = 0.00
    if freshness[ 2 ] != 0 and weight != 0:
        freshnessAddition += (weight / 100.00 ) * freshness[ 2 ]

    if weight not in weighted.keys():
        weighted[ weight ] = [ addition + str( item[ "channelid" ] ) ]
    else:
        weighted[ weight ].append( addition + str( item[ "channelid" ] ) )

def processMovie( habits, movies, weighted, item, freshness ):
    # If this movie has already been processed, pass
    if item['movieid'] in movies.keys():
        return

    # Save the movie
    movies[ item['movieid'] ] = item

    # If the movie is current being watched, pass
    if _playingNow( "movie", int( item[ "movieid" ] ) ):
        return
    #if lastplayedID is not None and lastplayedType == "movie":
    #    if int( item[ "movieid" ] ) == int( lastplayedID ):
    #        return

    # If this movie has been watched, pass
    if item[ 'playcount' ] >= 1:
        return

    # Cut the year from the title
    title = item[ "title" ]
    try:
        if title[:-6] == "(":
            title = title[:-7]
    except:
        pass

    # Get additional TMDB information
    keywords, related = sql.getTMDBExtras( "movie", item[ "imdbnumber" ], item[ "title" ], item[ "year" ] )

    # Work out the weighting
    weight = 0
    scores = []
    for key in habits.keys():
        # Get weighting
        weighting = getWeighting( "movies", key )
        for percentage, habit in habits[ key ]:
            for value in habit:
                value = value.decode( "utf-8" )
                if key == "mpaa":
                    # Check directly
                    if item[ 'mpaa' ] == value:
                        weight += ( weighting / 100 ) * percentage
                        scores.append( "%s: %s (%f)" %( key, value, ( weighting / 100 ) * percentage ) )

                if key == "tag":
                    # List
                    for tag in item[ "tag" ]:
                        if value in tag:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "tag" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "tag" ] ) ) ) )

                if key == "director":
                    # List
                    for director in item[ "director" ]:
                        if director == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "director" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "director" ] ) ) ) )

                if key == "writer":
                    # List
                    for writer in item[ "writer" ]:
                        if writer == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "writer" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "writer" ] ) ) ) )

                if key == "studio":
                    # List
                    for studio in item[ "studio" ]:
                        if studio == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "studio" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "studio" ] ) ) ) )

                if key == "genre":
                    # List
                    for genre in item[ "genre" ]:
                        if genre == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "genre" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "genre" ] ) ) ) )

                if key == "actor":
                    for actor in item[ "cast" ]:
                        if actor[ "name" ] == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "cast" ] ) )
                            scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( item[ "cast" ] ) ) ) )

                if key == "keyword":
                    if value in keywords:
                        weight += ( ( weighting / 100 ) * percentage ) / float( len( keywords ) )
                        scores.append( "%s: %s (%f)" %( key, value, ( ( weighting / 100 ) * percentage ) / float( len( keywords ) ) ) )

                if key == "related":
                    if value == title.lower():
                        weight += ( weighting / 100 ) * percentage
                        scores.append( "%s: %s (%f)" %( key, value, ( weighting / 100 ) * percentage ) )

    # Convert dateadded to a DateTime object
    dateadded = datetime.now() - datetime.strptime( item[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )
    freshnessAddition = 0.00

    # Add weighting dependant on fresh/recent
    if dateadded.days <= 2:
        if freshness[ 0 ] != 0 and weight != 0:
            freshnessAddition += ( weight / 100.00 ) * freshness[ 0 ]
    elif dateadded.days <= 7:
        if freshness[ 1 ] != 0 and weight != 0:
            freshnessAddition += ( weight / 100.00 ) * freshness[ 1 ]

    weight += int( freshnessAddition )

    if weight not in weighted.keys():
        weighted[ weight ] = [ item[ "movieid" ] ]
    else:
        weighted[ weight ].append( item[ "movieid" ] )

    movieScores[ item[ "movieid" ] ] = scores

def processTvshows( habits, episodes, weighted, logged, item, freshness ):
    # If this show has already been processed, pass
    if item['tvshowid'] in logged.keys():
        return
    logged[ item[ "tvshowid" ] ] = "Processed"

    # If the show has been watched, do no more
    if item[ "watchedepisodes" ] == item[ "episode" ]:
        return

    # Get additional TMDB information
    keywords, related = sql.getTMDBExtras( "episode", item[ "imdbnumber" ], item[ "label" ], item[ "premiered" ][:-6] )

    # Cut the year from the title
    title = item[ "title" ]
    try:
        if title[:-6] == "(":
            title = title[:-7]
    except:
        pass

    # Work out the weighting
    weight = 0
    for key in habits.keys():
        weighting = getWeighting( "episodes", key )
        for percentage, habit in habits[ key ]:
            for value in habit:
                value = value.decode( "utf-8" )
                if key == "mpaa":
                    # Check directly
                    if item[ 'mpaa' ] == value:
                        weight += ( weighting / 100 ) * percentage

                if key == "tag":
                    # List
                    for tag in item[ "tag" ]:
                        if tag == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "tag" ] ) )

                if key == "studio":
                    # List
                    for studio in item[ "studio" ]:
                        if studio == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "studio" ] ) )

                if key == "genre":
                    # List
                    for genre in item[ "genre" ]:
                        if genre == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "genre" ] ) )

                if key == "actor":
                    for actor in item[ "cast" ]:
                        if actor[ "name" ] == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "cast" ] ) )

                if key == "keyword":
                    if value in keywords:
                        weight += ( weighting / 100 ) * percentage

                if key == "related":
                    if value == title.lower():
                        weight += ( weighting / 100 ) * percentage

    # Prepare to get episode information
    nextUnwatched = None
    newest = None
    newestDate = "0"
    playedDate = "0"
    addNextUnwatched = True

    # Get hash
    itemHash = hashlib.md5( simplejson.dumps( item ) ).hexdigest()

    # If we already have the episode information...
    if item[ "tvshowid" ] in tvshowInformation.keys() and tvshowInformation[ item[ "tvshowid" ] ] == itemHash:
        # Retrieve previously saved next and newest episodes
        nextUnwatched = tvshowNextUnwatched[ item[ "tvshowid" ] ]
        newest = tvshowNewest[ item[ "tvshowid" ] ]

    else:
        # Get all episodes
        episode_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, "properties": ["title", "playcount", "plot", "season", "episode", "showtitle", "file", "lastplayed", "rating", "resume", "art", "streamdetails", "firstaired", "runtime", "writer", "cast", "dateadded"], "sort": {"method": "episode"}}, "id": 1}' %item['tvshowid'])
        episode_query = unicode(episode_query, 'utf-8', errors='ignore')
        episode_query = simplejson.loads(episode_query)
        xbmc.sleep( 100 )

        # Find the next unwatched and the newest added episodes
        if episode_query.has_key( "result" ) and episode_query[ "result" ].has_key( "episodes" ):
            for episode in episode_query[ "result" ][ "episodes" ]:
                # Skip the episode if its the last played
                if _playingNow( "episode", int( episode[ "episodeid" ] ) ):
                    continue
                #if lastplayedID is not None and lastplayedType == "episode":
                #    if int( episode[ "episodeid" ] ) == int( lastplayedID ):
                #        continue
                if episode[ "playcount" ] == 0:
                    if addNextUnwatched:
                        # Next unwatched episode after most recently played we've found
                        nextUnwatched = episode
                        addNextUnwatched = False
                    if episode[ "dateadded" ] > newestDate:
                        # This episode is newer than any we've previously found
                        newestDate = episode[ "dateadded" ]
                        newest = episode
                elif episode[ "lastplayed" ] > playedDate:
                    # We've watched this episode more recently than any we've previously found
                    playedDate = episode[ "lastplayed" ]
                    addNextUnwatched = True

            # Save these for future runs
            tvshowInformation[ item[ "tvshowid" ] ] = itemHash
            tvshowNextUnwatched[ item[ "tvshowid" ] ] = nextUnwatched
            tvshowNewest[ item[ "tvshowid" ] ] = newest
        else:
            log( "No episodes returned for tv show " + item[ "tvshowid" ] )

    # If we didn't find any episodes, return
    if nextUnwatched is None and newest is None:
        return

    # If both episodes are the same, just keep the newest
    if nextUnwatched == newest:
        nextUnwatched = None

    # Save the next unwatched, with an additional weighting of 10
    if nextUnwatched is not None:
        episodes[ nextUnwatched[ 'episodeid' ] ] = nextUnwatched

        if weight not in weighted.keys():
            weighted[ weight ] = [ nextUnwatched[ "episodeid" ] ]
        else:
            weighted[ weight ].append( nextUnwatched[ "episodeid" ] )

    # Save the newest episode, with additional weighting on its new-ness
    if newest is not None:
        # Convert dateadded to a DateTime object
        dateadded = datetime.now() - datetime.strptime( newest[ "dateadded" ], "%Y-%m-%d %H:%M:%S" )
        freshnessAddition = 0.00

        # How new is it
        if dateadded.days <= 2:
            if freshness[ 0 ] != 0 and weight != 0:
                freshnessAddition += ( weight / 100.00 ) * freshness[ 0 ]
        elif dateadded.days <= 7:
            if freshness[ 1 ] != 0 and weight != 0:
                freshnessAddition += ( weight / 100.00 ) * freshness[ 1 ]

        # If this isn't fresh/recent...
        if int( freshnessAddition) == 0:
            if nextUnwatched is None:
                # There's no next unwatched, so give this an additional weighting of 10
                freshnessAddition = 10
            else:
                # We already have a next unwatched, so we're done
                return

        episodes[ newest[ 'episodeid' ] ] = newest

        if weight not in weighted.keys():
            weighted[ weight ] = [ newest[ "episodeid" ] ]
        else:
            weighted[ weight ].append( newest[ "episodeid" ] )

def processAlbum( habits, albums, weighted, item, freshness ):
    # If this album has already been processed, pass
    if item['albumid'] in albums.keys():
        return

    # Save the album
    albums[ item['albumid'] ] = item

    # Work out the weighting
    weight = 0
    for key in habits.keys():
        # Get weighting
        weighting = getWeighting( "album", key )
        for percentage, habit in habits[ key ]:
            for value in habit:
                value = value.decode( "utf-8" )
                if key == "label":
                    # Check directly
                    if item[ 'label' ] == value:
                        weight += ( weighting / 100 ) * percentage

                if key == "artist":
                    # List
                    for artist in item[ "artist" ]:
                        if artist == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "artist" ] ) )

                if key == "style":
                    # List
                    for style in item[ "style" ]:
                        if style == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "style" ] ) )

                if key == "theme":
                    # List
                    for theme in item[ "theme" ]:
                        if theme == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "theme" ] ) )

                if key == "mood":
                    # List
                    for mood in item[ "mood" ]:
                        if mood == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "mood" ] ) )

                if key == "genre":
                    # List
                    for genre in item[ "genre" ]:
                        if genre == value:
                            weight += ( ( weighting / 100 ) * percentage ) / float( len( item[ "genre" ] ) )

    if weight not in weighted.keys():
        weighted[ weight ] = [ item[ "albumid" ] ]
    else:
        weighted[ weight ].append( item[ "albumid" ] )



def buildWidget( mediaType, weighted, items ):
    count = 0
    full_liz = []

    for key in sorted( weighted.keys(), reverse = True ):
        if mediaType == "movie":
            for movieID in weighted[ key ]:
                log( "(%s) %s" %( key, items[ movieID ][ "title" ] ) )
                count += 1
                movie_widget( items[ movieID ], full_liz, count )
                if count >= 50:
                    break

        if mediaType == "episode":
            for episodeID in weighted[ key ]:
                log( "(%s) %s - %s" %( key, items[ episodeID ][ "showtitle" ], items[ episodeID ][ "label" ] ) )
                count += 1
                episode_widget( items[ episodeID ], full_liz, count )
                if count >= 50:
                    break

        if mediaType == "album":
            for albumID in weighted[ key ]:
                log( "(%s) %s - %s" %( key, items[ albumID ][ "displayartist" ], items[ albumID ][ "title" ] ) )
                count += 1
                album_widget( items[ albumID ], full_liz, count )
                if count >= 50:
                    break

        if mediaType == "pvr":
            for pvrItem in weighted[ key ]:
                log( "(%s) %s" %( key, items[ pvrItem ][ "label" ] ) )
                count += 1
                pvr_widget( items[ pvrItem ], full_liz, count, pvrItem )
                if count >= 50:
                    break

        if count >= 50:
            return full_liz

    return full_liz

def movie_widget( item, full_liz, count ):
    watched = False
    if item['playcount'] >= 1:
        watched = True

    if len(item['studio']) > 0:
        studio = item['studio'][0]
    else:
        studio = ""
    if len(item['country']) > 0:
        country = item['country'][0]
    else:
        country = ""
    #if "cast" in item:
    #    cast = self._get_cast( item['cast'] )

    # create a list item
    liz = xbmcgui.ListItem(item['title'])
    liz.setInfo( type="Video", infoLabels={ "Title": item['title'] })
    liz.setInfo( type="Video", infoLabels={ "OriginalTitle": item['originaltitle'] })
    liz.setInfo( type="Video", infoLabels={ "Year": item['year'] })
    liz.setInfo( type="Video", infoLabels={ "Genre": " / ".join(item['genre']) })
    liz.setInfo( type="Video", infoLabels={ "Studio": studio })
    liz.setInfo( type="Video", infoLabels={ "Country": country })
    liz.setInfo( type="Video", infoLabels={ "Plot": item[ "plot" ] })
    liz.setInfo( type="Video", infoLabels={ "PlotOutline": item['plotoutline'] })
    liz.setInfo( type="Video", infoLabels={ "Tagline": item['tagline'] })
    liz.setInfo( type="Video", infoLabels={ "Rating": str(float(item['rating'])) })
    liz.setInfo( type="Video", infoLabels={ "Votes": item['votes'] })
    liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa'] })
    liz.setInfo( type="Video", infoLabels={ "Director": " / ".join(item['director']) })
    if "writer" in item:
        liz.setInfo( type="Video", infoLabels={ "Writer": " / ".join(item['writer']) })
    #if "cast" in item:
    #    liz.setInfo( type="Video", infoLabels={ "Cast": cast[0] })
    #    liz.setInfo( type="Video", infoLabels={ "CastAndRole": cast[1] })
    liz.setInfo( type="Video", infoLabels={ "Trailer": item['trailer'] })
    liz.setInfo( type="Video", infoLabels={ "Playcount": item['playcount'] })
    liz.setProperty("resumetime", str(item['resume']['position']))
    liz.setProperty("totaltime", str(item['resume']['total']))

    liz.setArt(item['art'])
    liz.setThumbnailImage(item['art'].get('poster', ''))
    liz.setIconImage('DefaultVideoCover.png')
    liz.setProperty("dbid", str(item['movieid']))
    liz.setProperty("fanart_image", item['art'].get('fanart', ''))
    for key, value in item['streamdetails'].iteritems():
        for stream in value:
            liz.addStreamInfo( key, stream )
    full_liz.append((item['file'], liz, False))

def episode_widget( item, full_liz, count ):
    episode = "%.2d" % float(item['episode'])
    season = "%.2d" % float(item['season'])
    episodeno = "s%se%s" %(season,episode)
    watched = False
    if item['playcount'] >= 1:
        watched = True

    liz = xbmcgui.ListItem(item['title'])
    liz.setInfo( type="Video", infoLabels={ "Title": item['title'] })
    liz.setInfo( type="Video", infoLabels={ "Episode": item['episode'] })
    liz.setInfo( type="Video", infoLabels={ "Season": item['season'] })
    #liz.setInfo( type="Video", infoLabels={ "Studio": item['studio'][0] })
    liz.setInfo( type="Video", infoLabels={ "Premiered": item['firstaired'] })
    liz.setInfo( type="Video", infoLabels={ "Plot": item[ "plot" ] })
    liz.setInfo( type="Video", infoLabels={ "TVshowTitle": item['showtitle'] })
    liz.setInfo( type="Video", infoLabels={ "Rating": str(round(float(item['rating']),1)) })
    #liz.setInfo( type="Video", infoLabels={ "MPAA": item['mpaa'] })
    liz.setInfo( type="Video", infoLabels={ "Playcount": item['playcount'] })
    if "writer" in item:
        liz.setInfo( type="Video", infoLabels={ "Writer": " / ".join(item['writer']) })
    liz.setProperty("episodeno", episodeno)
    liz.setProperty("resumetime", str(item['resume']['position']))
    liz.setProperty("totaltime", str(item['resume']['total']))
    liz.setArt(item['art'])
    liz.setThumbnailImage(item['art'].get('thumb',''))
    liz.setIconImage('DefaultTVShows.png')
    liz.setProperty("dbid", str(item['episodeid']))
    liz.setProperty("fanart_image", item['art'].get('tvshow.fanart',''))
    for key, value in item['streamdetails'].iteritems():
        for stream in value:
            liz.addStreamInfo( key, stream )
    full_liz.append((item['file'], liz, False))

def album_widget( item, full_liz, count ):
    # create a list item
    liz = xbmcgui.ListItem(item['title'])

    rating = str(item['rating'])
    if rating == '48':
        rating = ''

    liz.setInfo( type="Music", infoLabels={ "Title": item['title'] })
    liz.setInfo( type="Music", infoLabels={ "Artist": item['artist'][0] })
    liz.setInfo( type="Music", infoLabels={ "Genre": " / ".join(item['genre']) })
    liz.setInfo( type="Music", infoLabels={ "Year": item['year'] })
    liz.setInfo( type="Music", infoLabels={ "Rating": rating })
    liz.setProperty("Album_Mood", " / ".join(item['mood']) )
    liz.setProperty("Album_Style", " / ".join(item['style']) )
    liz.setProperty("Album_Theme", " / ".join(item['theme']) )
    liz.setProperty("Album_Type", " / ".join(item['type']) )
    liz.setProperty("Album_Label", item['albumlabel'])
    liz.setProperty("Album_Description", item['description'])

    liz.setThumbnailImage(item['thumbnail'])
    liz.setIconImage('DefaultAlbumCover.png')
    liz.setProperty("fanart_image", item['fanart'])
    liz.setProperty("dbid", str(item['albumid']))

    # Path will call plugin again, with the album id
    path = "plugin://" + __addonid__ + "/?type=playalb&id=" + str( item[ 'albumid' ])

    full_liz.append( ( path, liz, False ) )

def pvr_widget( item, full_liz, count, itemID ):
    if itemID.startswith( "R" ):
        # Create a list item for recorded tv
        liz = xbmcgui.ListItem(item['title'])
        liz.setInfo( type="Video", infoLabels={ "Title": item['title'] } )
        liz.setInfo( type="Video", infoLabels={ "Genre": " / ".join(item['genre']) } )
        liz.setInfo( type="Video", infoLabels={ "Plot": item[ "plot" ] } )
        liz.setInfo( type="Video", infoLabels={ "Playcount": item['playcount'] } )
        liz.setProperty( "resumetime", str( item[ 'resume' ][ 'position' ] ) )
        liz.setProperty( "totaltime", str( item[ 'resume' ][ 'total' ] ) )

        liz.setArt(item['art'])
        liz.setThumbnailImage(item['art'].get('thumb', ''))
        liz.setIconImage('DefaultTVShows.png')

        liz.setProperty( "ChannelName", item[ "channel" ] )
        liz.setProperty( "StartTime", item[ "starttime" ] )
        liz.setProperty( "EndTime", item[ "endtime" ] )

        liz.setInfo( type="Video", infoLabels={ "ChannelName": item['channel'] })
        liz.setInfo( type="Video", infoLabels={ "Channel": item['channel'] })

        liz.setProperty( "type", "recorded" )

        if __xbmcversion__ == "13":
            path = item[ "streamurl" ]
        else:
            path = "plugin://" + __addonid__ + "/?type=playrec&id=" + str( item[ "recordingid" ] )
        full_liz.append( ( path, liz, False ) )
    else:
        # Create a list item for live tv or radio
        liz = xbmcgui.ListItem(item['label'])

        liz.setInfo( type="Video", infoLabels={ "Title": item['label'] })

        liz.setThumbnailImage(item['thumbnail'])

        if itemID.startswith( "L" ):
            liz.setIconImage('DefaultVideo.png')
        else:
            liz.setIconImage('DefaultAudio.png')

        liz.setProperty( "type", "livechannel" )

        # Now Playing
        if "broadcastnow" in item.keys():
            liz.setProperty( "StartDate", item[ "broadcastnow" ][ "starttime" ] )
            liz.setProperty( "EndDate", item[ "broadcastnow" ][ "endtime" ] )
            liz.setProperty( "Title", item[ "broadcastnow" ][ "title" ] )
            liz.setProperty( "Genre", " / ".join( item[ "broadcastnow" ][ "genre" ] ) )
            liz.setProperty( "Plot", item[ "broadcastnow" ][ "plot" ] )
            liz.setProperty( "PlotOutline", item[ "broadcastnow" ][ "plotoutline" ] )

            startTime = datetime.strptime( item[ "broadcastnow" ][ "starttime" ], "%Y-%m-%d %H:%M:%S" )
            endTime = datetime.strptime( item[ "broadcastnow" ][ "endtime" ], "%Y-%m-%d %H:%M:%S" )
            liz.setProperty( "StartTime", startTime.strftime( "%H:%S" ) )
            liz.setProperty( "EndTime", endTime.strftime( "%H:%S" ) )

        # Next Playing
        if "broadcastnext" in item.keys():
            liz.setProperty( "NextStartDate", item[ "broadcastnext" ][ "starttime" ] )
            liz.setProperty( "NextEndDate", item[ "broadcastnext" ][ "endtime" ] )
            liz.setProperty( "NextTitle", item[ "broadcastnext" ][ "title" ] )
            liz.setProperty( "NextGenre", " / ".join( item[ "broadcastnext" ][ "genre" ] ) )
            liz.setProperty( "NextPlot", item[ "broadcastnext" ][ "plot" ] )
            liz.setProperty( "NextPlotOutline", item[ "broadcastnext" ][ "plotoutline" ] )

            startTime = datetime.strptime( item[ "broadcastnext" ][ "starttime" ], "%Y-%m-%d %H:%M:%S" )
            endTime = datetime.strptime( item[ "broadcastnext" ][ "endtime" ], "%Y-%m-%d %H:%M:%S" )
            liz.setProperty( "NextStartTime", startTime.strftime( "%H:%S" ) )
            liz.setProperty( "NextEndTime", endTime.strftime( "%H:%S" ) )

        path = "plugin://" + __addonid__ + "/?type=playpvr&id=" + str( item[ "channelid" ] )
        full_liz.append( ( path, liz, False ) )

def _playingNow( type, id ):
    # Check whether we (or any client) are currently playing the media
    for key in nowPlaying:
        if nowPlaying[ key ][ 0 ] == type and int( nowPlaying[ key ][ 1 ] ) == id:
            log( "Matched %s - %s" %( type, str( id ) ) )
            return True
        return False

def shrinkJson( type, weighted, json ):
    # Shrink the whole JSON into just the items needed to build the widget
    shrunk = {}
    count = 0

    for key in sorted( weighted.keys(), reverse = True ):
        for id in weighted[ key ]:
            shrunk[ id ] = json[ id ]
            count += 1
            if count >= 50:
                break
        if count >= 50:
            break

    return shrunk

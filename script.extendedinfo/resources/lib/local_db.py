import xbmcvfs
import simplejson
from Utils import *
id_list = []
title_list = []
originaltitle_list = []


def GetXBMCArtists():
    filename = ADDON_DATA_PATH + "/XBMCartists.txt"
    if xbmcvfs.exists(filename) and time.time() - os.path.getmtime(filename) < 0:
        return read_from_file(filename)
    else:
        json_response = get_Kodi_JSON('"method": "AudioLibrary.GetArtists", "params": {"properties": ["musicbrainzartistid","thumbnail"]}')
        save_to_file(json_response, "XBMCartists", ADDON_DATA_PATH)
        return json_response


def GetSimilarArtistsInLibrary(artistid):
    from LastFM import GetSimilarById
    simi_artists = GetSimilarById(artistid)
    if simi_artists is None:
        log('Last.fm didn\'t return proper response')
        return None
    xbmc_artists = GetXBMCArtists()
    artists = []
    for (count, simi_artist) in enumerate(simi_artists):
        for (count, xbmc_artist) in enumerate(xbmc_artists["result"]["artists"]):
            if xbmc_artist['musicbrainzartistid'] != '':
                if xbmc_artist['musicbrainzartistid'] == simi_artist['mbid']:
                    artists.append(xbmc_artist)
            elif xbmc_artist['artist'] == simi_artist['name']:
                json_response = get_Kodi_JSON('"method": "AudioLibrary.GetArtistDetails", "params": {"properties": ["genre", "description", "mood", "style", "born", "died", "formed", "disbanded", "yearsactive", "instrument", "fanart", "thumbnail"], "artistid": %s}' % str(xbmc_artist['artistid']))
                item = json_response["result"]["artistdetails"]
                newartist = {"Title": item['label'],
                             "Genre": " / ".join(item['genre']),
                             "Thumb": item['thumbnail'],  # remove
                             "Fanart": item['fanart'],  # remove
                             "Art(thumb)": item['thumbnail'],
                             "Art(fanart)": item['fanart'],
                             "Description": item['description'],
                             "Born": item['born'],
                             "Died": item['died'],
                             "Formed": item['formed'],
                             "Disbanded": item['disbanded'],
                             "YearsActive": " / ".join(item['yearsactive']),
                             "Style": " / ".join(item['style']),
                             "Mood": " / ".join(item['mood']),
                             "Instrument": " / ".join(item['instrument']),
                             "LibraryPath": 'musicdb://artists/' + str(item['artistid']) + '/'}
                artists.append(newartist)
    log('%i of %i artists found in last.FM is in XBMC database' % (len(artists), len(simi_artists)))
    return artists


def GetSimilarFromOwnLibrary(dbid):
    json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["genre","director","country","year","mpaa"], "movieid":%s }' % dbid)
    if "moviedetails" in json_response['result']:
        genres = json_response['result']['moviedetails']['genre']
        json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovies", "params": {"properties": ["genre","director","mpaa","country","year"], "sort": { "method": "random" } }')
        if "movies" in json_response['result']:
            quotalist = []
            for item in json_response['result']['movies']:
                difference = abs(int(item['year']) - int(json_response['result']['moviedetails']['year']))
                hit = 0.0
                miss = 0.0
                quota = 0.0
                for genre in genres:
                    if genre in item['genre']:
                        hit += 1.0
                    else:
                        miss += 1.0
                miss += 0.00001
                if hit > 0.0:
                    quota = float(hit) / float(hit + miss)
                if genres[0] == item['genre'][0]:
                    quota += 0.3
                if difference < 3:
                    quota += 0.3
                elif difference < 6:
                    quota += 0.15
                if json_response['result']['moviedetails']['country'][0] == item['country'][0]:
                    quota += 0.4
                if json_response['result']['moviedetails']['mpaa'] == item['mpaa']:
                    quota += 0.4
                if json_response['result']['moviedetails']['director'][0] == item['director'][0]:
                    quota += 0.6
                quotalist.append((quota, item["movieid"]))
            quotalist = sorted(quotalist, key=lambda quota: quota[0], reverse=True)
            for i, list_movie in enumerate(quotalist):
                if json_response['result']['moviedetails']['movieid'] is not list_movie[1]:
                    movies = []
                    newmovie = GetMovieFromDB(list_movie[1])
                    movies.append(newmovie)
                    if i == 20:
                        break
            return movies


def get_db_movies(filter_string="", limit=10):
    props = '"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded"]'
    json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovies", "params": {%s, %s, "limits": {"end": %d}}' % (props, filter_string, limit))
    if "result" in json_response and "movies" in json_response["result"]:
        movies = []
        for item in json_response["result"]["movies"]:
            movies.append(HandleDBMovieResult(item))
        return movies


def HandleDBMovieResult(movie):
    trailer = "plugin://script.extendedinfo/?info=playtrailer&&dbid=%s" % str(movie['movieid'])
    if ADDON.getSetting("infodialog_onclick") != "false":
        path = 'plugin://script.extendedinfo/?info=action&&id=RunScript(script.extendedinfo,info=extendedinfo,dbid=%s)' % str(movie['movieid'])
    else:
        path = trailer
    if (movie['resume']['position'] and movie['resume']['total']) > 0:
        resume = "true"
        played = '%s' % int((float(movie['resume']['position']) / float(movie['resume']['total'])) * 100)
    else:
        resume = "false"
        played = '0'
    streaminfo = media_streamdetails(movie['file'].encode('utf-8').lower(), movie['streamdetails'])
    db_movie = {'Art(fanart)': movie["art"].get('fanart', ""),
                'Art(poster)': movie["art"].get('poster', ""),
                'Fanart': movie["art"].get('fanart', ""),
                'Poster': movie["art"].get('poster', ""),
                'Banner': movie["art"].get('banner', ""),
                'DiscArt': movie["art"].get('discart', ""),
                'Title': movie.get('label', ""),
                'File': movie.get('file', ""),
                'Writer': " / ".join(movie['writer']),
                'Logo': movie['art'].get("clearlogo", ""),
                'OriginalTitle': movie.get('originaltitle', ""),
                'ID': movie.get('imdbnumber', ""),
                'Path': path,
                'PercentPlayed': played,
                'Resume': resume,
                # 'SubtitleLanguage': " / ".join(subs),
                # 'AudioLanguage': " / ".join(streams),
                'Play': "",
                'DBID': str(movie['movieid']),
                'Rating': str(round(float(movie['rating']), 1)),
                'Premiered': movie.get('year', "")}
    streams = []
    for i, item in enumerate(movie['streamdetails']['audio']):
        language = item['language']
        if language not in streams and language != "und":
            streams.append(language)
            db_movie['AudioLanguage.%d' % (i + 1)] = language
            db_movie['AudioCodec.%d' % (i + 1)] = item['codec']
            db_movie['AudioChannels.%d' % (i + 1)] = str(item['channels'])
    subs = []
    for i, item in enumerate(movie['streamdetails']['subtitle']):
        language = item['language']
        if language not in subs and language != "und":
            subs.append(language)
            db_movie['SubtitleLanguage.%d' % (i + 1)] = language
    db_movie.update(streaminfo)
    return db_movie


def GetMovieFromDB(movieid):
    json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded", "imdbnumber"], "movieid":%s }' % str(movieid))
    return HandleDBMovieResult(json_response["result"]["moviedetails"])


def GetXBMCAlbums():
    json_response = get_Kodi_JSON('"method": "AudioLibrary.GetAlbums", "params": {"properties": ["title"]}')
    if "result" in json_response and "albums" in json_response['result']:
        return json_response['result']['albums']
    else:
        return []


def create_channel_list():
    json_response = get_Kodi_JSON('"method":"PVR.GetChannels","params":{"channelgroupid":"alltv", "properties": [ "thumbnail", "locked", "hidden", "channel", "lastplayed" ]}')
    if ('result' in json_response) and ("movies" in json_response["result"]):
        return json_response
    else:
        return False


def compare_with_library(onlinelist=[], library_first=True, sortkey=False):
    global id_list
    global originaltitle_list
    global title_list
    global imdb_list
    if not title_list:
        now = time.time()
        id_list = xbmc.getInfoLabel("Window(home).Property(id_list.JSON)")
        if id_list and id_list != "[]":
            id_list = simplejson.loads(id_list)
            originaltitle_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(originaltitle_list.JSON)"))
            title_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(title_list.JSON)"))
            imdb_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(imdb_list.JSON)"))
        else:
            json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovies", "params": {"properties": ["originaltitle", "imdbnumber", "file"], "sort": { "method": "none" } }')
            id_list = []
            imdb_list = []
            originaltitle_list = []
            title_list = []
            if "result" in json_response and "movies" in json_response["result"]:
                for item in json_response["result"]["movies"]:
                    id_list.append(item["movieid"])
                    imdb_list.append(item["imdbnumber"])
                    originaltitle_list.append(item["originaltitle"].lower())
                    title_list.append(item["label"].lower())
            HOME.setProperty("id_list.JSON", simplejson.dumps(id_list))
            HOME.setProperty("originaltitle_list.JSON", simplejson.dumps(originaltitle_list))
            HOME.setProperty("title_list.JSON", simplejson.dumps(title_list))
            HOME.setProperty("imdb_list.JSON", simplejson.dumps(imdb_list))
        log("create_light_movielist: " + str(now - time.time()))
    now = time.time()
    local_items = []
    remote_items = []
    for online_item in onlinelist:
        found = False
        if "imdb_id" in online_item and online_item["imdb_id"] in imdb_list:
            index = imdb_list.index(online_item["imdb_id"])
            found = True
        elif online_item["Title"].lower() in title_list:
            index = title_list.index(online_item["Title"].lower())
            found = True
        elif online_item["OriginalTitle"].lower() in originaltitle_list:
            index = originaltitle_list.index(online_item["OriginalTitle"].lower())
            found = True
        if found:
            json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["streamdetails", "resume", "year", "art", "writer", "file"], "movieid":%s }' % str(id_list[index]))
            if "result" in json_response and "moviedetails" in json_response["result"]:
                local_item = json_response['result']['moviedetails']
                try:
                    diff = abs(local_item["year"] - int(online_item["Year"]))
                    if diff > 1:
                        remote_items.append(online_item)
                        continue
                except:
                    pass
                if (local_item['resume']['position'] and local_item['resume']['total']) > 0:
                    resume = "true"
                    played = '%s' % int((float(local_item['resume']['position']) / float(local_item['resume']['total'])) * 100)
                else:
                    resume = "false"
                    played = '0'
                streaminfo = media_streamdetails(local_item['file'].encode('utf-8').lower(), local_item['streamdetails'])
                online_item["Play"] = local_item["movieid"]
                online_item["DBID"] = local_item["movieid"]
                online_item["Path"] = local_item['file']
                online_item["PercentPlayed"] = played
                online_item["Resume"] = resume
                online_item["Path"] = local_item['file']
                online_item["FilenameAndPath"] = local_item['file']
                online_item["Writer"] = " / ".join(local_item['writer'])
                online_item["Logo"] = local_item['art'].get("clearlogo", "")
                online_item["DiscArt"] = local_item['art'].get("discart", "")
                online_item["Banner"] = local_item['art'].get("banner", "")
                online_item["Poster"] = local_item['art'].get("poster", "")
                online_item["Thumb"] = local_item['art'].get("poster", "")
                online_item.update(streaminfo)
                streams = []
                for i, item in enumerate(local_item['streamdetails']['audio']):
                    language = item['language']
                    if language not in streams and language != "und":
                        streams.append(language)
                        online_item['AudioLanguage.%d' % (i + 1)] = language
                        online_item['AudioCodec.%d' % (i + 1)] = item['codec']
                        online_item['AudioChannels.%d' % (i + 1)] = str(item['channels'])
                subs = []
                for i, item in enumerate(local_item['streamdetails']['subtitle']):
                    language = item['language']
                    if language not in subs and language != "und":
                        subs.append(language)
                        online_item['SubtitleLanguage.%d' % (i + 1)] = language
                online_item['SubtitleLanguage'] = " / ".join(subs)
                online_item['AudioLanguage'] = " / ".join(streams)
                if library_first:
                    local_items.append(online_item)
                else:
                    remote_items.append(online_item)
            else:
                remote_items.append(online_item)
        else:
            remote_items.append(online_item)
    log("compare time: " + str(now - time.time()))
    if sortkey:
        return sorted(local_items, key=lambda k: k[sortkey], reverse=True) + sorted(remote_items, key=lambda k: k[sortkey], reverse=True)
    else:
        return local_items + remote_items


def CompareAlbumWithLibrary(onlinelist):
    locallist = GetXBMCAlbums()
    for online_item in onlinelist:
        for localitem in locallist:
            if online_item["name"] == localitem["title"]:
                json_response = get_Kodi_JSON('"method": "AudioLibrary.GetAlbumDetails", "params": {"properties": ["thumbnail"], "albumid":%s }' % str(localitem["albumid"]))
                album = json_response["result"]["albumdetails"]
                online_item.update({"DBID": album["albumid"]})
                online_item.update(
                    {"Path": 'XBMC.RunScript(service.skin.widgets,albumid=' + str(album["albumid"]) + ')'})
                if album["thumbnail"]:
                    online_item.update({"thumb": album["thumbnail"]})
                    online_item.update({"Icon": album["thumbnail"]})
                break
    return onlinelist


def GetMovieSetName(dbid):
    json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["setid"], "movieid":%s }"' % dbid)
    if "moviedetails" in json_response["result"]:
        dbsetid = json_response['result']['moviedetails'].get('setid', "")
        if dbsetid:
            json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieSetDetails", "params": {"setid":%s }' % dbsetid)
            return json_response['result']['setdetails'].get('label', "")
    return ""


def GetImdbIDFromDatabase(type, dbid):
    if not dbid:
        return []
    if type == "movie":
        json_response = get_Kodi_JSON('"method": "VideoLibrary.GetMovieDetails", "params": {"properties": ["imdbnumber","title", "year"], "movieid":%s }' % dbid)
        if "moviedetails" in json_response["result"]:
            return json_response['result']['moviedetails']['imdbnumber']
    elif type == "tvshow":
        json_response = get_Kodi_JSON('"method": "VideoLibrary.GetTVShowDetails", "params": {"properties": ["imdbnumber","title", "year"], "tvshowid":%s }' % dbid)
        if "result" in json_response and "tvshowdetails" in json_response["result"]:
            return json_response['result']['tvshowdetails']['imdbnumber']
    return []


def get_tvshow_id_from_db_by_episode(dbid):
    json_response = get_Kodi_JSON('"method": "VideoLibrary.GetEpisodeDetails", "params": {"properties": ["tvshowid"], "episodeid":%s }' % dbid)
    if "episodedetails" in json_response["result"]:
        tvshowid = str(json_response['result']['episodedetails']['tvshowid'])
        return GetImdbIDFromDatabase("tvshow", tvshowid)

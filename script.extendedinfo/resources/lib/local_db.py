# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcvfs
import simplejson
from Utils import *
id_list = []
title_list = []
otitle_list = []
tvshow_id_list = []
tvshow_otitle_list = []
tvshow_title_list = []
tvshow_imdb_list = []


def get_kodi_artists():
    filename = ADDON_DATA_PATH + "/XBMCartists.txt"
    if xbmcvfs.exists(filename) and time.time() - os.path.getmtime(filename) < 0:
        return read_from_file(filename)
    else:
        json_response = get_kodi_json(method="AudioLibrary.GetArtists",
                                      params='{"properties": ["musicbrainzartistid","thumbnail"]}')
        save_to_file(content=json_response,
                     filename="XBMCartists",
                     path=ADDON_DATA_PATH)
        return json_response


def get_similar_artists_from_db(artist_id):
    from LastFM import get_similar_artists
    simi_artists = get_similar_artists(artist_id)
    if simi_artists is None:
        log('Last.fm didn\'t return proper response')
        return None
    xbmc_artists = get_kodi_artists()
    artists = []
    for simi_artist in simi_artists:
        for xbmc_artist in xbmc_artists["result"]["artists"]:
            if xbmc_artist['musicbrainzartistid'] != '' and xbmc_artist['musicbrainzartistid'] == simi_artist['mbid']:
                artists.append(xbmc_artist)
            elif xbmc_artist['artist'] == simi_artist['name']:
                json_response = get_kodi_json(method="AudioLibrary.GetArtistDetails",
                                              params='{"properties": ["genre", "description", "mood", "style", "born", "died", "formed", "disbanded", "yearsactive", "instrument", "fanart", "thumbnail"], "artistid": %s}' % str(xbmc_artist['artistid']))
                item = json_response["result"]["artistdetails"]
                newartist = {'title': item['label'],
                             "Genre": " / ".join(item['genre']),
                             "thumb": item['thumbnail'],
                             "Fanart": item['fanart'],
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


def get_similar_movies_from_db(dbid):
    movie_response = get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                   params='{"properties": ["genre","director","country","year","mpaa"], "movieid":%s }' % dbid)
    if "moviedetails" not in movie_response['result']:
        return []
    comp_movie = movie_response['result']['moviedetails']
    genres = comp_movie['genre']
    json_response = get_kodi_json(method="VideoLibrary.GetMovies",
                                  params='{"properties": ["genre","director","mpaa","country","year"], "sort": { "method": "random" } }')
    if "movies" not in json_response['result']:
        return []
    quotalist = []
    for item in json_response['result']['movies']:
        diff = abs(int(item['year']) - int(comp_movie['year']))
        hit = 0.0
        miss = 0.00001
        quota = 0.0
        for genre in genres:
            if genre in item['genre']:
                hit += 1.0
            else:
                miss += 1.0
        if hit > 0.0:
            quota = float(hit) / float(hit + miss)
        if genres and item['genre'] and genres[0] == item['genre'][0]:
            quota += 0.3
        if diff < 3:
            quota += 0.3
        elif diff < 6:
            quota += 0.15
        if comp_movie['country'] and item['country'] and comp_movie['country'][0] == item['country'][0]:
            quota += 0.4
        if comp_movie['mpaa'] and item['mpaa'] and comp_movie['mpaa'] == item['mpaa']:
            quota += 0.4
        if comp_movie['director'] and item['director'] and comp_movie['director'][0] == item['director'][0]:
            quota += 0.6
        quotalist.append((quota, item["movieid"]))
    quotalist = sorted(quotalist,
                       key=lambda quota: quota[0],
                       reverse=True)
    movies = []
    for i, list_movie in enumerate(quotalist):
        if comp_movie['movieid'] is not list_movie[1]:
            newmovie = get_movie_from_db(list_movie[1])
            movies.append(newmovie)
            if i == 20:
                break
    return movies


def get_db_movies(filter_str="", limit=10):
    props = '"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded", "imdbnumber"]'
    json_response = get_kodi_json(method="VideoLibrary.GetMovies",
                                  params='{%s, %s, "limits": {"end": %d}}' % (props, filter_str, limit))
    if "result" in json_response and "movies" in json_response["result"]:
        return [handle_db_movies(item) for item in json_response["result"]["movies"]]
    else:
        return []


def get_db_tvshows(filter_str="", limit=10):
    props = '"properties": ["title", "genre", "year", "rating", "plot", "studio", "mpaa", "cast", "playcount", "episode", "imdbnumber", "premiered", "votes", "lastplayed", "fanart", "thumbnail", "file", "originaltitle", "sorttitle", "episodeguide", "season", "watchedepisodes", "dateadded", "tag", "art"]'
    json_response = get_kodi_json(method="VideoLibrary.GetTVShows",
                                  params='{%s, %s, "limits": {"end": %d}}' % (props, filter_str, limit))
    if "result" in json_response and "tvshows" in json_response["result"]:
        return [handle_db_tvshows(item) for item in json_response["result"]["tvshows"]]
    else:
        return []


def handle_db_movies(movie):
    trailer = "plugin://script.extendedinfo/?info=playtrailer&&dbid=%s" % str(movie['movieid'])
    if SETTING("infodialog_onclick") != "false":
        path = 'plugin://script.extendedinfo/?info=extendedinfo&&dbid=%s' % str(movie['movieid'])
    else:
        path = 'plugin://script.extendedinfo/?info=playmovie&&dbid=%i' % movie['movieid']
    if (movie['resume']['position'] and movie['resume']['total']) > 0:
        resume = "true"
        played = '%s' % int((float(movie['resume']['position']) / float(movie['resume']['total'])) * 100)
    else:
        resume = "false"
        played = '0'
    stream_info = media_streamdetails(movie['file'].encode('utf-8').lower(), movie['streamdetails'])
    db_movie = {'fanart': movie["art"].get('fanart', ""),
                'poster': movie["art"].get('poster', ""),
                'Banner': movie["art"].get('banner', ""),
                'clearart': movie["art"].get('clearart', ""),
                'DiscArt': movie["art"].get('discart', ""),
                'title': movie.get('label', ""),
                'File': movie.get('file', ""),
                'year': str(movie.get('year', "")),
                'writer': " / ".join(movie['writer']),
                'Logo': movie['art'].get("clearlogo", ""),
                'OriginalTitle': movie.get('originaltitle', ""),
                'imdb_id': movie.get('imdbnumber', ""),
                'path': path,
                'plot': movie.get('plot', ""),
                'director': " / ".join(movie.get('director')),
                'writer': " / ".join(movie.get('writer')),
                'PercentPlayed': played,
                'Resume': resume,
                # 'SubtitleLanguage': " / ".join(subs),
                # 'AudioLanguage': " / ".join(streams),
                'Play': "",
                'trailer': trailer,
                'dbid': str(movie['movieid']),
                'Rating': str(round(float(movie['rating']), 1))}
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
    db_movie.update(stream_info)
    return dict((k, v) for k, v in db_movie.iteritems() if v)


def handle_db_tvshows(tvshow):
    if SETTING("infodialog_onclick") != "false":
        path = 'plugin://script.extendedinfo/?info=extendedtvinfo&&dbid=%s' % str(tvshow['tvshowid'])
    else:
        path = 'plugin://script.extendedinfo/?info=action&&id=ActivateWindow(videos,videodb://tvshows/titles/%s/,return)' % str(tvshow['tvshowid'])
    db_tvshow = {'fanart': tvshow["art"].get('fanart', ""),
                 'poster': tvshow["art"].get('poster', ""),
                 'Banner': tvshow["art"].get('banner', ""),
                 'DiscArt': tvshow["art"].get('discart', ""),
                 'title': tvshow.get('label', ""),
                 'genre': " / ".join(tvshow.get('genre', "")),
                 'File': tvshow.get('file', ""),
                 'year': str(tvshow.get('year', "")),
                 'Logo': tvshow['art'].get("clearlogo", ""),
                 'OriginalTitle': tvshow.get('originaltitle', ""),
                 'imdb_id': tvshow.get('imdbnumber', ""),
                 'path': path,
                 'Play': "",
                 'dbid': str(tvshow['tvshowid']),
                 'Rating': str(round(float(tvshow['rating']), 1))}
    return dict((k, v) for k, v in db_tvshow.iteritems() if v)


def get_movie_from_db(movie_id):
    response = get_kodi_json(method="VideoLibrary.GetMovieDetails",
                             params='{"properties": ["title", "originaltitle", "votes", "playcount", "year", "genre", "studio", "country", "tagline", "plot", "runtime", "file", "plotoutline", "lastplayed", "trailer", "rating", "resume", "art", "streamdetails", "mpaa", "director", "writer", "cast", "dateadded", "imdbnumber"], "movieid":%s }' % str(movie_id))
    if "result" in response and "moviedetails" in response["result"]:
        return handle_db_movies(response["result"]["moviedetails"])
    return {}


def get_tvshow_from_db(tvshow_id):
    response = get_kodi_json(method="VideoLibrary.GetTVShowDetails",
                             params='{"properties": ["title", "genre", "year", "rating", "plot", "studio", "mpaa", "cast", "playcount", "episode", "imdbnumber", "premiered", "votes", "lastplayed", "fanart", "thumbnail", "file", "originaltitle", "sorttitle", "episodeguide", "season", "watchedepisodes", "dateadded", "tag", "art"], "tvshowid":%s }' % str(tvshow_id))
    if "result" in response and "tvshowdetails" in response["result"]:
        return handle_db_tvshows(response["result"]["tvshowdetails"])
    return {}


def get_kodi_albums():
    json_response = get_kodi_json(method="AudioLibrary.GetAlbums",
                                  params='{"properties": ["title"]}')
    if "result" in json_response and "albums" in json_response['result']:
        return json_response['result']['albums']
    else:
        return []


def create_channel_list():
    json_response = get_kodi_json(method="PVR.GetChannels",
                                  params='{"channelgroupid":"alltv", "properties": [ "thumbnail", "locked", "hidden", "channel", "lastplayed" ]}')
    if ('result' in json_response) and ("movies" in json_response["result"]):
        return json_response
    else:
        return False


def merge_with_local_movie_info(online_list=[], library_first=True, sortkey=False):
    global id_list
    global otitle_list
    global title_list
    global imdb_list
    if not title_list:
        now = time.time()
        id_list = xbmc.getInfoLabel("Window(home).Property(id_list.JSON)")
        if id_list and id_list != "[]":
            id_list = simplejson.loads(id_list)
            otitle_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(otitle_list.JSON)"))
            title_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(title_list.JSON)"))
            imdb_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(imdb_list.JSON)"))
        else:
            json_response = get_kodi_json(method="VideoLibrary.GetMovies",
                                          params='{"properties": ["originaltitle", "imdbnumber"], "sort": { "method": "none" } }')
            id_list = []
            imdb_list = []
            otitle_list = []
            title_list = []
            if "result" in json_response and "movies" in json_response["result"]:
                for item in json_response["result"]["movies"]:
                    id_list.append(item["movieid"])
                    imdb_list.append(item["imdbnumber"])
                    otitle_list.append(item["originaltitle"].lower())
                    title_list.append(item["label"].lower())
            HOME.setProperty("id_list.JSON", simplejson.dumps(id_list))
            HOME.setProperty("otitle_list.JSON", simplejson.dumps(otitle_list))
            HOME.setProperty("title_list.JSON", simplejson.dumps(title_list))
            HOME.setProperty("imdb_list.JSON", simplejson.dumps(imdb_list))
        log("create_light_movielist: " + str(now - time.time()))
    now = time.time()
    local_items = []
    remote_items = []
    for online_item in online_list:
        found = False
        if "imdb_id" in online_item and online_item["imdb_id"] in imdb_list:
            index = imdb_list.index(online_item["imdb_id"])
            found = True
        elif online_item['title'].lower() in title_list:
            index = title_list.index(online_item['title'].lower())
            found = True
        elif "OriginalTitle" in online_item and online_item["OriginalTitle"].lower() in otitle_list:
            index = otitle_list.index(online_item["OriginalTitle"].lower())
            found = True
        if found:
            local_item = get_movie_from_db(id_list[index])
            if local_item:
                try:
                    diff = abs(int(local_item["year"]) - int(online_item["year"]))
                    if diff > 1:
                        remote_items.append(online_item)
                        continue
                except:
                    pass
                online_item.update(local_item)
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
        local_items = sorted(local_items, key=lambda k: k[sortkey], reverse=True)
        remote_items = sorted(remote_items, key=lambda k: k[sortkey], reverse=True)
    return local_items + remote_items


def merge_with_local_tvshow_info(online_list=[], library_first=True, sortkey=False):
    global tvshow_id_list
    global tvshow_otitle_list
    global tvshow_title_list
    global tvshow_imdb_list
    if not tvshow_title_list:
        now = time.time()
        tvshow_id_list = xbmc.getInfoLabel("Window(home).Property(tvshow_id_list.JSON)")
        if tvshow_id_list and tvshow_id_list != "[]":
            tvshow_id_list = simplejson.loads(tvshow_id_list)
            tvshow_otitle_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(tvshow_otitle_list.JSON)"))
            tvshow_title_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(tvshow_title_list.JSON)"))
            tvshow_imdb_list = simplejson.loads(xbmc.getInfoLabel("Window(home).Property(tvshow_imdb_list.JSON)"))
        else:
            json_response = get_kodi_json(method="VideoLibrary.GetTVShows",
                                          params='{"properties": ["originaltitle", "imdbnumber"], "sort": { "method": "none" } }')
            tvshow_id_list = []
            tvshow_imdb_list = []
            tvshow_otitle_list = []
            tvshow_title_list = []
            if "result" in json_response and "tvshows" in json_response["result"]:
                for item in json_response["result"]["tvshows"]:
                    tvshow_id_list.append(item["tvshowid"])
                    tvshow_imdb_list.append(item["imdbnumber"])
                    tvshow_otitle_list.append(item["originaltitle"].lower())
                    tvshow_title_list.append(item["label"].lower())
            HOME.setProperty("tvshow_id_list.JSON", simplejson.dumps(tvshow_id_list))
            HOME.setProperty("tvshow_otitle_list.JSON", simplejson.dumps(tvshow_otitle_list))
            HOME.setProperty("tvshow_title_list.JSON", simplejson.dumps(tvshow_title_list))
            HOME.setProperty("tvshow_imdb_list.JSON", simplejson.dumps(tvshow_imdb_list))
        log("create_light_tvshowlist: " + str(now - time.time()))
    now = time.time()
    local_items = []
    remote_items = []
    for online_item in online_list:
        found = False
        if "imdb_id" in online_item and online_item["imdb_id"] in tvshow_imdb_list:
            index = tvshow_imdb_list.index(online_item["imdb_id"])
            found = True
        elif online_item['title'].lower() in tvshow_title_list:
            index = tvshow_title_list.index(online_item['title'].lower())
            found = True
        elif "OriginalTitle" in online_item and online_item["OriginalTitle"].lower() in tvshow_otitle_list:
            index = tvshow_otitle_list.index(online_item["OriginalTitle"].lower())
            found = True
        if found:
            local_item = get_tvshow_from_db(tvshow_id_list[index])
            if local_item:
                try:
                    diff = abs(int(local_item["year"]) - int(online_item["year"]))
                    if diff > 1:
                        remote_items.append(online_item)
                        continue
                except:
                    pass
                online_item.update(local_item)
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
        local_items = sorted(local_items,
                             key=lambda k: k[sortkey],
                             reverse=True)
        remote_items = sorted(remote_items,
                              key=lambda k: k[sortkey],
                              reverse=True)
    return local_items + remote_items


def compare_album_with_library(online_list):
    local_list = get_kodi_albums()
    for online_item in online_list:
        for local_item in local_list:
            if not online_item["name"] == local_item["title"]:
                continue
            json_response = get_kodi_json(method="AudioLibrary.getAlbumDetails",
                                          params='{"properties": ["thumbnail"], "albumid":%s }' % str(local_item["albumid"]))
            album = json_response["result"]["albumdetails"]
            online_item["dbid"] = album["albumid"]
            online_item["path"] = 'plugin://script.extendedinfo/?info=playalbum&&dbid=%i' % album['albumid']
            if album["thumbnail"]:
                online_item.update({"thumb": album["thumbnail"]})
                online_item.update({"Icon": album["thumbnail"]})
            break
    return online_list


def get_set_name_from_db(dbid):
    json_response = get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                  params='{"properties": ["setid"], "movieid":%s }' % dbid)
    if "result" in json_response and "moviedetails" in json_response["result"]:
        set_dbid = json_response['result']['moviedetails'].get('setid', "")
        if set_dbid:
            json_response = get_kodi_json(method="VideoLibrary.GetMovieSetDetails",
                                          params='{"setid":%s }' % set_dbid)
            return json_response['result']['setdetails'].get('label', "")
    return ""


def get_imdb_id_from_db(media_type, dbid):
    if not dbid:
        return None
    if media_type == "movie":
        json_response = get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                      params='{"properties": ["imdbnumber","title", "year"], "movieid":%s }' % dbid)
        if "result" in json_response and "moviedetails" in json_response["result"]:
            return json_response['result']['moviedetails']['imdbnumber']
    elif media_type == "tvshow":
        json_response = get_kodi_json(method="VideoLibrary.GetTVShowDetails",
                                      params='{"properties": ["imdbnumber","title", "year"], "tvshowid":%s }' % dbid)
        if "result" in json_response and "tvshowdetails" in json_response["result"]:
            return json_response['result']['tvshowdetails']['imdbnumber']
    return None


def get_tvshow_id_from_db_by_episode(dbid):
    if not dbid:
        return None
    json_response = get_kodi_json(method="VideoLibrary.GetEpisodeDetails",
                                  params='{"properties": ["tvshowid"], "episodeid":%s }' % dbid)
    if "episodedetails" in json_response["result"]:
        tvshow_dbid = str(json_response['result']['episodedetails']['tvshowid'])
        return get_imdb_id_from_db(media_type="tvshow",
                                   dbid=tvshow_dbid)
    else:
        return None

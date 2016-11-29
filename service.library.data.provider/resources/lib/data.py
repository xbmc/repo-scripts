#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This script is based on service.skin.widgets
#    Thanks to the original authors

import sys
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import library

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString
LIBRARY = library.LibraryFunctions()


def get_playlist_stats(path):
    WINDOW = xbmcgui.Window(10000)
    if ("activatewindow" in path.lower()) and ("://" in path) and ("," in path):
        if ("\"" in path):
            # remove &quot; from path (gets added by favorites)
            path = path.translate(None, '\"')
        playlistpath = path.split(",")[1]
        json_query = xbmc.executeJSONRPC('''{"jsonrpc": "2.0", "method": "Files.GetDirectory",
                                             "params": {"directory": "%s", "media": "video",
                                             "properties": ["playcount",
                                                            "resume",
                                                            "episode",
                                                            "watchedepisodes",
                                                            "tvshowid"]},
                                             "id": 1}''' % (playlistpath))
        json_response = simplejson.loads(json_query)
        if "result" not in json_response:
            return None
        if "files" not in json_response["result"]:
            return None
        played = 0
        numitems = 0
        inprogress = 0
        episodes = 0
        watchedepisodes = 0
        tvshows = []
        tvshowscount = 0
        if "files" in json_response["result"]:
            for item in json_response["result"]["files"]:
                if "type" not in item:
                    continue
                if item["type"] == "episode":
                    episodes += 1
                    if item["playcount"] > 0:
                        watchedepisodes += 1
                    if item["tvshowid"] not in tvshows:
                        tvshows.append(item["tvshowid"])
                        tvshowscount += 1
                elif item["type"] == "tvshow":
                    episodes += item["episode"]
                    watchedepisodes += item["watchedepisodes"]
                    tvshowscount += 1
                else:
                    numitems += 1
                    if "playcount" in item.keys():
                        if item["playcount"] > 0:
                            played += 1
                        if item["resume"]["position"] > 0:
                            inprogress += 1
        WINDOW.setProperty('PlaylistWatched', str(played))
        WINDOW.setProperty('PlaylistCount', str(numitems))
        WINDOW.setProperty('PlaylistTVShowCount', str(tvshowscount))
        WINDOW.setProperty('PlaylistInProgress', str(inprogress))
        WINDOW.setProperty('PlaylistUnWatched', str(numitems - played))
        WINDOW.setProperty('PlaylistEpisodes', str(episodes))
        WINDOW.setProperty('PlaylistEpisodesUnWatched', str(episodes - watchedepisodes))


def _get_cast(castData):
    listCast = []
    listCastAndRole = []
    for castmember in castData:
        listCast.append(castmember["name"])
        listCastAndRole.append((castmember["name"], castmember["role"]))
    return [listCast, listCastAndRole]


def get_actors(dbid, dbtype, full_liz):
    json_query = _get_query(dbtype, dbid)
    if json_query:
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'moviedetails' in json_query['result']:
            for item in json_query['result']['moviedetails']['cast']:
                liz = xbmcgui.ListItem(item["name"])
                liz.setLabel(item["name"])
                liz.setLabel2(item["role"])
                if "thumbnail" in item:
                    liz.setThumbnailImage(item["thumbnail"])
                liz.setIconImage('DefaultActor.png')
                full_liz.append(("", liz, False))
        elif 'result' in json_query and 'episodedetails' in json_query['result']:
            for item in json_query['result']['episodedetails']['cast']:
                liz = xbmcgui.ListItem(item["name"])
                liz.setLabel(item["name"])
                liz.setLabel2(item["role"])
                if "thumbnail" in item:
                    liz.setThumbnailImage(item["thumbnail"])
                liz.setIconImage('DefaultActor.png')
                full_liz.append(("", liz, False))

        del json_query


def _combine_by_date(liz_a, date_a, liz_b, date_b, limit, settinglimit):
    count = 0
    full_liz = liz_a[:]

    for itemIndex, itemDate in enumerate(date_b):
        added = False
        for compareIndex, compareDate in enumerate(date_a):
            if compareIndex < count or count > settinglimit:
                continue
            if itemDate > compareDate:
                full_liz.insert(count, liz_b[itemIndex])
                date_a.insert(count, itemDate)
                added = True
                break
            count += 1
        if not added and count < settinglimit:
            full_liz.append(liz_b[-1])
            date_a.append(date_b[-1])

    # Limit the results
    if limit is not -1:
        full_liz = full_liz[:limit]
    full_liz = full_liz[:settinglimit]

    return full_liz


def play_album(album):
    xbmc.executeJSONRPC('''{ "jsonrpc": "2.0", "method": "Player.Open",
                        "params": { "item": { "albumid": %d } }, "id": 1 }''' % int(album))
    # Return ResolvedUrl as failed, as we've taken care of what to play
    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())


def parse_movies(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)

    count = 0
    if json_query:
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'movies' in json_query['result']:
            for item in json_query['result']['movies']:
                watched = False
                if item['playcount'] >= 1:
                    watched = True
                if not plot_enable and not watched:
                    plot = ADDON_LANGUAGE(32014)
                else:
                    plot = item['plot']
                if len(item['studio']) > 0:
                    studio = item['studio'][0]
                else:
                    studio = ""
                if len(item['country']) > 0:
                    country = item['country'][0]
                else:
                    country = ""
                if "director" in item:
                    director = " / ".join(item['director'])
                if "writer" in item:
                    writer = " / ".join(item['writer'])
                if "cast" in item:
                    cast = _get_cast(item['cast'])

                # create a list item
                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo(type="Video", infoLabels={"Title": item['title'],
                                                      "OriginalTitle": item['originaltitle'],
                                                      "Year": item['year'],
                                                      "Genre": " / ".join(item['genre']),
                                                      "Studio": studio,
                                                      "Country": country,
                                                      "Plot": plot,
                                                      "PlotOutline": item['plotoutline'],
                                                      "Tagline": item['tagline'],
                                                      "Rating": str(float(item['rating'])),
                                                      "Votes": item['votes'],
                                                      "MPAA": item['mpaa'],
                                                      "Director": director,
                                                      "Writer": writer,
                                                      "Cast": cast[0],
                                                      "CastAndRole": cast[1],
                                                      "mediatype": "movie",
                                                      "Trailer": item['trailer'],
                                                      "Playcount": item['playcount']})
                liz.setProperty("resumetime", str(item['resume']['position']))
                liz.setProperty("totaltime", str(item['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(item['movieid']))
                liz.setProperty("imdbnumber", str(item['imdbnumber']))
                liz.setProperty("fanart_image", item['art'].get('fanart', ''))
                liz.setArt(item['art'])
                liz.setThumbnailImage(item['art'].get('poster', ''))
                liz.setIconImage('DefaultVideoCover.png')
                hasVideo = False
                for key, value in item['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': item['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((item['file'], liz, False))

                if date_type is not None:
                    date_liz.append(item[date_type])

                count += 1
                if count == limit:
                    break

        del json_query


def parse_tvshows_recommended(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None, favourites=False):
    prefix = "recommended-episodes" if not favourites else "favouriteepisodes"
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)
    if json_query:
        # First unplayed episode of recent played tvshows
        json_query = simplejson.loads(json_query)
        if "result" in json_query and 'tvshows' in json_query['result']:
            count = 0
            for item in json_query['result']['tvshows']:
                if xbmc.abortRequested:
                    break
                json_query2 = xbmcgui.Window(10000).getProperty(prefix + "-data-" + str(item['tvshowid']))
                if json_query2:
                    json_query2 = simplejson.loads(json_query2)
                    if "result" in json_query2 and json_query2['result'] is not None and 'episodes' in json_query2['result']:
                        for item2 in json_query2['result']['episodes']:
                            episode = "%.2d" % float(item2['episode'])
                            season = "%.2d" % float(item2['season'])
                            episodeno = "s%se%s" % (season, episode)
                            break
                        watched = False
                        if item2['playcount'] >= 1:
                            watched = True
                        if not plot_enable and not watched:
                            plot = ADDON_LANGUAGE(32014)
                        else:
                            plot = item2['plot']
                        if len(item['studio']) > 0:
                            studio = item['studio'][0]
                        else:
                            studio = ""
                        if "cast" in item2:
                            cast = _get_cast(item2['cast'])
                        if "director" in item2:
                            director = " / ".join(item2['director'])
                        if "writer" in item2:
                            writer = " / ".join(item2['writer'])

                        liz = xbmcgui.ListItem(item2['title'])
                        liz.setInfo(type="Video", infoLabels={"Title": item2['title'],
                                                              "Episode": item2['episode'],
                                                              "Season": item2['season'],
                                                              "Studio": studio,
                                                              "Premiered": item2['firstaired'],
                                                              "Plot": plot,
                                                              "TVshowTitle": item2['showtitle'],
                                                              "Rating": str(float(item2['rating'])),
                                                              "MPAA": item['mpaa'],
                                                              "Playcount": item2['playcount'],
                                                              "Director": director,
                                                              "Writer": writer,
                                                              "Cast": cast[0],
                                                              "CastAndRole": cast[1],
                                                              "mediatype": "episode"})
                        liz.setProperty("episodeno", episodeno)
                        liz.setProperty("resumetime", str(item2['resume']['position']))
                        liz.setProperty("totaltime", str(item2['resume']['total']))
                        liz.setProperty("type", ADDON_LANGUAGE(list_type))
                        liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart', ''))
                        liz.setProperty("dbid", str(item2['episodeid']))
                        liz.setArt(item2['art'])
                        liz.setThumbnailImage(item2['art'].get('thumb', ''))
                        liz.setIconImage('DefaultTVShows.png')
                        hasVideo = False
                        for key, value in item2['streamdetails'].iteritems():
                            for stream in value:
                                if 'video' in key:
                                    hasVideo = True
                                liz.addStreamInfo(key, stream)

                        # if duration wasnt in the streaminfo try adding the scraped one
                        if not hasVideo:
                            stream = {'duration': item2['runtime']}
                            liz.addStreamInfo("video", stream)

                        full_liz.append((item2['file'], liz, False))

                        if date_type is not None:
                            date_liz.append(item[date_type])

                        count += 1
                        if count == limit:
                            break
                if count == limit:
                    break
        del json_query


def parse_tvshows_favourite(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    return parse_tvshows_recommended(request, list_type, full_liz, usecache, plot_enable, limit, date_liz, date_type, favourites=True)


def parse_tvshows(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)
    if json_query:
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'episodes' in json_query['result']:
            count = 0
            for item in json_query['result']['episodes']:
                episode = "%.2d" % float(item['episode'])
                season = "%.2d" % float(item['season'])
                episodeno = "s%se%s" % (season, episode)
                watched = False
                if item['playcount'] >= 1:
                    watched = True
                if not plot_enable and not watched:
                    plot = ADDON_LANGUAGE(32014)
                else:
                    plot = item['plot']
                if "cast" in item:
                    cast = _get_cast(item['cast'])
                if "director" in item:
                    director = " / ".join(item['director'])
                if "writer" in item:
                    writer = " / ".join(item['writer'])

                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo(type="Video", infoLabels={"Title": item['title'],
                                                      "Episode": item['episode'],
                                                      "Season": item['season'],
                                                      "Premiered": item['firstaired'],
                                                      "Plot": plot,
                                                      "TVshowTitle": item['showtitle'],
                                                      "Rating": str(float(item['rating'])),
                                                      "Playcount": item['playcount'],
                                                      "Director": director,
                                                      "Writer": writer,
                                                      "Cast": cast[0],
                                                      "CastAndRole": cast[1],
                                                      "mediatype": "episode"})
                liz.setProperty("episodeno", episodeno)
                liz.setProperty("resumetime", str(item['resume']['position']))
                liz.setProperty("totaltime", str(item['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(item['episodeid']))
                liz.setProperty("fanart_image", item['art'].get('tvshow.fanart', ''))
                liz.setArt(item['art'])
                liz.setThumbnailImage(item['art'].get('thumb', ''))
                liz.setIconImage('DefaultTVShows.png')

                hasVideo = False
                for key, value in item['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': item['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((item['file'], liz, False))

                if date_type is not None:
                    date_liz.append(item[date_type])

                count += 1
                if count == limit:
                    break
        del json_query


def parse_song(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)

    if json_query:
        json_query = simplejson.loads(json_query)
        count = 0
        if 'result' in json_query and 'songs' in json_query['result']:
            for item in json_query['result']['songs']:
                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo(type="Music", infoLabels={"Title": item['title']})
                if item['artist']:
                    liz.setInfo(type="Music", infoLabels={"Artist": item['artist'][0],
                                                          "Genre": " / ".join(item['genre']),
                                                          "Year": item['year'],
                                                          "Rating": str(float(item['rating'])),
                                                          "Album": item['album'],
                                                          "mediatype": "song"})
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("fanart_image", item['fanart'])
                liz.setProperty("dbid", str(item['songid']))
                liz.setThumbnailImage(item['thumbnail'])
                liz.setIconImage('DefaultMusicSongs.png')
                full_liz.append((item['file'], liz, False))

                if date_type is not None:
                    date_liz.append(item[date_type])

                count += 1
                if count == limit:
                    break
        del json_query


def parse_albums(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)

    if json_query:
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'albums' in json_query['result']:
            count = 0
            for item in json_query['result']['albums']:
                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo(type="Music", infoLabels={"Title": item['title']})
                if item['artist']:
                    liz.setInfo(type="Music", infoLabels={"Artist": item['artist'][0],
                                                          "Genre": " / ".join(item['genre']),
                                                          "Year": item['year'],
                                                          "Rating": str(item['rating']),
                                                          "mediatype": "album"})
                liz.setProperty("Album_Mood", " / ".join(item['mood']))
                liz.setProperty("Album_Style", " / ".join(item['style']))
                liz.setProperty("Album_Theme", " / ".join(item['theme']))
                liz.setProperty("Album_Type", " / ".join(item['type']))
                liz.setProperty("Album_Label", item['albumlabel'])
                liz.setProperty("Album_Description", item['description'])
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("fanart_image", item['fanart'])
                liz.setProperty("dbid", str(item['albumid']))
                liz.setThumbnailImage(item['thumbnail'])
                liz.setIconImage('DefaultAlbumCover.png')

                # Path will call plugin again, with the album id
                path = sys.argv[0] + "?type=play_album&album=" + str(item['albumid'])

                if date_type is not None:
                    date_liz.append(item[date_type])

                full_liz.append((path, liz, False))
                count += 1
                if count == limit:
                    break
        del json_query


def parse_musicvideos(request, list_type, full_liz, usecache, plot_enable, limit, date_liz=None, date_type=None):
    json_query = _get_data(request, usecache)
    while json_query == "LOADING":
        xbmc.sleep(100)
        json_query = _get_data(request, usecache)

    count = 0
    if json_query:
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'musicvideos' in json_query['result']:
            for item in json_query['result']['musicvideos']:
                watched = False
                if item['playcount'] >= 1:
                    watched = True
                if len(item['studio']) > 0:
                    studio = item['studio'][0]
                else:
                    studio = ""
                if not plot_enable and not watched:
                    plot = ADDON_LANGUAGE(32014)
                else:
                    plot = item['plot']
                if "director" in item:
                    director = " / ".join(item['director'])

                # create a list item
                liz = xbmcgui.ListItem(item['title'])
                liz.setInfo(type="Video", infoLabels={"Title": item['title'],
                                                      "Year": item['year'],
                                                      "Genre": " / ".join(item['genre']),
                                                      "Studio": studio,
                                                      "Plot": plot,
                                                      "Artist": item['artist'],
                                                      "Director": director,
                                                      "Playcount": item['playcount'],
                                                      "mediatype": "musicvideo"})
                liz.setProperty("resumetime", str(item['resume']['position']))
                liz.setProperty("totaltime", str(item['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(item['musicvideoid']))
                liz.setProperty("fanart_image", item['art'].get('fanart', ''))
                liz.setArt(item['art'])
                liz.setThumbnailImage(item['art'].get('poster', ''))
                liz.setIconImage('DefaultVideoCover.png')
                hasVideo = False
                for key, value in item['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                    # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': item['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((item['file'], liz, False))

                if date_type is not None:
                    date_liz.append(item[date_type])

                count += 1
                if count == limit:
                    break

        del json_query


def parse_dbid(dbtype, dbid, full_liz):
    json_query = _get_query(dbtype, dbid)
    while json_query == "LOADING":
        xbmc.sleep(100)
    if json_query:
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'moviedetails' in json_query['result']:
            item = json_query['result']['moviedetails']
        elif 'result' in json_query and 'episodedetails' in json_query['result']:
            item = json_query['result']['episodedetails']
        elif 'result' in json_query and 'songdetails' in json_query['result']:
            item = json_query['result']['songdetails']
        # create a list item
        liz = xbmcgui.ListItem(item['label'])
        if dbtype == "movie":
            liz.setInfo(type="Video", infoLabels={"mediatype": "movie"})
        if dbtype == "episode":
            liz.setInfo(type="Video", infoLabels={"mediatype": "episode"})
        if dbtype == "song":
            liz.setInfo(type="Music", infoLabels={"mediatype": "song"})
        full_liz.append((item['file'], liz, False))

        del json_query


def _get_data(request, usecache):
    if request == "randommovies":
        return LIBRARY._fetch_random_movies(usecache)
    elif request == "recentmovies":
        return LIBRARY._fetch_recent_movies(usecache)
    elif request == "recommendedmovies":
        return LIBRARY._fetch_recommended_movies(usecache)

    elif request == "randomepisodes":
        return LIBRARY._fetch_random_episodes(usecache)
    elif request == "recentepisodes":
        return LIBRARY._fetch_recent_episodes(usecache)
    elif request == "recommendedepisodes":
        return LIBRARY._fetch_recommended_episodes(usecache)
    elif request == "favouriteepisodes":
        return LIBRARY._fetch_favourite_episodes(usecache)

    elif request == "randomalbums":
        return LIBRARY._fetch_random_albums(usecache)
    elif request == "recentalbums":
        return LIBRARY._fetch_recent_albums(usecache)
    elif request == "recommendedalbums":
        return LIBRARY._fetch_recommended_albums(usecache)

    elif request == "randomsongs":
        return LIBRARY._fetch_random_songs(usecache)

    elif request == "randommusicvideos":
        return LIBRARY._fetch_random_musicvideos(usecache)
    elif request == "recentmusicvideos":
        return LIBRARY._fetch_recent_musicvideos(usecache)


def _get_query(dbtype, dbid):
    if not dbtype:
        if xbmc.getCondVisibility("VideoPlayer.Content(movies)"):
            method = '"VideoLibrary.GetMovieDetails"'
            param = '"movieid"'
        elif xbmc.getCondVisibility("VideoPlayer.Content(episodes)"):
            method = '"VideoLibrary.GetEpisodeDetails"'
            param = '"episodeid"'
        elif xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)"):
            method = '"VideoLibrary.GetMusicVideoDetails"'
            param = '"musicvideoid"'
    else:
        if dbtype == "movie":
            method = '"VideoLibrary.GetMovieDetails"'
            param = '"movieid"'
        elif dbtype == "tvshow":
            method = '"VideoLibrary.GetTVShowDetails"'
            param = '"tvshowid"'
        elif dbtype == "episode":
            method = '"VideoLibrary.GetEpisodeDetails"'
            param = '"episodeid"'
        elif dbtype == "musicvideo":
            method = '"VideoLibrary.GetMusicVideoDetails"'
            param = '"musicvideoid"'
        elif dbtype == "song":
            method = '"AudioLibrary.GetSongDetails"'
            param = '"songid"'
    json_query = xbmc.executeJSONRPC('''{ "jsonrpc": "2.0", "method": %s,
                                                            "params": {%s: %d,
                                                            "properties": ["title", "file", "cast"]},
                                                            "id": 1 }''' % (method, param, int(dbid)))
    return json_query

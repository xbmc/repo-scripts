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
import json as simplejson
from resources.lib import library


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


def get_actors(dbid, dbtype, full_liz):
    json_query = _get_query(dbtype, dbid)
    if json_query:
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)
        if 'result' in json_query and 'moviedetails' in json_query['result']:
            cast = json_query['result']['moviedetails']['cast']
        elif 'result' in json_query and 'episodedetails' in json_query['result']:
            cast = json_query['result']['episodedetails']['cast']
        for actor in cast:
            liz = xbmcgui.ListItem(actor["name"])
            liz.setLabel(actor["name"])
            liz.setLabel2(actor["role"])
            liz.setThumbnailImage(actor.get('thumbnail', ""))
            liz.setIconImage('DefaultActor.png')
            full_liz.append(("", liz, False))

        del json_query


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
            for movie in json_query['result']['movies']:
                if "cast" in movie:
                    cast = _get_cast(movie['cast'])

                # create a list item
                liz = xbmcgui.ListItem(movie['title'])
                liz.setInfo(type="Video", infoLabels={"Title": movie['title'],
                                                      "OriginalTitle": movie['originaltitle'],
                                                      "Year": movie['year'],
                                                      "Genre": _get_joined_items(movie.get('genre', "")),
                                                      "Studio": _get_first_item(movie.get('studio', "")),
                                                      "Country": _get_first_item(movie.get('country', "")),
                                                      "Plot": _get_plot(movie['plot'], plot_enable, movie['playcount']),
                                                      "PlotOutline": movie['plotoutline'],
                                                      "Tagline": movie['tagline'],
                                                      "Rating": str(float(movie['rating'])),
                                                      "Votes": movie['votes'],
                                                      "MPAA": movie['mpaa'],
                                                      "Director": _get_joined_items(movie.get('director', "")),
                                                      "Writer": _get_joined_items(movie.get('writer', "")),
                                                      "Cast": cast[0],
                                                      "CastAndRole": cast[1],
                                                      "mediatype": "movie",
                                                      "Trailer": movie['trailer'],
                                                      "Playcount": movie['playcount']})
                liz.setProperty("resumetime", str(movie['resume']['position']))
                liz.setProperty("totaltime", str(movie['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(movie['movieid']))
                liz.setProperty("imdbnumber", str(movie['imdbnumber']))
                liz.setProperty("fanart_image", movie['art'].get('fanart', ''))
                liz.setArt(movie['art'])
                liz.setThumbnailImage(movie['art'].get('poster', ''))
                liz.setIconImage('DefaultVideoCover.png')
                hasVideo = False
                for key, value in movie['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': movie['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((movie['file'], liz, False))

                if date_type is not None:
                    date_liz.append(movie[date_type])

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
            for tvshow in json_query['result']['tvshows']:
                if xbmc.abortRequested:
                    break
                json_query2 = xbmcgui.Window(10000).getProperty(prefix + "-data-" + str(tvshow['tvshowid']))
                if json_query2:
                    json_query2 = simplejson.loads(json_query2)
                    if "result" in json_query2 and json_query2['result'] is not None and 'episodes' in json_query2['result']:
                        for episode in json_query2['result']['episodes']:
                            nEpisode = "%.2d" % float(episode['episode'])
                            nSeason = "%.2d" % float(episode['season'])
                            fEpisode = "s%se%s" % (nSeason, nEpisode)
                            break
                        if "cast" in episode:
                            cast = _get_cast(episode['cast'])
                        liz = xbmcgui.ListItem(episode['title'])
                        liz.setInfo(type="Video", infoLabels={"Title": episode['title'],
                                                              "Episode": episode['episode'],
                                                              "Season": episode['season'],
                                                              "Studio": _get_first_item(tvshow.get('studio', "")),
                                                              "Premiered": episode['firstaired'],
                                                              "Plot": _get_plot(episode['plot'], plot_enable, episode['playcount']),
                                                              "TVshowTitle": episode['showtitle'],
                                                              "Rating": str(float(episode['rating'])),
                                                              "MPAA": tvshow['mpaa'],
                                                              "Playcount": episode['playcount'],
                                                              "Director": _get_joined_items(episode.get('director', "")),
                                                              "Writer": _get_joined_items(episode.get('writer', "")),
                                                              "Cast": cast[0],
                                                              "CastAndRole": cast[1],
                                                              "mediatype": "episode"})
                        liz.setProperty("episodeno", fEpisode)
                        liz.setProperty("resumetime", str(episode['resume']['position']))
                        liz.setProperty("totaltime", str(episode['resume']['total']))
                        liz.setProperty("type", ADDON_LANGUAGE(list_type))
                        liz.setProperty("fanart_image", episode['art'].get('tvshow.fanart', ''))
                        liz.setProperty("dbid", str(episode['episodeid']))
                        liz.setArt(episode['art'])
                        liz.setThumbnailImage(episode['art'].get('thumb', ''))
                        liz.setIconImage('DefaultTVShows.png')
                        hasVideo = False
                        for key, value in episode['streamdetails'].iteritems():
                            for stream in value:
                                if 'video' in key:
                                    hasVideo = True
                                liz.addStreamInfo(key, stream)

                        # if duration wasnt in the streaminfo try adding the scraped one
                        if not hasVideo:
                            stream = {'duration': episode['runtime']}
                            liz.addStreamInfo("video", stream)

                        full_liz.append((episode['file'], liz, False))

                        if date_type is not None:
                            date_liz.append(tvshow[date_type])

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
            for episode in json_query['result']['episodes']:
                nEpisode = "%.2d" % float(episode['episode'])
                nSeason = "%.2d" % float(episode['season'])
                fEpisode = "s%se%s" % (nSeason, nEpisode)
                if "cast" in episode:
                    cast = _get_cast(episode['cast'])

                liz = xbmcgui.ListItem(episode['title'])
                liz.setInfo(type="Video", infoLabels={"Title": episode['title'],
                                                      "Episode": episode['episode'],
                                                      "Season": episode['season'],
                                                      "Premiered": episode['firstaired'],
                                                      "Plot": _get_plot(episode['plot'], plot_enable, episode['playcount']),
                                                      "TVshowTitle": episode['showtitle'],
                                                      "Rating": str(float(episode['rating'])),
                                                      "Playcount": episode['playcount'],
                                                      "Director": _get_joined_items(episode.get('director', "")),
                                                      "Writer": _get_joined_items(episode.get('writer', "")),
                                                      "Cast": cast[0],
                                                      "CastAndRole": cast[1],
                                                      "mediatype": "episode"})
                liz.setProperty("episodeno", fEpisode)
                liz.setProperty("resumetime", str(episode['resume']['position']))
                liz.setProperty("totaltime", str(episode['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(episode['episodeid']))
                liz.setProperty("fanart_image", episode['art'].get('tvshow.fanart', ''))
                liz.setArt(episode['art'])
                liz.setThumbnailImage(episode['art'].get('thumb', ''))
                liz.setIconImage('DefaultTVShows.png')

                hasVideo = False
                for key, value in episode['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': episode['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((episode['file'], liz, False))

                if date_type is not None:
                    date_liz.append(episode[date_type])

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
            for song in json_query['result']['songs']:
                liz = xbmcgui.ListItem(song['title'])
                liz.setInfo(type="Music", infoLabels={"Title": song['title']})
                if song['artist']:
                    liz.setInfo(type="Music", infoLabels={"Artist": song['artist'][0],
                                                          "Genre": _get_joined_items(song.get('genre', "")),
                                                          "Year": song['year'],
                                                          "Rating": str(float(song['rating'])),
                                                          "Album": song['album'],
                                                          "mediatype": "song"})
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("fanart_image", song['fanart'])
                liz.setProperty("dbid", str(song['songid']))
                liz.setThumbnailImage(song['thumbnail'])
                liz.setIconImage('DefaultMusicSongs.png')
                full_liz.append((song['file'], liz, False))

                if date_type is not None:
                    date_liz.append(song[date_type])

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
            for album in json_query['result']['albums']:
                liz = xbmcgui.ListItem(album['title'])
                liz.setInfo(type="Music", infoLabels={"Title": album['title']})
                if album['artist']:
                    liz.setInfo(type="Music", infoLabels={"Artist": album['artist'][0],
                                                          "Genre": _get_joined_items(album.get('genre', "")),
                                                          "Year": album['year'],
                                                          "Rating": str(album['rating']),
                                                          "mediatype": "album"})
                liz.setProperty("Album_Mood", _get_joined_items(album.get('mood', "")))
                liz.setProperty("Album_Style", _get_joined_items(album.get('style', "")))
                liz.setProperty("Album_Theme", _get_joined_items(album.get('theme', "")))
                liz.setProperty("Album_Type", _get_joined_items(album.get('type', "")))
                liz.setProperty("Album_Label", album['albumlabel'])
                liz.setProperty("Album_Description", album['description'])
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("fanart_image", album['fanart'])
                liz.setProperty("dbid", str(album['albumid']))
                liz.setThumbnailImage(album['thumbnail'])
                liz.setIconImage('DefaultAlbumCover.png')

                # Path will call plugin again, with the album id
                path = sys.argv[0] + "?type=play_album&album=" + str(album['albumid'])

                if date_type is not None:
                    date_liz.append(album[date_type])

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
            for musicvideo in json_query['result']['musicvideos']:
                # create a list item
                liz = xbmcgui.ListItem(musicvideo['title'])
                liz.setInfo(type="Video", infoLabels={"Title": musicvideo['title'],
                                                      "Year": musicvideo['year'],
                                                      "Genre": " / ".join(musicvideo['genre']),
                                                      "Studio": _get_first_item(musicvideo.get('studio', "")),
                                                      "Plot": _get_plot(musicvideo['plot'], plot_enable, musicvideo['playcount']),
                                                      "Artist": musicvideo['artist'],
                                                      "Director": _get_joined_items(musicvideo.get('director', "")),
                                                      "Playcount": musicvideo['playcount'],
                                                      "mediatype": "musicvideo"})
                liz.setProperty("resumetime", str(musicvideo['resume']['position']))
                liz.setProperty("totaltime", str(musicvideo['resume']['total']))
                liz.setProperty("type", ADDON_LANGUAGE(list_type))
                liz.setProperty("dbid", str(musicvideo['musicvideoid']))
                liz.setProperty("fanart_image", musicvideo['art'].get('fanart', ''))
                liz.setArt(musicvideo['art'])
                liz.setThumbnailImage(musicvideo['art'].get('poster', ''))
                liz.setIconImage('DefaultVideoCover.png')
                hasVideo = False
                for key, value in musicvideo['streamdetails'].iteritems():
                    for stream in value:
                        if 'video' in key:
                            hasVideo = True
                        liz.addStreamInfo(key, stream)

                    # if duration wasnt in the streaminfo try adding the scraped one
                if not hasVideo:
                    stream = {'duration': musicvideo['runtime']}
                    liz.addStreamInfo("video", stream)
                full_liz.append((musicvideo['file'], liz, False))

                if date_type is not None:
                    date_liz.append(musicvideo[date_type])

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


def _get_cast(castData):
    listCast = []
    listCastAndRole = []
    for castmember in castData:
        listCast.append(castmember["name"])
        listCastAndRole.append((castmember["name"], castmember["role"]))
    return [listCast, listCastAndRole]


def _get_plot(plot, plot_enable, watched):
    if watched >= 1:
        watched = True
    else:
        watched = False
    if not plot_enable and not watched:
        plot = ADDON_LANGUAGE(32014)
    return plot


def _get_first_item(item):
    if len(item) > 0:
        item = item[0]
    else:
        item = ""
    return item


def _get_joined_items(item):
    if len(item) > 0:
        item = " / ".join(item)
    else:
        item = ""
    return item


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


def _get_query(dbtype, dbid):
    if not dbtype:
        if xbmc.getCondVisibility("VideoPlayer.Content(movies)"):
            dbtype = 'movie'
        elif xbmc.getCondVisibility("VideoPlayer.Content(episodes)"):
            dbtype = 'episode'
        elif xbmc.getCondVisibility("VideoPlayer.Content(musicvideos)"):
            dbtype = 'musicvideo'
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

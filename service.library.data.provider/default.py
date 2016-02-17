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
import xbmcplugin
import xbmcaddon
import library

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

ADDON = xbmcaddon.Addon()
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_LANGUAGE = ADDON.getLocalizedString

PLOT_ENABLE = True
LIBRARY = library.LibraryFunctions()


def log(txt):
    message = '%s: %s' % (ADDON_NAME, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


class Main:

    def __init__(self):
        self._parse_argv()
        self.WINDOW = xbmcgui.Window(10000)
        self.SETTINGSLIMIT = int(ADDON.getSetting("limit"))
        for content_type in self.TYPE.split("+"):
            full_liz = list()
            if content_type == "randommovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                self.parse_movies('randommovies', 32004, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentmovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                self.parse_movies('recentmovies', 32005, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedmovies":
                xbmcplugin.setContent(int(sys.argv[1]), 'movies')
                self.parse_movies('recommendedmovies', 32006, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                self.parse_tvshows_recommended('recommendedepisodes', 32010, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "favouriteepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                self.parse_tvshows_favourite('favouriteepisodes', 32020, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                self.parse_tvshows('recentepisodes', 32008, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomepisodes":
                xbmcplugin.setContent(int(sys.argv[1]), 'episodes')
                self.parse_tvshows('randomepisodes', 32007, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentvideos":
                listA = []
                listB = []
                dateListA = []
                dateListB = []
                self.parse_movies('recentmovies', 32005, listA, dateListA, "dateadded")
                self.parse_tvshows('recentepisodes', 32008, listB, dateListB, "dateadded")
                full_liz = self._combine_by_date(listA, dateListA, listB, dateListB)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                self.parse_albums('randomalbums', 32016, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                self.parse_albums('recentalbums', 32017, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedalbums":
                xbmcplugin.setContent(int(sys.argv[1]), 'albums')
                self.parse_albums('recommendedalbums', 32018, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randomsongs":
                xbmcplugin.setContent(int(sys.argv[1]), 'songs')
                self.parse_song('randomsongs', 32015, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "randommusicvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
                self.parse_musicvideos('randommusicvideos', 32022, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recentmusicvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
                self.parse_musicvideos('recentmusicvideos', 32023, full_liz)
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
            elif content_type == "recommendedmusicvideos":
                xbmcplugin.setContent(int(sys.argv[1]), 'musicvideos')
            elif content_type == 'playliststats':
                lo = self.id.lower()
                if ("activatewindow" in lo) and ("://" in lo) and ("," in lo):
                    if ("\"" in lo):
                        # remove &quot; from path (gets added by favorites)
                        path = self.id.translate(None, '\"')
                    else:
                        path = self.id
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
                    self.WINDOW.setProperty('PlaylistWatched', str(played))
                    self.WINDOW.setProperty('PlaylistCount', str(numitems))
                    self.WINDOW.setProperty('PlaylistTVShowCount', str(tvshowscount))
                    self.WINDOW.setProperty('PlaylistInProgress', str(inprogress))
                    self.WINDOW.setProperty('PlaylistUnWatched', str(numitems - played))
                    self.WINDOW.setProperty('PlaylistEpisodes', str(episodes))
                    self.WINDOW.setProperty('PlaylistEpisodesUnWatched', str(episodes - watchedepisodes))
                xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)

            # Play an albums
            elif content_type == "play_album":
                self.play_album(self.ALBUM)
                return

        if not self.TYPE:
            # Show a root menu
            full_liz = list()
            items = [[32004, "randommovies"],
                     [32005, "recentmovies"],
                     [32006, "recommendedmovies"],
                     [32007, "randomepisodes"],
                     [32008, "recentepisodes"],
                     [32010, "recommendedepisodes"],
                     [32020, "favouriteepisodes"],
                     [32019, "recentvideos"],
                     [32016, "randomalbums"],
                     [32017, "recentalbums"],
                     [32018, "recommendedalbums"],
                     [32015, "randomsongs"],
                     [32022, "randommusicvideos"],
                     [32023, "recentmusicvideos"]]
            for item in items:
                liz = xbmcgui.ListItem(ADDON_LANGUAGE(item[0]), iconImage='DefaultFolder.png')
                full_liz.append(("plugin://service.library.data.provider?type=" + item[1], liz, True))
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), full_liz)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]))

    def _init_vars(self):
        self.WINDOW = xbmcgui.Window(10000)

    def parse_movies(self, request, list_type, full_liz, date_liz=None, date_type=None):
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)

        count = 0
        if json_query:
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'movies' in json_query['result']:
                for item in json_query['result']['movies']:
                    watched = False
                    if item['playcount'] >= 1:
                        watched = True
                    if not PLOT_ENABLE and not watched:
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
                    if "cast" in item:
                        cast = self._get_cast(item['cast'])

                    # create a list item
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo(type="Video", infoLabels={"Title": item['title']})
                    liz.setInfo(type="Video", infoLabels={"OriginalTitle": item['originaltitle']})
                    liz.setInfo(type="Video", infoLabels={"Year": item['year']})
                    liz.setInfo(type="Video", infoLabels={"Genre": " / ".join(item['genre'])})
                    liz.setInfo(type="Video", infoLabels={"Studio": studio})
                    liz.setInfo(type="Video", infoLabels={"Country": country})
                    liz.setInfo(type="Video", infoLabels={"Plot": plot})
                    liz.setInfo(type="Video", infoLabels={"PlotOutline": item['plotoutline']})
                    liz.setInfo(type="Video", infoLabels={"Tagline": item['tagline']})
                    liz.setInfo(type="Video", infoLabels={"Rating": str(float(item['rating']))})
                    liz.setInfo(type="Video", infoLabels={"Votes": item['votes']})
                    liz.setInfo(type="Video", infoLabels={"MPAA": item['mpaa']})
                    liz.setInfo(type="Video", infoLabels={"Director": " / ".join(item['director'])})
                    if "writer" in item:
                        liz.setInfo(type="Video", infoLabels={"Writer": " / ".join(item['writer'])})
                    if "cast" in item:
                        liz.setInfo(type="Video", infoLabels={"Cast": cast[0]})
                        liz.setInfo(type="Video", infoLabels={"CastAndRole": cast[1]})
                    liz.setInfo(type="Video", infoLabels={"Trailer": item['trailer']})
                    liz.setInfo(type="Video", infoLabels={"Playcount": item['playcount']})
                    liz.setProperty("resumetime", str(item['resume']['position']))
                    liz.setProperty("totaltime", str(item['resume']['total']))
                    liz.setProperty("type", ADDON_LANGUAGE(list_type))

                    liz.setArt(item['art'])
                    liz.setThumbnailImage(item['art'].get('poster', ''))
                    liz.setIconImage('DefaultVideoCover.png')
                    liz.setProperty("dbid", str(item['movieid']))
                    liz.setProperty("imdbnumber", str(item['imdbnumber']))
                    liz.setProperty("fanart_image", item['art'].get('fanart', ''))
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
                    if count == self.LIMIT:
                        break

            del json_query

    def parse_tvshows_favourite(self, request, list_type, full_liz, date_liz=None, date_type=None):
        return self.parse_tvshows_recommended(request, list_type, full_liz, date_liz, date_type, favourites=True)

    def parse_tvshows_recommended(self, request, list_type, full_liz, date_liz=None, date_type=None, favourites=False):
        prefix = "recommended-episodes" if not favourites else "favouriteepisodes"
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)
        if json_query:
            # First unplayed episode of recent played tvshows
            json_query = simplejson.loads(json_query)
            if "result" in json_query and 'tvshows' in json_query['result']:
                count = 0
                for item in json_query['result']['tvshows']:
                    if xbmc.abortRequested:
                        break
                    json_query2 = self.WINDOW.getProperty(prefix + "-data-" + str(item['tvshowid']))
                    if json_query2:
                        json_query2 = simplejson.loads(json_query2)
                        if "result" in json_query2 and json_query2['result'] != None and 'episodes' in json_query2['result']:
                            for item2 in json_query2['result']['episodes']:
                                episode = "%.2d" % float(item2['episode'])
                                season = "%.2d" % float(item2['season'])
                                episodeno = "s%se%s" % (season, episode)
                                break
                            watched = False
                            if item2['playcount'] >= 1:
                                watched = True
                            if not PLOT_ENABLE and not watched:
                                plot = ADDON_LANGUAGE(32014)
                            else:
                                plot = item2['plot']
                            if len(item['studio']) > 0:
                                studio = item['studio'][0]
                            else:
                                studio = ""
                            if "cast" in item2:
                                cast = self._get_cast(item2['cast'])
                            rating = str(round(float(item2['rating']), 1))
                            if "director" in item2:
                                director = " / ".join(item2['director'])
                            if "writer" in item2:
                                writer = " / ".join(item2['writer'])

                            liz = xbmcgui.ListItem(item2['title'])
                            liz.setInfo(type="Video", infoLabels={"Title": item2['title']})
                            liz.setInfo(type="Video", infoLabels={"Episode": item2['episode']})
                            liz.setInfo(type="Video", infoLabels={"Season": item2['season']})
                            liz.setInfo(type="Video", infoLabels={"Studio": studio})
                            liz.setInfo(type="Video", infoLabels={"Premiered": item2['firstaired']})
                            liz.setInfo(type="Video", infoLabels={"Plot": plot})
                            liz.setInfo(type="Video", infoLabels={"TVshowTitle": item2['showtitle']})
                            liz.setInfo(type="Video", infoLabels={"Rating": rating})
                            liz.setInfo(type="Video", infoLabels={"MPAA": item['mpaa']})
                            liz.setInfo(type="Video", infoLabels={"Playcount": item2['playcount']})
                            liz.setInfo(type="Video", infoLabels={"Director": director})
                            liz.setInfo(type="Video", infoLabels={"Writer": writer})
                            liz.setInfo(type="Video", infoLabels={"Cast": cast[0]})
                            liz.setInfo(type="Video", infoLabels={"CastAndRole": cast[1]})
                            liz.setProperty("episodeno", episodeno)
                            liz.setProperty("resumetime", str(item2['resume']['position']))
                            liz.setProperty("totaltime", str(item2['resume']['total']))
                            liz.setProperty("type", ADDON_LANGUAGE(list_type))
                            liz.setArt(item2['art'])
                            liz.setThumbnailImage(item2['art'].get('thumb', ''))
                            liz.setIconImage('DefaultTVShows.png')
                            liz.setProperty("fanart_image", item2['art'].get('tvshow.fanart', ''))
                            liz.setProperty("dbid", str(item2['episodeid']))
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
                            if count == self.LIMIT:
                                break
                    if count == self.LIMIT:
                        break
            del json_query

    def parse_tvshows(self, request, list_type, full_liz, date_liz=None, date_type=None):
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)
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
                    if not PLOT_ENABLE and not watched:
                        plot = ADDON_LANGUAGE(32014)
                    else:
                        plot = item['plot']
                    if "cast" in item:
                        cast = self._get_cast(item['cast'])
                    rating = str(round(float(item['rating']), 1))
                    if "director" in item:
                        director = " / ".join(item['director'])
                    if "writer" in item:
                        writer = " / ".join(item['writer'])

                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo(type="Video", infoLabels={"Title": item['title']})
                    liz.setInfo(type="Video", infoLabels={"Episode": item['episode']})
                    liz.setInfo(type="Video", infoLabels={"Season": item['season']})
                    liz.setInfo(type="Video", infoLabels={"Premiered": item['firstaired']})
                    liz.setInfo(type="Video", infoLabels={"Plot": plot})
                    liz.setInfo(type="Video", infoLabels={"TVshowTitle": item['showtitle']})
                    liz.setInfo(type="Video", infoLabels={"Rating": rating})
                    liz.setInfo(type="Video", infoLabels={"Playcount": item['playcount']})
                    liz.setInfo(type="Video", infoLabels={"Director": director})
                    liz.setInfo(type="Video", infoLabels={"Writer": writer})
                    liz.setInfo(type="Video", infoLabels={"Cast": cast[0]})
                    liz.setInfo(type="Video", infoLabels={"CastAndRole": cast[1]})
                    liz.setProperty("episodeno", episodeno)
                    liz.setProperty("resumetime", str(item['resume']['position']))
                    liz.setProperty("totaltime", str(item['resume']['total']))
                    liz.setProperty("type", ADDON_LANGUAGE(list_type))
                    liz.setArt(item['art'])
                    liz.setThumbnailImage(item['art'].get('thumb', ''))
                    liz.setIconImage('DefaultTVShows.png')
                    liz.setProperty("dbid", str(item['episodeid']))
                    liz.setProperty("fanart_image", item['art'].get('tvshow.fanart', ''))

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
                    if count == self.LIMIT:
                        break
            del json_query

    def parse_song(self, request, list_type, full_liz, date_liz=None, date_type=None):
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)

        if json_query:
            json_query = simplejson.loads(json_query)
            count = 0
            if 'result' in json_query and 'songs' in json_query['result']:
                for item in json_query['result']['songs']:
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo(type="Music", infoLabels={"Title": item['title']})
                    if item['artist']:
                        liz.setInfo(type="Music", infoLabels={"Artist": item['artist'][0]})
                    liz.setInfo(type="Music", infoLabels={"Genre": " / ".join(item['genre'])})
                    liz.setInfo(type="Music", infoLabels={"Year": item['year']})
                    liz.setInfo(type="Music", infoLabels={"Rating": str(float(item['rating']))})
                    liz.setInfo(type="Music", infoLabels={"Album": item['album']})
                    liz.setProperty("type", ADDON_LANGUAGE(list_type))

                    liz.setThumbnailImage(item['thumbnail'])
                    liz.setIconImage('DefaultMusicSongs.png')
                    liz.setProperty("fanart_image", item['fanart'])
                    liz.setProperty("dbid", str(item['songid']))
                    full_liz.append((item['file'], liz, False))

                    if date_type is not None:
                        date_liz.append(item[date_type])

                    count += 1
                    if count == self.LIMIT:
                        break
            del json_query

    def parse_albums(self, request, list_type, full_liz, date_liz=None, date_type=None):
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)

        if json_query:
            json_query = simplejson.loads(json_query)
            if 'result' in json_query and 'albums' in json_query['result']:
                count = 0
                for item in json_query['result']['albums']:
                    rating = str(item['rating'])
                    if rating == '48':
                        rating = ''
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo(type="Music", infoLabels={"Title": item['title']})
                    if item['artist']:
                        liz.setInfo(type="Music", infoLabels={"Artist": item['artist'][0]})
                    liz.setInfo(type="Music", infoLabels={"Genre": " / ".join(item['genre'])})
                    liz.setInfo(type="Music", infoLabels={"Year": item['year']})
                    liz.setInfo(type="Music", infoLabels={"Rating": rating})
                    liz.setProperty("Album_Mood", " / ".join(item['mood']))
                    liz.setProperty("Album_Style", " / ".join(item['style']))
                    liz.setProperty("Album_Theme", " / ".join(item['theme']))
                    liz.setProperty("Album_Type", " / ".join(item['type']))
                    liz.setProperty("Album_Label", item['albumlabel'])
                    liz.setProperty("Album_Description", item['description'])
                    liz.setProperty("type", ADDON_LANGUAGE(list_type))

                    liz.setThumbnailImage(item['thumbnail'])
                    liz.setIconImage('DefaultAlbumCover.png')
                    liz.setProperty("fanart_image", item['fanart'])
                    liz.setProperty("dbid", str(item['albumid']))

                    # Path will call plugin again, with the album id
                    path = sys.argv[0] + "?type=play_album&album=" + str(item['albumid'])

                    if date_type is not None:
                        date_liz.append(item[date_type])

                    full_liz.append((path, liz, False))
                    count += 1
                    if count == self.LIMIT:
                        break
            del json_query

    def parse_musicvideos(self, request, list_type, full_liz, date_liz=None, date_type=None):
        json_query = self._get_data(request)
        while json_query == "LOADING":
            xbmc.sleep(100)
            json_query = self._get_data(request)

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
                    if not PLOT_ENABLE and not watched:
                        plot = ADDON_LANGUAGE(32014)
                    else:
                        plot = item['plot']
                    if "director" in item:
                        director = " / ".join(item['director'])

                    # create a list item
                    liz = xbmcgui.ListItem(item['title'])
                    liz.setInfo(type="Video", infoLabels={"Title": item['title']})
                    liz.setInfo(type="Video", infoLabels={"Year": item['year']})
                    liz.setInfo(type="Video", infoLabels={"Genre": " / ".join(item['genre'])})
                    liz.setInfo(type="Video", infoLabels={"Studio": studio})
                    liz.setInfo(type="Video", infoLabels={"Plot": plot})
                    liz.setInfo(type="Video", infoLabels={"Artist": item['artist']})
                    liz.setInfo(type="Video", infoLabels={"Director": director})
                    liz.setInfo(type="Video", infoLabels={"Playcount": item['playcount']})
                    liz.setProperty("resumetime", str(item['resume']['position']))
                    liz.setProperty("totaltime", str(item['resume']['total']))
                    liz.setProperty("type", ADDON_LANGUAGE(list_type))

                    liz.setArt(item['art'])
                    liz.setThumbnailImage(item['art'].get('poster', ''))
                    liz.setIconImage('DefaultVideoCover.png')
                    liz.setProperty("dbid", str(item['musicvideoid']))
                    liz.setProperty("fanart_image", item['art'].get('fanart', ''))
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
                    if count == self.LIMIT:
                        break

            del json_query

    def play_album(self, album):
        xbmc.executeJSONRPC('''{ "jsonrpc": "2.0", "method": "Player.Open",
                            "params": { "item": { "albumid": %d } }, "id": 1 }''' % int(album))
        # Return ResolvedUrl as failed, as we've taken care of what to play
        xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())

    def _get_cast(self, castData):
        listCast = []
        listCastAndRole = []
        for castmember in castData:
            listCast.append(castmember["name"])
            listCastAndRole.append((castmember["name"], castmember["role"]))
        return [listCast, listCastAndRole]

    def _combine_by_date(self, liz_a, date_a, liz_b, date_b):
        count = 0
        full_liz = liz_a[:]

        for itemIndex, itemDate in enumerate(date_b):
            added = False
            for compareIndex, compareDate in enumerate(date_a):
                if compareIndex < count or count > self.SETTINGSLIMIT:
                    continue
                if itemDate > compareDate:
                    full_liz.insert(count, liz_b[itemIndex])
                    date_a.insert(count, itemDate)
                    added = True
                    break
                count += 1
            if not added and count < self.SETTINGSLIMIT:
                full_liz.append(liz_b[-1])
                date_a.append(date_b[-1])

        # Limit the results
        if self.LIMIT is not -1:
            full_liz = full_liz[:self.LIMIT]
        full_liz = full_liz[:self.SETTINGSLIMIT]

        return full_liz

    def _get_data(self, request):
        if request == "randommovies":
            return LIBRARY._fetch_random_movies(self.USECACHE)
        elif request == "recentmovies":
            return LIBRARY._fetch_recent_movies(self.USECACHE)
        elif request == "recommendedmovies":
            return LIBRARY._fetch_recommended_movies(self.USECACHE)

        elif request == "randomepisodes":
            return LIBRARY._fetch_random_episodes(self.USECACHE)
        elif request == "recentepisodes":
            return LIBRARY._fetch_recent_episodes(self.USECACHE)
        elif request == "recommendedepisodes":
            return LIBRARY._fetch_recommended_episodes(self.USECACHE)
        elif request == "favouriteepisodes":
            return LIBRARY._fetch_favourite_episodes(self.USECACHE)

        elif request == "randomalbums":
            return LIBRARY._fetch_random_albums(self.USECACHE)
        elif request == "recentalbums":
            return LIBRARY._fetch_recent_albums(self.USECACHE)
        elif request == "recommendedalbums":
            return LIBRARY._fetch_recommended_albums(self.USECACHE)

        elif request == "randomsongs":
            return LIBRARY._fetch_random_songs(self.USECACHE)

        elif request == "randommusicvideos":
            return LIBRARY._fetch_random_musicvideos(self.USECACHE)
        elif request == "recentmusicvideos":
            return LIBRARY._fetch_recent_musicvideos(self.USECACHE)

    def _parse_argv(self):
        try:
            params = dict(arg.split("=") for arg in sys.argv[2].split("&"))
        except:
            params = {}
        self.TYPE = params.get("?type", "")
        self.ALBUM = params.get("album", "")
        self.USECACHE = params.get("reload", False)
        self.id = params.get("id", "")
        if self.USECACHE is not False:
            self.USECACHE = True
        self.LIMIT = int(params.get("limit", "-1"))
        global PLOT_ENABLE
        PLOT_ENABLE = ADDON.getSetting("plot_enable") == 'true'
        self.RANDOMITEMS_UNPLAYED = ADDON.getSetting("randomitems_unplayed") == 'true'

log('script version %s started' % ADDON_VERSION)
Main()
log('script version %s stopped' % ADDON_VERSION)

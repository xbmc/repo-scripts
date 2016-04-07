# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import json
import itertools
import KodiJson
import Utils
import addon
import time

PLUGIN_BASE = "plugin://script.extendedinfo/?info="
MOVIE_PROPS = ["title", "genre", "year", "rating", "director", "trailer",
               "tagline", "plot", "plotoutline", "originaltitle", "lastplayed",
               "playcount", "writer", "studio", "mpaa", "cast", "country",
               "imdbnumber", "runtime", "set", "showlink", "streamdetails",
               "top250", "votes", "file", "sorttitle",
               "resume", "setid", "dateadded", "tag", "art", "userrating", "ratings"]
TV_PROPS = ["title", "genre", "year", "rating", "plot",
            "studio", "mpaa", "cast", "playcount", "episode",
            "imdbnumber", "premiered", "votes", "lastplayed",
            "file", "originaltitle",
            "sorttitle", "episodeguide", "season", "watchedepisodes",
            "dateadded", "tag", "art", "userrating", "ratings", "runtime"]


class LocalDB(object):

    def __init__(self, *args, **kwargs):
        self.info = {}
        self.artists = []
        self.albums = []

    def get_artists(self):
        """
        get list of artists from db (limited metadata)
        """
        self.artists = KodiJson.get_artists(properties=["musicbrainzartistid", "thumbnail"])
        return self.artists

    def get_similar_artists(self, artist_id):
        """
        get list of artists from db which are similar to artist with *artist_id
        based on LastFM online data
        """
        import LastFM
        simi_artists = LastFM.get_similar_artists(artist_id)
        if simi_artists is None:
            Utils.log('Last.fm didn\'t return proper response')
            return None
        if not self.artists:
            self.artists = self.get_artists()
        artists = []
        for simi_artist, kodi_artist in itertools.product(simi_artists, self.artists):
            if kodi_artist['musicbrainzartistid'] and kodi_artist['musicbrainzartistid'] == simi_artist['mbid']:
                artists.append(kodi_artist)
            elif kodi_artist['artist'] == simi_artist['name']:
                data = Utils.get_kodi_json(method="AudioLibrary.GetArtistDetails",
                                           params={"properties": ["genre", "description", "mood", "style", "born", "died", "formed", "disbanded", "yearsactive", "instrument", "fanart", "thumbnail"], "artistid": kodi_artist['artistid']})
                item = data["result"]["artistdetails"]
                artwork = {"thumb": item['thumbnail'],
                           "fanart": item['fanart']}
                artists.append({"label": item['label'],
                                "artwork": artwork,
                                "title": item['label'],
                                "genre": " / ".join(item['genre']),
                                "artist_description": item['description'],
                                "userrating": item['userrating'],
                                "born": item['born'],
                                "died": item['died'],
                                "formed": item['formed'],
                                "disbanded": item['disbanded'],
                                "yearsactive": " / ".join(item['yearsactive']),
                                "style": " / ".join(item['style']),
                                "mood": " / ".join(item['mood']),
                                "instrument": " / ".join(item['instrument']),
                                "librarypath": 'musicdb://artists/%s/' % item['artistid']})
        Utils.log('%i of %i artists found in last.FM are in Kodi database' % (len(artists), len(simi_artists)))
        return artists

    def get_similar_movies(self, dbid):
        """
        get list of movies from db which are similar to movie with *dbid
        based on metadata-centric ranking
        """
        movie = Utils.get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                    params={"properties": ["genre", "director", "country", "year", "mpaa"], "movieid": dbid})
        if "moviedetails" not in movie['result']:
            return []
        comp_movie = movie['result']['moviedetails']
        genres = comp_movie['genre']
        data = Utils.get_kodi_json(method="VideoLibrary.GetMovies",
                                   params={"properties": ["genre", "director", "mpaa", "country", "year"], "sort": {"method": "random"}})
        if "movies" not in data['result']:
            return []
        quotalist = []
        for item in data['result']['movies']:
            item["mediatype"] = "movie"
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
                newmovie = self.get_movie(list_movie[1])
                movies.append(newmovie)
                if i == 20:
                    break
        return movies

    def get_movies(self, limit=10):
        """
        get list of movies with length *limit from db
        """
        data = Utils.get_kodi_json(method="VideoLibrary.GetMovies",
                                   params={"properties": MOVIE_PROPS, "limits": {"end": limit}})
        if "result" in data and "movies" in data["result"]:
            return [self.handle_movies(item) for item in data["result"]["movies"]]
        else:
            return []

    def get_tvshows(self, limit=10):
        """
        get list of tvshows with length *limit from db
        """
        data = Utils.get_kodi_json(method="VideoLibrary.GetTVShows",
                                   params={"properties": TV_PROPS, "limits": {"end": limit}})
        if "result" not in data or "tvshows" not in data["result"]:
            return []
        return [self.handle_tvshows(item) for item in data["result"]["tvshows"]]

    def handle_movies(self, movie):
        """
        convert movie data to listitems
        """
        trailer = PLUGIN_BASE + "playtrailer&&dbid=%s" % str(movie['movieid'])
        if addon.setting("infodialog_onclick") != "false":
            path = PLUGIN_BASE + 'extendedinfo&&dbid=%s' % str(movie['movieid'])
        else:
            path = PLUGIN_BASE + 'playmovie&&dbid=%i' % movie['movieid']
        if (movie['resume']['position'] and movie['resume']['total']) > 0:
            resume = "true"
            played = '%s' % int((float(movie['resume']['position']) / float(movie['resume']['total'])) * 100)
        else:
            resume = "false"
            played = '0'
        db_movie = Utils.ListItem(label=movie.get('label'),
                                  path=path)
        db_movie.set_infos({'title': movie.get('label'),
                            'file': movie.get('file'),
                            'year': str(movie.get('year')),
                            'writer': " / ".join(movie['writer']),
                            'mediatype': "movie",
                            'set': movie.get("set"),
                            'setid': movie.get("setid"),
                            'imdbnumber': movie.get("imdbnumber"),
                            'userrating': movie.get('userrating'),
                            'trailer': trailer,
                            'rating': str(round(float(movie['rating']), 1)),
                            'director': " / ".join(movie.get('director')),
                            'writer': " / ".join(movie.get('writer')),
                            # "tag": " / ".join(movie['tag']),
                            "genre": " / ".join(movie['genre']),
                            'plot': movie.get('plot'),
                            'originaltitle': movie.get('originaltitle')})
        db_movie.set_properties({'imdb_id': movie.get('imdbnumber'),
                                 'percentplayed': played,
                                 'resume': resume,
                                 'dbid': str(movie['movieid'])})
        db_movie.set_artwork(movie['art'])
        db_movie.set_videoinfos(movie['streamdetails']["video"])
        db_movie.set_audioinfos(movie['streamdetails']["audio"])
        stream_info = Utils.media_streamdetails(movie['file'].encode('utf-8').lower(),
                                                movie['streamdetails'])
        db_movie.update_properties(stream_info)
        db_movie.set_cast(movie.get("cast"))
        return db_movie

    def handle_tvshows(self, tvshow):
        """
        convert tvshow data to listitems
        """
        if addon.setting("infodialog_onclick") != "false":
            path = PLUGIN_BASE + 'extendedtvinfo&&dbid=%s' % tvshow['tvshowid']
        else:
            path = PLUGIN_BASE + 'action&&id=ActivateWindow(videos,videodb://tvshows/titles/%s/,return)' % tvshow['tvshowid']
        db_tvshow = Utils.ListItem(label=tvshow.get("label"),
                                   path=path)
        db_tvshow.set_infos({'title': tvshow.get('label'),
                             'genre': " / ".join(tvshow.get('genre')),
                             'rating': str(round(float(tvshow['rating']), 1)),
                             'mediatype': "tvshow",
                             'mpaa': tvshow.get("mpaa"),
                             'votes': tvshow.get("votes"),
                             'playcount': tvshow.get("playcount"),
                             'imdbnumber': tvshow.get("imdbnumber"),
                             # "tag": " / ".join(movie['tag']),
                             'year': str(tvshow.get('year')),
                             'originaltitle': tvshow.get('originaltitle')})
        db_tvshow.set_properties({'imdb_id': tvshow.get('imdbnumber'),
                                  'file': tvshow.get('file'),
                                  'watchedepisodes': tvshow.get('watchedepisodes'),
                                  'totalepisodes': tvshow.get('episode'),
                                  'dbid': tvshow['tvshowid']})
        db_tvshow.set_artwork(tvshow['art'])
        db_tvshow.set_cast(tvshow.get("cast"))
        return db_tvshow

    def get_movie(self, movie_id):
        """
        get info from db for movie with *movie_id
        """
        response = Utils.get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                       params={"properties": MOVIE_PROPS, "movieid": movie_id})
        if "result" in response and "moviedetails" in response["result"]:
            return self.handle_movies(response["result"]["moviedetails"])
        return {}

    def get_tvshow(self, tvshow_id):
        """
        get info from db for tvshow with *tvshow_id
        """
        response = Utils.get_kodi_json(method="VideoLibrary.GetTVShowDetails",
                                       params={"properties": TV_PROPS, "tvshowid": tvshow_id})
        if "result" in response and "tvshowdetails" in response["result"]:
            return self.handle_tvshows(response["result"]["tvshowdetails"])
        return {}

    def get_albums(self):
        """
        get a list of all albums from db
        """
        data = Utils.get_kodi_json(method="AudioLibrary.GetAlbums",
                                   params={"properties": ["title"]})
        if "result" not in data or "albums" not in data['result']:
            return []
        return data['result']['albums']

    def get_compare_info(self, media_type="movie", items=None):
        """
        fetches info needed for the locally-available check
        Caches some info as window properties.
        Hacky, but by far fastest way to cache between sessions
        """
        infos = ["ids", "imdbs", "otitles", "titles"]
        if not self.info.get(media_type):
            self.info[media_type] = {}
            dct = self.info[media_type]
            # now = time.time()
            dct["ids"] = addon.get_global("%s_ids.JSON" % media_type)
            if dct["ids"] and dct["ids"] != "[]":
                dct["ids"] = json.loads(dct["ids"])
                dct["otitles"] = json.loads(addon.get_global("%s_otitles.JSON" % media_type))
                dct["titles"] = json.loads(addon.get_global("%s_titles.JSON" % media_type))
                dct["imdbs"] = json.loads(addon.get_global("%s_imdbs.JSON" % media_type))
            else:
                for info in infos:
                    dct[info] = []
                for item in items:
                    dct["ids"].append(item["%sid" % media_type])
                    dct["imdbs"].append(item["imdbnumber"])
                    dct["otitles"].append(item["originaltitle"].lower())
                    dct["titles"].append(item["label"].lower())
                for info in infos:
                    addon.set_global("%s_%s.JSON" % (media_type, info), json.dumps(dct[info]))

            self.info[media_type] = dct

    def merge_with_local(self, media_type, items, library_first=True, sortkey=False):
        """
        merge *items from online sources with local db info (and sort)
        works for movies and tvshows
        """
        get_list = KodiJson.get_movies if media_type == "movie" else KodiJson.get_tvshows
        self.get_compare_info(media_type,
                              get_list(["originaltitle", "imdbnumber"]))
        local_items = []
        remote_items = []
        info = self.info[media_type]
        for item in items:
            index = False
            imdb_id = item.get_property("imdb_id")
            title = item.get_info("title").lower()
            otitle = item.get_info("originaltitle").lower()
            if "imdb_id" in item.get_properties() and imdb_id in info["imdbs"]:
                index = info["imdbs"].index(imdb_id)
            elif "title" in item.get_infos() and title in info["titles"]:
                index = info["titles"].index(title)
            elif "originaltitle" in item.get_infos() and otitle in info["otitles"]:
                index = info["otitles"].index(otitle)
            if index:
                get_info = self.get_movie if media_type == "movie" else self.get_tvshow
                local_item = get_info(info["ids"][index])
                if local_item:
                    try:
                        diff = abs(int(local_item.get_info("year")) - int(item.get_info("year")))
                        if diff > 1:
                            remote_items.append(item)
                            continue
                    except Exception:
                        pass
                    item.update_from_listitem(local_item)
                    if library_first:
                        local_items.append(item)
                        continue
            remote_items.append(item)
        if sortkey:
            local_items = sorted(local_items,
                                 key=lambda k: k.get_info(sortkey),
                                 reverse=True)
            remote_items = sorted(remote_items,
                                  key=lambda k: k.get_info(sortkey),
                                  reverse=True)
        return local_items + remote_items

    def compare_album_with_library(self, online_list):
        """
        merge *albums from online sources with local db info
        """
        if not self.albums:
            self.albums = self.get_albums()
        for item in online_list:
            for local_item in self.albums:
                if not item["name"] == local_item["title"]:
                    continue
                data = Utils.get_kodi_json(method="AudioLibrary.getAlbumDetails",
                                           params={"properties": ["thumbnail"], "albumid": local_item["albumid"]})
                album = data["result"]["albumdetails"]
                item["dbid"] = album["albumid"]
                item["path"] = PLUGIN_BASE + 'playalbum&&dbid=%i' % album['albumid']
                if album["thumbnail"]:
                    item.update({"thumb": album["thumbnail"]})
                break
        return online_list

    def get_set_name(self, dbid):
        """
        get name of set for movie with *dbid
        """
        data = Utils.get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                   params={"properties": ["setid"], "movieid": dbid})
        if "result" not in data or "moviedetails" not in data["result"]:
            return None
        set_dbid = data['result']['moviedetails'].get('setid')
        if set_dbid:
            data = Utils.get_kodi_json(method="VideoLibrary.GetMovieSetDetails",
                                       params={"setid": set_dbid})
            return data['result']['setdetails'].get('label')

    def get_imdb_id(self, media_type, dbid):
        if not dbid:
            return None
        if media_type == "movie":
            data = Utils.get_kodi_json(method="VideoLibrary.GetMovieDetails",
                                       params={"properties": ["imdbnumber", "title", "year"], "movieid": dbid})
            if "result" in data and "moviedetails" in data["result"]:
                return data['result']['moviedetails']['imdbnumber']
        elif media_type == "tvshow":
            data = Utils.get_kodi_json(method="VideoLibrary.GetTVShowDetails",
                                       params={"properties": ["imdbnumber", "title", "year"], "tvshowid": dbid})
            if "result" in data and "tvshowdetails" in data["result"]:
                return data['result']['tvshowdetails']['imdbnumber']
        return None

    def get_tvshow_id_by_episode(self, dbid):
        if not dbid:
            return None
        data = Utils.get_kodi_json(method="VideoLibrary.GetEpisodeDetails",
                                   params={"properties": ["tvshowid"], "episodeid": dbid})
        if "episodedetails" not in data["result"]:
            return None
        return self.get_imdb_id(media_type="tvshow",
                                dbid=str(data['result']['episodedetails']['tvshowid']))

local_db = LocalDB()

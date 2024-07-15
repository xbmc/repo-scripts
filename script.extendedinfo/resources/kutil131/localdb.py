# Copyright (C) 2016 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import itertools
import json

from resources.kutil131 import ItemList, VideoItem, addon, kodijson, utils
from resources.kutil131.abs_last_fm import AbstractLastFM

PLUGIN_BASE = "plugin://script.extendedinfo/?info="
MOVIE_PROPS = ["title", "genre", "year", "rating", "director", "trailer",
               "tagline", "plot", "plotoutline", "originaltitle", "lastplayed",
               "playcount", "writer", "studio", "mpaa", "cast", "country",
               "imdbnumber", "runtime", "set", "showlink", "streamdetails",
               "top250", "votes", "file", "sorttitle",
               "resume", "setid", "dateadded", "tag", "art", "userrating",
               "ratings", "uniqueid", "premiered"]
TV_PROPS = ["title", "genre", "year", "rating", "plot",
            "studio", "mpaa", "cast", "playcount", "episode",
            "imdbnumber", "premiered", "votes", "lastplayed",
            "file", "originaltitle",
            "sorttitle", "episodeguide", "season", "watchedepisodes",
            "dateadded", "tag", "art", "userrating", "ratings", "uniqueid", "runtime"]


class LocalDB:

    def __init__(self, last_fm: AbstractLastFM, *args, **kwargs):
        """

        :param last_fm: reference to implementation of AbstractLastFM
        :param args:
        :param kwargs:
        """
        self.info = {}
        self.artists = []
        self.albums = []
        self.last_fm = last_fm
        if last_fm is None:
            self.last_fm = AbstractLastFM()

    def get_artists(self):
        """
        get list of artists from db (limited metadata)
        """
        self.artists = kodijson.get_artists(properties=["musicbrainzartistid", "thumbnail"])
        return self.artists

    def get_similar_artists(self, artist_id):
        """
        get list of artists from db which are similar to artist with *artist_id
        based on LastFM online data
        """
        simi_artists = self.last_fm.get_similar_artists(artist_id)
        if simi_artists is None:
            utils.log('Last.fm didn\'t return proper response')
            return None
        if not self.artists:
            self.artists = self.get_artists()
        artists = ItemList(content_type="artists")
        for simi_artist, kodi_artist in itertools.product(simi_artists, self.artists):
            if kodi_artist['musicbrainzartistid'] and kodi_artist['musicbrainzartistid'] == simi_artist['mbid']:
                artists.append(kodi_artist)
            elif kodi_artist['artist'] == simi_artist['name']:
                data = kodijson.get_json(method="AudioLibrary.GetArtistDetails",
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
        utils.log('%i of %i artists found in last.FM are in Kodi database' % (len(artists), len(simi_artists)))
        return artists

    def get_similar_movies(self, dbid):
        """
        get list of movies from db which are similar to movie with *dbid
        based on metadata-centric ranking
        """
        movie = kodijson.get_json(method="VideoLibrary.GetMovieDetails",
                                  params={"properties": ["genre", "director", "country", "year", "mpaa"], "movieid": dbid})
        if "moviedetails" not in movie['result']:
            return []
        comp_movie = movie['result']['moviedetails']
        genres = comp_movie['genre']
        data = kodijson.get_json(method="VideoLibrary.GetMovies",
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
        movies = ItemList(content_type="movies")
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
        data = kodijson.get_json(method="VideoLibrary.GetMovies",
                                 params={"properties": MOVIE_PROPS, "limits": {"end": limit}})
        if "result" not in data or "movies" not in data["result"]:
            return []
        return ItemList(content_type="movies",
                        items=[self.handle_movie(item) for item in data["result"]["movies"]])

    def get_tvshows(self, limit=10):
        """
        get list of tvshows with length *limit from db
        """
        data = kodijson.get_json(method="VideoLibrary.GetTVShows",
                                 params={"properties": TV_PROPS, "limits": {"end": limit}})
        if "result" not in data or "tvshows" not in data["result"]:
            return []
        return ItemList(content_type="movies",
                        items=[self.handle_tvshow(item) for item in data["result"]["tvshows"]])

    def handle_movie(self, movie:dict) -> VideoItem:
        """
        convert movie data to listitems
        """
        trailer = PLUGIN_BASE + "playtrailer&&dbid=%s" % movie['movieid']
        if addon.setting("infodialog_onclick") != "false":
            path = PLUGIN_BASE + 'extendedinfo&&dbid=%s' % movie['movieid']
        else:
            path = PLUGIN_BASE + 'playmovie&&dbid=%i' % movie['movieid']
        resume = movie['resume']
        if (resume['position'] and resume['total']) > 0:
            resumable = "true"
            played = int((float(resume['position']) / float(resume['total'])) * 100)
        else:
            resumable = "false"
            played = 0
        db_movie = VideoItem(label=movie.get('label'),
                             path=path)
        db_movie.set_infos({'title': movie.get('label'),
                            'dbid': movie['movieid'],
                            'file': movie.get('file'),
                            'year': movie.get('year'),
                            'premiered' : movie.get('premiered'),
                            'tagline': movie.get('tagline'),
                            'writer': " / ".join(movie['writer']),
                            'mediatype': "movie",
                            'set': movie.get("set"),
                            'playcount': movie.get("playcount"),
                            'setid': movie.get("setid"),
                            'top250': movie.get("top250"),
                            'imdbnumber': movie.get("uniqueid", {}).get("imdb", ""),
                            'userrating': movie.get('userrating'),
                            'trailer': trailer,
                            'rating': round(float(movie['rating']), 1),
                            'director': " / ".join(movie.get('director')),
                            #'writer': " / ".join(movie.get('writer')),
                            #"tag": " / ".join(movie['tag']),
                            'tag': movie.get('tag'),
                            "genre": " / ".join(movie['genre']),
                            'plot': movie.get('plot'),
                            'plotoutline': movie.get('plotoutline'),
                            'studio': " / ".join(movie.get('studio')),
                            'mpaa': movie.get('mpaa'),
                            'originaltitle': movie.get('originaltitle')})
        db_movie.set_properties({'imdb_id': movie.get('uniqueid').get('imdb', ''),
                                 'showlink': " / ".join(movie['showlink']),
                                 'set': movie.get("set"),
                                 'setid': movie.get("setid"),
                                 'percentplayed': played,
                                 'resume': resumable})
        db_movie.set_artwork(movie['art'])
        db_movie.set_videoinfos(movie['streamdetails']["video"])
        db_movie.set_audioinfos(movie['streamdetails']["audio"])
        stream_info = media_streamdetails(movie['file'].lower(),
                                          movie['streamdetails'])
        db_movie.update_properties(stream_info)
        db_movie.set_cast(movie.get("cast"))
        return db_movie

    def handle_tvshow(self, tvshow):
        """
        convert tvshow data to listitems
        """
        if addon.setting("infodialog_onclick") != "false":
            path = PLUGIN_BASE + 'extendedtvinfo&&dbid=%s' % tvshow['tvshowid']
        else:
            path = PLUGIN_BASE + 'action&&id=ActivateWindow(videos,videodb://tvshows/titles/%s/,return)' % tvshow['tvshowid']
        db_tvshow = VideoItem(label=tvshow.get("label"),
                              path=path)
        db_tvshow.set_infos({'title': tvshow.get('label'),
                             'dbid': tvshow['tvshowid'],
                             'genre': " / ".join(tvshow.get('genre')),
                             'rating': round(float(tvshow['rating']), 1),
                             'mediatype': "tvshow",
                             'mpaa': tvshow.get("mpaa"),
                             'plot': tvshow.get("plot"),
                             'votes': tvshow.get("votes"),
                             'studio': " / ".join(tvshow.get('studio')),
                             'premiered': tvshow.get("premiered"),
                             'playcount': tvshow.get("playcount"),
                             'imdbnumber': tvshow.get("imdbnumber"),
                             'userrating': tvshow.get("userrating"),
                             'duration': tvshow.get("duration"),
                             # "tag": " / ".join(movie['tag']),
                             'year': tvshow.get('year'),
                             'originaltitle': tvshow.get('originaltitle')})
        db_tvshow.set_properties({'imdb_id': tvshow.get('imdbnumber'),
                                  'file': tvshow.get('file'),
                                  'watchedepisodes': tvshow.get('watchedepisodes'),
                                  'totalepisodes': tvshow.get('episode')})
        db_tvshow.set_artwork(tvshow['art'])
        db_tvshow.set_cast(tvshow.get("cast"))
        return db_tvshow

    def get_movie(self, movie_id) -> VideoItem:
        """
        get info from db for movie with *movie_id
        """
        response = kodijson.get_json(method="VideoLibrary.GetMovieDetails",
                                     params={"properties": MOVIE_PROPS, "movieid": movie_id})
        if "result" in response and "moviedetails" in response["result"]:
            return self.handle_movie(response["result"]["moviedetails"])
        return {}

    def get_tvshow(self, tvshow_id):
        """
        get info from db for tvshow with *tvshow_id
        """
        response = kodijson.get_json(method="VideoLibrary.GetTVShowDetails",
                                     params={"properties": TV_PROPS, "tvshowid": tvshow_id})
        if "result" in response and "tvshowdetails" in response["result"]:
            return self.handle_tvshow(response["result"]["tvshowdetails"])
        return {}

    def get_albums(self):
        """
        get a list of all albums from db
        """
        data = kodijson.get_json(method="AudioLibrary.GetAlbums",
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
        get_list = kodijson.get_movies if media_type == "movie" else kodijson.get_tvshows
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
        return ItemList(content_type=media_type + "s",
                        items=local_items + remote_items)

    def compare_album_with_library(self, online_list):
        """
        merge *albums from online sources with local db info
        """
        if not self.albums:
            self.albums = self.get_albums()
        for item in online_list:
            for local_item in self.albums:
                if not item.get_info("title") == local_item["title"]:
                    continue
                data = kodijson.get_json(method="AudioLibrary.getAlbumDetails",
                                         params={"properties": ["thumbnail"], "albumid": local_item["albumid"]})
                album = data["result"]["albumdetails"]
                item.set_info("dbid", album["albumid"])
                item.set_path(PLUGIN_BASE + 'playalbum&&dbid=%i' % album['albumid'])
                if album["thumbnail"]:
                    item.update_artwork({"thumb": album["thumbnail"]})
                break
        return online_list

    def get_set_name(self, dbid):
        """
        get name of set for movie with *dbid
        """
        data = kodijson.get_json(method="VideoLibrary.GetMovieDetails",
                                 params={"properties": ["setid"], "movieid": dbid})
        if "result" not in data or "moviedetails" not in data["result"]:
            return None
        set_dbid = data['result']['moviedetails'].get('setid')
        if set_dbid:
            data = kodijson.get_json(method="VideoLibrary.GetMovieSetDetails",
                                     params={"setid": set_dbid})
            return data['result']['setdetails'].get('label')

    def get_artist_mbid(self, dbid):
        """
        get mbid of artist with *dbid
        """
        data = kodijson.get_json(method="MusicLibrary.GetArtistDetails",
                                 params={"properties": ["musicbrainzartistid"], "artistid": dbid})
        mbid = data['result']['artistdetails'].get('musicbrainzartistid')
        return mbid if mbid else None

    def get_imdb_id(self, media_type, dbid):
        if not dbid:
            return None
        if media_type == "movie":
            data = kodijson.get_json(method="VideoLibrary.GetMovieDetails",
                                     params={"properties": ["uniqueid", "title", "year"], "movieid": int(dbid)})
            if "result" in data and "moviedetails" in data["result"]:
                try:
                    return data['result']['moviedetails']['uniqueid']['imdb']
                except KeyError:
                    return None
        elif media_type == "tvshow":
            data = kodijson.get_json(method="VideoLibrary.GetTVShowDetails",
                                     params={"properties": ["uniqueid", "title", "year"], "tvshowid": int(dbid)})
            if "result" in data and "tvshowdetails" in data["result"]:
                try:
                    return data['result']['tvshowdetails']['uniqueid']['imdb']
                except KeyError:
                    return None
        return None

    def get_tmdb_id(self, media_type, dbid):
        if not dbid:
            return None
        if media_type == "movie":
            data = kodijson.get_json(method="VideoLibrary.GetMovieDetails",
                                     params={"properties": ["uniqueid", "title", "year"], "movieid": int(dbid)})
            if "result" in data and "moviedetails" in data["result"]:
                return data['result']['moviedetails']['uniqueid'].get('tmdb', None)
        elif media_type == "tvshow":
            data = kodijson.get_json(method="VideoLibrary.GetTVShowDetails",
                                     params={"properties": ["uniqueid", "title", "year"], "tvshowid": int(dbid)})
            if "result" in data and "tvshowdetails" in data["result"]:
                return data['result']['tvshowdetails']['uniqueid'].get('tmdb', None)
        return None

    def get_tvshow_id_by_episode(self, dbid):
        if not dbid:
            return None
        data = kodijson.get_json(method="VideoLibrary.GetEpisodeDetails",
                                 params={"properties": ["tvshowid"], "episodeid": dbid})
        if "episodedetails" not in data["result"]:
            return None
        return self.get_imdb_id(media_type="tvshow",
                                dbid=str(data['result']['episodedetails']['tvshowid']))


def media_streamdetails(filename, streamdetails):
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    if video:
        # see StreamDetails.cpp
        if video[0]['width'] + video[0]['height'] == 0:
            info['VideoResolution'] = ""
        elif video[0]['width'] <= 720 and video[0]['height'] <= 480:
            info['VideoResolution'] = "480"
        elif video[0]['width'] <= 768 and video[0]['height'] <= 576:
            info['VideoResolution'] = "576"
        elif video[0]['width'] <= 960 and video[0]['height'] <= 544:
            info['VideoResolution'] = "540"
        elif video[0]['width'] <= 1280 and video[0]['height'] <= 720:
            info['VideoResolution'] = "720"
        elif video[0]['width'] <= 1920 and video[0]['height'] <= 1080:
            info['VideoResolution'] = "1080"
        elif video[0]['width'] * video[0]['height'] >= 6000000:
            info['VideoResolution'] = "4K"
        else:
            info['videoresolution'] = ""
        info['VideoCodec'] = str(video[0]['codec'])
        info["VideoAspect"] = select_aspectratio(video[0]['aspect'])
        info["VideoHdrType"] = video[0].get('hdrtype', '')
    if audio:
        info['AudioCodec'] = audio[0]['codec']
        info['AudioChannels'] = audio[0]['channels']
        streams = []
        for i, item in enumerate(audio, start=1):
            language = item['language']
            if language in streams or language == "und":
                continue
            streams.append(language)
            streaminfo = {'AudioLanguage.%d' % i: language,
                          'AudioCodec.%d' % i: item["codec"],
                          'AudioChannels.%d' % i: str(item['channels'])}
            info.update(streaminfo)
        subs = []
        for i, item in enumerate(streamdetails['subtitle'], start=1):
            language = item['language']
            if language in subs or language == "und":
                continue
            subs.append(language)
            info.update({'SubtitleLanguage.%d' % i: language})
    return info


def select_aspectratio(aspect):
    # see StreamDetails.cpp
    aspect = float(aspect)
    if aspect < 1.3499:  # sqrt(1.33*1.37)
        return "1.33"
    elif aspect < 1.5080:  # sqrt(1.37*1.66)
        return "1.37"
    elif aspect < 1.7190:  # sqrt(1.66*1.78)
        return "1.66"
    elif aspect < 1.8147:  # sqrt(1.78*1.85)
        return "1.78"
    elif aspect < 2.0174:  # sqrt(1.85*2.20)
        return "1.85"
    elif aspect < 2.2738:  # sqrt(2.20*2.35)
        return "2.20"
    elif aspect < 2.3749:  # sqrt(2.35*2.40)
        return "2.35"
    elif aspect < 2.4739:  # sqrt(2.40*2.55)
        return "2.40"
    elif aspect < 2.6529:  # sqrt(2.55*2.76)
        return "2.55"
    else:
        return "2.76"

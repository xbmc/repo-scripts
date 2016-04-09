# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import re
import urllib2
import urllib
import json
from functools32 import lru_cache

import xbmc
import xbmcgui

import Utils
import addon
from LocalDB import local_db
from WindowManager import wm

TMDB_KEY = '34142515d9d23817496eeb4ff1d223d0'
POSTER_SIZES = ["w92", "w154", "w185", "w342", "w500", "w780", "original"]
LOGO_SIZES = ["w45", "w92", "w154", "w185", "w300", "w500", "original"]
BACKDROP_SIZES = ["w300", "w780", "w1280", "original"]
PROFILE_SIZES = ["w45", "w185", "h632", "original"]
STILL_SIZES = ["w92", "w185", "w300", "original"]
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-agent': 'XBMC/16.0 ( phil65@kodi.tv )'
}
IMAGE_BASE_URL = "http://image.tmdb.org/t/p/"
POSTER_SIZE = "w500"
include_adult = addon.setting("include_adults").lower()
if addon.bool_setting("use_https"):
    URL_BASE = "https://api.themoviedb.org/3/"
else:
    URL_BASE = "http://api.themoviedb.org/3/"

ALL_MOVIE_PROPS = "account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating"
ALL_TV_PROPS = "account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos"
ALL_ACTOR_PROPS = "tv_credits,movie_credits,combined_credits,images,tagged_images"
ALL_SEASON_PROPS = "videos,images,external_ids,credits"
ALL_EPISODE_PROPS = "account_states,credits,external_ids,images,rating,videos"

PLUGIN_BASE = "plugin://script.extendedinfo/?info="

release_types = {1: "Premiere",
                 2: "Theatrical (limited)",
                 3: "Theatrical",
                 4: "Digital",
                 5: "Physical",
                 6: "TV"}

genders = {1: addon.LANG(32095),
           2: addon.LANG(32094)}


class SettingsMonitor(xbmc.Monitor):

    def __init__(self):
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        addon.reload_addon()
        username = addon.setting("tmdb_username")
        password = addon.setting("tmdb_password")
        if username and password:
            global Login
            Login = LoginProvider(username=username,
                                  password=password)
        if wm.active_dialog:
            wm.active_dialog.close()
            wm.active_dialog.logged_in = Login.check_login(cache_days=0)
            wm.active_dialog.doModal()


class LoginProvider(object):

    def __init__(self, *args, **kwargs):
        self.session_id = None
        self.request_token = None
        self.account_id = None
        self.monitor = SettingsMonitor()
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

    def check_login(self, cache_days=9999):
        if self.username:
            return(bool(self.get_session_id(cache_days)))
        return False

    def get_account_id(self):
        '''
        returns TMDB account id
        '''
        if self.account_id:
            return self.account_id
        self.session_id = self.get_session_id()
        response = get_data(url="account",
                            params={"session_id": self.session_id},
                            cache_days=999999)
        if not response:
            return None
        self.account_id = response.get("id")
        return self.account_id

    @lru_cache(maxsize=128)
    def get_guest_session_id(self):
        '''
        returns guest session id for TMDB
        '''
        response = get_data(url="authentication/guest_session/new",
                            cache_days=999999)
        if not response or "guest_session_id" not in response:
            return None
        return str(response["guest_session_id"])

    def get_session_id(self, cache_days=9999):
        '''
        returns session id for TMDB Account
        '''
        if self.session_id:
            return self.session_id
        self.request_token = self.auth_request_token(cache_days=cache_days)
        self.session_id = self.start_new_session(cache_days=cache_days)
        if self.session_id:
            return self.session_id
        self.session_id = self.start_new_session(cache_days=0)
        Utils.notify("login failed")
        return None

    def start_new_session(self, cache_days=0):
        response = get_data(url="authentication/session/new",
                            params={"request_token": self.request_token},
                            cache_days=cache_days)
        if response and "success" in response:
            self.session_id = str(response["session_id"])
            return self.session_id

    def auth_request_token(self, cache_days=9999):
        '''
        returns request token, is used to get session_id
        '''
        if self.request_token:
            return self.request_token
        response = get_data(url="authentication/token/new",
                            cache_days=999999)
        self.request_token = response["request_token"]
        params = {"request_token": self.request_token,
                  "username": self.username,
                  "password": self.password}
        response = get_data(url="authentication/token/validate_with_login",
                            params=params,
                            cache_days=cache_days)
        if response and response.get("success"):
            return response["request_token"]


def set_rating_prompt(media_type, media_id, dbid=None):
    if not media_type or not media_id:
        return False
    rating = xbmcgui.Dialog().select(heading=addon.LANG(32129),
                                     list=[str(float(i * 0.5)) for i in xrange(1, 21)])
    if rating == -1:
        return False
    if dbid:
        db_rating = round((rating + 1) / 2)
        if media_type == "movie":
            Utils.get_kodi_json(method="VideoLibrary.SetMovieDetails",
                                params={"movieid": dbid, "userrating": db_rating})
        elif media_type == "tv":
            Utils.get_kodi_json(method="VideoLibrary.SetTVShowDetails",
                                params={"tvshowid": dbid, "userrating": db_rating})
        elif media_type == "episode":
            Utils.get_kodi_json(method="VideoLibrary.SetEpisodeDetails",
                                params={"episodeid": dbid, "userrating": db_rating})
    set_rating(media_type=media_type,
               media_id=media_id,
               rating=(float(rating) * 0.5) + 0.5)
    return True


def set_rating(media_type, media_id, rating):
    '''
    media_type: movie, tv or episode
    media_id: tmdb_id / episode ident array
    rating: ratung value (0.5-10.0, 0.5 steps)
    '''
    params = {}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    else:
        params["guest_session_id"] = Login.get_guest_session_id()
    if media_type == "episode":
        if not media_id[1]:
            media_id[1] = "0"
        url = "tv/%s/season/%s/episode/%s/rating" % (media_id[0], media_id[1], media_id[2])
    else:
        url = "%s/%s/rating" % (media_type, media_id)
    # request.get_method = lambda: 'DELETE'
    results = send_request(url=url,
                           params=params,
                           values={"value": "%.1f" % rating})
    if results:
        Utils.notify(addon.NAME, results["status_message"])


def send_request(url, params, values, delete=False):
    params["api_key"] = TMDB_KEY
    params = {k: v for k, v in params.items() if v}
    params = {k: unicode(v).encode('utf-8') for k, v in params.iteritems()}
    url = "%s%s?%s" % (URL_BASE, url, urllib.urlencode(params))
    Utils.log(url)
    request = urllib2.Request(url=url,
                              data=json.dumps(values),
                              headers=HEADERS)
    if delete:
        request.get_method = lambda: 'DELETE'
    try:
        response = urllib2.urlopen(request, timeout=5).read()
    except urllib2.HTTPError as err:
        if err.code == 401:
            Utils.notify("Error", "Not authorized.")
        return None
    return json.loads(response)


def change_fav_status(media_id=None, media_type="movie", status="true"):
    params = {"session_id": Login.get_session_id()}
    values = {"media_type": "%s" % media_type,
              "media_id": media_id,
              "favorite": status}
    if not params["session_id"]:
        Utils.notify("Could not get session id")
        return None
    results = send_request(url="account/%s/favorite" % Login.get_account_id(),
                           params=params,
                           values=values)
    if results:
        Utils.notify(addon.NAME, results["status_message"])


def create_list(list_name):
    '''
    creates new list on TMDB with name *list_name
    returns newly created list id
    '''
    values = {'name': '%s' % list_name,
              'description': 'List created by ExtendedInfo Script for Kodi.'}
    results = send_request(url="list",
                           params={"session_id": Login.get_session_id()},
                           values=values)
    if results:
        Utils.notify(addon.NAME, results["status_message"])
    return results["list_id"]


def remove_list(list_id):
    results = send_request(url="list/%s" % list_id,
                           params={"session_id": Login.get_session_id()},
                           values={'media_id': list_id},
                           delete=True)
    if results:
        Utils.notify(addon.NAME, results["status_message"])
    return results["list_id"]


def change_list_status(list_id, movie_id, status):
    method = "add_item" if status else "remove_item"
    results = send_request(url="list/%s/%s" % (list_id, method),
                           params={"session_id": Login.get_session_id()},
                           values={'media_id': movie_id})
    if results:
        Utils.notify(addon.NAME, results["status_message"])


def get_account_lists(cache_time=0):
    '''
    returns movie lists for TMDB user
    '''
    session_id = Login.get_session_id()
    account_id = Login.get_account_id()
    if not session_id or not account_id:
        return []
    response = get_data(url="account/%s/lists" % (account_id),
                        params={"session_id": session_id},
                        cache_days=cache_time)
    return response["results"]


def get_certification_list(media_type):
    response = get_data(url="certification/%s/list" % media_type,
                        cache_days=999999)
    return response.get("certifications")


def merge_with_cert_desc(input_list, media_type):
    cert_list = get_certification_list(media_type)
    for item in input_list:
        iso = item.get_property("iso_3166_1").upper()
        if iso not in cert_list:
            continue
        hit = Utils.dictfind(lst=cert_list[iso],
                             key="certification",
                             value=item.get_property("certification"))
        if hit:
            item.set_property("meaning", hit["meaning"])
    return input_list


def handle_multi_search(results):
    listitems = []
    for item in results:
        if item["media_type"] == "movie":
            listitems.append(handle_movies([item])[0])
        elif item["media_type"] == "tvshow":
            listitems.append(handle_tvshows([item])[0])
        elif item["media_type"] == "person":
            listitems.append(handle_people([item])[0])
    return listitems


def handle_movies(results, local_first=True, sortkey="year"):
    response = get_data(url="genre/movie/list",
                        params={"language": addon.setting("LanguageID")},
                        cache_days=30)
    ids = [item["id"] for item in response["genres"]]
    labels = [item["name"] for item in response["genres"]]
    movies = []
    path = 'extendedinfo&&id=%s' if addon.bool_setting("infodialog_onclick") else "playtrailer&&id=%s"
    for movie in results:
        genres = [labels[ids.index(id_)] for id_ in movie.get("genre_ids", []) if id_ in ids]
        item = Utils.ListItem(label=movie.get('title'),
                              path=PLUGIN_BASE + path % movie.get("id"))
        release_date = movie.get('release_date')
        item.set_infos({'title': movie.get('title'),
                        'originaltitle': movie.get('original_title', ""),
                        'mediatype': "movie",
                        'country': movie.get('original_language'),
                        'plot': movie.get('overview'),
                        'Trailer': "%splaytrailer&&id=%s" % (PLUGIN_BASE, movie.get("id")),
                        'genre': " / ".join([i for i in genres if i]),
                        'votes': movie.get('vote_count'),
                        'year': Utils.get_year(release_date),
                        'rating': round(movie['vote_average'], 1) if movie.get('vote_average') else "",
                        'userrating': movie.get('rating'),
                        'premiered': release_date})
        item.set_properties({'id': movie.get("id"),
                             'popularity': movie.get('popularity'),
                             'credit_id': movie.get('credit_id'),
                             'character': movie.get('character'),
                             'job': movie.get('job'),
                             'department': movie.get('department')})
        item.set_artwork(get_image_urls(poster=movie.get("poster_path"),
                                        fanart=movie.get("backdrop_path")))
        movies.append(item)
    return local_db.merge_with_local(media_type="movie",
                                     items=movies,
                                     library_first=local_first,
                                     sortkey=sortkey)


def handle_tvshows(results, local_first=True, sortkey="year"):
    tvshows = []
    response = get_data(url="genre/tv/list",
                        params={"language": addon.setting("LanguageID")},
                        cache_days=30)
    ids = [item["id"] for item in response["genres"]]
    labels = [item["name"] for item in response["genres"]]
    for tv in results:
        tmdb_id = tv.get("id")
        genres = [labels[ids.index(id_)] for id_ in tv.get("genre_ids", []) if id_ in ids]
        duration = ""
        if "episode_run_time" in tv:
            if len(tv["episode_run_time"]) > 1:
                duration = "%i - %i" % (min(tv["episode_run_time"]), max(tv["episode_run_time"]))
            elif len(tv["episode_run_time"]) == 1:
                duration = "%i" % (tv["episode_run_time"][0])
        newtv = Utils.ListItem(label=tv.get('name'),
                               path=PLUGIN_BASE + 'extendedtvinfo&&id=%s' % tmdb_id)
        newtv.set_infos({'originaltitle': tv.get('original_name', ""),
                         'title': tv.get('name'),
                         'duration': duration,
                         'genre': " / ".join([i for i in genres if i]),
                         'country': tv.get('original_language'),
                         'plot': tv.get("overview"),
                         'year': Utils.get_year(tv.get('first_air_date')),
                         'mediatype': "tvshow",
                         'rating': round(tv['vote_average'], 1) if tv.get("vote_average") else "",
                         'userrating': tv.get('rating'),
                         'votes': tv.get('vote_count'),
                         'premiered': tv.get('first_air_date')})
        newtv.set_properties({'id': tmdb_id,
                              'character': tv.get('character'),
                              'popularity': tv.get('popularity'),
                              'credit_id': tv.get('credit_id'),
                              'totalepisodes': tv.get('number_of_episodes'),
                              'totalseasons': tv.get('number_of_seasons')})
        newtv.set_artwork(get_image_urls(poster=tv.get("poster_path"),
                                         fanart=tv.get("backdrop_path")))
        tvshows.append(newtv)
    tvshows = local_db.merge_with_local(media_type="tvshow",
                                        items=tvshows,
                                        library_first=local_first,
                                        sortkey=sortkey)
    return tvshows


def handle_episodes(results):
    listitems = []
    for item in results:
        title = Utils.clean_text(item.get("name"))
        if not title:
            title = u"%s %s" % (addon.LANG(20359), item.get('episode_number'))
        listitem = {'label': title}
        listitem = Utils.ListItem(label=title,
                                  artwork=get_image_urls(still=item.get("still_path")))
        listitem.set_infos({'mediatype': "episode",
                            'title': title,
                            'premiered': item.get('air_date'),
                            'episode': item.get('episode_number'),
                            'season': item.get('season_number'),
                            'userrating': item.get('rating'),
                            'plot': Utils.clean_text(item.get('overview')),
                            'rating': round(item['vote_average'], 1) if item.get('vote_average') else "",
                            'votes': item.get('vote_count')})
        listitem.set_properties({'id': item.get('id'),
                                 'production_code': item.get('production_code')})
        listitems.append(listitem)
    return listitems


def handle_misc(results):
    listitems = []
    for item in results:
        listitem = Utils.ListItem(label=Utils.clean_text(item.get('name')),
                                  path="plugin://script.extendedinfo?info=listmovies&---id=%s" % item.get('id'),
                                  artwork=get_image_urls(poster=item.get("poster_path")))
        listitem.set_infos({'year': Utils.get_year(item.get('release_date')),
                            'premiered': item.get('release_date'),
                            'plot': Utils.clean_text(item.get('description'))})
        listitem.set_properties({'certification': item.get('certification', "") + item.get('rating', ""),
                                 'item_count': item.get('item_count'),
                                 'favorite_count': item.get('favorite_count'),
                                 'iso_3166_1': item.get('iso_3166_1', "").lower(),
                                 'author': item.get('author'),
                                 'content': Utils.clean_text(item.get('content')),
                                 'id': item.get('id'),
                                 'url': item.get('url')})
        listitems.append(listitem)
    return listitems


def handle_seasons(results):
    listitems = []
    for item in results:
        season = item.get('season_number')
        listitem = Utils.ListItem(label=addon.LANG(20381) if season == 0 else u"%s %s" % (addon.LANG(20373), season),
                                  properties={'id': item.get('id')},
                                  artwork=get_image_urls(poster=item.get("poster_path")))
        listitem.set_infos({'mediatype': "season",
                            'season': season,
                            'premiered': item.get('air_date'),
                            'year': Utils.get_year(item.get('air_date'))})
        listitems.append(listitem)
    return listitems


def handle_videos(results):
    listitems = []
    for item in results:
        listitem = Utils.ListItem(label=item.get('name'),
                                  size=item.get('size'),
                                  artwork={'thumb': "http://i.ytimg.com/vi/%s/0.jpg" % item.get('key')})
        listitem.set_properties({'iso_639_1': item.get('iso_639_1'),
                                 'type': item.get('type'),
                                 'key': item.get('key'),
                                 'youtube_id': item.get('key'),
                                 'site': item.get('site'),
                                 'id': item.get('id')})
        listitems.append(listitem)
    return listitems


def handle_people(results):
    people = []
    for item in results:
        person = Utils.ListItem(label=item['name'],
                                path="%sextendedactorinfo&&id=%s" % (PLUGIN_BASE, item['id']),
                                infos={'mediatype': "artist"},
                                artwork=get_image_urls(profile=item.get("profile_path")))
        person.set_properties({'adult': item.get('adult'),
                               'alsoknownas': " / ".join(item.get('also_known_as', [])),
                               'biography': Utils.clean_text(item.get('biography')),
                               'birthday': item.get('birthday'),
                               'age': Utils.calculate_age(item.get('birthday'), item.get('deathday')),
                               'character': item.get('character'),
                               'department': item.get('department'),
                               'job': item.get('job'),
                               'id': item['id'],
                               'cast_id': item.get('cast_id'),
                               'credit_id': item.get('credit_id'),
                               'deathday': item.get('deathday'),
                               'placeofbirth': item.get('place_of_birth'),
                               'homepage': item.get('homepage')})
        people.append(person)
    return people


def handle_images(results):
    images = []
    for item in results:
        image = Utils.ListItem(artwork=get_image_urls(poster=item.get("file_path")))
        image.set_properties({'aspectratio': item['aspect_ratio'],
                              'vote_average': item.get("vote_average"),
                              'iso_639_1': item.get("iso_639_1")})
        if item.get("media"):
            image.set_infos({'title': item["media"].get("title")})
            if item["media"].get("poster_path"):
                image.update_artwork({'mediaposter': IMAGE_BASE_URL + POSTER_SIZE + item["media"].get("poster_path")})
        images.append(image)
    return images


def handle_companies(results):
    companies = []
    for item in results:
        company = Utils.ListItem(label=item['name'],
                                 infos={'plot': item['description']})
        company.set_properties({'parent_company': item['parent_company'],
                                'headquarters': item['headquarters'],
                                'homepage': item['homepage'],
                                'id': item['id'],
                                'logo_path': item['logo_path']})
        companies.append(company)
    return companies


def search_company(company_name):
    regex = re.compile('\(.+?\)')
    company_name = regex.sub('', company_name)
    params = {"query": company_name}
    response = get_data(url="search/company",
                        params=params,
                        cache_days=10)
    if response and "results" in response:
        return response["results"]
    else:
        Utils.log("Could not find company ID for %s" % company_name)
        return ""


def multi_search(search_str):
    params = {"query": search_str}
    response = get_data(url="search/multi",
                        params=params,
                        cache_days=1)
    if response and "results" in response:
        return response["results"]


def get_person_info(person_label, skip_dialog=False):
    if not person_label:
        return False
    params = {"query": person_label.split(" / ")[0],
              "include_adult": include_adult}
    response = get_data(url="search/person",
                        params=params,
                        cache_days=30)
    if not response or "results" not in response:
        return False
    people = [i for i in response["results"] if i["name"] == person_label]
    if len(people) > 1 and not skip_dialog:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        listitem, index = wm.open_selectdialog(listitems=handle_people(people))
        if index >= 0:
            return people[index]
    elif people:
        return people[0]
    elif response["results"]:
        return response["results"][0]
    return False


def get_keyword_id(keyword):
    params = {"query": keyword,
              "include_adult": include_adult}
    response = get_data(url="search/keyword",
                        params=params,
                        cache_days=30)
    if not response or not response.get("results"):
        Utils.log("could not find Keyword ID")
        return False
    if len(response["results"]) > 1:
        names = [item["name"] for item in response["results"]]
        selection = xbmcgui.Dialog().select(addon.LANG(32114), names)
        if selection > -1:
            return response["results"][selection]
    elif response["results"]:
        return response["results"][0]


def get_set_id(set_name):
    params = {"query": set_name.replace("[", "").replace("]", "").replace("Kollektion", "Collection"),
              "language": addon.setting("LanguageID")}
    response = get_data(url="search/collection",
                        params=params,
                        cache_days=14)
    if not response or not response.get("results"):
        return ""
    return response["results"][0]["id"]


def get_data(url="", params=None, cache_days=14):
    params = params if params else {}
    params["api_key"] = TMDB_KEY
    params = {k: v for k, v in params.items() if v}
    params = {k: unicode(v).encode('utf-8') for k, v in params.items()}
    url = "%s%s?%s" % (URL_BASE, url, urllib.urlencode(params))
    return Utils.get_JSON_response(url, cache_days, "TheMovieDB")


def get_company_data(company_id):
    if not company_id:
        return []
    response = get_data(url="company/%s/movies" % (company_id),
                        cache_days=30)
    if not response or not response.get("results"):
        return []
    return handle_movies(response["results"])


def get_credit_info(credit_id):
    if not credit_id:
        return []
    params = {"language": addon.setting("LanguageID")}
    return get_data(url="credit/%s" % (credit_id),
                    params=params,
                    cache_days=30)


def get_account_props(states):
    return {"FavButton_Label": addon.LANG(32155) if states.get("favorite") else addon.LANG(32154),
            "favorite": "True" if states.get("favorite") else "",
            "rated": states["rated"]["value"] if states["rated"] else "",
            "watchlist": states["watchlist"] if "watchlist" in states else ""}


def get_image_urls(poster=None, still=None, fanart=None, profile=None):
    images = {}
    if poster:
        images["poster"] = IMAGE_BASE_URL + "w500" + poster
        images["poster_original"] = IMAGE_BASE_URL + "original" + poster
        images["original"] = IMAGE_BASE_URL + "original" + poster
        images["poster_small"] = IMAGE_BASE_URL + "w342" + poster
        images["thumb"] = IMAGE_BASE_URL + "w342" + poster
    if still:
        images["thumb"] = IMAGE_BASE_URL + "w300" + still
        images["still"] = IMAGE_BASE_URL + "w300" + still
        images["still_original"] = IMAGE_BASE_URL + "original" + still
        images["still_small"] = IMAGE_BASE_URL + "w185" + still
    if fanart:
        images["fanart"] = IMAGE_BASE_URL + "w1280" + fanart
        images["fanart_original"] = IMAGE_BASE_URL + "original" + fanart
        images["original"] = IMAGE_BASE_URL + "original" + fanart
        images["fanart_small"] = IMAGE_BASE_URL + "w780" + fanart
    if profile:
        images["poster"] = IMAGE_BASE_URL + "w500" + profile
        images["poster_original"] = IMAGE_BASE_URL + "original" + profile
        images["poster_small"] = IMAGE_BASE_URL + "w342" + profile
        images["thumb"] = IMAGE_BASE_URL + "w342" + profile
    return images


def get_movie_tmdb_id(imdb_id=None, name=None, dbid=None):
    if dbid and (int(dbid) > 0):
        movie_id = local_db.get_imdb_id("movie", dbid)
        if movie_id:
            Utils.log("IMDB Id from local DB: %s" % (movie_id))
            return movie_id
    if imdb_id:
        params = {"external_source": "imdb_id",
                  "language": addon.setting("LanguageID")}
        response = get_data(url="find/tt%s" % (imdb_id.replace("tt", "")),
                            params=params)
        if response and response["movie_results"]:
            return response["movie_results"][0]["id"]
    return search_media(name) if name else None


def get_show_tmdb_id(tvdb_id=None, source="tvdb_id"):
    params = {"external_source": source,
              "language": addon.setting("LanguageID")}
    response = get_data(url="find/%s" % (tvdb_id),
                        params=params)
    if response and response["tv_results"]:
        return response["tv_results"][0]["id"]
    else:
        Utils.notify("TVShow Info not available.")
        return None


def get_trailer(movie_id):
    response = get_full_movie(movie_id)
    if response and "videos" in response and response['videos']['results']:
        return response['videos']['results'][0]['key']
    Utils.notify("Could not get trailer")
    return ""


def extended_movie_info(movie_id=None, dbid=None, cache_time=14):
    if not movie_id:
        return None
    params = {"append_to_response": ALL_MOVIE_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    info = get_data(url="movie/%s" % (movie_id),
                        params=params,
                        cache_days=cache_time)
    if not info:
        Utils.notify("Could not get movie information")
        return {}
    mpaa = ""
    studio = [i["name"] for i in info["production_companies"]]
    authors = [i["name"] for i in info['credits']['crew'] if i["department"] == "Writing"]
    directors = [i["name"] for i in info['credits']['crew'] if i["department"] == "Directing"]
    us_cert = Utils.dictfind(info['releases']['countries'], "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert["certification"]
    elif info['releases']['countries']:
        mpaa = info['releases']['countries'][0]['certification']
    movie_set = info.get("belongs_to_collection")
    movie = Utils.ListItem(label=info.get('title'),
                           path=PLUGIN_BASE + 'youtubevideo&&id=%s' % info.get("id", ""))
    movie.set_infos({'title': info.get('title'),
                     'Tagline': info.get('tagline'),
                     'duration': info.get('runtime'),
                     'mpaa': mpaa,
                     'Director': " / ".join(directors),
                     'writer': " / ".join(authors),
                     'plot': Utils.clean_text(info.get('overview')),
                     'originaltitle': info.get('original_title'),
                     'Country': info.get('original_language'),
                     'imdbnumber': info.get('imdb_id'),
                     'genre': " / ".join([i["name"] for i in info["genres"]]),
                     'year': Utils.get_year(info.get("release_date")),
                     'rating': round(info['vote_average'], 1) if info.get('vote_average') else "",
                     'premiered': info.get('release_date'),
                     'votes': info.get('vote_count'),
                     'Status': translate_status(info.get('status'))})
    movie.set_properties({'adult': str(info.get('adult')),
                          'popularity': info.get('popularity'),
                          'set': movie_set.get("name") if movie_set else "",
                          'set_id': movie_set.get("id") if movie_set else "",
                          'id': info.get('id'),
                          'imdb_id': info.get('imdb_id'),
                          'duration(h)': Utils.format_time(info.get("runtime"), "h"),
                          'duration(m)': Utils.format_time(info.get("runtime"), "m"),
                          'budget': Utils.millify(info.get("budget")),
                          'revenue': Utils.millify(info.get("revenue")),
                          'homepage': info.get('homepage'),
                          'studio': " / ".join(studio)})
    movie.set_artwork(get_image_urls(poster=info.get("poster_path"),
                                     fanart=info.get("backdrop_path")))
    videos = handle_videos(info["videos"]["results"]) if "videos" in info else []
    account_states = info.get("account_states")
    if dbid:
        local_item = local_db.get_movie(dbid)
        movie.update_from_listitem(local_item)
    else:
        movie = local_db.merge_with_local("movie", [movie])[0]
    # hack to get tmdb rating instead of local one
    movie.set_info("rating", round(info['vote_average'], 1) if info.get('vote_average') else "")
    listitems = {"actors": handle_people(info["credits"]["cast"]),
                 "similar": handle_movies(info["similar"]["results"]),
                 "lists": handle_misc(info["lists"]["results"]),
                 "studios": handle_misc(info["production_companies"]),
                 "releases": handle_misc(info["releases"]["countries"]),
                 "crew": handle_people(info["credits"]["crew"]),
                 "genres": handle_misc(info["genres"]),
                 "keywords": handle_misc(info["keywords"]["keywords"]),
                 "reviews": handle_misc(info["reviews"]["results"]),
                 "videos": videos,
                 "images": handle_images(info["images"]["posters"]),
                 "backdrops": handle_images(info["images"]["backdrops"])}
    return (movie, listitems, account_states)


def extended_tvshow_info(tvshow_id=None, cache_time=7, dbid=None):
    if not tvshow_id:
        return None
    params = {"append_to_response": ALL_TV_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    info = get_data(url="tv/%s" % (tvshow_id),
                    params=params,
                    cache_days=cache_time)
    if not info:
        return False
    account_states = info.get("account_states")
    videos = handle_videos(info["videos"]["results"]) if "videos" in info else []
    tmdb_id = info.get("id", "")
    if len(info.get("episode_run_time", -1)) > 1:
        duration = "%i - %i" % (min(info["episode_run_time"]), max(info["episode_run_time"]))
    elif len(info.get("episode_run_time", -1)) == 1:
        duration = "%i" % (info["episode_run_time"][0])
    else:
        duration = ""
    mpaas = info['content_ratings']['results']
    us_cert = Utils.dictfind(mpaas, "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert["rating"]
    elif mpaas:
        mpaa = mpaas[0]['rating']
    else:
        mpaa = ""
    tvshow = Utils.ListItem(label=info.get('name'),
                            path=PLUGIN_BASE + 'extendedtvinfo&&id=%s' % tmdb_id)
    tvshow.set_infos({'title': info.get('name'),
                      'tvshowtitle': info.get('name'),
                      'originaltitle': info.get('original_name', ""),
                      'duration': duration,
                      'mpaa': mpaa,
                      'genre': " / ".join([i["name"] for i in info["genres"]]),
                      'plot': Utils.clean_text(info.get("overview")),
                      'year': Utils.get_year(info.get('first_air_date')),
                      'mediatype': "tvshow",
                      'rating': round(info['vote_average'], 1) if info.get('vote_average') else "",
                      'country': info.get('original_language'),
                      'userrating': info.get('rating'),
                      'votes': info.get('vote_count'),
                      'premiered': info.get('first_air_date'),
                      'Status': translate_status(info.get('status'))})
    tvshow.set_properties({'credit_id': info.get('credit_id'),
                           'duration(h)': Utils.format_time(duration, "h"),
                           'duration(m)': Utils.format_time(duration, "m"),
                           'id': tmdb_id,
                           'popularity': info.get('popularity'),
                           'ShowType': info.get('type'),
                           'homepage': info.get('homepage'),
                           'last_air_date': info.get('last_air_date'),
                           'TotalEpisodes': info.get('number_of_episodes'),
                           'TotalSeasons': info.get('number_of_seasons'),
                           'in_production': info.get('in_production')})
    tvshow.set_artwork(get_image_urls(poster=info.get("poster_path"),
                                      fanart=info.get("backdrop_path")))
    if dbid:
        local_item = local_db.get_tvshow(dbid)
        tvshow.update_from_listitem(local_item)
    else:
        tvshow = local_db.merge_with_local("tvshow", [tvshow])[0]
    # hack to get tmdb rating instead of local one
    tvshow.set_info("rating", round(info['vote_average'], 1) if info.get('vote_average') else "")
    listitems = {"actors": handle_people(info["credits"]["cast"]),
                 "similar": handle_tvshows(info["similar"]["results"]),
                 "studios": handle_misc(info["production_companies"]),
                 "networks": handle_misc(info["networks"]),
                 "certifications": handle_misc(info["content_ratings"]["results"]),
                 "crew": handle_people(info["credits"]["crew"]),
                 "genres": handle_misc(info["genres"]),
                 "keywords": handle_misc(info["keywords"]["results"]),
                 "videos": videos,
                 "seasons": handle_seasons(info["seasons"]),
                 "images": handle_images(info["images"]["posters"]),
                 "backdrops": handle_images(info["images"]["backdrops"])}
    return (tvshow, listitems, account_states)


def extended_season_info(tvshow_id, season_number):
    if not tvshow_id or not season_number:
        return None
    params = {"append_to_response": ALL_TV_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    tvshow = get_data(url="tv/%s" % (tvshow_id),
                      params=params,
                      cache_days=99999)
    params = {"append_to_response": ALL_SEASON_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    response = get_data(url="tv/%s/season/%s" % (tvshow_id, season_number),
                        params=params,
                        cache_days=7)
    if not response:
        Utils.notify("Could not find season info")
        return None
    if response.get("name", False):
        title = response["name"]
    elif season_number == "0":
        title = addon.LANG(20381)
    else:
        title = "%s %s" % (addon.LANG(20373), season_number)
    season = Utils.ListItem(label=title)
    season.set_infos({'plot': Utils.clean_text(response["overview"]),
                      'tvshowtitle': tvshow.get('name'),
                      'title': title,
                      'premiered': response["air_date"]})
    season.set_artwork(get_image_urls(poster=response.get("poster_path")))
    season.set_properties({'id': response["id"]})
    videos = handle_videos(response["videos"]["results"]) if "videos" in response else []
    listitems = {"actors": handle_people(response["credits"]["cast"]),
                 "crew": handle_people(response["credits"]["crew"]),
                 "videos": videos,
                 "episodes": handle_episodes(response["episodes"]),
                 "images": handle_images(response["images"]["posters"]),
                 "backdrops": handle_images(response["images"].get("backdrops", []))}
    return (season, listitems)


def extended_episode_info(tvshow_id, season, episode, cache_time=7):
    if not tvshow_id or not episode:
        return None
    if not season:
        season = 0
    params = {"append_to_response": ALL_EPISODE_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    response = get_data(url="tv/%s/season/%s/episode/%s" % (tvshow_id, season, episode),
                        params=params,
                        cache_days=cache_time)
    if not response:
        Utils.notify("Could not find episode info")
        return None
    answer = {"actors": handle_people(response["credits"]["cast"]),
              "crew": handle_people(response["credits"]["crew"]),
              "guest_stars": handle_people(response["credits"]["guest_stars"]),
              "videos": handle_videos(response["videos"]["results"]) if "videos" in response else [],
              "images": handle_images(response["images"]["stills"])}
    return (handle_episodes([response])[0], answer, response.get("account_states"))


def extended_actor_info(actor_id):
    if not actor_id:
        return None
    response = get_data(url="person/%s" % (actor_id),
                        params={"append_to_response": ALL_ACTOR_PROPS},
                        cache_days=1)
    if not response:
        Utils.notify("Could not find actor info")
        return None
    listitems = {"movie_roles": handle_movies(response["movie_credits"]["cast"]),
                 "tvshow_roles": handle_tvshows(response["tv_credits"]["cast"]),
                 "movie_crew_roles": handle_movies(response["movie_credits"]["crew"]),
                 "tvshow_crew_roles": handle_tvshows(response["tv_credits"]["crew"]),
                 "tagged_images": handle_images(response["tagged_images"]["results"]) if "tagged_images" in response else [],
                 "images": handle_images(response["images"]["profiles"])}
    info = Utils.ListItem(label=response['name'],
                          path="%sextendedactorinfo&&id=%s" % (PLUGIN_BASE, response['id']),
                          infos={'mediatype': "artist"})
    info.set_properties({'adult': response.get('adult'),
                         'alsoknownas': " / ".join(response.get('also_known_as', [])),
                         'biography': Utils.clean_text(response.get('biography')),
                         'birthday': response.get('birthday'),
                         'age': Utils.calculate_age(response.get('birthday'), response.get('deathday')),
                         'character': response.get('character'),
                         'department': response.get('department'),
                         'job': response.get('job'),
                         'id': response['id'],
                         'gender': genders.get(response['gender']),
                         'cast_id': response.get('cast_id'),
                         'credit_id': response.get('credit_id'),
                         'deathday': response.get('deathday'),
                         'placeofbirth': response.get('place_of_birth'),
                         'homepage': response.get('homepage'),
                         "DBMovies": len([d for d in listitems["movie_roles"] if "dbid" in d])})
    info.set_artwork(get_image_urls(profile=response.get("profile_path")))
    return (info, listitems)


def translate_status(status):
    translations = {"released": addon.LANG(32071),
                    "post production": addon.LANG(32072),
                    "in production": addon.LANG(32073),
                    "ended": addon.LANG(32074),
                    "returning series": addon.LANG(32075),
                    "planned": addon.LANG(32076)}
    if status:
        return translations.get(status.lower(), status)


def get_movie_lists(movie_id):
    response = get_full_movie(movie_id)
    return handle_misc(response["lists"]["results"])


def get_rated_media_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    if Login.check_login():
        session_id = Login.get_session_id()
        account_id = Login.get_account_id()
        if not session_id:
            Utils.notify("Could not get session id")
            return []
        params = {"session_id": session_id,
                  "language": addon.setting("LanguageID")}
        response = get_data(url="account/%s/rated/%s" % (account_id, media_type),
                            params=params,
                            cache_days=0)
    else:
        session_id = Login.get_guest_session_id()
        if not session_id:
            Utils.notify("Could not get session id")
            return []
        params = {"language": addon.setting("LanguageID")}
        response = get_data(url="guest_session/%s/rated/%s" % (session_id, media_type),
                            params=params,
                            cache_days=0)
    if media_type == "tv/episodes":
        return handle_episodes(response["results"])
    elif media_type == "tv":
        return handle_tvshows(response["results"], False, None)
    else:
        return handle_movies(response["results"], False, None)


def get_fav_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    session_id = Login.get_session_id()
    account_id = Login.get_account_id()
    if not session_id:
        Utils.notify("Could not get session id")
        return []
    params = {"session_id": session_id,
              "language": addon.setting("LanguageID")}
    response = get_data(url="account/%s/favorite/%s" % (account_id, media_type),
                        params=params,
                        cache_days=0)
    if "results" not in response:
        return []
    if media_type == "tv":
        return handle_tvshows(response["results"], False, None)
    elif media_type == "tv/episodes":
        return handle_episodes(response["results"])
    else:
        return handle_movies(response["results"], False, None)


def get_movies_from_list(list_id, cache_time=5):
    '''
    get movie dict list from tmdb list.
    '''
    response = get_data(url="list/%s" % (list_id),
                        params={"language": addon.setting("LanguageID")},
                        cache_days=cache_time)
    return handle_movies(response["items"], False, None) if response else []


def get_popular_actors():
    '''
    get dict list containing popular actors / directors / writers
    '''
    response = get_data(url="person/popular",
                        cache_days=1)
    return handle_people(response["results"])


def get_actor_credits(actor_id, media_type):
    '''
    media_type: movie or tv
    '''
    response = get_data(url="person/%s/%s_credits" % (actor_id, media_type),
                        cache_days=1)
    return handle_movies(response["cast"])


def get_full_movie(movie_id):
    params = {"include_image_language": "en,null,%s" % addon.setting("LanguageID"),
              "language": addon.setting("LanguageID"),
              "append_to_response": ALL_MOVIE_PROPS
              }
    return get_data(url="movie/%s" % (movie_id),
                    params=params,
                    cache_days=30)


def get_keywords(movie_id):
    '''
    get dict list containing movie keywords
    '''
    response = get_full_movie(movie_id)
    keywords = []
    if "keywords" in response:
        for keyword in response["keywords"]["keywords"]:
            keywords.append({'id': keyword.get('id'),
                            'label': keyword['name']})
    return keywords


def get_similar_movies(movie_id):
    '''
    get dict list containing movies similar to *movie_id
    '''
    response = get_full_movie(movie_id)
    if not response.get("similar"):
        return []
    return handle_movies(response["similar"]["results"])


def get_similar_tvshows(tvshow_id):
    '''
    return list with similar tvshows for show with *tvshow_id (TMDB ID)
    '''
    params = {"append_to_response": ALL_TV_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    response = get_data(url="tv/%s" % (tvshow_id),
                        params=params,
                        cache_days=10)
    if not response.get("similar"):
        return []
    return handle_tvshows(response["similar"]["results"])


def get_tmdb_shows(tvshow_type):
    '''
    return list with tv shows
    available types: airing, on_the_air, top_rated, popular
    '''
    params = {"language": addon.setting("LanguageID")}
    response = get_data(url="tv/%s" % (tvshow_type),
                        params=params,
                        cache_days=0.3)
    if not response.get("results"):
        return []
    return handle_tvshows(response["results"], False, None)


def get_tmdb_movies(movie_type):
    '''
    return list with movies
    available types: now_playing, upcoming, top_rated, popular
    '''
    params = {"language": addon.setting("LanguageID")}
    response = get_data(url="movie/%s" % (movie_type),
                        params=params,
                        cache_days=0.3)
    if not response.get("results"):
        return []
    return handle_movies(response["results"], False, None)


def get_set_movies(set_id):
    '''
    return list with movies which are part of set with *set_id
    '''
    params = {"append_to_response": "images",
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    response = get_data(url="collection/%s" % (set_id),
                        params=params,
                        cache_days=14)
    if not response:
        return [], {}
    artwork = get_image_urls(poster=response.get("poster_path"),
                             fanart=response.get("backdrop_path"))
    info = {"label": response["name"],
            "overview": response["overview"],
            "id": response["id"]}
    info.update(artwork)
    return handle_movies(response.get("parts", [])), info


def get_person_movies(person_id):
    params = {"language": addon.setting("LanguageID")}
    response = get_data(url="person/%s/credits" % (person_id),
                        params=params,
                        cache_days=14)
    # return handle_movies(response["crew"]) + handle_movies(response["cast"])
    if "crew" not in response:
        return []
    return handle_movies(response["crew"])


def search_media(media_name=None, year='', media_type="movie", cache_days=1):
    '''
    return list of items with type *media_type for search with *media_name
    '''
    if not media_name:
        return None
    params = {"query": "%s %s".format(media_name, year) if year else media_name,
              "language": addon.setting("language"),
              "include_adult": include_adult}
    response = get_data(url="search/%s" % (media_type),
                        params=params,
                        cache_days=cache_days)
    if response == "Empty":
        return None
    for item in response['results']:
        if item['id']:
            return item['id']

Login = LoginProvider(username=addon.setting("tmdb_username"),
                      password=addon.setting("tmdb_password"))

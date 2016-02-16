# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from YouTube import *
from Utils import *
from local_db import *
import re
from urllib2 import Request, urlopen
from functools32 import lru_cache
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
    'User-agent': 'XBMC/14.0 ( phil65@kodi.tv )'
}
base_url = "http://image.tmdb.org/t/p/"
poster_size = "w500"
fanart_size = "w1280"
include_adult = SETTING("include_adults").lower()
if SETTING("use_https"):
    URL_BASE = "https://api.themoviedb.org/3/"
else:
    URL_BASE = "http://api.themoviedb.org/3/"


@lru_cache(maxsize=128)
def check_login():
    if SETTING("tmdb_username"):
        session_id = get_session_id()
        if session_id:
            return "True"
    return ""


def set_rating_prompt(media_type, media_id):
    if not media_type or not media_id:
        return False
    ratings = [str(float(i * 0.5)) for i in range(1, 21)]
    rating = xbmcgui.Dialog().select(LANG(32129), ratings)
    if rating == -1:
        return False
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
    if check_login():
        session_id = "session_id=" + get_session_id()
    else:
        session_id = "guest_session_id=" + get_guest_session_id()
    values = '{"value": %.1f}' % rating
    if media_type == "episode":
        if not media_id[1]:
            media_id[1] = "0"
        url = URL_BASE + "tv/%s/season/%s/episode/%s/rating?api_key=%s&%s" % (media_id[0], media_id[1], media_id[2], TMDB_KEY, session_id)
    else:
        url = URL_BASE + "%s/%s/rating?api_key=%s&%s" % (media_type, media_id, TMDB_KEY, session_id)
            # request.get_method = lambda: 'DELETE'
    request = Request(url=url,
                      data=values,
                      headers=HEADERS)
    response = urlopen(request, timeout=3).read()
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])


def change_fav_status(media_id=None, media_type="movie", status="true"):
    session_id = get_session_id()
    account_id = get_account_info()
    values = '{"media_type": "%s", "media_id": %s, "favorite": %s}' % (media_type, media_id, status)
    if not session_id:
        notify("Could not get session id")
        return None
    url = URL_BASE + "account/%s/favorite?session_id=%s&api_key=%s" % (account_id, session_id, TMDB_KEY)
    request = Request(url,
                      data=values,
                      headers=HEADERS)
    response = urlopen(request, timeout=3).read()
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])


def create_list(list_name):
    '''
    creates new list on TMDB with name *list_name
    returns newly created list id
    '''
    session_id = get_session_id()
    url = URL_BASE + "list?api_key=%s&session_id=%s" % (TMDB_KEY, session_id)
    values = {'name': '%s' % list_name, 'description': 'List created by ExtendedInfo Script for Kodi.'}
    request = Request(url,
                      data=simplejson.dumps(values),
                      headers=HEADERS)
    response = urlopen(request, timeout=3).read()
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])
    return results["list_id"]


def remove_list(list_id):
    session_id = get_session_id()
    url = URL_BASE + "list/%s?api_key=%s&session_id=%s" % (list_id, TMDB_KEY, session_id)
    values = {'media_id': list_id}
    request = Request(url,
                      data=simplejson.dumps(values),
                      headers=HEADERS)
    request.get_method = lambda: 'DELETE'
    response = urlopen(request, timeout=3).read()
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])
    return results["list_id"]


def change_list_status(list_id, movie_id, status):
    if status:
        method = "add_item"
    else:
        method = "remove_item"
    session_id = get_session_id()
    url = URL_BASE + "list/%s/%s?api_key=%s&session_id=%s" % (list_id, method, TMDB_KEY, session_id)
    values = {'media_id': movie_id}
    request = Request(url,
                      data=simplejson.dumps(values),
                      headers=HEADERS)
    try:
        response = urlopen(request, timeout=3).read()
    except urllib2.HTTPError as err:
        if err.code == 401:
            notify("Error", "Not authorized to modify list")
    results = simplejson.loads(response)
    notify(ADDON_NAME, results["status_message"])


def get_account_lists(cache_time=0):
    '''
    returns movie lists for TMDB user
    '''
    session_id = get_session_id()
    account_id = get_account_info()
    if session_id and account_id:
        response = get_tmdb_data("account/%s/lists?session_id=%s&" % (account_id, session_id), cache_time)
        return response["results"]
    else:
        return []


@lru_cache(maxsize=128)
def get_account_info():
    '''
    returns TMDB account id
    '''

    session_id = get_session_id()
    response = get_tmdb_data("account?session_id=%s&" % session_id, 999999)
    if "id" in response:
        return response["id"]
    else:
        return None


def get_certification_list(media_type):
    response = get_tmdb_data("certification/%s/list?" % media_type, 999999)
    if "certifications" in response:
        return response["certifications"]
    else:
        return []


def add_movie_to_list(movie_id):
    selection = xbmcgui.Dialog().select(heading=LANG(22080),
                                        list=[LANG(32083)])
    if selection == 0:
        account_lists = get_account_lists()
        listitems = ["%s (%i)" % (i["name"], i["item_count"]) for i in account_lists]
        index = xbmcgui.Dialog().select(LANG(32136), listitems)
        change_list_status(list_id=account_lists[index]["id"],
                           movie_id=movie_id,
                           status=True)


def merge_with_cert_desc(input_list, media_type):
    cert_list = get_certification_list(media_type)
    for item in input_list:
        if item["iso_3166_1"].upper() not in cert_list:
            continue
        hit = dictfind(lst=cert_list[item["iso_3166_1"].upper()],
                       key="certification",
                       value=item["certification"])
        if hit:
            item["meaning"] = hit["meaning"]
    return input_list


@lru_cache(maxsize=128)
def get_guest_session_id():
    '''
    returns guest session id for TMDB
    '''
    response = get_tmdb_data("authentication/guest_session/new?", 999999)
    if "guest_session_id" in response:
        return str(response["guest_session_id"])
    else:
        return None


@lru_cache(maxsize=128)
def get_session_id():
    '''
    returns session id for TMDB Account
    '''
    request_token = auth_request_token()
    response = get_tmdb_data("authentication/session/new?request_token=%s&" % request_token, 99999)
    if response and "success" in response:
        pass_dict_to_skin({"tmdb_logged_in": "true"})
        return str(response["session_id"])
    else:
        request_token = auth_request_token(cache_days=0)
        response = get_tmdb_data("authentication/session/new?request_token=%s&" % request_token, 0)
        if response and "success" in response:
            pass_dict_to_skin({"tmdb_logged_in": "true"})
            return str(response["session_id"])
    pass_dict_to_skin({"tmdb_logged_in": ""})
    notify("login failed")
    return None


@lru_cache(maxsize=128)
def get_request_token():
    response = get_tmdb_data("authentication/token/new?", 999999)
    return response["request_token"]


@lru_cache(maxsize=128)
def auth_request_token(cache_days=9999):
    '''
    returns request token, is used to get session_id
    '''
    request_token = get_request_token()
    username = url_quote(SETTING("tmdb_username"))
    password = url_quote(SETTING("tmdb_password"))
    response = get_tmdb_data("authentication/token/validate_with_login?request_token=%s&username=%s&password=%s&" % (request_token, username, password), cache_days)
    if "success" in response and response["success"]:
        return response["request_token"]
    else:
        return None


def handle_tmdb_multi_search(results=[]):
    listitems = []
    for item in results:
        if item["media_type"] == "movie":
            listitem = handle_tmdb_movies([item])[0]
        elif item["media_type"] == "tv":
            listitem = handle_tmdb_tvshows([item])[0]
        else:
            listitem = handle_tmdb_people([item])[0]
        listitems.append(listitem)
    return listitems


def handle_tmdb_movies(results=[], local_first=True, sortkey="year"):
    response = get_tmdb_data("genre/movie/list?language=%s&" % (SETTING("LanguageID")), 30)
    id_list = [item["id"] for item in response["genres"]]
    label_list = [item["name"] for item in response["genres"]]
    movies = []
    for movie in results:
        if "genre_ids" in movie:
            genre_list = [label_list[id_list.index(genre_id)] for genre_id in movie["genre_ids"] if genre_id in id_list]
            genres = " / ".join(genre_list)
        else:
            genres = ""
        tmdb_id = str(fetch(movie, 'id'))
        artwork = get_image_urls(poster=movie.get("poster_path"),
                                 fanart=movie.get("backdrop_path"))
        trailer = "plugin://script.extendedinfo/?info=playtrailer&&id=" + tmdb_id
        if SETTING("infodialog_onclick") != "false":
            path = 'plugin://script.extendedinfo/?info=extendedinfo&&id=%s' % tmdb_id
        else:
            path = trailer
        listitem = {'title': fetch(movie, 'title'),
                    'Label': fetch(movie, 'title'),
                    'OriginalTitle': fetch(movie, 'original_title'),
                    'id': tmdb_id,
                    'path': path,
                    'media_type': "movie",
                    'country': fetch(movie, 'original_language'),
                    'plot': fetch(movie, 'overview'),
                    'Trailer': trailer,
                    'Popularity': fetch(movie, 'popularity'),
                    'Rating': fetch(movie, 'vote_average'),
                    'credit_id': fetch(movie, 'credit_id'),
                    'character': fetch(movie, 'character'),
                    'job': fetch(movie, 'job'),
                    'department': fetch(movie, 'department'),
                    'Votes': fetch(movie, 'vote_count'),
                    'User_Rating': fetch(movie, 'rating'),
                    'year': get_year(fetch(movie, 'release_date')),
                    'genre': genres,
                    'time_comparer': fetch(movie, 'release_date').replace("-", ""),
                    'Premiered': fetch(movie, 'release_date')}
        listitem.update(artwork)
        movies.append(listitem)
    movies = merge_with_local_movie_info(movies, local_first, sortkey)
    return movies


def handle_tmdb_tvshows(results, local_first=True, sortkey="year"):
    tvshows = []
    response = get_tmdb_data("genre/tv/list?language=%s&" % (SETTING("LanguageID")), 30)
    id_list = [item["id"] for item in response["genres"]]
    label_list = [item["name"] for item in response["genres"]]
    for tv in results:
        tmdb_id = fetch(tv, 'id')
        artwork = get_image_urls(poster=tv.get("poster_path"),
                                 fanart=tv.get("backdrop_path"))
        if "genre_ids" in tv:
            genre_list = [label_list[id_list.index(genre_id)] for genre_id in tv["genre_ids"] if genre_id in id_list]
            genres = " / ".join(genre_list)
        else:
            genres = ""
        duration = ""
        if "episode_run_time" in tv:
            if len(tv["episode_run_time"]) > 1:
                duration = "%i - %i" % (min(tv["episode_run_time"]), max(tv["episode_run_time"]))
            elif len(tv["episode_run_time"]) == 1:
                duration = "%i" % (tv["episode_run_time"][0])
        newtv = {'title': fetch(tv, 'name'),
                 'TVShowTitle': fetch(tv, 'name'),
                 'OriginalTitle': fetch(tv, 'original_name'),
                 'duration': duration,
                 'id': tmdb_id,
                 'genre': genres,
                 'country': fetch(tv, 'original_language'),
                 'Popularity': fetch(tv, 'popularity'),
                 'credit_id': fetch(tv, 'credit_id'),
                 'Plot': fetch(tv, "overview"),
                 'year': get_year(fetch(tv, 'first_air_date')),
                 'media_type': "tv",
                 'character': fetch(tv, 'character'),
                 'path': 'plugin://script.extendedinfo/?info=extendedtvinfo&&id=%s' % tmdb_id,
                 'Rating': fetch(tv, 'vote_average'),
                 'User_Rating': str(fetch(tv, 'rating')),
                 'Votes': fetch(tv, 'vote_count'),
                 'TotalEpisodes': fetch(tv, 'number_of_episodes'),
                 'TotalSeasons': fetch(tv, 'number_of_seasons'),
                 'Release_Date': fetch(tv, 'first_air_date'),
                 'Premiered': fetch(tv, 'first_air_date')}
        newtv.update(artwork)
        tvshows.append(newtv)
    tvshows = merge_with_local_tvshow_info(tvshows, local_first, sortkey)
    return tvshows


def handle_tmdb_episodes(results):
    listitems = []
    for item in results:
        title = clean_text(fetch(item, 'name'))
        if not title:
            title = "%s %s" % (LANG(20359), fetch(item, 'episode_number'))
        artwork = get_image_urls(still=item.get("still_path"))
        listitem = {'media_type': "episode",
                    'title': title,
                    'release_date': fetch(item, 'air_date'),
                    'episode': fetch(item, 'episode_number'),
                    'production_code': fetch(item, 'production_code'),
                    'season': fetch(item, 'season_number'),
                    'Rating': fetch(item, 'vote_average'),
                    'Votes': fetch(item, 'vote_count'),
                    'id': fetch(item, 'id'),
                    'Description': clean_text(fetch(item, 'overview'))}
        listitem.update(artwork)
        listitems.append(listitem)
    return listitems


def handle_tmdb_misc(results):
    listitems = []
    for item in results:
        artwork = get_image_urls(poster=item.get("poster_path"))
        listitem = {'title': clean_text(fetch(item, 'name')),
                    'certification': fetch(item, 'certification') + fetch(item, 'rating'),
                    'item_count': fetch(item, 'item_count'),
                    'favorite_count': fetch(item, 'favorite_count'),
                    'release_date': fetch(item, 'release_date'),
                    'path': "plugin://script.extendedinfo?info=listmovies&---id=%s" % fetch(item, 'id'),
                    'year': get_year(fetch(item, 'release_date')),
                    'iso_3166_1': fetch(item, 'iso_3166_1').lower(),
                    'author': fetch(item, 'author'),
                    'content': clean_text(fetch(item, 'content')),
                    'id': fetch(item, 'id'),
                    'url': fetch(item, 'url'),
                    'Description': clean_text(fetch(item, 'description'))}
        listitem.update(artwork)
        listitems.append(listitem)
    return listitems


def handle_tmdb_seasons(results):
    listitems = []
    for season in results:
        season_number = str(fetch(season, 'season_number'))
        artwork = get_image_urls(poster=season.get("poster_path"))
        if season_number == "0":
            title = LANG(20381)
        else:
            title = "%s %s" % (LANG(20373), season_number)
        listitem = {'media_type': "season",
                    'title': title,
                    'season': season_number,
                    'air_date': fetch(season, 'air_date'),
                    'year': get_year(fetch(season, 'air_date')),
                    'id': fetch(season, 'id')}
        listitem.update(artwork)
        listitems.append(listitem)
    return listitems


def handle_tmdb_videos(results):
    listitems = []
    for item in results:
        image = "http://i.ytimg.com/vi/" + fetch(item, 'key') + "/0.jpg"
        listitem = {'thumb': image,
                    'title': fetch(item, 'name'),
                    'iso_639_1': fetch(item, 'iso_639_1'),
                    'type': fetch(item, 'type'),
                    'key': fetch(item, 'key'),
                    'youtube_id': fetch(item, 'key'),
                    'site': fetch(item, 'site'),
                    'id': fetch(item, 'id'),
                    'size': fetch(item, 'size')}
        listitems.append(listitem)
    return listitems


def handle_tmdb_people(results):
    people = []
    for person in results:
        artwork = get_image_urls(profile=person.get("profile_path"))
        also_known_as = " / ".join(fetch(person, 'also_known_as'))
        newperson = {'adult': str(fetch(person, 'adult')),
                     'name': person['name'],
                     'title': person['name'],
                     'also_known_as': also_known_as,
                     'alsoknownas': also_known_as,
                     'biography': clean_text(fetch(person, 'biography')),
                     'birthday': fetch(person, 'birthday'),
                     'age': calculate_age(fetch(person, 'birthday'), fetch(person, 'deathday')),
                     'character': fetch(person, 'character'),
                     'department': fetch(person, 'department'),
                     'job': fetch(person, 'job'),
                     'media_type': "person",
                     'id': str(person['id']),
                     'cast_id': str(fetch(person, 'cast_id')),
                     'credit_id': str(fetch(person, 'credit_id')),
                     'path': "plugin://script.extendedinfo/?info=extendedactorinfo&&id=" + str(person['id']),
                     'deathday': fetch(person, 'deathday'),
                     'place_of_birth': fetch(person, 'place_of_birth'),
                     'placeofbirth': fetch(person, 'place_of_birth'),
                     'homepage': fetch(person, 'homepage')}
        newperson.update(artwork)
        people.append(newperson)
    return people


def handle_tmdb_images(results):
    images = []
    for item in results:
        artwork = get_image_urls(poster=item.get("file_path"))
        image = {'aspectratio': item['aspect_ratio'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1")}
        image.update(artwork)
        images.append(image)
    return images


def handle_tmdb_tagged_images(results):
    images = []
    for item in results:
        artwork = get_image_urls(poster=item.get("file_path"))
        image = {'aspectratio': item['aspect_ratio'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1"),
                 'title': fetch(item["media"], "title"),
                 'mediaposter': base_url + poster_size + fetch(item["media"], "poster_path")}
        image.update(artwork)
        images.append(image)
    return images


def handle_tmdb_companies(results):
    companies = []
    for company in results:
        newcompany = {'parent_company': company['parent_company'],
                      'name': company['name'],
                      'description': company['description'],
                      'headquarters': company['headquarters'],
                      'homepage': company['homepage'],
                      'id': company['id'],
                      'logo_path': company['logo_path']}
        companies.append(newcompany)
    return companies


def search_company(company_name):
    regex = re.compile('\(.+?\)')
    company_name = regex.sub('', company_name)
    response = get_tmdb_data("search/company?query=%s&" % url_quote(company_name), 10)
    if response and "results" in response:
        return response["results"]
    else:
        log("Could not find company ID for %s" % company_name)
        return ""


def multi_search(search_str):
    response = get_tmdb_data("search/multi?query=%s&" % url_quote(search_str), 1)
    if response and "results" in response:
        return response["results"]
    else:
        log("Error when searching for %s" % search_str)
        return ""


def get_person_info(person_label, skip_dialog=False):
    persons = person_label.split(" / ")
    response = get_tmdb_data("search/person?query=%s&include_adult=%s&" % (url_quote(persons[0]), include_adult), 30)
    if not response or "results" not in response:
        return False
    if len(response["results"]) > 1 and not skip_dialog:
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        listitem, index = wm.open_selectdialog(listitems=handle_tmdb_people(response["results"]))
        if index >= 0:
            return response["results"][index]
    elif response["results"]:
        return response["results"][0]
    return False


def get_keyword_id(keyword):
    response = get_tmdb_data("search/keyword?query=%s&include_adult=%s&" % (url_quote(keyword), include_adult), 30)
    if response and "results" in response and response["results"]:
        if len(response["results"]) > 1:
            names = [item["name"] for item in response["results"]]
            selection = xbmcgui.Dialog().select(LANG(32114), names)
            if selection > -1:
                return response["results"][selection]
        elif response["results"]:
            return response["results"][0]
    else:
        log("could not find Keyword ID")
        return False


def get_set_id(set_name):
    set_name = set_name.replace("[", "").replace("]", "").replace("Kollektion", "Collection")
    response = get_tmdb_data("search/collection?query=%s&language=%s&" % (url_quote(set_name.encode("utf-8")), SETTING("LanguageID")), 14)
    if "results" in response and response["results"]:
        return response["results"][0]["id"]
    else:
        return ""


def get_tmdb_data(url="", cache_days=14, folder="TheMovieDB"):
    url = URL_BASE + "%sapi_key=%s" % (url, TMDB_KEY)
    return get_JSON_response(url, cache_days, folder)


def get_company_data(company_id):
    response = get_tmdb_data("company/%s/movies?" % (company_id), 30)
    if response and "results" in response:
        return handle_tmdb_movies(response["results"])
    else:
        return []


def get_credit_info(credit_id):
    return get_tmdb_data("credit/%s?language=%s&" % (credit_id, SETTING("LanguageID")), 30)


def get_account_props(account_states):
    props = {}
    if account_states.get("favorite"):
        props["FavButton_Label"] = LANG(32155)
        props["favorite"] = "True"
    else:
        props["FavButton_Label"] = LANG(32154)
        props["favorite"] = ""
    if account_states["rated"]:
        props["rated"] = str(account_states["rated"]["value"])
    else:
        props["rated"] = ""
    if "watchlist" in account_states:
        props["watchlist"] = str(account_states["watchlist"])
    return props


def get_image_urls(poster=None, still=None, fanart=None, profile=None):
    images = {}
    if poster:
        images["poster"] = base_url + "w500" + poster
        images["poster_original"] = base_url + "original" + poster
        images["original"] = base_url + "original" + poster
        images["poster_small"] = base_url + "w342" + poster
        images["thumb"] = base_url + "w342" + poster
    if still:
        images["thumb"] = base_url + "w300" + still
        images["still"] = base_url + "w300" + still
        images["still_original"] = base_url + "original" + still
        images["still_small"] = base_url + "w185" + still
    if fanart:
        images["fanart"] = base_url + "w1280" + fanart
        images["fanart_original"] = base_url + "original" + fanart
        images["original"] = base_url + "original" + fanart
        images["fanart_small"] = base_url + "w780" + fanart
    if profile:
        images["poster"] = base_url + "w500" + profile
        images["poster_original"] = base_url + "original" + profile
        images["poster_small"] = base_url + "w342" + profile
        images["thumb"] = base_url + "w342" + profile
    return images


def get_movie_tmdb_id(imdb_id=None, name=None, dbid=None):
    if dbid and (int(dbid) > 0):
        movie_id = get_imdb_id_from_db("movie", dbid)
        log("IMDB Id from local DB: %s" % (movie_id))
        return movie_id
    elif imdb_id:
        response = get_tmdb_data("find/tt%s?external_source=imdb_id&language=%s&" % (imdb_id.replace("tt", ""), SETTING("LanguageID")), 30)
        if response["movie_results"]:
            return response["movie_results"][0]["id"]
    if name:
        return search_media(name)
    else:
        return None


def get_show_tmdb_id(tvdb_id=None, source="tvdb_id"):
    response = get_tmdb_data("find/%s?external_source=%s&language=%s&" % (tvdb_id, source, SETTING("LanguageID")), 30)
    if response and response["tv_results"]:
        return response["tv_results"][0]["id"]
    else:
        notify("TVShow Info not available.")
        return None


def get_trailer(movie_id=None):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movie_id, SETTING("LanguageID"), SETTING("LanguageID")), 30)
    if response and "videos" in response and response['videos']['results']:
        return response['videos']['results'][0]['key']
    notify("Could not get trailer")
    return ""


def extended_movie_info(movie_id=None, dbid=None, cache_time=14):
    if not movie_id:
        return None
    if check_login():
        session_str = "session_id=%s&" % (get_session_id())
    else:
        session_str = ""
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&%s" %
                             (movie_id, SETTING("LanguageID"), SETTING("LanguageID"), session_str), cache_time)
    if not response:
        notify("Could not get movie information")
        return {}
    mpaa = ""
    set_name = ""
    set_id = ""
    genres = [i["name"] for i in response["genres"]]
    Studio = [i["name"] for i in response["production_companies"]]
    authors = [i["name"] for i in response['credits']['crew'] if i["department"] == "Writing"]
    directors = [i["name"] for i in response['credits']['crew'] if i["department"] == "Directing"]
    us_cert = dictfind(response['releases']['countries'], "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert["certification"]
    elif response['releases']['countries']:
        mpaa = response['releases']['countries'][0]['certification']
    movie_set = fetch(response, "belongs_to_collection")
    if movie_set:
        set_name = fetch(movie_set, "name")
        set_id = fetch(movie_set, "id")
    artwork = get_image_urls(poster=response.get("poster_path"),
                             fanart=response.get("backdrop_path"))
    path = 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % fetch(response, "id")
    movie = {'title': fetch(response, 'title'),
             'Label': fetch(response, 'title'),
             'Tagline': fetch(response, 'tagline'),
             'duration': fetch(response, 'runtime'),
             'duration(h)': format_time(fetch(response, 'runtime'), "h"),
             'duration(m)': format_time(fetch(response, 'runtime'), "m"),
             'mpaa': mpaa,
             'Director': " / ".join(directors),
             'writer': " / ".join(authors),
             'Budget': millify(fetch(response, 'budget')),
             'Revenue': millify(fetch(response, 'revenue')),
             'Homepage': fetch(response, 'homepage'),
             'Set': set_name,
             'SetId': set_id,
             'id': fetch(response, 'id'),
             'imdb_id': fetch(response, 'imdb_id'),
             'Plot': clean_text(fetch(response, 'overview')),
             'OriginalTitle': fetch(response, 'original_title'),
             'Country': fetch(response, 'original_language'),
             'genre': " / ".join(genres),
             'Rating': fetch(response, 'vote_average'),
             'Votes': fetch(response, 'vote_count'),
             'Adult': str(fetch(response, 'adult')),
             'Popularity': fetch(response, 'popularity'),
             'Status': translate_status(fetch(response, 'status')),
             'path': path,
             'release_date': fetch(response, 'release_date'),
             'Premiered': fetch(response, 'release_date'),
             'Studio': " / ".join(Studio),
             'year': get_year(fetch(response, 'release_date'))}
    movie.update(artwork)
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    else:
        videos = []
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    if dbid:
        local_item = get_movie_from_db(dbid)
        movie.update(local_item)
    else:
        movie = merge_with_local_movie_info([movie])[0]
    movie['Rating'] = fetch(response, 'vote_average')  # hack to get tmdb rating instead of local one
    listitems = {"actors": handle_tmdb_people(response["credits"]["cast"]),
                 "similar": handle_tmdb_movies(response["similar"]["results"]),
                 "lists": handle_tmdb_misc(response["lists"]["results"]),
                 "studios": handle_tmdb_misc(response["production_companies"]),
                 "releases": handle_tmdb_misc(response["releases"]["countries"]),
                 "crew": handle_tmdb_people(response["credits"]["crew"]),
                 "genres": handle_tmdb_misc(response["genres"]),
                 "keywords": handle_tmdb_misc(response["keywords"]["keywords"]),
                 "reviews": handle_tmdb_misc(response["reviews"]["results"]),
                 "videos": videos,
                 "images": handle_tmdb_images(response["images"]["posters"]),
                 "backdrops": handle_tmdb_images(response["images"]["backdrops"])}
    return (movie, listitems, account_states)


def extended_tvshow_info(tvshow_id=None, cache_time=7, dbid=None):
    if not tvshow_id:
        return None
    session_str = ""
    if check_login():
        session_str = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                             (tvshow_id, SETTING("LanguageID"), SETTING("LanguageID"), session_str), cache_time)
    if not response:
        return False
    videos = []
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    tmdb_id = fetch(response, 'id')
    artwork = get_image_urls(poster=response.get("poster_path"),
                             fanart=response.get("backdrop_path"))
    if len(response.get("episode_run_time", -1)) > 1:
        duration = "%i - %i" % (min(response["episode_run_time"]), max(response["episode_run_time"]))
    elif len(response.get("episode_run_time", -1)) == 1:
        duration = "%i" % (response["episode_run_time"][0])
    else:
        duration = ""
    us_cert = dictfind(response['content_ratings']['results'], "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert["rating"]
    elif response['content_ratings']['results']:
        mpaa = response['content_ratings']['results'][0]['rating']
    else:
        mpaa = ""
    genres = [item["name"] for item in response["genres"]]
    tvshow = {'title': fetch(response, 'name'),
              'TVShowTitle': fetch(response, 'name'),
              'OriginalTitle': fetch(response, 'original_name'),
              'duration': duration,
              'duration(h)': format_time(duration, "h"),
              'duration(m)': format_time(duration, "m"),
              'id': tmdb_id,
              'mpaa': mpaa,
              'genre': " / ".join(genres),
              'credit_id': fetch(response, 'credit_id'),
              'Plot': clean_text(fetch(response, "overview")),
              'year': get_year(fetch(response, 'first_air_date')),
              'media_type': "tv",
              'path': 'plugin://script.extendedinfo/?info=extendedtvinfo&&id=%s' % tmdb_id,
              'Popularity': fetch(response, 'popularity'),
              'Rating': fetch(response, 'vote_average'),
              'country': fetch(response, 'original_language'),
              'User_Rating': str(fetch(response, 'rating')),
              'Votes': fetch(response, 'vote_count'),
              'Status': translate_status(fetch(response, 'status')),
              'ShowType': fetch(response, 'type'),
              'homepage': fetch(response, 'homepage'),
              'last_air_date': fetch(response, 'last_air_date'),
              'first_air_date': fetch(response, 'first_air_date'),
              'TotalEpisodes': fetch(response, 'number_of_episodes'),
              'TotalSeasons': fetch(response, 'number_of_seasons'),
              'in_production': fetch(response, 'in_production'),
              'Release_Date': fetch(response, 'first_air_date'),
              'Premiered': fetch(response, 'first_air_date')}
    tvshow.update(artwork)
    if dbid:
        local_item = get_tvshow_from_db(dbid)
        tvshow.update(local_item)
    else:
        tvshow = merge_with_local_tvshow_info([tvshow])[0]
    tvshow['Rating'] = fetch(response, 'vote_average')  # hack to get tmdb rating instead of local one
    listitems = {"actors": handle_tmdb_people(response["credits"]["cast"]),
                 "similar": handle_tmdb_tvshows(response["similar"]["results"]),
                 "studios": handle_tmdb_misc(response["production_companies"]),
                 "networks": handle_tmdb_misc(response["networks"]),
                 "certifications": handle_tmdb_misc(response["content_ratings"]["results"]),
                 "crew": handle_tmdb_people(response["credits"]["crew"]),
                 "genres": handle_tmdb_misc(response["genres"]),
                 "keywords": handle_tmdb_misc(response["keywords"]["results"]),
                 "videos": videos,
                 "seasons": handle_tmdb_seasons(response["seasons"]),
                 "images": handle_tmdb_images(response["images"]["posters"]),
                 "backdrops": handle_tmdb_images(response["images"]["backdrops"])}
    return (tvshow, listitems, account_states)


def extended_season_info(tvshow_id, season_number):
    if not tvshow_id or not season_number:
        return None
    session_str = ""
    if check_login():
        session_str = "session_id=%s&" % (get_session_id())
    tvshow = get_tmdb_data("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                           (tvshow_id, SETTING("LanguageID"), SETTING("LanguageID"), session_str), 99999)
    response = get_tmdb_data("tv/%s/season/%s?append_to_response=videos,images,external_ids,credits&language=%s&include_image_language=en,null,%s&" % (tvshow_id, season_number, SETTING("LanguageID"), SETTING("LanguageID")), 7)
    if not response:
        notify("Could not find season info")
        return None
    if response.get("name", False):
        title = response["name"]
    elif season_number == "0":
        title = LANG(20381)
    else:
        title = "%s %s" % (LANG(20373), season_number)
    season = {'SeasonDescription': clean_text(response["overview"]),
              'Plot': clean_text(response["overview"]),
              'TVShowTitle': fetch(tvshow, 'name'),
              'title': title,
              'release_date': response["air_date"],
              'AirDate': response["air_date"]}
    artwork = get_image_urls(poster=response.get("poster_path"))
    season.update(artwork)
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    else:
        videos = []
    listitems = {"actors": handle_tmdb_people(response["credits"]["cast"]),
                 "crew": handle_tmdb_people(response["credits"]["crew"]),
                 "videos": videos,
                 "episodes": handle_tmdb_episodes(response["episodes"]),
                 "images": handle_tmdb_images(response["images"]["posters"]),
                 "backdrops": handle_tmdb_images(response["images"].get("backdrops", []))}
    return (season, listitems)


def extended_episode_info(tvshow_id, season, episode, cache_time=7):
    if not tvshow_id or not episode:
        return None
    if not season:
        season = 0
    session_str = ""
    if check_login():
        session_str = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s/season/%s/episode/%s?append_to_response=account_states,credits,external_ids,images,rating,videos&language=%s&include_image_language=en,null,%s&%s&" %
                             (tvshow_id, season, episode, SETTING("LanguageID"), SETTING("LanguageID"), session_str), cache_time)
    videos = []
    if "videos" in response:
        videos = handle_tmdb_videos(response["videos"]["results"])
    answer = {"actors": handle_tmdb_people(response["credits"]["cast"]),
              "crew": handle_tmdb_people(response["credits"]["crew"]),
              "guest_stars": handle_tmdb_people(response["credits"]["guest_stars"]),
              "videos": videos,
              "images": handle_tmdb_images(response["images"]["stills"])}
    return (handle_tmdb_episodes([response])[0], answer, response.get("account_states"))


def extended_actor_info(actor_id):
    if not actor_id:
        return None
    response = get_tmdb_data("person/%s?append_to_response=tv_credits,movie_credits,combined_credits,images,tagged_images&" % (actor_id), 1)
    tagged_images = []
    if "tagged_images" in response:
        tagged_images = handle_tmdb_tagged_images(response["tagged_images"]["results"])
    listitems = {"movie_roles": handle_tmdb_movies(response["movie_credits"]["cast"]),
                 "tvshow_roles": handle_tmdb_tvshows(response["tv_credits"]["cast"]),
                 "movie_crew_roles": handle_tmdb_movies(response["movie_credits"]["crew"]),
                 "tvshow_crew_roles": handle_tmdb_tvshows(response["tv_credits"]["crew"]),
                 "tagged_images": tagged_images,
                 "images": handle_tmdb_images(response["images"]["profiles"])}
    info = handle_tmdb_people([response])[0]
    info["DBMovies"] = str(len([d for d in listitems["movie_roles"] if "dbid" in d]))
    return (info, listitems)


def translate_status(status_string):
    translations = {"released": LANG(32071),
                    "post production": LANG(32072),
                    "in production": LANG(32073),
                    "ended": LANG(32074),
                    "returning series": LANG(32075),
                    "planned": LANG(32076)}
    if status_string.lower() in translations:
        return translations[status_string.lower()]
    else:
        return status_string


def get_movie_lists(list_id):
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (list_id, SETTING("LanguageID"), SETTING("LanguageID")), 5)
    return handle_tmdb_misc(response["lists"]["results"])


def get_rated_media_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    if check_login():
        session_id = get_session_id()
        account_id = get_account_info()
        if not session_id:
            notify("Could not get session id")
            return []
        response = get_tmdb_data("account/%s/rated/%s?session_id=%s&language=%s&" % (account_id, media_type, session_id, SETTING("LanguageID")), 0)
    else:
        session_id = get_guest_session_id()
        if not session_id:
            notify("Could not get session id")
            return []
        response = get_tmdb_data("guest_session/%s/rated_movies?language=%s&" % (session_id, SETTING("LanguageID")), 0)
    if media_type == "tv/episodes":
        return handle_tmdb_episodes(response["results"])
    elif media_type == "tv":
        return handle_tmdb_tvshows(response["results"], False, None)
    else:
        return handle_tmdb_movies(response["results"], False, None)


def get_fav_items(media_type):
    '''takes "tv/episodes", "tv" or "movies"'''
    session_id = get_session_id()
    account_id = get_account_info()
    if not session_id:
        notify("Could not get session id")
        return []
    response = get_tmdb_data("account/%s/favorite/%s?session_id=%s&language=%s&" % (account_id, media_type, session_id, SETTING("LanguageID")), 0)
    if "results" in response:
        if media_type == "tv":
            return handle_tmdb_tvshows(response["results"], False, None)
        elif media_type == "tv/episodes":
            return handle_tmdb_episodes(response["results"])
        else:
            return handle_tmdb_movies(response["results"], False, None)
    else:
        return []


def get_movies_from_list(list_id, cache_time=5):
    '''
    get movie dict list from tmdb list.
    '''

    response = get_tmdb_data("list/%s?language=%s&" % (list_id, SETTING("LanguageID")), cache_time)
    return handle_tmdb_movies(response["items"], False, None)


def get_popular_actors():
    '''
    get dict list containing popular actors / directors / writers
    '''
    response = get_tmdb_data("person/popular?", 1)
    return handle_tmdb_people(response["results"])


def get_actor_credits(actor_id, media_type):
    '''
    media_type: movie or tv
    '''
    response = get_tmdb_data("person/%s/%s_credits?" % (actor_id, media_type), 1)
    return handle_tmdb_movies(response["cast"])


def get_keywords(movie_id):
    '''
    get dict list containing movie keywords
    '''
    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movie_id, SETTING("LanguageID"), SETTING("LanguageID")), 30)
    keywords = []
    if "keywords" in response:
        for keyword in response["keywords"]["keywords"]:
            keyword_dict = {'id': fetch(keyword, 'id'),
                            'name': keyword['name']}
            keywords.append(keyword_dict)
    return keywords


def get_similar_movies(movie_id):
    '''
    get dict list containing movies similar to *movie_id
    '''

    response = get_tmdb_data("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                             (movie_id, SETTING("LanguageID"), SETTING("LanguageID")), 10)
    if "similar" in response:
        return handle_tmdb_movies(response["similar"]["results"])
    else:
        return []


def get_similar_tvshows(tvshow_id):
    '''
    return list with similar tvshows for show with *tvshow_id (TMDB ID)
    '''
    session_str = ""
    if check_login():
        session_str = "session_id=%s&" % (get_session_id())
    response = get_tmdb_data("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                             (tvshow_id, SETTING("LanguageID"), SETTING("LanguageID"), session_str), 10)
    if "similar" in response:
        return handle_tmdb_tvshows(response["similar"]["results"])
    else:
        return []


def get_tmdb_shows(tvshow_type):
    '''
    return list with tv shows
    available types: airing, on_the_air, top_rated, popular
    '''
    response = get_tmdb_data("tv/%s?language=%s&" % (tvshow_type, SETTING("LanguageID")), 0.3)
    if "results" in response:
        return handle_tmdb_tvshows(response["results"], False, None)
    else:
        return []


def get_tmdb_movies(movie_type):
    '''
    return list with movies
    available types: now_playing, upcoming, top_rated, popular
    '''
    response = get_tmdb_data("movie/%s?language=%s&" % (movie_type, SETTING("LanguageID")), 0.3)
    if "results" in response:
        return handle_tmdb_movies(response["results"], False, None)
    else:
        return []


def get_set_movies(set_id):
    '''
    return list with movies which are part of set with *set_id
    '''
    response = get_tmdb_data("collection/%s?language=%s&append_to_response=images&include_image_language=en,null,%s&" % (set_id, SETTING("LanguageID"), SETTING("LanguageID")), 14)
    if response:
        artwork = get_image_urls(poster=response.get("poster_path"),
                                 fanart=response.get("backdrop_path"))
        info = {"label": response["name"],
                "overview": response["overview"],
                "id": response["id"]}
        info.update(artwork)
        return handle_tmdb_movies(response.get("parts", [])), info
    else:
        return [], {}


def get_person_movies(person_id):
    response = get_tmdb_data("person/%s/credits?language=%s&" % (person_id, SETTING("LanguageID")), 14)
    # return handle_tmdb_movies(response["crew"]) + handle_tmdb_movies(response["cast"])
    if "crew" in response:
        return handle_tmdb_movies(response["crew"])
    else:
        return []


def search_media(media_name=None, year='', media_type="movie"):
    '''
    return list of items with type *media_type for search with *media_name
    '''
    search_query = url_quote("%s %s" % (media_name, year))
    if not search_query:
        return None
    response = get_tmdb_data("search/%s?query=%s&language=%s&include_adult=%s&" % (media_type, search_query, SETTING("LanguageID"), include_adult), 1)
    if not response == "Empty":
        for item in response['results']:
            if item['id']:
                return item['id']
    return None

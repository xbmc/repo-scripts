import xbmcaddon
import os
import xbmc
from YouTube import *
from Utils import *
import urllib
import threading
from urllib2 import Request, urlopen


moviedb_key = '34142515d9d23817496eeb4ff1d223d0'
addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')
addon_strings = addon.getLocalizedString
Addon_Data_Path = os.path.join(xbmc.translatePath("special://profile/addon_data/%s" % addon_id).decode("utf-8"))
base_url = ""
poster_size = ""
fanart_size = ""
homewindow = xbmcgui.Window(10000)
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-agent': 'XBMC/14.0 ( phil65@kodi.tv )'
}
poster_sizes = ["w92", "w154", "w185", "w342", "w500", "w780", "original"]
logo_sizes = ["w45", "w92", "w154", "w185", "w300", "w500", "original"]
backdrop_sizes = ["w300", "w780", "w1280", "original"]
profile_sizes = ["w45", "w185", "h632", "original"]
still_sizes = ["w92", "w185", "w300", "original"]
include_adult = str(addon.getSetting("include_adults")).lower()


def checkLogin():
    if addon.getSetting("tmdb_username"):
        session_id = get_session_id()
        if session_id:
            return "True"
    return ""


def RateMedia(media_type, media_id, rating):
    if checkLogin():
        session_id_string = "session_id=" + get_session_id()
    else:
        session_id_string = "guest_session_id=" + get_guest_session_id()
    values = '{"value": %.1f}' % rating
    log(values)
    if media_type == "episode":
        url = "http://api.themoviedb.org/3/tv/%s/season/%s/episode/%s/rating?api_key=%s&%s" % (str(media_id[0]), str(media_id[1]), str(media_id[2]), moviedb_key, session_id_string)
        log(url)
    else:
        url = "http://api.themoviedb.org/3/%s/%s/rating?api_key=%s&%s" % (media_type, str(media_id), moviedb_key, session_id_string)
    request = Request(url, data=values, headers=headers)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    Notify(addon_name, results["status_message"])


def ChangeFavStatus(media_id=None, media_type="movie", status="true"):
    session_id = get_session_id()
    account_id = get_account_info()
    values = '{"media_type": "%s", "media_id": %s, "favorite": %s}' % (media_type, str(media_id), status)
    url = "http://api.themoviedb.org/3/account/%s/favorite?session_id=%s&api_key=%s" % (str(account_id), str(session_id), moviedb_key)
    log(url)
    request = Request(url, data=values, headers=headers)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    Notify(addon_name, results["status_message"])


def CreateList(listname):
    session_id = get_session_id()
    url = "http://api.themoviedb.org/3/list?api_key=%s&session_id=%s" % (moviedb_key, session_id)
    values = {'name': '%s' % listname, 'description': 'List created by ExtendedInfo Script for Kodi.'}
    request = Request(url, data=simplejson.dumps(values), headers=headers)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    # prettyprint(results)
    Notify(addon_name, results["status_message"])
    return results["list_id"]


def RemoveList(list_id):
    session_id = get_session_id()
    url = "http://api.themoviedb.org/3/list/%s?api_key=%s&session_id=%s" % (list_id, moviedb_key, session_id)
    log("Remove List: " + url)
    # prettyprint(results)
    values = {'media_id': list_id}
    request = Request(url, data=simplejson.dumps(values), headers=headers)
    request.get_method = lambda: 'DELETE'
    response = urlopen(request).read()
    results = simplejson.loads(response)
    Notify(addon_name, results["status_message"])
    return results["list_id"]

def ChangeListStatus(list_id, movie_id, status):
    if status:
        method = "add_item"
    else:
        method = "remove_item"
    session_id = get_session_id()
    url = "http://api.themoviedb.org/3/list/%s/%s?api_key=%s&session_id=%s" % (list_id, method, moviedb_key, session_id)
    log(url)
    values = {'media_id': movie_id}
    request = Request(url, data=simplejson.dumps(values), headers=headers)
    response = urlopen(request).read()
    results = simplejson.loads(response)
    Notify(addon_name, results["status_message"])


def GetAccountLists(cache_time=0):
    session_id = get_session_id()
    account_id = get_account_info()
    if session_id and account_id:
        response = GetMovieDBData("account/%s/lists?session_id=%s&" % (str(account_id), session_id), cache_time)
        return response["results"]
    else:
        return False


def get_account_info():
    session_id = get_session_id()
    response = GetMovieDBData("account?session_id=%s&" % session_id, 999999)
    # prettyprint(response)
    return response["id"]

def get_certification_list(media_type):
    response = GetMovieDBData("certification/%s/list?" % media_type, 999999)
    return response["certifications"]

def get_guest_session_id():
    response = GetMovieDBData("authentication/guest_session/new?", 999999)
    # prettyprint(response)
    return response["guest_session_id"]


def get_session_id():
    request_token = auth_request_token()
    response = GetMovieDBData("authentication/session/new?request_token=%s&" % request_token, 99999)
    # prettyprint(response)
    if response and "success" in response:
        passDictToSkin({"tmdb_logged_in": "true"})
        return response["session_id"]
    else:
        passDictToSkin({"tmdb_logged_in": ""})
        Notify("login failed")
        return None


def get_request_token():
    response = GetMovieDBData("authentication/token/new?", 999999)
    # prettyprint(response)
    return response["request_token"]


def auth_request_token():
    request_token = get_request_token()
    username = addon.getSetting("tmdb_username")
    password = addon.getSetting("tmdb_password")
    response = GetMovieDBData("authentication/token/validate_with_login?request_token=%s&username=%s&password=%s&" % (request_token, username, password), 999999)
    # prettyprint(response)
    if "success" in response and response["success"]:
        return response["request_token"]
    else:
        return None


def HandleTMDBMultiSearchResult(results=[]):
    listitems = []
    for item in results:
        if item["media_type"] == "movie":
            listitem = HandleTMDBMovieResult([item])[0]
        elif item["media_type"] == "tv":
            listitem = HandleTMDBTVShowResult([item])[0]
        else:
            listitem = HandleTMDBPeopleResult([item])[0]
        listitems.append(listitem)
    return listitems

def HandleTMDBMovieResult(results=[], local_first=True, sortkey="Year"):
    movies = []
    ids = []
    log("starting HandleTMDBMovieResult")
    for movie in results:
        tmdb_id = str(fetch(movie, 'id'))
        if ("backdrop_path" in movie) and (movie["backdrop_path"]):
            backdrop_path = base_url + fanart_size + movie['backdrop_path']
        else:
            backdrop_path = ""
        if ("poster_path" in movie) and (movie["poster_path"]):
            poster_path = base_url + poster_size + movie['poster_path']
            small_poster_path = base_url + "w342" + movie["poster_path"]
        else:
            poster_path = ""
            small_poster_path = ""
        release_date = fetch(movie, 'release_date')
        if release_date:
            year = release_date[:4]
            time_comparer = release_date.replace("-", "")
        else:
            year = ""
            time_comparer = ""
        trailer = "plugin://script.extendedinfo/?info=playtrailer&&id=" + tmdb_id
        if addon.getSetting("infodialog_onclick"):
            path = 'plugin://script.extendedinfo/?info=extendedinfo&&id=%s' % tmdb_id
        else:
            path = trailer
        newmovie = {'Art(fanart)': backdrop_path,
                    'Art(poster)': small_poster_path,  # needs to be adjusted to poster_path (-->skin)
                    'Thumb': small_poster_path,
                    'Poster': small_poster_path,
                    'fanart': backdrop_path,
                    'Title': fetch(movie, 'title'),
                    'Label': fetch(movie, 'title'),
                    'OriginalTitle': fetch(movie, 'original_title'),
                    'ID': tmdb_id,
                    'Path': path,
                    'media_type': "movie",
                    'Trailer': trailer,
                    'Rating': fetch(movie, 'vote_average'),
                    'credit_id': fetch(movie, 'credit_id'),
                    'character': fetch(movie, 'character'),
                    'job': fetch(movie, 'job'),
                    'department': fetch(movie, 'department'),
                    'Votes': fetch(movie, 'vote_count'),
                    'User_Rating': fetch(movie, 'rating'),
                    'Year': year,
                    'time_comparer': time_comparer,
                    'Premiered': release_date}
        if not tmdb_id in ids:
            ids.append(tmdb_id)
            movies.append(newmovie)
    movies = CompareWithLibrary(movies, local_first, sortkey)
    return movies


def HandleTMDBTVShowResult(results, local_first=True, sortkey="year"):
    tvshows = []
    ids = []
    log("starting HandleTMDBTVShowResult")
    for tv in results:
        tmdb_id = fetch(tv, 'id')
        poster_path = ""
        duration = ""
        year = ""
        backdrop_path = ""
        if ("backdrop_path" in tv) and (tv["backdrop_path"]):
            backdrop_path = base_url + fanart_size + tv['backdrop_path']
        if ("poster_path" in tv) and (tv["poster_path"]):
            poster_path = base_url + poster_size + tv['poster_path']
        if "episode_run_time" in tv:
            if len(tv["episode_run_time"]) > 1:
                duration = "%i - %i" % (min(tv["episode_run_time"]), max(tv["episode_run_time"]))
            elif len(tv["episode_run_time"]) == 1:
                duration = "%i" % (tv["episode_run_time"][0])
            else:
                duration = ""
        release_date = fetch(tv, 'first_air_date')
        if release_date:
            year = release_date[:4]
        newtv = {'Art(fanart)': backdrop_path,
                 'Art(poster)': poster_path,
                 'Thumb': poster_path,
                 'Poster': poster_path,
                 'fanart': backdrop_path,
                 'Title': fetch(tv, 'name'),
                 'TVShowTitle': fetch(tv, 'name'),
                 'OriginalTitle': fetch(tv, 'original_name'),
                 'Duration': duration,
                 'ID': tmdb_id,
                 'credit_id': fetch(tv, 'credit_id'),
                 'Plot': fetch(tv, "overview"),
                 'year': year,
                 'media_type': "tv",
                 'Path': 'plugin://script.extendedinfo/?info=extendedtvinfo&&id=%s' % tmdb_id,
                 'Rating': fetch(tv, 'vote_average'),
                 'User_Rating': str(fetch(tv, 'rating')),
                 'Votes': fetch(tv, 'vote_count'),
                 'number_of_episodes': fetch(tv, 'number_of_episodes'),
                 'number_of_seasons': fetch(tv, 'number_of_seasons'),
                 'Release_Date': release_date,
                 'ReleaseDate': release_date,
                 'Premiered': release_date}
        if not tmdb_id in ids:
            ids.append(tmdb_id)
            tvshows.append(newtv)
    # tvshows = CompareWithLibrary(tvshows, local_first, sortkey)
    return tvshows


def HandleTMDBEpisodesResult(results):
    listitems = []
    for item in results:
        still_path = ""
        still_path_small = ""
        if "still_path" in item and item["still_path"]:
            still_path = base_url + "original" + item['still_path']
            still_path_small = base_url + "w300" + item['still_path']
        listitem = {'Art(poster)': still_path,
                    'Poster': still_path,
                    'Thumb': still_path_small,
                    'Title': cleanText(fetch(item, 'name')),
                    'release_date': fetch(item, 'air_date'),
                    'episode': fetch(item, 'episode_number'),
                    'production_code': fetch(item, 'production_code'),
                    'season': fetch(item, 'season_number'),
                    'Rating': fetch(item, 'vote_average'),
                    'Votes': fetch(item, 'vote_count'),
                    'ID': fetch(item, 'id'),
                    'Description': cleanText(fetch(item, 'overview'))}
        listitems.append(listitem)
    return listitems


def HandleTMDBMiscResult(results):
    listitems = []
    for item in results:
        poster_path = ""
        small_poster_path = ""
        if ("poster_path" in item) and (item["poster_path"]):
            poster_path = base_url + poster_size + item['poster_path']
            small_poster_path = base_url + "w342" + item["poster_path"]
        release_date = fetch(item, 'release_date')
        if release_date:
            year = release_date[:4]
        else:
            year = ""
        listitem = {'Art(poster)': poster_path,
                    'Poster': poster_path,
                    'Thumb': small_poster_path,
                    'Title': cleanText(fetch(item, 'name')),
                    'certification': fetch(item, 'certification') + fetch(item, 'rating'),
                    'item_count': fetch(item, 'item_count'),
                    'favorite_count': fetch(item, 'favorite_count'),
                    'release_date': release_date,
                    'year': year,
                    'iso_3166_1': fetch(item, 'iso_3166_1'),
                    'author': fetch(item, 'author'),
                    'content': cleanText(fetch(item, 'content')),
                    'ID': fetch(item, 'id'),
                    'url': fetch(item, 'url'),
                    'Description': cleanText(fetch(item, 'description'))}
        listitems.append(listitem)
    return listitems

def HandleTMDBSeasonResult(results):
    listitems = []
    for season in results:
        year = ""
        poster_path = ""
        season_number = str(fetch(season, 'season_number'))
        small_poster_path = ""
        air_date = fetch(season, 'air_date')
        if air_date:
            year = air_date[:4]
        if ("poster_path" in season) and season["poster_path"]:
            poster_path = base_url + poster_size + season['poster_path']
            small_poster_path = base_url + "w342" + season["poster_path"]
        if season_number == "0":
            Title = "Specials"
        else:
            Title = "Season %s" % season_number
        listitem = {'Art(poster)': poster_path,
                    'Poster': poster_path,
                    'Thumb': small_poster_path,
                    'Title': Title,
                    'Season': season_number,
                    'air_date': air_date,
                    'Year': year,
                    'ID': fetch(season, 'id')}
        listitems.append(listitem)
    return listitems




def HandleTMDBVideoResult(results):
    listitems = []
    for item in results:
        image = "http://i.ytimg.com/vi/" + fetch(item, 'key') + "/0.jpg"
        listitem = {'Thumb': image,
                    'Title': fetch(item, 'name'),
                    'iso_639_1': fetch(item, 'iso_639_1'),
                    'type': fetch(item, 'type'),
                    'key': fetch(item, 'key'),
                    'youtube_id': fetch(item, 'key'),
                    'site': fetch(item, 'site'),
                    'ID': fetch(item, 'id'),
                    'size': fetch(item, 'size')}
        listitems.append(listitem)
    return listitems


def HandleTMDBPeopleResult(results):
    people = []
    for person in results:
        image = ""
        image_small = ""
        description = "[B]Known for[/B]:[CR][CR]"
        if "known_for" in results:
            for movie in results["known_for"]:
                description = description + movie["title"] + " (%s)" % (movie["release_date"]) + "[CR]"
        builtin = 'RunScript(script.extendedinfo,info=extendedactorinfo,id=%s)' % str(person['id'])
        if "profile_path" in person and person["profile_path"]:
            image = base_url + poster_size + person["profile_path"]
            image_small = base_url + "w342" + person["profile_path"]
        alsoknownas = " / ".join(fetch(person, 'also_known_as'))
        newperson = {'adult': str(fetch(person, 'adult')),
                     'name': person['name'],
                     'title': person['name'],
                     'also_known_as': alsoknownas,
                     'alsoknownas': alsoknownas,
                     'biography': cleanText(fetch(person, 'biography')),
                     'birthday': fetch(person, 'birthday'),
                     'age': calculate_age(fetch(person, 'birthday')),
                     'character': fetch(person, 'character'),
                     'department': fetch(person, 'department'),
                     'job': fetch(person, 'job'),
                     'media_type': "person",
                     'description': description,
                     'plot': description,
                     'id': str(person['id']),
                     'cast_id': str(fetch(person, 'cast_id')),
                     'credit_id': str(fetch(person, 'credit_id')),
                     'path': "plugin://script.extendedinfo/?info=action&&id=" + builtin,
                     'deathday': fetch(person, 'deathday'),
                     'place_of_birth': fetch(person, 'place_of_birth'),
                     'placeofbirth': fetch(person, 'place_of_birth'),
                     'homepage': fetch(person, 'homepage'),
                     'thumb': image_small,
                     'icon': image_small,
                     'poster': image}
        people.append(newperson)
    return people


def HandleTMDBPeopleImagesResult(results):
    images = []
    for item in results:
        image = {'aspectratio': item['aspect_ratio'],
                 'thumb': base_url + "w342" + item['file_path'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1"),
                 'poster': base_url + poster_size + item['file_path'],
                 'original': base_url + "original" + item['file_path']}
        images.append(image)
    return images


def HandleTMDBPeopleTaggedImagesResult(results):
    images = []
    for item in results:
        image = {'aspectratio': item['aspect_ratio'],
                 'thumb': base_url + "w342" + item['file_path'],
                 'vote_average': fetch(item, "vote_average"),
                 'iso_639_1': fetch(item, "iso_639_1"),
                 'Title': fetch(item["media"], "title"),
                 'mediaposter': base_url + poster_size + fetch(item["media"], "poster_path"),
                 'poster': base_url + poster_size + item['file_path'],
                 'original': base_url + "original" + item['file_path']}
        images.append(image)
    return images


def HandleTMDBCompanyResult(results):
    companies = []
    log("starting HandleLastFMCompanyResult")
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


def SearchforCompany(Company):
    import re
    regex = re.compile('\(.+?\)')
    Company = regex.sub('', Company)
    log(Company)
    response = GetMovieDBData("search/company?query=%s&" % urllib.quote_plus(Company), 10)
    try:
        return response["results"]
    except:
        log("could not find Company ID")
        return ""


def MultiSearch(String):
    response = GetMovieDBData("search/multi?query=%s&" % urllib.quote_plus(String), 1)
    if response and "results" in response:
        return response["results"]
    else:
        log("Error when searching")
        return ""


def GetPersonID(person):
    persons = person.split(" / ")
    # if len(persons) > 1:
    #     personlist = []
    #     for item in persons:
    #         personlist.append(item["name"])
    #     selection = xbmcgui.Dialog().select("Select Actor", personlist)
    # else:
    person = persons[0]
    response = GetMovieDBData("search/person?query=%s&include_adult=%s&" % (urllib.quote_plus(person), include_adult), 30)
    if response and "results" in response:
        if len(response["results"]) > 1:
            names = []
            for item in response["results"]:
                names.append(item["name"])
            selection = xbmcgui.Dialog().select(addon.getLocalizedString(32151), names)
            if selection > -1:
                return response["results"][selection]
        else:
            return response["results"][0]
    else:
        log("could not find Person ID")
    return False


def GetKeywordID(keyword):
    response = GetMovieDBData("search/keyword?query=%s&include_adult=%s&" % (urllib.quote_plus(keyword), include_adult), 30)
    if response and "results" in response and response["results"]:
        if len(response["results"]) > 1:
            names = []
            for item in response["results"]:
                names.append(item["name"])
            selection = xbmcgui.Dialog().select(addon.getLocalizedString(32114), names)
            if selection > -1:
                return response["results"][selection]
        else:
            return response["results"][0]
    else:
        log("could not find Keyword ID")
        return False


def SearchForSet(setname):
    setname = setname.replace("[", "").replace("]", "").replace("Kollektion", "Collection")
    response = GetMovieDBData("search/collection?query=%s&language=%s&" % (urllib.quote_plus(setname.encode("utf-8")), addon.getSetting("LanguageID")), 14)
    try:
        return response["results"][0]["id"]
    except:
        return ""


def GetMovieDBData(url="", cache_days=14, folder=False):
    # session_id = get_session_id()
    # url = "http://api.themoviedb.org/3/%sapi_key=%s&session_id=%s" % (url, moviedb_key, session_id)
    url = "http://api.themoviedb.org/3/%sapi_key=%s" % (url, moviedb_key)
    global base_url
    global poster_size
    global fanart_size
    if not base_url:
        base_url = True
        base_url, poster_size, fanart_size = GetMovieDBConfig()
    results = Get_JSON_response(url, cache_days, folder)
    return results


def GetMovieDBConfig():
    return ("http://image.tmdb.org/t/p/", "w500", "w1280")
    response = GetMovieDBData("configuration?", 60)
    # prettyprint(response)
    if response:
        return (response["images"]["base_url"], response["images"]["poster_sizes"][-2], response["images"]["backdrop_sizes"][-2])
    else:
        return ("", "", "")


def GetCompanyInfo(company_id):
    response = GetMovieDBData("company/%s/movies?append_to_response=movies&" % (company_id), 30)
    if response and "results" in response:
        return HandleTMDBMovieResult(response["results"])
    else:
        return []


def GetCreditInfo(credit_id):
    response = GetMovieDBData("credit/%s?language=%s&" % (str(credit_id), addon.getSetting("LanguageID")), 30)
    prettyprint(response)
    # if response and "results" in response:
        # return HandleTMDBMovieResult(response["results"])
    # else:
    #     return []

# def millify(n):
#     import math
#     millnames = [' ', '.000', ' Million', ' Billion', ' Trillion']
#     millidx = max(0, min(len(millnames) - 1, int(math.floor(math.log10(abs(n)) / 3.0))))
#     if millidx == 3:
#             return '%.1f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
#     else:
#             return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])


def millify(n):
    millnames = [' ', '.000', ' Million', ' Billion', ' Trillion']
    if n and n > 100:
        n = float(n)
        char_count = len(str(n))
        millidx = (char_count / 3) - 1
        if millidx == 3 or char_count == 9:
            return '%.2f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
        else:
            return '%.0f%s' % (n / 10 ** (3 * millidx), millnames[millidx])
    else:
        return ""


def GetSeasonInfo(tmdb_tvshow_id, tvshowname, season_number):
    if not tmdb_tvshow_id:
        response = GetMovieDBData("search/tv?query=%s&language=%s&" % (urllib.quote_plus(tvshowname), addon.getSetting("LanguageID")), 30)
        tmdb_tvshow_id = str(response['results'][0]['id'])
    response = GetMovieDBData("tv/%s/season/%s?append_to_response=videos,images,external_ids,credits&language=%s&include_image_language=en,null,%s&" % (tmdb_tvshow_id, season_number, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 7)
    # prettyprint(response)
    videos = []
    backdrops = []
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + poster_size + response['poster_path']
        poster_path_small = base_url + "w342" + response['poster_path']
    else:
        poster_path = ""
        poster_path_small = ""
    if response.get("name", False):
        Title = response["name"]
    elif season_number == "0":
        Title = "Specials"
    else:
        Title = "Season %s" % season_number
    season = {'SeasonDescription': cleanText(response["overview"]),
              'Plot': cleanText(response["overview"]),
              'TVShowTitle': tvshowname,
              'Thumb': poster_path_small,
              'Poster': poster_path,
              'Title': Title,
              'ReleaseDate': response["air_date"],
              'AirDate': response["air_date"]}
    if "videos" in response:
        videos = HandleTMDBVideoResult(response["videos"]["results"])
    if "backdrops" in response["images"]:
        backdrops = HandleTMDBPeopleImagesResult(response["images"]["backdrops"])
    answer = {"general": season,
              "actors": HandleTMDBPeopleResult(response["credits"]["cast"]),
              "crew": HandleTMDBPeopleResult(response["credits"]["crew"]),
              "videos": videos,
              "episodes": HandleTMDBEpisodesResult(response["episodes"]),
              "images": HandleTMDBPeopleImagesResult(response["images"]["posters"]),
              "backdrops": backdrops}
    return answer


def GetMovieDBID(imdbid):
    response = GetMovieDBData("find/tt%s?external_source=imdb_id&language=%s&" % (imdbid.replace("tt", ""), addon.getSetting("LanguageID")), 30)
    return response["movie_results"][0]["id"]

def Get_Show_TMDB_ID(tvdb_id=None, source="tvdb_id"):
    response = GetMovieDBData("find/%s?external_source=%s&language=%s&" % (tvdb_id, source, addon.getSetting("LanguageID")), 30)
    try:
        return response["tv_results"][0]["id"]
    except:
        Notify("TVShow Info not available.")
        return None


def GetTrailer(movieid=None):
    response = GetMovieDBData("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                              (movieid, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 30)
    if response and "videos" in response and response['videos']['results']:
        youtube_id = response['videos']['results'][0]['key']
        return youtube_id
    Notify("Could not get trailer")
    return ""


def GetExtendedMovieInfo(movieid=None, dbid=None, cache_time=14):
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = GetMovieDBData("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&%s" %
                              (movieid, addon.getSetting("LanguageID"), addon.getSetting("LanguageID"), session_string), cache_time)
    # prettyprint(response)
    authors = []
    directors = []
    genres = []
    year = ""
    Studio = []
    mpaa = ""
    SetName = ""
    SetID = ""
    poster_path = ""
    poster_path_small = ""
    backdrop_path = ""
    if not response:
        Notify("Could not get movie information")
        return {}
    for item in response['genres']:
        genres.append(item["name"])
    for item in response['credits']['crew']:
        if item["job"] == "Author":
            authors.append(item["name"])
        if item["job"] == "Director":
            directors.append(item["name"])
    if response['releases']['countries']:
        mpaa = response['releases']['countries'][0]['certification']
    for item in response['production_companies']:
        Studio.append(item["name"])
    Set = fetch(response, "belongs_to_collection")
    if Set:
        SetName = fetch(Set, "name")
        SetID = fetch(Set, "id")
    if 'release_date' in response and fetch(response, 'release_date'):
        year = fetch(response, 'release_date')[:4]
    if ("backdrop_path" in response) and (response["backdrop_path"]):
        backdrop_path = base_url + fanart_size + response['backdrop_path']
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + "original" + response['poster_path']
        poster_path_small = base_url + "w342" + response['poster_path']
    path = 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % str(fetch(response, "id"))
    movie = {'Art(fanart)': backdrop_path,
             'Art(poster)': poster_path,
             'Thumb': poster_path_small,
             'Poster': poster_path,
             'fanart': backdrop_path,
             'Title': fetch(response, 'title'),
             'Label': fetch(response, 'title'),
             'Tagline': fetch(response, 'tagline'),
             'Duration': fetch(response, 'runtime'),
             'mpaa': mpaa,
             'Director': " / ".join(directors),
             'Writer': " / ".join(authors),
             'Budget': millify(fetch(response, 'budget')),
             'Revenue': millify(fetch(response, 'revenue')),
             'Homepage': fetch(response, 'homepage'),
             'Set': SetName,
             'SetId': SetID,
             'ID': fetch(response, 'id'),
             'imdb_id': fetch(response, 'imdb_id'),
             'Plot': cleanText(fetch(response, 'overview')),
             'OriginalTitle': fetch(response, 'original_title'),
             'Country': fetch(response, 'original_language'),
             'Genre': " / ".join(genres),
             'Rating': fetch(response, 'vote_average'),
             'Votes': fetch(response, 'vote_count'),
             'Adult': str(fetch(response, 'adult')),
             'Popularity': fetch(response, 'popularity'),
             'Status': fetch(response, 'status'),
             'Path': path,
             'ReleaseDate': fetch(response, 'release_date'),
             'Premiered': fetch(response, 'release_date'),
             'Studio': " / ".join(Studio),
             'Year': year}
    if "videos" in response:
        videos = HandleTMDBVideoResult(response["videos"]["results"])
    else:
        videos = []
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    similar_thread = Get_ListItems_Thread(HandleTMDBMovieResult, response["similar"]["results"])
    actor_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["cast"])
    crew_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["crew"])
    poster_thread = Get_ListItems_Thread(HandleTMDBPeopleImagesResult, response["images"]["posters"])
    threads = [similar_thread, actor_thread, crew_thread, poster_thread]
    for item in threads:
        item.start()
    for item in threads:
        item.join()
    synced_movie = CompareWithLibrary([movie])
    if synced_movie:
        answer = {"general": synced_movie[0],
                  "actors": actor_thread.listitems,
                  "similar": similar_thread.listitems,
                  "lists": HandleTMDBMiscResult(response["lists"]["results"]),
                  "studios": HandleTMDBMiscResult(response["production_companies"]),
                  "releases": HandleTMDBMiscResult(response["releases"]["countries"]),
                  "crew": crew_thread.listitems,
                  "genres": HandleTMDBMiscResult(response["genres"]),
                  "keywords": HandleTMDBMiscResult(response["keywords"]["keywords"]),
                  "reviews": HandleTMDBMiscResult(response["reviews"]["results"]),
                  "videos": videos,
                  "account_states": account_states,
                  "images": poster_thread.listitems,
                  "backdrops": HandleTMDBPeopleImagesResult(response["images"]["backdrops"])}
    else:
        answer = []
    return answer


def GetExtendedTVShowInfo(tvshow_id=None, cache_time=7):
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = GetMovieDBData("tv/%s?append_to_response=account_states,alternative_titles,content_ratings,credits,external_ids,images,keywords,rating,similar,translations,videos&language=%s&include_image_language=en,null,%s&%s" %
                              (str(tvshow_id), addon.getSetting("LanguageID"), addon.getSetting("LanguageID"), session_string), cache_time)
    # prettyprint(response)
    videos = []
    similar_thread = Get_ListItems_Thread(HandleTMDBTVShowResult, response["similar"]["results"])
    actor_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["cast"])
    crew_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["crew"])
    poster_thread = Get_ListItems_Thread(HandleTMDBPeopleImagesResult, response["images"]["posters"])
    threads = [similar_thread, actor_thread, crew_thread, poster_thread]
    for item in threads:
        item.start()
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    if "videos" in response:
        videos = HandleTMDBVideoResult(response["videos"]["results"])
    tmdb_id = fetch(response, 'id')
    poster_path = ""
    duration = ""
    year = ""
    backdrop_path = ""
    if ("backdrop_path" in response) and (response["backdrop_path"]):
        backdrop_path = base_url + fanart_size + response['backdrop_path']
    if ("poster_path" in response) and (response["poster_path"]):
        poster_path = base_url + "original" + response['poster_path']
    if "episode_run_time" in response:
        if len(response["episode_run_time"]) > 1:
            duration = "%i - %i" % (min(response["episode_run_time"]), max(response["episode_run_time"]))
        elif len(response["episode_run_time"]) == 1:
            duration = "%i" % (response["episode_run_time"][0])
        else:
            duration = ""
    release_date = fetch(response, 'first_air_date')
    if release_date:
        year = release_date[:4]
    newtv = {'Art(fanart)': backdrop_path,
             'Art(poster)': poster_path,
             'Thumb': poster_path,
             'Poster': poster_path,
             'fanart': backdrop_path,
             'Title': fetch(response, 'name'),
             'TVShowTitle': fetch(response, 'name'),
             'OriginalTitle': fetch(response, 'original_name'),
             'Duration': duration,
             'ID': tmdb_id,
             'credit_id': fetch(response, 'credit_id'),
             'Plot': cleanText(fetch(response, "overview")),
             'year': year,
             'media_type': "tv",
             'Path': 'plugin://script.extendedinfo/?info=extendedtvinfo&&id=%s' % tmdb_id,
             'Rating': fetch(response, 'vote_average'),
             'User_Rating': str(fetch(response, 'rating')),
             'Votes': fetch(response, 'vote_count'),
             'Status': fetch(response, 'status'),
             'ShowType': fetch(response, 'type'),
             'homepage': fetch(response, 'homepage'),
             'last_air_date': fetch(response, 'last_air_date'),
             'first_air_date': release_date,
             'number_of_episodes': fetch(response, 'number_of_episodes'),
             'number_of_seasons': fetch(response, 'number_of_seasons'),
             'in_production': fetch(response, 'in_production'),
             'Release_Date': release_date,
             'ReleaseDate': release_date,
             'Premiered': release_date}
    for item in threads:
        item.join()
    answer = {"general": newtv,
              "actors": actor_thread.listitems,
              "similar": similar_thread.listitems,
              "studios": HandleTMDBMiscResult(response["production_companies"]),
              "networks": HandleTMDBMiscResult(response["networks"]),
              "certifications": HandleTMDBMiscResult(response["content_ratings"]["results"]),
              "crew": crew_thread.listitems,
              "genres": HandleTMDBMiscResult(response["genres"]),
              "keywords": HandleTMDBMiscResult(response["keywords"]["results"]),
              "videos": videos,
              "account_states": account_states,
              "seasons": HandleTMDBSeasonResult(response["seasons"]),
              "images": poster_thread.listitems,
              "backdrops": HandleTMDBPeopleImagesResult(response["images"]["backdrops"])}
    return answer

def GetExtendedEpisodeInfo(tvshow_id, season, episode, cache_time=7):
    session_string = ""
    if checkLogin():
        session_string = "session_id=%s&" % (get_session_id())
    response = GetMovieDBData("tv/%s/season/%s/episode/%s?append_to_response=account_states,credits,external_ids,images,rating,videos&language=%s&include_image_language=en,null,%s&%s&" %
                              (str(tvshow_id), str(season), str(episode), addon.getSetting("LanguageID"), addon.getSetting("LanguageID"), session_string), cache_time)
    videos = []
    # prettyprint(response)
    if "videos" in response:
        videos = HandleTMDBVideoResult(response["videos"]["results"])
    actor_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["cast"])
    crew_thread = Get_ListItems_Thread(HandleTMDBPeopleResult, response["credits"]["crew"])
    still_thread = Get_ListItems_Thread(HandleTMDBPeopleImagesResult, response["images"]["stills"])
    threads = [actor_thread, crew_thread, still_thread]
    for item in threads:
        item.start()
    if "account_states" in response:
        account_states = response["account_states"]
    else:
        account_states = None
    for item in threads:
        item.join()
    answer = {"general": HandleTMDBEpisodesResult([response])[0],
              "actors": actor_thread.listitems,
              "account_states": account_states,
              "crew": crew_thread.listitems,
              # "genres": HandleTMDBMiscResult(response["genres"]),
              "videos": videos,
              # "seasons": HandleTMDBSeasonResult(response["seasons"]),
              "images": still_thread.listitems}
    return answer


def GetExtendedActorInfo(actorid):
    response = GetMovieDBData("person/%s?append_to_response=tv_credits,movie_credits,combined_credits,images,tagged_images&" % (actorid), 1)
    movie_roles = Get_ListItems_Thread(HandleTMDBMovieResult, response["movie_credits"]["cast"])
    tvshow_roles = Get_ListItems_Thread(HandleTMDBTVShowResult, response["tv_credits"]["cast"])
    movie_crew_roles = Get_ListItems_Thread(HandleTMDBMovieResult, response["movie_credits"]["crew"])
    tvshow_crew_roles = Get_ListItems_Thread(HandleTMDBTVShowResult, response["tv_credits"]["crew"])
    poster_thread = Get_ListItems_Thread(HandleTMDBPeopleImagesResult, response["images"]["profiles"])
    threads = [movie_roles, tvshow_roles, movie_crew_roles, tvshow_crew_roles, poster_thread]
    for item in threads:
        item.start()
    for item in threads:
        item.join()
    tagged_images = []
    if "tagged_images" in response:
        tagged_images = HandleTMDBPeopleTaggedImagesResult(response["tagged_images"]["results"])
    answer = {"general": HandleTMDBPeopleResult([response])[0],
              "movie_roles": movie_roles.listitems,
              "tvshow_roles": tvshow_roles.listitems,
              "movie_crew_roles": movie_crew_roles.listitems,
              "tvshow_crew_roles": tvshow_crew_roles.listitems,
              "tagged_images": tagged_images,
              "images": poster_thread.listitems}
    return answer


def GetMovieLists(list_id):
    response = GetMovieDBData("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                              (list_id, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 5)
    return HandleTMDBMiscResult(response["lists"]["results"])


def GetRatedMedia(media_type):
    if checkLogin():
        session_id = get_session_id()
        account_id = get_account_info()
        response = GetMovieDBData("account/%s/rated/%s?session_id=%s&language=%s&" % (str(account_id), media_type, str(session_id), addon.getSetting("LanguageID")), 0)
    else:
        session_id = get_guest_session_id()
        response = GetMovieDBData("guest_session/%s/rated_movies?language=%s&" % (str(session_id), addon.getSetting("LanguageID")), 0)
    if media_type == "tv":
        return HandleTMDBTVShowResult(response["results"], False, None)
    else:
        return HandleTMDBMovieResult(response["results"], False, None)


def GetFavItems(media_type):
    session_id = get_session_id()
    account_id = get_account_info()
    response = GetMovieDBData("account/%s/favorite/%s?session_id=%s&language=%s&" % (str(account_id), media_type, str(session_id), addon.getSetting("LanguageID")), 0)
    return HandleTMDBMovieResult(response["results"], False, None)


def GetMoviesFromList(list_id, cache_time=5):
    response = GetMovieDBData("list/%s?language=%s&" % (str(list_id), addon.getSetting("LanguageID")), cache_time)
  #  prettyprint(response)
    return HandleTMDBMovieResult(response["items"], False, None)


def GetPopularActorList():
    response = GetMovieDBData("person/popular?", 1)
    return HandleTMDBPeopleResult(response["results"])


def GetActorMovieCredits(actor_id):
    response = GetMovieDBData("person/%s/movie_credits?" % (actor_id), 1)
    return HandleTMDBMovieResult(response["cast"])


def GetActorTVShowCredits(actor_id):
    response = GetMovieDBData("person/%s/tv_credits?" % (actor_id), 1)
    return HandleTMDBMovieResult(response["cast"])


def GetMovieKeywords(movie_id):
    response = GetMovieDBData("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                              (movie_id, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 30)
    keywords = []
    if "keywords" in response:
        for keyword in response["keywords"]["keywords"]:
            newkeyword = {'id': fetch(keyword, 'id'),
                          'name': keyword['name']}
            keywords.append(newkeyword)
        return keywords
    else:
        log("No keywords in JSON answer")
        return []


def GetSimilarMovies(movie_id):
    response = GetMovieDBData("movie/%s?append_to_response=account_states,alternative_titles,credits,images,keywords,releases,videos,translations,similar,reviews,lists,rating&include_image_language=en,null,%s&language=%s&" %
                              (movie_id, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 10)
    if "similar" in response:
        return HandleTMDBMovieResult(response["similar"]["results"])
    else:
        log("No JSON Data available")


def GetMovieDBTVShows(tvshowtype):
    response = GetMovieDBData("tv/%s?language=%s&" % (tvshowtype, addon.getSetting("LanguageID")), 0.3)
    if "results" in response:
        return HandleTMDBTVShowResult(response["results"], False, None)
    else:
        log("No JSON Data available for GetMovieDBTVShows(%s)" % tvshowtype)
        log(response)


def GetMovieDBMovies(movietype):
    response = GetMovieDBData("movie/%s?language=%s&" % (movietype, addon.getSetting("LanguageID")), 0.3)
    if "results" in response:
        return HandleTMDBMovieResult(response["results"], False, None)
    else:
        log("No JSON Data available for GetMovieDBMovies(%s)" % movietype)
        log(response)


def GetSetMovies(set_id):
    response = GetMovieDBData("collection/%s?language=%s&append_to_response=images&include_image_language=en,null,%s&" % (set_id, addon.getSetting("LanguageID"), addon.getSetting("LanguageID")), 14)
    if response:
        # prettyprint(response)
        if ("backdrop_path" in response) and (response["backdrop_path"]):
            backdrop_path = base_url + fanart_size + response['backdrop_path']
        else:
            backdrop_path = ""
        if ("poster_path" in response) and (response["poster_path"]):
            poster_path = base_url + "original" + response['poster_path']
            small_poster_path = base_url + "w342" + response["poster_path"]
        else:
            poster_path = ""
            small_poster_path = ""
        info = {"label": response["name"],
                "Poster": poster_path,
                "Thumb": small_poster_path,
                "Fanart": backdrop_path,
                "overview": response["overview"],
                "overview": response["overview"],
                "ID": response["id"]}
        return HandleTMDBMovieResult(response.get("parts", [])), info
    else:
        log("No JSON Data available")
        return [], {}


def GetDirectorMovies(person_id):
    response = GetMovieDBData("person/%s/credits?language=%s&" % (person_id, addon.getSetting("LanguageID")), 14)
    # return HandleTMDBMovieResult(response["crew"]) + HandleTMDBMovieResult(response["cast"])
    if "crew" in response:
        return HandleTMDBMovieResult(response["crew"])
    else:
        log("No JSON Data available")


def search_media(media_name=None, year='', media_type="movie"):
    log('TMDB API search criteria: Title[''%s''] | Year[''%s'']' % (media_name, year))
    media_name = urllib.quote_plus(media_name.encode('utf8', 'ignore'))
    tmdb_id = ''
    if media_name:
        response = GetMovieDBData("search/%s?query=%s+%s&language=%s&include_adult=%s&" % (media_type, media_name, year, addon.getSetting("LanguageID"), include_adult), 1)
        try:
            if response == "Empty":
                tmdb_id = ''
            else:
                for item in response['results']:
                    if item['id']:
                        tmdb_id = item['id']
                        break
        except Exception as e:
            log(e)
        if tmdb_id == '':
            log('TMDB API search found no ID')
        else:
            log('TMDB API search found ID: %s' % tmdb_id)
    return tmdb_id


class Get_ListItems_Thread(threading.Thread):
    def __init__(self, function=None, param=None):
        threading.Thread.__init__(self)
        self.function = function
        self.param = param
        self.setName(self.function.__name__)
        log("init " + self.function.__name__)

    def run(self):
        self.listitems = self.function(self.param)
        return True


class Get_Youtube_Vids_Thread(threading.Thread):

    def __init__(self, search_string="", hd="", order="relevance", limit=15):
        threading.Thread.__init__(self)
        self.search_string = search_string
        self.hd = hd
        self.order = order
        self.limit = limit

    def run(self):
        self.listitems = GetYoutubeSearchVideosV3(self.search_string, self.hd, self.order, self.limit)

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# Modifications copyright (C) 2022 - Scott Smart <scott967@kodi.tv>
# This program is Free Software see LICENSE file for details

"""functions and classes to retrieve info from TMDB api v3
see:  https://developers.themoviedb.org/3/getting-started

Public variables:
    Login(LoginProvider):  a TMDB session instance that logs into TMDB on
        creation

Public functions:
    set_rating:  sets local videodb userrating or TMDB user rating
                    (called from button in dialogvideoinfo)
    change_fav_status:  sets TMDB user favorite (called from button in dialogvideoinfo)
    create_list:  creates a new user list on TMDB
    remove_list_dialog:  opens a Kodi select dialog to allow user to select
        a TMDB list for removal
    change_list_status:  Adds or removes a video item from user's TMDB list
    get_account_lists:  gets the user's TMDB lists
    get_certification_list:  gets the TMDB certifications ("MPAA")
    handle_movies/tvshows/episodes:  creates a kutils131 ItemList instance
        of kutils131 VideoItems instances with Kodi listitem properties for the
        video media type to display as Kodi container content items
    handle_lists:  adds user TMDB lists to kutils131 ItemList instance for display
        in Kodi cantainer content
    handle_seasons:  adds seasons to kutils131 ItemList instance
    handle_videos:  adds video clips as kutils131 VideoItems to kutils131 ItemList instance
    search_companies:  gets the TMDB company ID for company (studio) name string
    multi_search:  performs TMDB multisearch "Multi search currently supports
        searching for movies, tv shows and people in a single request."
    get_list_movies:  query TMDB movie list for TMDB id
    get_person_info:  query TMDB actors/crew details for person name(s)
    get_keywords:  query TMDB keywords by keyword string for TMDB id
    get_set_id:  query TMDB sets by string for TMDB id
    get_data:  query TMDB with various search terms
    get_company_data:  query TMDB for company data using TMDB id
    get_credit_info:  query TMDB for credit data using TMDB id
    get_account_props:  provide various TMDB account related info as a dict
    get_movie_tmdb_id:  queries TMDB for TMDB video id if IMDB id is in
        local videodb
    get_show_tmdb_id:  queries TMDB for TMDB tvshow id if TVDB id is in
        local videodb
    get_movie_videos:  queries TMDB for movie trailers
    extended_movie_info:  sets Kodi listitem properties as a kutils
        VideoItem instance and additionally returns a dict of kutil itemlists
        instances
    get_tvshow:  queries TMDB for tvshow details as dict
    extended_tvshow_info: sets Kodi listitem properties as a kutils
        VideoItem instance and additionally returns a dict of kutil itemlists
        instances
    extended_season_info:  sets Kodi listitem properties as a kutils
        VideoItem instance and additionally returns a dict of kutil itemlists
        instances
    get_episode:  queries TMDB for episode details as dict
    extended_episode_info: sets Kodi listitem properties as a kutils
        VideoItem instance and additionally returns a dict of kutil itemlists
        instances
    extended_actor_info:  sets Kodi listitem properties as a kutils
        VideoItem instance and additionally returns a dict of kutil itemlists
        instances
    get_movie_lists:  gets kutils131 ItemList instance for movie lists
    get_rated_media_items:  queries TMDB for user media ratings
    get_fav_items:  queries TMDB for user favorites
    get_movies_from_list:  queries TMDB for movie list
    get_popular_actors:  queries TMDB for popular actors
    get_movie:  queries TMDB for movie given TMDB id
    get_similar_movies:  queries TMDB for similar movies
    get_similar_tvshows:  queries TMDB for similar tvshows
    get_tvshows/movies:  queries TMDB for tvshows/movies matching type
    get_set_movies:  queries TMDB for itemlist of movies in set
    get_person_movies:  queries TMDB for itemlist of movies for actor
    search_media:  generalized TMDB query

"""

from __future__ import annotations

import re
import traceback
import urllib.error
import urllib.parse
import urllib.request

from resources.kutil131 import (ItemList, VideoItem, addon, kodiaddon, kodijson, local_db,
                                selectdialog, utils)

TMDB_TOKEN = ('wpjCrsKBwpjClnvCmsKiwoDCmcKCf8KFwrB8ZsKFwpl-bWXCnsKqesKgwprCh8K'
              'HwpzChMKgesKhwoJ7wqXCmn3CssKIwpzChcKHwpjCscKJwojCisKiwofCm37CoMK'
              'QdHdlwoJ7wonCrsKBacKKYX3Csn9iwoN3wpjCsX93fcKqwoLCn35pwo_CmX9pfsK'
              'hwonCrcKBe8KGwqh9wqV7ZcKQwop6wrF-ZsKJwq7ChnVxbcKEdMKLwqrCj8KkfsK'
              'fwo3CisKCwqR5wqbChMKawphmd8KjwpPCrX1twpDCqnrCoMKZd8KiwpnCmMKkwob'
              'CnMKOesKDwpV8e8KAYsKQwot_wrHCkcKLbcKswoLCm8KfwrDCnMKBZHfCgMKAwpT'
              'CjsKJwpzCr8KWwpbCkcKnwoV5wpliesKYaWzChcKJwovCoMKua3htwojCj396wox'
              '8woLChcKQwqDCscKDwpHCpMKe')
POSTER_SIZES = ["w92", "w154", "w185", "w342", "w500", "w780", "original"]
LOGO_SIZES = ["w45", "w92", "w154", "w185", "w300", "w500", "original"]
BACKDROP_SIZES = ["w300", "w780", "w1280", "original"]
PROFILE_SIZES = ["w45", "w185", "h632", "original"]
STILL_SIZES = ["w92", "w185", "w300", "original"]
HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-agent': 'Kodi/19.0 ( scott967@kodi.tv )',
    'Authorization': ''
}
IMAGE_BASE_URL = "http://image.tmdb.org/t/p/"
POSTER_SIZE = "w500"
URL_BASE = "https://api.themoviedb.org/3/"
ALL_MOVIE_PROPS = ("account_states,alternative_titles,credits,images,keywords,"
                   "release_dates,videos,translations,similar,reviews,lists,rating")
ALL_TV_PROPS = ("account_states,alternative_titles,content_ratings,credits,"
                "external_ids,images,keywords,rating,similar,translations,videos")
ALL_ACTOR_PROPS = "tv_credits,movie_credits,combined_credits,images,tagged_images"
ALL_SEASON_PROPS = "videos,images,external_ids,credits"
ALL_EPISODE_PROPS = "account_states,credits,external_ids,images,rating,videos"

PLUGIN_BASE = "plugin://script.extendedinfo/?info="

RELEASE_TYPES = {1: "Premiere",
                 2: "Theatrical (limited)",
                 3: "Theatrical",
                 4: "Digital",
                 5: "Physical",
                 6: "TV"}

GENDERS = {1: addon.LANG(32095),
           2: addon.LANG(32094)}

STATUS = {"released": addon.LANG(32071),
          "post production": addon.LANG(32072),
          "in production": addon.LANG(32073),
          "ended": addon.LANG(32074),
          "returning series": addon.LANG(32075),
          "planned": addon.LANG(32076)}


def _mulitple_repl(text:str) -> str:
    """ replaces html tags in text with Kodi label formats
    TRANS is a literal dict with regex patterns to match and replace
    Args:
            text (str): string to replace tags

        Returns:
            str: string with Kodi formatting

    """
    TRANS = {"<a.*?</a>": "",
             "<b>": "[B]",
             "</b>": "[/B]",
             "<i>": "[I]",
             "</i>": "[/I]"}
    regex = re.compile(f"({'|'.join(map(re.escape, TRANS.keys()))})")
    return regex.sub(lambda mo: TRANS[mo.group()], text)

class LoginProvider:
    """
    logs into TMDB for user or guest and gets corresponding session or guest session id
    """

    def __init__(self, *args, **kwargs) -> LoginProvider:
        """Creates a new user for accessing tmdb

        Returns:
            LoginProvider: session for user
        """
        self.session_id = None
        self.logged_in = False
        self.account_id = None
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

    def reset_session_id(self):
        """Resets the user session_id in settings when tmdb authentication fails
        This will require obraining a new session_id via get_session_id
        """
        utils.log('tmdb.LoginProvider tmdb authentication failed, resetting session_id')
        if addon.setting("session_id"):
            addon.set_setting("session_id", "")


    def check_login(self) -> bool:
        """determines if user has an active login (session id) on tmdb when opening a tmdb-based
        dialog
        see https://developers.themoviedb.org/3/authentication/how-do-i-generate-a-session-id
        for the tmdb protocol
        Note: in api v4 this will become mandatory.  Optional in v3
        Note2: checks addon settings for a saved session id first.

        Returns:
            bool: true if user has an active session id from tmdb
        """
        if self.username and self.password:
            return bool(self.get_session_id())
        return False

    def get_account_id(self) -> str:
        """returns TMDB account id.  Requires an active session id

        Returns:
            str: the tmdb account id or None
        """
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

    def get_guest_session_id(self) -> str:
        """returns guest session id for TMDB guest session has limited privledge

        Returns:
            str: tmdb guest session id or None
        """
        response = get_data(url="authentication/guest_session/new",
                            cache_days=9999)
        if not response or "guest_session_id" not in response:
            return None
        return str(response["guest_session_id"])

    def test_session_id(self, session_id) -> bool:
        """tests session_id by getting account_id
        If no account_id returned session_id is invalid.

        Args:
            session_id (str): a session_id stored in settings

        Returns:
            bool: True if session_id got and account_id
        """
        response = get_data(url="account",
                            params={"session_id": session_id},
                            cache_days=999999)
        if response and "status_code" in response: 
            return response.get("status_code") == 1
        return False

    def get_session_id(self, cache_days=999) -> str:
        """gets the tmdb session id from addon settings or creates one if not found

        Args:
            cache_days (int, optional): Days to cache a session id in settings.
            Defaults to 999.

        Returns:
            str: the tmdb session id
        """
        if addon.setting("session_id"):
            self.session_id = addon.setting("session_id")
            if self.test_session_id(self.session_id):
                return addon.setting("session_id")
        self.create_session_id()
        return self.session_id

    def create_session_id(self) -> None:
        """gets session id from tmdb as self.session_id and saves it in addon settings
        1.  get request token from tmdb
        2.  create session with login using username/pass
        """
        response = get_data(url="authentication/token/new",
                            cache_days=0)
        params = {"request_token": response["request_token"],
                  "username": self.username,
                  "password": self.password}
        response = get_data(url="authentication/token/validate_with_login",
                            params=params,
                            cache_days=0)
        if response and response.get("success"):
            request_token = response["request_token"]
            response = get_data(url="authentication/session/new",
                                params={"request_token": request_token})
            if response and "success" in response:
                self.session_id = str(response["session_id"])
                addon.set_setting("session_id", self.session_id)


def set_rating(media_type, media_id, rating, dbid=None):
    '''Sets rating for a user media item on tmdb account and Kodi userrating
    media_type: movie, tv or episode
    media_id: tmdb_id / episode ident array
    rating: rating value (1 - 10, 0 for deleting)
    dbid: dbid for syncing userrating of db item
    '''
    if not media_type or not media_id or rating == -1:
        return False
    if dbid:
        kodijson.set_userrating(media_type, dbid, rating)
    params = {}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    else:
        params["guest_session_id"] = Login.get_guest_session_id()
        utils.log('tmdb.set_rating no login use guest session id')
    if media_type == "episode":
        if not media_id[1]:
            media_id[1] = "0"
        url = f"tv/{media_id[0]}/season/{media_id[1]}/episode/{media_id[2]}/rating"
    else:
        url = f"{media_type}/{media_id}/rating"
    results = send_request(url=url,
                           params=params,
                           values={"value": "%.1f" %
                                   float(rating)} if rating > 0 else {},
                           delete=rating == 0)
    if results:
        utils.notify(addon.NAME, results["status_message"])
        return True


def send_request(url, params, values, delete=False):
    """formats a tmdb api query url

    Args:
        url (_type_): _description_
        params (_type_): _description_
        values (_type_): _description_
        delete (bool, optional): request is a post or delete. Defaults to False.

    Returns:
        _type_: _description_
    """
    HEADERS['Authorization'] = 'Bearer ' + kodiaddon.decode_string(TMDB_TOKEN, uuick=addon.setting('tmdb_tok'))
    params = {k: str(v) for k, v in params.items() if v}
    url = f"{URL_BASE}{url}?{urllib.parse.urlencode(params)}"
    if delete:
        return utils.delete(url, values=values, headers=HEADERS)
    else:
        return utils.post(url, values=values, headers=HEADERS)


def change_fav_status(media_id=None, media_type="movie", status="true") -> str:
    """Updates user favorites list on tmdb

    Args:
        media_id (_type_, optional): tmdb id. Defaults to None.
        media_type (str, optional): _tmdb medi type. Defaults to "movie".
        status (str, optional): tmdb favorite status. Defaults to "true".

    Returns:
        str: tmdb result status message
    """
    session_id = Login.get_session_id()
    if not session_id:
        utils.notify("Could not get session id")
        return None
    values = {"media_type": media_type,
              "media_id": media_id,
              "favorite": status}
    results = send_request(url=f"account/{Login.get_account_id()}/favorite",
                           params={"session_id": session_id},
                           values=values)
    if results:
        utils.notify(addon.NAME, results["status_message"])


def create_list(list_name):
    '''
    creates new list on TMDB with name *list_name
    returns newly created list id
    '''
    values = {'name': list_name,
              'description': 'List created by ExtendedInfo Script for Kodi.'}
    results = send_request(url="list",
                           params={"session_id": Login.get_session_id()},
                           values=values)
    if results:
        utils.notify(addon.NAME, results["status_message"])
    return results["list_id"]


def remove_list_dialog(account_lists) -> bool:
    """opens select dialog to remove list from user tmdb lists

    Args:
        account_lists (_type_): user's existing tgmdb lists

    Returns:
        bool: True if user successfully removed a list
    """
    index = selectdialog.open(header=addon.LANG(32138),
                              listitems=account_lists)
    if index >= 0:
        remove_list(account_lists[index]["id"])
        return True


def remove_list(list_id):
    """removes user selected list from user's tmdb lists
    raises toast with results from tmdb

    Args:
        list_id (_type_): id of user tmdb list to remove

    Returns:
        _type_: _description_
    """
    results = send_request(url=f"list/{list_id}",
                           params={"session_id": Login.get_session_id()},
                           values={'media_id': list_id},
                           delete=True)
    if results:
        utils.notify(addon.NAME, results["status_message"])
    return results["list_id"]


def change_list_status(list_id, movie_id, status):
    """adds or removes item from user tmdb list
    raises toast with results from tmdb

    Args:
        list_id (_type_): the user list to update
        movie_id (_type_): th eitem tmdb id to update
        status (_type_): add or remove item
    """
    method = "add_item" if status else "remove_item"
    results = send_request(url=f"list/{list_id}/{method}",
                           params={"session_id": Login.get_session_id()},
                           values={'media_id': movie_id})
    if results:
        utils.notify(addon.NAME, results["status_message"])


def get_account_lists(cache_days=0):
    '''
    returns movie lists for TMDB user
    '''
    session_id = Login.get_session_id()
    account_id = Login.get_account_id()
    if not session_id or not account_id:
        return []
    response = get_data(url=f"account/{account_id}/lists",
                        params={"session_id": session_id},
                        cache_days=cache_days)
    return response["results"]


def get_certification_list(media_type:str) -> dict[str,list]:
    """Gets the known certifications and meanings from tmdb
    The list is cached since it doesn't change (much?)

    Args:
        media_type (str): movie/tv

    Returns:
        dict[str,list]: a dict keys are ISO-1366-1 countries
                        values are list of certs and their descriptions
    """
    response = get_data(url=f"certification/{media_type}/list",
                        cache_days=999999)
    return response.get("certifications")


def merge_with_cert_desc(input_list: ItemList, media_type: str) -> ItemList:
    """adds the tmdb text description of certification

    Args:
        input_list (ItemList): the ItemList of releases (with country and cert)
        media_type (str): movie or tv

    Returns:
        ItemList: the input ItemList with cert meanings appended to the VideoItems
    """
    cert_list = get_certification_list(media_type)
    for item in input_list:
        iso = item.get_property("iso_3166_1")
        if iso not in cert_list:
            continue
        hit = utils.dictfind(lst=cert_list[iso],
                             key="certification",
                             value=item.get_property("certification"))
        if hit:
            item.set_property("meaning", hit["meaning"])
    return input_list

def get_best_release(co_releases:list) -> dict:
    """Gets a single release for a country with multiple releases
    Ensures the release has a cert.  Best release is release with
    "lowest" tmdb release type value

    Args:
        co_releases (list): _description_

    Returns:
        dict: _description_
    """
    best_release = {}
    for release in co_releases:
        if not release.get('certification'):
            continue
        if not best_release:
            best_release = release
        elif int(release.get('type')) < int(best_release.get('type')):
            best_release = release
    return best_release


def handle_multi_search(results):
    listitems = ItemList(content_type="videos")
    for item in results:
        if item["media_type"] == "movie":
            listitems.append(handle_movies([item])[0])
        elif item["media_type"] == "tv":
            listitems.append(handle_tvshows([item])[0])
        elif item["media_type"] == "person":
            listitems.append(handle_people([item])[0])
    return listitems


def handle_movies(results: list[dict], local_first=True, sortkey="year") ->ItemList[VideoItem]:
    """takes a list of movies (dicts) and adds local db data and then sorts as an ItemList
    The tmdb movie keys are converted to extendedinfo keys and genre ids converted
    to localized text strings, then a VideoItem is created for each movie.  The
    Kodi videodb is searched for any matching local movies and these are added to
    the ItemList as VideoItems.

    Args:
        results (List[dict]): a list of movies, each movie is a dict
        local_first (bool, optional): should movies in the db list first. Defaults to True.
        sortkey (str, optional): key to sort the movies. Defaults to "year".

    Returns:
        ItemList:  a kutils131 ItemList of the movies to display in a Kodi container
    """
    response: dict = get_data(url="genre/movie/list",
                              params={"language": addon.setting("LanguageID")},
                              cache_days=30)
    ids: list[int] = [item["id"] for item in response["genres"]]
    labels: list[str] = [item["name"] for item in response["genres"]]
    movies = ItemList(content_type="movies")
    path = 'extendedinfo&&id=%s' if addon.bool_setting(
        "infodialog_onclick") else "playtrailer&&id=%s"
    for movie in results:
        genres = [labels[ids.index(id_)] for id_ in movie.get(
            "genre_ids", []) if id_ in ids]
        item = VideoItem(label=movie.get('title'),
                         path=PLUGIN_BASE + path % movie.get("id"))
        release_date = movie.get('release_date')
        item.set_infos({'title': movie.get('title'),
                        'originaltitle': movie.get('original_title', ""),
                        'mediatype': "movie",
                        'country': movie.get('original_language'),
                        'plot': movie.get('overview'),
                        'Trailer': f"{PLUGIN_BASE}playtrailer&&id={movie.get('id')}",
                        'genre': " / ".join([i for i in genres if i]),
                        'votes': movie.get('vote_count'),
                        'year': utils.get_year(release_date),
                        'rating': round(movie['vote_average'], 1) if movie.get('vote_average') else "",
                        'userrating': movie.get('rating'),
                        'premiered': release_date})
        item.set_properties({'id': movie.get("id"),
                             'popularity': round(movie['popularity'], 1) if movie.get('popularity') else "",
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


def handle_tvshows(results:list[dict], local_first=True, sortkey="year"):
    tvshows = ItemList(content_type="tvshows")
    response = get_data(url="genre/tv/list",
                        params={"language": addon.setting("LanguageID")},
                        cache_days=30)
    ids = [item["id"] for item in response["genres"]]
    labels = [item["name"] for item in response["genres"]]
    for tv in results:
        tmdb_id = tv.get("id")
        genres = [labels[ids.index(id_)]
                  for id_ in tv.get("genre_ids", []) if id_ in ids]
        duration = ""
        if "episode_run_time" in tv:
            if len(tv["episode_run_time"]) > 1:
                duration = "%i - %i" % (min(tv["episode_run_time"]),
                                        max(tv["episode_run_time"]))
            elif len(tv["episode_run_time"]) == 1:
                duration = "%i" % (tv["episode_run_time"][0])
        newtv = VideoItem(label=tv.get('name'),
                          path=f'{PLUGIN_BASE}extendedtvinfo&&id={tmdb_id}')
        newtv.set_infos({'originaltitle': tv.get('original_name', ""),
                         'title': tv.get('name'),
                         'duration': duration,
                         'genre': " / ".join([i for i in genres if i]),
                         'country': tv.get('original_language'),
                         'plot': tv.get("overview"),
                         'year': utils.get_year(tv.get('first_air_date')),
                         'mediatype': "tvshow",
                         'rating': round(tv['vote_average'], 1) if tv.get("vote_average") else "",
                         'userrating': tv.get('rating'),
                         'votes': tv.get('vote_count'),
                         'premiered': tv.get('first_air_date')})
        newtv.set_properties({'id': tmdb_id,
                              'character': tv.get('character'),
                              'popularity': round(tv['popularity'], 1) if tv.get('popularity') else "",
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


def handle_episodes(results:list[dict]) -> ItemList[VideoItem]:
    """Creates an ItemList of VideoItems for episodes

    Args:
        results (_type_): tmdb episode details

    Returns:
        _type_: Kutils131 ItemList of episode VideoItmes
    """
    listitems = ItemList(content_type="episodes")
    for item in results:
        title = item.get("name")
        if not title:
            title = "%s %s" % (addon.LANG(20359), item.get('episode_number'))
        listitem = {'label': title}
        listitem = VideoItem(label=title,
                             artwork=get_image_urls(still=item.get("still_path")))
        listitem.set_infos({'mediatype': "episode",
                            'title': title,
                            'aired': item.get('air_date'),
                            'episode': item.get('episode_number'),
                            'season': item.get('season_number'),
                            'code': item.get("production_code"),
                            'userrating': item.get('rating'),
                            'plot': item.get('overview'),
                            'rating': round(item['vote_average'], 1) if item.get('vote_average') else "",
                            'votes': item.get('vote_count')})
        listitem.set_properties({'id': item.get('id'),
                                 'production_code': item.get('production_code')})
        listitems.append(listitem)
    return listitems


def handle_release_dates(results:list[dict]) -> ItemList[VideoItem]:
    """Creates ItemList of video mpaa cert and dates as VideoItems

    Args:
        results (list[dict]): a list of dicts with TMDB releases

    Returns:
        ItemList: ItemList of releases/certs
    """
    listitems = ItemList()
    for item in results:
        if len(item["release_dates"]) == 1:
            ref:dict = item["release_dates"][0] #only handles the first listed release per country
            if not ref.get("certification"):
                continue
            #listitem = VideoItem(label=item.get('name')) #no key 'name'
            listitem = VideoItem(label='')
            listitem.set_properties({'certification': ref.get('certification'),
                                    'iso_3166_1': item.get('iso_3166_1', ""),
                                    'note': ref.get('note'),
                                    'iso_639_1': ref.get('iso_639_1'),
                                    'release_date': ref.get('release_date'),
                                    'type': RELEASE_TYPES.get(ref.get('type'))})
        else:
            ref:dict = get_best_release(item["release_dates"])
            if not ref:
                continue
            listitem = VideoItem(label='')
            listitem.set_properties({'certification': ref.get('certification'),
                                    'iso_3166_1': item.get('iso_3166_1', ""),
                                    'note': ref.get('note'),
                                    'iso_639_1': ref.get('iso_639_1'),
                                    'release_date': ref.get('release_date'),
                                    'type': RELEASE_TYPES.get(ref.get('type'))})
        listitems.append(listitem)
    return listitems


def handle_content_ratings(results:list[dict]) -> ItemList[VideoItem]:
    listitems = ItemList()
    for item in results:
        listitem = VideoItem(label=item['rating'])
        listitem.set_properties({'iso_3166_1': item['iso_3166_1'].lower(),
                                 'certification': item['rating'].lower()})
        listitems.append(listitem)
    return listitems


def handle_reviews(results:list[dict]) -> ItemList[VideoItem]:
    """Creates an ItemList of VideoItems for tmdb reviews

    Args:
        results (_type_): tmdb review details

    Returns:
        ItemList: Kutils131 ItemList of review VideoItmes
    """
    listitems = ItemList()
    for item in results:
        listitem = VideoItem(label=item.get('author'))
        listitem.set_properties({'author': item.get('author'),
                                 'content': _mulitple_repl(item.get('content')).lstrip(),
                                 'id': item.get('id'),
                                 'url': item.get('url')})
        listitems.append(listitem)
    return listitems


def handle_text(results:list[dict]) -> ItemList[VideoItem]:
    """Converts list of textual info (genres, countries) to ItemList

    Args:
        results (list[dict]): a list of related text info

    Returns:
        ItemList: an ItemList of the text info as VideoItems
    """
    listitems = ItemList()
    for item in results:
        listitem = VideoItem(label=item.get('name'))
        listitem.set_property("id", item.get('id'))
        listitems.append(listitem)
    return listitems


def handle_lists(results:list[dict]) -> ItemList[VideoItem]:
    """Converts various tmdb user movie lists to ItemList

    Args:
        results (list[dict]): list of user movie collections each item is a collection

    Returns:
        ItemList: ItemList of collections as VideoItems type of 'set'
    """
    listitems = ItemList(content_type="sets")
    for item in results:
        listitem = VideoItem(label=item.get('name'),
                             path="plugin://script.extendedinfo?info=listmovies&---id=%s" % item.get(
                                 'id'),
                             artwork=get_image_urls(poster=item.get("poster_path")))
        listitem.set_infos({'plot': item.get('description'),
                            "media_type": "set"})
        listitem.set_properties({'certification': item.get('certification', "") + item.get('rating', ""),
                                 'item_count': item.get('item_count'),
                                 'favorite_count': item.get('favorite_count'),
                                 'iso_3166_1': item.get('iso_3166_1', "").lower(),
                                 'id': item.get('id')})
        listitems.append(listitem)
    return listitems


def handle_seasons(results:list[dict]) -> ItemList[VideoItem]:
    """Creates an ItemList of VideoItems for seasons

    Args:
        results (_type_): tmdb season details

    Returns:
        ItemList: Kutils131 ItemList of season VideoItmes
    """
    listitems = ItemList(content_type="seasons")
    for item in results:
        season = item.get('season_number')
        listitem = VideoItem(label=addon.LANG(20381) if season == 0 else "%s %s" % (addon.LANG(20373), season),
                             properties={'id': item.get('id')},
                             artwork=get_image_urls(poster=item.get("poster_path")))
        listitem.set_infos({'mediatype': "season",
                            'season': season,
                            'premiered': item.get('air_date'),
                            'year': utils.get_year(item.get('air_date'))})
        listitems.append(listitem)
    return listitems


def handle_videos(results:list[dict]) -> ItemList[VideoItem]:
    """Creates an ItemList of video clips/trailers as VideoItems

    Args:
        results (list[dict]): list of clips/trailers

    Returns:
        ItemList: ItemList of VideoItems of the clips/trailers
    """
    listitems = ItemList(content_type="videos")
    for item in results:
        listitem = VideoItem(label=item.get('name'),
                             size=item.get('size'),
                             artwork={'thumb': "http://i.ytimg.com/vi/%s/0.jpg" % item.get('key')})
        listitem.set_infos({'mediatype': "video"})
        listitem.set_properties({'iso_639_1': item.get('iso_639_1'),
                                 'type': item.get('type'),
                                 'key': item.get('key'),
                                 'youtube_id': item.get('key'),
                                 'site': item.get('site'),
                                 'id': item.get('id')})
        listitems.append(listitem)
    return listitems


def handle_people(results:list[dict], select: bool = False) -> ItemList[VideoItem]:
    """converts list of tmdb people into kutils131 videoitems
    The VideoItem properties are tmdb query results

    Args:
        results (list[dict]): a list of dicts, each dict is tmdb data for a person
        select (bool): True if people are to be added to select dialog listing

    Returns:
        ItemList: A kutils131 ItemList of VideoItems for tmdb persons
    """
    people = ItemList(content_type="actors")
    for item in results:
        name_ext: str = ''
        if item.get('adult'):
            name_ext = name_ext + ' Adult'
        if item.get('known_for_department'):
            name_ext = name_ext + f' {item["known_for_department"]}'
        if name_ext != '':
            name_ext = f' -{name_ext}'
        person = VideoItem(label=item['name'] if not select else f'{item["name"]}{name_ext}',
                           path=f"{PLUGIN_BASE}extendedactorinfo&&id={item['id']}",
                           infos={'mediatype': "artist"},
                           artwork=get_image_urls(profile=item.get("profile_path")))
        person.set_properties({'adult': item.get('adult'),
                               'alsoknownas': " / ".join(item.get('also_known_as', [])),
                               'biography': item.get('biography'),
                               'birthday': item.get('birthday'),
                               'age': utils.calculate_age(item.get('birthday'), item.get('deathday')),
                               'character': item.get('character'),
                               'department': item.get('department'),
                               'job': item.get('job'),
                               'id': item['id'],
                               'cast_id': item.get('cast_id'),
                               'credit_id': item.get('credit_id'),
                               'deathday': item.get('deathday'),
                               'placeofbirth': item.get('place_of_birth'),
                               'homepage': item.get('homepage'),
                               'known_for_department': item.get('known_for_department')})
        people.append(person)
    return people


def handle_images(results:list[dict]) -> ItemList[VideoItem]:
    """creates VideoItems of images and returns an ItemList

    Args:
        results (list[dict]): image list

    Returns:
        ItemList: kutils131 itemlist of the images as VideoItems type 'music'?
    """
    images = ItemList(content_type="images")
    for item in results:
        artwork = get_image_urls(poster=item.get("file_path"))  #artwork is a dict key imagetype value path to image
        image = VideoItem(artwork=artwork)
        image.set_properties({'aspectratio': item['aspect_ratio'],
                              'type': "poster" if item['aspect_ratio'] < 0.7 else "fanart",
                              'rating': item.get("vote_average"),
                              'votes': item.get("vote_count"),
                              'iso_639_1': item.get("iso_639_1")})
        if item.get("media") and item["media"].get("title"):  #tmdb has 2 media returns: movie and tv
            image.set_label(item["media"].get("title"))
            image.set_property("movie_id", item["media"].get("id"))
            poster_path = item["media"].get("poster_path")
            if poster_path:
                image.update_artwork(
                    {'mediaposter': IMAGE_BASE_URL + POSTER_SIZE + poster_path})
        image.set_info("mediatype", "music")
        images.append(image)
    return images


def handle_companies(results:list[dict]) -> ItemList[VideoItem]:
    """Converts list of studios from tmdb to ItemList of VideoItems

    Args:
        results (list[dict]): tmdb "production comapnies" list

    Returns:
        ItemList: ItemList of studio VideoItems
    """
    companies = ItemList(content_type="studios")
    for item in results:
        company = VideoItem(label=item['name'],
                            infos={'plot': item.get('description')})
        company.set_properties({'parent_company': item.get('parent_company'),
                                'headquarters': item.get('headquarters'),
                                'homepage': item.get('homepage'),
                                'id': item['id']})
        art = "resource://resource.images.studios.white/{}.png".format(
            item['name']) if item['name'] else ""
        company.set_artwork({"thumb": art,
                             "icon": art})
        companies.append(company)
    return companies


def search_companies(company_name):
    regex = re.compile(r'\(.+?\)')
    response = get_data(url="search/company",
                        params={"query": regex.sub('', company_name)},
                        cache_days=10)
    if response and "results" in response:
        return handle_companies(response["results"])
    else:
        return None


def multi_search(search_str, page=1, cache_days=1):
    params = {"query": search_str,
              "include_adult": addon.setting("include_adults").lower(),
              "page": page}
    response = get_data(url="search/multi",
                        params=params,
                        cache_days=cache_days)
    if response and "results" in response:
        itemlist = handle_multi_search(response["results"])
        itemlist.set_totals(response["total_results"])
        return itemlist


def get_list_movies(list_id, force):
    url = "list/%s" % (list_id)
    response = get_data(url=url,
                        params={"language": addon.setting("LanguageID")},
                        cache_days=0 if force else 2)
    if not response:
        return None
    items = handle_movies(results=response["items"],
                          local_first=True,
                          sortkey=None)
    itemlist = ItemList(items=items)
    itemlist.set_totals(len(response["items"]))
    return itemlist


def get_person_info(person_label:str, skip_dialog=False) -> dict:
    """takes an actor name and returns actor info for it

    Args:
        person_label (str): the actor name, or names with ' / ' as separator
        skip_dialog (bool, optional): Option to show user select dialog for
                                      mulitple tmdb names. Defaults to False.
                                      If true first actor in response is returned

    Returns:
        dict: a dict of info for the named actor -- keys
            'adult' : bool
            'gender' : int enum
            'id' : int
            'known_for' : list of dicts of media info
            'known_for_department' : str enum
            'name' : str
            'popularity' : float
            'profile_path' : str of image path/filename
        False:  if no response

    """
    if not person_label:
        return False
    params = {"query": person_label.split(" / ")[0],
              "include_adult": addon.setting("include_adults").lower()}
    response = get_data(url="search/person",
                        params=params,
                        cache_days=30)
    if not response or "results" not in response:
        return False
    people: list[dict] = [i for i in response["results"] if i["name"] == person_label]
    if len(people) > 1 and not skip_dialog:
        index = selectdialog.open(header=f'{addon.LANG(32151)} TMDB People',
                                  listitems=handle_people(people, select=True))
        return people[index] if index > -1 else False
    elif people:
        return people[0]
    elif response["results"]:
        return response["results"][0]
    return False


def get_keywords(search_label):
    params = {"query": search_label,
              "include_adult": addon.setting("include_adults").lower()}
    response = get_data(url="search/keyword",
                        params=params,
                        cache_days=30)
    if not response or not response.get("results"):
        return False
    return response["results"]


def get_set_id(set_name):
    params = {"query": set_name.replace("[", "").replace("]", "").replace("Kollektion", "Collection"),
              "language": addon.setting("LanguageID")}
    response = get_data(url="search/collection",
                        params=params,
                        cache_days=14)
    if not response or not response.get("results"):
        return ""
    return response["results"][0]["id"]


def get_data(url:str = "", params:dict = None, cache_days:float = 14) -> dict|None:
    """Queries tmdb api v3 or local cache

    Args:
        url (str, optional): tmdb query terms for the search apiv3. Defaults to "".
        params (dict, None): Dict of optional parameters for
                                           query. Defaults to None.
        cache_days (float, optional): Days to check for cached values.
                                      Defaults to 14.

    Returns:
        response(dict): A dict of JSON.loads response from TMDB or None if no
        TMDB response
    """
    params = params if params else {}
    HEADERS['Authorization'] = 'Bearer ' + kodiaddon.decode_string(TMDB_TOKEN, uuick=addon.setting('tmdb_tok'))
    params = {k: str(v) for k, v in params.items() if v}
    url = "%s%s?%s" % (URL_BASE, url, urllib.parse.urlencode(params))
    response = utils.get_JSON_response(url, cache_days, folder='TheMovieDB', headers=HEADERS)
    if not response:
        utils.log("tmdb.get_data No response from TMDB")
        return None
    if "status_code" in response and response.get("status_code") != 1:
        utils.log(f'tmdb.get_data FAIL TMDB status code: {response.get("status_code")} - {response.get("status_message")} {traceback.format_stack(limit=-3)}')
        if response.get('status_code') == 3:
            Login.reset_session_id()
        return None
    return response


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
    return get_data(url=f"credit/{credit_id}",
                    params={"language": addon.setting("LanguageID")},
                    cache_days=30)


def get_account_props(states) -> dict:
    return {"FavButton_Label": addon.LANG(32155) if states.get("favorite") else addon.LANG(32154),
            "favorite": "True" if states.get("favorite") else "",
            "rated": int(states["rated"]["value"]) if states["rated"] else "",
            "watchlist": states["watchlist"] if "watchlist" in states else ""}


def get_image_urls(poster=None, still=None, fanart=None, profile: str =None) -> dict:
    '''
    get a dict with all available images for given image types
    '''
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


def get_movie_tmdb_id(imdb_id:str=None, name:str=None, dbid:int=None):
    """Gets tmdb id for movie


    Args:
        imdb_id (str, optional): the movie imbd id. Defaults to None.
        name (str, optional): the movie title. Defaults to None.
        dbid (int, optional): the kodi db movie id should be > 0. Defaults to None.

    Returns:
        str: tmdb id for local movie get local imdb_id and use for query
        or fall back to title
    """
    if dbid and (int(dbid) > 0):
        imdb_id = local_db.get_imdb_id("movie", dbid)
    if imdb_id:
        params = {"external_source": "imdb_id",
                  "language": addon.setting("LanguageID")}
        response = get_data(url="find/tt%s" % (imdb_id.replace("tt", "")),
                            params=params)
        if response and response["movie_results"]:
            return response["movie_results"][0]["id"]
    return search_media(media_name = name) if name else None


def get_show_tmdb_id(tvdb_id=None, source="tvdb_id"):
    params = {"external_source": source,
              "language": addon.setting("LanguageID")}
    response = get_data(url="find/%s" % (tvdb_id),
                        params=params)
    if not response or not response["tv_results"]:
        utils.notify("TVShow Info not available.")
        return None
    return response["tv_results"][0]["id"]


def get_show_id(tmdb_id=None, return_id="imdb_id"):
    params = {"append_to_response": "external_ids",
              "language": addon.setting("LanguageID")}
    response = get_data(url="tv/%s" % (tmdb_id),
                        params=params)
    if not response:
        utils.notify("TVShow Info not available.")
        return None
    return response["external_ids"][return_id]


def get_movie_videos(movie_id):
    '''
    get trailers / teasers for movie with *movie_id
    '''
    response = get_movie(movie_id)
    if response and "videos" in response and response['videos']['results']:
        return response['videos']['results']
    utils.notify("Could not get movie videos")
    return None


def extended_movie_info(movie_id=None, dbid=None, cache_days=14) -> tuple[VideoItem, dict[str, ItemList], dict] | None:
    """get listitem with extended info for movie with *movie_id
    merge in info from *dbid if available

    Args:
        movie_id (str, optional): TMDB movie id. Defaults to None.
        dbid (int, optional): Local library dbid. Defaults to None.
        cache_days (int, optional): Days to use cached info. Defaults to 14.

    Returns:
        tuple:  kutils131 VideoItem of movie info
                dict of key str value kutils131 ItemList
                dict of account states
    """
    if not movie_id:
        return None
    info: dict | None = get_movie(movie_id=movie_id, cache_days=cache_days)
    if not info or info.get('success') is False:
        utils.notify("Could not get tmdb movie information")
        return (None, None, None)
    mpaa = ""
    studio = [i["name"] for i in info.get("production_companies")]
    authors = [i["name"] for i in info['credits']
               ['crew'] if i["department"] == "Writing"]
    directors = [i["name"] for i in info['credits']
                 ['crew'] if i["department"] == "Directing"]
    us_cert = utils.dictfind(
        info['release_dates']['results'], "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert['release_dates'][0]["certification"]
    elif info['release_dates']['results']:
        mpaa = info['release_dates']['results'][0]['release_dates'][0]['certification']
    movie_set:dict = info.get("belongs_to_collection")
    movie = VideoItem(label=info.get('title'),
                      path=PLUGIN_BASE + 'youtubevideo&&id=%s' % info.get("id", ""))
    movie.set_infos({'title': info.get('title'),
                     'tagline': info.get('tagline'),
                     'duration': info.get('runtime'),
                     'mpaa': mpaa,
                     'director': " / ".join(directors),
                     'writer': " / ".join(authors),
                     'plot': info.get('overview'),
                     'originaltitle': info.get('original_title'),
                     'country': info.get('original_language'),
                     'imdbnumber': info.get('imdb_id'),
                     'genre': " / ".join([i["name"] for i in info["genres"]]),
                     'year': utils.get_year(info.get("release_date")),
                     'rating': round(info['vote_average'], 1) if info.get('vote_average') else "",
                     'premiered': info.get('release_date'),
                     'votes': info.get('vote_count'),
                     'studio': " / ".join(studio),
                     'status': translate_status(info.get('status'))})
    movie.set_properties({'adult': str(info.get('adult')),
                          'popularity': round(info['popularity'], 1) if info.get('popularity') else "",
                          'set': movie_set.get("name") if movie_set else "",
                          'set_id': movie_set.get("id") if movie_set else "",
                          'id': info.get('id'),
                          'imdb_id': info.get('imdb_id'),
                          'budget': utils.millify(info.get("budget")),
                          'revenue': utils.millify(info.get("revenue")),
                          'homepage': info.get('homepage')})
    movie.set_artwork(get_image_urls(poster=info.get("poster_path"),
                                     fanart=info.get("backdrop_path")))
    videos = handle_videos(info["videos"]["results"]
                           ) if "videos" in info else []
    account_states: dict = info.get("account_states")
    if dbid:
        local_item: dict = local_db.get_movie(dbid)
        movie.update_from_listitem(local_item)
    else:
        movie = local_db.merge_with_local("movie", [movie])[0]
    # hack to get tmdb rating instead of local one
    movie.set_info("rating", round(
        info['vote_average'], 1) if info.get('vote_average') else "")
    releases = merge_with_cert_desc(handle_release_dates(
        info["release_dates"]["results"]), "movie")
    listitems: dict[str, ItemList] = {"actors": handle_people(info["credits"]["cast"]),
                 "similar": handle_movies(info["similar"]["results"]),
                 "lists": sort_lists(handle_lists(info["lists"]["results"])),
                 "studios": handle_companies(info["production_companies"]),
                 "releases": releases,
                 "crew": handle_people(info["credits"]["crew"]).reduce(),
                 "genres": handle_text(info["genres"]),
                 "keywords": handle_text(info["keywords"]["keywords"]),
                 "reviews": handle_reviews(info["reviews"]["results"]),
                 "videos": videos,
                 "images": handle_images(info["images"]["posters"]),
                 "backdrops": handle_images(info["images"]["backdrops"])}
    return (movie, listitems, account_states)


def get_tvshow(tvshow_id, cache_days=30, light=False):
    if not tvshow_id:
        return None
    params = {"append_to_response": None if light else ALL_TV_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    return get_data(url="tv/%s" % (tvshow_id),
                    params=params,
                    cache_days=cache_days)


def extended_tvshow_info(tvshow_id=None, cache_days=7, dbid=None):
    '''
    get listitem with extended info for tvshow with *tvshow_id
    merge in info from *dbid if available
    '''
    info = get_tvshow(tvshow_id, cache_days)
    if not info:
        return False
    account_states = info.get("account_states")
    videos = handle_videos(info["videos"]["results"]
                           ) if "videos" in info else []
    tmdb_id = info.get("id", "")
    if len(info.get("episode_run_time", -1)) > 1:
        duration = "%i - %i" % (min(info["episode_run_time"]),
                                max(info["episode_run_time"]))
    elif len(info.get("episode_run_time", -1)) == 1:
        duration = "%i" % (info["episode_run_time"][0])
    else:
        duration = ""
    mpaas = info['content_ratings']['results']
    us_cert = utils.dictfind(mpaas, "iso_3166_1", "US")
    if us_cert:
        mpaa = us_cert["rating"]
    elif mpaas:
        mpaa = mpaas[0]['rating']
    else:
        mpaa = ""
    tvshow = VideoItem(label=info.get('name'),
                       path=PLUGIN_BASE + 'extendedtvinfo&&id=%s' % tmdb_id)
    tvshow.set_infos({'title': info.get('name'),
                      'originaltitle': info.get('original_name', ""),
                      'duration': duration,
                      'mpaa': mpaa,
                      'genre': " / ".join([i["name"] for i in info["genres"]]),
                      'plot': info.get("overview"),
                      'year': utils.get_year(info.get('first_air_date')),
                      'mediatype': "tvshow",
                      'rating': round(info['vote_average'], 1) if info.get('vote_average') else "",
                      'country': info.get('original_language'),
                      'userrating': info.get('rating'),
                      'votes': info.get('vote_count'),
                      'premiered': info.get('first_air_date'),
                      'Status': translate_status(info.get('status'))})
    tvshow.set_properties({'credit_id': info.get('credit_id'),
                           'id': tmdb_id,
                           'popularity': round(info['popularity'], 1) if info.get('popularity') else "",
                           'showtype': info.get('type'),
                           'homepage': info.get('homepage'),
                           'last_air_date': info.get('last_air_date'),
                           'totalepisodes': info.get('number_of_episodes'),
                           'totalseasons': info.get('number_of_seasons'),
                           'in_production': info.get('in_production')})
    tvshow.set_artwork(get_image_urls(poster=info.get("poster_path"),
                                      fanart=info.get("backdrop_path")))
    if dbid:
        local_item = local_db.get_tvshow(dbid)
        tvshow.update_from_listitem(local_item)
    else:
        tvshow = local_db.merge_with_local("tvshow", [tvshow])[0]
    # hack to get tmdb rating instead of local one
    tvshow.set_info("rating", round(
        info['vote_average'], 1) if info.get('vote_average') else "")
    certifications = merge_with_cert_desc(
        handle_content_ratings(info["content_ratings"]["results"]), "tv")
    listitems = {"actors": handle_people(info["credits"]["cast"]),
                 "similar": handle_tvshows(info["similar"]["results"]),
                 "studios": handle_companies(info["production_companies"]),
                 "networks": handle_companies(info["networks"]),
                 "certifications": certifications,
                 "crew": handle_people(info["credits"]["crew"]),
                 "genres": handle_text(info["genres"]),
                 "keywords": handle_text(info["keywords"]["results"]),
                 "videos": videos,
                 "seasons": handle_seasons(info["seasons"]),
                 "images": handle_images(info["images"]["posters"]),
                 "backdrops": handle_images(info["images"]["backdrops"])}
    return (tvshow, listitems, account_states)


def extended_season_info(tvshow_id, season_number):
    '''
    get listitem with extended info for season (*tvshow_id, *season_number)
    '''
    if not tvshow_id or season_number is None:
        return None
    tvshow = get_tvshow(tvshow_id)
    params = {"append_to_response": ALL_SEASON_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    response = get_data(url="tv/%s/season/%s" % (tvshow_id, season_number),
                        params=params,
                        cache_days=7)
    if not response:
        utils.notify("Could not find season info")
        return None
    if response.get("name"):
        title = response["name"]
    elif season_number == "0":
        title = addon.LANG(20381)
    else:
        title = "%s %s" % (addon.LANG(20373), season_number)
    season = VideoItem(label=title)
    season.set_infos({'plot': response["overview"],
                      'tvshowtitle': tvshow.get('name'),
                      'title': title,
                      'premiered': response["air_date"]})
    season.set_artwork(get_image_urls(poster=response.get("poster_path")))
    season.set_properties({'id': response["id"]})
    videos = handle_videos(
        response["videos"]["results"]) if "videos" in response else []
    listitems = {"actors": handle_people(response["credits"]["cast"]),
                 "crew": handle_people(response["credits"]["crew"]),
                 "videos": videos,
                 "episodes": handle_episodes(response["episodes"]),
                 "images": handle_images(response["images"]["posters"]),
                 "backdrops": handle_images(response["images"].get("backdrops", []))}
    return (season, listitems)


def get_episode(tvshow_id, season, episode, cache_days=7):
    if not tvshow_id or not episode:
        return None
    if not season:
        season = 0
    params = {"append_to_response": ALL_EPISODE_PROPS,
              "language": addon.setting("LanguageID"),
              "include_image_language": "en,null,%s" % addon.setting("LanguageID")}
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    return get_data(url="tv/%s/season/%s/episode/%s" % (tvshow_id, season, episode),
                    params=params,
                    cache_days=cache_days)


def extended_episode_info(tvshow_id, season, episode, cache_days=7):
    '''
    get ListItem and lists with extended info for episode (*tvshow_id, *season, *episode)
    '''
    response = get_episode(tvshow_id, season, episode, cache_days)
    if not response:
        utils.notify("Could not find episode info")
        return None
    answer = {"actors": handle_people(response["credits"]["cast"] + response["credits"]["guest_stars"]),
              "crew": handle_people(response["credits"]["crew"]),
              "videos": handle_videos(response["videos"]["results"]) if "videos" in response else [],
              "images": handle_images(response["images"]["stills"])}
    return (handle_episodes([response])[0], answer, response.get("account_states"))


def extended_actor_info(actor_id: int) -> tuple[VideoItem, dict[str, ItemList]]:
    """gets ListItem and lists with extended info for actor with actor_id
    data is a dict from JSON returned by tmdb for an actor
    lists is a dict of "append_to_response" queries extracted from data
    info is a Kodi video listitem instance with properties set from data

    Args:
        actor_id (int): the tmdb actor id

    Returns:
        info[VideoItem]: a populated Kodi listitem
        lists[dict]: a dict of kutils131 Itemlists (one per category) Itemlist is sequence
                     of kutils131 VideoItems
        None: if no results from tmdb
    """
    if not actor_id:
        return None
    data: dict = get_data(url="person/%s" % (actor_id),
                        params={"append_to_response": ALL_ACTOR_PROPS},
                        cache_days=1)
    if not data:
        utils.notify("Could not find actor info")
        return None
    # extract info from data dict as list of ItemLists
    lists: dict[str, ItemList] = {"movie_roles": handle_movies(data["movie_credits"]["cast"]).reduce("character"),
             "tvshow_roles": handle_tvshows(data["tv_credits"]["cast"]).reduce("character"),
             "movie_crew_roles": handle_movies(data["movie_credits"]["crew"]).reduce(),
             "tvshow_crew_roles": handle_tvshows(data["tv_credits"]["crew"]).reduce(),
             "tagged_images": handle_images(data["tagged_images"]["results"]) if "tagged_images" in data else [],
             "images": handle_images(data["images"]["profiles"])}
    info = VideoItem(label=data['name'],
                     path=f"{PLUGIN_BASE}extendedactorinfo&&id={data['id']}",
                     infos={'mediatype': "artist"}) # kutils VideoItem subclass of ListItem a kodi-like class
    info.set_properties({'adult': data.get('adult'),
                         'alsoknownas': " / ".join(data.get('also_known_as', [])),
                         'biography': data.get('biography'),
                         'birthday': data.get('birthday'),
                         'age': utils.calculate_age(data.get('birthday'), data.get('deathday')),
                         'character': data.get('character'),    #cast
                         'department': data.get('department'),  #crew
                         'job': data.get('job'),    #crew
                         'id': data['id'],
                         'gender': GENDERS.get(data['gender']),
                         'cast_id': data.get('cast_id'),
                         'credit_id': data.get('credit_id'),    #cast and crew
                         'deathday': data.get('deathday'),
                         'placeofbirth': data.get('place_of_birth'),
                         'homepage': data.get('homepage'),
                         'totalmovies': len(lists["movie_roles"]),
                         "DBMovies": len([d for d in lists["movie_roles"] if "dbid" in d])})
    info.set_artwork(get_image_urls(profile=data.get("profile_path")))
    return (info, lists)


def translate_status(status):
    '''
    get movies from person with *person_id
    '''
    return STATUS.get(status.lower(), status)


def get_movie_lists(movie_id) -> ItemList:
    data = get_movie(movie_id)
    return handle_lists(data["lists"]["results"])


def get_rated_media_items(media_type, sort_by=None, page=1, cache_days=0):
    '''
    takes "tv/episodes", "tv" or "movies"
    '''
    if Login.check_login():
        session_id = Login.get_session_id()
        account_id = Login.get_account_id()
        if not session_id:
            utils.notify("Could not get session id")
            return []
        params = {"sort_by": sort_by,
                  "page": page,
                  "session_id": session_id,
                  "language": addon.setting("LanguageID")}
        data = get_data(url="account/%s/rated/%s" % (account_id, media_type),
                        params=params,
                        cache_days=cache_days)
    else:
        session_id = Login.get_guest_session_id()
        if not session_id:
            utils.notify("Could not get session id")
            return []
        params = {"language": addon.setting("LanguageID"),
                  "page": page}
        data = get_data(url="guest_session/%s/rated/%s" % (session_id, media_type),
                        params=params,
                        cache_days=0)
    if media_type == "tv/episodes":
        itemlist = handle_episodes(data["results"])
    elif media_type == "tv":
        itemlist = handle_tvshows(data["results"], False, None)
    else:
        itemlist = handle_movies(data["results"], False, None)
    itemlist.set_totals(data["total_results"])
    itemlist.set_total_pages(data["total_pages"])
    return itemlist


def get_fav_items(media_type, sort_by=None, page=1):
    '''
    takes "tv/episodes", "tv" or "movies"
    '''
    session_id = Login.get_session_id()
    account_id = Login.get_account_id()
    if not session_id:
        utils.notify("Could not get session id")
        return []
    params = {"sort_by": sort_by,
              "language": addon.setting("LanguageID"),
              "page": page,
              "session_id": session_id}
    data = get_data(url="account/%s/favorite/%s" % (account_id, media_type),
                    params=params,
                    cache_days=0)
    if "results" not in data:
        return []
    if media_type == "tv":
        itemlist = handle_tvshows(data["results"], False, None)
    elif media_type == "tv/episodes":
        itemlist = handle_episodes(data["results"])
    else:
        itemlist = handle_movies(data["results"], False, None)
    itemlist.set_totals(data["total_results"])
    itemlist.set_total_pages(data["total_pages"])
    return itemlist


def get_movies_from_list(list_id:str, cache_days=5):
    '''
    get movie dict list from tmdb list.
    '''
    data = get_data(url=f"list/{list_id}",
                    params={"language": addon.setting("LanguageID")},
                    cache_days=cache_days)
    return handle_movies(data["items"], False, None) if data else []


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


def get_movie(movie_id, light=False, cache_days=30) -> dict | None:
    """gets details from tmdb for a movie with tmdb movie-id

    Args:
        movie_id (str): tmdb movie id
        light (bool, optional): return limited info. Defaults to False.
        cache_days (int, None):days to use cache vice new query.
                                    Defaults to 30.

    Returns:
        Union[dict, None]: A dict of movie infos.  If no response from TMDB
                            returns None
    """
    params = {"include_image_language": f"en,null,{addon.setting('LanguageID')}",
              "language": addon.setting("LanguageID"),
              "append_to_response": None if light else ALL_MOVIE_PROPS
              }
    if Login.check_login():
        params["session_id"] = Login.get_session_id()
    return get_data(url=f"movie/{movie_id}",
                    params=params,
                    cache_days=cache_days)

def get_similar_movies(movie_id):
    '''
    get dict list containing movies similar to *movie_id
    '''
    response = get_movie(movie_id)
    if not response or not response.get("similar"):
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


def get_tvshows(tvshow_type):
    '''
    return list with tv shows
    available types: airing, on_the_air, top_rated, popular
    '''
    response = get_data(url="tv/%s" % (tvshow_type),
                        params={"language": addon.setting("LanguageID")},
                        cache_days=0.3)
    if not response.get("results"):
        return []
    return handle_tvshows(response["results"], False, None)


def get_movies(movie_type: str) -> list | dict:
    """gets list with movies of movie_type from tmdb

    Args:
        movie_type (str): now_playing, upcoming, top_rated, popular

    Returns:
        list: [description]
    """
    response = get_data(url=f'movie/{movie_type}',
                        params={"language": addon.setting("LanguageID")},
                        cache_days=0.3)
    if not response.get("results"):
        return []
    return handle_movies(response["results"], False, None)


def get_set_movies(set_id:str) -> tuple[ItemList,dict]:
    """Creates an ItemList of movie VideoItems for movies in set

    Args:
        set_id (str): the tmdb collection id

    Returns:
        tuple[ItemList,dict]: an ItemList of movies as VideoItems
                              a dict of set info
    """
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
    '''
    get movies from person with *person_id
    '''
    response = get_data(url="person/%s/credits" % (person_id),
                        params={"language": addon.setting("LanguageID")},
                        cache_days=14)
    # return handle_movies(response["crew"]) + handle_movies(response["cast"])
    if not response or "crew" not in response:
        return []
    return handle_movies(response["crew"])


def sort_lists(lists: ItemList) -> ItemList:
    """sorts an itemlist by finding tmdb movie in account list

    Args:
        lists (ItemList): an itemlist of movies

    Returns:
        ItemList: the itemlist ordered by account list first 
    """
    if not Login.check_login():
        return lists
    ids = [i["id"] for i in get_account_lists(10)]
    own_lists = [i for i in lists if i.get_property("id") in ids]
    for item in own_lists:
        item.set_property("account", "True")
    misc_lists = [i for i in lists if i.get_property("id") not in ids]
    return own_lists + misc_lists


def search_media(media_name=None, year='', media_type="movie", cache_days=1):
    '''
    return list of items with type *media_type for search with *media_name
    '''
    if not media_name:
        return None
    params = {"query": "{} {}".format(media_name, year) if year else media_name,
              "language": addon.setting("language"),
              "include_adult": addon.setting("include_adults").lower()}
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

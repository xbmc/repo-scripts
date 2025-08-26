
from urllib.parse import unquote
from difflib import SequenceMatcher
import json
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon

from resources.lib.utilities import log, normalize_string

__addon__ = xbmcaddon.Addon()


def get_file_path():
    return xbmc.Player().getPlayingFile()


def get_media_data():

    # confusiong results with imdb_id, removed
  #  item = {"year": xbmc.getInfoLabel("VideoPlayer.Year"),
  #          "season_number": str(xbmc.getInfoLabel("VideoPlayer.Season")),
  #          "episode_number": str(xbmc.getInfoLabel("VideoPlayer.Episode")),
  #          "tv_show_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
  #          "original_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
  #          "imdb_id": xbmc.getInfoLabel("VideoPlayer.IMDBNumber")}

    item = {"query": None,
            "year": xbmc.getInfoLabel("VideoPlayer.Year"),
            "season_number": str(xbmc.getInfoLabel("VideoPlayer.Season")),
            "episode_number": str(xbmc.getInfoLabel("VideoPlayer.Episode")),
            "tv_show_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.TVshowtitle")),
            "original_title": normalize_string(xbmc.getInfoLabel("VideoPlayer.OriginalTitle")),
            "parent_tmdb_id": None,
            "parent_imdb_id": None,
            "imdb_id": None,
            "tmdb_id": None}




    if item["tv_show_title"]:
        item["tvshowid"] = xbmc.getInfoLabel("VideoPlayer.TvShowDBID")
        item["query"] = item["tv_show_title"]
        item["year"] = None  # Kodi gives episode year, OS searches by series year. Without year safer.
        # Reset movie-specific IDs for TV shows
        # TODO if no season and episode numbers use guessit
        
        # Extract TMDB and IMDB IDs for TV shows to improve search results
        if len(item["tvshowid"]) != 0:
            try:
                TVShowDetails = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "id":"1", "method": "VideoLibrary.GetTVShowDetails", "params":{"tvshowid":'+item["tvshowid"]+', "properties": ["episodeguide", "imdbnumber"]} }')
                TVShowDetails_dict = json.loads(TVShowDetails)
                if "result" in TVShowDetails_dict and "tvshowdetails" in TVShowDetails_dict["result"]:
                    tvshow_details = TVShowDetails_dict["result"]["tvshowdetails"]
                    
                    # Extract parent IMDB ID from imdbnumber field
                    if "imdbnumber" in tvshow_details and tvshow_details["imdbnumber"]:
                        imdb_raw = str(tvshow_details["imdbnumber"])
                        # Extract numeric part from IMDB ID (remove 'tt' prefix if present)
                        if imdb_raw.startswith('tt'):
                            imdb_number = imdb_raw[2:]
                        else:
                            imdb_number = imdb_raw
                        # Validate it's numeric and reasonable length (IMDB IDs are typically 6-8 digits)
                        if imdb_number.isdigit() and 6 <= len(imdb_number) <= 8:
                            item["parent_imdb_id"] = int(imdb_number)
                            log(__name__, f"Found parent IMDB ID for TV show: {item['parent_imdb_id']}")
                    
                    # Extract parent TMDB ID from episodeguide
                    if "episodeguide" in tvshow_details and tvshow_details["episodeguide"]:
                        episodeguideXML = tvshow_details["episodeguide"]
                        episodeguide = ET.fromstring(episodeguideXML)
                        if episodeguide.text:
                            episodeguideJSON = json.loads(episodeguide.text)
                            if "tmdb" in episodeguideJSON and episodeguideJSON["tmdb"]:
                                tmdb_id = int(episodeguideJSON["tmdb"])
                                if tmdb_id > 0:
                                    item["parent_tmdb_id"] = tmdb_id
                                    log(__name__, f"Found parent TMDB ID for TV show: {item['parent_tmdb_id']}")
            except (json.JSONDecodeError, ET.ParseError, ValueError, KeyError) as e:
                log(__name__, f"Failed to extract TV show IDs: {e}")
                item["parent_tmdb_id"] = None
                item["parent_imdb_id"] = None

    elif item["original_title"]:
        item["query"] = item["original_title"]
        
        # For movies, try to extract IMDB and TMDB IDs
        try:
            # Get IMDB ID from VideoPlayer
            imdb_raw = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
            if imdb_raw:
                # Extract numeric part from IMDB ID (remove 'tt' prefix if present)
                if imdb_raw.startswith('tt'):
                    imdb_number = imdb_raw[2:]
                else:
                    imdb_number = imdb_raw
                # Validate it's numeric and reasonable length (IMDB IDs are typically 6-8 digits)
                if imdb_number.isdigit() and 6 <= len(imdb_number) <= 8:
                    item["imdb_id"] = int(imdb_number)
                    log(__name__, f"Found IMDB ID for movie: {item['imdb_id']}")
            
            # Try to get TMDB ID (might be available in some library setups)
            # This is less common but worth trying
            tmdb_raw = xbmc.getInfoLabel("VideoPlayer.DBID")
            if tmdb_raw and tmdb_raw.isdigit():
                tmdb_id = int(tmdb_raw)
                if tmdb_id > 0:
                    item["tmdb_id"] = tmdb_id
                    log(__name__, f"Found TMDB ID for movie: {item['tmdb_id']}")
        except (ValueError, KeyError) as e:
            log(__name__, f"Failed to extract movie IDs: {e}")


    # Clean up and apply fallback logic for IDs
    # Remove zero or invalid IDs
    if item.get("parent_tmdb_id") == 0:
        item["parent_tmdb_id"] = None
    if item.get("parent_imdb_id") == 0:
        item["parent_imdb_id"] = None
    if item.get("tmdb_id") == 0:
        item["tmdb_id"] = None
    if item.get("imdb_id") == 0:
        item["imdb_id"] = None
        
    # Apply fallback strategy: prefer one ID type to avoid conflicts
    # For TV shows: prefer parent_tmdb_id over parent_imdb_id
    if item.get("parent_tmdb_id") and item.get("parent_imdb_id"):
        log(__name__, f"Both parent TMDB and IMDB IDs found, preferring TMDB ID: {item['parent_tmdb_id']}")
        item["parent_imdb_id"] = None
        
    # For movies: prefer tmdb_id over imdb_id
    if item.get("tmdb_id") and item.get("imdb_id"):
        log(__name__, f"Both TMDB and IMDB IDs found for movie, preferring TMDB ID: {item['tmdb_id']}")
        item["imdb_id"] = None
        
    if not item["query"]:
        log(__name__, "query still blank, fallback to title")
        item["query"] = normalize_string(xbmc.getInfoLabel("VideoPlayer.Title"))  # no original title, get just Title

    # TODO get episodes like that and test them properly out
    if item["episode_number"].lower().find("s") > -1:  # Check if season is "Special"
        item["season_number"] = "0"  #
        item["episode_number"] = item["episode_number"][-1:]

    # Remove tvshowid since it's only used internally and not needed by API
    if "tvshowid" in item:
        del item["tvshowid"]

    return item


def get_language_data(params):
    search_languages = unquote(params.get("languages")).split(",")
    search_languages_str = ""
    preferred_language = params.get("preferredlanguage")

    # fallback_language = __addon__.getSetting("fallback_language")



    if preferred_language and preferred_language not in search_languages and preferred_language != "Unknown"  and preferred_language != "Undetermined":
        search_languages.append(preferred_language)
        search_languages_str=search_languages_str+","+preferred_language

    """ should implement properly as fallback, not additional language, leave it for now
    """

    #if fallback_language and fallback_language not in search_languages:
    #    search_languages_str=search_languages_str+","+fallback_language

        #search_languages_str=fallback_language

    for language in search_languages:
        lang = convert_language(language)
        if lang:
            log(__name__, f"Language  found: '{lang}' search_languages_str:'{search_languages_str}")
            if search_languages_str=="":
                search_languages_str=lang
            else:
                search_languages_str=search_languages_str+","+lang
        #item["languages"].append(lang)
            #if search_languages_str=="":
            #    search_languages_str=lang
           # if lang=="Undetermined":
            #    search_languages_str=search_languages_str
            #else:

        else:
            log(__name__, f"Language code not found: '{language}'")










    item = {
        "hearing_impaired": __addon__.getSetting("hearing_impaired"),
        "foreign_parts_only": __addon__.getSetting("foreign_parts_only"),
        "machine_translated": __addon__.getSetting("machine_translated"),
        "ai_translated": __addon__.getSetting("ai_translated"),
        "languages": search_languages_str}

     # for language in search_languages:
     #  lang = convert_language(language)

     #  if lang:
     #      #item["languages"].append(lang)
     #      item["languages"]=item["languages"]+","+lang
     #  else:
     #      log(__name__, f"Language code not found: '{language}'")

    return item


def convert_language(language, reverse=False):
   # language_list = {
   #     "English": "en",
   #     "Portuguese (Brazil)": "pt-br",
   #     "Portuguese": "pt-pt",
   #     "Chinese (simplified)": "zh-cn",
   #     "Chinese (traditional)": "zh-tw"}
    language_list = {
        "English": "en",
        "Portuguese (Brazil)": "pt-br",
        "Portuguese": "pt-pt",
        "Chinese": "zh-cn",
        "Chinese (simplified)": "zh-cn",
        "Chinese (traditional)": "zh-tw"}

    reverse_language_list = {v: k for k, v in list(language_list.items())}

    if reverse:
        iterated_list = reverse_language_list
        xbmc_param = xbmc.ENGLISH_NAME
    else:
        iterated_list = language_list
        xbmc_param = xbmc.ISO_639_1

    if language in iterated_list:
        return iterated_list[language]
    else:
        return xbmc.convertLanguage(language, xbmc_param)

def get_flag(language_code):
    language_list = {
        "pt-pt": "pt",
        "pt-br": "pb",
        "zh-cn": "zh",
        "zh-tw": "-"
    }
    return language_list.get(language_code.lower(), language_code)


def clean_feature_release_name(title, release, movie_name=""):
    if not title:
        if not movie_name:
            if not release:
                raise ValueError("None of title, release, movie_name contains a string")
            return release
        else:
            if not movie_name[0:4].isnumeric():
                name = movie_name
            else:
                name = movie_name[7:]
    else:
        name = title

    match_ratio = SequenceMatcher(None, name, release).ratio()
    log(__name__, f"name: {name}, release: {release}, match_ratio: {match_ratio}")
    if name in release:
        return release
    elif match_ratio > 0.3:
        return release
    else:
        return f"{name} {release}"

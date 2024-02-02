from __future__ import absolute_import
from urllib import unquote
from difflib import SequenceMatcher

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

    item = {u"query": None,
            u"year": xbmc.getInfoLabel(u"VideoPlayer.Year"),
            u"season_number": unicode(xbmc.getInfoLabel(u"VideoPlayer.Season")),
            u"episode_number": unicode(xbmc.getInfoLabel(u"VideoPlayer.Episode")),
            u"tv_show_title": normalize_string(xbmc.getInfoLabel(u"VideoPlayer.TVshowtitle")),
            u"original_title": normalize_string(xbmc.getInfoLabel(u"VideoPlayer.OriginalTitle"))}




    if item[u"tv_show_title"]:
        item[u"query"] = item[u"tv_show_title"]
        item[u"year"] = None  # Kodi gives episode year, OS searches by series year. Without year safer.
        item[u"imdb_id"] = None  # Kodi gives strange id. Without id safer.
        # TODO if no season and episode numbers use guessit

    elif item[u"original_title"]:
        item[u"query"] = item[u"original_title"]


    if not item[u"query"]:
        log(__name__, u"query still blank, fallback to title")
        item[u"query"] = normalize_string(xbmc.getInfoLabel(u"VideoPlayer.Title"))  # no original title, get just Title

    # TODO get episodes like that and test them properly out
    if item[u"episode_number"].lower().find(u"s") > -1:  # Check if season is "Special"
        item[u"season_number"] = u"0"  #
        item[u"episode_number"] = item[u"episode_number"][-1:]

    return item


def get_language_data(params):
    search_languages = unquote(params.get(u"languages")).split(u",")
    search_languages_str = u""
    preferred_language = params.get(u"preferredlanguage")

    # fallback_language = __addon__.getSetting("fallback_language")



    if preferred_language and preferred_language not in search_languages and preferred_language != u"Unknown"  and preferred_language != u"Undetermined":
        search_languages.append(preferred_language)
        search_languages_str=search_languages_str+u","+preferred_language

    u""" should implement properly as fallback, not additional language, leave it for now
    """

    #if fallback_language and fallback_language not in search_languages:
    #    search_languages_str=search_languages_str+","+fallback_language

        #search_languages_str=fallback_language

    for language in search_languages:
        lang = convert_language(language)
        if lang:
            log(__name__, "Language  found: '%s' search_languages_str:'%s" % (lang, search_languages_str) )
            if search_languages_str==u"":
                search_languages_str=lang
            else:
                search_languages_str=search_languages_str+u","+lang
        #item["languages"].append(lang)
            #if search_languages_str=="":
            #    search_languages_str=lang
           # if lang=="Undetermined":
            #    search_languages_str=search_languages_str
            #else:

        else:
            log(__name__, "Language code not found: '%s'" % (language) )










    item = {
        u"hearing_impaired": __addon__.getSetting(u"hearing_impaired"),
        u"foreign_parts_only": __addon__.getSetting(u"foreign_parts_only"),
        u"machine_translated": __addon__.getSetting(u"machine_translated"),
        u"languages": search_languages_str}

     # for language in search_languages:
     #  lang = convert_language(language)

     #  if lang:
     #      #item["languages"].append(lang)
     #      item["languages"]=item["languages"]+","+lang
     #  else:
     #      log(__name__, "Language code not found: '%s'" % (language) )

    return item


def convert_language(language, reverse=False):
    language_list = {
        u"English": u"en",
        u"Portuguese (Brazil)": u"pt-br",
        u"Portuguese": u"pt-pt",
        u"Chinese (simplified)": u"zh-cn",
        u"Chinese (traditional)": u"zh-tw"}
    reverse_language_list = dict((v, k) for k, v in list(language_list.items()))

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
        u"pt-pt": u"pt",
        u"pt-br": u"pb"
    }
    return language_list.get(language_code.lower(), language_code)


def clean_feature_release_name(title, release, movie_name=u""):
    if not title:
        if not movie_name:
            if not release:
                raise ValueError(u"None of title, release, movie_name contains a string")
            return release
        else:
            if not movie_name[0:4].isnumeric():
                name = movie_name
            else:
                name = movie_name[7:]
    else:
        name = title

    match_ratio = SequenceMatcher(None, name, release).ratio()
    log(__name__, "name: %s, release: %s, match_ratio: %s" % (name, release, match_ratio) )
    if name in release:
        return release
    elif match_ratio > 0.3:
        return release
    else:
        return "%s %s" % (name, release) 

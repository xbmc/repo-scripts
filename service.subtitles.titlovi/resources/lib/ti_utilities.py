# -*- coding: utf-8 -*-

import sys
import urllib
import base64
import xbmc
import xbmcvfs
import unicodedata
from xml.dom import minidom

__addon__ = sys.modules["__main__"].__addon__
__scriptname__ = sys.modules["__main__"].__scriptname__
__version__ = sys.modules["__main__"].__version__

LANGUAGES = (
    # Full Language name[0]
    # podnapisi[1]
    # ISO 639-1[2]
    # ISO 639-1 Code[3]
    # Script Setting Language[4]
    # localized name id number[5]
    ("Bosnian"      , "10",  "bs",   "bos",   "3",    30204),
    ("Croatian"     , "38",  "hr",   "hrv",   "7",    30208),
    ("English"      , "2",   "en",   "eng",   "11",   30212),
    ("Macedonian"   , "35",  "mk",   "mac",   "28",   30229),
    ("Serbian"      , "36",  "sr",   "scc",   "36",   30237),
    ("Slovenian"    , "1",   "sl",   "slv",   "38",   30239),
    ("SerbianLatin" , "36",  "sr",   "scc",   "100",  30237))


def languageTranslate(lang, lang_from, lang_to):
    for x in LANGUAGES:
        if lang == x[lang_from]:
            return x[lang_to]


def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'),
             level=xbmc.LOGDEBUG)


def compare_columns(b, a):
    return cmp(b["language_name"], a["language_name"]) or \
        cmp(a["sync"], b["sync"])


class OSDBServer:

    KEY = "UGE4Qk0tYXNSMWEtYTJlaWZfUE9US1NFRC1WRUQtWA=="

    def search_subtitles(self, name, tvshow, season, episode, lang, year):
        # log(__name__, 'Season: %s' % season)
        # log(__name__, 'Episode: %s' % episode)
        if len(tvshow) > 1:
            name = tvshow
        subtitles_list = []
        api_key = base64.b64decode(self.KEY)[::-1]

        # if len(tvshow) > 0:
        #     search_string = ("%s S%.2dE%.2d" % (name,
        #                                         int(season),
        #                                         int(episode),))
        #     search_string = search_string.replace(" ", "+")
        # else:

        search_string = name.replace(" ", "+")

        search_url_base = "http://api.titlovi.com/xml_get_api.ashx?x-dev_api_id=%s&keyword=%s&language=%s&uiculture=en" % (api_key, search_string, "%s")
        subtitles = None
        supported_languages = ["bs", "hr", "en", "mk", "sr", "sl", "rs", "ba", "si", None]

        for i in range(len(lang)):
            if str(lang[i]) == "sr":
                lang1 = "rs"
            elif str(lang[i]) == "bs":
                lang1 = "ba"
            elif str(lang[i]) == "sl":
                lang1 = "si"
            else:
                lang1 = str(lang[i])

            if lang1 in supported_languages:
                url = search_url_base % lang1
                log(__name__, "%s - Language %i" % (url, i))
                temp_subs = self.fetch(url)
                if temp_subs:
                    if subtitles:
                        subtitles = subtitles + temp_subs
                    else:
                        subtitles = temp_subs
            else:
                log(__name__, "Unsupported lang: %s" % lang1)
        try:
            if subtitles:
                url_base = "http://en.titlovi.com/downloads/default.ashx?type=1&mediaid=%s"
                log(__name__, "Found subs: %s" % len(subtitles))
                for subtitle in subtitles:
                    subtitle_id = 0
                    rating = 0
                    filename = ""
                    movie = ""
                    lang_name = ""
                    lang_id = ""
                    flag_image = ""
                    link = ""
                    format = "srt"

                    tv_info = self.get_tvshow_info(subtitle)

                    if subtitle.getElementsByTagName("safeTitle")[0].firstChild:
                        movie = subtitle.getElementsByTagName("safeTitle")[0] \
                            .firstChild.data
                    if subtitle.getElementsByTagName("year")[0].firstChild:
                        movie_year = subtitle.getElementsByTagName("year")[0] \
                            .firstChild.data
                    if subtitle.getElementsByTagName("release")[0].firstChild:
                        filename = subtitle.getElementsByTagName("release")[0] \
                            .firstChild.data
                        if tv_info:
                            # log(__name__, 'Found tv show: %s' % tv_info)
                            filename = "%s (%s) %s %s.srt" % (movie,
                                                           movie_year,
                                                           tv_info,
                                                           filename,)
                        else:
                            filename = "%s (%s) %s.srt" % (movie, movie_year, filename,)
                        if len(filename) < 2:
                            filename = "%s (%s).srt" % (movie, movie_year,)
                    else:
                        log(__name__, 'Filename not exist')
                        if tv_info:
                            filename = "%s (%s) %s.srt" % (movie,
                                                           movie_year,
                                                           tv_info,)
                        else:
                            filename = "%s (%s).srt" % (movie, movie_year,)
                    if subtitle.getElementsByTagName("score")[0].firstChild:
                        rating = int(float(subtitle.getElementsByTagName("score")[0]
                                     .firstChild.data))
                    if subtitle.getElementsByTagName("language")[0].firstChild:
                        lang = subtitle.getElementsByTagName("language")[0] \
                            .firstChild.data
                        if lang == "rs":
                            lang = "sr"
                        if lang == "ba":
                            lang = "bs"
                        if lang == "si":
                            lang = "sl"
                        lang_name = lang
                    subtitle_id = subtitle.getElementsByTagName("url")[0] \
                        .firstChild.data
                    subtitle_id = subtitle_id.split("-")[-1].replace("/", "")
                    flag_image = lang_name
                    link = url_base % subtitle_id
                    if len(tvshow) > 0:
                        checkEpisode = 'S%.2dE%.2d' % (int(season),
                                                      int(episode))
                        checkSeasonPack = 'S%.2d Pack' % int(season)
                        if (checkEpisode in filename) or (checkSeasonPack in filename):
                            subtitles_list.append({'filename': filename,
                                                        'link': link,
                                                        'language_name': languageTranslate((lang_name),2,0),
                                                        'language_id': lang_id,
                                                        'language_flag': flag_image,
                                                        'movie': movie,
                                                        'ID': subtitle_id,
                                                        'rating': str(rating),
                                                        'format': format,
                                                        'sync': False,
                                                        'hearing_imp': False
                                                        })
                    else:
                        subtitles_list.append({'filename': filename,
                                                        'link': link,
                                                        'language_name': languageTranslate((lang_name),2,0),
                                                        'language_id': lang_id,
                                                        'language_flag': flag_image,
                                                        'movie': movie,
                                                        'ID': subtitle_id,
                                                        'rating': str(rating),
                                                        'format': format,
                                                        'sync': False,
                                                        'hearing_imp': False
                                                        })
                    # log(__name__, "link: %s" % link)
                    # log(__name__, "movie: %s" % movie)
                    # log(__name__, "rating: %s" % rating)
                return subtitles_list
        except:
            return subtitles_list

    def get_tvshow_info(self, subtitle):
        if(len(subtitle.getElementsByTagName('TVShow'))!=0):
            season = subtitle.getElementsByTagName("season")[0] \
                .firstChild.data
            tvinfo = 'S%.2d' % int(season)
            if(len(subtitle.getElementsByTagName('episode'))!=0):
                episode = subtitle.getElementsByTagName("episode")[0] \
                    .firstChild.data
                tvinfo = '%sE%.2d' % (tvinfo, int(episode))
            else:
                tvinfo = '%s Pack' % tvinfo
        else:
            tvinfo = None
        return tvinfo

    def fetch(self, url):
        socket = urllib.urlopen(url)
        result = socket.read()
        socket.close()
        xmldoc = minidom.parseString(result)
        return xmldoc.getElementsByTagName("subtitle")

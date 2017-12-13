# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2
import socket
import re
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
    xbmc.log((u"### Titlovi.com ### [%s] - %s" % (module, msg,)).encode('utf-8'),
             level=xbmc.LOGDEBUG)


def compare_columns(b, a):
    return cmp(b["language_name"], a["language_name"]) or \
        cmp(a["sync"], b["sync"])


class OSDBServer:

    def search_subtitles(self, name, tvshow, season, episode, lang, year):
        # log(__name__, 'Season: %s' % season)
        # log(__name__, 'Episode: %s' % episode)

        if tvshow:
            name = tvshow
            log(__name__, 'tvshow: %s' % tvshow)
            log(__name__, 'name: %s' % name)
        subtitles_list = []
        # api_key = base64.b64decode(self.KEY)[::-1]
 
        search_string = name.replace(" ", "+")

        if tvshow:
            if season and episode:
                search_url_base = "https://titlovi.com/titlovi/?prijevod=%s&jezik=%s&t=2&s=%s&e=%s&sort=4" % (search_string, "%s", int(season), episode)
            elif season:
                search_url_base = "https://titlovi.com/titlovi/?prijevod=%s&jezik=%s&t=2&s=%s&e=0&sort=4" % (search_string, "%s", int(season))
        else:
            if year:
                search_url_base = "https://titlovi.com/titlovi/?prijevod=%s&jezik=%s&g=%s&sort=4" % (search_string, "%s", year)
            else:
                search_url_base = "https://titlovi.com/titlovi/?prijevod=%s&jezik=%s&sort=4" % (search_string, "%s")

        subtitles = None
        supported_languages = ["bs", "hr", "en", "mk", "sr", "sl", "rs", "ba", "si", "bosanski", "hrvatski", "cirilica", "english", "makedonski", "srpski", "slovenski", None] # kodi format

        for i in range(len(lang)):
            if str(lang[i]) == "sr":
                lang1 = "srpski"
            elif str(lang[i]) == "bs":
                lang1 = "bosanski"
            elif str(lang[i]) == "sl":
                lang1 = "slovenski"
            elif str(lang[i]) == "mk":
                lang1 = "makedonski"
            elif str(lang[i]) == "hr":
                lang1 = "hrvatski"
            elif str(lang[i]) == "en":
                lang1 = "english"
            else:
                lang1 = str(lang[i])

            if lang1 in supported_languages:
                url = search_url_base % lang1
                log(__name__, "%s - SearchURL: %i" % (url, i))
                temp_subs = self.openUrl(url)
                if temp_subs:
                    if subtitles:
                        subtitles = subtitles + temp_subs
                    else:
                        subtitles = temp_subs
            else:
                log(__name__, "Unsupported lang: %s" % lang1)

        # log(__name__, "Subs: %s" % subtitles)

        try:
            if subtitles:
                url_base = "https://titlovi.com/download/?type=1&mediaid=%s"
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

                    lang = subtitle['lang_name']
                    if lang == "rs":
                        lang = "sr"
                    if lang == "ba":
                        lang = "bs"
                    if lang == "si":
                        lang = "sl"

                    lang_name = lang

                    subtitle_id = subtitle['ID']
                    flag_image = lang_name
                    link = url_base % subtitle['ID']
                    movie = subtitle['movie']

                    # log(__name__, "season: %02d" % int(season))
                    # log(__name__, "season: %s" % episode)

                    if tvshow:
                        if episode:
                            filename = "%s S%02dE%02d %s" % (movie, int(season), int(episode), subtitle['release'])
                        else:
                            filename = "%s S%02d Pack %s" % (movie, int(season), subtitle['release'])
                    else:
                        filename = "%s %s.srt" % (movie, subtitle['release'])

                    log(__name__, "Filename: %s" % filename)

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

    def openUrl(self, url):
        try:
            useragent = {'User-Agent': "Mozilla/5.0"}
            req = urllib2.Request(url, headers=useragent)
            website = urllib2.urlopen(req)
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'We failed to reach a server.'
                print 'Reason: ', e.reason
                return False
            elif hasattr(e, 'code'):
                print 'The server couldn\'t fulfill the request.'
                print 'Error code: ', e.code
                return False
        except socket.timeout as e:
            # catched
            print type(e)
            return False
        else:
            # read html code
            html = website.read()
            website.close()

        naslovRE = re.compile('<li class=".*?"><h3.*?a href="(.*?)">(.*?)<\/a>.*?<i>(.*?)<\/i>.*?<\/h3><h4>(.*?)<span.*?<\/h4>.*?<img.*?src="(.*?)"')
        naslovMatch = naslovRE.findall(html)
        prevodi = []
        for detali in naslovMatch:
            id = detali[0].split("-")[-1]
            id = id[:-1]
            ime = detali[1] + " " + detali[2]
            lang = detali[4].split("/")[-1]
            lang = lang[:-5]
            release = detali[3].decode('utf-8')
            prevodi.append({'movie': ime,
                            'ID': id,
                            'release': release,
                            'lang_name': lang})
        return prevodi
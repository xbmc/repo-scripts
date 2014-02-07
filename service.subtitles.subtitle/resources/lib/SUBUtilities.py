# -*- coding: utf-8 -*-
import cookielib
import os
import re
import urllib
import urllib2
import unicodedata
import zlib
import shutil

try:
    import StorageServer
except ImportError:
    import storageserverdummy as StorageServer

try:
    import xbmc
    import xbmcvfs
    import xbmcaddon
except ImportError:
    from stubs import xbmc
    from stubs import xbmcvfs
    from stubs import xbmcaddon

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version')  # Module version
__scriptname__ = __addon__.getAddonInfo('name')
__language__ = __addon__.getLocalizedString
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")

cache = StorageServer.StorageServer(__scriptname__, int(24 * 364 / 2))  # 6 months

#===============================================================================
# Private utility functions
#===============================================================================
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


def get_cache_key(prefix="", str=""):
    str = re.sub('\W+', '_', str).lower()
    return prefix + str


# Returns the corresponding script language name for the Hebrew unicode language
def heb_to_eng(language):
    languages = {
        "עברית": "he",
        "אנגלית": "en",
        "ערבית": "ar",
        "צרפתית": "fr",
        "גרמנית": "de",
        "רוסית": "ru",
        "טורקית": "tr",
        "ספרדית": "sp"
    }
    return languages[language]


class SubtitleHelper:
    BASE_URL = "http://www.subtitle.co.il"

    def __init__(self):
        self.urlHandler = URLHandler()

    def get_subtitle_list(self, item):
        if item["tvshow"]:
            search_results = self._search_tvshow(item)
            results = self._build_tvshow_subtitle_list(search_results, item)
        else:
            search_results = self._search_movie(item)
            results = self._build_movie_subtitle_list(search_results, item)

        return results

    # return list of tv-series from the site`s search
    def _search_tvshow(self, item):
        search_string = re.split(r'\s\(\w+\)$', item["tvshow"])[0]

        cache_key = get_cache_key("tv-show_", search_string)
        results = cache.get(cache_key)

        if not results:
            query = {"q": search_string.lower(), "cs": "series"}

            search_result = self.urlHandler.request(self.BASE_URL + "/browse.php?" + urllib.urlencode(query))
            if search_result is None:
                return results  # return empty set

            urls = re.findall(
                u'<a href="viewseries\.php\?id=(\d+)[^"]+" itemprop="url">[^<]+</a></div><div style="direction:ltr;" class="smtext">([^<]+)</div>',
                search_result)

            results = self._filter_urls(urls, search_string, item)
            cache.set(cache_key, repr(results))
        else:
            results = eval(results)

        return results

    # return list of movie from the site`s search
    def _search_movie(self, item):
        results = []
        search_string = item["title"]
        query = {"q": search_string.lower(), "cs": "movies", "fy": int(item["year"]) - 1,
                 "uy": int(item["year"]) + 1}

        search_result = self.urlHandler.request(self.BASE_URL + "/browse.php?" + urllib.urlencode(query))
        if search_result is None:
            return results  # return empty set

        urls = re.findall(
            u'<a href="view\.php\?id=(\d+)[^"]+" itemprop="url">[^<]+</a></div><div style="direction:ltr;" class="smtext">([^<]+)</div><span class="smtext">(\d{4})</span>',
            search_result)

        results = self._filter_urls(urls, search_string, item)
        return results

    def _filter_urls(self, urls, search_string, item):
        filtered = []
        search_string = search_string.lower()

        if not item["tvshow"]:
            for (id, eng_name, year) in urls:
                if search_string.startswith(eng_name.lower()) and \
                        (item["year"] == '' or
                                 year == '' or
                                     (int(year) - 1) <= int(item["year"]) <= (int(year) + 1) or
                                     (int(item["year"]) - 1) <= int(year) <= (int(item["year"]) + 1)):
                    filtered.append({"name": eng_name, "id": id, "year": year})
        else:
            for (id, eng_name) in urls:
                if search_string.startswith(eng_name.lower()):
                    filtered.append({"name": eng_name, "id": id})

        log(__scriptname__, "filtered: %s" % filtered)
        return filtered

    def _build_movie_subtitle_list(self, search_results, item):
        ret = []
        total_downloads = 0
        for result in search_results:
            url = self.BASE_URL + "/view.php?" + urllib.urlencode({"id": result["id"], "m": "subtitles"})
            subtitle_page = self._is_logged_in(url)
            x, i = self._retrive_subtitles(subtitle_page, item)
            total_downloads += i
            ret += x

        # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(it["rating"] / float(total_downloads), 1) * 5))

        return sorted(ret, key=lambda x: (x['lang_index'], x['sync'], x['rating']), reverse=True)

    def _build_tvshow_subtitle_list(self, search_results, item):
        ret = []
        total_downloads = 0
        for result in search_results:
            cache_key = get_cache_key("tv-show_seasons_", "%s_%s" % (result["name"], result["id"]))
            subtitle_page = cache.get(cache_key)
            if not subtitle_page:
                url = self.BASE_URL + "/viewseries.php?" + urllib.urlencode({"id": result["id"], "m": "subtitles"})
                subtitle_page = self._is_logged_in(url)
                if subtitle_page is not None:
                    # Retrieve the requested season
                    subtitle_page = re.findall("seasonlink_(\d+)[^>]+>(\d+)</a>", subtitle_page)
                    cache.set(cache_key, repr(subtitle_page))
            else:
                subtitle_page = eval(subtitle_page)

            if subtitle_page:
                for (season_id, season_num) in subtitle_page:
                    if season_num == item["season"]:
                        cache_key = get_cache_key("tv-show_episodes_", "%s_%s" % (result["name"], season_id))
                        found_episodes = cache.get(cache_key)
                        if not found_episodes:
                            # Retrieve the requested episode
                            url = self.BASE_URL + "/getajax.php?" + urllib.urlencode({"seasonid": season_id})
                            subtitle_page = self.urlHandler.request(url)
                            if subtitle_page is not None:
                                found_episodes = re.findall("episodelink_(\d+)[^>]+>(\d+)</a>", subtitle_page)
                                cache.set(cache_key, repr(found_episodes))
                        else:
                            found_episodes = eval(found_episodes)

                        if found_episodes:
                            for (episode_id, episode_num) in found_episodes:
                                if episode_num == item["episode"]:
                                    url = self.BASE_URL + "/getajax.php?" + urllib.urlencode({"episodedetails": episode_id})
                                    subtitle_page = self.urlHandler.request(url)

                                    x, i = self._retrive_subtitles(subtitle_page, item)
                                    total_downloads += i
                                    ret += x

        # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(it["rating"] / float(total_downloads), 1) * 5))

        return sorted(ret, key=lambda x: (x['lang_index'], x['sync'], x['rating']), reverse=True)

    def _retrive_subtitles(self, page, item):
        ret = []
        total_downloads = 0
        if page is not None:
            found_subtitles = re.findall(
                "downloadsubtitle\.php\?id=(?P<fid>\d*).*?subt_lang.*?title=\"(?P<language>.*?)\".*?subtitle_title.*?title=\"(?P<title>.*?)\">.*?>(?P<downloads>[^ ]+) הורדות",
                page)
            for (subtitle_id, language, title, downloads) in found_subtitles:
                if xbmc.convertLanguage(heb_to_eng(language), xbmc.ISO_639_2) in item[
                    "3let_language"]:
                    subtitle_rate = self._calc_rating(title, item["file_original_path"])
                    total_downloads += int(downloads.replace(",", ""))
                    ret.append(
                        {'lang_index': item["3let_language"].index(
                            xbmc.convertLanguage(heb_to_eng(language), xbmc.ISO_639_2)),
                         'filename': title,
                         'link': subtitle_id,
                         'language_name': xbmc.convertLanguage(heb_to_eng(language),
                                                               xbmc.ENGLISH_NAME),
                         'language_flag': xbmc.convertLanguage(heb_to_eng(language),
                                                               xbmc.ISO_639_1),
                         'ID': subtitle_id,
                         'rating': int(downloads.replace(",", "")),
                         'sync': subtitle_rate >= 4,
                         'hearing_imp': 0
                        })
        return ret, total_downloads


    def _calc_rating(self, subsfile, file_original_path):
        file_name = os.path.basename(file_original_path)
        folder_name = os.path.split(os.path.dirname(file_original_path))[-1]

        subsfile = re.sub('\W+', '.', subsfile).lower()
        file_name = re.sub('\W+', '.', file_name).lower()
        folder_name = re.sub('\W+', '.', folder_name).lower()
        log(__scriptname__, "# Comparing Releases:\n [subtitle-rls] %s \n [filename-rls] %s \n [folder-rls] %s" % (
            subsfile, file_name, folder_name))

        subsfile = subsfile.split('.')
        file_name = file_name.split('.')[:-1]
        folder_name = folder_name.split('.')

        if len(file_name) > len(folder_name):
            diff_file = list(set(file_name) - set(subsfile))
            rating = (1 - (len(diff_file) / float(len(file_name)))) * 5
        else:
            diff_folder = list(set(folder_name) - set(subsfile))
            rating = (1 - (len(diff_folder) / float(len(folder_name)))) * 5

        log(__scriptname__,
            "\n rating: %f (by %s)" % (round(rating, 1), "file" if len(file_name) > len(folder_name) else "folder"))

        return round(rating, 1)

    def download(self, id, zip_filename):
        ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        ## pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

        query = {"id": id}
        url = self.BASE_URL + "/downloadsubtitle.php?" + urllib.urlencode(query)
        f = self.urlHandler.request(url)

        with open(zip_filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()
        xbmc.sleep(500)

        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_filename, __temp__,)).encode('utf-8'), True)

    def _is_logged_in(self, url):
        content = self.urlHandler.request(url)
        if content is not None and re.search(r'friends\.php', content):  #check if logged in
            return content
        elif self.login():
            return self.urlHandler.request(url)
        else:
            return None

    def login(self):
        email = __addon__.getSetting("SUBemail")
        password = __addon__.getSetting("SUBpassword")
        query = {'email': email, 'password': password, 'Login': 'התחבר'}
        content = self.urlHandler.request(self.BASE_URL + "/login.php", query)
        if re.search(r'<form action="/login\.php"', content):
            xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, __language__(32005))).encode('utf-8'))
            return None
        else:
            self.urlHandler.save_cookie()
            return True


class URLHandler():
    def __init__(self):
        self.cookie_filename = os.path.join(__profile__, "cookiejar.txt")
        self.cookie_jar = cookielib.LWPCookieJar(self.cookie_filename)
        if os.access(self.cookie_filename, os.F_OK):
            self.cookie_jar.load()

        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie_jar))
        self.opener.addheaders = [('Accept-Encoding', 'gzip'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent',
                                   'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:16.0) Gecko/20100101 Firefox/16.0')]

    def request(self, url, data=None, decode_zlib=True, ajax=False, referer=None, cookie=None):
        if data is not None:
            data = urllib.urlencode(data)
        if ajax:
            self.opener.addheaders += [('X-Requested-With', 'XMLHttpRequest')]
        if referer is not None:
            self.opener.addheaders += [('Referer', referer)]
        if cookie is not None:
            self.opener.addheaders += [('Cookie', cookie)]

        content = None
        log(__scriptname__, "Getting url: %s" % (url))
        try:
            response = self.opener.open(url, data)

            content = None if response.code != 200 else response.read()

            if decode_zlib and response.headers.get('content-encoding', '') == 'gzip':
                try:
                    content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                except zlib.error:
                    pass

            response.close()
        except Exception as e:
            log(__scriptname__, "Failed to get url: %s\n%s" % (url, e))
            # Second parameter is the filename
        return content

    def save_cookie(self):
        self.cookie_jar.save()

        # item = {'episode': '11', 'temp': False, 'title': '', 'season': '11', 'year': '', 'rar': False,
        #         'tvshow': 'Two and a Half Men',
        #         'file_original_path': u'D:\\Videos\\Series\\Two.and.a.Half.Men\\Season 11\\Two.and.a.Half.Men.S11E13.480p.HDTV.X264-DIMENSION.mkv',
        #         '3let_language': ['en', 'he']}
        # item = {'episode': '', 'temp': False, 'title': 'Her', 'season': '', 'year': '2014', 'rar': False, 'tvshow': '',
        #         'file_original_path': u'D:\\Videos\\Movies\\Her\\Her.2013.DVDScr.XviD-SaM.mp4',
        #         '3let_language': ['en', 'he']}
        # # {'episode': '4', 'temp': False, 'title': 'Killer Within', 'season': '3', 'year': '', 'rar': False, 'tvshow': 'The Walking Dead', 'file_original_path': u'D:\\Videos\\Series\\The.Walking.Dead\\Season 3\\The.Walking.Dead.S03E04.720p.HDTV.x264-IMMERSE.mkv', '3let_language': ['eng', 'heb']}
        # item = {'episode': '', 'temp': False, 'title': 'Free Birds', 'season': '', 'year': '2013', 'rar': False, 'tvshow': '',
        #         'file_original_path': u'D:\\Videos\\Movies\\Free.Birds.2013.1080p.BRRip.x264-YIFY\\FB13.1080p.BRRip.x264-YIFY.mp4',
        #         '3let_language': ['en', 'he']}


        # item = {'episode': '11', 'temp': False, 'title': 'Blind Spot', 'season': '2', 'year': '', 'rar': False,
        #         'tvshow': 'Arrow',
        #         'file_original_path': u'D:\\Videos\\Series\\Arrow\\Season  2\\Arrow.S02E11.720p.HDTV.X264-DIMENSION.mkv',
        #         '3let_language': ['en', 'he']}
        # helper = SubtitleHelper()
        # print helper.get_subtitle_list(item)
        # print helper.login()
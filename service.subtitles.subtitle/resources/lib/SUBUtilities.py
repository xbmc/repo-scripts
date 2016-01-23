# -*- coding: utf-8 -*-
import HTMLParser
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
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp', '')), 'utf-8')

cache = StorageServer.StorageServer(__scriptname__, int(24 * 364 / 2))  # 6 months
regexHelper = re.compile('\W+', re.UNICODE)


# ===============================================================================
# Private utility functions
# ===============================================================================
def normalizeString(str):
    return unicodedata.normalize(
            'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('utf-8', 'ignore')


def clean_title(item):
    title = os.path.splitext(os.path.basename(item["title"]))
    tvshow = os.path.splitext(os.path.basename(item["tvshow"]))

    if len(title) > 1:
        if re.match(r'^\.[a-z]{2,4}$', title[1], re.IGNORECASE):
            item["title"] = title[0]
        else:
            item["title"] = ''.join(title)
    else:
        item["title"] = title[0]

    if len(tvshow) > 1:
        if re.match(r'^\.[a-z]{2,4}$', tvshow[1], re.IGNORECASE):
            item["tvshow"] = tvshow[0]
        else:
            item["tvshow"] = ''.join(tvshow)
    else:
        item["tvshow"] = tvshow[0]

    item["title"] = unicode(item["title"], "utf-8")
    item["tvshow"] = unicode(item["tvshow"], "utf-8")
    # Removes country identifier at the end
    item["title"] = re.sub(r'\([^\)]+\)\W*$', '', item["title"])
    item["tvshow"] = re.sub(r'\([^\)]+\)\W*$', '', item["tvshow"])


def parse_rls_title(item):
    title = regexHelper.sub(' ', item["title"])
    tvshow = regexHelper.sub(' ', item["tvshow"])

    groups = re.findall(r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})", title, re.I)

    if len(groups) == 0:
        groups = re.findall(r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})", tvshow, re.I)

    if len(groups) > 0 and len(groups[0]) >= 3:
        title, year, season, episode = groups[0]
        item["year"] = str(int(year)) if len(year) == 4 else year

        item["tvshow"] = regexHelper.sub(' ', title).strip()
        item["season"] = str(int(season))
        item["episode"] = str(int(episode))
        log(__scriptname__, "TV Parsed Item: %s" % (item,))

    else:
        groups = re.findall(r"(.*?)(\d{4})", item["title"], re.I)
        if len(groups) > 0 and len(groups[0]) >= 1:
            title = groups[0][0]
            item["title"] = regexHelper.sub(' ', title).strip()
            item["year"] = groups[0][1] if len(groups[0]) == 2 else item["year"]

            log(__scriptname__, "MOVIE Parsed Item: %s" % (item,))


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


def get_cache_key(prefix="", str=""):
    str = re.sub(r'[\'\(\)\.\-\]\[ ]+', '_', str).lower()
    return prefix + '_' + str


def clear_cache():
    cache.delete("tv-show%")
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, __language__(32007))).encode('utf-8'))


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
    BASE_URL = "http://www.ktuvit.com"

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

        cache_key = get_cache_key("tv-show", search_string)
        results = cache.get(cache_key)

        if not results:
            query = {"q": search_string.encode("utf-8").lower(), "cs": "series"}
            search_result = self.urlHandler.request(self.BASE_URL + "/browse.php", query)
            if search_result is None:
                return results  # return empty set

            urls = re.findall(
                    u'<a href="(?P<url>/tt\d+/[^/]+/)[^"]*" itemprop="url">([^<]+)</a></div><div style="direction:ltr;" class="smtext">([^<]+)</div>',
                    search_result)

            results = self._filter_urls(urls, search_string, item)
            if results:
                cache.set(cache_key, repr(results))
        else:
            results = eval(results)

        return results

    # return list of movie from the site`s search
    def _search_movie(self, item):
        results = []
        search_string = item["title"]
        query = {"q": search_string.encode("utf-8").lower(), "cs": "movies"}
        if item["year"]:
            query["fy"] = int(item["year"]) - 1
            query["uy"] = int(item["year"]) + 1

        search_result = self.urlHandler.request(self.BASE_URL + "/browse.php", query)
        if search_result is None:
            return results  # return empty set

        urls = re.findall(
                u'<a href="/tt1(?P<id>\d+)/[^"]+" itemprop="url">(?P<heb_name>[^<]+)</a></div><div style="direction:ltr;" class="smtext">(?P<eng_name>[^<]+)</div><span class="smtext">(?P<year>\d{4})</span>',
                search_result)

        results = self._filter_urls(urls, search_string, item)
        return results

    def _filter_urls(self, urls, search_string, item):
        filtered = []
        search_string = regexHelper.sub(' ', search_string.lower())

        h = HTMLParser.HTMLParser()

        log(__scriptname__, "urls: %s" % urls)

        if not item["tvshow"]:
            for (id, heb_name, eng_name, year) in urls:
                eng_name = unicode(eng_name, 'utf-8')
                heb_name = unicode(heb_name, 'utf-8')

                eng_name = h.unescape(eng_name).replace(' ...', '').lower()
                heb_name = h.unescape(heb_name).replace(' ...', '')

                eng_name = regexHelper.sub(' ', eng_name)
                heb_name = regexHelper.sub(' ', heb_name)

                if (search_string.startswith(eng_name) or eng_name.startswith(search_string) or
                        search_string.startswith(heb_name) or heb_name.startswith(search_string)) and \
                        (item["year"] == '' or
                                 year == '' or
                                     (int(year) - 1) <= int(item["year"]) <= (int(year) + 1) or
                                     (int(item["year"]) - 1) <= int(year) <= (int(item["year"]) + 1)):
                    filtered.append({"name": eng_name, "id": id, "year": year})
        else:
            for (url, heb_name, eng_name) in urls:
                eng_name = unicode(eng_name, 'utf-8')
                heb_name = unicode(heb_name, 'utf-8')

                eng_name = h.unescape(eng_name).replace(' ...', '').lower()
                heb_name = h.unescape(heb_name).replace(' ...', '')

                eng_name = regexHelper.sub(' ', eng_name)
                heb_name = regexHelper.sub(' ', heb_name)

                if (search_string.startswith(eng_name) or eng_name.startswith(search_string) or
                        search_string.startswith(heb_name) or heb_name.startswith(search_string)):
                    filtered.append({"name": eng_name, "url": urllib.quote(url)})

        log(__scriptname__, "filtered: %s" % filtered)
        return filtered

    def _build_movie_subtitle_list(self, search_results, item):
        ret = []
        total_downloads = 0
        for result in search_results:
            subtitle_page = self._is_logged_in(self.BASE_URL + "/getajax.php", {"moviedetailssubtitles": result["id"]})
            x, i = self._retrive_subtitles(subtitle_page, item)
            total_downloads += i
            ret += x

        # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(it["rating"] / float(total_downloads), 1) * 5))

        return sorted(ret, key=lambda x: (x['is_preferred'], x['lang_index'], x['sync'], x['rating']), reverse=True)

    def _build_tvshow_subtitle_list(self, search_results, item):
        ret = []
        total_downloads = 0

        for result in search_results:
            cache_key_season = get_cache_key("tv-show", "%s_%s" % (result["name"], "seasons"))
            subtitle_page = cache.get(cache_key_season)
            if not subtitle_page:
                used_cached_seasons = False
                subtitle_page = self._is_logged_in(self.BASE_URL + result["url"])
                if subtitle_page is not None:
                    # Retrieve the requested season
                    subtitle_page = re.findall("seasonlink_(\d+)[^>]+>(\d+)</a>", subtitle_page)
                    if subtitle_page:
                        cache.set(cache_key_season, repr(subtitle_page))
            else:
                used_cached_seasons = True
                subtitle_page = eval(subtitle_page)

            if subtitle_page:
                season_found = False
                for (season_id, season_num) in subtitle_page:
                    if season_num == item["season"]:
                        season_found = True

                        cache_key_episode = get_cache_key("tv-show",
                                                          "%s_s%s_%s" % (result["name"], season_num, "episodes"))
                        found_episodes = cache.get(cache_key_episode)
                        if not found_episodes:
                            used_cached_episodes = False
                            # Retrieve the requested episode
                            url = self.BASE_URL + "/getajax.php"
                            subtitle_page = self.urlHandler.request(url, {"seasonid": season_id})
                            if subtitle_page is not None:
                                found_episodes = re.findall("episodelink_(\d+)[^>]+>(\d+)</a>", subtitle_page)

                                if found_episodes:
                                    cache.set(cache_key_episode, repr(found_episodes))
                        else:
                            used_cached_episodes = True
                            found_episodes = eval(found_episodes)

                        if found_episodes:
                            episode_found = False
                            for (episode_id, episode_num) in found_episodes:
                                if episode_num == item["episode"]:
                                    episode_found = True

                                    subtitle_page = self._is_logged_in(self.BASE_URL + "/getajax.php",
                                                                       {"episodedetails": episode_id})

                                    x, i = self._retrive_subtitles(subtitle_page, item)
                                    total_downloads += i
                                    ret += x

                            if not episode_found and used_cached_episodes:
                                cache.delete(cache_key_episode)  # used cached episodes list and not found
                                return self._build_tvshow_subtitle_list(search_results, item)  # try the search again

                if not season_found and used_cached_seasons:
                    cache.delete(cache_key_season)  # used cached season list and not found so delete the cache
                    return self._build_tvshow_subtitle_list(search_results, item)  # try the search again

        # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(it["rating"] / float(total_downloads), 1) * 5))

        return sorted(ret, key=lambda x: (x['is_preferred'], x['lang_index'], x['sync'], x['rating']), reverse=True)

    def _retrive_subtitles(self, page, item):
        ret = []
        total_downloads = 0
        if page is not None:
            found_subtitles = re.findall(
                "downloadsubtitle\.php\?id=(?P<fid>\d*).*?subt_lang.*?title=\"(?P<language>.*?)\".*?subtitle_title.*?title=\"(?P<title>.*?)\">.*?>(?P<downloads>[^ ]+) הורדות",
                page)
            for (subtitle_id, language, title, downloads) in found_subtitles:
                if xbmc.convertLanguage(heb_to_eng(language), xbmc.ISO_639_2) in item["3let_language"]:
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
                                'id': subtitle_id,
                                'rating': int(downloads.replace(",", "")),
                                'sync': subtitle_rate >= 3.8,
                                'hearing_imp': 0,
                                'is_preferred':
                                    xbmc.convertLanguage(heb_to_eng(language), xbmc.ISO_639_2) == item[
                                        'preferredlanguage']
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
        # # Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        # # pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

        f = self.urlHandler.request(self.BASE_URL + "/downloadsubtitle.php", {"id": id})

        with open(zip_filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()
        xbmc.sleep(500)

        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_filename, __temp__,)).encode('utf-8'), True)

    def _is_logged_in(self, url, query_string=None):
        content = self.urlHandler.request(url, query_string)

        if content is not None and content.find('עליך להיות משתמש כדי לצפות בתוכן זה') == -1:  # check if logged in
            return content
        elif self.login():
            return self.urlHandler.request(url, query_string)
        else:
            return None

    def login(self):
        email = __addon__.getSetting("SUBemail")
        password = __addon__.getSetting("SUBpassword")
        post_data = {'email': email, 'password': password, 'Login': 'התחבר'}
        content = self.urlHandler.request(self.BASE_URL + "/login.php", None, post_data)
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
                                   'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36')]

    def request(self, url, query_string=None, data=None, decode_zlib=True, ajax=False, referrer=None, cookie=None):
        if data is not None:
            data = urllib.urlencode(data)
        if query_string is not None:
            query_string = urllib.urlencode(query_string)
            url += "?" + query_string
        if ajax:
            self.opener.addheaders += [('X-Requested-With', 'XMLHttpRequest')]
        if referrer is not None:
            self.opener.addheaders += [('Referrer', referrer)]
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

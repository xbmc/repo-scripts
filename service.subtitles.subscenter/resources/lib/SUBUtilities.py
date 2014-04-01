# -*- coding: utf-8 -*-
import HTMLParser
import os
import re
import urllib
import urllib2
import unicodedata
import json
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


def clear_cache():
    cache.delete("tv-show%")
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, __language__(32004))).encode('utf-8'))


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


def get_cache_key(prefix="", str=""):
    str = re.sub('\W+', '_', str).lower()
    return prefix + str


class SubscenterHelper:
    BASE_URL = "http://www.subscenter.org"

    def __init__(self):
        self.urlHandler = URLHandler()

    def get_subtitle_list(self, item):
        search_results = self._search(item)
        results = self._build_subtitle_list(search_results, item)

        return results

    # return list of movies / tv-series from the site`s search
    def _search(self, item):
        results = []

        search_string = re.split(r'\s\(\w+\)$', item["tvshow"])[0] if item["tvshow"] else item["title"]

        if item["tvshow"]:
            cache_key = get_cache_key("tv-show_", search_string)
            results = cache.get(cache_key)
            if results:
                results = eval(results)

        if not results:
            query = {"q": search_string.lower()}
            search_result = self.urlHandler.request(self.BASE_URL + "/he/subtitle/search/?" + urllib.urlencode(query))
            if search_result is None:
                return results  # return empty set

            urls = re.findall('<a href=".*/he/subtitle/(movie|series)/([^/]+)/">[^/]+ / ([^<]+)</a>', search_result)
            years = re.findall(u'<span class="special">[^:]+: </span>(\d{4}).<br />', search_result)
            for i, url in enumerate(urls):
                year = years[i] if len(years) > i else ''
                urls[i] += (year,)

            results = self._filter_urls(urls, search_string, item)

            if item["tvshow"] and results:
                cache.set(cache_key, repr(results))

        return results


    def _filter_urls(self, urls, search_string, item):
        filtered = []
        search_string = search_string.lower()
        h = HTMLParser.HTMLParser()
        for i, (content_type, slug, eng_name, year) in enumerate(urls):
            eng_name = h.unescape(eng_name)
            if ((content_type == "movie" and not item["tvshow"]) or
                    (content_type == "series" and item["tvshow"])) and \
                    search_string.startswith(eng_name.replace(' ...', '').lower()) and \
                    (item["year"] == '' or
                             year == '' or
                                 (int(year) - 1) <= int(item["year"]) <= (int(year) + 1) or
                                 (int(item["year"]) - 1) <= int(year) <= (int(item["year"]) + 1)):
                filtered.append({"type": content_type, "name": eng_name, "slug": slug, "year": year})
        log(__scriptname__, "filtered: %s" % filtered)
        return filtered

    def _build_subtitle_list(self, search_results, item):
        ret = []
        total_downloads = 0
        for result in search_results:
            url = self.BASE_URL + "/he/cinemast/data/" + result["type"] + "/sb/" + result["slug"]
            url += "/" + item["season"] + "/" + item["episode"] + "/" if result["type"] == "series" else "/"
            subs_list = self.urlHandler.request(url)

            if subs_list is not None:
                subs_list = json.loads(subs_list, encoding="utf-8")
                for language in subs_list.keys():
                    if xbmc.convertLanguage(language, xbmc.ISO_639_2) in item["3let_language"]:
                        for translator_group in subs_list[language]:
                            for quality in subs_list[language][translator_group]:
                                for index in subs_list[language][translator_group][quality]:
                                    current = subs_list[language][translator_group][quality][index]
                                    title = current["subtitle_version"]
                                    subtitle_rate = self._calc_rating(title, item["file_original_path"])
                                    total_downloads += current["downloaded"]
                                    ret.append(
                                        {'lang_index': item["3let_language"].index(
                                            xbmc.convertLanguage(language, xbmc.ISO_639_2)),
                                         'filename': title,
                                         'link': current["key"],
                                         'language_name': xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
                                         'language_flag': language,
                                         'ID': current["id"],
                                         'rating': str(current["downloaded"]),
                                         'sync': subtitle_rate >= 4,
                                         'hearing_imp': current["hearing_impaired"] > 0
                                        })
        # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(float(it["rating"]) / float(total_downloads), 1) * 5))

        return sorted(ret, key=lambda x: (x['lang_index'], x['sync'], x['rating']), reverse=True)

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

    def download(self, id, language, key, filename, zip_filename):
        ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        ## pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

        query = {"v": filename,
                 "key": key}
        url = self.BASE_URL + "/he/subtitle/download/" + language + "/" + str(id) + "/?" + urllib.urlencode(query)
        f = self.urlHandler.request(url)

        with open(zip_filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()
        xbmc.sleep(500)

        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_filename, __temp__,)).encode('utf-8'), True)


class URLHandler():
    def __init__(self):
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('Accept-Encoding', 'gzip'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent',
                                   'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:16.0) Gecko/20100101 Firefox/16.0')]

    def request(self, url, data=None, ajax=False, referer=None, cookie=None):
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

            if response.headers.get('content-encoding', '') == 'gzip':
                try:
                    content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                except zlib.error:
                    pass

            response.close()
        except Exception as e:
            log(__scriptname__, "Failed to get url: %s\n%s" % (url, e))
            # Second parameter is the filename
        return content

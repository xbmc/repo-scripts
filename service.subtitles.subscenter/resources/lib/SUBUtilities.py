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
    from tests.stubs import xbmc
    from tests.stubs import xbmcvfs
    from tests.stubs import xbmcaddon

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version')  # Module version
__scriptname__ = __addon__.getAddonInfo('name')
__language__ = __addon__.getLocalizedString
__profile__ = unicode(xbmc.translatePath(__addon__.getAddonInfo('profile')), 'utf-8')
__temp__ = unicode(xbmc.translatePath(os.path.join(__profile__, 'temp', '')), 'utf-8')

store = StorageServer.StorageServer(__scriptname__, int(24 * 364 / 2))  # 6 months
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
    item["title"] = re.sub(r'\([^\)]+\)\W*$', '', item["title"]).strip()
    item["tvshow"] = re.sub(r'\([^\)]+\)\W*$', '', item["tvshow"]).strip()


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
        log("TV Parsed Item: %s" % (item,))

    else:
        groups = re.findall(r"(.*?)(\d{4})", item["title"], re.I)
        if len(groups) > 0 and len(groups[0]) >= 1:
            title = groups[0][0]
            item["title"] = regexHelper.sub(' ', title).strip()
            item["year"] = groups[0][1] if len(groups[0]) == 2 else item["year"]

            log("MOVIE Parsed Item: %s" % (item,))


def clear_store():
    store.delete("%")
    notify(32004)


def get_store_key(prefix="", str=""):
    str = re.sub(r'[\'\(\)\.\-\]\[ ]+', '_', str).lower()
    return prefix + str


def log(msg):
    xbmc.log((u"### [%s] - %s" % (__scriptname__, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


def notify(msg_id):
    xbmc.executebuiltin((u'Notification(%s,%s)' % (__scriptname__, __language__(msg_id))).encode('utf-8'))


class SubscenterHelper:
    BASE_URL = "http://www.subscenter.org/he/api/"

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
        user_token = self.get_user_token()

        query = {"q": search_string.encode("utf-8"), "user": user_token["user"], "token": user_token["token"]}
        if item["tvshow"]:
            query["type"] = "series"
            query["season"] = item["season"]
            query["episode"] = item["episode"]
        else:
            query["type"] = "movies"
            query["year_start"] = int(item["year"])-1
            query["year_end"] = int(item["year"])

        search_result = self.urlHandler.request(self.BASE_URL + "search/", query)

        if search_result is not None and search_result["result"] == "failed":
            # Update cached token
            user_token = self.get_user_token(True)
            query["token"] = user_token["token"]
            search_result = self.urlHandler.request(self.BASE_URL + "search/", query)

        if search_result is not None and search_result["result"] == "failed":
            notify(32009)
            return results

        log("Results: %s" % search_result)

        if search_result is None or search_result["result"] != "success" or search_result["count"] < 1:
            return results  # return empty set

        results = self._filter_results(search_result["data"], search_string, item)
        log("Filtered: %s" % results)

        return results

    def _filter_results(self, results, search_string, item):
        filtered = []
        search_string = regexHelper.sub('', search_string.lower())

        for result in results:
            eng_name = result["name_en"].strip().lower()
            heb_name = result["name_he"].strip()

            eng_name = regexHelper.sub(' ', eng_name)
            eng_name_tmp = regexHelper.sub('', eng_name)
            heb_name = regexHelper.sub('', heb_name)

            if (search_string.startswith(eng_name_tmp) or eng_name_tmp.startswith(search_string) or
                    search_string.startswith(heb_name) or heb_name.startswith(search_string)) and \
                    (item["year"] == '' or
                             result["year"] == '' or
                                 (int(result["year"]) - 1) <= int(item["year"]) <= (int(result["year"]) + 1) or
                                 (int(item["year"]) - 1) <= int(result["year"]) <= (int(item["year"]) + 1)):
                filtered.append({"name": eng_name, "year": result["year"], "subs": result["subtitles"]})
        return filtered

    def _build_subtitle_list(self, search_results, item):
        ret = []
        for result in search_results:
            total_downloads = 0
            counter = 0
            subs_list = result["subs"]

            if subs_list is not None:
                for language in subs_list.keys():
                    if xbmc.convertLanguage(language, xbmc.ISO_639_2) in item["3let_language"]:
                        for current in subs_list[language]:
                            counter += 1
                            title = current["version"]
                            subtitle_rate = self._calc_rating(title, item["file_original_path"])
                            total_downloads += int(current["downloads"])
                            ret.append(
                                {'lang_index': item["3let_language"].index(
                                    xbmc.convertLanguage(language, xbmc.ISO_639_2)),
                                    'filename': title,
                                    'link': current["key"],
                                    'language_name': xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
                                    'language_flag': language,
                                    'id': current["id"],
                                    'rating': current["downloads"],
                                    'sync': subtitle_rate >= 3.8,
                                    'hearing_imp': False,
                                    'is_preferred':
                                        xbmc.convertLanguage(language, xbmc.ISO_639_2) == item[
                                            'preferredlanguage']
                                })
            # Fix the rating
            if total_downloads:
                for it in ret[-1 * counter:]:
                    it["rating"] = str(min(int(round(float(it["rating"]) / float(total_downloads), 1) * 8), 5))

        return sorted(ret, key=lambda x: (x['is_preferred'], x['lang_index'], x['sync'], x['rating']), reverse=True)

    def _calc_rating(self, subsfile, file_original_path):
        file_name = os.path.basename(file_original_path)
        folder_name = os.path.split(os.path.dirname(file_original_path))[-1]

        subsfile = re.sub(r'\W+', '.', subsfile).lower()
        file_name = re.sub(r'\W+', '.', file_name).lower()
        folder_name = re.sub(r'\W+', '.', folder_name).lower()
        log("# Comparing Releases:\n [subtitle-rls] %s \n [filename-rls] %s \n [folder-rls] %s" % (
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

        log("\n rating: %f (by %s)" % (round(rating, 1), "file" if len(file_name) > len(folder_name) else "folder"))

        return round(rating, 1)

    def download(self, id, language, key, filename, zip_filename):
        ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        ## pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

        query = {"v": filename,
                 "key": key,
                 "sub_id": id}

        user_token = self.get_user_token()

        url = self.BASE_URL + "subtitle/download/" + language + "/?" + urllib.urlencode(query)

        f = self.urlHandler.request(url, user_token)

        with open(zip_filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()
        xbmc.sleep(500)

        xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip_filename, __temp__,)).encode('utf-8'), True)

    def login(self, isFromSettings=False):
        email = __addon__.getSetting("Email")
        password = __addon__.getSetting("Password")
        post_data = {'username': email, 'password': password}
        content = self.urlHandler.request(self.BASE_URL + "login/", post_data)

        if content['result'] == 'success':
            if isFromSettings:
                notify(32010)

            del content["result"]
            return content
        else:
            notify(32009)
            return None

    def get_user_token(self, force_update=False):
        if force_update:
            store.delete('credentials')

        results = store.get('credentials')
        if results:
            results = json.loads(results)
        else:
            results = self.login()
            store.set('credentials', json.dumps(results))

        return results


class URLHandler():
    def __init__(self):
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('Accept-Encoding', 'gzip'),
                                  ('Accept-Language', 'en-us,en;q=0.5'),
                                  ('Pragma', 'no-cache'),
                                  ('Cache-Control', 'no-cache'),
                                  ('User-Agent',
                                   'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36')]

    def request(self, url, data=None, query_string=None, ajax=False, referrer=None, cookie=None):
        if data is not None:
            data = urllib.urlencode(data)
        if query_string is not None:
            url += '?' + urllib.urlencode(query_string)
        if ajax:
            self.opener.addheaders += [('X-Requested-With', 'XMLHttpRequest')]
        if referrer is not None:
            self.opener.addheaders += [('Referrer', referrer)]
        if cookie is not None:
            self.opener.addheaders += [('Cookie', cookie)]

        content = None
        log("Getting url: %s" % (url))
        if data is not None and 'password' not in data:
            log("Post Data: %s" % (data))
        try:
            response = self.opener.open(url, data)
            content = None if response.code != 200 else response.read()

            if response.headers.get('content-encoding', '') == 'gzip':
                try:
                    content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                except zlib.error:
                    pass

            if response.headers.get('content-type', '') == 'application/json':
                content = json.loads(content, encoding="utf-8")

            response.close()
        except Exception as e:
            log("Failed to get url: %s\n%s" % (url, e))
            # Second parameter is the filename
        return content

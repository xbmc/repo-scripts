# -*- coding: utf-8 -*-
import os
import re
import urllib
import urllib2
import unicodedata
import json
import zlib
import shutil
# from stubs import xbmc
# from stubs import xbmcvfs
# from stubs import xbmcaddon
import xbmc
import xbmcvfs
import xbmcaddon


__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo('version') # Module version
__scriptname__ = __addon__.getAddonInfo('name')
__profile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode("utf-8")
__temp__ = xbmc.translatePath(os.path.join(__profile__, 'temp')).decode("utf-8")



#===============================================================================
# Private utility functions
#===============================================================================
def normalizeString(str):
    return unicodedata.normalize(
        'NFKD', unicode(unicode(str, 'utf-8'))
    ).encode('ascii', 'ignore')


def log(module, msg):
    xbmc.log((u"### [%s] - %s" % (module, msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)


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
        query = {"q": search_string.lower()}
        search_result = self.urlHandler.request(self.BASE_URL + "/he/subtitle/search/?" + urllib.urlencode(query))
        if search_result is None:
            return results # return empty set

        urls = re.findall('<a href=".*/he/subtitle/(movie|series)/([^/]+)/">[^/]+ / ([^<]+)</a>', search_result)
        years = re.findall(u'<span class="special">[^:]+: </span>(\d{4}).<br />', search_result)
        for i, url in enumerate(urls):
            year = years[i] if len(years)>i else ''
            urls[i] += (year,)

        results = self._filter_urls(urls, search_string, item)
        return results


    def _filter_urls(self, urls, search_string, item):
        filtered = []
        search_string = search_string.lower()

        for i, (content_type, slug, eng_name, year) in enumerate(urls):
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
                                         'rating': current["downloaded"],
                                         'sync': subtitle_rate >= 4,
                                         'hearing_imp': current["hearing_impaired"] > 0
                                        })
            # Fix the rating
        if total_downloads:
            for it in ret:
                it["rating"] = str(int(round(it["rating"] / float(total_downloads), 1) * 5))

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


# item = {'episode': '11', 'temp': False, 'title': '', 'season': '11', 'year': '', 'rar': False,
#        'tvshow': 'Two and a Half Men',
#        'file_original_path': u'D:\\Videos\\Series\\Two.and.a.Half.Men\\Season 11\\Two.and.a.Half.Men.S11E13.480p.HDTV.X264-DIMENSION.mkv',
#       '3let_language': ['en', 'he']}
# # item = {'episode': '', 'temp': False, 'title': 'Broken Arrow', 'season': '', 'year': '1997', 'rar': False, 'tvshow': '',
# #         'file_original_path': u'D:\\Videos\\Movies\\Broken Arrow (1996)\\Broken-Arrow_720p BluRay,,DTS.x264-CDDHD.mp4',
# #         '3let_language': ['en', 'he']}
# # {'episode': '4', 'temp': False, 'title': 'Killer Within', 'season': '3', 'year': '', 'rar': False, 'tvshow': 'The Walking Dead', 'file_original_path': u'D:\\Videos\\Series\\The.Walking.Dead\\Season 3\\The.Walking.Dead.S03E04.720p.HDTV.x264-IMMERSE.mkv', '3let_language': ['eng', 'heb']}
# item = {'episode': '', 'temp': False, 'title': 'Free Birds', 'season': '', 'year': '2013', 'rar': False, 'tvshow': '',
#         'file_original_path': u'D:\\Videos\\Movies\\Free.Birds.2013.1080p.BRRip.x264-YIFY\\FB13.1080p.BRRip.x264-YIFY.mp4',
#         '3let_language': ['en', 'he']}
# helper = SubscenterHelper()
# helper.get_subtitle_list(item)
#
#
# def get_rating(subsfile, videofile):
#     x = 0
#     rating = 0
#     log(__scriptname__, "# Comparing Releases:\n %s [subtitle-rls] \n %s [filename-rls]" % (subsfile, videofile))
#     videofile = "".join(videofile.split('.')[:-1]).lower()
#     subsfile = subsfile.lower().replace('.', '')
#     videofile = videofile.replace('.', '')
#     for release_type in releases_types:
#         if release_type in videofile:
#             x += 1
#             if (release_type in subsfile): rating += 1
#     if x: rating = (rating / float(x)) * 4
#     # Compare group name
#     if videofile.split('-')[-1] == subsfile.split('-')[-1]:
#         rating += 1
#     # Group name didn't match
#     # try to see if group name is in the beginning (less info on file less weight)
#     elif videofile.split('-')[0] == subsfile.split('-')[-1]:
#         rating += 0.5
#     if rating > 0:
#         rating *= 2
#     log(__scriptname__, "# Result is: %f" % rating)
#     return round(rating)
#
# # The function receives a subtitles page id number, a list of user selected
# # languages and the current subtitles list and adds all found subtitles matching
# # the language selection to the subtitles list.
# def prepare_subtitle_list(subtitle_page_uri, language_list, file_name):
#     subtitles_list = []
#     # Retrieve the subtitles page (html)
#     try:
#         subtitlePage = getURL(BASE_URL + subtitle_page_uri)
#     except:
#         # Didn't find the page - no such episode?
#         return
#
#     # Didn't find the page - no such episode?
#     if not subtitlePage:
#         return
#
#     log(__scriptname__, "data=%s" % (subtitlePage))
#     found_subtitles = json.loads(subtitlePage, encoding="utf-8")
#
#     for language in found_subtitles.keys():
#         if xbmc.convertLanguage(language, xbmc.ISO_639_2) in language_list:
#             for translator in found_subtitles[language]:
#                 for quality in found_subtitles[language][translator]:
#                     for rating in found_subtitles[language][translator][quality]:
#                         current = found_subtitles[language][translator][quality][rating]
#                         title = current["subtitle_version"]
#                         subtitle_rate = get_rating(title, file_name)
#                         subtitles_list.append(
#                             {'lang_index': language_list.index(xbmc.convertLanguage(language, xbmc.ISO_639_2)),
#                              'filename': title,
#                              'link': current["key"],
#                              'language_name': xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
#                              'language_flag': language,
#                              'ID': current["id"],
#                              'rating': str(subtitle_rate),
#                              'sync': subtitle_rate >= 8,
#                              'hearing_imp': current["hearing_impaired"] > 0
#                             })
#     return subtitles_list
#
#
# def search(item):
#     if item['tvshow']:
#         searchString = item['tvshow'].replace(" ", "+")
#     else:
#         searchString = item['title'].replace(" ", "+")
#     log(__scriptname__, "Search string = %s" % (searchString.lower()))
#
#     # Retrieve the search results (html)
#     searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower())
#     # Search most likely timed out, no results
#     if not searchResults:
#         return
#
#     # Look for subtitles page links
#     if item['tvshow']:
#         subtitleIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
#     else:
#         subtitleIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
#         # Look for more subtitle pages
#
#     pages = re._search(MULTI_RESULTS_PAGE_PATTERN, unicode(searchResults, "utf-8"))
#     # If we found them look inside for subtitles page links
#     if (pages):
#         # Limit to only 2 pages
#         while (int(pages.group("curr_page")) <= 2):
#             searchResults = getURL(BASE_URL + "/he/subtitle/search/?q=" + searchString.lower() + "&page=" + str(
#                 int(pages.group("curr_page")) + 1))
#
#             if item['tvshow']:
#                 tempSIDs = re.findall(TV_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
#             else:
#                 tempSIDs = re.findall(MOVIES_SEARCH_RESULTS_PATTERN, searchResults, re.DOTALL)
#
#             for sid in tempSIDs:
#                 subtitleIDs.append(sid)
#             pages = re._search(MULTI_RESULTS_PAGE_PATTERN, unicode(searchResults, "utf-8"))
#
#     # Uniqify the list
#     subtitleIDs = list(set(subtitleIDs))
#     # If looking for tvshows try to append season and episode to url
#     for i in range(len(subtitleIDs)):
#         subtitleIDs[i] = subtitleIDs[i].replace("/subtitle/", "/cinemast/data/")
#         if item['tvshow']:
#             subtitleIDs[i] = subtitleIDs[i].replace("/series/", "/series/sb/")
#             subtitleIDs[i] += item["season"] + "/" + item["episode"] + "/"
#         else:
#             subtitleIDs[i] = subtitleIDs[i].replace("/movie/", "/movie/sb/")
#
#     file_name = os.path.basename(item['file_original_path']);
#     subtitles_list = []
#     for sid in subtitleIDs:
#         subtitles_list += prepare_subtitle_list(sid, item['3let_language'], file_name)
#
#     if subtitles_list:
#         # Sort the subtitles
#         subtitles_list = sorted(subtitles_list, key=lambda x: int(float(x['rating'])), reverse=True)
#         for it in subtitles_list:
#             listitem = xbmcgui.ListItem(label=it["language_name"],
#                                         label2=it["filename"],
#                                         iconImage=it["rating"],
#                                         thumbnailImage=it["language_flag"]
#             )
#             if it["sync"]:
#                 listitem.setProperty("sync", "true")
#             else:
#                 listitem.setProperty("sync", "false")
#
#             if it.get("hearing_imp", False):
#                 listitem.setProperty("hearing_imp", "true")
#             else:
#                 listitem.setProperty("hearing_imp", "false")
#
#             url = "plugin://%s/?action=download&link=%s&ID=%s&filename=%s" % (
#                 __scriptid__, it["link"], it["ID"], it["filename"])
#             xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=listitem, isFolder=False)
#
#
# def download(id, key, filename, stack=False):
#     subtitle_list = []
#     exts = [".srt", ".sub"]
#
#     ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
#     ## pass that to XBMC to copy and activate
#     if xbmcvfs.exists(__temp__):
#         shutil.rmtree(__temp__)
#     xbmcvfs.mkdirs(__temp__)
#
#     zip = os.path.join(__temp__, "subs.zip")
#     url = BASE_URL + "/subtitle/download/he/" + str(id) + "/?v=" + filename + "&key=" + key
#     log(__scriptname__, "Fetching subtitles using url %s" % url)
#     f = urllib.urlopen(url)
#     with open(zip, "wb") as subFile:
#         subFile.write(f.read())
#     subFile.close()
#     xbmc.sleep(500)
#     xbmc.executebuiltin(('XBMC.Extract("%s","%s")' % (zip, __temp__,)).encode('utf-8'), True)
#
#     for file in xbmcvfs.listdir(__temp__)[1]:
#         full_path = os.path.join(__temp__, file)
#         if os.path.splitext(full_path)[1] in exts:
#             subtitle_list.append(full_path)
#
#     return subtitle_list

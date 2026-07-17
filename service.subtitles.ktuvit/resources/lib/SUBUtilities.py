import os
import re
import unicodedata
import json
import zlib
import shutil

import xbmc
import xbmcvfs
import xbmcaddon
from bs4 import BeautifulSoup

from http.cookiejar import LWPCookieJar
from urllib.request import Request, build_opener, HTTPCookieProcessor
from urllib.parse import urlencode

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo("version")  # Module version
__scriptname__ = __addon__.getAddonInfo("name")
__language__ = __addon__.getLocalizedString
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, "temp", ""))
__kodi_version__ = xbmc.getInfoLabel("System.BuildVersion").split(" ")[0]

regexHelper = re.compile("\W+", re.UNICODE)


# ===============================================================================
# Private utility functions
# ===============================================================================
def normalizeString(_str):
    if not isinstance(_str, str):
        _str = unicodedata.normalize("NFKD", _str)  # .encode('utf-8', 'ignore')
    return _str


def clean_title(item):
    title = os.path.splitext(os.path.basename(item["title"]))
    tvshow = os.path.splitext(os.path.basename(item["tvshow"]))

    if len(title) > 1:
        if re.match(r"^\.[a-z]{2,4}$", title[1], re.IGNORECASE):
            item["title"] = title[0]
        else:
            item["title"] = "".join(title)
    else:
        item["title"] = title[0]

    if len(tvshow) > 1:
        if re.match(r"^\.[a-z]{2,4}$", tvshow[1], re.IGNORECASE):
            item["tvshow"] = tvshow[0]
        else:
            item["tvshow"] = "".join(tvshow)
    else:
        item["tvshow"] = tvshow[0]

    # Removes country identifier at the end
    item["title"] = re.sub(r"\([^\)]+\)\W*$", "", item["title"]).strip()
    item["tvshow"] = re.sub(r"\([^\)]+\)\W*$", "", item["tvshow"]).strip()


def parse_rls_title(item):
    title = regexHelper.sub(" ", item["title"])
    tvshow = regexHelper.sub(" ", item["tvshow"])

    groups = re.findall(
        r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})",
        title,
        re.I,
    )

    if len(groups) == 0:
        groups = re.findall(
            r"(.*?) (\d{4})? ?(?:s|season|)(\d{1,2})(?:e|episode|x|\n)(\d{1,2})",
            tvshow,
            re.I,
        )

    if len(groups) > 0 and len(groups[0]) >= 3:
        title, year, season, episode = groups[0]
        item["year"] = str(int(year)) if len(year) == 4 else year

        item["tvshow"] = regexHelper.sub(" ", title).strip()
        item["season"] = str(int(season))
        item["episode"] = str(int(episode))
        log("TV Parsed Item: %s" % (item,))

    else:
        groups = re.findall(r"(.*?)(\d{4})", item["title"], re.I)
        if len(groups) > 0 and len(groups[0]) >= 1:
            title = groups[0][0]
            item["title"] = regexHelper.sub(" ", title).strip()
            item["year"] = groups[0][1] if len(groups[0]) == 2 else item["year"]

            log("MOVIE Parsed Item: %s" % (item,))


def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, msg), level=xbmc.LOGDEBUG)


def notify(msg_id):
    xbmc.executebuiltin(
        ("Notification(%s,%s)" % (__scriptname__, __language__(msg_id)))
    )


class SubsHelper:
    BASE_URL = "https://www.ktuvit.me/Services"

    def __init__(self):
        self.urlHandler = URLHandler()

    def get_subtitle_list(self, item):
        search_results = self._search(item)
        results = self._build_subtitle_list(search_results, item)

        return results

    # return list of movies / tv-series from the site`s search
    def _search(self, item):
        search_string = (
            re.split(r"\s\(\w+\)$", item["tvshow"])[0]
            if item["tvshow"]
            else item["title"]
        )
        log("search_string: %s" % search_string)

        query = {
            "FilmName": search_string,
            "Actors": [],
            "Studios": None,
            "Directors": [],
            "Genres": [],
            "Countries": [],
            "Languages": [],
            "Year": "",
            "Rating": [],
            "Page": 1,
            "SearchType": "0",
            "WithSubsOnly": False,
        }
        if item["tvshow"]:
            query["SearchType"] = "1"
        elif item["year"]:
            query["Year"] = item["year"]

        search_result = self.urlHandler.request(
            self.BASE_URL + "/ContentProvider.svc/SearchPage_search",
            data={"request": query},
        )

        results = []
        log("Results: %s" % search_result)

        if search_result is None or len(search_result["Films"]) == 0:
            notify(32001)
            return results  # return empty set

        ids = self._get_filtered_ids(search_result["Films"], search_string)
        log("Filtered Ids: %s" % ids)

        if item["tvshow"]:
            results = self._search_tvshow(item, ids)
        else:
            results = self._search_movie(ids)

        log("Subtitles: %s" % results)

        return results

    def _search_tvshow(self, item, ids):
        subs = []

        for id in ids:
            query_string = {
                "moduleName": "SubtitlesList",
                "SeriesID": id,
                "Season": item["season"],
                "Episode": item["episode"],
            }
            raw_html = self.urlHandler.request(
                self.BASE_URL + "/GetModuleAjax.ashx", query_string=query_string
            )

            sub_list = BeautifulSoup(raw_html, "html.parser")
            sub_rows = sub_list.find_all("tr")

            for row in sub_rows:
                columns = row.find_all("td")
                sub = {"id": id}
                for index, column in enumerate(columns):
                    if index == 0:
                        sub["rls"] = column.get_text().strip().split("\n")[0]
                    if index == 4:
                        sub["downloads"] = int(column.get_text().strip())
                    if index == 5:
                        sub["sub_id"] = column.find(
                            "input", attrs={"data-sub-id": True}
                        )["data-sub-id"]

                subs.append(sub)

        return subs

    def _search_movie(self, ids):
        subs = []

        for movie_id in ids:
            query_string = {
                "ID": movie_id,
            }
            raw_html = self.urlHandler.request(
                self.BASE_URL + "/../MovieInfo.aspx", query_string=query_string
            )
            html = BeautifulSoup(raw_html, "html.parser")
            sub_rows = html.select("table#subtitlesList tbody > tr")
            log("html %s" % sub_rows)

            for row in sub_rows:
                columns = row.find_all("td")
                sub = {"id": movie_id}
                for index, column in enumerate(columns):
                    if index == 0:
                        sub["rls"] = column.get_text().strip().split("\n")[0]
                    if index == 4:
                        sub["downloads"] = int(column.get_text().strip())
                    if index == 5:
                        sub["sub_id"] = column.find(
                            "a", attrs={"data-subtitle-id": True}
                        )["data-subtitle-id"]

                subs.append(sub)

        return subs

    def _build_subtitle_list(self, search_results, item):
        language = "he"
        lang3 = xbmc.convertLanguage(language, xbmc.ISO_639_2)
        total_downloads = 0
        ret = []
        for result in search_results:
            title = result["rls"]
            subtitle_rate = self._calc_rating(title, item["file_original_path"])
            total_downloads += result["downloads"]

            ret.append(
                {
                    "lang_index": item["3let_language"].index(lang3),
                    "filename": title,
                    "language_name": xbmc.convertLanguage(language, xbmc.ENGLISH_NAME),
                    "language_flag": language,
                    "id": result["id"],
                    "sub_id": result["sub_id"],
                    "rating": result["downloads"],
                    "sync": subtitle_rate >= 3.8,
                    "hearing_imp": False,
                    "is_preferred": lang3 == item["preferredlanguage"],
                }
            )

        # Fix the rating
        if total_downloads:
            for it in ret:
                log("rating %s totals %s" % (it["rating"], total_downloads))
                it["rating"] = str(
                    int(round(it["rating"] / float(total_downloads), 1) * 5)
                )

        return sorted(
            ret,
            key=lambda x: (x["is_preferred"], x["lang_index"], x["sync"], x["rating"]),
            reverse=True,
        )

    def _calc_rating(self, subsfile, file_original_path):
        file_name = os.path.basename(file_original_path)
        folder_name = os.path.split(os.path.dirname(file_original_path))[-1]

        subsfile = re.sub(r"\W+", ".", subsfile).lower()
        file_name = re.sub(r"\W+", ".", file_name).lower()
        folder_name = re.sub(r"\W+", ".", folder_name).lower()
        log(
            "# Comparing Releases:\n [subtitle-rls] %s \n [filename-rls] %s \n [folder-rls] %s"
            % (subsfile, file_name, folder_name)
        )

        subsfile = subsfile.split(".")
        file_name = file_name.split(".")[:-1]
        folder_name = folder_name.split(".")

        if len(file_name) > len(folder_name):
            diff_file = list(set(file_name) - set(subsfile))
            rating = (1 - (len(diff_file) / float(len(file_name)))) * 5
        else:
            diff_folder = list(set(folder_name) - set(subsfile))
            rating = (1 - (len(diff_folder) / float(len(folder_name)))) * 5

        log(
            "\n rating: %f (by %s)"
            % (
                round(rating, 1),
                "file" if len(file_name) > len(folder_name) else "folder",
            )
        )

        return round(rating, 1)

    def download(self, id, sub_id, filename):
        ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        ## pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            shutil.rmtree(__temp__)
        xbmcvfs.mkdirs(__temp__)

        query = {
            "request": {
                "FilmID": id,
                "SubtitleID": sub_id,
                "FontSize": 0,
                "FontColor": "",
                "PredefinedLayout": -1,
            }
        }

        response = self.urlHandler.request(
            self.BASE_URL + "/ContentProvider.svc/RequestSubtitleDownload", data=query
        )
        f = self.urlHandler.request(
            self.BASE_URL + "/DownloadFile.ashx",
            query_string={"DownloadIdentifier": response["DownloadIdentifier"]},
        )
        with open(filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()

    def login(self, notify_success=False):
        email = __addon__.getSetting("email")
        password = __addon__.getSetting("password")
        post_data = {"request": {"Email": email, "Password": password}}

        response = self.urlHandler.request(
            self.BASE_URL + "/MembershipService.svc/Login", data=post_data
        )
        log(response)
        if response["IsSuccess"] is True:
            self.urlHandler.save_cookie()
            if notify_success:
                notify(32007)
            return True
        else:
            notify(32005)
            return None

    def _get_filtered_ids(self, list, search_string):
        ids = []

        search_string = regexHelper.sub("", search_string).lower()

        for result in list:
            eng_name = regexHelper.sub(
                "", regexHelper.sub(" ", result["EngName"])
            ).lower()
            heb_name = regexHelper.sub("", result["HebName"])

            if (
                search_string.startswith(eng_name)
                or eng_name.startswith(search_string)
                or search_string.startswith(heb_name)
                or heb_name.startswith(search_string)
            ):
                ids.append(result["ID"])

        return ids


class URLHandler:
    def __init__(self):
        cookie_filename = os.path.join(__profile__, "cookiejar.txt")
        self.cookie_jar = LWPCookieJar(cookie_filename)
        if os.access(cookie_filename, os.F_OK):
            self.cookie_jar.load()

        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self.opener.addheaders = [
            ("Accept-Encoding", "gzip"),
            ("Accept-Language", "en-us,en;q=0.5"),
            ("Pragma", "no-cache"),
            ("Cache-Control", "no-cache"),
            ("Content-type", "application/json"),
            (
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Kodi/%s Chrome/78.0.3904.97 Safari/537.36"
                % (__kodi_version__),
            ),
        ]

    def request(self, url, data=None, query_string=None, referrer=None, cookie=None):
        if data is not None:
            data = json.dumps(data).encode("utf8")
        if query_string is not None:
            url += "?" + urlencode(query_string)
        if referrer is not None:
            self.opener.addheaders += [("Referrer", referrer)]
        if cookie is not None:
            self.opener.addheaders += [("Cookie", cookie)]

        content = None
        log("Getting url: %s" % (url))
        if data is not None:
            log("Post Data: %s" % (data))
        try:
            req = Request(url, data, headers={"Content-Type": "application/json"})
            response = self.opener.open(req)
            content = None if response.code != 200 else response.read()

            if response.headers.get("content-encoding", "") == "gzip":
                try:
                    content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                except zlib.error:
                    pass

            if response.headers.get("content-type", "").startswith("application/json"):
                parsed_content = json.loads(content)
                content = json.loads(parsed_content["d"])

            response.close()
        except Exception as e:
            log("Failed to get url: %s\n%s" % (url, e))
            # Second parameter is the filename
        return content

    def save_cookie(self):
        # extend cookie expiration
        for cookie in self.cookie_jar:
            if cookie.expires is not None:
                cookie.expires += 2 * 12 * 30 * 24 * 60 * 60

        self.cookie_jar.save()

# -*- coding: utf-8 -*-
from http.cookiejar import LWPCookieJar
from urllib.request import HTTPCookieProcessor, build_opener
from urllib.parse import urlencode, quote_plus
import json
import os
import re
import unicodedata
import zlib
import bs4
import uuid

import xbmc
import xbmcvfs
import xbmcaddon
import xbmcgui

__addon__ = xbmcaddon.Addon()
__version__ = __addon__.getAddonInfo("version")  # Module version
__scriptname__ = __addon__.getAddonInfo("name")
__language__ = __addon__.getLocalizedString
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
__temp__ = xbmcvfs.translatePath(os.path.join(__profile__, "temp", ""))

regexHelper = re.compile("\W+", re.UNICODE)


def normalizeString(str):
    return unicodedata.normalize("NFKD", str)


def log(msg):
    xbmc.log(("### [%s] - %s" % (__scriptname__, msg)), level=xbmc.LOGDEBUG)


def notify(msg_id):
    xbmcgui.Dialog().notification(__scriptname__, __language__(msg_id))


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


class NapisyHelper:
    BASE_URL = "https://napisy24.pl"

    def __init__(self):
        self.urlHandler = URLHandler()

    def get_subtitle_list(self, item):
        if item["tvshow"]:
            search_results = self._search_tvshow(item)
        else:
            search_results = self._search_movie(item)

        log("Search results: %s" % search_results)
        results = self._build_subtitle_list(search_results, item)
        log("Results: %s" % results)

        return results

    def download(self, id):
        ## Cleanup temp dir, we recomend you download/unzip your subs in temp folder and
        ## pass that to XBMC to copy and activate
        if xbmcvfs.exists(__temp__):
            (dirs, files) = xbmcvfs.listdir(__temp__)
            for file in files:
                xbmcvfs.delete(os.path.join(__temp__, file))
        else:
            xbmcvfs.mkdirs(__temp__)

        subtitle_type_map = ["sru", "sr", "tmp", "mdvd", "mpl2"]
        subs_format = int(__addon__.getSetting("subs_format"))

        query = {"napisId": id, "typ": subtitle_type_map[subs_format]}

        f = self.urlHandler.request(
            self.BASE_URL + "/download", query, referer=self.BASE_URL
        )

        if f is None and self.login(True):
            f = self.urlHandler.request(
                self.BASE_URL + "/download", query, referer=self.BASE_URL
            )

        if f is None:
            return

        zip_filename = os.path.join(__temp__, "%s.zip" % str(uuid.uuid4()))

        with open(zip_filename, "wb") as subFile:
            subFile.write(f)
        subFile.close()

        exts = [".srt", ".sub", ".txt"]
        zip_filepath = "zip://%s" % quote_plus(zip_filename)
        (dirs, files) = xbmcvfs.listdir(zip_filepath)
        subtitle_list = []
        for file in files:
            if os.path.splitext(file)[1] in exts:
                filename_dest = os.path.join(__temp__, file)
                flag = xbmcvfs.copy(zip_filepath + "/" + file, filename_dest)
                if flag:
                    subtitle_list.append(filename_dest)

        return subtitle_list

    def login(self, notify_success=False):
        login_form = self.urlHandler.request(self.BASE_URL + "/cb-login")

        html = bs4.BeautifulSoup(login_form, "html.parser")
        form = html.find("form", attrs={"id": "login-form"})
        inputs = form.find_all("input", attrs={"type": "hidden"})

        username = __addon__.getSetting("username")
        password = __addon__.getSetting("password")
        post_data = {"username": username, "passwd": password, "Submit": ""}

        for input in inputs:
            post_data[input["name"]] = input["value"]

        content = self.urlHandler.request(self.BASE_URL + "/cb-login", data=post_data)

        if content.find(self.BASE_URL + "/cb-logout") > -1:
            self.urlHandler.save_cookie()

            if notify_success:
                notify(32014)

            return True
        else:
            notify(32005)
            return False

    # return list of tv-series from the site`s search
    def _search_tvshow(self, item):
        results = []

        search_string = re.split(r"\s\(\w+\)$", item["tvshow"])[0]

        data = {
            "serial": search_string.encode("utf-8").lower(),
            "sezon": item["season"],
            "epizod": item["episode"],
        }
        search_result = self.urlHandler.request(
            self.BASE_URL + "/run/pages/serial_napis.php", data=data
        )

        if search_result is None:
            return results  # return empty set

        search_result = json.loads(search_result)

        for result in search_result:
            html = bs4.BeautifulSoup(result["table"], "html.parser")
            versions = [
                tag["data-wydanie"]
                for tag in html.find_all("h6", attrs={"data-wydanie": True})
            ][0].split(";")

            for version in versions:
                results.append(
                    {
                        "id": result["napisid"],
                        "title": result["serial"].title(),
                        "release": "%s.%s"
                        % (
                            regexHelper.sub(".", result["serial"].title()),
                            version.strip(),
                        ),
                        "language": "pl",
                        "video_file_size": re.findall("[\d.]+ MB", result["table"])[0],
                        "downloads": int(result["pobran"]),
                    }
                )

        return results

    def _search_movie(self, item):
        query = {"page": 1, "lang": 0, "search": item["title"], "typ": 1}
        content = self.urlHandler.request(self.BASE_URL + "/szukaj", query)
        movie_list = bs4.BeautifulSoup(content, "html.parser")
        movie_list = movie_list.select("[data-napis-id]")

        results = []

        for row in movie_list:
            napis_id = row["data-napis-id"]
            title = row.find("div", {"class": "uu_oo_uu"}).get_text().title()
            column2 = row.find("div", {"class": "infoColumn2"})
            column2 = "".join([str(x) for x in column2.contents])
            column2 = [x.strip() for x in filter(None, column2.split("<br/>"))]
            year = column2[0]
            video_file_size = column2[4]
            releases = row.find("div", attrs={"data-releases": True})["data-releases"]

            for release in releases.split("<br>"):
                release = "%s.%s" % (regexHelper.sub(".", title), release.strip())
                if year == item["year"]:
                    results.append(
                        {
                            "id": napis_id,
                            "title": title,
                            "release": release,
                            "video_file_size": video_file_size,
                            "language": "pl",
                            "downloads": 0,
                        }
                    )

        return results

    def _build_subtitle_list(self, search_results, item):
        results = []
        total_downloads = 0

        for result in search_results:
            lang3 = xbmc.convertLanguage(result["language"], xbmc.ISO_639_2)

            if lang3 in item["3let_language"]:
                total_downloads += result["downloads"]
                results.append(
                    {
                        "lang_index": item["3let_language"].index(lang3),
                        "filename": result["release"],
                        "language_name": xbmc.convertLanguage(
                            result["language"], xbmc.ENGLISH_NAME
                        ),
                        "language_flag": result["language"],
                        "id": result["id"],
                        "rating": result["downloads"],
                        "sync": self._is_synced(
                            item, result["video_file_size"], result["release"]
                        ),
                        "hearing_imp": False,
                        "is_preferred": lang3 == item["preferredlanguage"],
                    }
                )

        # Fix the rating
        if total_downloads:
            for it in results:
                it["rating"] = min(
                    int(round(it["rating"] / float(total_downloads), 1) * 8), 5
                )

        return sorted(
            results,
            key=lambda x: (x["is_preferred"], x["lang_index"], x["sync"], x["rating"]),
            reverse=True,
        )

    def _is_synced(self, item, video_file_size, version):
        sync = False

        if len(video_file_size) > 0:
            video_file_size = float(re.findall("([\d.]+) MB", video_file_size)[0])
            file_size = round(item["file_original_size"] / float(1048576), 2)
            if file_size == video_file_size:
                sync = True

        if not sync:
            sync = self._calc_rating(version, item["file_original_path"]) >= 3.8

        return sync

    def _calc_rating(self, version, file_original_path):
        file_name = os.path.basename(file_original_path)
        folder_name = os.path.split(os.path.dirname(file_original_path))[-1]

        version = re.sub(r"\W+", ".", version).lower()
        file_name = re.sub(r"\W+", ".", file_name).lower()
        folder_name = re.sub(r"\W+", ".", folder_name).lower()
        log(
            "# Comparing Releases:\n [subtitle-rls] %s \n [filename-rls] %s \n [folder-rls] %s"
            % (version, file_name, folder_name)
        )

        version = version.split(".")
        file_name = file_name.split(".")[:-1]
        folder_name = folder_name.split(".")

        if len(file_name) > len(folder_name):
            diff_file = list(set(file_name) - set(version))
            rating = (1 - (len(diff_file) / float(len(file_name)))) * 5
        else:
            diff_folder = list(set(folder_name) - set(version))
            rating = (1 - (len(diff_folder) / float(len(folder_name)))) * 5

        log(
            "\n rating: %f (by %s)"
            % (
                round(rating, 1),
                "file" if len(file_name) > len(folder_name) else "folder",
            )
        )

        return round(rating, 1)


class URLHandler:
    def __init__(self):
        self.cookie_filename = os.path.join(__profile__, "cookiejar.txt")
        self.cookie_jar = LWPCookieJar(self.cookie_filename)
        if os.access(self.cookie_filename, os.F_OK):
            self.cookie_jar.load()

        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        self.opener.addheaders = [
            ("Accept-Encoding", "gzip"),
            ("Accept-Language", "en-us,en;q=0.5"),
            ("Pragma", "no-cache"),
            ("Cache-Control", "no-cache"),
            (
                "User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            ),
        ]

    def request(
        self,
        url,
        query_string=None,
        data=None,
        ajax=False,
        referer=None,
        cookie=None,
        decode_zlib=True,
    ):
        if data is not None:
            self.opener.addheaders += [
                ("Content-Type", "application/x-www-form-urlencoded; charset=UTF-8")
            ]
            data = urlencode(data).encode("utf-8")
        if query_string is not None:
            query_string = urlencode(query_string)
            url += "?" + query_string
        if ajax:
            self.opener.addheaders += [("X-Requested-With", "XMLHttpRequest")]
        if referer is not None:
            self.opener.addheaders += [("Referer", referer)]
        if cookie is not None:
            self.opener.addheaders += [("Cookie", cookie)]

        content = None
        log("Getting url: %s\nData: %s" % (url, data))
        try:
            response = self.opener.open(url, data)

            if response.code == 200:
                content = response.read()

                if decode_zlib and "gzip" in response.headers.get(
                    "content-encoding", ""
                ):
                    try:
                        content = zlib.decompress(content, 16 + zlib.MAX_WBITS)
                    except zlib.error:
                        pass

                if "application/json" in response.headers.get("content-type", ""):
                    content = json.loads(content)
                elif "text/html" in response.headers.get("content-type", ""):
                    content = content.decode("utf-8", "replace")

            response.close()
        except Exception as e:
            log("Failed to get url: %s\n%s" % (url, e))
            # Second parameter is the filename
        return content

    def save_cookie(self):
        self.cookie_jar.save()

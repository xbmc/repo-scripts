# -*- coding: utf-8 -*-
import json
import os
import re
import ssl
import unicodedata
from typing import Union
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import xbmc
import xbmcvfs

TheTVDBApi = "A1738606AC58C23D"
TMDBApi = "96e0692265de9b2019b16f0c144efa56"


def decodeString(input_str: Union[str, bytes, bytearray]):
    if isinstance(input_str, bytes) or isinstance(input_str, bytearray):
        try:
            input_str = input_str.decode('utf-8')
        except UnicodeDecodeError:
            log(
                "Could not decode string using UTF-8. Trying Windows-1252",
                "ERROR")
            try:
                input_str = input_str.decode('cp1252')
            except UnicodeDecodeError:
                log(
                    "Could not decode string using Windows-1252. "
                    "Trying ISO-8859-1",
                    "ERROR")
                try:
                    input_str = input_str.decode('iso-8859-1')
                except UnicodeDecodeError:
                    pass
    if isinstance(input_str, bytes) or isinstance(input_str, bytearray):
        # this still hasn't been decoded. Let's go with UTF-8 and ignore errors.
        log(
            "Everything else failed. Decoding to UTF-8 and ignoring errors.",
            "ERROR")
        input_str = input_str.decode('utf-8', 'ignore')
    return input_str


def normalizeString(input_str: Union[str, bytes, bytearray]):
    input_str = decodeString(input_str)

    nfkd_form = unicodedata.normalize('NFKD', input_str)
    text = nfkd_form.encode('ascii', 'ignore')
    return text.decode("utf-8")


def safeFilename(filename):
    keepcharacters = (' ', '.', '_', '-')
    return "".join(
        c for c in filename if c.isalnum() or c in keepcharacters).rstrip()


def log(msg, logtype="DEBUG"):
    # xbmc.log((u"### [%s] - %s" % (__scriptname__,msg,)).encode('utf-8'),level=xbmc.LOGDEBUG )
    if logtype == "DEBUG":
        loglevel = xbmc.LOGDEBUG
    elif logtype == "INFO":
        loglevel = xbmc.LOGINFO
    elif logtype == "ERROR":
        loglevel = xbmc.LOGERROR
    else:
        loglevel = xbmc.LOGDEBUG
    xbmc.log(
        ("### [LegendasTV] - %s" % msg),
        level=loglevel)


def getTheTVDBToken():
    HTTPRequest = Request(
        "https://api.thetvdb.com/login",
        data=json.dumps({"apikey": TheTVDBApi}).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    try:
        HTTPResponse = urlopen(HTTPRequest).read()
        return json.loads(HTTPResponse)['token']
    except:
        return None


def getShowId():
    try:
        playerid_query = '{' \
                         '  "jsonrpc": "2.0",' \
                         '  "method": "Player.GetActivePlayers",' \
                         '  "id": 1' \
                         '}'
        playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0][
            'playerid']
        tvshowid_query = '{' \
                         '  "jsonrpc": "2.0",' \
                         '  "method": "Player.GetItem",' \
                         '  "params": {' \
                         f'     "playerid": {str(playerid)},' \
                         '      "properties": [' \
                         '          "tvshowid"' \
                         '      ]' \
                         '  },' \
                         '  "id": 1' \
                         '}'
        tvshowid = \
            json.loads(xbmc.executeJSONRPC(tvshowid_query))['result']['item'][
                'tvshowid']
        tvdbid_query = '{' \
                       '    "jsonrpc": "2.0",' \
                       '    "method": "VideoLibrary.GetTVShowDetails",' \
                       '    "params": {' \
                       f'       "tvshowid": {str(tvshowid)},' \
                       '        "properties": [' \
                       '            "imdbnumber"' \
                       '        ]' \
                       '    },' \
                       '    "id": 1' \
                       '}'
        tvdbid = json.loads(xbmc.executeJSONRPC(tvdbid_query))['result'][
            'tvshowdetails']['imdbnumber']
        log("getShowId: got TVDB id ->%s<-" % tvdbid, "DEBUG")
        return tvdbid
    except:
        log("Failed to find TVDBid in database,", "ERROR")
        return None


def getShowIMDB():
    ShowID = getShowId()
    if ShowID:
        try:
            TheTVDBToken = getTheTVDBToken()
            HTTPRequest = Request(
                "https://api.thetvdb.com/series/%s" % ShowID,
                headers={'Authorization': 'Bearer %s' % TheTVDBToken})
            HTTPResponse = urlopen(HTTPRequest).read()
            JSONContent = json.loads(HTTPResponse)
            if "data" in JSONContent:
                ShowIMDB = JSONContent['data']['imdbId']
                log("getShowIMDB: got IMDB id ->%s<-" % ShowIMDB, "DEBUG")
                return ShowIMDB
        except:
            log("getShowIMDB: Failed to get IMDB id.", "DEBUG")
            return None
    else:
        return None


def getMovieIMDB():
    try:
        playerid_query = '{' \
                         '  "jsonrpc": "2.0",' \
                         '  "method": "Player.GetActivePlayers",' \
                         '  "id": 1' \
                         '}'
        playerid = json.loads(xbmc.executeJSONRPC(playerid_query))['result'][0][
            'playerid']
        movieid_query = '{' \
                        '   "jsonrpc": "2.0",' \
                        '   "method": "Player.GetItem",' \
                        '  "params": {' \
                        f'      "playerid": {str(playerid)},' \
                        '       "properties": [' \
                        '           "imdbnumber", ' \
                        '           "title", ' \
                        '           "year"' \
                        '       ]}, ' \
                        '   "id": 1' \
                        '}'
        movieid = json.loads(xbmc.executeJSONRPC(movieid_query))
        # print(json.dumps(movieid, sort_keys=True, indent=4, separators=(',', ': ')))

        if "imdbnumber" in movieid['result']['item'] and len(
                movieid['result']['item']["imdbnumber"]):
            log("getMovieIMDB: IMDB id ->%s<- already on database." %
                movieid['result']['item']["imdbnumber"], "DEBUG")
            return movieid['result']['item']["imdbnumber"]
        elif "title" in movieid['result']['item'] and len(
                movieid['result']['item']["title"]):
            MovieTitle = movieid['result']['item']["title"]
            Query = urlencode({
                "api_key": TMDBApi,
                "page": "1",
                "query": MovieTitle,
                "year": movieid["result"]["item"]["year"]
            })
            HTTPRequest = Request(
                "https://api.themoviedb.org/3/search/movie", data=Query.encode("utf-8"))
            HTTPRequest.get_method = lambda: "GET"
            try:
                HTTPResponse = urlopen(HTTPRequest).read()
            except Exception as e:
                log("getMovieIMDB: TMDB download error: %s" % str(e))

            JSONContent = json.loads(HTTPResponse)
            if len(JSONContent['results']):
                TMDBId = JSONContent['results'][0]['id']
                HTTPRequest = Request(
                    "https://api.themoviedb.org/3/movie/%s?api_key=%s" % (
                        TMDBId, TMDBApi))
                HTTPResponse = urlopen(HTTPRequest).read()
                JSONContent = json.loads(HTTPResponse)
                if "imdb_id" in JSONContent:
                    log("getMovieID: got IMDB ->%s<- from TMDB" % JSONContent[
                        "imdb_id"], "DEBUG")
                    return JSONContent["imdb_id"]
            return None
    except:
        return None


def getTVShowOrginalTitle(Title, ShowID):
    if ShowID:
        try:
            TheTVDBToken = getTheTVDBToken()
        except Exception as e:
            log("xbmcOriginalTitle: TheTVDBToken failed: %s" % str(e))
            return normalizeString(Title)
        print("https://api.thetvdb.com/series/%s" % ShowID)
        HTTPRequest = Request(
            "https://api.thetvdb.com/series/%s" % ShowID,
            headers={'Authorization': 'Bearer %s' % TheTVDBToken})
        print(HTTPRequest)
        HTTPResponse = urlopen(HTTPRequest).read()

        try:
            JSONContent = json.loads(HTTPResponse)
        except Exception as e:
            return normalizeString(Title)

        if "data" in JSONContent:
            OriginalTitle = JSONContent['data']['seriesName']
            log("getTVShowOrginalTitle: %s" % OriginalTitle, "DEBUG")
            return OriginalTitle
    else:
        return Title


def getMovieOriginalTitle(Title, MovieID):
    if MovieID:
        HTTPRequest = Request(
            "https://api.themoviedb.org/3/find/%s?external_source=imdb_id&api_key=%s" % (
                MovieID, TMDBApi))
        context = ssl.create_default_context()
        HTTPResponse = urlopen(HTTPRequest, context=context).read()
        JSONContent = json.loads(HTTPResponse)
        if len(JSONContent["movie_results"]):
            return normalizeString(
                JSONContent["movie_results"][0]['original_title'])
    else:
        return Title


def isStacked(subA, subB):
    subA, subB = re.escape(subA), re.escape(subB)
    regexesStacked = [
        re.compile(r"(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[0-9]+)(.*?)(\.[^.]+)$"),
        re.compile(r"(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[a-d])(.*?)(\.[^.]+)$"),
        re.compile(r"(.*?)([ ._-]*[a-d])(.*?)(\.[^.]+)$")
    ]
    for regex in regexesStacked:
        if regex.search(subA):
            fnA, diskA, otherA, extA = re.findall(regex, subA)[0]
            if regex.search(subB):
                fnB, diskB, otherB, extB = re.findall(regex, subB)[0]
                if fnA == fnB and otherA == otherB:
                    return True
    return False


# based on extract_all_libarchive by @zachmorris
def extractArchiveToFolder(translated_archive_url, extract_to_dir):
    overall_success = True
    files_out = list()

    log('-----------------------------------------------------------')
    log('---- Extracting archive URL: %s' % translated_archive_url)
    log('---- To directory: %s' % extract_to_dir)

    log('---- Calling xbmcvfs.listdir...')
    dirs_in_archive, files_in_archive = xbmcvfs.listdir(translated_archive_url)

    for ff in files_in_archive:

        log('---- File found in archive: %s' % ff)

        url_from = os.path.join(translated_archive_url, ff).replace('\\', '/')
        log('---- URL from: %s' % url_from)

        file_to = os.path.join(xbmcvfs.translatePath(extract_to_dir), ff)
        log('---- File to: %s' % file_to)

        log('---- Calling xbmcvfs.copy...')
        copy_success = xbmcvfs.copy(url_from, file_to)

        if not copy_success:
            log('---- Copy ERROR!!!!!')
            overall_success = False
        else:
            log('---- Copy OK')
            files_out.append(file_to)

    for dd in dirs_in_archive:

        log('---- Directory found in archive: %s' % dd)

        dir_to_create = os.path.join(extract_to_dir, dd)
        log('---- Directory to create: %s' % dir_to_create)

        log('---- Calling xbmcvfs.mkdir...')
        mkdir_success = xbmcvfs.mkdir(dir_to_create)

        if mkdir_success:

            log('---- Mkdir OK')

            dir_inside_archive_url = translated_archive_url + '/' + dd + '/'
            log(
                '---- Directory inside archive URL: %s' % dir_inside_archive_url)

            log('---- Calling extractArchiveToFolder...')
            files_out2, success2 = extractArchiveToFolder(
                dir_inside_archive_url, dir_to_create)

            if success2:
                files_out = files_out + files_out2
            else:
                overall_success = False

        else:
            overall_success = False
            log('---- Mkdir ERROR!!!!!')

    return files_out, overall_success

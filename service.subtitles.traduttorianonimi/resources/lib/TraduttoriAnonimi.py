# -*- coding: utf-8 -*-
#
#  TraduttoriAnonimi.py
#  
#  Copyright 2017 ShellAddicted <shelladdicted@gmail.com<>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#

__author__ = "ShellAddicted"
__copyright__ = "Copyright 2017, ShellAddicted"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "ShellAddicted"
__email__ = "shelladdicted@gmail.com"
__status__ = "Development"

import re

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

try:
    xrange
except NameError:
    xrange = range

from bs4 import BeautifulSoup
import requests

import logging

class TraduttoriAnonimi:

    def __init__(self, baseURL="http://traduttorianonimi.it", showsListPath="elenco-serie/",headers={"user-agent": "Kodi-SubtitleService-TraduttoriAnonimi"}):
        self._initLogger();

        self._baseURL = baseURL
        self.log.debug("baseURL=> {0}".format(self._baseURL))

        self._showsListPath = showsListPath
        self.log.debug("showsListPath=> {0}".format(self._showsListPath))

        self._showsListURL = urlparse.urljoin(self._baseURL, self._showsListPath)
        self.log.debug("showsListURL=> {0}".format(self._showsListURL))

        self._headers=headers

        self._showsList = {}
        self.UpdateShowsList()

    def _initLogger(self):
        self.log = logging.getLogger("TraduttoriAnonimi")
        self.log.setLevel(logging.DEBUG)
        style = logging.Formatter("{%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s")
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(style)
        self.log.addHandler(consoleHandler)

    def _retriveURL(self,url, headers=None):
        """
        return a requests response object of a GET Request
        :param url: url to the resource
        :param headers: headers of the request
        :return: requests.models.Response or None
        """
        if headers is None:
            headers=self._headers

        try:
            self.log.debug("GET Request => HEADERS={0} ; URL={1}".format(headers, url))
            q = requests.get(url, headers=headers)
            self.log.debug("GET Request <= Response HEADERS={0}".format(q.headers))
            return q
        except:
            return None

    def _searchInDict(self,token, where):
        showNameRegex = re.compile(self._magicUnicode(token), re.IGNORECASE)
        result = []

        for x, y in where.items():
            if showNameRegex.search(self._magicUnicode(x)):
                result.append({"Name": x, "URL": y})

        if len(result) == 0:
            result = None

        return result

    @staticmethod
    def _magicUnicode(data):
        """
        Return Unicode (utf-8) text encoded
        :param data: data (text) to encode
        :return:
        """
        # unicode is not defined in python3.x
        if type(data) != bytes:
            return str(data).encode("utf-8")
        else:
            return data

    @staticmethod
    def _magicInt(x):
        """
        Cast to integer (if possible) without raise an exception (that is ignored)
        :param x: value to Cast
        :return: int (if possible) else exactly the input (x)
        """
        try:
            return int(x)
        except (TypeError, ValueError):
            return x

    def UpdateShowsList(self):
        self.log.info("Grabbing Shows list from Website.")
        url = self._showsListURL

        self.log.debug("self._showsList re-initialized")
        self._showsList = {}

        for attempt in xrange(100):
            r = self._retriveURL(url)
            self.log.debug("Attempt #{0}".format(attempt))
            if r is not None:
                html = r.content
                parser = BeautifulSoup(html, "html.parser")

                for showTag in parser.findAll("a", {"href": re.compile("serie\?c=\d+", re.IGNORECASE)}):
                    showName = self._magicUnicode(showTag.find("img").attrs["title"])
                    self._showsList[showName] = showTag.attrs["href"]

                try:
                    tmp = parser.find("div", {"class": "pagination"}).find("a", {"class": "next"})
                except AttributeError:
                    tmp = None

                if tmp is not None:
                    url = urlparse.urljoin(self._baseURL, tmp.attrs["href"])
                    self.log.debug("Next Page Found. Following => {0}".format(url))
                else:
                    self.log.debug("Next Page Not Found. Exiting from loop")
                    break
            else:
                self.log.error("response is None. Exiting from loop")
                break
        return self._showsList

    def searchTvShow(self,showName):
        return self._searchInDict(showName,self._showsList)

    def getSubtitles(self, showName, season, episode):
        showName = self._magicUnicode(showName)
        self.log.debug("Searching "+str(showName)+"  s"+str(season)+" e"+str(episode))
        showsResults = self._searchInDict(showName, self._showsList)
        episodeRegex = re.compile(
            "(?P<tvshowname>.+)(?:(?:\s|s|\.)|\.s|\.so)(?P<season>\d+)(?:x|e|\.x|\.e)(?P<episode>\d+)", re.IGNORECASE)
        if showsResults is None:
            self.log.info("No showsResults")
            return []
        subtitlesResults = []
        for show in showsResults:
            r = self._retriveURL(show["URL"])
            if r is not None:
                html = r.content
                parser = BeautifulSoup(html, "html.parser")

                for ep in parser.findAll("td", {"class": "dwn"}):
                    subs=ep.findAll("a")
                    if subs is not None:
                        for tmp in subs:
                            self.log.debug("Analyzing => {0}".format(tmp))
                            if tmp is not None and "title" in tmp.attrs and "href" in tmp.attrs:
                                x = episodeRegex.search(tmp.attrs["title"])
                                self.log.debug("Regex Groups=> {0}".format(x.groups()))
                                if self._magicInt(x.group("season")) == season and self._magicInt(x.group("episode")) == episode:
                                    self.log.info("Subtitle Found")
                                    subtitlesResults.append({"Name": tmp.attrs["title"], "URL": tmp.attrs["href"]})
        return subtitlesResults
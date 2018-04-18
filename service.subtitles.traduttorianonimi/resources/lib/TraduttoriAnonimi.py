# -*- coding: utf-8 -*-
#
#  TraduttoriAnonimi.py
#  
#  Copyright 2018 ShellAddicted <shelladdicted@gmail.com>
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

__author__ = "ShellAddicted"
__copyright__ = "Copyright 2018, ShellAddicted"
__license__ = "GPL"
__version__ = "1.1.0"
__maintainer__ = "ShellAddicted"
__email__ = "shelladdicted@gmail.com"
__status__ = "Development"

import re
import logging

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

class TraduttoriAnonimi:

    def __init__(self, baseURL="http://traduttorianonimi.it", showsListPath="elenco-serie/?S={0}", headers={"user-agent": "Kodi-SubtitleService-TraduttoriAnonimi"}):
        self._baseURL = baseURL
        self._showsListURL = urlparse.urljoin(baseURL, showsListPath)
        self._headers = headers
        
        self._episodeRegex = re.compile("(?P<tvshowname>.+)(?:(?:\s|s|\.)|\.s|\.so)(?P<season>\d+)(?:x|e|\.x|\.e)(?P<episode>\d+)", re.IGNORECASE)

        self._log = logging.getLogger("TraduttoriAnonimi")

    def _retriveURL(self, url):
        try:
            return requests.get(url, headers = self._headers)
        except Exception:
            self._log.error("request failed.", exc_info=True)
            return None

    def _searchInDict(self, token, where):
        results = []
        showNameRegex = re.compile(self._magicUnicode(token), re.IGNORECASE)
        for name, url in where.items():
            if showNameRegex.search(self._magicUnicode(name)):
                results.append({"Name": name, "URL": url})
        return results

    @staticmethod
    def _magicUnicode(data):
        # unicode is not defined in python3, use bytes
        if type(data) != bytes:
            return str(data).encode("utf-8")
        else:
            return data

    @staticmethod
    def _magicInt(x):
        try:
            return int(x)
        except (TypeError, ValueError):
            return x

    def getShows(self, firstLetter="*"):
        # Get Shows as a dict {showName: showURL}
        shows = {}

        for fl in "abcdefghijklmnopqrstuvwxyz" if firstLetter == "*" else firstLetter[0]:
            for attempt in xrange(5): # Max 5 attempts
                # Shows are alphabetically ordered, so go directly to the right position
                # Sample URL: http://www.traduttorianonimi.it/elenco-serie/?S=Tt  where 'Tt' (T) is the first letter of show title [lower+upper(case)]
                
                self._log.debug("Loading shows... Attempt #{0}".format(attempt))
                r = self._retriveURL(self._showsListURL.format(fl.upper() + fl.lower()))
                try:
                    if r is not None:
                        parser = BeautifulSoup(r.content, "html.parser")
                        for showTag in parser.findAll("a", {"href": re.compile("serie\?c=\d+", re.IGNORECASE)}):
                            showTitle = self._magicUnicode(showTag.find("img").attrs["title"])
                            shows[showTitle] = showTag.attrs["href"]
                        self._log.info("Shows successfully loaded.")
                        break
                    else:
                        self._log.error("Invalid response, retry.")

                except Exception:
                    self._log.error("loading failed.", exc_info=True)  # Log the error and continue
        return shows

    def getSubtitles(self, showName, season, episode):
        shows = self.getShows(showName[0])
        showMatches = self._searchInDict(showName, shows) # Search for the correct show
        if showMatches is []:
            self._log.error("Show not found :-(")
            return []

        subtitlesResults = []
        for show in showMatches:
            r = self._retriveURL(show["URL"])
            if r is not None:
                try:
                    parser = BeautifulSoup(r.content, "html.parser")
                    for ep in parser.findAll("td", {"class": "dwn"}):
                        subs = ep.findAll("a")
                        if subs is not None:
                            for tmp in subs:
                                if tmp is not None and "title" in tmp.attrs and "href" in tmp.attrs:
                                    x = self._episodeRegex.search(tmp.attrs["title"])
                                    if self._magicInt(x.group("season")) == season and self._magicInt(x.group("episode")) == episode:
                                        subtitlesResults.append({"Name": tmp.attrs["title"], "URL": tmp.attrs["href"]})
                except Exception:
                    self._log.error("parsing failed", exc_info=True)
            else:
                self._log.error("empty response.")
        return subtitlesResults
#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import os, random, re, time, zlib
from urllib.request import urlopen
from typing import Callable

import xbmcgui, xbmcvfs

from resources.lib.util import logger
from .strings import *


class Imdb:
    QUOTES_INDEX = 'quotes.index'
    QUOTES_LIST = 'quotes.list'
    QUOTES_URL = 'ftp://ftp.fu-berlin.de/pub/misc/movies/database/frozendata/quotes.list.gz'

    def __init__(self):
        listsPath = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
        self.quotesIndexPath = os.path.join(listsPath, self.QUOTES_INDEX)
        self.quotesListPath = os.path.join(listsPath, self.QUOTES_LIST)
        self.quotesIndex = None

    def isDataPresent(self):
        return os.path.exists(self.quotesIndexPath) and os.path.exists(self.quotesListPath)

    def loadData(self):
        if os.path.exists(self.quotesIndexPath):
            startTime = time.time()
            f = open(self.quotesIndexPath, encoding='utf8')
            self.quotesIndex = f.read()
            f.close()
            logger.debug(f"Loaded {len(self.quotesIndex) / 1048576} MB quotes index in {time.time() - startTime} seconds")

    def downloadFiles(self, downloadState):
        downloadState.idx += 1
        self._downloadGzipFile(self.QUOTES_URL, self.quotesListPath, downloadState.progress, self._createQuotesIndex)

    def getRandomQuote(self, name, year=None, season=None, episode=None, maxLength=None):
        quotes = self._loadQuotes(name, season, episode, year)
        if not quotes:
            return None

        quote = None
        for retries in range(0, 25):
            quote = quotes[random.randint(0, len(quotes)-1)]
            if maxLength is None or len(quote) < maxLength:
                break

        # filter and cleanup
        return re.sub(r'\n  ', ' ', quote)

    def _createQuotesIndex(self, line: str):
        """
        Creates an index file of the QUOTES_LIST file. The index contains
        byte offsets of each movie title to make it possible to load just
        part of the QUOTES_LIST file.

        :param line: a line from QUOTES_LIST
        """
        if not hasattr(self, 'indexFile'):
            self.bytesProcessed = 0
            self.indexFile = open(self.quotesIndexPath, 'w', encoding='utf8')

        if line.startswith('#'):
            self.indexFile.write(line[2:].strip() + "\t" + str(self.bytesProcessed) + "\n")

        # must get length of bytes encoded as utf-8, and must decode files as utf-8, in order for the byte offset to work.
        self.bytesProcessed += len(line.encode('utf8'))
        return line

    def _downloadGzipFile(self, url: str, destination: str, progressCallback: Callable = None, postprocessLineCallback = None):
        """
        Downloads a gzip compressed file and extracts it on the fly.
        Optionally providing progress via the progressCallback and postprocessing on a line level
        via the postprocessLineCallback.

        :param url: the full url of the gzip file
        :param destination: the full path of the destination file
        :param progressCallback: a callback function which is invoked periodically with progress information
        """
        response = urlopen(url, timeout=30)
        file = open(destination, 'w', encoding='utf8')
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)

        partialLine = None
        contentReceived = 0
        contentLength = int(response.headers.get('Content-Length'))
        while True:
            chunk = response.read(102400)
            if not chunk:
                break
            contentReceived += len(chunk)
            decompressedChunk = decompressor.decompress(chunk).decode('iso-8859-1')

            if postprocessLineCallback is not None:
                if partialLine is not None:
                    decompressedChunk = partialLine + decompressedChunk
                    partialLine = None

                lines = decompressedChunk.splitlines(True)
                processedChunk = ''

                for line in lines:
                    if line[-1:] == '\n': # We have a complete line
                        processedLine = postprocessLineCallback(line)
                        if processedLine != '':
                            processedChunk += processedLine
                    else: # partial line
                        partialLine = line
                file.write(processedChunk)

            else:
                file.write(decompressedChunk)

            if progressCallback is not None:
                percentage = int(contentReceived * 100 / contentLength)
                if not progressCallback(contentReceived, contentLength, percentage):
                    break

        file.close()
        response.close() # todo: .close() may not be needed/supported anymore. should I be using "with" syntax?

    def _loadQuotes(self, name: str, season: str, episode: str, year):
        """
        Loads quotes from QUOTES_LIST using the byte offsets in QUOTES_INDEX,
        so we only need to load a few kilobytes instead of a few 100 megabytes.

        :param name: the name of the movie or tv show
        :param season: the season of the tv show
        :param episode: the episode of the tv show
        :return a list containing the individual quotes from the movie or tv show
        """
        # find position using index
        if season is not None and episode is not None:
            pattern = rf'\n"{name}" \([0-9]+\)( \{{.*?\(\#{season}.{episode}\)\}})?\t([0-9]+)\n[^\t]+\t([0-9]+)'
            start = 2
            end = 3
        else:
            year = '' if year is None else year
            pattern = rf'\n{name} *\({year}[^\t]+\t([0-9]+)\n[^\t]+\t([0-9]+)'
            start = 1
            end = 2
        m = re.search(pattern, self.quotesIndex, re.DOTALL)
        if m is None:
            return []

        # load quotes based on position
        f = open(self.quotesListPath, encoding='utf8')
        f.seek(int(m.group(start)))
        quotes = f.read(int(m.group(end)) - int(m.group(start)))
        f.close()

        # remove first line, remove last two newline chars, and split on double new lines
        return quotes[quotes.find('\n')+1:-2].split('\n\n')


def downloadData():
    class DownloadState:
        def __init__(self, count):
            self.idx = 0
            self.count = count

        def progress(self, received, size, percentage):
            line1 = strings(M_FILE_X_OF_Y) % (self.idx, self.count)
            line2 = strings(M_RETRIEVED_X_OF_Y_MB) % (received / 1048576, size / 1048576)
            d.update(percentage, line1 + "\n" + line2)
            return not d.iscanceled()

    i = Imdb()
    d = xbmcgui.DialogProgress()
    try:
        ds = DownloadState(1)
        d.create(strings(M_DOWNLOADING_IMDB_DATA))
        i.downloadFiles(ds)

        canceled = d.iscanceled()
        d.close()
        del d

        if not canceled:
            xbmcgui.Dialog().ok(strings(M_DOWNLOADING_IMDB_DATA), strings(M_DOWNLOAD_COMPLETE))
    except Exception as ex:
        d.close()
        del d
        xbmcgui.Dialog().ok(strings(M_DOWNLOADING_IMDB_DATA), str(ex))

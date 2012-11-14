#
#      Copyright (C) 2012 Tommy Winther
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

import re
import random
import os
import urllib2
import zlib
import time

from strings import *

import xbmc
import xbmcgui

class Imdb(object):
    ACTOR_PATTERN = re.compile('^([^\t\(]+)( \([^\)]+\))?\t.*?$')

    QUOTES_INDEX = 'quotes.index'
    QUOTES_LIST = 'quotes.list'
    QUOTES_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz'
    ACTORS_LIST = 'actors.list'
    ACTORS_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/actors.list.gz' 

    def __init__(self):
        listsPath = xbmc.translatePath(ADDON.getAddonInfo('profile'))
        self.actorsPath = os.path.join(listsPath, self.ACTORS_LIST)
        self.quotesIndexPath = os.path.join(listsPath, self.QUOTES_INDEX)
        self.quotesListPath = os.path.join(listsPath, self.QUOTES_LIST)

        self.actorNames = None
        self.quotesIndex = None

    def isDataPresent(self):
        return os.path.exists(self.actorsPath) and os.path.exists(self.quotesIndexPath) and os.path.exists(self.quotesListPath)

    def loadData(self):
        if os.path.exists(self.quotesIndexPath):
            startTime = time.time()
            f = open(self.quotesIndexPath)
            self.quotesIndex = f.read()
            f.close()
            xbmc.log("Loaded %d MB quotes index in %d seconds" % (len(self.quotesIndex) / 1048576, (time.time() - startTime)))

        if os.path.exists(self.actorsPath):
            startTime = time.time()
            f = open(self.actorsPath)
            self.actorNames = f.read().decode('iso-8859-1').splitlines()
            f.close()
            xbmc.log("Loaded %d actor names in %d seconds" % (len(self.actorNames), (time.time() - startTime)))

    def downloadFiles(self, downloadState):
        downloadState.idx += 1
        self._downloadGzipFile(self.QUOTES_URL, self.quotesListPath, downloadState.progress, self._createQuotesIndex)
        downloadState.idx += 1
        self._downloadGzipFile(self.ACTORS_URL, self.actorsPath, downloadState.progress, self._postprocessActorNames)


    def getRandomQuote(self, name, season = None, episode = None, maxLength = None):
        quotes = self._loadQuotes(name, season, episode)
        if not quotes:
            return None

        quote = None
        for retries in range(0, 25):
            quote = quotes[random.randint(0, len(quotes)-1)]
            if maxLength is None or len(quote) < maxLength:
                break

        # filter and cleanup
        return re.sub('\n  ', ' ', quote)

    def isActor(self, name):
        if self.actorNames:
            #m = re.search('^%s$' % name, self.actorNames, re.MULTILINE)
            return name in self.actorNames
        else:
            xbmc.log("%s does not exists, has it been downloaded yet?" % self.ACTORS_LIST)
            return None


    def _postprocessActorNames(self, line):
        """
        Changes author names from Lastname, Firstname into Firstname Lastname line by line
        and removes duplicate lines. It is assumed the lines are provided sorted.

        @param line: a line from ACTORS_LIST
        @type line: str
        """
        if not hasattr(self, 'previousLastnameFirstname'):
            self.previousLastnameFirstname = None

        m = self.ACTOR_PATTERN.search(line)
        if m is not None:
            lastnameFirstname = m.group(1).strip()
            if lastnameFirstname != self.previousLastnameFirstname:
                self.previousLastnameFirstname = lastnameFirstname

                parts = lastnameFirstname.split(', ', 2)
                if len(parts) == 2:
                    firstnameLastname = "%s %s\n" % (parts[1], parts[0])
                    return firstnameLastname

        return ''

    def _createQuotesIndex(self, line):
        """
        Creates an index file of the QUOTES_LIST file. The index contains
        byte offsets of each movie title to make it possible to load just 
        part of the QUOTES_LIST file.

        @param line: a line from QUOTES_LIST
        @type line: str
        """
        if not hasattr(self, 'indexFile'):
            self.bytesProcessed = 0
            self.indexFile = open(self.quotesIndexPath, 'w')

        if line.startswith('#'):
            self.indexFile.write(line[2:].strip() + "\t" + str(self.bytesProcessed) + "\n")

        self.bytesProcessed += len(line)
        return line


    def _downloadGzipFile(self, url, destination, progressCallback = None, postprocessLineCallback = None):
        """
        Downloads a gzip compressed file and extracts it on the fly.
        Optionally providing progress via the progressCallback and postprocessing on a line level
        via the postprocessLineCallback.

        @param url: the full url of the gzip file
        @type url: str
        @param destination: the full path of the destination file
        @type destination: str
        @param progressCallback: a callback function which is invoked periodically with progress information
        @type progressCallback: method
        """
        response = urllib2.urlopen(url, timeout=30)
        file = open(destination, 'wb')
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)

        partialLine = None
        contentReceived = 0
        contentLength = int(response.info()['Content-Length'])
        while True:
            chunk = response.read(102400)
            if not chunk:
                break
            contentReceived += len(chunk)
            decompressedChunk = decompressor.decompress(chunk)

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
        response.close()

    def _loadQuotes(self, name, season, episode):
        """
        Loads quotes from QUOTES_LIST using the byte offsets in QUOTES_INDEX,
        so we only need to load a few kilobytes instead of a few 100 megabytes.

        @param name: the name of the movie or tv show
        @type name: str
        @param season: the season of the tv show
        @type season: str
        @param episode: the episode of the tv show
        @type episode: str
        @return a list containing the individual quotes from the movie or tv show
        """
        # find position using index
        if season is not None and episode is not None:
            pattern = '\n"%s".*?\(\#%s.%s\)\}\t([0-9]+)\n[^\t]+\t([0-9]+)' % (name, season, episode)
        else:
            pattern = '\n%s [^\t]+\t([0-9]+)\n[^\t]+\t([0-9]+)' % name
        m = re.search(pattern, self.quotesIndex, re.DOTALL)
        if m is None:
            return []

        # load quotes based on position
        f = open(self.quotesListPath)
        f.seek(int(m.group(1)))
        quotes = f.read(int(m.group(2)) - int(m.group(1)))
        f.close()

        # remove first line and split on double new lines
        return quotes[quotes.find('\n')+1:-2].split('\n\n')

if __name__ == '__main__':
    # this script is invoked from addon settings

    # Make sure data dir exists
    if not os.path.exists(xbmc.translatePath(ADDON.getAddonInfo('profile'))):
        os.makedirs(xbmc.translatePath(ADDON.getAddonInfo('profile')))

    class DownloadState(object):
        def __init__(self, count):
            self.idx = 0
            self.count = count

        def progress(self, received, size, percentage):
            line1 = strings(S_FILE_X_OF_Y) % (self.idx, self.count)
            line2 = strings(S_RETRIEVED_X_OF_Y_MB) % (received / 1048576, size / 1048576)
            d.update(percentage, line1, line2)
            return not d.iscanceled()

    i = Imdb()
    d = xbmcgui.DialogProgress()
    try:
        ds = DownloadState(2)
        d.create(strings(S_DOWNLOADING_IMDB_DATA))
        i.downloadFiles(ds)

        canceled = d.iscanceled()
        d.close()
        del d

        if not canceled:
            xbmcgui.Dialog().ok(strings(S_DOWNLOADING_IMDB_DATA), strings(S_DOWNLOAD_COMPLETE))
    except Exception, ex:
        d.close()
        del d

        xbmcgui.Dialog().ok(strings(S_DOWNLOADING_IMDB_DATA), str(ex))

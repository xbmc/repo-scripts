import re
import random
import os
import urllib2
import zlib

from strings import *

import xbmc
import xbmcgui
import xbmcaddon

class Imdb(object):
    ACTOR_PATTERN = re.compile('^([^\t\(]+)( \([^\)]+\))?\t.*?$')

    QUOTES_LIST = 'quotes.list'
    QUOTES_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz' 
    ACTORS_LIST = 'actors.list'
    ACTORS_URL = 'http://ftp.sunet.se/pub/tv+movies/imdb/actors.list.gz' 

    def __init__(self, listsPath):
        self.path = listsPath

        actorsPath = os.path.join(self.path, self.ACTORS_LIST)
        if os.path.exists(actorsPath):
            f = open(actorsPath)
            self.actorsData = f.read()
            f.close()
        else:
            self.actorsData = None


    def downloadFiles(self, progressCallback = None):
        self._downloadGzipFile(self.QUOTES_URL, self.QUOTES_LIST, progressCallback)
        self._downloadGzipFile(self.ACTORS_URL, self.ACTORS_LIST, progressCallback, self._postprocessActorNames)


    def _postprocessActorNames(self, line):
        m = self.ACTOR_PATTERN.search(line)
        if m is not None:
            lastnameFirstname = m.group(1).strip()
            parts = lastnameFirstname.split(', ', 2)
            if len(parts) == 2:
                firstnameLastname = "%s %s\n" % (parts[1], parts[0])
                return firstnameLastname

        return ''
 

    def _downloadGzipFile(self, url, destination, progressCallback = None, postprocessLineCallback = None):
        """
        Downloads a gzip compressed file and extracts it on the fly.

        Keyword parameters:
        url -- The full url of the gzip file
        destination -- the full path of the destination file
        progressCallback -- a callback function which is invoked periodically with progress information
        """
        response = urllib2.urlopen(url)
        file = open(os.path.join(self.path, destination), 'wb')
        decompressor = zlib.decompressobj(16+zlib.MAX_WBITS)

        partialLine = None
        previousLine = None
        contentReceived = 0
        contentLength = int(response.info()['Content-Length'])
        while True:
            chunk = response.read(8192)
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
                        if processedLine != previousLine and processedLine != '':
                            previousLine = processedLine
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

    def getRandomQuote(self, movie, maxLength = None):
        quotes = self._parseMovieQuotes(movie)
        if quotes is None:
            return None

        quote = None
        retries = 0
        while retries < 10:
            retries += 1
            quote = quotes[random.randint(0, len(quotes)-1)]
            if maxLength is None or len(quote) < maxLength:
                break

        quote = self._filterAndCleanup(quote)

        return quote

    def _filterAndCleanup(self, quote):
        quote = re.sub('\n  ', ' ', quote)
        return quote

    def _parseMovieQuotes(self, movie):
        pattern = '\n# %s [^\n]+\n(.*?)\n\n#' % movie

        path = os.path.join(self.path, self.QUOTES_LIST)
        if os.path.exists(path):
            f = open(path)
            
            #data = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            data = f.read()
            m = re.search(pattern, data, re.DOTALL)
            if m is None:
                return None
            
            quotes = m.group(1).split('\n\n')
            #data.close()
            f.close()
            
            return quotes
        else:
            xbmc.log("%s does not exists, has it been downloaded yet?" % self.QUOTES_LIST)
            return None

    def isActor(self, name):
        if self.actorsData is not None:
            m = re.search('^%s$' % name, self.actorsData, re.MULTILINE)
            return m is not None
        else:
            # if we don't have data all actors are Female
            return False


if __name__ == '__main__':
    # this script is invoked from addon settings

    def progress(received, size, percentage):
        line1 = strings(S_RETRIEVED_X_OF_Y_MB) % (received / 1048576, size / 1048576)
        d.update(percentage, line1)
        return not d.iscanceled()


    addon = xbmcaddon.Addon(id = 'script.moviequiz')
    path = xbmc.translatePath(addon.getAddonInfo('profile'))
    if not os.path.exists(path):
        os.mkdir(path)
    i = Imdb(path)

    try:
        d = xbmcgui.DialogProgress()
        d.create(strings(S_DOWNLOADING_IMDB_DATA))
        i.downloadFiles(progress)
    finally:
        d.close()
        del d

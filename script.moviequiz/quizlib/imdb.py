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
    QUOTES_LIST = 'quotes.list'
    FILES = [
        {'name' : QUOTES_LIST, 'url' : 'http://ftp.sunet.se/pub/tv+movies/imdb/quotes.list.gz'}
    ]

    def __init__(self, listsPath):
        self.path = listsPath

    def downloadFiles(self, progressCallback):
        for file in self.FILES:
            self._downloadGzipFile(file['url'], file['name'], progressCallback)
        

    def _downloadGzipFile(self, url, destination, progressCallback):
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

        contentReceived = 0
        contentLength = int(response.info()['Content-Length'])
        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            contentReceived += len(chunk)
            decompressedChunk = decompressor.decompress(chunk)
            file.write(decompressedChunk)

            percentage = int(contentReceived * 100 / contentLength)
            if not progressCallback(contentReceived, contentLength, percentage):
                break

        file.close()
        response.close()

    def getRandomQuote(self, movie, obfuscate = True):
        quotes = self._parseMovieQuotes(movie)
        if quotes is None:
            return None

        quote = quotes[random.randint(0, len(quotes)-1)]
        quote = self._filterAndCleanup(quote)
        if obfuscate:
            quote = self.obfuscateQuote(quote)

        return quote

    def obfuscateQuote(self, quote):
        names = list()
        for m in re.finditer('(.*?\:)', quote):
            name = m.group(1)
            if not name in names:
                names.append(name)

        print names
        for idx, name in enumerate(names):
            repl = '#%d:' % (idx + 1)
            quote = quote.replace(name, repl)

        print "Quote: %s" % quote

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

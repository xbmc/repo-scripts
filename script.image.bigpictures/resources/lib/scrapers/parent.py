import urllib2
import os
import sys
import time
import re
from zlib import crc32

scriptname = sys.modules['__main__'].__scriptname__
cachedir = sys.modules['__main__'].__cachedir__


class ScraperParent:

    NAME = str()

    def getCachedURL(self, url, referer=None):
        print '[SCRIPT][%s] attempting to open %s' % (scriptname, url)
        ua = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:2.0) ' \
             'Gecko/20100101 Firefox/4.0'
        headers = [('User-Agent', ua)]
        if referer:
            headers.append(('Referer', referer))
        filename = str(crc32(url))
        cachefilefullpath = cachedir + filename
        timetolive = 3600
        if (not os.path.isdir(cachedir)):
            os.makedirs(cachedir)
        try:
            cachefiledate = os.path.getmtime(cachefilefullpath)
        except:
            cachefiledate = 0
        if (time.time() - (timetolive)) > cachefiledate:
            try:
                print '[SCRIPT][%s] %s retrieved from web' % (scriptname, url)
                opener = urllib2.build_opener()
                opener.addheaders = headers
                sock = opener.open(url)
                link = sock.read()
                outfile = open(cachefilefullpath, 'w')
                outfile.write(link)
                outfile.close()
            except urllib2.HTTPError, error:
                print '[SCRIPT][%s] error opening %s' % (scriptname, url)
                print error.msg, error.code, error.geturl()
        else:
            print '[SCRIPT][%s] %s retrieved from cache' % (scriptname, url)
            sock = open(cachefilefullpath, 'r')
            link = sock.read()
        sock.close()
        return link

    def cleanHTML(self, s):
        """The 2nd half of this removes HTML tags.
        The 1st half deals with the fact that beautifulsoup sometimes spits
        out a list of NavigableString objects instead of a regular string.
        This only happens when there are HTML elements, so it made sense to
        fix both problems in the same function."""
        tmp = list()
        for ns in s:
            tmp.append(str(ns))
        s = ''.join(tmp)
        s = re.sub('\s+', ' ', s)  # remove extra spaces
        s = re.sub('<.+?>|Image:.+?\r|\r', '', s)  # html, image captions, & NL
        s = s.replace('&#39;', '\'')  # replace html-encoded double-quotes
        s = s.replace('&#8217;', '\'')  # replace html-encoded single-quotes
        s = s.replace('&#8221;', '"')  # replace html-encoded double-quotes
        s = re.sub('# *$', '', s)  # remove hash at the end
        s = s.strip()
        return s

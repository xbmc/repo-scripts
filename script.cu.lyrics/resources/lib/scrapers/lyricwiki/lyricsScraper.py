#-*- coding: UTF-8 -*-
import sys, re, urllib2, socket, HTMLParser
import xbmc, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
from utilities import *

__language__ = sys.modules[ "__main__" ].__language__
__title__ = __language__(30008)
__service__ = 'lyricwiki'

LIC_TXT = 'we are not licensed to display the full lyrics for this song at the moment'

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__( self ):
        self.url = 'http://lyrics.wikia.com/api.php?artist=%s&song=%s&fmt=realjson'

    def get_lyrics_thread(self, song):
        log( "%s: searching lyrics for %s" % (__service__, song))
        log( "%s: search api url: %s" % (__service__, self.url))
        l = Lyrics()
        l.song = song
        req = urllib2.urlopen(self.url % (urllib2.quote(song.artist), urllib2.quote(song.title)))
        response = req.read()
        req.close()
        data = simplejson.loads(response)
        try:
            self.page = data['url']
        except:
            return None, __language__(30002) % (song.title, song.artist), __service__
        if not self.page.endswith('action=edit'):
            log( "%s: search url: %s" % (__service__, self.page))
            req = urllib2.urlopen(self.page)
            response = req.read()
            req.close()
            matchcode = re.search('lyricbox.*?div>(.*?)<!--', response)
            try:
                lyricscode = (matchcode.group(1))
                htmlparser = HTMLParser.HTMLParser()
                lyricstext = htmlparser.unescape(lyricscode).replace('<br />', '\n')
                l.lyrics = re.sub('<[^<]+?>', '', lyricstext)
                if LIC_TXT in l.lyrics:
                    return __language__(30002) % (song.title, song.artist), __service__
                l.source = __title__
                return l, None, __service__
            except:
                return None, __language__(30004) % __title__, __service__
        else:
            return None, __language__(30002) % (song.title, song.artist), __service__

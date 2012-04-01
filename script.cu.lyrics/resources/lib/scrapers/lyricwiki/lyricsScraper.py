import sys, re, urllib2, socket, HTMLParser
import xbmc, xbmcaddon
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson
import lyrics

__language__ = sys.modules[ "__main__" ].__language__
__title__ = __language__(30008)
__allow_exceptions__ = True

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__( self ):
        self.url = 'http://lyrics.wikia.com/api.php?artist=%s&song=%s&fmt=realjson'

    def get_lyrics_start(self, *args):
        lyricThread = threading.Thread(target=self.get_lyrics_thread, args=args)
        lyricThread.setDaemon(True)
        lyricThread.start()

    def get_lyrics_thread(self, song):
        xbmc.log(msg='SCRAPER-DEBUG-Lyricwiki: LyricsFetcher.get_lyrics_thread %s' % (song), level=xbmc.LOGDEBUG)
        l = lyrics.Lyrics()
        l.song = song
        req = urllib2.urlopen(self.url % (urllib2.quote(song.artist), urllib2.quote(song.title)))
        response = req.read()
        req.close()
        data = simplejson.loads(response)
        self.page = data['url']
        if not self.page.endswith('action=edit'):
            req = urllib2.urlopen(self.page)
            response = req.read()
            req.close()
            matchcode = re.search('lyricbox.*?div>(.*?)<!--', response)
            try:
                lyricscode = (matchcode.group(1))
                htmlparser = HTMLParser.HTMLParser()
                l.lyrics = htmlparser.unescape(lyricscode).replace('<br />', '\n')
                l.source = __title__
                return l, None
            except:
                return None, __language__(30004) % __title__
        else:
            return None, __language__(30002) % (song.title, song.artist)

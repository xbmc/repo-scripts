#-*- coding: UTF-8 -*-
'''
Scraper for http://www.viewlyrics.com

PedroHLC
'''

import urllib
import urllib2
import socket
import re
import hashlib
import difflib
import chardet
from utilities import *

__title__ = 'MiniLyrics'
__priority__ = '100'
__lrc__ = True

socket.setdefaulttimeout(10)


class MiniLyrics(object):
    '''
    Minilyrics specific functions
    '''
    @staticmethod
    def vl_enc(data, md5_extra):
        datalen = len(data)
        md5 = hashlib.md5()
        md5.update(data + md5_extra)
        hexx = md5.hexdigest()
        hasheddata = ''
        i = 0
        while (i < (len(hexx) - 1)):
            hasheddata += chr(int(hexx[i] + hexx[i + 1], 16))
            i += 2
        j = 0
        i = 0
        while (i < datalen):
            try:
                j += data[i]
            except TypeError:
                j += ord(data[i])
            i += 1
        magickey = chr(int(round(float(j) / float(datalen))))
        encddata = list(range(len(data)))
        if isinstance(magickey, int):
            pass
        else:
            magickey = ord(magickey)
        for i in range(datalen):
            if isinstance(data[i], int):
                encddata[i] = data[i] ^ magickey
            else:
                encddata[i] = ord(data[i]) ^ magickey
        try:
            result = '\x02' + chr(magickey) + '\x04\x00\x00\x00' + str(hasheddata) + bytearray(encddata).decode('utf-8')
        except UnicodeDecodeError:
            result = '\x02' + chr(magickey) + '\x04\x00\x00\x00' + str(hasheddata) + bytearray(encddata)
        return result

    @staticmethod
    def vl_dec(data):
        magickey = data[1]
        result = ''
        i = 22
        datalen = len(data)
        if isinstance(magickey, int):
            pass
        else:
            magickey = ord(magickey)
        for i in range(22, datalen):
            if isinstance(data[i], int):
                result += chr(data[i] ^ magickey)
            else:
                result += chr(ord(data[i]) ^ magickey)
        return result

class LyricsFetcher:
    def __init__(self):
        self.proxy = None

    def htmlDecode(self,string):
        entities = {'&apos;':'\'','&quot;':'"','&gt;':'>','&lt;':'<','&amp;':'&'}
        for i in entities:
            string = string.replace(i,entities[i])
        return string

    def get_lyrics(self, song):
        log('%s: searching lyrics for %s - %s' % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        search_url = 'http://search.crintsoft.com/searchlyrics.htm'
        search_query_base = u"<?xml version='1.0' encoding='utf-8' standalone='yes' ?><searchV1 client=\"ViewLyricsOpenSearcher\" artist=\"{artist}\" title=\"{title}\" OnlyMatched=\"1\" />"
        search_useragent = 'MiniLyrics'
        search_md5watermark = b'Mlv1clt4.0'
        search_encquery = MiniLyrics.vl_enc(search_query_base.format(artist=song.artist.decode('utf-8'), title=song.title.decode('utf-8')).encode('utf-8'), search_md5watermark)
        headers = {"User-Agent": "{ua}".format(ua=search_useragent),
                   "Content-Length": "{content_length}".format(content_length=len(search_encquery)),
                   "Connection": "Keep-Alive",
                   "Expect": "100-continue",
                   "Content-Type": "application/x-www-form-urlencoded"
                   }
        try:
            request = urllib2.Request(search_url, data=search_encquery, headers=headers)
            response = urllib2.urlopen(request)
            search_result = response.read()
        except:
            return
        rawdata = MiniLyrics.vl_dec(search_result)
        # might be a better way to parse the data 
        lrcdata = rawdata.replace('\x00', '*')
        artistmatch = re.search('artist\*(.*?)\*',lrcdata)
        if not artistmatch:
            return
        titlematch = re.search('title\*(.*?)\*',lrcdata)
        if not titlematch:
            return
        artist = artistmatch.group(1)
        title = titlematch.group(1)
        links = []
        if (difflib.SequenceMatcher(None, song.artist.lower(), artist.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), title.lower()).ratio() > 0.8):
            results = re.findall('[a-z0-9/_]*?\.lrc', lrcdata)
            for item in results:
                links.append((artist + ' - ' + title, item, artist, title))
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        lyr = self.get_lyrics_from_list(links[0])
        if not lyr:
            return None
        lyrics.lyrics = lyr
        return lyrics

    def get_lyrics_from_list(self, link):
        title,url,artist,song = link
        try:
            f = urllib.urlopen('http://search.crintsoft.com/l/' + url)
            lyrics = f.read()
        except:
            return
        enc = chardet.detect(lyrics)
        lyrics = lyrics.decode(enc['encoding'], 'ignore')
        return lyrics

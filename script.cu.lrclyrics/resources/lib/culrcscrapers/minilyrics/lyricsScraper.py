#-*- coding: UTF-8 -*-
"""
Scraper for http://www.viewlyrics.com

taxigps
"""

import urllib
import urllib2
import socket
import re
from hashlib import md5
import chardet
import difflib
from utilities import *

__title__ = "MiniLyrics"
__priority__ = '100'
__lrc__ = True

socket.setdefaulttimeout(10)

class LyricsFetcher:
    def __init__( self ):
        self.proxy = None

    def htmlEncode(self,string):
        chars = {'\'':'&apos;','"':'&quot;','>':'&gt;','<':'&lt;','&':'&amp;'}
        for i in chars:
            string = string.replace(i,chars[i])
        return string

    def htmlDecode(self,string):
        entities = {'&apos;':'\'','&quot;':'"','&gt;':'>','&lt;':'<','&amp;':'&'}
        for i in entities:
            string = string.replace(i,entities[i])
        return string

    def decryptResultXML(self,value):
        magickey = ord(value[1])
        neomagic = ''
        for i in range(20, len(value)):
            neomagic += chr(ord(value[i]) ^ magickey)
        return neomagic

    def miniLyricsParser(self,response):
        text = self.decryptResultXML(response)
        lines = text.splitlines()
        ret = []
        for line in lines:
            if line.strip().startswith("<fileinfo filetype=\"lyrics\" "):
                loc = []
                loc.append(self.htmlDecode(re.search('link=\"([^\"]*)\"',line).group(1)))
                if not loc[0].lower().endswith(".lrc"):
                    continue
                if(re.search('artist=\"([^\"]*)\"',line)):
                    loc.insert(0,self.htmlDecode(re.search('artist=\"([^\"]*)\"',line).group(1)))
                else:
                    loc.insert(0,' ')
                if(re.search('title=\"([^\"]*)\"',line)):
                    loc.insert(1,self.htmlDecode(re.search('title=\"([^\"]*)\"',line).group(1)))
                else:
                    loc.insert(1,' ')
                ret.append(loc)
        return ret

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        xml ="<?xml version=\"1.0\" encoding='utf-8'?>\r\n"
        xml+="<search filetype=\"lyrics\" artist=\"%s\" title=\"%s\" " % (song.artist, song.title)
        xml+="ClientCharEncoding=\"utf-8\"/>\r\n"
        md5hash = md5(xml+"Mlv1clt4.0").digest()
        request = "\x02\x00\x04\x00\x00\x00%s%s" % (md5hash, xml)
        del md5hash,xml
        url = "http://www.viewlyrics.com:1212/searchlyrics.htm"
        #url = "http://search.crintsoft.com/searchlyrics.htm"
        req = urllib2.Request(url,request)
        req.add_header("User-Agent", "MiniLyrics")
        if self.proxy:
            opener = urllib2.build_opener(urllib2.ProxyHandler(self.proxy))
        else:
            opener = urllib2.build_opener()
        try:
            response = opener.open(req).read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None

        lrcList = self.miniLyricsParser(response)
        links = []
        for x in lrcList:
            if (difflib.SequenceMatcher(None, song.artist.lower(), x[0].lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), x[1].lower()).ratio() > 0.8):
                links.append( ( x[0] + ' - ' + x[1], x[2], x[0], x[1] ) )
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
            f = urllib.urlopen(url)
            lyrics = f.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
        enc = chardet.detect(lyrics)
        lyrics = lyrics.decode(enc['encoding'], 'ignore')
        return lyrics

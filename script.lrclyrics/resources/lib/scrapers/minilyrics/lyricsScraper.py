#-*- coding: UTF-8 -*-
"""
Scraper for http://www.viewlyrics.com

taxigps
"""

import urllib
import urllib2
import re
from hashlib import md5
import chardet

__title__ = "MiniLyrics"
__allow_exceptions__ = False

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

    def get_lyrics(self, artist, song):
        xml ="<?xml version=\"1.0\" encoding='utf-8'?>\r\n"
        xml+="<search filetype=\"lyrics\" artist=\"%s\" title=\"%s\" " % (artist, song)
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
            return ""

        lrcList = self.miniLyricsParser(response)
        links = []
        for x in lrcList:
            links.append( ( x[0] + ' - ' + x[1], x[2], x[0], x[1] ) )
        if len(links) == 0:
            return ""
        elif len(links) == 1:
            lyrics = self.get_lyrics_from_list(links[0])
            return lyrics
        else:
            return links

    def get_lyrics_from_list(self, link):
        title,url,artist,song = link
        f = urllib.urlopen(url)
        lyrics = f.read()
        enc = chardet.detect(lyrics)
        if (enc['encoding'] == 'utf-8'):
            return lyrics
        else:
            return unicode( lyrics, enc['encoding'] ).encode( "utf-8")

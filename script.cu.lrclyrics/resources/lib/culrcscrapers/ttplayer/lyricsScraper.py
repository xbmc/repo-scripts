# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
"""
Scraper for http://lrcct2.ttplayer.com/

taxigps
"""

import os
import socket
import urllib
import re
import random
import difflib
from utilities import *

__title__ = "TTPlayer"
__priority__ = '110'
__lrc__ = True

socket.setdefaulttimeout(10)

LYRIC_TITLE_STRIP=["\(live[^\)]*\)", "\(acoustic[^\)]*\)",
                    "\([^\)]*mix\)", "\([^\)]*version\)",
                    "\([^\)]*edit\)", "\(feat[^\)]*\)"]
LYRIC_TITLE_REPLACE=[("/", "-"),(" & ", " and ")]
LYRIC_ARTIST_REPLACE=[("/", "-"),(" & ", " and ")]

class ttpClient(object):
    '''
    privide ttplayer specific function, such as encoding artist and title,
    generate a Id code for server authorizition.
    (see http://ttplyrics.googlecode.com/svn/trunk/crack) 
    '''
    @staticmethod
    def CodeFunc(Id, data):
        '''
        Generate a Id Code
        These code may be ugly coz it is translated
        from C code which is translated from asm code
        grabed by ollydbg from ttp_lrcs.dll.
        (see http://ttplyrics.googlecode.com/svn/trunk/crack) 
        '''
        length = len(data)

        tmp2=0
        tmp3=0

        tmp1 = (Id & 0x0000FF00) >> 8                                                   #右移8位后为x0000015F

            #tmp1 0x0000005F
        if ( (Id & 0x00FF0000) == 0 ):
            tmp3 = 0x000000FF & ~tmp1                                                   #CL 0x000000E7
        else:
            tmp3 = 0x000000FF & ((Id & 0x00FF0000) >> 16)                               #右移16后为x00000001

        tmp3 = tmp3 | ((0x000000FF & Id) << 8)                                          #tmp3 0x00001801
        tmp3 = tmp3 << 8                                                                #tmp3 0x00180100
        tmp3 = tmp3 | (0x000000FF & tmp1)                                               #tmp3 0x0018015F
        tmp3 = tmp3 << 8                                                                #tmp3 0x18015F00
        if ( (Id & 0xFF000000) == 0 ) :
            tmp3 = tmp3 | (0x000000FF & (~Id))                                          #tmp3 0x18015FE7
        else :
            tmp3 = tmp3 | (0x000000FF & (Id >> 24))                                     #右移24位后为0x00000000

        #tmp3   18015FE7
        
        i=length-1
        while(i >= 0):
            char = ord(data[i])
            if char >= 0x80:
                char = char - 0x100
            tmp1 = (char + tmp2) & 0x00000000FFFFFFFF
            tmp2 = (tmp2 << (i%2 + 4)) & 0x00000000FFFFFFFF
            tmp2 = (tmp1 + tmp2) & 0x00000000FFFFFFFF
            #tmp2 = (ord(data[i])) + tmp2 + ((tmp2 << (i%2 + 4)) & 0x00000000FFFFFFFF)
            i -= 1

        #tmp2 88203cc2
        i=0
        tmp1=0
        while(i<=length-1):
            char = ord(data[i])
            if char >= 128:
                char = char - 256
            tmp7 = (char + tmp1) & 0x00000000FFFFFFFF
            tmp1 = (tmp1 << (i%2 + 3)) & 0x00000000FFFFFFFF
            tmp1 = (tmp1 + tmp7) & 0x00000000FFFFFFFF
            #tmp1 = (ord(data[i])) + tmp1 + ((tmp1 << (i%2 + 3)) & 0x00000000FFFFFFFF)
            i += 1

        #EBX 5CC0B3BA

        #EDX = EBX | Id
        #EBX = EBX | tmp3
        tmp1 = (((((tmp2 ^ tmp3) & 0x00000000FFFFFFFF) + (tmp1 | Id)) & 0x00000000FFFFFFFF) * (tmp1 | tmp3)) & 0x00000000FFFFFFFF
        tmp1 = (tmp1 * (tmp2 ^ Id)) & 0x00000000FFFFFFFF

        if tmp1 > 0x80000000:
            tmp1 = tmp1 - 0x100000000
        return tmp1
    
    @staticmethod
    def EncodeArtTit(str):
        rtn = ''
        uni = unicode(str, 'UTF-8')
        str = uni.encode('UTF-16')[2:]
        for i in range(len(str)):
            rtn += '%02x' % ord(str[i])

        return rtn


class LyricsFetcher:
    def __init__( self ):
        self.LIST_URL = 'http://ttlrccnc.qianqian.com/dll/lyricsvr.dll?sh?Artist=%s&Title=%s&Flags=0'
        self.LYRIC_URL = 'http://ttlrccnc.qianqian.com/dll/lyricsvr.dll?dl?Id=%d&Code=%d&uid=01&mac=%012x'

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        artist = song.artist
        title = song.title
        # replace ampersands and the like
        for exp in LYRIC_ARTIST_REPLACE:
                p = re.compile(exp[0])
                artist = p.sub(exp[1], artist)
        for exp in LYRIC_TITLE_REPLACE:
                p = re.compile(exp[0])
                title = p.sub(exp[1], title)

        # strip things like "(live at Somewhere)", "(accoustic)", etc
        for exp in LYRIC_TITLE_STRIP:
            p = re.compile(exp)
            title = p.sub('', title)

        # compress spaces
        title = title.strip().replace('`','').replace('/','')
        artist = artist.strip().replace('`','').replace('/','')

        try:
            url = self.LIST_URL %(ttpClient.EncodeArtTit(artist.replace(' ','').lower()), ttpClient.EncodeArtTit(title.replace(' ','').lower()))
            f = urllib.urlopen(url)
            Page = f.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
        links_query = re.compile('<lrc id=\"(.*?)\" artist=\"(.*?)\" title=\"(.*?)\"></lrc>')
        urls = re.findall(links_query, Page)
        links = []
        for x in urls:
            if (difflib.SequenceMatcher(None, artist.lower(), x[1].lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, title.lower(), x[2].lower()).ratio() > 0.8):
                links.append( ( x[1] + ' - ' + x[2], x[0], x[1], x[2] ) )
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        for link in links:
            lyr = self.get_lyrics_from_list(link)
            if lyr and lyr.startswith('['):
                lyrics.lyrics = lyr
                return lyrics
        return None

    def get_lyrics_from_list(self, link):
        title,Id,artist,song = link
        log('%s %s %s' %(Id, artist, song))
        try:
            url = self.LYRIC_URL %(int(Id),ttpClient.CodeFunc(int(Id), artist + song), random.randint(0,0xFFFFFFFFFFFF))
            f = urllib.urlopen(url)
            Page = f.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                   __title__, self.__class__.__name__,
                   sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                   sys.exc_info()[ 2 ].tb_lineno,
                   sys.exc_info()[ 1 ]
                   ))
            return None
        # ttplayer occasionally returns incorrect lyrics. if we have an 'ar' tag with a value we can check if the artist matches
        if Page.startswith('[ti:'):
            check = Page.split('\n')
            if check[1][0:4] == '[ar:' and not check[1][4:-1] == '':
                if (difflib.SequenceMatcher(None, artist.lower(), check[1][4:-1].lower()).ratio() > 0.8):
                    return Page
            else:
                return Page
        elif Page.startswith('['):
            return Page
        return ''

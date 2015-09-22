# -*- Mode: python; coding: utf-8; tab-width: 8; indent-tabs-mode: t; -*-
"""
Scraper for http://newlyrics.gomtv.com/

edge
"""

import sys
import socket
import hashlib
import urllib
import re
from utilities import *
from audiofile import AudioFile

__title__ = "GomAudio"
__priority__ = '130'
__lrc__ = True

socket.setdefaulttimeout(10)

GOM_URL = "http://newlyrics.gomtv.com/cgi-bin/lyrics.cgi?cmd=find_get_lyrics&file_key=%s&title=%s&artist=%s&from=gomaudio_local"

class gomClient(object):
    '''
    privide Gom specific function, such as key from mp3
    '''
    @staticmethod
    def GetKeyFromFile(file):
        musf = AudioFile()
        musf.Open(file)
        buf = musf.ReadAudioStream(100*1024)	# 100KB from audio data
        musf.Close()
        # calculate hashkey
        m = hashlib.md5(); m.update(buf);
        return m.hexdigest()

    @staticmethod
    def mSecConv(msec):
        s,ms = divmod(msec/10,100)
        m,s = divmod(s,60)
        return m,s,ms

class LyricsFetcher:
    def __init__( self ):
        self.base_url = "http://newlyrics.gomtv.com/"

    def get_lyrics(self, song):
        log( "%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title))
        lyrics = Lyrics()
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__

        key = None
        try:
            ext = os.path.splitext(song.filepath.decode("utf-8"))[1].lower()
            sup_ext = ['.mp3', '.ogg', '.wma', '.flac', '.ape', '.wav']
            if ext in sup_ext:
                key = gomClient.GetKeyFromFile( song.filepath )
            if not key:
                return None
            url = GOM_URL %(key, urllib.quote(song.title.decode("utf-8").encode("euc-kr")), urllib.quote(song.artist.decode("utf-8").encode("euc-kr")))
            response = urllib.urlopen( url )
            Page = response.read()
        except:
            log( "%s: %s::%s (%d) [%s]" % (
                    __title__, self.__class__.__name__,
                    sys.exc_info()[ 2 ].tb_frame.f_code.co_name,
                    sys.exc_info()[ 2 ].tb_lineno,
                    sys.exc_info()[ 1 ]
                ))
            return None

        if Page[:Page.find('>')+1] != '<lyrics_reply result="0">':
            return None
        syncs = re.compile('<sync start="(\d+)">([^<]*)</sync>').findall(Page)
        lyrline = []
        lyrline.append( "[ti:%s]" %song.title )
        lyrline.append( "[ar:%s]" %song.artist )
        for sync in syncs:
            # timeformat conversion
            t = "%02d:%02d.%02d" % gomClient.mSecConv( int(sync[0]) )
            # unescape string
            try:
                s = unicode(sync[1], "euc-kr").encode("utf-8").replace("&apos;","'").replace("&quot;",'"')
                lyrline.append( "[%s]%s" %(t,s) )
            except:
                pass
        lyrics.lyrics = '\n'.join( lyrline )
        return lyrics

import os
import re
import chardet
from mutagen_culrc.flac import FLAC
from mutagen_culrc.mp3 import MP3
from mutagen_culrc.mp4 import MP4
import xbmcvfs
from utilities import *

LANGUAGE  = sys.modules[ "__main__" ].LANGUAGE

def getEmbedLyrics(song, getlrc):
    lyrics = Lyrics()
    lyrics.song = song
    lyrics.source = LANGUAGE( 32002 )
    lyrics.lrc = getlrc
    filename = song.filepath.decode("utf-8")
    ext = os.path.splitext(filename)[1].lower()
    lry = None
    if ext == '.mp3':
        lry = getID3Lyrics(filename, getlrc)
        if not lry:
            try:
                text = getLyrics3(filename, getlrc)
                enc = chardet.detect(text)
                lry = text.decode(enc['encoding'])
            except:
                pass
    elif  ext == '.flac':
        lry = getFlacLyrics(filename, getlrc)
    elif  ext == '.m4a':
        lry = getMP4Lyrics(filename, getlrc)
    if not lry:
        return None
    lyrics.lyrics = lry
    return lyrics

"""
Get lyrics embed with Lyrics3/Lyrics3V2 format
See: http://id3.org/Lyrics3
     http://id3.org/Lyrics3v2
"""
def getLyrics3(filename, getlrc):
    f = xbmcvfs.File(filename)
    f.seek(-128-9, os.SEEK_END)
    buf = f.read(9)
    if (buf != "LYRICS200" and buf != "LYRICSEND"):
        f.seek(-9, os.SEEK_END)
        buf = f.read(9)
    if (buf == "LYRICSEND"):
        """ Find Lyrics3v1 """
        f.seek(-5100-9-11, os.SEEK_CUR)
        buf = f.read(5100+11)
        f.close();
        start = buf.find("LYRICSBEGIN")
        content = buf[start+11:]
        if (getlrc and isLRC(content)) or (not getlrc and not isLRC(content)):
            return content
    elif (buf == "LYRICS200"):
        """ Find Lyrics3v2 """
        f.seek(-9-6, os.SEEK_CUR)
        size = int(f.read(6))
        f.seek(-size-6, os.SEEK_CUR)
        buf = f.read(11)
        if(buf == "LYRICSBEGIN"):
            buf = f.read(size-11)
            tags=[]
            while buf!= '':
                tag = buf[:3]
                length = int(buf[3:8])
                content = buf[8:8+length]
                if (tag == 'LYR'):
                    if (getlrc and isLRC(content)) or (not getlrc and not isLRC(content)):
                        return content
                buf = buf[8+length:]
    f.close();
    return None

def ms2timestamp(ms):
    mins = "0%s" % int(ms/1000/60)
    sec = "0%s" % int((ms/1000)%60)
    msec = "0%s" % int((ms%1000)/10)
    timestamp = "[%s:%s.%s]" % (mins[-2:],sec[-2:],msec[-2:])
    return timestamp

"""
Get USLT/SYLT/TXXX lyrics embed with ID3v2 format
See: http://id3.org/id3v2.3.0
"""
def getID3Lyrics(filename, getlrc):
    codecs = ['latin_1', 'utf-16', 'utf16-be', 'utf-8']
    try:
        data = MP3(filename)
        for tag,value in data.iteritems():
            if getlrc and tag.startswith('SYLT'):
                lyr = ''
                text = data[tag].text
                for line in text:
                    txt = line[0].encode("utf-8").strip()
                    stamp = ms2timestamp(line[1])
                    lyr += "%s%s\r\n" % (stamp, txt)
                return lyr
            if not getlrc and (tag.startswith('USLT') or tag.startswith('TXXX')):
                if tag.startswith('USLT'):
                    text = data[tag].text
                elif tag.lower().endswith('lyrics'): # TXXX tags contain arbitrary info. only accept 'TXXX:lyrics'
                    text = data[tag].text[0]
                lyr = text.encode("utf-8")
                return lyr
    except:
        return None

def getFlacLyrics(filename, getlrc):
    try:
        tags = FLAC(filename)
        if tags.has_key('lyrics'):
            lyr = tags['lyrics'][0]
            match = re.compile('\[(\d+):(\d\d)(\.\d+|)\]').search(lyr)
            if (getlrc and match) or ((not getlrc) and (not match)):
                return lyr
    except:
        return None

def getMP4Lyrics(filename, getlrc):
    try:
        tags = MP4(filename)
        if tags.has_key('\xa9lyr'):
            lyr = tags['\xa9lyr'][0]
            match = re.compile('\[(\d+):(\d\d)(\.\d+|)\]').search(lyr)
            if (getlrc and match) or ((not getlrc) and (not match)):
                return lyr
    except:
        return None

def isLRC(lyr):
    match = re.compile('\[(\d+):(\d\d)(\.\d+|)\]').search(lyr)
    if match:
        return True
    else:
        return False

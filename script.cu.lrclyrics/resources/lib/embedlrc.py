import os
import re
import chardet
from tagger import *
from mutagen.flac import FLAC
import xbmcvfs
from utilities import *

__language__  = sys.modules[ "__main__" ].__language__

def getEmbedLyrics(song, getlrc):
    lyrics = Lyrics()
    lyrics.song = song
    lyrics.source = __language__( 32002 )
    lyrics.lrc = getlrc
    filename = song.filepath.decode("utf-8")
    lry = None
    if getlrc:
        try:
            lry = getLyrics3(filename)
        except:
            pass
    if lry:
        enc = chardet.detect(lry)
        lyrics.lyrics = lry.decode(enc['encoding'])
    else:
        lry = getID3Lyrics(filename, getlrc)
        if not lry:
            lry = getFlacLyrics(filename, getlrc)
            if not lry:
                return None
        lyrics.lyrics = lry
    return lyrics

"""
Get LRC lyrics embed with Lyrics3/Lyrics3V2 format
See: http://id3.org/Lyrics3
     http://id3.org/Lyrics3v2
"""
def getLyrics3(filename):
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
        return buf[start+11:]
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
                    return content
                buf = buf[8+length:]
    f.close();
    return None

def endOfString(string, utf16=False):
    if (utf16):
        pos = 0
        while True:
            pos += string[pos:].find('\x00\x00') + 1
            if (pos % 2 == 1):
                return pos - 1
    else:
        return string.find('\x00')

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
    id3 = ID3v2(filename)
    if id3.version == 2.2:
        sylt = "SLT"
        uslt = "ULT"
        txxx = "TXX"
    else:
        sylt = "SYLT"
        uslt = "USLT"
        txxx = "TXXX"
    for tag in id3.frames:
        if getlrc and tag.fid == sylt:
            enc = ['latin_1','utf_16','utf_16_be','utf_8'][ord(tag.rawdata[0])]
            lang = tag.rawdata[1:4]
            format = tag.rawdata[4]
            ctype = tag.rawdata[5]
            raw = tag.rawdata[6:]
            utf16 = bool(enc.find('16') != -1)
            pos = endOfString(raw, utf16)
            desc = raw[:pos]
            if utf16:
                pos += 1
            content = raw[pos+1:]
            del raw
            lyrics = ""
            while content != "":
                pos = endOfString(content, utf16)
                if (enc == 'latin_1'):
                    enc = chardet.detect(content[:pos])['encoding']
                text = content[:pos].decode(enc)
                if utf16:
                    pos += 1
                time = content[pos+1:pos+5]
                timems = 0
                for x in range(4):
                    timems += (256)**(3-x) * ord(time[x])
                lyrics += "%s%s\r\n" % (ms2timestamp(timems), text.replace('\n','').replace('\r','').strip())
                content = content[pos+5:]
            return lyrics
        elif tag.fid == txxx:
            """
            Frame data in rawdata[]:
            Text encoding     $xx
            Description       <textstring> $00 (00)
            Value         <textstring>
            """
            enc = ['latin_1','utf_16','utf_16_be','utf_8'][ord(tag.rawdata[0])]
            raw = tag.rawdata[1:]
            utf16 = bool(enc.find('16') != -1)
            pos = endOfString(raw, utf16)
            desc = raw[:pos].decode(enc)
            if utf16:
                pos += 1
            if (len(desc) == 6 and desc.lower() == "lyrics"):
                lyrics = raw[pos+1:]
                if (enc == 'latin_1'):
                    enc = chardet.detect(lyrics)['encoding']
                lyr = lyrics.decode(enc)
                match1 = re.compile('\[(\d+):(\d\d)(\.\d+|)\]').search(lyr)
                if (getlrc and match1) or ((not getlrc) and (not match1)):
                    return lyr
        elif (not getlrc) and tag.fid == uslt:
            """
            Frame data in rawdata[]:
            Text encoding        $xx
            Language             $xx xx xx
            Content descriptor   <textstring> $00 (00)
            Lyrics/text          <textstring>
            """
            enc = ['latin_1','utf_16','utf_16_be','utf_8'][ord(tag.rawdata[0])]
            lang = tag.rawdata[1:4]
            raw = tag.rawdata[4:]
            utf16 = bool(enc.find('16') != -1)
            pos = endOfString(raw, utf16)
            desc = raw[:pos]
            if utf16:
                pos += 1
            lyrics = raw[pos+1:]
            if (enc == 'latin_1'):
                enc = chardet.detect(lyrics)['encoding']
            return lyrics.decode(enc)
    return None

def getFlacLyrics(filename, getlrc):
    try:
        tags = FLAC(filename)
        if tags.has_key('lyrics'):
            lyr = tags['lyrics'][0]
            match1 = re.compile('\[(\d+):(\d\d)(\.\d+|)\]').search(lyr)
            if (getlrc and match1) or ((not getlrc) and (not match1)):
                return lyr
    except:
        return None

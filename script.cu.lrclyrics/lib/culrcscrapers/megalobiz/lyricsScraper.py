#-*- coding: UTF-8 -*-
'''
Scraper for https://www.megalobiz.com/

megalobiz

https://github.com/rtcq/syncedlyrics
'''

import json
import requests
import difflib
from lib.utils import *

__title__ = "Megalobiz"
__priority__ = '140'
__lrc__ = True

def convert_ms(ms):
    minutes = (ms // 1000) // 60
    seconds = (ms // 1000) % 60
    milliseconds = ms % 1000 // 10
    return f"[{minutes:02d}:{seconds:02d}:{milliseconds:02d}]"

class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.SEARCH_URL = 'https://api.megalobiz.com/api/v1/lrcs?page=1&pageSize=20&search=%s %s'
        self.LYRIC_URL = 'https://www.megalobiz.com/%s'
        self.TOKEN_URL = 'https://megalobiz.com/_next/static/chunks/43f5jbj-3-o1o.js'

    def get_lyrics(self, song):
        lastsearchfile = os.path.join(PROFILE, 'megalobiz_lastsearch')
        if xbmcvfs.exists(lastsearchfile):
            os.remove(lastsearchfile)
        log("%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        # get the token file. not sure if the .js url changes over time, in case it changes, get it from the header of the main page
        try:
            url = self.SEARCH_URL % (song.artist, song.title)
            response = requests.get(self.TOKEN_URL, timeout=10)
            result = response.text
        except:
            return None
        matchcode = re.search('",r="(.*?)"', result, flags=re.DOTALL)
        if matchcode:
            tokencode = (matchcode.group(1))
            token = 'Bearer %s' % tokencode
        else:
            return None
        headers = {"Authorization": token}
        # get the lyrics list
        try:
            url = self.SEARCH_URL % (song.artist, song.title)
            response = requests.get(url, headers=headers, timeout=10)
            result = response.json()
        except:
            return None
        links = []
        validlyrics = {'results': []}
        link = 0
        for item in result["models"]:
            try:
                artistname = item['title'].split('-')[0].strip()
                songtitle = item['title'].split('-')[1].strip()
            except:
                continue
            #quick check if the lyrics are valid
            validlines = False
            for line in item['content']['lines']:
                if 'time' not in line: # skip partially synchronized lyrics
                    break
                elif line['time'] == 0:  # either the song has no timestamps, or has only 1 line of text starting at 0 (false possitive, too bad)
                    continue
                elif line['time'] == 0 and line['text'].startswith('('): # skip lines like (verse) or (chorus) which have no timestamp attached to them
                    continue
                validlines = True
            if validlines:
                if (difflib.SequenceMatcher(None, song.artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, song.title.lower(), songtitle.lower()).ratio() > 0.8):
                    links.append((artistname + ' - ' + songtitle, link, artistname, songtitle))
                    validlyrics['results'].append(item)
                    link += 1
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        # save the valid lyricsdata
        lastsearchfile = os.path.join(PROFILE, 'megalobiz_lastsearch')
        lastsearch = xbmcvfs.File(lastsearchfile, 'w')
        json.dump(validlyrics, lastsearch)
        lastsearch.close()
        # get the lyrics
        lyricdata = validlyrics['results'][0]
        lyr = ''
        for item in lyricdata['content']['lines']:
            if item['time'] == 0 and item['text'].startswith('('):
                continue
            else:
                linetime =  item['time']
                linetext = item['text']
                timestamp = convert_ms(linetime)
                lyr = lyr + timestamp + ' ' + linetext + '\n'
        lyrics.lyrics = lyr
        return lyrics

    def get_lyrics_from_list(self, link):
        lastsearchfile = os.path.join(PROFILE, 'megalobiz_lastsearch')
        if xbmcvfs.exists(lastsearchfile):
            lastsearch = xbmcvfs.File(lastsearchfile)
            lastsearchdata = json.load(lastsearch)
            lastsearch.close()
        else:
            return None
        title,num,artist,song = link
        lyr = ''
        for item in lastsearchdata['results'][num]['content']['lines']:
            if item['time'] == 0 and item['text'].startswith('('):
                continue
            else:
                linetime =  item['time']
                linetext = item['text']
                timestamp = convert_ms(linetime)
                lyr = lyr + timestamp + ' ' + linetext + '\n'
        return lyr

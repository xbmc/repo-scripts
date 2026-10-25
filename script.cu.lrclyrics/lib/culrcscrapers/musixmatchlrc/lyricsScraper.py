#-*- coding: UTF-8 -*-

'''
Scraper for https://www.musixmatch.com/

musixmatchlrc

https://github.com/spicetify/cli/blob/main/CustomApps/lyrics-plus/ProviderMusixmatch.js
https://github.com/rtcq/syncedlyrics (unmaintained)
'''

import requests
import json
import time
import difflib
import urllib
import xbmcvfs
from lib.utils import *

__title__ = "musixmatchlrc"
__priority__ = '100'
__lrc__ = True


class LyricsFetcher:
    def __init__(self, *args, **kwargs):
        self.DEBUG = kwargs['debug']
        self.settings = kwargs['settings']
        self.SEARCH_URL = 'https://apic-desktop.musixmatch.com/ws/1.1/%s'
        self.TOKEN_URL = 'https://apic-appmobile.musixmatch.com/ws/1.1/token.get?app_id=mac-ios-v2.0'
        self.current_time = int(time.time())
        self.headers = {"Host": "apic-appmobile.musixmatch.com", "authority": "apic-appmobile.musixmatch.com", "X-Cookie": "x-mxm-token-guid=", "x-mxm-app-version": "10.1.1", "X-User-Agent": "Musixmatch/2025120901 CFNetwork/3860.300.31 Darwin/25.2.0", "Accept-Language": "en-US,en;q=0.9", "Connection": "keep-alive", "Accept": "application/json"}

    def get_token(self):
        self.token = ''
        tokenpath = os.path.join(PROFILE, 'musixmatchlrc_token')
        if xbmcvfs.exists(tokenpath):
            tokenfile = xbmcvfs.File(tokenpath)
            tokendata = json.load(tokenfile)
            tokenfile.close()
            cached_token = tokendata.get("token")
            expiration_time = tokendata.get("expiration_time")
            if cached_token and expiration_time and self.current_time < expiration_time:
                self.token = cached_token
            else:
                os.remove(tokenpath)
        if not self.token:
            try:
                response = requests.get(self.TOKEN_URL, headers=self.headers, timeout=10)
                result = response.json()
            except:
                return None
            if 'message' in result and 'body' in result["message"] and 'user_token' in result["message"]["body"]:
                self.token = result["message"]["body"]["user_token"]
                expiration_time = self.current_time + 86400 # tokens should not expire, but just to be safe, use 1 day
                tokendata = {}
                tokendata['token'] = self.token
                tokendata['expiration_time'] = expiration_time
                tokenfile = xbmcvfs.File(tokenpath, 'w')
                json.dump(tokendata, tokenfile)
                tokenfile.close()
        return self.token

    def get_lyrics(self, song):
        self.token = self.get_token()
        if not self.token:
            return
        log("%s: searching lyrics for %s - %s" % (__title__, song.artist, song.title), debug=self.DEBUG)
        lyrics = Lyrics(settings=self.settings)
        lyrics.song = song
        lyrics.source = __title__
        lyrics.lrc = __lrc__
        artist = song.artist.replace(' ', '+')
        title = song.title.replace(' ', '+')
        base_url = ("https://apic-appmobile.musixmatch.com/ws/1.1/macro.subtitles.get?format=json&namespace=lyrics_richsynched&app_id=mac-ios-v2.0&")
        params = {"q_artist": song.artist, "q_artists": song.artist, "q_track": song.title, "usertoken": self.token}
        url = base_url + urllib.parse.urlencode(params)
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            result = response.json()
        except:
            return None
        links = []
        try:
            songtitle = result['message']['body']['macro_calls']['matcher.track.get']['message']['body']['track']['track_name']
            artistname = result['message']['body']['macro_calls']['matcher.track.get']['message']['body']['track']['artist_name']
            if (difflib.SequenceMatcher(None, artist.lower(), artistname.lower()).ratio() > 0.8) and (difflib.SequenceMatcher(None, title.lower(), songtitle.lower()).ratio() > 0.8):
                pass
            else:
                return None
            for item in result['message']['body']['macro_calls']['track.subtitles.get']['message']['body']['subtitle_list']:
                 validlyrics = item['subtitle']['subtitle_body']
                 links.append((artistname + ' - ' + songtitle, validlyrics, artistname, songtitle))
        except:
            return None
        if len(links) == 0:
            return None
        elif len(links) > 1:
            lyrics.list = links
        for link in links:
            lyr = self.get_lyrics_from_list(link)
            if lyr:
                lyrics.lyrics = lyr
                return lyrics
        return None

    def get_lyrics_from_list(self, link):
        title,lyr,artist,song = link
        return lyr

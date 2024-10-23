from collections import OrderedDict
import json
from pathlib import Path
import re
import time

import requests
import xbmcaddon


NOWPLAYING_URL = 'https://api.radioparadise.com/api/nowplaying_list_v2022?chan={}&list_num=10'
COVER_URL = 'https://img.radioparadise.com/{}'
SLIDESHOW_URL = 'https://img.radioparadise.com/slideshow/720/{}.jpg'

BREAK_COVER_URL = 'https://img.radioparadise.com/covers/l/101.jpg'
BREAK_SONG = ('Commercial-free', 'Listener-supported')

KEY_FILTER_RE = re.compile(r'[^\w\']+')

# Number of songs to cache
MAX_SONGS = 30
# Number of seconds to wait for API responses
UPDATE_TIMEOUT = 3
# Number of seconds to wait before retrying API updates
UPDATE_WAIT = 5

# List of channel objects from channels.json
CHANNELS = None
# Map of stream URL to channel object
CHANNEL_INFO = None


class NowPlaying():
    """Provides song information from the "nowplaying" API."""

    def __init__(self):
        """Constructor"""
        self.songs = OrderedDict()
        self.set_channel(None)

    def get_song_data(self, song_key):
        """Return a dict for the build_key()-created key, or None.

        The "cover" value will be an absolute URL.
        """
        return self.songs.get(song_key)

    def get_next_song(self, song_key):
        """Return a dict for song_key's successor, or None.

        The "cover" value will be an absolute URL.
        """
        next_key = self.songs.get(song_key, {}).get('next_key')
        return self.songs.get(next_key)

    def set_channel(self, channel_id):
        """Set the RP channel ID, or None."""
        if channel_id is not None:
            self.url = NOWPLAYING_URL.format(channel_id)
        else:
            self.url = None
        self.current = None
        self.next_update = 0
        self.songs.clear()

    def update(self):
        """Update song information from the API, if necessary.

        Calls the API only when the "current" song ends.

        Raises an exception on error responses or timeouts.
        """
        if self.url is None:
            return
        if time.time() < self.next_update:
            return

        try:
            res = requests.get(self.url, timeout=UPDATE_TIMEOUT)
            res.raise_for_status()
        except Exception:
            self.next_update = time.time() + UPDATE_WAIT
            raise

        next_key = None
        data = res.json()
        for index, song in enumerate(data['song']):
            if song['artist'] is None:
                song['artist'] = 'Unknown Artist'
            if song['title'] is None:
                song['title'] = 'Unknown Title'
            song['cover'] = COVER_URL.format(song['cover'])
            slides = song.get('slideshow', '').split(',')
            slides = [SLIDESHOW_URL.format(s) for s in slides if s]
            song['slide_urls'] = slides
            song['next_key'] = next_key
            key = build_key((song['artist'], song['title']))
            self.songs[key] = song
            next_key = key
            if index == 0:
                self.current = song
        if (break_key := build_key(BREAK_SONG)) not in self.songs:
            self.songs[break_key] = {
                'artist': BREAK_SONG[0],
                'title': BREAK_SONG[1],
                'cover': BREAK_COVER_URL,
                'duration': '30000',
            }

        now = time.time()
        next_update = (self.current['play_time'] + int(self.current['duration'])) / 1000
        if next_update > now:
            self.next_update = next_update
        else:
            self.next_update = now + UPDATE_WAIT

        while len(self.songs) > MAX_SONGS:
            self.songs.popitem(last=False)


def build_key(strings):
    """Return a normalized tuple of words in the strings."""
    result = []
    for s in strings:
        words = KEY_FILTER_RE.sub(' ', s).casefold().split()
        result.extend(words)
    return tuple(sorted(result))


def init():
    global CHANNELS, CHANNEL_INFO
    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')
    channels_json = Path(addon_path, 'resources', 'channels.json')
    CHANNELS = json.loads(channels_json.read_text())
    CHANNEL_INFO = {s['url_aac']: s for s in CHANNELS}
    CHANNEL_INFO.update({s['url_flac']: s for s in CHANNELS})


init()

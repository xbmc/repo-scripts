from collections import OrderedDict
import re
import time

import requests


NOWPLAYING_URL = 'https://api.radioparadise.com/api/nowplaying_list?chan={}'
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

STREAMS = [
    {
        'channel': 0,
        'title': 'RP Main Mix',
        'url_aac': 'http://stream.radioparadise.com/aac-128',
        'url_flac': 'http://stream.radioparadise.com/flacm',
    },
    {
        'channel': 1,
        'title': 'RP Mellow Mix',
        'url_aac': 'http://stream.radioparadise.com/mellow-128',
        'url_flac': 'http://stream.radioparadise.com/mellow-flacm',
    },
    {
        'channel': 2,
        'title': 'RP Rock Mix',
        'url_aac': 'http://stream.radioparadise.com/rock-128',
        'url_flac': 'http://stream.radioparadise.com/rock-flacm',
    },
    {
        'channel': 3,
        'title': 'RP Global Mix',
        'url_aac': 'http://stream.radioparadise.com/global-128',
        'url_flac': 'http://stream.radioparadise.com/global-flacm',
    },
]
STREAM_INFO = {s['url_aac']: s for s in STREAMS}
STREAM_INFO.update({s['url_flac']: s for s in STREAMS})


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

    def set_channel(self, channel):
        """Set the RP channel number, or None."""
        if channel is not None:
            self.url = NOWPLAYING_URL.format(channel)
        else:
            self.url = None
        self.current = None
        self.next_update = 0
        self.songs.clear()

    def update(self):
        """Update song information from the API, if necessary.

        Calls the API only if the "refresh" timer has expired.

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
        song_items = sorted(list(data['song'].items()), key=lambda s: int(s[0]))
        for index, song in song_items:
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
            if index == '0':
                self.current = song
        if (break_key := build_key(BREAK_SONG)) not in self.songs:
            self.songs[break_key] = {
                'artist': BREAK_SONG[0],
                'title': BREAK_SONG[1],
                'cover': BREAK_COVER_URL,
                'duration': '30000',
            }
        self.next_update = time.time() + data['refresh']
        while len(self.songs) > MAX_SONGS:
            self.songs.popitem(last=False)


def build_key(strings):
    """Return a normalized tuple of words in the strings."""
    result = []
    for s in strings:
        words = KEY_FILTER_RE.sub(' ', s).casefold().split()
        result.extend(words)
    return tuple(sorted(result))

import re
import time

import requests


BREAK_COVER_URL = 'https://img.radioparadise.com/covers/l/101.jpg'
BREAK_KEY = ('Commercial-free', 'Listener-supported')

COVER_URL = 'https://img.radioparadise.com/{}'

KEY_FILTER_RE = re.compile(r'[^\w\']+')

NOWPLAYING_URL = 'https://api.radioparadise.com/api/nowplaying_list?chan={}'

SLIDESHOW_URL = 'https://img.radioparadise.com/slideshow/720/{}.jpg'

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
        'title': 'RP World/Etc Mix',
        'url_aac': 'http://stream.radioparadise.com/world-etc-128',
        'url_flac': 'http://stream.radioparadise.com/world-etc-flacm',
    },
]
STREAM_INFO = {s['url_aac']: s for s in STREAMS}
STREAM_INFO.update({s['url_flac']: s for s in STREAMS})


class NowPlaying():
    """Provides song information from the "nowplaying" API."""

    def __init__(self):
        """Constructor"""
        self.set_channel(None)

    def get_song_data(self, song_key):
        """Return a dict for the (artist, title) key, or None.

        The "cover" value will be an absolute URL.
        """
        key = build_key(song_key)
        return self.songs.get(key)

    def set_channel(self, channel):
        """Set the RP channel number, or None."""
        if channel is not None:
            self.url = NOWPLAYING_URL.format(channel)
        else:
            self.url = None
        self.next_update = 0
        self.songs = {}

    def update(self):
        """Update song information from the API, if necessary.

        Calls the API only if the "refresh" timer has expired.

        Raises an exception on error responses or timeouts.
        """
        if self.url is None:
            return
        now = time.time()
        if now < self.next_update:
            return
        res = requests.get(self.url, timeout=2)
        res.raise_for_status()
        data = res.json()
        songs = {}
        for song in data['song'].values():
            song['cover'] = COVER_URL.format(song['cover'])
            key = build_key((song['artist'], song['title']))
            songs[key] = song
        if BREAK_KEY not in songs:
            key = build_key(BREAK_KEY)
            songs[key] = {'cover': BREAK_COVER_URL}
        self.songs = songs
        self.next_update = now + data['refresh']


def build_key(strings):
    """Return a normalized tuple of words in the strings."""
    result = []
    for s in strings:
        words = KEY_FILTER_RE.sub(' ', s).casefold().split()
        result.extend(words)
    return tuple(sorted(result))

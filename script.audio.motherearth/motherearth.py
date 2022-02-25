import re
import time
import requests

KEY_FILTER_RE = re.compile(r'[^\w\']+')

NOWPLAYING_URL = 'http://server9.streamserver24.com:9090/api/nowplaying/{}'

STREAMS = [
    {
        'channel': 0,
        'title': 'Mother Earth Radio',
        'url_aac': 'http://server9.streamserver24.com:18900/motherearth.aac',
        'url_flac': 'http://server9.streamserver24.com:18900/motherearth',
    },
    {
        'channel': 1,
        'title': 'Mother Earth Klassik',
        'url_aac': 'http://server9.streamserver24.com:18910/motherearth.klassik.aac',
        'url_flac': 'http://server9.streamserver24.com:18910/motherearth.klassik',
    },
    {
        'channel': 2,
        'title': 'Mother Earth Instrumental',
        'url_aac': 'http://server9.streamserver24.com:18920/motherearth.instrumental.aac',
        'url_flac': 'http://server9.streamserver24.com:18920/motherearth.instrumental',
    },
]
STREAM_INFO = {s['url_aac']: s for s in STREAMS}
STREAM_INFO.update({s['url_flac']: s for s in STREAMS})


class NowPlaying():
    """Provides song information from the "nowplaying" API."""

    def __init__(self):
        """Constructor"""
        self.set_channel(None)

    @property
    def current(self):
        """Return a dict for the current "nowplaying" song, or None.

        The "cover" value will be an absolute URL.
        """
        return self._current

    def get_song_data(self, song_key):
        """Return a dict for the (artist, title) key, or None.

        The "cover" value will be an absolute URL.
        """
        key = build_key(song_key)
        return self.songs.get(key)

    def set_channel(self, channel):
        """Set the channel number, or None."""
        if channel is not None:
            self.url = NOWPLAYING_URL.format((channel) + 3)
        else:
            self.url = None
        self._current = None
        self.next_update = 0
        self.songs = {}

    def update(self):
        """Update song information from the API, if necessary.

        Calls the API only if the "refresh" timer has expired.

        """
        if self.url is None:
            return
        now = time.time()
        if now < self.next_update:
            return
        res = requests.get(self.url, timeout=2)
        res.raise_for_status()
        data = res.json()
        current = None
        songs = {}
        key = build_key((data['now_playing']['song']['artist'], data['now_playing']['song']['title']))            
        songs[key] = {
            'artist': data['now_playing']['song']['artist'],
            'cover': data['now_playing']['song']['art'],
            'title': data['now_playing']['song']['title'],
            'genre': data['now_playing']['song']['genre'],
            'album': data['now_playing']['song']['album'],
            }
        current = songs[key]
        self._current = current
        self.songs = songs
        self.next_update = now + data['now_playing']['remaining']

def build_key(strings):
    """Return a normalized tuple of words in the strings."""
    result = []
    for s in strings:
        words = KEY_FILTER_RE.sub(' ', s).casefold().split()
        result.extend(words)
    return tuple(sorted(result))

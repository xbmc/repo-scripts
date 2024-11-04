import re
import time
import requests

KEY_FILTER_RE = re.compile(r'[^\w\']+')

NOWPLAYING_URL = 'https://motherearth.streamserver24.com/api/nowplaying/{}'

STREAMS = [
    {
        'channel': 0,
        'title': 'Mother Earth Radio',
        'url_aac': 'https://motherearth.streamserver24.com/listen/motherearth/motherearth.aac',
        'url_flac': 'https://motherearth.streamserver24.com/listen/motherearth/motherearth',
    },
    {
        'channel': 1,
        'title': 'Mother Earth Klassik',
        'url_aac': 'https://motherearth.streamserver24.com/listen/motherearth_klassik/motherearth.klassik.aac',
        'url_flac': 'https://motherearth.streamserver24.com/listen/motherearth_klassik/motherearth.klassik',
    },
    {
        'channel': 2,
        'title': 'Mother Earth Instrumental',
        'url_aac': 'https://motherearth.streamserver24.com/listen/motherearth_instrumental/motherearth.instrumental.aac',
        'url_flac': 'https://motherearth.streamserver24.com/listen/motherearth_instrumental/motherearth.instrumental',
    },
        {
        'channel': 3,
        'title': 'Mother Earth Jazz',
        'url_aac': 'https://motherearth.streamserver24.com/listen/motherearth_jazz/motherearth.jazz.aac',
        'url_flac': 'https://motherearth.streamserver24.com/listen/motherearth_jazz/motherearth.jazz',
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
        response = requests.get(self.url, timeout=2)
        response.raise_for_status()
        data = response.json()
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

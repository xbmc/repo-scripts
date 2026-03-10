import re
import time
import requests

KEY_FILTER_RE = re.compile(r'[^\w\']+')

NOWPLAYING_URL = 'https://stream.motherearthradio.de/api/nowplaying/{}'

STREAMS = [
    {
        'channel': 0,
        'station': 'motherearth',
        'title': 'Mother Earth Radio',
        'url_aac': 'https://stream.motherearthradio.de/listen/motherearth/motherearth.aac',
        'url_flac': 'https://stream.motherearthradio.de/listen/motherearth/motherearth',
    },
    {
        'channel': 1,
        'station': 'motherearth_klassik',
        'title': 'Mother Earth Klassik',
        'url_aac': 'https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik.aac',
        'url_flac': 'https://stream.motherearthradio.de/listen/motherearth_klassik/motherearth.klassik',
    },
    {
        'channel': 2,
        'station': 'motherearth_instrumental',
        'title': 'Mother Earth Instrumental',
        'url_aac': 'https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental.aac',
        'url_flac': 'https://stream.motherearthradio.de/listen/motherearth_instrumental/motherearth.instrumental',
    },
    {
        'channel': 3,
        'station': 'motherearth_jazz',
        'title': 'Mother Earth Jazz',
        'url_aac': 'https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz.aac',
        'url_flac': 'https://stream.motherearthradio.de/listen/motherearth_jazz/motherearth.jazz',
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
        """Return a dict for the current "nowplaying" song, or None."""
        return self._current

    def get_song_data(self, song_key):
        """Return a dict for the (artist, title) key, or None."""
        key = build_key(song_key)
        return self.songs.get(key)

    def set_channel(self, channel):
        """Set the channel number, or None."""
        if channel is not None and 0 <= channel < len(STREAMS):
            station = STREAMS[channel]['station']
            self.url = NOWPLAYING_URL.format(station)
        else:
            self.url = None
        self._current = None
        self.next_update = 0
        self.songs = {}

    def update(self):
        """Update song information from the API, if necessary."""
        if self.url is None:
            return
        now = time.time()
        if now < self.next_update:
            return
        try:
            response = requests.get(self.url, timeout=2)
            response.raise_for_status()
            data = response.json()
            song = data['now_playing']['song']
            songs = {}
            key = build_key((song['artist'], song['title']))
            songs[key] = {
                'artist': song['artist'],
                'cover':  song.get('art', ''),
                'title':  song['title'],
                'genre':  song.get('genre', ''),
                'album':  song.get('album', ''),
            }
            self._current = songs[key]
            self.songs = songs
            self.next_update = now + data['now_playing'].get('remaining', 30)
        except Exception:
            # Network error, HTTP error, or unexpected API response —
            # keep existing metadata and retry after 30 seconds
            self.next_update = now + 30


def build_key(strings):
    """Return a normalized tuple of words in the strings."""
    result = []
    for s in strings:
        words = KEY_FILTER_RE.sub(' ', s).casefold().split()
        result.extend(words)
    return tuple(sorted(result))

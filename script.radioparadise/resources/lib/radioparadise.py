import json
from pathlib import Path
import time
from typing import Any, Dict, List, Union

import requests
import xbmcaddon

from .logger import Logger
from .song import Song, SongKey


# RP URLs
_NOWPLAYING_URL = 'https://api.radioparadise.com/api/nowplaying_list_v2022?chan={}&list_num=10'
_COVER_URL = 'https://img.radioparadise.com/{}'
_SLIDESHOW_URL = 'https://img.radioparadise.com/slideshow/720/{}.jpg'

# Metadata for the "station break", which does not appear in the API
_BREAK_SONG = Song(
    'Commercial-free',
    'Listener-supported',
    '',
    0,
    0,
    'https://img.radioparadise.com/covers/l/101.jpg',
    [],
    0.0
)

# Number of seconds to wait for API responses
_UPDATE_TIMEOUT = 3
# Number of seconds to wait before retrying API updates
_UPDATE_WAIT = 5

_LOG = Logger('rp_api')


class NowPlaying:
    """Provides song information from the ``nowplaying`` API."""

    def __init__(self) -> None:
        self._url = None
        self._next_update = 0.0
        self._songs: List[Song] = []
        self.set_channel(None)

    def get_song(self, key: SongKey) -> Union[Song, None]:
        """Return the Song for key, or None."""
        if key == _BREAK_SONG.key:
            return _BREAK_SONG
        for song in self._songs:
            if song.key == key:
                return song
        return None

    def get_next_song(self, key: SongKey) -> Union[Song, None]:
        """Return the next Song for key, or None."""
        for index, song in enumerate(self._songs):
            if song.key == key and index > 0:
                return self._songs[index - 1]
        return None

    def set_channel(self, stream_url: Union[str, None]) -> None:
        """Set the RP channel, or None to stop updates."""
        if stream_url is not None:
            c = Channels().by_url(stream_url)
            self._url = _NOWPLAYING_URL.format(c.channel_id) if c else None
        else:
            self._url = None
        self._next_update = 0.0
        self._songs.clear()

    def update(self) -> None:
        """Update song information from the API, if necessary.

        Calls the API only when the latest known song ends.

        Raises an exception on error responses or timeouts.
        """
        if self._url is None:
            return
        if time.time() < self._next_update:
            return

        latest_song = None
        latest_time = 0

        try:
            res = requests.get(self._url, timeout=_UPDATE_TIMEOUT)
            res.raise_for_status()

            self._songs.clear()
            songs = res.json().get('song', [])
            songs.sort(key=lambda s: s.get('play_time'), reverse=True)
            for data in songs:
                song = NowPlaying._parse_song(data)
                self._songs.append(song)
                play_time = round(data.get('play_time', 0) / 1000)
                if play_time > latest_time:
                    latest_song = song
                    latest_time = play_time
        except Exception:
            self._next_update = time.time() + _UPDATE_WAIT
            raise

        if latest_song:
            next_update = latest_time + latest_song.duration
        else:
            next_update = 0
        now = time.time()
        if next_update > now:
            self._next_update = next_update
        else:
            self._next_update = now + _UPDATE_WAIT

        next_update_hms = time.strftime('%H:%M:%S', time.localtime(self._next_update))
        if latest_song:
            _LOG.log(f'latest_song: {latest_song} (next: {next_update_hms})')
        else:
            _LOG.error(f'No song data. (next: {next_update_hms})')

    @staticmethod
    def _parse_song(data: Dict[str, Any]) -> Song:
        # Replace unexpected null values from the API
        d = ReplaceNoneDict(data)
        artist = d.get('artist', 'Unknown Artist')
        title = d.get('title', 'Unknown Title')
        album = d.get('album', '')
        year = int(d.get('year', '0'))
        duration = round(int(d.get('duration', '0')) / 1000)
        cover = _COVER_URL.format(d.get('cover', ''))
        slideshow = d.get('slideshow', '').split(',')
        slides = [_SLIDESHOW_URL.format(s) for s in slideshow if s]
        rating = d.get('listener_rating', 0.0)
        return Song(artist, title, album, year, duration, cover, slides, rating)


class ReplaceNoneDict(Dict[str, Any]):
    """dict that replaces None values."""

    def get(self, key: str, default: Any = None) -> Any:
        """Returns the default if the value for key is None."""
        value = super().get(key, default)
        return value if value is not None else default


class Channel:
    """Channel information.

    Attributes
    ----------
    channel_id
        Channel ID for the ``nowplaying`` API.
    title
        Channel title.
    url_aac
        Stream URL to use when the addon is set to ``AAC``.
    url_flac
        Stream URL to use when the addon is set to ``FLAC``.
    """

    def __init__(
            self,
            channel_id: int,
            title: str,
            url_aac: str,
            url_flac: str) -> None:
        self.channel_id = channel_id
        self.title = title
        self.url_aac = url_aac
        self.url_flac = url_flac


class Channels:
    """Channel list and lookup.

    Its creation is not thread-safe, but the data is static.
    """

    _instance: Union['Channels', None] = None

    def __new__(cls) -> 'Channels':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_channels()
        return cls._instance

    def _load_channels(self) -> None:
        addon = xbmcaddon.Addon()
        addon_path = addon.getAddonInfo('path')
        channels_file = Path(addon_path, 'resources', 'channels.json')
        channels_list = json.loads(channels_file.read_text())
        self._channels = []
        self._by_id = {}
        self._by_url = {}
        for data in channels_list:
            channel_id = int(data['channel_id'])
            title = str(data['title'])
            url_aac = str(data['url_aac'])
            url_flac = str(data['url_flac'])
            channel = Channel(channel_id, title, url_aac, url_flac)
            self._channels.append(channel)
            self._by_id[channel.channel_id] = channel
            self._by_url[channel.url_aac] = channel
            self._by_url[channel.url_flac] = channel

    def list(self) -> List[Channel]:
        """Return all Channels."""
        return self._channels

    def by_id(self, channel_id: int) -> Union[Channel, None]:
        """Return the Channel matching the ID, or None."""
        return self._by_id.get(channel_id)

    def by_url(self, url: str) -> Union[Channel, None]:
        """Return the Channel matching the stream URL, or None."""
        return self._by_url.get(url)

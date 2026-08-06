import time
from typing import List, Union

import requests
import xbmc
from xbmcaddon import Addon, Settings

from .song import Song, SongKey
from .radioparadise import Channels


class Player(xbmc.Player):
    """Handles xbmc.Player callbacks and restarts playback.

    Attributes
    ----------
    stream_url
        The currently playing RP stream URL, or None.
    """

    def __init__(self) -> None:
        super().__init__()
        self.stream_url: Union[str, None] = None
        self._restart_time = 0.0

    def reset(self) -> None:
        """Reset internal state when not playing RP."""
        self.stream_url = None
        self._restart_time = 0.0

    def get_player_key(self) -> SongKey:
        """Return a key for the currently playing song."""
        key_parts = []
        if self.isPlayingAudio():
            try:
                player_tag = self.getMusicInfoTag()
                key_parts = [player_tag.getArtist(), player_tag.getTitle()]
            except Exception:
                pass
        return SongKey(*key_parts)

    def restart(self) -> None:
        """Restart playback, if necessary."""
        if not self._restart_time or time.time() < self._restart_time:
            return
        if self.stream_url is None:
            return

        try:
            res = requests.head(self.stream_url, timeout=3.0)
            do_restart = (res.status_code == 200)
        except Exception:
            do_restart = False
        if do_restart:
            self._restart_time = 0.0
            self.play(self.stream_url)
        else:
            self._restart_time = time.time() + 3.0

    def onAVStarted(self) -> None:
        """xbmc.Player callback."""
        if self.stream_url:
            xbmc.executebuiltin('Action(FullScreen)')
        else:
            self.reset()

    def onPlayBackEnded(self) -> None:
        """xbmc.Player callback."""
        if self.stream_url:
            self._restart_time = time.time()
        else:
            self.reset()

    def onPlayBackError(self) -> None:
        """xbmc.Player callback."""
        if self.stream_url:
            self._restart_time = time.time()
        else:
            self.reset()

    def onPlayBackStarted(self) -> None:
        """xbmc.Player callback."""
        if (
            self.isPlaying() and
            (url := self.getPlayingFile()) and
            Channels().by_url(url)
        ):
            self.stream_url = url
            self._restart_time = 0.0
        else:
            self.reset()

    def onPlayBackStopped(self) -> None:
        """xbmc.Player callback."""
        self.reset()


class PlayerUpdater(xbmc.Player):
    """Manages song metadata and artwork in the Kodi player."""

    def update(
            self,
            song: Union[Song, None] = None,
            fanart: Union[str, None] = None) -> None:
        """Update the Kodi player's song metadata and artwork."""
        if not self.isPlayingAudio():
            return

        item = self.getPlayingItem()
        if song is not None:
            tag = item.getMusicInfoTag()
            tag.setArtist(song.artist)
            tag.setTitle(song.title)
            tag.setGenres([])
            tag.setAlbum(song.album)
            tag.setRating(song.rating)
            tag.setUserRating(round(song.rating))
            tag.setYear(song.year)
            item.setArt({'thumb': song.cover})
            item.setArt({'fanart': None})
        if fanart is not None:
            item.setArt({'fanart': fanart})
        self.updateInfoTag(item)

    def clear(self) -> None:
        """Clear most of the Kodi player's song information.

        The player's current artist and title are preserved.
        """
        if not self.isPlayingAudio():
            return

        player_tag = self.getMusicInfoTag()
        item = self.getPlayingItem()
        tag = item.getMusicInfoTag()
        tag.setArtist(player_tag.getArtist())
        tag.setTitle(player_tag.getTitle())
        tag.setGenres([])
        tag.setAlbum('')
        tag.setRating(0)
        tag.setUserRating(0)
        tag.setYear(0)
        item.setArt({'thumb': None})
        item.setArt({'fanart': None})
        self.updateInfoTag(item)


class Slideshow:
    """Provides timed slide URLs."""

    def __init__(self) -> None:
        self.set_slides(None)

    def set_slides(self, slides: Union[List[str], None]) -> None:
        """Set the slides, or None to stop the slideshow.

        Parameters
        ----------
        slides
            URLs for slideshow images.
        """
        settings = self._get_settings()
        slideshow = settings.getString('slideshow')
        if slideshow == 'rp':
            self._slides = slides
        else:
            self._slides = None
        self._delay = settings.getInt('slide_duration')
        self._index = 0
        self._time = 0.0

    def next_slide(self) -> Union[str, None]:
        """Return the next slide URL, or None."""
        slide = None
        now = time.time()
        if self._slides and self._time + self._delay < now:
            slide = self._slides[self._index]
            self._index = (self._index + 1) % len(self._slides)
            self._time = now
        return slide

    def _get_settings(self) -> Settings:
        """Return the current Settings."""
        return Addon().getSettings()

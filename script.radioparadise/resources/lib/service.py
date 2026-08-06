from abc import ABC, abstractmethod
import time
from typing import Union

import xbmc

from .logger import Logger
from .player import Player, PlayerUpdater, Slideshow
from .radioparadise import NowPlaying
from .song import Song, SongKey


_LOG = Logger('rp_service')


class SongTracker:
    """Tracks song metadata/expiration and updates the player."""

    def __init__(
            self,
            now_playing: NowPlaying,
            slideshow: Slideshow,
            updater: PlayerUpdater,
            expiration_delay: int = 10) -> None:
        """
        Parameters
        ----------
        expiration_delay
            Grace period after a tracked song has expired, in seconds.
        """
        self.waiting_state = SongTrackerWaitingState(self, now_playing)
        self.tracking_state = SongTrackerTrackingState(self, now_playing)
        self._state: SongTrackerState = self.waiting_state
        self._tracked_key: Union[SongKey, None] = None
        self._tracked_time = 0.0
        self._tracked_song: Union[Song, None] = None
        self._slideshow = slideshow
        self._updater = updater
        self._expiration_delay = expiration_delay

    def update(self, player_key: SongKey) -> None:
        """Update tracked data and the player, as necessary."""
        if self._tracked_key != player_key:
            # Keep track of the local start time on song changes
            if self._tracked_key is not None:
                self._tracked_time = time.time()
            self._tracked_key = player_key
            _LOG.log(f'tracked_key: {player_key}')
            self._state.update_new_key(self._tracked_key)
        else:
            self._state.update_same_key(self._tracked_key)
        if (slide := self._slideshow.next_slide()) is not None:
            self._updater.update(fanart=slide)

    def set_state(self, state: 'SongTrackerState') -> None:
        """Set the new state."""
        self._state = state

    def set_tracked_song(self, song: Union[Song, None]) -> None:
        """Set the new tracked song and update the player.

        If None is passed, it will only clear the player.
        """
        old_song_expired = self.is_tracked_song_expired()
        old_song_duration = self._tracked_song.duration if self._tracked_song else 0
        if old_song_expired:
            _LOG.log('Tracked song expired.')

        if song is not None:
            if old_song_expired:
                # We have enough information to continue tracking
                self._tracked_time += old_song_duration
            self._tracked_song = song
            self._slideshow.set_slides(song.slides)
            slide = self._slideshow.next_slide()
            self._updater.update(song=song, fanart=slide)
            _LOG.log(f'>>>>> {self._tracked_song} <<<<<')
        else:
            self._slideshow.set_slides(None)
            self._updater.clear()
            _LOG.log('<<<<< Player cleared! >>>>>')

    def is_tracked_song_expired(self) -> bool:
        """Return True if the tracked song should be considered expired.

        This can only happen if the tracked key hasn't changed.
        """
        if (
            self._tracked_song and
            self._tracked_song.key == self._tracked_key and
            self._tracked_song.duration and
            self._tracked_time
        ):
            expiration = self._tracked_time + self._tracked_song.duration + self._expiration_delay
            return time.time() > expiration
        else:
            return False


class SongTrackerState(ABC):
    """Base class for SongTrackerStates."""

    def __init__(self, tracker: SongTracker, now_playing: NowPlaying):
        self._tracker = tracker
        self._now_playing = now_playing

    @abstractmethod
    def update_new_key(self, key: SongKey) -> None:
        """Perform updates for a new tracked key."""
        pass

    @abstractmethod
    def update_same_key(self, key: SongKey) -> None:
        """Perform updates for an unchanged tracked key."""
        pass


class SongTrackerWaitingState(SongTrackerState):
    """Waiting for a matching song from the API."""

    def update_new_key(self, key: SongKey) -> None:
        self._match_key(key)

    def update_same_key(self, key: SongKey) -> None:
        if not self._tracker.is_tracked_song_expired():
            self._match_key(key)

    def _match_key(self, key: SongKey) -> None:
        song = self._now_playing.get_song(key)
        if song is not None:
            self._tracker.set_tracked_song(song)
            self._tracker.set_state(self._tracker.tracking_state)


class SongTrackerTrackingState(SongTrackerState):
    """Tracking a matched song from the API."""

    def update_new_key(self, key: SongKey) -> None:
        song = self._now_playing.get_song(key)
        self._tracker.set_tracked_song(song)
        if song is None:
            self._tracker.set_state(self._tracker.waiting_state)

    def update_same_key(self, key: SongKey) -> None:
        if not self._tracker.is_tracked_song_expired():
            return

        song = self._now_playing.get_next_song(key)
        self._tracker.set_tracked_song(song)
        if song is None:
            self._tracker.set_state(self._tracker.waiting_state)


def run_service() -> None:
    _LOG.log('Service started.')
    now_playing = NowPlaying()
    slideshow = Slideshow()
    updater = PlayerUpdater()
    tracker = SongTracker(now_playing, slideshow, updater)
    player = Player()
    monitor = xbmc.Monitor()

    stream_url = None
    while not monitor.abortRequested():
        if monitor.waitForAbort(0.2):
            break

        if stream_url != player.stream_url:
            stream_url = player.stream_url
            now_playing.set_channel(stream_url)

        if stream_url:
            try:
                now_playing.update()
            except Exception as e:
                _LOG.error('API update failed.', exc=e)

            try:
                if (player_key := player.get_player_key()):
                    tracker.update(player_key)
                else:
                    player.restart()
            except Exception as e:
                _LOG.error('Exception in run_service.', exc=e)
    _LOG.log('Service exiting.')

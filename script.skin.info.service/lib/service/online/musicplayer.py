"""Music + musicvideo player handler: fetches artist/track/album online data and rotates fanart."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Final

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import clear_group, set_prop, batch_set_props

if TYPE_CHECKING:
    from lib.data.music import MusicOnlineResult
    from lib.service.online.main import OnlineServiceMain


PLAYER_MUSIC_ONLINE_PREFIX: Final = "SkinInfo.Player.Online.Music."
PLAYER_MUSICVIDEO_ONLINE_PREFIX: Final = "SkinInfo.Player.Online.MusicVideo."


@dataclass(frozen=True)
class _Mode:
    """Everything that differs between the audio and musicvideo tracks."""
    video_content: str
    player: str
    prefix: str
    fetch_mbids: bool
    log_label: str


@dataclass
class _State:
    """Playback state for one mode."""
    key: Optional[str] = None
    part_key: Optional[Tuple[str, str]] = None
    thread: Optional[threading.Thread] = None
    thread_key: Optional[Tuple[str, Tuple[str, str]]] = None


_MODES = (
    _Mode(
        video_content="",
        player="MusicPlayer",
        prefix=PLAYER_MUSIC_ONLINE_PREFIX,
        fetch_mbids=True,
        log_label="Music player",
    ),
    _Mode(
        video_content="musicvideos",
        player="VideoPlayer",
        prefix=PLAYER_MUSICVIDEO_ONLINE_PREFIX,
        fetch_mbids=False,
        log_label="Music video player",
    ),
)


def get_playing_artist_mbids() -> List[str]:
    """Return MusicBrainz artist IDs for the currently playing audio (or `[]`)."""
    try:
        player = xbmc.Player()
        if not player.isPlayingAudio():
            return []
        tag = player.getMusicInfoTag()
        mbids = tag.getMusicBrainzArtistID()
        if isinstance(mbids, list):
            return [m for m in mbids if m]
        return []
    except Exception:
        return []


class MusicPlayerHandler:
    """Tracks audio and musicvideo playback, fetches online data, rotates fanart."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._player = xbmc.Player()
        self._content_file: Optional[str] = None
        self._content_match = False
        self._players: Tuple[Tuple[_Mode, _State], ...] = tuple(
            (mode, _State()) for mode in _MODES
        )
        self._fanart_urls: List[str] = []
        self._fanart_index: int = 0
        self._fanart_last_rotate: float = 0.0
        self._active_prefix: str = PLAYER_MUSIC_ONLINE_PREFIX

    def process(self) -> None:
        """Fetch artist online data whenever either player moves to a new artist."""
        for mode, state in self._players:
            self._process(mode, state)

    def rotate_fanart(self) -> None:
        """Cycle through artist fanart URLs at the configured slideshow interval."""
        # snapshot: a fetch worker can swap the list mid-rotation
        urls = self._fanart_urls
        if len(urls) <= 1:
            return

        now = time.time()

        interval_str = xbmc.getInfoLabel(
            'Skin.String(SkinInfo.SlideshowRefreshInterval)'
        ) or '10'
        try:
            interval = max(5, min(int(interval_str), 3600))
        except ValueError:
            interval = 10

        if now - self._fanart_last_rotate < interval:
            return

        self._fanart_last_rotate = now
        next_index = (self._fanart_index + 1) % len(urls)
        self._fanart_index = next_index
        set_prop(
            f"{self._active_prefix}Artist.FanArt",
            urls[next_index],
        )

    def _mode_active(self, mode: _Mode) -> bool:
        """True while this mode's player plays; a video's content is read once per file."""
        if not mode.video_content:
            return self._player.isPlayingAudio()
        if not self._player.isPlayingVideo():
            return False
        playing = xbmc.getInfoLabel("Player.Filenameandpath")
        if playing != self._content_file:
            self._content_file = playing
            self._content_match = xbmc.getCondVisibility(
                f"VideoPlayer.Content({mode.video_content})")
        return self._content_match

    def _process(self, mode: _Mode, state: _State) -> None:
        """Start a fetch thread when this player's artist, album or track changes."""
        if not self._mode_active(mode):
            self._reset(mode, state)
            return

        artist_name = xbmc.getInfoLabel(f"{mode.player}.Artist") or ""
        if not artist_name:
            self._reset(mode, state)
            return

        # the track and album props change per track, not per artist
        part_key = (xbmc.getInfoLabel(f"{mode.player}.Album") or "",
                    xbmc.getInfoLabel(f"{mode.player}.Title") or "")
        artist_changed = artist_name != state.key
        if not artist_changed and part_key == state.part_key:
            return

        state.key = artist_name
        state.part_key = part_key
        if artist_changed:
            self._fanart_urls = []
            self._fanart_index = 0

        thread_key = (artist_name, part_key)
        if state.thread and state.thread.is_alive() and state.thread_key == thread_key:
            return

        state.thread_key = thread_key
        state.thread = threading.Thread(
            target=self._fetch_worker,
            args=(mode, state, artist_name, part_key, artist_changed),
            daemon=True,
        )
        state.thread.start()

    def _fetch_worker(self, mode: _Mode, state: _State, artist_name: str,
                      part_key: Tuple[str, str], fetch_artist: bool) -> None:
        """Fetch off-thread, discarding a stale result and clearing properties on an empty one."""
        try:
            if self._service.abort_flag.is_requested():
                return

            album, title = part_key[0] or None, part_key[1] or None

            if not fetch_artist:
                if artist_name == state.key and part_key == state.part_key:
                    self._apply_parts(mode, artist_name, title, album)
                return

            from lib.data.music import fetch_artist_online_data

            mbids = get_playing_artist_mbids() if mode.fetch_mbids else None
            result = fetch_artist_online_data(
                artist_name,
                mbids=mbids or None,
                album=album,
                track=title,
                abort_flag=self._service.capped_abort_flag,
            )

            if artist_name != state.key:
                return
            if not result:
                clear_group(mode.prefix)
                self._apply_parts(mode, artist_name, title, album)
                return

            self._apply(mode, artist_name, result, title, album)
            self._apply_lists(mode, state, artist_name, result.mbid)

        except Exception as e:
            log("Service", f"{mode.log_label} online fetch error: {e}", xbmc.LOGWARNING)

    def _apply(self, mode: _Mode, artist_name: str, result: 'MusicOnlineResult',
               track: Optional[str], album: Optional[str]) -> None:
        """Publish artist, track and album properties under this mode's prefix."""
        from lib.data.music import fill_artist_online_props

        self._fanart_urls = result.fanart_urls
        self._fanart_index = 0
        self._fanart_last_rotate = time.time()
        self._active_prefix = mode.prefix

        artist_props: Dict[str, Optional[str]] = {}
        fill_artist_online_props(artist_props, mode.prefix, result, name=artist_name)
        batch_set_props(artist_props)

        self._apply_parts(mode, artist_name, track, album)

    def _apply_parts(self, mode: _Mode, artist_name: str,
                     track: Optional[str], album: Optional[str]) -> None:
        """Publish the track and album properties for whatever is playing now."""
        from lib.data.music import fill_track_online_props, fill_album_online_props

        if track:
            track_props: Dict[str, Optional[str]] = {}
            fill_track_online_props(track_props, mode.prefix, artist_name, track,
                                    abort_flag=self._service.capped_abort_flag)
            if track_props:
                batch_set_props(track_props)

        if album:
            album_props: Dict[str, Optional[str]] = {}
            fill_album_online_props(album_props, mode.prefix, artist_name, album,
                                    abort_flag=self._service.capped_abort_flag)
            if album_props:
                batch_set_props(album_props)

    def _apply_lists(self, mode: _Mode, state: _State, artist_name: str, mbid: str) -> None:
        """Fetch and apply the artist's studio albums and similar artists if still playing."""
        from lib.data.music import fetch_artist_lists, fill_artist_lists

        albums, similar = fetch_artist_lists(mbid, abort_flag=self._service.capped_abort_flag)
        if artist_name != state.key:
            return
        props: Dict[str, Optional[str]] = {}
        fill_artist_lists(props, mode.prefix, albums, similar)
        batch_set_props(props)

    def _reset(self, mode: _Mode, state: _State) -> None:
        """Clear this player's properties once it stops."""
        if state.key:
            clear_group(mode.prefix)
            state.part_key = None
            self._fanart_urls = []
            self._fanart_index = 0
            state.key = None

"""Music video focus handler: sets `SkinInfo.MusicVideo.Online.*` for the focused item."""
from __future__ import annotations

import threading
from typing import Dict, Optional, Tuple, TYPE_CHECKING, Final

import xbmc

from lib.kodi.client import log
from lib.kodi.utilities import (
    LabelSnapshot, batch_set_props, clear_group, modal_dialog_active, normalize_dbtype,
)

if TYPE_CHECKING:
    from lib.service.online.main import OnlineServiceMain, CancelToken


ONLINE_PREFIX: Final = "SkinInfo.MusicVideo.Online."
FOCUS_LABELS: Final = ("ListItem.DBType", "ListItem.DBID", "ListItem.Property(musicvideomediatype)",
                       "ListItem.Artist", "ListItem.Album", "ListItem.Title", "ListItem.Label")

_ONLINE_KEYS = (
    "Artist.Bio", "Artist.FanArt", "Artist.FanArt.Count",
    "Artist.Thumb", "Artist.Clearlogo", "Artist.Banner",
    "Track.Wiki", "Track.Tags", "Track.Listeners", "Track.Playcount",
    "Album.Wiki", "Album.Tags", "Album.Label",
)


class MusicVideoFocusHandler:
    """Sets SkinInfo.MusicVideo.Online.* for the focused music video."""

    def __init__(self, service: 'OnlineServiceMain'):
        self._service = service
        self._last_key: Optional[str] = None
        self._fetch_thread: Optional[threading.Thread] = None
        self._token: Optional['CancelToken'] = None

    def process(self, labels: LabelSnapshot) -> None:
        """Read the focused music video or artist node and start a background online fetch."""
        artist, album, title = self._read_focus(labels)
        if not artist:
            if modal_dialog_active():
                return
            if self._last_key is not None:
                self._cancel_pending()
                clear_group(ONLINE_PREFIX)
                self._last_key = None
            return

        key = "{}|{}|{}".format(artist, title, album)
        if key == self._last_key:
            return
        self._last_key = key

        self._cancel_pending()
        clear_group(ONLINE_PREFIX)
        token = self._service.new_cancel_token()
        self._token = token
        self._fetch_thread = threading.Thread(
            target=self._fetch_worker,
            args=(artist, album, title, token),
            daemon=True,
        )
        self._fetch_thread.start()

    def _cancel_pending(self) -> None:
        """Cancel the previous item's in-flight fetch so a fast scroll stops piling on."""
        if self._token is not None:
            self._token.cancel()
            self._token = None

    @staticmethod
    def _read_focus(labels: LabelSnapshot) -> Tuple[str, str, str]:
        """Read (artist, album, title) for a focused music video or artist node, else empties."""
        dbtype = normalize_dbtype(labels.get("ListItem.DBType"))
        if dbtype == "musicvideo":
            if not labels.get("ListItem.DBID"):
                return "", "", ""
            return (labels.get("ListItem.Artist"), labels.get("ListItem.Album"),
                    labels.get("ListItem.Title"))
        mediatype = labels.get("ListItem.Property(musicvideomediatype)")
        if dbtype == "actor" and normalize_dbtype(mediatype) == "artist":
            return labels.get("ListItem.Label"), "", ""
        return "", "", ""

    def _fetch_worker(self, artist: str, album: str, title: str,
                      token: 'CancelToken') -> None:
        """Fetch artist, album and track data off-thread for the focused music video."""
        try:
            if token.is_requested():
                return

            from lib.data.music import (
                fetch_artist_online_data,
                fill_artist_online_props,
                fill_track_online_props,
                fill_album_online_props,
            )

            result = fetch_artist_online_data(
                artist, album=album or None, track=title or None, abort_flag=token,
            )

            if token.is_requested():
                return

            props: Dict[str, Optional[str]] = {
                f"{ONLINE_PREFIX}{k}": "" for k in _ONLINE_KEYS
            }
            if result:
                fill_artist_online_props(props, ONLINE_PREFIX, result)
            if title:
                fill_track_online_props(props, ONLINE_PREFIX, artist, title, abort_flag=token)
            if album:
                fill_album_online_props(props, ONLINE_PREFIX, artist, album, abort_flag=token)

            if token.is_requested() or self._token is not token:
                return
            batch_set_props(props)

        except Exception as e:
            log("Service", f"Music video focus online fetch error: {e}", xbmc.LOGWARNING)

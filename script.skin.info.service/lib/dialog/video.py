from __future__ import annotations

from typing import Dict, Optional, Final

import xbmc

from lib.dialog.base import InfoDialogBase, ADDON_PATH
from lib.kodi.client import log

XML_FILE: Final = 'script-skin-info-service-DialogVideoInfo.xml'


class DialogVideoInfo(InfoDialogBase):
    """Video info window driven by online data, with library containers when a dbid is known."""

    def __init__(self, *args, **kwargs):
        self._media_type: str = kwargs.pop('media_type', '')
        self._dbid: str = kwargs.pop('dbid', '')
        self._tmdb_id: str = kwargs.pop('tmdb_id', '')
        self._imdb_id: str = kwargs.pop('imdb_id', '')
        self._online_props: Dict[str, str] = kwargs.pop('online_props', {})
        super().__init__(*args, **kwargs)
        self._set_load_properties()

    def onInit(self) -> None:
        """Populate the dialog and start the poster and fanart blur once Kodi has built it."""
        xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
        self.mark_topmost()
        self._set_video_properties()
        self._bind_containers()
        self._start_blur([
            ('blurredposter', self._online_props.get('Poster', '')),
            ('blurredfanart', self._online_props.get('Fanart', '')),
        ])

    def _set_load_properties(self) -> None:
        """Set the properties the skin reads while loading; the rest wait for onInit."""
        props = {'mediatype': self._media_type}
        if self._dbid:
            props['dbid'] = self._dbid
        self.set_properties(props)

    def _set_video_properties(self) -> None:
        """Set the dialog's online properties along with its media type and ids."""
        props = dict(self._online_props)
        props['mediatype'] = self._media_type
        if self._dbid:
            props['dbid'] = self._dbid
        if self._tmdb_id:
            props['tmdb_id'] = self._tmdb_id
        if self._imdb_id:
            props['imdb_id'] = self._imdb_id
        self.set_properties(props)

    def _bind_containers(self) -> None:
        """Bind the skin's containers to plugin paths for credits, posters and related titles."""
        base_url = 'plugin://script.skin.info.service/'
        containers: Dict[str, str] = {}

        if not self._media_type:
            return

        id_args = []
        if self._tmdb_id:
            id_args.append(f"tmdb_id={self._tmdb_id}")
        if self._dbid:
            id_args.append(f"dbid={self._dbid}")
        if not id_args:
            return
        id_query = '&'.join(id_args)

        containers['cast'] = (
            f"{base_url}?action=get_cast"
            f"&dbtype={self._media_type}&online=true&{id_query}"
        )

        if self._media_type in ('movie', 'tvshow'):
            containers['crew'] = f"{base_url}?action=crew&dbtype={self._media_type}&{id_query}"
            containers['recommendations'] = (
                f"{base_url}?action=tmdb_recommendations&dbtype={self._media_type}&{id_query}"
            )
            containers['similar'] = (
                f"{base_url}?action=similar&dbtype={self._media_type}&{id_query}"
            )
            containers['posters'] = (
                f"{base_url}?action=tmdb_posters&dbtype={self._media_type}&{id_query}"
            )

        if self._dbid:
            containers['library'] = f"{base_url}?dbid={self._dbid}&dbtype={self._media_type}"

        for name, path in containers.items():
            self.setProperty(f"container.{name}.path", path)


def open_video_info(
    tmdb_id: str = '',
    imdb_id: str = '',
    media_type: str = '',
    dbid: str = '',
    online_props: Optional[Dict[str, str]] = None,
) -> None:
    """Open the video info dialog, fetching online data first when none was supplied."""
    if not online_props:
        if not tmdb_id and not imdb_id:
            log("General", "DialogVideoInfo: No tmdb_id or imdb_id", xbmc.LOGWARNING)
            return

        from lib.data.online import fetch_all_online_data
        online_props = fetch_all_online_data(
            media_type=media_type,
            imdb_id=imdb_id,
            tmdb_id=tmdb_id,
        )

        if not online_props:
            log("General", f"DialogVideoInfo: No online data for tmdb={tmdb_id}", xbmc.LOGWARNING)
            return

    dialog = DialogVideoInfo(
        XML_FILE,
        ADDON_PATH,
        'default',
        '1080i',
        media_type=media_type,
        dbid=dbid,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        online_props=online_props,
    )
    dialog.doModal()
    del dialog

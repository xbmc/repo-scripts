from __future__ import annotations

import urllib.parse
from typing import Dict, Optional, Final

import xbmc

from lib.dialog.base import InfoDialogBase, ADDON_PATH
from lib.kodi.client import log

XML_FILE: Final = 'script-skin-info-service-DialogActorInfo.xml'


class DialogActorInfo(InfoDialogBase):
    """Person info window backed by TMDB, with library and online filmography containers."""

    def __init__(self, *args, **kwargs):
        self._person_data: Dict = kwargs.pop('person_data', {})
        self._person_id: int = kwargs.pop('person_id', 0)
        self._person_name: str = kwargs.pop('person_name', '')
        super().__init__(*args, **kwargs)

    def onInit(self) -> None:
        """Populate the dialog and start the profile blur once Kodi has built it."""
        xbmc.executebuiltin('Dialog.Close(busydialognocancel,true)')
        self.mark_topmost()
        self._set_person_properties()
        self._bind_containers()
        self._start_blur([('blurredthumb', self.getProperty('profileimage'))])

    def _set_person_properties(self) -> None:
        """Set the person's TMDB details and id as dialog properties."""
        from lib.data.api.person import build_person_props

        props = build_person_props(self._person_data)
        props['person_id'] = str(self._person_id)
        self.set_properties(props)

    def _bind_containers(self) -> None:
        """Point the skin's containers at plugin paths for the person's credits and images."""
        base_url = 'plugin://script.skin.info.service/'
        pid = str(self._person_id)
        encoded_name = urllib.parse.quote(self._person_name)

        containers = {
            'library_movies': (
                f"{base_url}?action=person_library&info_type=movies"
                f"&person_id={pid}&person_name={encoded_name}"
            ),
            'library_tvshows': (
                f"{base_url}?action=person_library&info_type=tvshows"
                f"&person_id={pid}&person_name={encoded_name}"
            ),
            'movies': (
                f"{base_url}?action=person_info&info_type=filmography&person_id={pid}&dbtype=movie"
            ),
            'tvshows': (
                f"{base_url}?action=person_info&info_type=filmography&person_id={pid}&dbtype=tvshow"
            ),
            'all_credits': f"{base_url}?action=person_info&info_type=filmography&person_id={pid}",
            'crew': f"{base_url}?action=person_info&info_type=crew&person_id={pid}",
            'images': f"{base_url}?action=person_info&info_type=images&person_id={pid}",
        }

        for name, path in containers.items():
            self.setProperty(f"container.{name}.path", path)


def open_actor_info(
    person_id: int,
    person_name: str,
    person_data: Optional[Dict] = None,
) -> None:
    """Open the actor info dialog, fetching the person data when none was supplied."""
    if not person_data:
        from lib.data.api.person import get_person_data
        person_data = get_person_data(person_id)
        if not person_data:
            log("General", f"DialogActorInfo: No data for person_id={person_id}", xbmc.LOGWARNING)
            return

    dialog = DialogActorInfo(
        XML_FILE,
        ADDON_PATH,
        'default',
        '1080i',
        person_data=person_data,
        person_id=person_id,
        person_name=person_name,
    )
    dialog.doModal()
    del dialog

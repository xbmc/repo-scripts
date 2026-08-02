from __future__ import annotations

import urllib.parse
from typing import Dict, Optional

import xbmc
import xbmcgui

from lib.info.dialogs.base import InfoDialogBase, ADDON_PATH
from lib.kodi.client import log

XML_FILE = 'script-skin-info-service-DialogActorInfo.xml'


class DialogActorInfo(InfoDialogBase):

    def __init__(self, *args, **kwargs):
        self._person_data: Dict = kwargs.pop('person_data', {})
        self._person_id: int = kwargs.pop('person_id', 0)
        self._person_name: str = kwargs.pop('person_name', '')
        super().__init__(*args, **kwargs)

    def onInit(self) -> None:
        xbmc.executebuiltin('Dialog.Close(busydialog,true)')
        self.mark_topmost()
        self._set_person_properties()
        self._bind_containers()
        self._start_blur([('BlurredThumb', self.getProperty('ProfileImage'))])

    def _set_person_properties(self) -> None:
        from lib.data.api.person import build_person_props

        props = build_person_props(self._person_data)
        props['person_id'] = str(self._person_id)
        self.set_properties(props)

    def _bind_containers(self) -> None:
        base_url = 'plugin://script.skin.info.service/'
        pid = str(self._person_id)
        encoded_name = urllib.parse.quote(self._person_name)

        containers = {
            'library_movies': (
                f"{base_url}?action=person_library&info_type=movies&person_name={encoded_name}"
            ),
            'library_tvshows': (
                f"{base_url}?action=person_library&info_type=tvshows&person_name={encoded_name}"
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

    def onAction(self, action: xbmcgui.Action) -> None:
        if self.is_close_action(action):
            self.close()


def open_actor_info(
    person_id: int,
    person_name: str,
    person_data: Optional[Dict] = None,
) -> None:
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

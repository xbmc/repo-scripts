from __future__ import annotations

from typing import Dict
import xbmcgui


_CLOSE_ACTIONS = (
    xbmcgui.ACTION_NAV_BACK,
    xbmcgui.ACTION_PREVIOUS_MENU,
    92, 216, 247, 257, 275, 61467, 61448,
)


class DialogBase(xbmcgui.WindowXMLDialog):

    def set_properties(self, props: Dict[str, str]) -> None:
        for key, value in props.items():
            if value:
                self.setProperty(key, str(value))

    def is_close_action(self, action: xbmcgui.Action) -> bool:
        return action.getId() in _CLOSE_ACTIONS

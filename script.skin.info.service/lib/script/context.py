"""Context menu handler for Skin Info Service."""
from __future__ import annotations

import sys
import xbmc
import xbmcaddon
import xbmcgui


_ARTWORK_TYPES = ('movie', 'tvshow', 'episode', 'season', 'set', 'musicvideo', 'artist', 'album')
_RATINGS_TYPES = ('movie', 'tvshow', 'episode', 'set')
_NFO_TYPES = ('movie', 'tvshow', 'episode', 'musicvideo')

# (setting_id, label_id, action, applicable_types_or_None_for_any)
_MENU_REGISTRY = (
    ('context_show_review_artwork',   32100, 'review_artwork',   _ARTWORK_TYPES),
    ('context_show_download_artwork', 32290, 'download_artwork', _ARTWORK_TYPES),
    ('context_show_update_ratings',   32101, 'update_ratings',   _RATINGS_TYPES),
    ('context_show_edit_metadata',    32103, 'edit',             None),
    ('context_show_export_nfo',       32029, 'export_nfo',       _NFO_TYPES),
)


def main() -> None:
    """Context-menu entry: show enabled actions (review/download art, ratings, edit), dispatch."""
    addon: xbmcaddon.Addon = xbmcaddon.Addon()

    listitem = getattr(sys, 'listitem', None)
    if listitem is None:
        return

    db_id: int = 0
    db_type: str = ''

    videotag = listitem.getVideoInfoTag()
    if videotag:
        db_id = videotag.getDbId()
        db_type = videotag.getMediaType()

    if not db_id or not db_type:
        musictag = listitem.getMusicInfoTag()
        if musictag:
            db_id = musictag.getDbId()
            db_type = musictag.getMediaType()

    if not db_id or not db_type:
        return

    menu_items: list[str] = []
    actions: list[str] = []

    for setting_id, label_id, action_name, applicable_types in _MENU_REGISTRY:
        if applicable_types is not None and db_type not in applicable_types:
            continue
        if not addon.getSettingBool(setting_id):
            continue
        menu_items.append(addon.getLocalizedString(label_id))
        actions.append(action_name)

    if not menu_items:
        return

    selected: int = xbmcgui.Dialog().contextmenu(menu_items)
    if selected < 0:
        return

    xbmc.executebuiltin(
        f'RunScript(script.skin.info.service,action={actions[selected]},dbid={db_id},dbtype={db_type})'
    )

"""Multi-select ordered image chooser for extra art slots.

Handles EXTRA art slots only (fanart1/fanart2, poster1/poster2, etc.).
Main art slot (fanart, poster, etc.) is handled by dialogs/select.py

Skinner control IDs and window/ListItem properties: DOCS/tools/artwork-review.md
"""
from __future__ import annotations

import xbmc
import xbmcgui
from typing import Optional, cast
from lib.artwork.dialogs.base import ArtworkDialogBase
from lib.artwork.utilities import parse_art_slot_index
from lib.artwork.config import FANART_DIMENSIONS_VARIANTS
from lib.kodi.client import get_item_details, KODI_GET_DETAILS_METHODS, log, ADDON


class ArtworkDialogMulti(ArtworkDialogBase):
    """Dialog for managing extra art slots (fanart1/fanart2, poster1/poster2, etc.).

    Uses a working set approach:
    - List 100: Working set (click to remove)
    - List 200: Available art not in working set (click to add)
    - Apply: Saves working set as fanart1, fanart2, etc.
    """

    CURRENT_ART_LIST = 100
    AVAILABLE_ART_LIST = 200
    BUTTON_APPLY = 300
    BUTTON_CANCEL = 301
    BUTTON_CLEAR_ALL = 302
    BUTTON_SORT = 303
    BUTTON_SOURCE_PREF = 304

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.media_type = kwargs.get('media_type', 'movie')
        self.dbid = kwargs.get('dbid', 0)
        self.title = kwargs.get('title', '')
        self.art_type = kwargs.get('art_type', 'fanart')
        self.test_mode = kwargs.get('test_mode', False)

        self.current_extra_art = {}
        self.current_main_art = None
        self.available_art = []
        self.full_artwork_list = []
        self.working_art = []
        self.result = None
        self.sort_mode = 'popularity'
        self.source_pref = 'all'

    def onInit(self):
        """Called when dialog opens."""
        self.setProperty('multiart_dialog_active', 'true')

        if self.test_mode:
            self._load_test_data()
        else:
            self._load_current_extra_art()
            self._fetch_available_art()

        # Set window properties for XML
        art_label = (
            f"Multi-Art {self.art_type.title()}"
            if self.art_type != 'fanart'
            else "Multi-Art Fanart"
        )
        self.setProperty('heading', self.title)
        self.setProperty('arttype', art_label)
        self.setProperty('mediatype', self.media_type)

        self._populate_current_art()
        self._populate_available_art()
        self._update_selection_count()

        available_sources = self._get_available_sources()
        self.setProperty('show_source_button', 'true' if len(available_sources) > 1 else 'false')

        available_resolutions = self._get_available_resolutions()
        self.setProperty('show_sort_button', 'true' if len(available_resolutions) > 1 else 'false')

        self._publish_sort_state()
        self._publish_source_pref_state()

    def _load_current_extra_art(self) -> None:
        """Load current extra art URLs from library (numbered slots only) and main art."""
        if self.media_type not in KODI_GET_DETAILS_METHODS:
            return

        details = get_item_details(self.media_type, self.dbid, ['art'])
        if not isinstance(details, dict):
            return

        art = details.get('art', {})

        # Load main art slot (e.g., 'fanart', 'poster')
        self.current_main_art = art.get(self.art_type)

        for key, url in art.items():
            if key.startswith(self.art_type) and key != self.art_type:
                suffix = key[len(self.art_type):]
                if suffix and suffix.isdigit():
                    if url:
                        self.current_extra_art[key] = url

        sorted_slots = sorted(
            self.current_extra_art.items(),
            key=lambda x: parse_art_slot_index(x[0])
        )
        self.working_art = [url for _, url in sorted_slots if url]

    def _fetch_available_art(self) -> None:
        """Fetch available art from online sources (TMDB, fanart.tv)."""
        from lib.data.api.artwork import create_default_fetcher
        from lib.artwork.utilities import sort_artwork_by_popularity, filter_artwork_by_language

        try:
            fetcher = create_default_fetcher()
            all_art = fetcher.fetch_all(self.media_type, self.dbid)
            self.full_artwork_list = all_art.get(self.art_type, [])

            filtered = filter_artwork_by_language(
                self.full_artwork_list,
                art_type=self.art_type,
                language_code=None
            )

            self.available_art = sort_artwork_by_popularity(
                filtered,
                art_type=self.art_type,
                sort_mode=self.sort_mode,
                source_pref=self.source_pref
            )
        except Exception as e:
            import traceback
            log(
                "Artwork",
                f"Error fetching available art: {str(e)}\n{traceback.format_exc()}",
                xbmc.LOGERROR,
            )
            self.available_art = []
            self.full_artwork_list = []

    def _load_test_data(self) -> None:
        """Load dummy test data for skinning preview."""
        import xbmcvfs

        art_type_map = {
            'poster': ('artwork_test_poster.png', (1000, 1500)),
            'keyart': ('artwork_test_poster.png', (1000, 1500)),
            'fanart': ('artwork_test_fanart.png', (1920, 1080)),
            'clearlogo': ('artwork_test_clearlogo.png', (800, 310)),
            'clearart': ('artwork_test_landscape.png', (1000, 562)),
            'landscape': ('artwork_test_landscape.png', (1000, 562)),
            'thumb': ('artwork_test_landscape.png', (1000, 562)),
            'banner': ('artwork_test_banner.png', (1000, 185)),
            'characterart': ('artwork_test_characterart.png', (1000, 1399)),
            'discart': ('artwork_test_square.png', (1000, 1000)),
        }

        image_file, _ = art_type_map.get(
            self.art_type.lower(), ('artwork_test_poster.png', (1000, 1500))
        )
        test_image_path = xbmcvfs.translatePath(f'special://home/addons/script.skin.info.service/resources/skins/default/media/artwork_test/{image_file}')

        self.current_extra_art = {
            f'{self.art_type}1': test_image_path,
            f'{self.art_type}2': test_image_path,
        }

        self.working_art = [test_image_path, test_image_path]

        base_dims = FANART_DIMENSIONS_VARIANTS.get(
            self.art_type, [(1920, 1080), (1280, 720), (3840, 2160)]
        )

        self.available_art = []
        for i in range(20):
            width, height = base_dims[i % len(base_dims)]

            self.available_art.append({
                'url': f'{test_image_path}#{i}',
                'previewurl': test_image_path,
                'width': width,
                'height': height,
            })

    def _populate_current_art(self) -> None:
        """Populate CURRENT_ART_LIST with working art set (click to remove)."""
        try:
            control = self.getControl(self.CURRENT_ART_LIST)
        except Exception:
            return

        art_by_url = {
            self._normalize_url(art.get('url', '')): art
            for art in self.full_artwork_list if art.get('url')
        }

        items = []
        for idx, url in enumerate(self.working_art):
            if not url:
                continue

            slot = f"{self.art_type}{idx + 1}"

            item = xbmcgui.ListItem(label=slot)
            item.setProperty('url', url)
            item.setProperty('index', str(idx))

            art_info = art_by_url.get(self._normalize_url(url))
            if art_info:
                preview = art_info.get('previewurl', url)
                item.setArt({'thumb': preview})

                width = art_info.get('width')
                height = art_info.get('height')
                if width and height:
                    item.setProperty('dimensions', f"{width}x{height}")
                    item.setProperty('width', str(width))
                    item.setProperty('height', str(height))
            else:
                item.setArt({'thumb': url})

            items.append(item)

        self.populate_list_batch(control, items)

    def create_artwork_listitem(self, art_info: dict, index: int) -> xbmcgui.ListItem:
        """Override to add is_current property marking artwork already set as main art."""
        item = super().create_artwork_listitem(art_info, index)

        if self.current_main_art:

            url = art_info.get('url', '')
            normalized_current = self._normalize_url(self.current_main_art)
            normalized_art = self._normalize_url(url)

            if normalized_current == normalized_art:
                item.setProperty('is_current', 'true')
            else:
                item.setProperty('is_current', 'false')
        else:
            item.setProperty('is_current', 'false')

        return item

    def _populate_available_art(self) -> None:
        """Populate AVAILABLE_ART_LIST with options not already in working set."""
        try:
            control = self.getControl(self.AVAILABLE_ART_LIST)
        except Exception:
            return

        normalized_working_urls = {self._normalize_url(url) for url in self.working_art}

        items = [
            self.create_artwork_listitem(art_info, idx)
            for idx, art_info in enumerate(self.available_art)
            if self._normalize_url(art_info.get('url', '')) not in normalized_working_urls
        ]

        self.populate_list_batch(control, items)

    def _update_selection_count(self) -> None:
        """Update selection count property (matches regular artwork dialog format)."""
        count = len(self.working_art)
        if count == 0:
            count_text = ADDON.getLocalizedString(32012)
        else:
            count_text = ADDON.getLocalizedString(32015).format(count)

        self.setProperty('count', count_text)
        self.setProperty('count_total', str(len(self.available_art)))
        self.setProperty('count_selected', str(count))

    def onClick(self, controlId):
        """Handle button/list clicks."""
        if controlId == self.AVAILABLE_ART_LIST:
            self._add_from_available()

        elif controlId == self.CURRENT_ART_LIST:
            self._remove_from_current()

        elif controlId == self.BUTTON_APPLY:
            self._apply_changes()

        elif controlId == self.BUTTON_CANCEL:
            self.result = None
            self.close()

        elif controlId == self.BUTTON_CLEAR_ALL:
            self._clear_all()

        elif controlId == self.BUTTON_SORT:
            self._toggle_sort_mode()

        elif controlId == self.BUTTON_SOURCE_PREF:
            self._toggle_source_pref()

    def _add_from_available(self) -> None:
        """Move selected item from available list into working set.

        Removes from the available list (active control, preserves focus)
        and rebuilds the current list.
        """
        try:
            available_control = cast(xbmcgui.ControlList, self.getControl(self.AVAILABLE_ART_LIST))
            item = available_control.getSelectedItem()
            if not item:
                return

            url = item.getProperty('fullurl')
            if not url:
                return

            self.working_art.append(url)

            selected_pos = available_control.getSelectedPosition()
            xbmc.sleep(50)
            available_control.removeItem(selected_pos)

            remaining = available_control.size()
            if remaining > 0:
                available_control.selectItem(min(selected_pos, remaining - 1))

            self._populate_current_art()
            self._update_selection_count()

        except Exception as e:
            log("Artwork", f"Error adding from available: {str(e)}", xbmc.LOGERROR)

    def _remove_from_current(self) -> None:
        """Remove selected item from working set, returning it to the available list.

        Removes from the current list (active control, preserves focus)
        and rebuilds the available list.
        """
        try:
            current_control = cast(xbmcgui.ControlList, self.getControl(self.CURRENT_ART_LIST))
            item = current_control.getSelectedItem()
            if not item:
                return

            index = int(item.getProperty('index'))

            if not (0 <= index < len(self.working_art)):
                return

            self.working_art.pop(index)

            selected_pos = current_control.getSelectedPosition()
            xbmc.sleep(50)
            current_control.removeItem(selected_pos)

            remaining = current_control.size()
            if remaining > 0:
                current_control.selectItem(min(selected_pos, remaining - 1))

            for i in range(remaining):
                li = current_control.getListItem(i)
                li.setLabel(f"{self.art_type}{i + 1}")
                li.setProperty('index', str(i))

            self._populate_available_art()
            self._update_selection_count()

        except Exception as e:
            log("Artwork", f"Error removing from current: {str(e)}", xbmc.LOGERROR)

    def _clear_all(self) -> None:
        """Clear working set back to original state."""
        sorted_slots = sorted(
            self.current_extra_art.items(),
            key=lambda x: parse_art_slot_index(x[0])
        )
        self.working_art = [url for _, url in sorted_slots if url]

        self._populate_current_art()
        self._populate_available_art()
        self._update_selection_count()

    def _apply_changes(self) -> None:
        """Apply working set as final extra art assignments."""
        art_dict = {}
        for idx, url in enumerate(self.working_art):
            slot = f"{self.art_type}{idx + 1}"
            art_dict[slot] = url

        for slot in self.current_extra_art.keys():
            if slot not in art_dict:
                art_dict[slot] = None

        self.result = art_dict
        self.close()

    def close(self) -> None:
        """Override close to clear active dialog property."""
        self.setProperty('multiart_dialog_active', '')
        super().close()

    def _resort_artwork(self) -> None:
        """Re-sort and filter artwork from full list, then refresh available panel."""
        from lib.artwork.utilities import sort_artwork_by_popularity, filter_artwork_by_language

        filtered = filter_artwork_by_language(
            self.full_artwork_list,
            art_type=self.art_type,
            language_code=None
        )

        self.available_art = sort_artwork_by_popularity(
            filtered,
            art_type=self.art_type,
            sort_mode=self.sort_mode,
            source_pref=self.source_pref
        )

        self._populate_available_art()
        self._update_selection_count()


def show_multiart_dialog(
    media_type: str, dbid: int, title: str, art_type: str = 'fanart', test_mode: bool = False
) -> Optional[dict]:
    """Show multi-art dialog and return selected art dict.

    Manages numbered slots only (e.g. fanart1, fanart2). Returns dict like
    {'fanart1': 'url1', 'fanart2': 'url2'} or None if cancelled.
    """
    addon_path = ADDON.getAddonInfo('path')

    dialog = ArtworkDialogMulti(
        'script.skin.info.service-MultiArtSelection.xml',
        addon_path,
        'default',
        '1080i',
        media_type=media_type,
        dbid=dbid,
        title=title,
        art_type=art_type,
        test_mode=test_mode
    )

    dialog.doModal()
    result = dialog.result
    del dialog

    return result

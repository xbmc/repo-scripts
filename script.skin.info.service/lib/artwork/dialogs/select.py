"""Visual artwork chooser for manual review.

Skinner control IDs and window/ListItem properties: DOCS/tools/artwork-review.md
"""
from __future__ import annotations

import xbmc
from lib.infrastructure.dialogs import show_select
from typing import Optional, List, Tuple
from lib.artwork.dialogs.base import ArtworkDialogBase
from lib.artwork.dialogs.multi import show_multiart_dialog
from lib.kodi.settings import KodiSettings
from lib.kodi.client import decode_image_url, log, ADDON


ARTLAYOUT_MAP = {
    'poster': 'poster',
    'keyart': 'poster',
    'fanart': 'fanart',
    'thumb': 'fanart',
    'landscape': 'landscape',
    'clearart': 'landscape',
    'discart': 'square',
    'cutout': 'square',
    'back': 'square',
    '3dthumb': 'square',
}


class ArtworkDialogSelect(ArtworkDialogBase):
    """Dialog for selecting artwork from multiple options with thumbnail preview."""

    ARTWORK_LIST = 100
    BUTTON_SKIP = 201
    BUTTON_CANCEL = 202
    BUTTON_MULTIART = 203
    BUTTON_CHANGE_LANGUAGE = 204
    BUTTON_SORT = 205
    BUTTON_SOURCE_PREF = 206

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = kwargs.get('title', '')
        self.art_type = kwargs.get('art_type', '')
        self.available_art = kwargs.get('available_art', [])
        self.media_type = kwargs.get('media_type', '')
        self.year = kwargs.get('year', '')
        self.current_url = kwargs.get('current_url', '')
        self.dbid = kwargs.get('dbid', 0)
        self.test_mode = kwargs.get('test_mode', False)
        self.review_mode = kwargs.get('review_mode', 'missing')

        self.selected_index = None
        self.result = None
        self.queued_multiart = None

        self.full_artwork_list = kwargs.get('full_artwork_list', [])
        self.current_language = None
        self.available_languages = []
        self.sort_mode = 'popularity'
        self.source_pref = 'all'

    def onInit(self):
        """Called when dialog opens."""
        from lib.artwork.utilities import get_available_languages

        if not self.full_artwork_list:
            self.full_artwork_list = self.available_art

        self.available_languages = get_available_languages(self.full_artwork_list)

        self.setProperty('heading', self.title)
        self.setProperty('year', self.year)
        self.setProperty('mediatype', self.media_type)
        self.setProperty('arttype', self.art_type.lower())
        art_layout = ARTLAYOUT_MAP.get(self.art_type.lower(), '')
        if self.art_type.lower() == 'thumb' and self.media_type in ('artist', 'album'):
            art_layout = 'square'
        self.setProperty('artlayout', art_layout)
        self.setProperty('hascurrentart', 'true' if self.current_url else 'false')
        self.setProperty('currentarturl',
                         decode_image_url(self.current_url) if self.current_url else '')
        self.setProperty('count_total', str(len(self.full_artwork_list)))
        self.setProperty('show_multiart', 'true' if self.art_type == 'fanart' else 'false')

        available_sources = self._get_available_sources()
        self.setProperty('show_source_button', 'true' if len(available_sources) > 1 else 'false')

        available_resolutions = self._get_available_resolutions()
        self.setProperty('show_sort_button', 'true' if len(available_resolutions) > 1 else 'false')

        self.setProperty('show_multiart', 'true' if self.art_type == 'fanart' else 'false')

        self._resort_artwork()
        self._publish_sort_state()
        self._publish_source_pref_state()

        if self.available_art:
            try:
                self.setFocusId(self.ARTWORK_LIST)
            except Exception:
                try:
                    self.setFocusId(self.BUTTON_SKIP)
                except Exception:
                    pass
        elif self.full_artwork_list:
            # Filtered list empty but artwork exists; focus language change
            try:
                self.setFocusId(self.BUTTON_CHANGE_LANGUAGE)
            except Exception:
                try:
                    self.setFocusId(self.BUTTON_SKIP)
                except Exception:
                    pass
        else:
            try:
                self.setFocusId(self.BUTTON_SKIP)
            except Exception:
                pass

    def _populate_artwork_list(self) -> None:
        """Populate list with available artwork options using batch operation."""
        try:
            control = self.getControl(self.ARTWORK_LIST)
        except Exception:
            return

        normalized_current = self._normalize_url(self.current_url) if self.current_url else None

        items = []
        for idx, art_info in enumerate(self.available_art):
            item = self.create_artwork_listitem(art_info, idx)
            if normalized_current:
                art_url = art_info.get('url', '')
                normalized_art = self._normalize_url(art_url) if art_url else ''
                if normalized_current == normalized_art:
                    item.setProperty('is_current', 'true')
            items.append(item)

        self.populate_list_batch(control, items)

    def onClick(self, controlId):
        """Handle button/list clicks."""
        if controlId == self.ARTWORK_LIST:
            self._select_current()

        elif controlId == self.BUTTON_SKIP:
            self.result = 'skip'
            self.close()

        elif controlId == self.BUTTON_CANCEL:
            self.result = None
            self.close()

        elif controlId == self.BUTTON_MULTIART:
            self._launch_multiart()

        elif controlId == self.BUTTON_CHANGE_LANGUAGE:
            self._show_language_picker()

        elif controlId == self.BUTTON_SORT:
            self._toggle_sort_mode()

        elif controlId == self.BUTTON_SOURCE_PREF:
            self._toggle_source_pref()

    def onAction(self, action):
        """Handle keyboard/remote actions."""
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448):
            self.result = None
            self.close()

    def _select_current(self) -> None:
        """Select currently focused artwork."""
        try:
            control = self.getControl(self.ARTWORK_LIST)
            item = control.getSelectedItem()  # type: ignore[attr-defined]
            if not item:
                return

            self.selected_index = int(item.getProperty('index'))
            self.result = 'selected'
            self.close()

        except Exception as e:
            log("Artwork", f"Error selecting artwork: {str(e)}", xbmc.LOGERROR)

    def _launch_multiart(self) -> None:
        """Launch the multi-art dialog; queues its result instead of closing, applied when the main
        dialog closes."""
        if self.art_type != 'fanart':
            return

        if not self.dbid and not self.test_mode:
            log("Artwork", "Cannot launch multi-art - no dbid provided", xbmc.LOGWARNING)
            return

        result = show_multiart_dialog(
            media_type=self.media_type,
            dbid=self.dbid,
            title=self.title,
            art_type='fanart',
            test_mode=self.test_mode
        )

        if result:
            self.queued_multiart = result
            self.setProperty('multiart_queued', 'true')

    def _show_language_picker(self) -> None:
        """Show dialog to select language filter."""
        from lib.artwork.utilities import get_language_display_name
        from lib.kodi.utilities import get_preferred_language_code, normalize_language_tag

        is_filtered = len(self.available_art) != len(self.full_artwork_list)
        # Show picker only if multiple languages exist or a filter is active (needs an All option)
        if not self.available_languages or (len(self.available_languages) <= 1 and not is_filtered):
            return

        def count_language(lang: str) -> int:
            return sum(1 for art in self.full_artwork_list
                       if normalize_language_tag(art.get('language')) == lang)

        preferred_lang = get_preferred_language_code()
        is_filtered = len(self.available_art) != len(self.full_artwork_list)

        sorted_languages = []
        other_languages = []

        for lang in self.available_languages:
            if lang == preferred_lang:
                continue
            if lang == '':
                continue
            other_languages.append((lang, count_language(lang)))

        other_languages.sort(key=lambda x: x[1], reverse=True)

        if preferred_lang in self.available_languages:
            sorted_languages.append(preferred_lang)

        if '' in self.available_languages:
            sorted_languages.append('')

        sorted_languages.extend([lang for lang, _ in other_languages])

        # Show "All images" only if it would combine multiple languages
        if is_filtered and len(sorted_languages) > 1:
            sorted_languages.append('all')

        labels = []
        for lang in sorted_languages:
            if lang == 'all':
                labels.append(f"All images ({len(self.full_artwork_list)})")
            else:
                count = count_language(lang)
                display = "Text-free" if lang == '' else get_language_display_name(lang)
                labels.append(f"{display} ({count})")

        selected = show_select(ADDON.getLocalizedString(32554), labels)
        if selected < 0:
            return

        new_language = sorted_languages[selected]
        # Apply even if unchanged - switches from art-type filtering to simple filtering
        if new_language == 'all':
            self.current_language = 'all'
        else:
            self.current_language = new_language
        self._resort_artwork()

    def _resort_artwork(self) -> None:
        """Re-sort and filter artwork from full list, then refresh UI."""
        from lib.artwork.utilities import sort_artwork_by_popularity
        from lib.kodi.utilities import normalize_language_tag

        if self.current_language == 'all':
            filtered = self.full_artwork_list
        elif self.current_language is not None:
            # Explicit language choice: simple filter, skip art-type rules
            filtered = [
                art for art in self.full_artwork_list
                if normalize_language_tag(art.get('language')) == self.current_language
            ]
        else:
            # Initial load: use art-type-aware filtering
            from lib.artwork.utilities import filter_artwork_by_language
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
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        """Update UI properties and repopulate list without filtering."""
        from lib.artwork.utilities import get_language_display_name
        from lib.kodi.utilities import get_preferred_language_code

        self.setProperty('count_filtered', str(len(self.available_art)))

        try:
            prefer_fanart_language = KodiSettings.prefer_fanart_language()
        except Exception:
            prefer_fanart_language = False

        is_fanart_no_lang_filter = self.art_type == 'fanart' and not prefer_fanart_language

        if self.current_language == 'all':
            language_display = 'All images'
            language_short = 'all'
        elif self.current_language is not None:
            language_display = get_language_display_name(self.current_language)
            language_short = self.current_language
        elif is_fanart_no_lang_filter:
            language_display = 'Text-free'
            language_short = ''
        else:
            preferred = get_preferred_language_code()
            language_display = get_language_display_name(preferred)
            language_short = preferred

        if len(self.available_art) != len(self.full_artwork_list):
            if is_fanart_no_lang_filter and self.current_language is None:
                count_text = (f"{len(self.available_art)} of {len(self.full_artwork_list)} "
                              "available (Text-free)")
            else:
                count_text = (f"{len(self.available_art)} of {len(self.full_artwork_list)} "
                              f"available ({language_display})")
        else:
            count_text = f"{len(self.full_artwork_list)} available"
        self.setProperty('count', count_text)
        self.setProperty('language', language_display)
        self.setProperty('language_short', language_short)

        show_lang_button = (len(self.available_languages) > 1
                            or len(self.available_art) != len(self.full_artwork_list))
        self.setProperty('show_change_language', 'true' if show_lang_button else 'false')

        self._populate_artwork_list()

def show_artwork_selection_dialog(
    title: str,
    art_type: str,
    available_art: List[dict],
    full_artwork_list: Optional[List[dict]] = None,
    media_type: str = '',
    year: str = '',
    current_url: str = '',
    dbid: int = 0,
    test_mode: bool = False,
    review_mode: str = 'missing'
) -> Tuple[str, Optional[dict], Optional[dict]]:
    """Show the artwork selection dialog; returns (action, artwork, queued_multiart) with action
    'selected'/'skip'/'cancel'."""
    # Skip only if no artwork exists at all, not just filtered down to empty
    if not available_art and not full_artwork_list:
        return ('skip', None, None)

    addon_path = ADDON.getAddonInfo('path')

    dialog = ArtworkDialogSelect(
        'script.skin.info.service-ArtworkSelection.xml',
        addon_path,
        'default',
        '1080i',
        title=title,
        art_type=art_type,
        available_art=available_art,
        full_artwork_list=full_artwork_list or available_art,
        media_type=media_type,
        year=year,
        current_url=current_url,
        dbid=dbid,
        test_mode=test_mode,
        review_mode=review_mode
    )

    dialog.doModal()
    result = dialog.result
    selected_index = dialog.selected_index
    queued_multiart = dialog.queued_multiart
    # selected_index is only valid against the dialog's copy; its language filter/sort reorders
    # the list
    final_art_list = dialog.available_art
    del dialog

    if result == 'selected' and selected_index is not None:
        return ('selected', final_art_list[selected_index], queued_multiart)
    elif result == 'skip':
        return ('skip', None, queued_multiart)
    else:
        return ('cancel', None, queued_multiart)

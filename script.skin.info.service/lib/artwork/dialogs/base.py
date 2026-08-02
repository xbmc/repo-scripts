"""Base dialog class with shared artwork functionality"""

from __future__ import annotations

from typing import List
import xbmcgui
from lib.artwork.utilities import get_language_display_name
from lib.kodi.client import decode_image_url, ADDON


class ArtworkDialogBase(xbmcgui.WindowXMLDialog):
    """Base class for artwork dialogs.

    Subclasses must define `BUTTON_SORT`, `BUTTON_SOURCE_PREF` control IDs and
    state vars `full_artwork_list`, `sort_mode`, `source_pref`, plus implement
    `_resort_artwork()`.
    """

    # Placeholders so subclass-supplied attrs typecheck for the helpers below
    BUTTON_SORT: int = 0
    BUTTON_SOURCE_PREF: int = 0
    full_artwork_list: list = []
    sort_mode: str = 'popularity'
    source_pref: str = 'all'

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison; collapses fanart.tv paths to filename only."""
        if not url:
            return ''
        decoded = decode_image_url(url)
        if 'assets.fanart.tv' in decoded:
            return decoded.split('/')[-1]
        return decoded

    def _get_available_sources(self) -> set:
        """Get set of unique sources in the full artwork list."""
        sources = set()
        for art in self.full_artwork_list:
            source = art.get('source', '').lower()
            if source in ('tmdb', 'fanart.tv', 'fanarttv'):
                sources.add('tmdb' if source == 'tmdb' else 'fanart')
        return sources

    def _get_available_resolutions(self) -> set:
        """Get set of unique resolutions in the full artwork list."""
        resolutions = set()
        for art in self.full_artwork_list:
            width = art.get('width')
            height = art.get('height')
            if width and height:
                resolutions.add((width, height))
        return resolutions

    def _toggle_sort_mode(self) -> None:
        """Toggle between popularity and resolution sort modes."""
        self.sort_mode = 'resolution' if self.sort_mode == 'popularity' else 'popularity'
        self._resort_artwork()
        self._publish_sort_state()

    def _publish_sort_state(self) -> None:
        """Publish sort state for the XML to label itself; skins own presentation."""
        self.setProperty(
            'sort_label',
            ADDON.getLocalizedString(32657 if self.sort_mode == 'popularity' else 32658))
        self.setProperty('sort_mode', self.sort_mode)

    def _toggle_source_pref(self) -> None:
        """Toggle between source filters: all -> tmdb -> fanart -> all."""
        if self.source_pref == 'all':
            self.source_pref = 'tmdb'
        elif self.source_pref == 'tmdb':
            self.source_pref = 'fanart'
        else:
            self.source_pref = 'all'
        self._resort_artwork()
        self._publish_source_pref_state()

    _SOURCE_PREF_LABELS = {'all': 32132, 'tmdb': 32133, 'fanart': 32134}

    def _publish_source_pref_state(self) -> None:
        """Publish source filter state for the XML to label itself; skins own presentation."""
        string_id = self._SOURCE_PREF_LABELS.get(self.source_pref, 32134)
        self.setProperty('source_label', ADDON.getLocalizedString(string_id))
        self.setProperty('source_pref', self.source_pref)

    def _resort_artwork(self) -> None:
        """Subclasses re-sort `full_artwork_list` by sort_mode/source_pref/language."""
        raise NotImplementedError

    def create_artwork_listitem(
        self,
        art_info: dict,
        index: int
    ) -> xbmcgui.ListItem:
        """Create a ListItem from an artwork info dict, with properties for display in the dialog
        skin XML."""
        url = art_info.get('url', '')
        preview = art_info.get('previewurl', url)
        width = art_info.get('width', 0)
        height = art_info.get('height', 0)
        language = art_info.get('language', '')
        season = art_info.get('season', '')
        source = art_info.get('source', '')

        label = f"Option {index + 1}"

        item = xbmcgui.ListItem(label=label)
        item.setArt({'thumb': preview, 'icon': preview})
        item.setProperty('fullurl', url)
        item.setProperty('index', str(index))

        if width:
            item.setProperty('width', str(width))
        if height:
            item.setProperty('height', str(height))
        if width and height:
            item.setProperty('dimensions', f"{width}x{height}")
        if language:
            item.setProperty('language_short', language)
            item.setProperty('language', get_language_display_name(language))
        if season:
            item.setProperty('season', str(season))
        if source:
            item.setProperty('source', source)

        return item

    def populate_list_batch(self, control, items: List[xbmcgui.ListItem]) -> None:
        """Batch-add items via addItems(), faster than looping addItem()."""
        control.reset()
        if items:
            control.addItems(items)

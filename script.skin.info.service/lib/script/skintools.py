"""Skinner tools to preview the artwork-selection and multi-art dialogs with mock data via
RunScript."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
import xbmcgui

_ART_TYPES = [
    'poster',
    'fanart',
    'clearlogo',
    'clearart',
    'landscape',
    'banner',
    'characterart',
    'discart',
    'keyart',
    'thumb',
]


def _select_art_type_menu(dialog_type: str, preselect: int = 0) -> tuple[Optional[str], int]:
    """Prompt for art type. Returns `(art_type_or_None_on_cancel, selected_index)`."""
    dialog = xbmcgui.Dialog()
    art_labels = [art.capitalize() for art in _ART_TYPES]

    selected = dialog.select(
        f'Select Art Type for {dialog_type.capitalize()} Dialog Test',
        art_labels,  # type: ignore[arg-type]
        preselect=preselect
    )

    if selected < 0:
        return None, -1

    return _ART_TYPES[selected], selected


def _loop_with_art_menu(dialog_label: str, art_type: Optional[str], runner) -> None:
    """Show the art-type picker when `art_type` is None and call `runner(art_type)`; loops
    in menu mode."""
    show_menu = art_type is None
    last_selected_index = 0

    while True:
        if show_menu:
            art_type, last_selected_index = _select_art_type_menu(dialog_label, last_selected_index)
            if art_type is None:
                return

        if art_type is None:
            return

        runner(art_type)

        if not show_menu:
            return


def test_artwork_selection_dialog(art_type: Optional[str] = None) -> None:
    """Skinner test: artwork-selection dialog with mock data; None shows art-type menu + loops."""
    from lib.artwork.dialogs.select import show_artwork_selection_dialog
    from lib.kodi.client import log

    def _run(art_type: str) -> None:
        log("General", f"Skinner Test: Opening artwork selection dialog for art_type={art_type}")
        mock_art_items = _generate_mock_art_items(art_type, count=12)
        result = show_artwork_selection_dialog(
            title='Test Movie (2024)',
            art_type=art_type,
            available_art=mock_art_items,
            media_type='movie',
            year='2024',
            current_url='https://image.tmdb.org/t/p/original/current_artwork.jpg',
            dbid=1,
            test_mode=True,
        )
        log("General", f"Skinner Test: Dialog result = {result}")

    _loop_with_art_menu('artwork', art_type, _run)


def test_multiart_dialog(art_type: Optional[str] = None) -> None:
    """Skinner test: open multi-art dialog with mock data. None shows art-type menu + loops."""
    from lib.artwork.dialogs.multi import show_multiart_dialog
    from lib.kodi.client import log

    def _run(art_type: str) -> None:
        log("General", f"Skinner Test: Opening multi-art dialog for art_type={art_type}")
        result = show_multiart_dialog(
            media_type='movie',
            dbid=1,
            title='Test Movie (2024)',
            art_type=art_type,
            test_mode=True,
        )
        log("General", f"Skinner Test: Multi-art dialog result = {result}")

    _loop_with_art_menu('multiart', art_type, _run)


def _generate_mock_art_items(art_type: str, count: int = 12) -> List[Dict[str, Any]]:
    """Produce `count` mock art-item dicts for dialog testing (uses bundled test images)."""
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

    image_file, dimensions = art_type_map.get(
        art_type.lower(), ('artwork_test_poster.png', (1000, 1500))
    )
    test_image = xbmcvfs.translatePath(
        f'special://home/addons/script.skin.info.service/resources/skins/default/'
        f'media/artwork_test/{image_file}'
    )

    mock_items = []

    sources = ['tmdb', 'fanarttv', 'tmdb', 'fanarttv']
    languages = ['en', 'en', 'es', 'fr', 'de', None, None, None]

    for i in range(count):
        source = sources[i % len(sources)]
        language = languages[i % len(languages)]

        item = {
            'url': test_image,
            'preview_url': test_image,
            'previewurl': test_image,
            'source': source,
            'rating': 8.5 - (i * 0.3),
            'votes': 1000 - (i * 50),
            'language': language,
            'width': dimensions[0],
            'height': dimensions[1],
        }

        mock_items.append(item)

    return mock_items

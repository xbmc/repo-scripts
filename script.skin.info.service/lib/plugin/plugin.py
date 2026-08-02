"""Plugin entry point. Parses `?action=` and dispatches via `_HANDLERS`."""
from __future__ import annotations

import sys
from urllib.parse import parse_qs
import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import ADDON, log


def _handle_root_menu(handle: int) -> None:
    """Show root menu with Tools, Search, and Widgets folders."""
    items = [
        (ADDON.getLocalizedString(32530), "plugin://script.skin.info.service/?action=exec_tools",
         "DefaultAddonProgram.png", False),
        (ADDON.getLocalizedString(32614), "plugin://script.skin.info.service/?action=menu_search",
         "DefaultAddonsSearch.png", True),
        (ADDON.getLocalizedString(32615), "plugin://script.skin.info.service/?action=menu_widgets",
         "DefaultAddonVideo.png", True),
    ]

    for label, path, icon, is_folder in items:
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({'icon': icon, 'thumb': icon})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=is_folder)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_search_menu(handle: int) -> None:
    """Show search submenu."""
    items = [
        (ADDON.getLocalizedString(32616),
         "plugin://script.skin.info.service/?action=exec_search&dbtype=movie",
         "DefaultMovies.png"),
        (ADDON.getLocalizedString(32617),
         "plugin://script.skin.info.service/?action=exec_search&dbtype=tv",
         "DefaultTVShows.png"),
        (ADDON.getLocalizedString(32618),
         "plugin://script.skin.info.service/?action=exec_search&dbtype=person",
         "DefaultActor.png"),
    ]

    for label, path, icon in items:
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({'icon': icon, 'thumb': icon})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=False)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_widgets_menu(handle: int) -> None:
    """Show widgets submenu."""
    items = [
        (ADDON.getLocalizedString(32619), "plugin://script.skin.info.service/?action=discover_menu",
         "DefaultAddonVideo.png", True),
        (ADDON.getLocalizedString(32620), "plugin://script.skin.info.service/?action=next_up",
         "DefaultInProgressShows.png", True),
        (ADDON.getLocalizedString(32621),
         "plugin://script.skin.info.service/?action=recent_episodes_grouped",
         "DefaultRecentlyAddedEpisodes.png", True),
        (ADDON.getLocalizedString(32622), "plugin://script.skin.info.service/?action=menu_seasonal",
         "DefaultYear.png", True),
        (ADDON.getLocalizedString(32623),
         "plugin://script.skin.info.service/?action=recommended&dbtype=movie",
         "DefaultMovies.png", True),
        (ADDON.getLocalizedString(32624),
         "plugin://script.skin.info.service/?action=recommended&dbtype=tvshow",
         "DefaultTVShows.png", True),
    ]

    for label, path, icon, is_folder in items:
        li = xbmcgui.ListItem(label, offscreen=True)
        li.setArt({'icon': icon, 'thumb': icon})
        xbmcplugin.addDirectoryItem(handle, path, li, isFolder=is_folder)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


_SEASONAL_MENU = [
    (32642, "christmas"), (32643, "halloween"), (32644, "valentines"),
    (32645, "thanksgiving"), (32646, "starwars"), (32647, "startrek"),
    (32648, "newyear"), (32649, "easter"), (32650, "independence"),
]


def _handle_seasonal_menu(handle: int) -> None:
    """Show seasonal submenu (one entry per SEASONAL_TAGS key)."""
    for string_id, key in _SEASONAL_MENU:
        li = xbmcgui.ListItem(ADDON.getLocalizedString(string_id), offscreen=True)
        li.setArt({'icon': "DefaultYear.png", 'thumb': "DefaultYear.png"})
        xbmcplugin.addDirectoryItem(
            handle, f"plugin://script.skin.info.service/?action=seasonal&season={key}",
            li, isFolder=True)

    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _wrap_menu(menu_handler):
    """Wrap a `(handle)` menu handler so it accepts the `(handle, params)` dispatch signature."""
    def wrapped(handle: int, _params: dict) -> None:
        menu_handler(handle)
    return wrapped


def _handle_exec_tools(handle: int, _params: dict) -> None:
    xbmcplugin.endOfDirectory(handle, succeeded=False)
    xbmc.executebuiltin('RunScript(script.skin.info.service,action=tools)')


def _handle_exec_search(handle: int, params: dict) -> None:
    dbtype = params.get('dbtype', ['movie'])[0]
    xbmcplugin.endOfDirectory(handle, succeeded=False)
    xbmc.executebuiltin(f'RunScript(script.skin.info.service,action=tmdb_search,dbtype={dbtype})')


def _handle_path_stats(handle: int, params: dict) -> None:
    from lib.plugin.pathstats import handle_path_stats
    handle_path_stats(handle, params)


def _handle_wrap(handle: int, params: dict) -> None:
    from lib.plugin.wrap import handle_wrap
    handle_wrap(handle, params)


def _handle_online(handle: int, params: dict) -> None:
    from lib.plugin.online import handle_online
    handle_online(handle, params)


def _handle_get_cast(handle: int, params: dict) -> None:
    from lib.plugin.cast import handle_get_cast
    handle_get_cast(handle, params)


def _handle_get_cast_player(handle: int, params: dict) -> None:
    from lib.plugin.cast import handle_get_cast_player
    handle_get_cast_player(handle, params)


def _handle_discover_menu_action(handle: int, params: dict) -> None:
    from lib.plugin.widgets.discovery import handle_discover_menu
    handle_discover_menu(handle, params)


def _handle_discover_movies_menu_action(handle: int, params: dict) -> None:
    from lib.plugin.widgets.discovery import handle_discover_movies_menu
    handle_discover_movies_menu(handle, params)


def _handle_discover_tvshows_menu_action(handle: int, params: dict) -> None:
    from lib.plugin.widgets.discovery import handle_discover_tvshows_menu
    handle_discover_tvshows_menu(handle, params)


def _handle_next_up(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_next_up
    handle_next_up(handle, params)


def _handle_recent_episodes_grouped(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_recent_episodes_grouped
    handle_recent_episodes_grouped(handle, params)


def _handle_by_actor(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_by_actor
    handle_by_actor(handle, params)


def _handle_by_director(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_by_director
    handle_by_director(handle, params)


def _handle_similar(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_similar
    handle_similar(handle, params)


def _handle_recommended(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_recommended
    handle_recommended(handle, params)


def _handle_tmdb_recommendations(handle: int, params: dict) -> None:
    from lib.plugin.widgets.discovery import handle_tmdb_recommendations
    handle_tmdb_recommendations(handle, params)


def _handle_seasonal(handle: int, params: dict) -> None:
    from lib.plugin.widgets.video import handle_seasonal
    handle_seasonal(handle, params)


def _handle_similar_artists(handle: int, params: dict) -> None:
    from lib.plugin.widgets.music import handle_similar_artists
    handle_similar_artists(handle, params)


def _handle_artist_albums(handle: int, params: dict) -> None:
    from lib.plugin.widgets.music import handle_artist_albums
    handle_artist_albums(handle, params)


def _handle_artist_musicvideos(handle: int, params: dict) -> None:
    from lib.plugin.widgets.music import handle_artist_musicvideos
    handle_artist_musicvideos(handle, params)


def _handle_genre_artists(handle: int, params: dict) -> None:
    from lib.plugin.widgets.music import handle_genre_artists
    handle_genre_artists(handle, params)


def _handle_letter_jump(handle: int, params: dict) -> None:
    from lib.skin.container import handle_letter_jump_list
    handle_letter_jump_list(handle, params)


def _handle_jump_letter_exec(handle: int, params: dict) -> None:
    from lib.skin.container import handle_letter_jump_exec
    handle_letter_jump_exec(handle, params)


def _handle_person_info(handle: int, params: dict) -> None:
    from lib.plugin.person import handle_person_info
    handle_person_info(handle, params)


def _handle_person_library(handle: int, params: dict) -> None:
    from lib.plugin.person import handle_person_library
    handle_person_library(handle, params)


def _handle_tmdb_details(handle: int, params: dict) -> None:
    from lib.plugin.person import handle_tmdb_details
    handle_tmdb_details(handle, params)


def _handle_crew_list(handle: int, params: dict) -> None:
    from lib.plugin.person import handle_crew_list
    handle_crew_list(handle, params)


def _handle_creators(handle: int, params: dict) -> None:
    params['crew_type'] = ['creator']
    _handle_crew_list(handle, params)


def _handle_directors(handle: int, params: dict) -> None:
    params['crew_type'] = ['director']
    _handle_crew_list(handle, params)


def _handle_writers(handle: int, params: dict) -> None:
    params['crew_type'] = ['writer']
    _handle_crew_list(handle, params)


_HANDLERS = {
    'menu_search': _wrap_menu(_handle_search_menu),
    'menu_widgets': _wrap_menu(_handle_widgets_menu),
    'menu_seasonal': _wrap_menu(_handle_seasonal_menu),
    'exec_tools': _handle_exec_tools,
    'exec_search': _handle_exec_search,
    'get_cast': _handle_get_cast,
    'get_cast_player': _handle_get_cast_player,
    'path_stats': _handle_path_stats,
    'wrap': _handle_wrap,
    'discover_menu': _handle_discover_menu_action,
    'discover_movies_menu': _handle_discover_movies_menu_action,
    'discover_tvshows_menu': _handle_discover_tvshows_menu_action,
    'next_up': _handle_next_up,
    'recent_episodes_grouped': _handle_recent_episodes_grouped,
    'by_actor': _handle_by_actor,
    'by_director': _handle_by_director,
    'similar': _handle_similar,
    'recommended': _handle_recommended,
    'tmdb_recommendations': _handle_tmdb_recommendations,
    'seasonal': _handle_seasonal,
    'similar_artists': _handle_similar_artists,
    'artist_albums': _handle_artist_albums,
    'artist_musicvideos': _handle_artist_musicvideos,
    'genre_artists': _handle_genre_artists,
    'letter_jump': _handle_letter_jump,
    'jump_letter_exec': _handle_jump_letter_exec,
    'person_info': _handle_person_info,
    'person_library': _handle_person_library,
    'tmdb_details': _handle_tmdb_details,
    'online': _handle_online,
    'creators': _handle_creators,
    'directors': _handle_directors,
    'writers': _handle_writers,
    'crew': _handle_crew_list,
}


def main() -> None:
    """Plugin entry point: parse `?action=...` from `sys.argv[2]` and dispatch to its handler."""
    try:
        handle = int(sys.argv[1])
    except (ValueError, IndexError) as e:
        log("Plugin", f"Invalid handle provided: {e}", xbmc.LOGERROR)
        return

    if len(sys.argv) < 3 or not sys.argv[2] or sys.argv[2] == "?":
        _handle_root_menu(handle)
        return

    query_string = sys.argv[2]
    if query_string.startswith("?"):
        query_string = query_string[1:]

    import html
    query_string = html.unescape(query_string)
    params = parse_qs(query_string)
    action = params.get('action', [''])[0]

    handler = _HANDLERS.get(action)
    if handler is not None:
        handler(handle, params)
        return

    from lib.plugin.widgets.discovery import WIDGET_REGISTRY, handle_discover
    if action in WIDGET_REGISTRY:
        handle_discover(handle, action, params)
    else:
        from lib.plugin.dbid import handle_dbid_query
        handle_dbid_query(handle, params)


if __name__ == "__main__":
    main()

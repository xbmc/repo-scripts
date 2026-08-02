"""Entry point for script.skin.info.service."""
import sys
import xbmc
from typing import Callable, Dict, Optional
from lib.kodi.client import log
from lib.kodi.utilities import set_prop, clear_prop, resolve_infolabel
from lib.infrastructure.dialogs import DialogProgress


def _set_window_prop(key: str, value: str, window: str) -> None:
    """Set a window property. Routes home-window writes through the cached helper to avoid
    desync with service-layer writes that share the same property name."""
    if window == "home":
        set_prop(key, value)
    else:
        xbmc.executebuiltin(f'SetProperty({key},{value},{window})')


def _clear_window_prop(key: str, window: str) -> None:
    """Clear a window property. Routes home-window clears through the cached helper."""
    if window == "home":
        clear_prop(key)
    else:
        xbmc.executebuiltin(f'ClearProperty({key},{window})')


def _clear_blur_properties(blur_key: str, orig_key: str, window: str) -> None:
    """Clear both blur properties on `window`."""
    _clear_window_prop(blur_key, window)
    _clear_window_prop(orig_key, window)


def _blur_image_and_set_property(source: str, prefix: str = "",
                                 radius: Optional[int] = None,
                                 window: str = "home") -> None:
    """Blur `source` and set `SkinInfo.[prefix.]BlurredImage`/`.Original` on `window`;
    empty `source` clears them."""
    prop_base = f"SkinInfo.{prefix}." if prefix else "SkinInfo."
    blur_key = f"{prop_base}BlurredImage"
    orig_key = f"{prop_base}BlurredImage.Original"

    try:
        if not source:
            _clear_blur_properties(blur_key, orig_key, window)
            return

        if radius is None:
            blur_radius_str = xbmc.getInfoLabel("Skin.String(SkinInfo.BlurRadius)") or "40"
            try:
                radius = int(blur_radius_str)
                if radius < 1:
                    radius = 40
            except (ValueError, TypeError):
                radius = 40

        from lib.service import blur
        blurred_path = blur.blur_image(source, radius)

        if blurred_path:
            log("Blur", f"Setting {blur_key} on window {window} to: {blurred_path}", xbmc.LOGDEBUG)
            _set_window_prop(blur_key, blurred_path, window)
            _set_window_prop(orig_key, source, window)
        else:
            log("Blur", "Blur failed, clearing properties", xbmc.LOGDEBUG)
            _clear_blur_properties(blur_key, orig_key, window)

    except Exception as e:
        log("Blur", f"RunScript blur failed: {e}", xbmc.LOGERROR)
        _clear_blur_properties(blur_key, orig_key, window)


def _parse_args(start_index: int) -> dict:
    """Parse `sys.argv[start_index:]` with both positional and `key=value` support."""
    args = {}
    positional_index = 0

    for i in range(start_index, len(sys.argv)):
        arg = sys.argv[i]

        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key.strip()] = value.strip()
        else:
            args[positional_index] = arg
            positional_index += 1

    return args


def _handle_colorpicker(args: dict) -> None:
    from lib.skin.colorpicker import colorpicker
    colorpicker(**args)


def _handle_blur(args: dict) -> None:
    source = resolve_infolabel(args.get('source', ""))
    prefix = args.get('prefix', "Custom")
    window = args.get('window_id', "home")
    radius = args.get('radius')
    if radius is not None:
        try:
            radius = int(radius)
        except (ValueError, TypeError):
            radius = None
    _blur_image_and_set_property(source, prefix, radius, window)


def _handle_split_string(args: dict) -> None:
    from lib.skin.strings import split_string
    string = resolve_infolabel(args.get('string', ""))
    split_string(
        string, args.get('separator', "|"), args.get('prefix', ''), args.get('window', 'home'))


def _handle_urlencode(args: dict) -> None:
    from lib.skin.strings import urlencode
    string = resolve_infolabel(args.get('string', ""))
    urlencode(string, args.get('prefix', ''), args.get('window', 'home'))


def _handle_urldecode(args: dict) -> None:
    from lib.skin.strings import urldecode
    string = resolve_infolabel(args.get('string', ""))
    urldecode(string, args.get('prefix', ''), args.get('window', 'home'))


def _handle_math(args: dict) -> None:
    from lib.skin.math import evaluate_math
    evaluate_math(args.get('expression', ""), args.get('prefix', ''), args.get('window', 'home'))


def _handle_copy_item(args: dict) -> None:
    from lib.skin.properties import copy_container_item
    copy_container_item(
        args.get('container', ""), args.get('infolabels', ''), args.get('artwork', ''),
        args.get('prefix', ''), args.get('window', 'home'),
    )


def _handle_container_labels(args: dict) -> None:
    from lib.skin.properties import aggregate_container_labels
    aggregate_container_labels(
        args.get('container', ""), args.get('infolabel', ""),
        args.get('separator', ' / '), args.get('prefix', 'SkinInfo'), args.get('window', 'home'),
    )


def _handle_refresh_counter(args: dict) -> None:
    from lib.skin.properties import refresh_counter
    refresh_counter(args.get('uid', ""), args.get('prefix', 'SkinInfo'))


def _handle_file_exists(args: dict) -> None:
    from lib.skin.files import check_file_exists
    check_file_exists(
        args.get('paths', ""), args.get('separator', '|'),
        args.get('prefix', ''), args.get('window', 'home'),
    )


def _handle_json(args: dict) -> None:
    from lib.skin.json import execute_from_args
    execute_from_args(args)


def _handle_container_move(args: dict) -> None:
    from lib.skin.container import move_to_position
    move_to_position(
        args.get('main_focus', ""), args.get('main_position'), args.get('main_action'),
        args.get('next_focus'), args.get('next_position'), args.get('next_action'),
    )


def _handle_get_setting(args: dict) -> None:
    from lib.skin.settings import get_setting
    get_setting(args.get('setting', ""), args.get('prefix', 'SkinInfo'), args.get('window', 'home'))


def _handle_set_setting(args: dict) -> None:
    from lib.skin.settings import set_setting
    setting = args.get('setting', "")
    value = args.get('value', "")
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif value.isdigit():
        value = int(value)
    noconfirm = args.get('noconfirm', 'false').lower() == 'true'
    set_setting(setting, value, noconfirm)


def _handle_toggle_setting(args: dict) -> None:
    from lib.skin.settings import toggle_setting
    noconfirm = args.get('noconfirm', 'false').lower() == 'true'
    toggle_setting(args.get('setting', ""), noconfirm)


def _handle_reset_setting(args: dict) -> None:
    from lib.skin.settings import reset_setting
    noconfirm = args.get('noconfirm', 'false').lower() == 'true'
    reset_setting(args.get('setting', ""), noconfirm)


def _handle_update_library_ratings(args: dict) -> None:
    from lib.rating.menu import initialize_sources
    from lib.rating.updater import update_library_ratings
    media_type = args.get('dbtype', 'movie').lower()
    if media_type not in ("movie", "tvshow", "episode"):
        media_type = "movie"
    use_background = args.get('background', 'true').lower() == 'true'
    update_library_ratings(media_type, initialize_sources(), use_background=use_background)


def _handle_sync_tvshows(_args: dict) -> None:
    from lib.script.sync import run_sync_tvshows
    run_sync_tvshows()


def _handle_playall(args: dict) -> None:
    from lib.skin.playback import playall
    playall(resolve_infolabel(args.get('path', "")))


def _handle_playrandom(args: dict) -> None:
    from lib.skin.playback import playrandom
    playrandom(resolve_infolabel(args.get('path', "")))


def _handle_tools(_args: dict) -> None:
    from lib.script.tools import run_tools
    run_tools()


def _handle_review_artwork(args: dict) -> None:
    from lib.artwork.manager import run_art_fetcher_single
    run_art_fetcher_single(args.get('dbid'), args.get('dbtype'))


def _handle_download_artwork(args: dict) -> None:
    from lib.artwork.manager import download_item_artwork
    download_item_artwork(args.get('dbid'), args.get('dbtype'))


def _handle_update_ratings(args: dict) -> None:
    from lib.rating.menu import update_single_item_ratings
    update_single_item_ratings(args.get('dbid'), args.get('dbtype'))


def _handle_edit(args: dict) -> None:
    from lib.editor.menu import run_editor
    run_editor(args.get('dbid'), args.get('dbtype'))


def _handle_export_nfo(args: dict) -> None:
    import xbmcgui
    from lib.kodi.client import ADDON
    from lib.editor.nfo import write_nfo
    from lib.infrastructure.dialogs import show_notification

    dbid = args.get('dbid')
    dbtype = args.get('dbtype')
    if not dbid or dbid == "-1" or not dbtype:
        return

    wrote = write_nfo(dbtype.lower(), int(dbid), forced=True)
    if wrote:
        show_notification(ADDON.getLocalizedString(32029), ADDON.getLocalizedString(32030),
                          xbmcgui.NOTIFICATION_INFO, 3000)
    else:
        show_notification(ADDON.getLocalizedString(32029), ADDON.getLocalizedString(32031),
                          xbmcgui.NOTIFICATION_WARNING, 3000)


def _handle_settings_action(args: dict) -> None:
    from lib.data.api import settings as api_settings
    sub_action = args.get('sub_action')
    provider = args.get('provider')
    if sub_action == "edit_api_key" and provider:
        api_settings.edit_api_key(provider)
    elif sub_action == "test_api_key" and provider:
        api_settings.test_api_key(provider)
    elif sub_action == "clear_api_key" and provider:
        api_settings.clear_api_key(provider)
    elif sub_action == "authorize_trakt":
        api_settings.authorize_trakt()
    elif sub_action == "test_trakt_connection":
        api_settings.test_trakt_connection()
    elif sub_action == "revoke_trakt_authorization":
        api_settings.revoke_trakt_authorization()


def _handle_arttest(args: dict) -> None:
    from lib.script.skintools import test_artwork_selection_dialog
    test_artwork_selection_dialog(args.get('art_type'))


def _handle_multiarttest(args: dict) -> None:
    from lib.script.skintools import test_multiart_dialog
    test_multiart_dialog(args.get('art_type'))


def _handle_person_info(args: dict) -> None:
    from lib.script.person import handle_person_info_action
    handle_person_info_action(args)


def _handle_person_search(args: dict) -> None:
    from lib.script.person import handle_person_search_action
    handle_person_search_action(args)


def _handle_tmdb_search(args: dict) -> None:
    import xbmcgui
    import re
    from lib.data.api.tmdb import ApiTmdb

    media_type = args.get('dbtype', 'movie')
    doneaction = args.get('doneaction', '')
    window = args.get('window', 'home')
    property_name = args.get('property', 'SkinInfo.Search.Details')

    if media_type not in ('movie', 'tv', 'person'):
        log("General", f"tmdb_search: Invalid dbtype '{media_type}'", xbmc.LOGERROR)
        return

    log("General", f"tmdb_search: Opening keyboard for {media_type} search", xbmc.LOGDEBUG)

    keyboard = xbmcgui.Dialog().input(heading=f'Search {media_type.upper()}')
    if not keyboard:
        log("General", "tmdb_search: User cancelled keyboard", xbmc.LOGDEBUG)
        return

    query = keyboard.strip()
    if not query:
        log("General", "tmdb_search: Empty query entered", xbmc.LOGDEBUG)
        return

    year = 0
    year_match = re.search(r':(\d{4})$', query)
    if year_match:
        year = int(year_match.group(1))
        query = query[:year_match.start()].strip()
        log("General", f"tmdb_search: Extracted year={year} from query", xbmc.LOGDEBUG)

    log("General", f"tmdb_search: Searching TMDB for '{query}' (type={media_type}, year={year})",
        xbmc.LOGDEBUG)

    api = ApiTmdb()
    results = api.search(query, media_type, year)

    if not results:
        xbmcgui.Dialog().notification(
            'TMDB Search', 'No results found', xbmcgui.NOTIFICATION_INFO, 3000)
        log("General", f"tmdb_search: No results found for '{query}'", xbmc.LOGDEBUG)
        return

    log("General", f"tmdb_search: Found {len(results)} results", xbmc.LOGDEBUG)

    listitems = []
    for result in results[:20]:
        if media_type == 'movie':
            title = result.get('title', 'Unknown')
            year_str = result.get('release_date', '')[:4] if result.get('release_date') else ''
            label2 = (f"{year_str} - {result.get('overview', '')[:100]}"
                      if year_str else result.get('overview', '')[:100])
            poster = result.get('poster_path', '')
        elif media_type == 'tv':
            title = result.get('name', 'Unknown')
            year_str = result.get('first_air_date', '')[:4] if result.get('first_air_date') else ''
            label2 = (f"{year_str} - {result.get('overview', '')[:100]}"
                      if year_str else result.get('overview', '')[:100])
            poster = result.get('poster_path', '')
        else:
            title = result.get('name', 'Unknown')
            label2 = result.get('known_for_department', '')
            poster = result.get('profile_path', '')

        listitem = xbmcgui.ListItem(label=title, label2=label2, offscreen=True)
        if poster:
            from lib.data.api.utilities import tmdb_image_url
            image_url = tmdb_image_url(poster, 'w500')
            listitem.setArt({'icon': image_url, 'thumb': image_url})

        listitem.setProperty('tmdb_id', str(result.get('id', '')))
        listitems.append(listitem)

    selected_index = xbmcgui.Dialog().select(f'Search Results: {query}', listitems, useDetails=True)

    if selected_index < 0:
        log("General", "tmdb_search: User cancelled selection", xbmc.LOGDEBUG)
        return

    tmdb_id = listitems[selected_index].getProperty('tmdb_id')
    log("General", f"tmdb_search: User selected {media_type} with tmdb_id={tmdb_id}", xbmc.LOGDEBUG)

    xbmc.executebuiltin(f'ClearProperty({property_name},{window})')

    details_url = f"plugin://script.skin.info.service/?action=tmdb_details&type={media_type}&tmdb_id={tmdb_id}"
    xbmc.executebuiltin(f'SetProperty({property_name},{details_url},{window})')

    log("General", f"tmdb_search: Set property {property_name}={details_url}", xbmc.LOGDEBUG)

    if doneaction:
        for builtin in doneaction.split('|'):
            if builtin.strip():
                log("General", f"tmdb_search: Executing builtin: {builtin.strip()}", xbmc.LOGDEBUG)
                xbmc.executebuiltin(builtin.strip())


def _handle_search_library_person(args: dict) -> None:
    import urllib.parse
    import xbmcgui
    from lib.kodi.client import request

    name = urllib.parse.unquote(args.get('name', ''))
    crew = args.get('crew', '')

    if not name:
        log("General", "search_library_person: Missing name", xbmc.LOGERROR)
        return

    if crew and crew not in ('director', 'writer'):
        log("General", f"search_library_person: Invalid crew type '{crew}'", xbmc.LOGERROR)
        return

    field = crew if crew else 'actor'
    if field == 'writer':
        field = 'writers'

    log("General", f"search_library_person: Searching library for {crew or 'actor'} '{name}'",
        xbmc.LOGDEBUG)

    progress = DialogProgress()
    progress.create(xbmc.getLocalizedString(194), name)

    movies = request('VideoLibrary.GetMovies', {
        'filter': {'field': field, 'operator': 'is', 'value': name},
        'properties': ['title', 'year', 'art', 'playcount', 'file'],
        'sort': {'method': 'title', 'order': 'ascending'}
    })

    if field == 'writers':
        tvshows = None
        episodes = None
    else:
        tvshows = request('VideoLibrary.GetTVShows', {
            'filter': {'field': field, 'operator': 'is', 'value': name},
            'properties': ['title', 'year', 'art', 'watchedepisodes', 'episode'],
            'sort': {'method': 'title', 'order': 'ascending'}
        })

        episodes = request('VideoLibrary.GetEpisodes', {
            'filter': {'field': field, 'operator': 'is', 'value': name},
            'properties': ['title', 'showtitle', 'art', 'playcount', 'file'],
            'sort': {'method': 'title', 'order': 'ascending'}
        })

    progress.close()

    items = []

    if movies and 'movies' in movies.get('result', {}):
        for movie in movies['result']['movies']:
            label = movie['title']
            if movie.get('year'):
                label += f" ({movie['year']})"
            items.append({
                'label': f"[{xbmc.getLocalizedString(20338)}] {label}",
                'type': 'movie',
                'id': movie['movieid'],
                'art': movie.get('art', {}),
                'playcount': movie.get('playcount', 0),
                'file': movie.get('file', '')
            })

    if tvshows and 'tvshows' in tvshows.get('result', {}):
        for show in tvshows['result']['tvshows']:
            label = show['title']
            if show.get('year'):
                label += f" ({show['year']})"
            items.append({
                'label': f"[{xbmc.getLocalizedString(20364)}] {label}",
                'type': 'tvshow',
                'id': show['tvshowid'],
                'art': show.get('art', {}),
                'watchedepisodes': show.get('watchedepisodes', 0),
                'episode': show.get('episode', 0)
            })

    if episodes and 'episodes' in episodes.get('result', {}):
        for episode in episodes['result']['episodes']:
            label = f"{episode['title']} ({episode['showtitle']})"
            items.append({
                'label': f"[{xbmc.getLocalizedString(20359)}] {label}",
                'type': 'episode',
                'id': episode['episodeid'],
                'art': episode.get('art', {}),
                'playcount': episode.get('playcount', 0),
                'file': episode.get('file', '')
            })

    if not items:
        xbmcgui.Dialog().ok(xbmc.getLocalizedString(194), xbmc.getLocalizedString(284))
        return

    list_items = []
    for item in items:
        list_item = xbmcgui.ListItem(item['label'], offscreen=True)

        art = item.get('art', {})
        if item['type'] == 'episode' and art.get('thumb'):
            list_item.setArt({'thumb': art['thumb'], 'icon': art['thumb']})
        elif art.get('poster'):
            list_item.setArt({'thumb': art['poster'], 'icon': art['poster']})

        if item['type'] == 'tvshow':
            watched = item.get('watchedepisodes', 0)
            total = item.get('episode', 0)
            if watched > 0 and watched == total:
                list_item.setProperty('overlay', '5')
                list_item.setLabel2(xbmc.getLocalizedString(16102))
        else:
            playcount = item.get('playcount', 0)
            if playcount > 0:
                list_item.setProperty('overlay', '5')
                list_item.setLabel2(xbmc.getLocalizedString(16102))

            video_info = list_item.getVideoInfoTag()
            video_info.setPlaycount(playcount)
            if item.get('file'):
                video_info.setPath(item['file'])

        list_items.append(list_item)

    dialog = xbmcgui.Dialog()
    selected = dialog.select(xbmc.getLocalizedString(283), list_items, useDetails=True)

    if selected >= 0:
        item = items[selected]
        if item['type'] == 'movie':
            xbmc.executebuiltin(f'ActivateWindow(Videos,videodb://movies/titles/{item["id"]},return)')
        elif item['type'] == 'tvshow':
            xbmc.executebuiltin(f'ActivateWindow(Videos,videodb://tvshows/titles/{item["id"]},return)')
        elif item['type'] == 'episode':
            xbmc.executebuiltin(f'ActivateWindow(Videos,videodb://episodes/{item["id"]},return)')


def _handle_online_fetch(args: dict) -> None:
    from lib.service.online import fetch_all_online_data
    from lib.kodi.client import get_item_details
    from lib.data.api.tmdb import ApiTmdb
    from lib.data.database._infrastructure import init_database

    init_database()

    media_type = args.get("dbtype", "")
    dbid = args.get("dbid", "")
    tmdb_id = args.get("tmdb_id", "")
    imdb_id = args.get("imdb_id", "")
    window = args.get("window", "home")
    property_name = args.get("property", "SkinInfo.Online.Content")

    if not media_type:
        log("General", "online_fetch: Missing required parameter 'dbtype'", xbmc.LOGWARNING)
        return

    media_type = media_type.lower().strip()
    if media_type not in ("movie", "tvshow", "episode"):
        log("General", f"online_fetch: Invalid media type '{media_type}'", xbmc.LOGWARNING)
        return

    is_episode = media_type == "episode"

    tvdb_id = ""

    if tmdb_id or imdb_id:
        pass
    elif dbid:
        try:
            dbid_int = int(dbid)
            if dbid_int <= 0:
                raise ValueError("DBID must be positive")
        except (ValueError, TypeError) as e:
            log("General", f"online_fetch: Invalid DBID '{dbid}': {e}", xbmc.LOGWARNING)
            return

        if is_episode:
            episode_details = get_item_details("episode", dbid_int, ["tvshowid"])
            if not episode_details or not episode_details.get("tvshowid"):
                log("General", f"online_fetch: Could not get parent show for episode {dbid}",
                    xbmc.LOGWARNING)
                return
            tvshow_dbid = episode_details["tvshowid"]
            details = get_item_details("tvshow", tvshow_dbid, ["uniqueid"])
        else:
            details = get_item_details(media_type, dbid_int, ["uniqueid"])

        if not details:
            log("General", f"online_fetch: Could not get details for {media_type} {dbid}",
                xbmc.LOGWARNING)
            return

        uniqueid_dict = details.get("uniqueid") or {}
        imdb_id = uniqueid_dict.get("imdb") or ""
        tmdb_id = uniqueid_dict.get("tmdb") or ""
        tvdb_id = uniqueid_dict.get("tvdb") or ""
    else:
        log("General",
            "online_fetch: Missing required parameter - provide dbid, tmdb_id, or imdb_id",
            xbmc.LOGWARNING)
        return

    if is_episode:
        media_type = "tvshow"

    if not imdb_id and not tmdb_id and not tvdb_id:
        log("General", "online_fetch: No valid IDs available", xbmc.LOGWARNING)
        return

    if not tmdb_id:
        tmdb_api = ApiTmdb()
        if imdb_id:
            resolved_id = tmdb_api.find_by_external_id(imdb_id, "imdb_id", media_type)
            if resolved_id and resolved_id.get("id"):
                tmdb_id = str(resolved_id["id"])
        elif tvdb_id and media_type == "tvshow":
            resolved_id = tmdb_api.find_by_external_id(tvdb_id, "tvdb_id", media_type)
            if resolved_id and resolved_id.get("id"):
                tmdb_id = str(resolved_id["id"])

    is_library_item = bool(dbid)
    fetch_all_online_data(media_type, imdb_id, tmdb_id, is_library_item=is_library_item)

    plugin_url = f"plugin://script.skin.info.service/?action=online&dbtype={media_type}"
    if tmdb_id:
        plugin_url += f"&tmdb_id={tmdb_id}"
    if imdb_id:
        plugin_url += f"&imdb_id={imdb_id}"

    log("General", f"online_fetch: Setting {property_name}={plugin_url} on {window}", xbmc.LOGDEBUG)
    xbmc.executebuiltin(f"SetProperty({property_name},{plugin_url},{window})")


def _restore_focus(args: dict, dialog_xml: str) -> None:
    """Focus the `focus` control once its dialog has left the screen.

    A closing dialog lingers a beat, so focusing before it's gone lands on the
    dialog, not the control underneath.
    """
    control_id = args.get('focus', '')
    if not (control_id.isdigit() and int(control_id) > 0):
        return
    monitor = xbmc.Monitor()
    for _ in range(60):
        if not xbmc.getCondVisibility(f'Window.IsVisible({dialog_xml})'):
            break
        if monitor.waitForAbort(0.05):
            return
    xbmc.executebuiltin(f'SetFocus({control_id})')


def _handle_dialog_actor_info(args: dict) -> None:
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        _handle_dialog_actor_info_inner(args)
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialog,true)')
        _restore_focus(args, 'script-skin-info-service-DialogActorInfo.xml')


def _handle_dialog_actor_info_inner(args: dict) -> None:
    from lib.data.api import person as person_api
    from lib.data.database._infrastructure import init_database

    init_database()

    person_id_str = args.get('person_id')
    name = args.get('name', '')
    role = args.get('role', '')
    dbid = args.get('dbid')
    dbtype = args.get('dbtype', 'movie')
    crew = args.get('crew', '')
    separator = args.get('separator', ' / ')
    auto_search = args.get('auto_search', 'true').lower() == 'true'
    online = args.get('online', 'false').lower() == 'true'

    person_id = None
    if person_id_str:
        try:
            person_id = int(person_id_str)
        except (ValueError, TypeError):
            log("General", f"dialog_actor_info: Invalid person_id '{person_id_str}'", xbmc.LOGERROR)
            return

    if not person_id and crew:
        from lib.script.person import resolve_via_crew
        resolved = resolve_via_crew(person_api, name, dbid, dbtype, crew, separator, auto_search)
        if not resolved:
            return
        person_id, name = resolved

    elif not person_id:
        from lib.script.person import resolve_via_actor
        person_id = resolve_via_actor(
            person_api, name, role, dbid, dbtype, auto_search, online,
            args.get('sourceid'), open_window='', set_search_query=False,
        )
        if not person_id:
            return

    from lib.info.dialogs.actor import open_actor_info
    open_actor_info(
        person_id=person_id,
        person_name=name,
    )


def _handle_dialog_image_viewer(args: dict) -> None:
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        _handle_dialog_image_viewer_inner(args)
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialog,true)')
        _restore_focus(args, 'script-skin-info-service-DialogImageViewer.xml')


def _handle_dialog_image_viewer_inner(args: dict) -> None:
    images_path = args.get('images_path', '')
    if not images_path:
        log("General", "dialog_image_viewer: Missing images_path", xbmc.LOGWARNING)
        return

    selected_index_str = args.get('selected_index', '0')
    try:
        selected_index = max(0, int(selected_index_str) - 1)
    except (ValueError, TypeError):
        selected_index = 0

    from lib.info.dialogs.image import open_image_viewer
    open_image_viewer(images_path=images_path, selected_index=selected_index)


def _handle_dialog_video_info(args: dict) -> None:
    xbmc.executebuiltin('ActivateWindow(busydialog)')
    try:
        _handle_dialog_video_info_inner(args)
    finally:
        xbmc.executebuiltin('Dialog.Close(busydialog,true)')
        _restore_focus(args, 'script-skin-info-service-DialogVideoInfo.xml')


def _handle_dialog_video_info_inner(args: dict) -> None:
    from lib.data.database._infrastructure import init_database

    init_database()

    media_type = args.get('dbtype', '')
    if media_type == 'tv':
        media_type = 'tvshow'
    dbid = args.get('dbid', '')
    tmdb_id = args.get('tmdb_id', '')
    imdb_id = args.get('imdb_id', '')

    if not tmdb_id and not imdb_id:
        if not dbid or not media_type:
            log("General", "dialog_video_info: Need dbid+dbtype or tmdb_id/imdb_id",
                xbmc.LOGWARNING)
            return

        from lib.kodi.client import get_item_details
        try:
            dbid_int = int(dbid)
        except (ValueError, TypeError):
            log("General", f"dialog_video_info: Invalid dbid '{dbid}'", xbmc.LOGWARNING)
            return

        if media_type == 'episode':
            episode_details = get_item_details("episode", dbid_int, ["tvshowid"])
            if episode_details and episode_details.get("tvshowid"):
                details = get_item_details("tvshow", episode_details["tvshowid"], ["uniqueid"])
            else:
                return
        else:
            details = get_item_details(media_type, dbid_int, ["uniqueid"])

        if not details:
            return
        uniqueid = details.get("uniqueid") or {}
        imdb_id = uniqueid.get("imdb", "")
        tmdb_id = uniqueid.get("tmdb", "")

    from lib.info.dialogs.video import open_video_info
    open_video_info(
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        media_type=media_type,
        dbid=dbid,
    )


_HANDLERS: Dict[str, Callable[[dict], None]] = {
    "colorpicker": _handle_colorpicker,
    "blur": _handle_blur,
    "split_string": _handle_split_string,
    "urlencode": _handle_urlencode,
    "urldecode": _handle_urldecode,
    "math": _handle_math,
    "copy_item": _handle_copy_item,
    "container_labels": _handle_container_labels,
    "refresh_counter": _handle_refresh_counter,
    "file_exists": _handle_file_exists,
    "json": _handle_json,
    "container_move": _handle_container_move,
    "get_setting": _handle_get_setting,
    "set_setting": _handle_set_setting,
    "toggle_setting": _handle_toggle_setting,
    "reset_setting": _handle_reset_setting,
    "update_library_ratings": _handle_update_library_ratings,
    "sync_tvshows": _handle_sync_tvshows,
    "playall": _handle_playall,
    "playrandom": _handle_playrandom,
    "tools": _handle_tools,
    "review_artwork": _handle_review_artwork,
    "download_artwork": _handle_download_artwork,
    "update_ratings": _handle_update_ratings,
    "edit": _handle_edit,
    "export_nfo": _handle_export_nfo,
    "settings_action": _handle_settings_action,
    "arttest": _handle_arttest,
    "multiarttest": _handle_multiarttest,
    "person_info": _handle_person_info,
    "person_search": _handle_person_search,
    "tmdb_search": _handle_tmdb_search,
    "search_library_person": _handle_search_library_person,
    "online_fetch": _handle_online_fetch,
    "dialog_actor_info": _handle_dialog_actor_info,
    "dialog_video_info": _handle_dialog_video_info,
    "dialog_image_viewer": _handle_dialog_image_viewer,
}


def _dispatch_dialog(dialog: str, args: dict) -> None:
    from lib.skin.dialogs import (
        dialog_yesno, dialog_yesnocustom, dialog_ok, dialog_select,
        dialog_multiselect, dialog_contextmenu, dialog_input, dialog_numeric,
        dialog_textviewer, dialog_notification, dialog_browse, dialog_colorpicker,
        dialog_progress
    )

    dialog_map = {
        'yesno': dialog_yesno,
        'yesnocustom': dialog_yesnocustom,
        'ok': dialog_ok,
        'select': dialog_select,
        'multiselect': dialog_multiselect,
        'contextmenu': dialog_contextmenu,
        'input': dialog_input,
        'numeric': dialog_numeric,
        'textviewer': dialog_textviewer,
        'notification': dialog_notification,
        'browse': dialog_browse,
        'colorpicker': dialog_colorpicker,
        'progress': dialog_progress,
    }

    dialog_func = dialog_map.get(dialog.lower())
    if dialog_func:
        dialog_func(**args)
    else:
        log("General", f"Unknown dialog type '{dialog}'", xbmc.LOGERROR)


def main() -> None:
    """Script entry: parse `action=` or `dialog=` from argv, dispatch to the matching handler."""
    if len(sys.argv) <= 1:
        log("General",
            "No action or dialog specified. Skins opt in via Skin.SetBool(SkinInfo.Service)",
            xbmc.LOGWARNING)
        return

    args = _parse_args(1)
    action = args.get('action', '')
    dialog = args.get('dialog', '')

    if not action and not dialog:
        first_arg = sys.argv[1].lower().strip()
        if '=' not in first_arg:
            log("General", f"Invalid syntax '{first_arg}'. Use action=name or dialog=type",
                xbmc.LOGERROR)
            return
        log("General", "No action or dialog specified", xbmc.LOGERROR)
        return

    if dialog:
        _dispatch_dialog(dialog, args)
        return

    handler = _HANDLERS.get(action)
    if handler is None:
        log("General",
            f"Unknown action '{action}'. Expected one of: {', '.join(sorted(_HANDLERS))}",
            xbmc.LOGWARNING)
        return

    handler(args)


if __name__ == "__main__":
    main()

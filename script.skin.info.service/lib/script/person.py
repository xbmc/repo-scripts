"""`action=person_info` and `action=person_search` handlers.

Both resolve a TMDB person and set `SkinInfo.Person.{Details,Images,Filmography,Crew,
LibraryMovies,LibraryTVShows}` plugin URLs on the home window.

`person_info` input modes:
- `person_id=N` provided directly
- `crew=director|writer|creator` plus `dbid`/`dbtype` (TMDB-driven crew lookup)
- `name`/`role` plus `dbid`/`dbtype` (actor matching)

`person_search` input modes:
- `name`+`dbid`+`dbtype`: auto-match against the item's TMDB credits, fall back to
  search dialog on miss
- `query` (or `name`) only: TMDB search dialog
- After resolution, blurs the person's TMDB profile image into a separate window
  property for skin background use.
"""
from __future__ import annotations

import urllib.parse
from typing import Optional, Tuple

import xbmc
import xbmcgui

from lib.kodi.client import log


_PERSON_PROP_KEYS = (
    'SkinInfo.person_id',
    'SkinInfo.Person.Details',
    'SkinInfo.Person.Images',
    'SkinInfo.Person.Filmography',
    'SkinInfo.Person.Crew',
    'SkinInfo.Person.LibraryMovies',
    'SkinInfo.Person.LibraryTVShows',
    'SkinInfo.Person.SearchQuery',
)


def _clear_person_properties() -> None:
    """Clear all `SkinInfo.Person.*` and `SkinInfo.person_id` properties on the home window."""
    for key in _PERSON_PROP_KEYS:
        xbmc.executebuiltin(f'ClearProperty({key},home)')


def resolve_via_crew(person_api, name: str, dbid: Optional[str], dbtype: str, crew: str,
                     separator: str, auto_search: bool) -> Optional[tuple]:
    """Resolve `(person_id, name)` via TMDB crew listing. Returns None on failure."""
    if crew not in ('director', 'writer', 'creator'):
        log(
            "General",
            f"person_info: Invalid crew type '{crew}', expected director/writer/creator",
            xbmc.LOGERROR,
        )
        return None
    if not dbid:
        log("General", "person_info: crew mode requires dbid parameter", xbmc.LOGERROR)
        return None

    try:
        dbid_int = int(dbid)
    except (ValueError, TypeError):
        log("General", f"person_info: Invalid dbid '{dbid}'", xbmc.LOGERROR)
        return None

    tmdb_id = person_api.resolve_tmdb_id(dbtype, dbid_int)
    if not tmdb_id:
        log(
            "General",
            f"person_info: Could not resolve TMDB ID for {dbtype} {dbid}",
            xbmc.LOGERROR,
        )
        return None

    if not name:
        return _resolve_crew_from_tmdb(person_api, tmdb_id, dbtype, crew)

    return _resolve_crew_from_name(person_api, tmdb_id, dbtype, crew, name, separator, auto_search)


def _resolve_crew_from_tmdb(person_api, tmdb_id, dbtype: str, crew: str) -> Optional[tuple]:
    """Pick a crew member from TMDB's crew list. Single match auto-resolves; multi shows picker."""
    from lib.data.api.utilities import tmdb_image_url

    crew_list = person_api.get_crew_from_tmdb(crew, tmdb_id, dbtype)
    if not crew_list:
        log("General", f"person_info: No {crew}s found for TMDB {tmdb_id}", xbmc.LOGDEBUG)
        return None

    if len(crew_list) == 1:
        person_id = crew_list[0]['id']
        name = crew_list[0]['name']
        log(
            "General",
            f"person_info: Single {crew} found: {name} (person_id={person_id})",
            xbmc.LOGDEBUG,
        )
        return person_id, name

    items = []
    for member in crew_list:
        item = xbmcgui.ListItem(member['name'], offscreen=True)
        if member.get('job'):
            item.setLabel2(member['job'])
        if member.get('profile_path'):
            image_url = tmdb_image_url(member['profile_path'], 'h632')
            item.setArt({'thumb': image_url, 'icon': image_url})
        items.append(item)

    selected = xbmcgui.Dialog().select(f"Select {crew.title()}", items, useDetails=True)
    if selected < 0:
        log("General", f"person_info: User cancelled {crew} selection", xbmc.LOGDEBUG)
        return None

    person_id = crew_list[selected]['id']
    name = crew_list[selected]['name']
    log(
        "General",
        f"person_info: User selected {crew}: {name} (person_id={person_id})",
        xbmc.LOGDEBUG,
    )
    return person_id, name


def _resolve_crew_from_name(person_api, tmdb_id, dbtype: str, crew: str, name: str,
                            separator: str, auto_search: bool) -> Optional[tuple]:
    """Match a crew member by name (with optional separator-split picker)."""
    names = [n.strip() for n in name.split(separator) if n.strip()]
    if not names:
        log("General", "person_info: No valid names after parsing", xbmc.LOGERROR)
        return None

    if len(names) == 1:
        selected_name = names[0]
    else:
        selected = xbmcgui.Dialog().select(f"Select {crew.title()}", names)  # type: ignore[arg-type]
        if selected < 0:
            log("General", f"person_info: User cancelled {crew} selection", xbmc.LOGDEBUG)
            return None
        selected_name = names[selected]

    person_id = person_api.match_crew_to_person_id(
        selected_name, crew, tmdb_id, dbtype, auto_search=auto_search
    )
    if not person_id:
        log("General", f"person_info: Could not match {crew} '{selected_name}'", xbmc.LOGDEBUG)
        return None

    return person_id, selected_name


def resolve_via_actor(person_api, name: str, role: str, dbid: Optional[str], dbtype: str,
                      auto_search: bool, online: bool, sourceid: Optional[str],
                      open_window: str, set_search_query: bool = True) -> Optional[int]:
    """Resolve a person_id via actor name+role match; `set_search_query=False` skips the
    SearchQuery fallback for callers that don't read window props."""
    if not name or not dbid:
        log("General", "person_info: Missing required parameters (name, dbid)", xbmc.LOGERROR)
        return None

    try:
        dbid_int = int(dbid)
    except (ValueError, TypeError):
        log("General", f"person_info: Invalid dbid '{dbid}'", xbmc.LOGERROR)
        return None

    if dbtype in ('set', 'season'):
        if not sourceid:
            log(
                "General",
                f"person_info: {dbtype.capitalize()}s require sourceid parameter",
                xbmc.LOGERROR,
            )
            return None
        try:
            source_dbid = int(sourceid)
            source_dbtype = 'movie' if dbtype == 'set' else 'episode'
        except (ValueError, TypeError):
            log("General", f"person_info: Invalid sourceid '{sourceid}'", xbmc.LOGERROR)
            return None
        resolve_dbtype = source_dbtype
        resolve_dbid = source_dbid
    else:
        source_dbid = dbid_int
        source_dbtype = dbtype
        resolve_dbtype = dbtype
        resolve_dbid = dbid_int

    tmdb_id = person_api.resolve_tmdb_id(resolve_dbtype, resolve_dbid)
    if not tmdb_id:
        log("General", f"person_info: Could not resolve TMDB ID for {dbtype} {dbid}", xbmc.LOGERROR)
        return None

    person_id = person_api.match_actor_to_person_id(
        name, role, tmdb_id, source_dbtype, source_dbid,
        auto_search=auto_search, online=online,
    )
    if person_id:
        return person_id

    if not auto_search and set_search_query:
        encoded_name = urllib.parse.quote(name)
        encoded_role = urllib.parse.quote(role)
        search_command = (
            f"RunScript(script.skin.info.service,action=person_search,"
            f"name={encoded_name},role={encoded_role},dbtype={dbtype},dbid={dbid}"
        )
        if open_window:
            search_command += f",open_window={open_window}"
        search_command += ")"
        xbmc.executebuiltin(f'SetProperty(SkinInfo.Person.SearchQuery,{search_command},home)')
        log(
            "General",
            f"person_info: Auto-match failed, set SearchQuery property for '{name}'",
            xbmc.LOGDEBUG,
        )
    else:
        log("General", f"person_info: Could not match actor '{name}'", xbmc.LOGDEBUG)
    return None


def _set_person_properties(person_id: int, name: str, open_window: str) -> None:
    """Build the SkinInfo.Person.* plugin URLs and set them as window properties."""
    base_url = "plugin://script.skin.info.service/"
    encoded_name = urllib.parse.quote(name)

    xbmc.executebuiltin(f'SetProperty(SkinInfo.person_id,{person_id},home)')

    routes = (
        ('SkinInfo.Person.Details',
         f"{base_url}?action=person_info&info_type=details&person_id={person_id}"),
        ('SkinInfo.Person.Images',
         f"{base_url}?action=person_info&info_type=images&person_id={person_id}"),
        ('SkinInfo.Person.Filmography',
         f"{base_url}?action=person_info&info_type=filmography&person_id={person_id}"),
        ('SkinInfo.Person.Crew',
         f"{base_url}?action=person_info&info_type=crew&person_id={person_id}"),
        ('SkinInfo.Person.LibraryMovies',
         f"{base_url}?action=person_library&info_type=movies&person_name={encoded_name}"),
        ('SkinInfo.Person.LibraryTVShows',
         f"{base_url}?action=person_library&info_type=tvshows&person_name={encoded_name}"),
    )
    for prop, url in routes:
        xbmc.executebuiltin(f'SetProperty({prop},{url},home)')

    log("General", f"person_info: Set properties for person_id={person_id} ({name})", xbmc.LOGDEBUG)

    if open_window:
        xbmc.executebuiltin(f'ActivateWindow({open_window})')


def _blur_person_profile(profile_path: str) -> None:
    """Fire-and-forget RunScript to blur TMDB profile into `SkinInfo.Person.BlurredImage`."""
    from lib.data.api.utilities import tmdb_image_url
    profile_url = tmdb_image_url(profile_path)
    xbmc.executebuiltin(
        f'RunScript(script.skin.info.service,action=blur,source={profile_url},prefix=Person,window=home)'
    )


def _resolve_search_auto_match(person_api, name: str, role: str,
                              dbid: str, dbtype: str) -> Optional[int]:
    """Try to match a name+role against the dbid item's TMDB credits. None on any miss."""
    try:
        dbid_int = int(dbid)
    except (ValueError, TypeError):
        log("General", f"person_search: Invalid dbid '{dbid}'", xbmc.LOGERROR)
        return None

    tmdb_id = person_api.resolve_tmdb_id(dbtype, dbid_int)
    if not tmdb_id:
        return None

    return person_api.match_actor_to_person_id(
        name, role, tmdb_id, dbtype, dbid_int, auto_search=True,
    )


def _resolve_search_dialog(person_api, query: str) -> Optional[Tuple[int, dict]]:
    """Show the TMDB person-search dialog and fetch full person_data. None on cancel/miss."""
    from lib.data.api.tmdb import ApiTmdb
    api = ApiTmdb()

    person_id = person_api._search_with_dialog(query, api)
    if not person_id:
        return None

    person_data = person_api.get_person_data(person_id)
    if not person_data:
        log(
            "General",
            f"person_search: Failed to get details for person_id={person_id}",
            xbmc.LOGERROR,
        )
        return None

    return person_id, person_data


def handle_person_search_action(args: dict) -> None:
    """Entry point for `action=person_search`; see module docstring for input modes."""
    from lib.data.api import person as person_api
    from lib.data.database._infrastructure import init_database

    init_database()
    _clear_person_properties()

    name = urllib.parse.unquote(args.get('name', ''))
    role = urllib.parse.unquote(args.get('role', ''))
    dbid = args.get('dbid')
    dbtype = args.get('dbtype', 'movie')
    open_window = args.get('open_window', '')

    person_id: Optional[int] = None
    person_name = name
    person_data: Optional[dict] = None

    if name and dbid:
        person_id = _resolve_search_auto_match(person_api, name, role, dbid, dbtype)
        if person_id:
            person_data = person_api.get_person_data(person_id)

    if not person_id:
        query = args.get('query', name)
        if not query:
            log("General", "person_search: No query provided", xbmc.LOGERROR)
            return
        result = _resolve_search_dialog(person_api, query)
        if not result:
            return
        person_id, person_data = result
        person_name = person_data.get('name', query)

    if person_data and person_data.get('profile_path'):
        _blur_person_profile(person_data['profile_path'])

    assert person_id is not None
    _set_person_properties(person_id, person_name, open_window)


def handle_person_info_action(args: dict) -> None:
    """Entry point for `action=person_info`; see module docstring for input modes."""
    from lib.data.api import person as person_api
    from lib.data.database._infrastructure import init_database

    init_database()
    _clear_person_properties()

    name = args.get('name', '')
    role = args.get('role', '')
    dbid = args.get('dbid')
    dbtype = args.get('dbtype', 'movie')
    auto_search = args.get('auto_search', 'true').lower() == 'true'
    online = args.get('online', 'false').lower() == 'true'
    person_id_str = args.get('person_id')
    open_window = args.get('open_window', '')
    crew = args.get('crew', '')
    separator = args.get('separator', ' / ')

    person_id: Optional[int] = None
    if person_id_str:
        try:
            person_id = int(person_id_str)
            log("General", f"person_info: Using provided person_id {person_id}", xbmc.LOGDEBUG)
        except (ValueError, TypeError):
            log("General", f"person_info: Invalid person_id '{person_id_str}'", xbmc.LOGERROR)
            return

    if not person_id and crew:
        result = resolve_via_crew(person_api, name, dbid, dbtype, crew, separator, auto_search)
        if result is None:
            return
        person_id, name = result
    elif not person_id:
        person_id = resolve_via_actor(
            person_api, name, role, dbid, dbtype,
            auto_search, online, args.get('sourceid'), open_window,
        )
        if person_id is None:
            return

    assert person_id is not None
    person_api.get_person_data(person_id)
    _set_person_properties(person_id, name, open_window)

"""Plugin handlers for cast lists (library and player)."""
from __future__ import annotations

import traceback
from typing import Optional

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import log, extract_result
from lib.data.api.utilities import tmdb_image_url


_MAX_CAST_ITEMS = 2000


def _deduplicate_cast(items: list) -> list:
    """Dedupe cast across items by `name` (first wins); adds `_source_id` to each actor."""
    seen = set()
    unique_cast = []

    for item in items:
        cast = item.get('cast', [])
        item_id = item.get('movieid') or item.get('episodeid')

        for actor in cast:
            name = actor.get('name')
            if name and name not in seen:
                seen.add(name)
                actor_copy = actor.copy()
                if item_id:
                    actor_copy['_source_id'] = item_id
                unique_cast.append(actor_copy)

    if len(unique_cast) > _MAX_CAST_ITEMS:
        unique_cast = unique_cast[:_MAX_CAST_ITEMS]

    return unique_cast


def _create_cast_listitems(handle: int, cast_list: list) -> int:
    """Add ListItems to the plugin directory for each actor. Returns count added."""
    items_added = 0
    for actor in cast_list:
        name = actor.get('name', '')
        if not name:
            continue

        role = actor.get('role') or actor.get('character', '')
        if not role and 'roles' in actor and actor['roles']:
            role = actor['roles'][0].get('character', '')

        item = xbmcgui.ListItem(label=name, label2=role, offscreen=True)
        thumb = actor.get('thumbnail') or actor.get('profile_path') or ''

        if thumb.startswith('/'):
            thumb = tmdb_image_url(thumb, 'h632')

        if thumb:
            item.setArt({'icon': thumb, 'thumb': thumb})
        else:
            item.setArt({'icon': 'DefaultActor.png', 'thumb': 'DefaultActor.png'})

        source_id = actor.get('_source_id')
        if source_id:
            item.setProperty('source_id', str(source_id))

        person_id = actor.get('id')
        if person_id:
            item.setProperty('person_id', str(person_id))

        xbmcplugin.addDirectoryItem(handle, '', item, False)
        items_added += 1

    if items_added > 0:
        xbmcplugin.setContent(handle, 'actors')

    return items_added


def _handle_online_cast(handle: int, dbtype: str, dbid: int, tmdb_id: int = 0,
                        imdb_id: str = '', season: Optional[int] = None,
                        episode: Optional[int] = None) -> Optional[int]:
    """Fetch and add cast ListItems from TMDB; returns None if the TMDB ID can't be resolved."""
    from lib.kodi.client import get_item_details
    from lib.data.api.tmdb import ApiTmdb
    from lib.data.api.person import resolve_tmdb_id

    api = ApiTmdb()

    if not tmdb_id and dbid:
        tmdb_id = resolve_tmdb_id(dbtype, dbid) or 0
    if not tmdb_id and imdb_id:
        find_type = 'movie' if dbtype == 'movie' else 'tvshow'
        tmdb_id = api.find_by_imdb(imdb_id, find_type) or 0
    if not tmdb_id:
        log(
            "Plugin",
            f"Online Cast: Could not resolve TMDB ID for {dbtype} (dbid={dbid}, imdb={imdb_id})",
            xbmc.LOGWARNING,
        )
        return None

    cast = []

    if dbtype == 'movie':
        data = api.get_movie_details_extended(tmdb_id)
        if data and 'credits' in data:
            cast = data['credits'].get('cast', [])

    elif dbtype == 'tvshow':
        data = api.get_tv_details_extended(tmdb_id)
        if data and 'credits' in data:
            cast = data['credits'].get('cast', [])

    elif dbtype == 'season':
        if season is not None:
            season_num = season
        elif dbid:
            details = get_item_details(dbtype, dbid, ['season'])
            season_num = details.get('season') if details else None
        else:
            season_num = None
        if season_num is None:
            log("Plugin", "Online Cast: season needs a season param or a dbid", xbmc.LOGWARNING)
            return None

        season_data = api.get_season_details(tmdb_id, season_num)
        if season_data:
            main_cast = season_data.get('aggregate_credits', {}).get('cast', [])
            all_guests = {}
            for ep in season_data.get('episodes', []):
                for guest in ep.get('guest_stars', []):
                    guest_id = guest.get('id')
                    if guest_id and guest_id not in all_guests:
                        all_guests[guest_id] = guest
            cast = main_cast + list(all_guests.values())

    elif dbtype == 'episode':
        if season is not None and episode is not None:
            season_num, episode_num = season, episode
        elif dbid:
            details = get_item_details(dbtype, dbid, ['season', 'episode'])
            if not details:
                log("Plugin", f"Online Cast: Failed to get episode details for {dbid}",
                    xbmc.LOGWARNING)
                return None
            season_num = details.get('season')
            episode_num = details.get('episode')
        else:
            log("Plugin", "Online Cast: episode needs season+episode params or a dbid",
                xbmc.LOGWARNING)
            return None

        episode_data = api.get_episode_details_extended(tmdb_id, season_num, episode_num)
        if episode_data and 'credits' in episode_data:
            episode_cast = episode_data['credits'].get('cast', [])
            episode_guests = episode_data['credits'].get('guest_stars', [])
            cast = episode_cast + episode_guests

    if not cast:
        log("Plugin", f"Online Cast: No cast found for {dbtype} tmdb {tmdb_id}", xbmc.LOGINFO)
        return 0

    log("Plugin", f"Online Cast: Found {len(cast)} cast members for {dbtype} tmdb {tmdb_id}",
        xbmc.LOGDEBUG)
    return _create_cast_listitems(handle, cast)


def handle_get_cast(handle: int, params: dict) -> None:
    """Plugin entry for cast listings; `online=true` fetches from TMDB, default reads the Kodi
    library."""
    try:
        dbid = params.get('dbid', [''])[0]
        dbtype = params.get('dbtype', [''])[0]
        tmdb_id_str = params.get('tmdb_id', [''])[0]
        imdb_id_str = params.get('imdb_id', [''])[0]
        season_str = params.get('season', [''])[0]
        episode_str = params.get('episode', [''])[0]
        online = params.get('online', ['false'])[0].lower() == 'true'

        if dbtype not in ('movie', 'set', 'tvshow', 'season', 'episode'):
            log("Plugin", f'Library Cast: Invalid dbtype "{dbtype}"', xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        if online and not dbid and not tmdb_id_str and not imdb_id_str:
            log(
                "Plugin",
                "Online Cast: Missing required parameters (need tmdb_id, imdb_id, or dbid)",
                xbmc.LOGWARNING,
            )
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        if not online and not dbid:
            log("Plugin", "Library Cast: Missing required parameters (dbid)", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        try:
            tmdb_id = int(tmdb_id_str) if tmdb_id_str else 0
        except (ValueError, TypeError):
            tmdb_id = 0

        season = int(season_str) if season_str.isdigit() else None
        episode = int(episode_str) if episode_str.isdigit() else None

        from lib.kodi.client import get_item_details

        items_added = 0

        if online:
            log(
                "Plugin",
                f"Online Cast: {dbtype} request (tmdb_id={tmdb_id or '-'}, "
                f"imdb_id={imdb_id_str or '-'}, s={season}, e={episode})",
                xbmc.LOGDEBUG,
            )
            items_added = _handle_online_cast(
                handle, dbtype, int(dbid) if dbid else 0, tmdb_id, imdb_id_str, season, episode)
            if items_added is None:
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return
            log("Plugin", f"Online Cast: Created {items_added} ListItems", xbmc.LOGINFO)
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        if dbtype in ('movie', 'episode', 'tvshow'):
            if dbtype == 'movie':
                details = get_item_details('movie', int(dbid), ['cast'])
            elif dbtype == 'episode':
                details = get_item_details('episode', int(dbid), ['cast'])
            else:
                details = get_item_details('tvshow', int(dbid), ['cast'])

            if not details:
                log(
                    "Plugin",
                    f"Library Cast: {dbtype.capitalize()} {dbid} not found",
                    xbmc.LOGWARNING,
                )
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return

            cast = details.get('cast', [])
            if not cast:
                log("Plugin", f"Library Cast: No cast found for {dbtype} {dbid}", xbmc.LOGINFO)
                xbmcplugin.endOfDirectory(handle, succeeded=True)
                return

            log(
                "Plugin",
                f"Library Cast: Processing {dbtype} {dbid} - Found {len(cast)} cast members",
                xbmc.LOGDEBUG,
            )
            items_added = _create_cast_listitems(handle, cast)

        elif dbtype in ('set', 'season'):
            if dbtype == 'set':
                details = get_item_details(
                    'set',
                    int(dbid),
                    ['title'],
                    movies={
                        'properties': ['cast'],
                        'sort': {'method': 'year', 'order': 'ascending'},
                    }
                )
                items = details.get('movies', []) if details else []

            else:
                from lib.kodi.client import request

                season_details = get_item_details('season', int(dbid), ['season', 'tvshowid'])
                if not season_details:
                    log("Plugin", f"Library Cast: Season {dbid} not found", xbmc.LOGWARNING)
                    xbmcplugin.endOfDirectory(handle, succeeded=False)
                    return

                tvshow_id = season_details.get('tvshowid')
                season_num = season_details.get('season')

                result = request(
                    'VideoLibrary.GetEpisodes',
                    {
                        'tvshowid': tvshow_id,
                        'season': season_num,
                        'properties': ['cast'],
                        'sort': {'method': 'episode', 'order': 'ascending'}
                    }
                )
                items = extract_result(result, 'episodes', [])

            if not items:
                log("Plugin", f"Library Cast: No items found for {dbtype} {dbid}", xbmc.LOGINFO)
                xbmcplugin.endOfDirectory(handle, succeeded=True)
                return

            unique_cast = _deduplicate_cast(items)

            log(
                "Plugin",
                f"Library Cast: Processing {dbtype} {dbid} - Found {len(items)} items, "
                f"deduplicated to {len(unique_cast)} unique cast",
                xbmc.LOGDEBUG,
            )

            items_added = _create_cast_listitems(handle, unique_cast)

        log("Plugin", f"Library Cast: Created {items_added} ListItems", xbmc.LOGINFO)
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        log("Plugin", f"Library Cast: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def handle_get_cast_player(handle: int, params: dict) -> None:
    """Plugin entry for player cast. `aggregate=true` on episodes returns the show's combined
    cast."""
    try:
        content = xbmc.getInfoLabel('VideoPlayer.Content()')
        dbid = xbmc.getInfoLabel('VideoPlayer.DBID')
        tvshow_dbid = xbmc.getInfoLabel('VideoPlayer.TvShowDBID')

        if not content or not dbid:
            log("Plugin", "Player Cast: No video playing or missing DBID", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        content_type = content.rstrip('s')

        valid_types = ('movie', 'episode', 'musicvideo')
        if content_type not in valid_types:
            log("Plugin",
                f'Player Cast: Unsupported content type "{content_type}"',
                xbmc.LOGWARNING
            )
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        from lib.kodi.client import get_item_details, request

        aggregate = params.get('aggregate', ['false'])[0].lower() == 'true'

        if content_type == 'episode' and aggregate and tvshow_dbid:
            result = request(
                'VideoLibrary.GetEpisodes',
                {
                    'tvshowid': int(tvshow_dbid),
                    'properties': ['cast'],
                    'sort': {'method': 'episode', 'order': 'ascending'}
                }
            )
            items = extract_result(result, 'episodes', [])
            log(
                "Plugin",
                f"Player Cast: Aggregating cast from entire show (DBID: {tvshow_dbid})",
                xbmc.LOGDEBUG,
            )

        else:
            details = get_item_details(content_type, int(dbid), ['cast'])
            if not details:
                log("Plugin", f"Player Cast: No details for {content_type} {dbid}", xbmc.LOGWARNING)
                xbmcplugin.endOfDirectory(handle, succeeded=False)
                return

            items = [details]
            log("Plugin", f"Player Cast: Getting cast for {content_type} {dbid}", xbmc.LOGDEBUG)

        if not items:
            log("Plugin", "Player Cast: No items found", xbmc.LOGINFO)
            xbmcplugin.endOfDirectory(handle, succeeded=True)
            return

        unique_cast = _deduplicate_cast(items)
        log(
            "Plugin",
            f"Player Cast: Found {len(items)} items, "
            f"deduplicated to {len(unique_cast)} unique cast",
            xbmc.LOGDEBUG,
        )

        items_added = _create_cast_listitems(handle, unique_cast)

        log("Plugin", f"Player Cast: Created {items_added} ListItems", xbmc.LOGINFO)
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        log("Plugin", f"Player Cast: Error - {e}", xbmc.LOGERROR)
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)

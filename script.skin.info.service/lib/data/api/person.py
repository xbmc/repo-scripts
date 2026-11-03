"""Match a Kodi actor or crew member to a TMDB person, and shape that person for display."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, Optional

import xbmc
import xbmcgui

from lib.kodi.client import log, get_item_details, ADDON
from lib.kodi.utilities import MULTI_VALUE_SEP
from lib.data.api.tmdb import ApiTmdb
from lib.data.api.utilities import tmdb_image_url
from lib.data.database import cache as db_cache


def build_person_props(person_data: dict) -> Dict[str, str]:
    """Build the display properties a dialog or ListItem shows for a TMDB person."""
    props: Dict[str, str] = {'name': person_data.get('name', 'Unknown')}

    if person_data.get('biography'):
        props['biography'] = person_data['biography']

    birthday = person_data.get('birthday')
    deathday = person_data.get('deathday')

    if birthday:
        props['birthday'] = birthday
        try:
            birth_date = datetime.fromisoformat(birthday)
            end_date = datetime.fromisoformat(deathday) if deathday else datetime.now()
            age = end_date.year - birth_date.year
            if (end_date.month, end_date.day) < (birth_date.month, birth_date.day):
                age -= 1
            props['age'] = str(age)
            props['birthdayformatted'] = birth_date.strftime(xbmc.getRegion('dateshort'))
        except (ValueError, TypeError):
            pass

    if deathday:
        props['deathday'] = deathday
        try:
            death_date = datetime.fromisoformat(deathday)
            props['deathdayformatted'] = death_date.strftime(xbmc.getRegion('dateshort'))
        except (ValueError, TypeError):
            pass

    if person_data.get('place_of_birth'):
        props['birthplace'] = person_data['place_of_birth']

    if person_data.get('known_for_department'):
        props['knownfor'] = person_data['known_for_department']

    if person_data.get('id'):
        props['person_id'] = str(person_data['id'])

    if person_data.get('imdb_id'):
        props['imdb_id'] = person_data['imdb_id']

    gender_text = {1: 'Female', 2: 'Male'}.get(person_data.get('gender') or 0)
    if gender_text:
        props['gender'] = gender_text

    external_ids = person_data.get('external_ids', {})
    for key in ('instagram_id', 'twitter_id', 'facebook_id', 'tiktok_id', 'youtube_id'):
        value = external_ids.get(key)
        if value:
            props[key.replace('_id', '')] = value

    profile_path = person_data.get('profile_path')
    if profile_path:
        props['profileimage'] = tmdb_image_url(profile_path)

    cast = person_data.get('combined_credits', {}).get('cast', [])
    if cast:
        for media_type, title_key, prop in (('movie', 'title', 'topmovies'),
                                            ('tv', 'name', 'toptvshows')):
            entries = sorted((c for c in cast if c.get('media_type') == media_type),
                             key=lambda c: c.get('popularity', 0), reverse=True)
            seen: set = set()
            unique = []
            for entry in entries:
                entry_id = entry.get('id')
                if entry_id and entry_id not in seen:
                    seen.add(entry_id)
                    unique.append(entry)
            top = MULTI_VALUE_SEP.join(e.get(title_key, '') for e in unique[:5] if e.get(title_key))
            if top:
                props[prop] = top

    return props


def library_tmdb_id(dbtype: str, dbid: int) -> Optional[int]:
    """Get a library item's TMDB id, converting an IMDb or TVDB id when that is all it has."""
    if dbtype in ('season', 'episode'):
        details = get_item_details(dbtype, dbid, ['tvshowid'])
        if not details:
            return None
        tvshow_id = details.get('tvshowid')
        if not tvshow_id:
            return None
        return library_tmdb_id('tvshow', tvshow_id)

    details = get_item_details(dbtype, dbid, ['uniqueid'])
    if not details:
        return None

    uniqueid = details.get('uniqueid', {})
    find_type = 'tvshow' if dbtype == 'tvshow' else 'movie'

    if uniqueid.get('tmdb'):
        try:
            return int(uniqueid['tmdb'])
        except (ValueError, TypeError):
            pass

    if uniqueid.get('imdb'):
        tmdb_id = _convert_external_id(uniqueid['imdb'], 'imdb_id', find_type)
        if tmdb_id:
            return tmdb_id

    if dbtype in ('tvshow', 'episode') and uniqueid.get('tvdb'):
        tmdb_id = _convert_external_id(uniqueid['tvdb'], 'tvdb_id', find_type)
        if tmdb_id:
            return tmdb_id

    # IMDb IDs stored under non-standard keys (e.g. "unknown")
    for value in uniqueid.values():
        if isinstance(value, str) and value.startswith('tt'):
            tmdb_id = _convert_external_id(value, 'imdb_id', find_type)
            if tmdb_id:
                return tmdb_id

    log("Person", f"Could not resolve TMDB ID for {dbtype} {dbid}, uniqueid={uniqueid}",
        xbmc.LOGWARNING)
    return None


def _convert_external_id(external_id: str, source: str, media_type: str) -> Optional[int]:
    """Convert an IMDb or TVDB id to a TMDB id through TMDB's find endpoint."""
    api = ApiTmdb()
    result = api.find_by_external_id(external_id, source, media_type)
    if result and "id" in result:
        return result["id"]
    return None


def match_actor_to_person_id(actor_name: str, actor_role: str, tmdb_id: int, dbtype: str,
                             dbid: int = 0, auto_search: bool = True,
                             online: bool = False) -> Optional[int]:
    """Match a person in the cast, then the crew, to a TMDB person id; may search on a miss."""
    api = ApiTmdb()
    credits = []
    crew: list = []

    if dbtype == 'episode':
        details = get_item_details(dbtype, dbid, ['season', 'episode'])
        if not details:
            log("Person", f"Failed to get episode details for dbid {dbid}", xbmc.LOGWARNING)
            return None

        season_num = details.get('season')
        episode_num = details.get('episode')
        if season_num is None or episode_num is None:
            log("Person", f"Missing season/episode for dbid {dbid}", xbmc.LOGWARNING)
            return None

        episode_data = api.get_episode_details_extended(tmdb_id, season_num, episode_num)
        if not episode_data or 'credits' not in episode_data:
            log("Person",
                f"No episode data found for TV {tmdb_id} S{season_num}E{episode_num}",
                xbmc.LOGWARNING)
            return None

        episode_cast = episode_data.get('credits', {}).get('cast', [])
        episode_guests = episode_data.get('credits', {}).get('guest_stars', [])
        crew = episode_data.get('credits', {}).get('crew') or []

        if online:
            credits = episode_cast + episode_guests
            log("Person",
                f"Episode credits (online): {len(episode_cast)} episode cast + "
                f"{len(episode_guests)} episode guests = {len(credits)} total",
                xbmc.LOGDEBUG)
        else:
            show_data = api.get_complete_data('tvshow', tmdb_id)
            aggregate = (show_data or {}).get('aggregate_credits', {}).get('cast', [])
            combined_cast = _flatten_aggregate_credits(aggregate)
            credits = combined_cast + episode_guests
            log("Person",
                f"Episode credits (aggregate): {len(combined_cast)} aggregate cast entries + "
                f"{len(episode_guests)} episode guests = {len(credits)} total",
                xbmc.LOGDEBUG)

    elif dbtype == 'season':
        details = get_item_details(dbtype, dbid, ['season'])
        if not details:
            log("Person", f"Failed to get season details for dbid {dbid}", xbmc.LOGWARNING)
            return None

        season_num = details.get('season')
        if season_num is None:
            log("Person", f"No season number found for dbid {dbid}", xbmc.LOGWARNING)
            return None

        log("Person", f"Fetching season details for TV {tmdb_id} season {season_num}",
            xbmc.LOGDEBUG)
        season_data = api.get_season_details(tmdb_id, season_num)

        if not season_data:
            log("Person", f"No data found for TV {tmdb_id} season {season_num}", xbmc.LOGWARNING)
            return None

        main_cast = season_data.get('aggregate_credits', {}).get('cast', [])
        crew = season_data.get('aggregate_credits', {}).get('crew') or []

        all_guests = {}
        for episode in season_data.get('episodes', []):
            for guest in episode.get('guest_stars', []):
                guest_id = guest.get('id')
                if guest_id and guest_id not in all_guests:
                    all_guests[guest_id] = guest

        credits = main_cast + list(all_guests.values())
        log("Person",
            f"Season credits: {len(main_cast)} main cast + {len(all_guests)} unique guests = "
            f"{len(credits)} total",
            xbmc.LOGDEBUG)

    else:
        media_type = 'movie' if dbtype == 'movie' else 'tvshow'
        complete_data = api.get_complete_data(media_type, tmdb_id)

        if not complete_data or 'credits' not in complete_data:
            log("Person", f"No credits found for {media_type} {tmdb_id}", xbmc.LOGWARNING)
            return None

        credits = tmdb_cast(complete_data, media_type)
        crew = complete_data['credits'].get('crew') or []

    match = match_credit(credits, actor_name, actor_role) or match_credit(crew, actor_name, '')
    if match:
        return match['id']

    if auto_search:
        log("Person", f"All automatic matching failed for '{actor_name}', showing search dialog",
            xbmc.LOGDEBUG)
        return _search_with_dialog(actor_name, api)

    log("Person", f"All automatic matching failed for '{actor_name}', auto_search disabled",
        xbmc.LOGDEBUG)
    return None


def _flatten_aggregate_credits(aggregate_cast: list) -> list:
    """Expand aggregate credits, one entry per actor role, into the shape the matchers expect."""
    flat: list = []
    for actor in aggregate_cast:
        roles = actor.get('roles') or []
        if not roles:
            flat.append({**actor, 'character': ''})
            continue
        for role in roles:
            flat.append({**actor, 'character': role.get('character', '')})
    return flat


def tmdb_cast(data: Optional[dict], media_type: str) -> list:
    """Get the cast from a complete TMDB record, across all seasons for a TV show."""
    data = data or {}
    if media_type == 'tvshow':
        aggregate = data.get('aggregate_credits', {}).get('cast', [])
        if aggregate:
            return _flatten_aggregate_credits(aggregate)
    return data.get('credits', {}).get('cast', [])


def normalize_name(name: str) -> str:
    """Normalize a name for matching, ignoring accents, apostrophe style and dots in initials."""
    import re
    import unicodedata

    normalized = unicodedata.normalize('NFD', name)
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub("[\u2018\u2019]", "'", normalized)
    normalized = re.sub(r'([A-Z])\.\s*', r'\1 ', normalized)
    normalized = ' '.join(normalized.split())

    return normalized.strip()


def exact_match(credits: list, name: str, role: str) -> Optional[dict]:
    """Match exact name and exact role."""
    normalized_name = normalize_name(name)
    for actor in credits:
        actor_name = actor.get('name', '')
        normalized_actor = normalize_name(actor_name)
        if normalized_actor == normalized_name and actor.get('character') == role:
            return actor
    return None


def fuzzy_role_match(credits: list, name: str, role: str) -> Optional[dict]:
    """Match exact name with fuzzy role (substring)."""
    if not role:
        return None

    normalized_name = normalize_name(name)
    role_lower = role.lower()
    for actor in credits:
        actor_name = actor.get('name', '')
        normalized_actor = normalize_name(actor_name)
        if normalized_actor == normalized_name:
            character = actor.get('character', '').lower()
            if role_lower in character or character in role_lower:
                return actor
    return None


def name_only_match(credits: list, name: str) -> Optional[dict]:
    """Match name only, ignore role."""
    normalized_name = normalize_name(name)
    for actor in credits:
        actor_name = actor.get('name', '')
        normalized_actor = normalize_name(actor_name)
        if normalized_actor == normalized_name:
            return actor
    return None


def fuzzy_name_match(credits: list, name: str) -> Optional[dict]:
    """Match with name variations (handle 'First Last' vs 'Last, First')."""
    name_lower = name.lower().strip()
    name_reversed = ' '.join(reversed(name.split())).lower()

    for actor in credits:
        actor_name = actor.get('name', '').lower().strip()
        if actor_name == name_lower or actor_name == name_reversed:
            return actor
    return None


def match_credit(credits: list, name: str, role: str,
                 usable: Optional[Callable[[dict], bool]] = None) -> Optional[dict]:
    """Match an actor to a credit, strictest matcher first, passing over unusable matches."""
    matchers = (
        ('exact match', lambda: exact_match(credits, name, role)),
        ('fuzzy role', lambda: fuzzy_role_match(credits, name, role)),
        ('name only', lambda: name_only_match(credits, name)),
        ('fuzzy name', lambda: fuzzy_name_match(credits, name)),
    )
    for label, matcher in matchers:
        match = matcher()
        if match and (usable is None or usable(match)):
            log("Person", f"Matched '{name}' via {label} (person_id={match.get('id')})",
                xbmc.LOGDEBUG)
            return match
    return None


def _search_with_dialog(name: str, api: ApiTmdb) -> Optional[int]:
    """Search TMDB by name and let the user pick unless one result; None if none or on cancel."""
    results = api.search(name, 'person')

    if not results:
        xbmcgui.Dialog().notification(
            ADDON.getLocalizedString(32703),
            ADDON.getLocalizedString(32401).format(name),
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return None
    if len(results) == 1:
        log("Person", f"Single search result for '{name}' (person_id={results[0]['id']})",
            xbmc.LOGDEBUG)
        return results[0]['id']

    items = []
    for result in results[:10]:
        item = xbmcgui.ListItem(result['name'], offscreen=True)

        known_for = result.get('known_for_department', '')
        if known_for:
            item.setLabel2(known_for)

        profile_path = result.get('profile_path')
        if profile_path:
            image_url = tmdb_image_url(profile_path, 'h632')
            item.setArt({'thumb': image_url, 'icon': image_url})

        items.append(item)

    dialog = xbmcgui.Dialog()
    selected = dialog.select(ADDON.getLocalizedString(32272), items, useDetails=True)

    if selected < 0:
        log("Person", f"User cancelled person selection for '{name}'", xbmc.LOGDEBUG)
        return None

    person_id = results[selected]['id']
    log("Person", f"User selected '{results[selected]['name']}' (person_id={person_id})",
        xbmc.LOGDEBUG)
    return person_id


def get_person_data(person_id: int) -> Optional[dict]:
    """Get a TMDB person's full record, from the cache when it holds one."""
    cached = db_cache.get_cached_person_data(person_id)
    if cached:
        log("Person", f"Loaded person {person_id} from cache", xbmc.LOGDEBUG)
        return cached

    api = ApiTmdb()
    data = api.get_person_details(person_id)

    if data:
        db_cache.cache_person_data(person_id, data)
        log("Person", f"Fetched and cached person {person_id}", xbmc.LOGDEBUG)

    return data


def match_crew_to_person_id(
    crew_name: str,
    crew_type: str,
    tmdb_id: int,
    dbtype: str,
    auto_search: bool = True
) -> Optional[int]:
    """Match a director, writer or creator to a TMDB person id; may search on a miss."""
    api = ApiTmdb()
    normalized_name = normalize_name(crew_name)

    if crew_type == "creator":
        if dbtype != "tvshow":
            log("Person", f"Creator lookup only valid for TV shows, got {dbtype}", xbmc.LOGWARNING)
            return None

        data = api.get_tv_details_extended(tmdb_id)
        if not data:
            log("Person", f"No TV data found for TMDB ID {tmdb_id}", xbmc.LOGWARNING)
            return None

        created_by = data.get("created_by") or []
        for creator in created_by:
            creator_name = creator.get("name", "")
            if normalize_name(creator_name) == normalized_name:
                person_id = creator.get("id")
                log("Person", f"Matched creator '{crew_name}' (person_id={person_id})",
                    xbmc.LOGDEBUG)
                return person_id

        log("Person", f"Creator '{crew_name}' not found in created_by for TV {tmdb_id}",
            xbmc.LOGDEBUG)

    else:
        media_type = "movie" if dbtype == "movie" else "tvshow"
        data = api.get_complete_data(media_type, tmdb_id)

        if not data or "credits" not in data:
            log("Person", f"No credits found for {media_type} {tmdb_id}", xbmc.LOGWARNING)
            return None

        crew = data["credits"].get("crew") or []

        if crew_type not in _CREW_JOBS:
            log("Person", f"Unknown crew_type '{crew_type}'", xbmc.LOGWARNING)
            return None

        # Kodi credits people TMDB lists under other jobs, such as Novel or Director for a writer
        member = next((m for m in crew
                       if normalize_name(m.get("name", "")) == normalized_name), None)
        if member:
            person_id = member.get("id")
            log("Person", f"Matched {crew_type} '{crew_name}' (person_id={person_id})",
                xbmc.LOGDEBUG)
            return person_id

        log("Person",
            f"{crew_type.title()} '{crew_name}' not found in crew for {media_type} {tmdb_id}",
            xbmc.LOGDEBUG)

    if auto_search:
        log("Person", f"Crew matching failed for '{crew_name}', showing search dialog",
            xbmc.LOGDEBUG)
        return _search_with_dialog(crew_name, api)

    return None


_CREW_JOBS = {
    "director": {"Director"},
    "writer": {"Writer", "Screenplay", "Story", "Original Story"},
}


_CREW_JOB_PRIORITY: dict[str, int] = {
    'Director': 1,
    'Co-Director': 1,
    'Creator': 2,
    'Writer': 3,
    'Screenplay': 3,
    'Story': 3,
    'Original Story': 3,
    'Showrunner': 4,
    'Executive Producer': 4,
    'Producer': 5,
    'Co-Producer': 5,
    'Line Producer': 5,
    'Editor': 6,
    'Director of Photography': 7,
    'Cinematography': 7,
    'Original Music Composer': 8,
    'Composer': 8,
    'Casting Director': 9,
    'Casting': 9,
    'Production Design': 10,
    'Art Direction': 10,
    'Costume Design': 11,
}


def get_crew_from_tmdb(
    crew_type: str,
    tmdb_id: int,
    dbtype: str,
    abort_flag=None
) -> list[dict]:
    """Get one crew type from TMDB, or the whole crew deduped with their jobs joined."""
    api = ApiTmdb()

    if crew_type == "creator":
        if dbtype != "tvshow":
            log("Person", f"Creator lookup only valid for TV shows, got {dbtype}", xbmc.LOGWARNING)
            return []

        data = api.get_tv_details_extended(tmdb_id, abort_flag)
        if not data:
            return []

        created_by = data.get("created_by") or []
        return [
            {
                "id": c.get("id"),
                "name": c.get("name", ""),
                "profile_path": c.get("profile_path"),
                "job": "Creator"
            }
            for c in created_by if c.get("id")
        ]

    media_type = "movie" if dbtype == "movie" else "tvshow"
    data = api.get_complete_data(media_type, tmdb_id, abort_flag=abort_flag)

    if not data or "credits" not in data:
        return []

    crew = data["credits"].get("crew") or []

    job_filter = _CREW_JOBS.get(crew_type)
    if job_filter is None and crew_type not in ("", "all"):
        return []

    if job_filter is None:
        sorted_members = sorted(crew, key=lambda m: _CREW_JOB_PRIORITY.get(m.get("job", ""), 99))

        by_person: dict[int, dict] = {}
        for member in sorted_members:
            person_id = member.get("id")
            if not person_id:
                continue
            job = member.get("job", "")
            existing = by_person.get(person_id)
            if existing:
                if job and job not in existing["job"].split(", "):
                    existing["job"] = f"{existing['job']}, {job}"
            else:
                by_person[person_id] = {
                    "id": person_id,
                    "name": member.get("name", ""),
                    "profile_path": member.get("profile_path"),
                    "job": job
                }
        return list(by_person.values())

    seen_ids: set[int] = set()
    result = []
    for member in crew:
        person_id = member.get("id")
        job = member.get("job", "")
        if person_id and job in job_filter and person_id not in seen_ids:
            seen_ids.add(person_id)
            result.append({
                "id": person_id,
                "name": member.get("name", ""),
                "profile_path": member.get("profile_path"),
                "job": job
            })

    return result

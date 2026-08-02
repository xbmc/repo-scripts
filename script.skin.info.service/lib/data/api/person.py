"""Person data coordination - matching actors to TMDB person IDs."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import xbmc
import xbmcgui

from lib.kodi.client import log, get_item_details, ADDON
from lib.kodi.utilities import MULTI_VALUE_SEP
from lib.data.api.tmdb import ApiTmdb
from lib.data.api.utilities import tmdb_image_url
from lib.data import database as db


def build_person_props(person_data: dict) -> Dict[str, str]:
    """Build display properties from a TMDB person payload.

    Shared by the actor info dialog (window properties) and the person plugin
    handler (ListItem properties). Includes `ProfileImage` for consumers that
    also want it as art.
    """
    props: Dict[str, str] = {'Name': person_data.get('name', 'Unknown')}

    if person_data.get('biography'):
        props['Biography'] = person_data['biography']

    birthday = person_data.get('birthday')
    deathday = person_data.get('deathday')

    if birthday:
        props['Birthday'] = birthday
        try:
            birth_date = datetime.strptime(birthday, '%Y-%m-%d')
            end_date = datetime.strptime(deathday, '%Y-%m-%d') if deathday else datetime.now()
            age = end_date.year - birth_date.year
            if (end_date.month, end_date.day) < (birth_date.month, birth_date.day):
                age -= 1
            props['Age'] = str(age)
            props['BirthdayFormatted'] = birth_date.strftime(xbmc.getRegion('dateshort'))
        except (ValueError, TypeError):
            pass

    if deathday:
        props['Deathday'] = deathday
        try:
            death_date = datetime.strptime(deathday, '%Y-%m-%d')
            props['DeathdayFormatted'] = death_date.strftime(xbmc.getRegion('dateshort'))
        except (ValueError, TypeError):
            pass

    if person_data.get('place_of_birth'):
        props['Birthplace'] = person_data['place_of_birth']

    if person_data.get('known_for_department'):
        props['KnownFor'] = person_data['known_for_department']

    if person_data.get('id'):
        props['person_id'] = str(person_data['id'])

    if person_data.get('imdb_id'):
        props['imdb_id'] = person_data['imdb_id']

    gender_text = {1: 'Female', 2: 'Male'}.get(person_data.get('gender') or 0)
    if gender_text:
        props['Gender'] = gender_text

    external_ids = person_data.get('external_ids', {})
    for key in ('instagram_id', 'twitter_id', 'facebook_id', 'tiktok_id', 'youtube_id'):
        value = external_ids.get(key)
        if value:
            props[key.replace('_id', '').title()] = value

    profile_path = person_data.get('profile_path')
    if profile_path:
        props['ProfileImage'] = tmdb_image_url(profile_path)

    cast = person_data.get('combined_credits', {}).get('cast', [])
    if cast:
        for media_type, title_key, prop in (('movie', 'title', 'TopMovies'),
                                            ('tv', 'name', 'TopTVShows')):
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


def resolve_tmdb_id(dbtype: str, dbid: int) -> Optional[int]:
    """Get TMDB ID for library item, converting from IMDb/TVDB if needed."""
    if dbtype in ('season', 'episode'):
        details = get_item_details(dbtype, dbid, ['tvshowid'])
        if not details:
            return None
        tvshow_id = details.get('tvshowid')
        if not tvshow_id:
            return None
        return resolve_tmdb_id('tvshow', tvshow_id)

    details = get_item_details(dbtype, dbid, ['uniqueid'])
    if not details:
        return None

    uniqueid = details.get('uniqueid', {})

    if uniqueid.get('tmdb'):
        try:
            return int(uniqueid['tmdb'])
        except (ValueError, TypeError):
            pass

    if uniqueid.get('imdb'):
        tmdb_id = _convert_external_id(uniqueid['imdb'], 'imdb_id')
        if tmdb_id:
            return tmdb_id

    if dbtype in ('tvshow', 'episode') and uniqueid.get('tvdb'):
        tmdb_id = _convert_external_id(uniqueid['tvdb'], 'tvdb_id')
        if tmdb_id:
            return tmdb_id

    # IMDb IDs stored under non-standard keys (e.g. "unknown")
    for value in uniqueid.values():
        if isinstance(value, str) and value.startswith('tt'):
            tmdb_id = _convert_external_id(value, 'imdb_id')
            if tmdb_id:
                return tmdb_id

    log("Person", f"Could not resolve TMDB ID for {dbtype} {dbid}, uniqueid={uniqueid}",
        xbmc.LOGWARNING)
    return None


def _convert_external_id(external_id: str, source: str) -> Optional[int]:
    """Convert IMDB/TVDB ID to TMDB ID using TMDB Find API."""
    api = ApiTmdb()
    result = api.find_by_external_id(external_id, source)
    if result and "id" in result:
        return result["id"]
    return None


def match_actor_to_person_id(actor_name: str, actor_role: str, tmdb_id: int, dbtype: str,
                             dbid: int = 0, auto_search: bool = True,
                             online: bool = False) -> Optional[int]:
    """Match actor to TMDB person ID using 5-stage strategy.

    Shows dialog select on failure for user to choose correct person.
    For episodes, tmdb_id is the tvshow TMDB ID. dbid is required for episodes/seasons.
    online=True uses TMDB data directly; False matches Kodi scraper behavior.
    """
    api = ApiTmdb()
    credits = []

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

        credits = complete_data['credits'].get('cast', [])

    match = exact_match(credits, actor_name, actor_role)
    if match:
        log("Person", f"Matched '{actor_name}' via exact match (person_id={match['id']})",
            xbmc.LOGDEBUG)
        return match['id']

    match = fuzzy_role_match(credits, actor_name, actor_role)
    if match:
        log("Person", f"Matched '{actor_name}' via fuzzy role (person_id={match['id']})",
            xbmc.LOGDEBUG)
        return match['id']

    match = name_only_match(credits, actor_name)
    if match:
        log("Person", f"Matched '{actor_name}' via name only (person_id={match['id']})",
            xbmc.LOGDEBUG)
        return match['id']

    match = fuzzy_name_match(credits, actor_name)
    if match:
        log("Person", f"Matched '{actor_name}' via fuzzy name (person_id={match['id']})",
            xbmc.LOGDEBUG)
        return match['id']

    if auto_search:
        log("Person", f"All automatic matching failed for '{actor_name}', showing search dialog",
            xbmc.LOGDEBUG)
        return _search_with_dialog(actor_name, api)

    log("Person", f"All automatic matching failed for '{actor_name}', auto_search disabled",
        xbmc.LOGDEBUG)
    return None


def _flatten_aggregate_credits(aggregate_cast: list) -> list:
    """Expand TMDB `aggregate_credits.cast` (one entry per actor with `roles[]`) into one entry
    per role.

    Each output entry preserves the actor fields plus a single `character` string,
    matching the shape that the matcher chain (`exact_match`/`fuzzy_role_match`/...) expects.
    """
    flat: list = []
    for actor in aggregate_cast:
        roles = actor.get('roles') or []
        if not roles:
            flat.append({**actor, 'character': ''})
            continue
        for role in roles:
            flat.append({**actor, 'character': role.get('character', '')})
    return flat


def normalize_name(name: str) -> str:
    """Normalize name for matching by handling special characters and initials."""
    import re
    import unicodedata

    normalized = unicodedata.normalize('NFD', name)
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"['']", "'", normalized)
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


def _search_with_dialog(name: str, api: ApiTmdb) -> Optional[int]:
    """Search TMDB and show dialog for user selection."""
    results = api.search_person(name)

    if not results:
        xbmcgui.Dialog().notification(
            "Person Info",
            f"Actor '{name}' not found",
            xbmcgui.NOTIFICATION_WARNING,
            3000
        )
        return None

    items = []
    for result in results[:10]:
        item = xbmcgui.ListItem(result['name'])

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
    """Get complete person data, using cache if available."""
    cached = db.get_cached_person_data(person_id)
    if cached:
        log("Person", f"Loaded person {person_id} from cache", xbmc.LOGDEBUG)
        return cached

    api = ApiTmdb()
    data = api.get_person_details(person_id)

    if data:
        db.cache_person_data(person_id, data)
        log("Person", f"Fetched and cached person {person_id}", xbmc.LOGDEBUG)

    return data


def match_crew_to_person_id(
    crew_name: str,
    crew_type: str,
    tmdb_id: int,
    dbtype: str,
    auto_search: bool = True
) -> Optional[int]:
    """Match crew member to TMDB person ID. crew_type: 'director', 'writer', or 'creator'."""
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

        if crew_type == "director":
            job_filter = {"Director"}
        elif crew_type == "writer":
            job_filter = {"Writer", "Screenplay", "Story", "Original Story"}
        else:
            log("Person", f"Unknown crew_type '{crew_type}'", xbmc.LOGWARNING)
            return None

        for member in crew:
            member_name = member.get("name", "")
            member_job = member.get("job", "")
            if normalize_name(member_name) == normalized_name and member_job in job_filter:
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
    dbtype: str
) -> list[dict]:
    """Get crew members from TMDB.

    `crew_type` may be `director`, `writer`, `creator`, or empty/`all` for full crew
    (deduped by person, multiple jobs joined as `Director, Producer`).

    Returns list of dicts with id, name, profile_path, job.
    """
    api = ApiTmdb()

    if crew_type == "creator":
        if dbtype != "tvshow":
            log("Person", f"Creator lookup only valid for TV shows, got {dbtype}", xbmc.LOGWARNING)
            return []

        data = api.get_tv_details_extended(tmdb_id)
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
    data = api.get_complete_data(media_type, tmdb_id)

    if not data or "credits" not in data:
        return []

    crew = data["credits"].get("crew") or []

    if crew_type == "director":
        job_filter: Optional[set[str]] = {"Director"}
    elif crew_type == "writer":
        job_filter = {"Writer", "Screenplay", "Story", "Original Story"}
    elif crew_type in ("", "all"):
        job_filter = None
    else:
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

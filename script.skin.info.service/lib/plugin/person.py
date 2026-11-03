"""Plugin handlers for person info, person library, crew lists, and TMDB details."""
from __future__ import annotations

from typing import Dict, List, Optional

import xbmc
import xbmcgui
import xbmcplugin

from lib.kodi.client import ADDON, log, extract_result
from lib.data.api.utilities import tmdb_image_url
from lib.kodi.formatters import format_rating, pick_clearlogo


def handle_person_info(handle: int, params: dict) -> None:
    """Plugin entry for person info. `info_type` routes to details/images/filmography/crew."""
    from lib.data.api import person as person_api

    try:
        person_id = params.get('person_id', [''])[0]
        info_type = params.get('info_type', [''])[0]

        if not person_id or not info_type:
            log("Plugin", "Person Info: Missing required parameters", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        try:
            person_id = int(person_id)
        except (ValueError, TypeError):
            log("Plugin", f"Person Info: Invalid person_id '{person_id}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        person_data = person_api.get_person_data(person_id)
        if not person_data:
            log("Plugin", f"Person Info: No data for person_id={person_id}", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        if info_type == 'details':
            _handle_person_details(handle, person_data)
        elif info_type == 'images':
            _handle_person_images(handle, person_data)
        elif info_type == 'filmography':
            _handle_person_filmography(handle, person_data, params)
        elif info_type == 'crew':
            _handle_person_crew(handle, person_data, params)
        else:
            log("Plugin", f"Person Info: Unknown info_type '{info_type}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)

    except Exception as e:
        log("Plugin", f"Person Info: Error - {e}", xbmc.LOGERROR)
        import traceback
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def _handle_person_details(handle: int, person_data: dict) -> None:
    """Handle `info_type=details`: one ListItem carrying every person property."""
    from lib.data.api.person import build_person_props

    props = build_person_props(person_data)
    item = xbmcgui.ListItem(props['name'], offscreen=True)

    profile_image = props.get('ProfileImage')
    if profile_image:
        item.setArt({'thumb': profile_image, 'icon': profile_image})

    for key, value in props.items():
        item.setProperty(key, value)

    xbmcplugin.addDirectoryItem(handle, '', item, False)
    xbmcplugin.setContent(handle, 'actors')
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_person_images(handle: int, person_data: dict) -> None:
    """Handle `info_type=images`: the profile images, best rated first."""
    images = person_data.get('images', {}).get('profiles', [])

    if not images:
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    images.sort(key=lambda x: x.get('vote_average', 0), reverse=True)

    for i, image in enumerate(images):
        file_path = image.get('file_path')
        if not file_path:
            continue

        item = xbmcgui.ListItem(ADDON.getLocalizedString(32740).format(i + 1), offscreen=True)

        image_url = tmdb_image_url(file_path)
        item.setArt({'thumb': image_url, 'icon': image_url})

        width = image.get('width')
        height = image.get('height')
        if width:
            item.setProperty('width', str(width))
        if height:
            item.setProperty('height', str(height))
        if width and height:
            item.setProperty('dimensions', f"{width}x{height}")

        vote_average = image.get('vote_average')
        if vote_average:
            item.setProperty('rating', format_rating(vote_average))

        vote_count = image.get('vote_count')
        if vote_count:
            item.setProperty('votes', str(vote_count))

        item.setProperty('aspectratio', str(image.get('aspect_ratio', '')))

        xbmcplugin.addDirectoryItem(handle, '', item, False)

    xbmcplugin.setContent(handle, 'images')
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_person_filmography(handle: int, person_data: dict, params: dict) -> None:
    """Handle `info_type=filmography`: the acting credits, filtered and sorted."""
    credits = person_data.get('combined_credits', {}).get('cast', [])

    credits = _dedupe_credits(credits, 'character', ' / ')
    credits = _filter_credits(credits, params)
    credits = _sort_credits(credits, params)

    limit_str = params.get('limit', [''])[0]
    if limit_str:
        try:
            limit = int(limit_str)
            credits = credits[:limit]
        except (ValueError, TypeError):
            pass

    library_dbids = _library_dbid_map(credits)

    for credit in credits:
        item = _create_credit_listitem(credit, library_dbids)
        xbmcplugin.addDirectoryItem(handle, '', item, False)

    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _handle_person_crew(handle: int, person_data: dict, params: dict) -> None:
    """Handle `info_type=crew`: one entry per title with jobs joined, unless a `job` is given."""
    credits = person_data.get('combined_credits', {}).get('crew', [])

    job_filter = params.get('job', [''])[0]
    if job_filter:
        target = job_filter.lower()
        credits = [c for c in credits if (c.get('job') or '').lower() == target]
    else:
        credits = _dedupe_credits(credits, 'job', ', ')

    credits = _filter_credits(credits, params)
    credits = _sort_credits(credits, params)

    limit_str = params.get('limit', [''])[0]
    if limit_str:
        try:
            limit = int(limit_str)
            credits = credits[:limit]
        except (ValueError, TypeError):
            pass

    library_dbids = _library_dbid_map(credits)

    for credit in credits:
        item = _create_credit_listitem(credit, library_dbids)

        if credit.get('job'):
            item.setProperty('job', credit['job'])
        if credit.get('department'):
            item.setProperty('department', credit['department'])

        xbmcplugin.addDirectoryItem(handle, '', item, False)

    xbmcplugin.setContent(handle, 'movies')
    xbmcplugin.endOfDirectory(handle, succeeded=True)


def _dedupe_credits(credits: list, field: str, separator: str) -> list:
    """Dedupe credits for the same title into one entry with one field's values joined."""
    seen: dict = {}
    for credit in credits:
        key = (credit.get('id'), credit.get('media_type'))
        if key in seen:
            existing = seen[key].get(field) or ''
            new_value = credit.get(field) or ''
            if new_value and new_value not in existing.split(separator):
                seen[key][field] = f"{existing}{separator}{new_value}" if existing else new_value
        else:
            seen[key] = dict(credit)
    return list(seen.values())


def _filter_credits(credits: list, params: dict) -> list:
    """Filter credits by media type, minimum votes and release, per the request."""
    from datetime import datetime

    dbtype = params.get('dbtype', ['both'])[0]
    if dbtype == 'tvshow':
        dbtype = 'tv'
    if dbtype in ('movie', 'tv'):
        credits = [c for c in credits if c.get('media_type') == dbtype]

    min_votes_str = params.get('min_votes', ['0'])[0]
    try:
        min_votes = int(min_votes_str)
        if min_votes > 0:
            credits = [c for c in credits if c.get('vote_count', 0) >= min_votes]
    except (ValueError, TypeError):
        pass

    exclude_unreleased = params.get('exclude_unreleased', ['false'])[0].lower() == 'true'
    if exclude_unreleased:
        today = datetime.now().strftime('%Y-%m-%d')
        # undated credits are unannounced future projects
        credits = [
            c for c in credits
            if (c.get('release_date') or c.get('first_air_date') or '9999') <= today
        ]

    return credits


def _sort_credits(credits: list, params: dict) -> list:
    """Sort credits by popularity, date, rating or title; any other `sort` keeps TMDB's order."""
    sort_method = params.get('sort', ['popularity'])[0]

    if sort_method == 'popularity':
        credits.sort(key=lambda c: c.get('popularity') or 0, reverse=True)
    elif sort_method == 'date_desc':
        credits.sort(
            key=lambda c: c.get('release_date') or c.get('first_air_date', '0000'),
            reverse=True,
        )
    elif sort_method == 'date_asc':
        credits.sort(key=lambda c: c.get('release_date') or c.get('first_air_date', '9999'))
    elif sort_method == 'rating':
        credits.sort(key=lambda c: c.get('vote_average', 0), reverse=True)
    elif sort_method == 'title':
        credits.sort(key=lambda c: (c.get('title') or c.get('name', '')).lower())

    return credits


def handle_person_library(handle: int, params: dict) -> None:
    """Plugin entry for library movies or shows featuring an actor, by TMDB credit or cast link."""
    try:
        info_type = params.get('info_type', [''])[0]
        person_name = params.get('person_name', [''])[0]
        person_id = params.get('person_id', [''])[0]

        if info_type not in ('movies', 'tvshows'):
            log("Plugin", f"Person Library: Invalid info_type '{info_type}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        if not person_id and not person_name:
            log("Plugin", "Person Library: Missing required parameters", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        dbtype = 'movie' if info_type == 'movies' else 'tvshow'

        from lib.kodi.client import KODI_ID_KEYS
        id_key = KODI_ID_KEYS[dbtype]

        items = _library_from_filmography(person_id, dbtype) if person_id else []
        if person_name:
            seen = {item.get(id_key) for item in items}
            for item in _library_from_actor_link(person_name, dbtype):
                if item.get(id_key) not in seen:
                    items.append(item)

        items.sort(key=lambda item: (-(item.get('year') or 0),
                                     (item.get('title') or '').lower()))

        for item in items:
            xbmcplugin.addDirectoryItem(handle, '', _create_library_listitem(item, dbtype), False)

        xbmcplugin.setContent(handle, info_type)
        xbmcplugin.endOfDirectory(handle, succeeded=True)

    except Exception as e:
        log("Plugin", f"Person Library: Error - {e}", xbmc.LOGERROR)
        import traceback
        log("Plugin", traceback.format_exc(), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def _library_from_filmography(person_id: str, dbtype: str) -> List[dict]:
    """Library items whose TMDB id appears in the person's filmography."""
    from lib.data.api.person import get_person_data
    from lib.data.database.rollcall import get_dbids_by_tmdb
    from lib.kodi.client import get_item_details

    try:
        person_data = get_person_data(int(person_id))
    except (ValueError, TypeError):
        log("Plugin", f"Person Library: Invalid person_id '{person_id}'", xbmc.LOGWARNING)
        return []

    if not person_data:
        return []

    media_type = 'movie' if dbtype == 'movie' else 'tv'
    roles: Dict[str, str] = {}
    for credit in person_data.get('combined_credits', {}).get('cast', []):
        if credit.get('media_type') != media_type:
            continue
        tmdb_id = str(credit.get('id') or '')
        if tmdb_id and tmdb_id not in roles:
            roles[tmdb_id] = credit.get('character', '')

    items = []
    properties = ['title', 'year', 'rating', 'playcount', 'art']
    for tmdb_id, dbid in get_dbids_by_tmdb(dbtype, roles).items():
        details = get_item_details(dbtype, dbid, properties)
        if not details:
            continue
        details['_role'] = roles.get(tmdb_id, '')
        items.append(details)

    return items


def _library_from_actor_link(person_name: str, dbtype: str) -> List[dict]:
    """Library items Kodi links to the actor by name; show-level links hold main cast only."""
    from lib.kodi.client import request

    method, result_key = (
        ('VideoLibrary.GetMovies', 'movies') if dbtype == 'movie'
        else ('VideoLibrary.GetTVShows', 'tvshows')
    )
    result = request(method, {
        'filter': {'field': 'actor', 'operator': 'is', 'value': person_name},
        'properties': ['title', 'year', 'rating', 'playcount', 'art', 'cast']
    })

    items = extract_result(result, result_key, [])
    for item in items:
        for actor in item.get('cast', []):
            if actor.get('name') == person_name:
                item['_role'] = actor.get('role', '')
                break
    return items


def _create_library_listitem(item: dict, dbtype: str) -> xbmcgui.ListItem:
    """Create a ListItem for a library movie or show in the person containers."""
    title = item.get('title', 'Unknown')
    year = item.get('year', '')

    label = f"{title} ({year})" if year else title
    listitem = xbmcgui.ListItem(label, offscreen=True)

    video_tag = listitem.getVideoInfoTag()
    video_tag.setMediaType(dbtype)
    video_tag.setTitle(title)

    dbid = item.get('movieid' if dbtype == 'movie' else 'tvshowid')
    if dbid:
        video_tag.setDbId(dbid)

    listitem.setProperty('title', title)
    if year:
        video_tag.setYear(int(year))
        listitem.setProperty('year', str(year))

    rating = item.get('rating')
    if rating:
        listitem.setProperty('rating', format_rating(rating))

    playcount = item.get('playcount')
    if playcount:
        listitem.setProperty('playcount', str(playcount))

    role = item.get('_role', '')
    if role:
        listitem.setProperty('role', role)
        listitem.setLabel2(role)

    art = item.get('art', {})
    if art:
        listitem.setArt(art)

    return listitem


_CREDIT_DBTYPES = (('movie', 'movie'), ('tv', 'tvshow'))


def _library_dbid_map(credits: list) -> dict:
    """DBIDs for the credits that are in the library, keyed by `(media_type, tmdb_id)`."""
    from lib.data.database.rollcall import get_dbids_by_tmdb

    mapping: dict = {}
    for media_type, dbtype in _CREDIT_DBTYPES:
        tmdb_ids = [c.get('id') for c in credits if c.get('media_type') == media_type]
        for tmdb_id, dbid in get_dbids_by_tmdb(dbtype, tmdb_ids).items():
            mapping[(media_type, tmdb_id)] = dbid
    return mapping


def _create_credit_listitem(credit: dict, library_dbids: Optional[dict] = None) -> xbmcgui.ListItem:
    """Create a ListItem for a TMDB credit, flagged with its dbid when it is in the library."""
    title = credit.get('title') or credit.get('name', 'Unknown')
    item = xbmcgui.ListItem(title, offscreen=True)

    video_tag = item.getVideoInfoTag()

    media_type = credit.get('media_type', 'movie')
    video_tag.setMediaType('tvshow' if media_type == 'tv' else media_type)

    video_tag.setTitle(title)

    if credit.get('overview'):
        video_tag.setPlot(credit['overview'])

    release_date = credit.get('release_date') or credit.get('first_air_date')
    if release_date:
        try:
            year = int(release_date[:4])
            video_tag.setYear(year)
        except (ValueError, TypeError, IndexError):
            pass

    if credit.get('vote_average'):
        video_tag.setRating(float(credit['vote_average']))

    art = {}
    if credit.get('poster_path'):
        art['poster'] = tmdb_image_url(credit['poster_path'], 'w500')
    if credit.get('backdrop_path'):
        art['fanart'] = tmdb_image_url(credit['backdrop_path'], 'w780')
    if art:
        item.setArt(art)

    tmdb_id = credit.get('id')
    if tmdb_id:
        item.setProperty('tmdb_id', str(tmdb_id))
        dbid = (library_dbids or {}).get((media_type, str(tmdb_id)))
        if dbid:
            item.setProperty('dbid', str(dbid))
            item.setProperty('isinlibrary', 'true')

    character = credit.get('character', '')
    item.setProperty('role', character)
    item.setProperty('releasedate', release_date or '')
    if character:
        item.setLabel2(character)
    item.setProperty('mediatype', media_type)

    return item


def handle_crew_list(handle: int, params: dict) -> None:
    """Plugin entry for a title's directors, writers or creators, by dbid or `tmdb_id`."""
    from lib.data.api import person as person_api
    from lib.data.api.person import library_tmdb_id

    crew_type = params.get('crew_type', [''])[0]
    dbtype = params.get('dbtype', [''])[0]
    dbid_str = params.get('dbid', [''])[0]
    tmdb_id_str = params.get('tmdb_id', [''])[0]

    if not dbtype:
        log("Plugin", "Crew List: Missing required parameters (dbtype)", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if not dbid_str and not tmdb_id_str:
        log(
            "Plugin",
            "Crew List: Missing required parameters (need tmdb_id or dbid)",
            xbmc.LOGWARNING,
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if crew_type and crew_type not in ('director', 'writer', 'creator', 'all'):
        log("Plugin", f"Crew List: Invalid crew_type '{crew_type}'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if crew_type == 'creator' and dbtype != 'tvshow':
        log("Plugin", "Crew List: creator only valid for tvshow", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    tmdb_id: int = 0
    if tmdb_id_str:
        try:
            tmdb_id = int(tmdb_id_str)
        except (ValueError, TypeError):
            tmdb_id = 0

    if not tmdb_id:
        try:
            dbid = int(dbid_str)
        except (ValueError, TypeError):
            log("Plugin", f"Crew List: Invalid dbid '{dbid_str}'", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        resolved = library_tmdb_id(dbtype, dbid)
        tmdb_id = resolved or 0
        if not tmdb_id:
            log(
                "Plugin",
                f"Crew List: Could not resolve TMDB ID for {dbtype} {dbid}",
                xbmc.LOGWARNING,
            )
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

    crew_list = person_api.get_crew_from_tmdb(crew_type, tmdb_id, dbtype)

    if not crew_list:
        log("Plugin", f"Crew List: No {crew_type}s found for {dbtype} tmdb={tmdb_id}",
            xbmc.LOGDEBUG)
        xbmcplugin.endOfDirectory(handle, succeeded=True)
        return

    for member in crew_list:
        name = member.get('name', 'Unknown')
        item = xbmcgui.ListItem(label=name, offscreen=True)

        if member.get('job'):
            item.setLabel2(member['job'])

        profile_path = member.get('profile_path')
        if profile_path:
            image_url = tmdb_image_url(profile_path, 'h632')
            item.setArt({'thumb': image_url, 'icon': image_url})
        else:
            item.setArt({'thumb': 'DefaultActor.png', 'icon': 'DefaultActor.png'})

        person_id = member.get('id')
        if person_id:
            item.setProperty('person_id', str(person_id))

        item.setProperty('job', member.get('job', ''))

        xbmcplugin.addDirectoryItem(handle, '', item, False)

    xbmcplugin.setContent(handle, 'actors')
    xbmcplugin.endOfDirectory(handle, succeeded=True)

    log(
        "Plugin",
        f"Crew List: Returned {len(crew_list)} {crew_type}s for {dbtype} tmdb={tmdb_id}",
        xbmc.LOGDEBUG,
    )


def handle_tmdb_details(handle: int, params: dict) -> None:
    """Plugin entry for one TMDB movie, show or person as a ListItem, by `tmdb_id`."""
    from lib.data.api.tmdb import ApiTmdb

    media_type = params.get('type', ['movie'])[0]
    tmdb_id_str = params.get('tmdb_id', [''])[0]

    if not tmdb_id_str:
        log("Plugin", "TMDB Details: Missing tmdb_id", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    try:
        tmdb_id = int(tmdb_id_str)
    except (ValueError, TypeError):
        log("Plugin", f"TMDB Details: Invalid tmdb_id '{tmdb_id_str}'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if media_type == 'person':
        from lib.data.api import person as person_api
        person_data = person_api.get_person_data(tmdb_id)
        if not person_data:
            log("Plugin", f"TMDB Details: No person data for tmdb_id={tmdb_id}", xbmc.LOGWARNING)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return

        _handle_person_details(handle, person_data)
        return

    api = ApiTmdb()

    if media_type in ('movie', 'tv'):
        data = api.get_complete_data('movie' if media_type == 'movie' else 'tvshow', tmdb_id,
                                     is_library_item=False)
    else:
        log("Plugin", f"TMDB Details: Invalid type '{media_type}'", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    if not data:
        log("Plugin", f"TMDB Details: No data for {media_type} tmdb_id={tmdb_id}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    title = data.get('title' if media_type == 'movie' else 'name', 'Unknown')
    listitem = xbmcgui.ListItem(title, offscreen=True)

    video_tag = listitem.getVideoInfoTag()
    video_tag.setMediaType(media_type if media_type == 'movie' else 'tvshow')
    video_tag.setTitle(title)

    listitem.setProperty('tmdb_id', str(tmdb_id))

    if data.get('overview'):
        video_tag.setPlot(data['overview'])

    if data.get('tagline'):
        video_tag.setTagLine(data['tagline'])

    if data.get('original_title' if media_type == 'movie' else 'original_name'):
        video_tag.setOriginalTitle(
            data.get('original_title' if media_type == 'movie' else 'original_name')
        )

    if media_type == 'movie':
        if data.get('release_date'):
            try:
                year = int(data['release_date'][:4])
                video_tag.setYear(year)
            except (ValueError, TypeError):
                pass
            video_tag.setPremiered(data['release_date'])
        if data.get('runtime'):
            video_tag.setDuration(data['runtime'] * 60)
    else:
        if data.get('first_air_date'):
            try:
                year = int(data['first_air_date'][:4])
                video_tag.setYear(year)
            except (ValueError, TypeError):
                pass
            video_tag.setPremiered(data['first_air_date'])

    if data.get('vote_average'):
        video_tag.setRating(data['vote_average'])
    if data.get('vote_count'):
        video_tag.setVotes(data['vote_count'])

    if data.get('genres'):
        genres = [g['name'] for g in data['genres']]
        video_tag.setGenres(genres)

    if data.get('production_companies'):
        studios = [s['name'] for s in data['production_companies']]
        video_tag.setStudios(studios)

    if data.get('production_countries'):
        countries = [c['name'] for c in data['production_countries']]
        video_tag.setCountries(countries)

    credits = data.get('credits', {})
    if credits.get('cast'):
        cast_list = []
        for person in credits['cast'][:20]:
            cast_member = xbmc.Actor(
                person.get('name', ''),
                person.get('character', ''),
                order=person.get('order', 0),
                thumbnail=tmdb_image_url(person.get('profile_path'), 'w500')
            )
            cast_list.append(cast_member)
        video_tag.setCast(cast_list)

    if credits.get('crew'):
        directors = [c['name'] for c in credits['crew'] if c.get('job') == 'Director']
        if directors:
            video_tag.setDirectors(directors)

        writers = [
            c['name'] for c in credits['crew']
            if c.get('job') in ('Writer', 'Screenplay', 'Story')
        ]
        if writers:
            video_tag.setWriters(writers)

    release_dates = data.get('release_dates' if media_type == 'movie' else 'content_ratings', {})
    if media_type == 'movie' and release_dates.get('results'):
        for country in release_dates['results']:
            if country.get('iso_3166_1') == 'US' and country.get('release_dates'):
                for rd in country['release_dates']:
                    if rd.get('certification'):
                        video_tag.setMpaa(rd['certification'])
                        break
                break
    elif media_type == 'tv' and release_dates.get('results'):
        for rating in release_dates['results']:
            if rating.get('iso_3166_1') == 'US' and rating.get('rating'):
                video_tag.setMpaa(rating['rating'])
                break

    external_ids = data.get('external_ids', {})
    if external_ids.get('imdb_id'):
        video_tag.setIMDBNumber(external_ids['imdb_id'])

    videos = data.get('videos', {})
    if videos.get('results'):
        trailers = [
            v for v in videos['results']
            if v.get('type') == 'Trailer' and v.get('site') == 'YouTube'
        ]
        if trailers:
            trailer_url = f"plugin://plugin.video.youtube/play/?video_id={trailers[0]['key']}"
            video_tag.setTrailer(trailer_url)

    if data.get('keywords'):
        if media_type == 'movie':
            keywords = [k['name'] for k in data['keywords'].get('keywords', [])]
        else:
            keywords = [k['name'] for k in data['keywords'].get('results', [])]
        if keywords:
            video_tag.setTags(keywords)

    art = {}
    if data.get('poster_path'):
        art['poster'] = tmdb_image_url(data['poster_path'], 'w500')
    if data.get('backdrop_path'):
        art['fanart'] = tmdb_image_url(data['backdrop_path'])

    images = data.get('images', {})
    clearlogo = pick_clearlogo(images.get('logos'))
    if clearlogo:
        art['clearlogo'] = clearlogo

    if art:
        listitem.setArt(art)

    xbmcplugin.addDirectoryItem(handle, '', listitem, False)
    xbmcplugin.endOfDirectory(handle)

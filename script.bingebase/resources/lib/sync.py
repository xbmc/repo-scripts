import time

from resources.lib.utils import (
    get_setting, get_setting_bool, set_setting, jsonrpc,
    get_show_uniqueids_by_tvshowid, log_error, notify
)


def _to_kodi_datetime(iso_string):
    """Convert ISO 8601 (e.g. '2025-08-08T18:53:08Z') to Kodi format ('2025-08-08 18:53:08')."""
    return iso_string.replace('T', ' ').replace('Z', '')


def get_watched_movies():
    result = jsonrpc('VideoLibrary.GetMovies', {
        'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'},
        'properties': ['title', 'year', 'playcount', 'lastplayed', 'uniqueid'],
    })
    if result and 'movies' in result:
        return result['movies']
    return []


def get_watched_episodes():
    result = jsonrpc('VideoLibrary.GetEpisodes', {
        'filter': {'field': 'playcount', 'operator': 'greaterthan', 'value': '0'},
        'properties': ['title', 'showtitle', 'season', 'episode', 'playcount', 'lastplayed', 'uniqueid', 'tvshowid'],
    })
    if result and 'episodes' in result:
        return result['episodes']
    return []


def get_all_movies():
    result = jsonrpc('VideoLibrary.GetMovies', {
        'properties': ['title', 'year', 'playcount', 'uniqueid'],
    })
    if result and 'movies' in result:
        return result['movies']
    return []


def get_all_episodes():
    result = jsonrpc('VideoLibrary.GetEpisodes', {
        'properties': ['title', 'showtitle', 'season', 'episode', 'playcount', 'uniqueid'],
    })
    if result and 'episodes' in result:
        return result['episodes']
    return []


def _format_movie_for_import(movie):
    return {
        'title': movie.get('title', ''),
        'year': movie.get('year', 0),
        'playcount': movie.get('playcount', 1),
        'lastplayed': movie.get('lastplayed', ''),
        'uniqueIds': movie.get('uniqueid', {}),
    }


def _format_episode_for_import(episode, show_uids_cache):
    # Look up show-level IDs, using cache to avoid repeated JSON-RPC calls
    tvshowid = episode.get('tvshowid')
    if tvshowid and tvshowid not in show_uids_cache:
        show_uids_cache[tvshowid] = get_show_uniqueids_by_tvshowid(tvshowid)
    show_uids = show_uids_cache.get(tvshowid, {})

    return {
        'title': episode.get('title', ''),
        'tvShowTitle': episode.get('showtitle', ''),
        'season': episode.get('season', 0),
        'episode': episode.get('episode', 0),
        'playcount': episode.get('playcount', 1),
        'lastplayed': episode.get('lastplayed', ''),
        'uniqueIds': episode.get('uniqueid', {}),
        'showUniqueIds': {
            'tmdb': show_uids.get('tmdb', ''),
            'tvdb': show_uids.get('tvdb', ''),
            'imdb': show_uids.get('imdb', ''),
        },
    }


def import_kodi_to_bingebase(api):
    movies = get_watched_movies()
    episodes = get_watched_episodes()

    formatted_movies = [_format_movie_for_import(m) for m in movies]
    show_uids_cache = {}
    formatted_episodes = [_format_episode_for_import(e, show_uids_cache) for e in episodes]

    if not formatted_movies and not formatted_episodes:
        return 0, 0

    api.import_history(formatted_movies, formatted_episodes)
    return len(formatted_movies), len(formatted_episodes)


def _extract_uniqueids(item):
    """Extract unique IDs from a Bingebase item, handling both formats:
    - Nested: {"uniqueIds": {"tmdb": "123"}}
    - Flat: {"tmdb_id": "123"}
    """
    uids = item.get('uniqueIds', {})
    if uids:
        return uids
    # Flat format from API
    result = {}
    for key_suffix, id_type in [('tmdb_id', 'tmdb'), ('tvdb_id', 'tvdb'), ('imdb_id', 'imdb')]:
        val = item.get(key_suffix, '')
        if val:
            result[id_type] = str(val)
    return result


def _find_kodi_item(kodi_items, uniqueids):
    for item in kodi_items:
        kodi_uids = item.get('uniqueid', {})
        for id_type in ('tmdb', 'tvdb', 'imdb'):
            bingebase_id = str(uniqueids.get(id_type, ''))
            kodi_id = str(kodi_uids.get(id_type, ''))
            if bingebase_id and kodi_id and bingebase_id == kodi_id:
                return item
    return None


def export_bingebase_to_kodi(api, since=None):
    data = api.export_history(since=since)

    if not data:
        return 0

    bb_movies = data.get('movies', [])
    bb_episodes = data.get('episodes', [])
    kodi_movies = get_all_movies()
    kodi_episodes = get_all_episodes()
    marked_count = 0

    for movie in bb_movies:
        uids = _extract_uniqueids(movie)
        match = _find_kodi_item(kodi_movies, uids)
        if match and match.get('playcount', 0) == 0:
            params = {
                'movieid': match['movieid'],
                'playcount': 1,
            }
            watched_at = movie.get('watched_at', '')
            if watched_at:
                params['lastplayed'] = _to_kodi_datetime(watched_at)
            jsonrpc('VideoLibrary.SetMovieDetails', params)
            marked_count += 1

    for episode in bb_episodes:
        uids = _extract_uniqueids(episode)
        match = _find_kodi_item(kodi_episodes, uids)
        if match and match.get('playcount', 0) == 0:
            params = {
                'episodeid': match['episodeid'],
                'playcount': 1,
            }
            watched_at = episode.get('watched_at', '')
            if watched_at:
                params['lastplayed'] = _to_kodi_datetime(watched_at)
            jsonrpc('VideoLibrary.SetEpisodeDetails', params)
            marked_count += 1

    return marked_count


def do_sync(api):
    notify('Syncing...')

    try:
        if get_setting_bool('sync_kodi_to_bingebase'):
            import_kodi_to_bingebase(api)

        last_sync = _get_last_sync_timestamp()

        if get_setting_bool('sync_bingebase_to_kodi'):
            export_bingebase_to_kodi(api, since=last_sync)

        _save_last_sync_timestamp()
        notify('Sync complete')

    except Exception:
        log_error('Sync failed')
        import xbmcgui
        notify('Sync failed', icon=xbmcgui.NOTIFICATION_ERROR)


def _get_last_sync_timestamp():
    ts = get_setting('last_sync_timestamp')
    return ts if ts else None


def _save_last_sync_timestamp():
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    set_setting('last_sync_timestamp', ts)

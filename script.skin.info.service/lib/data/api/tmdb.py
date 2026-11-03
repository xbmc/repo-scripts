"""TMDB API access: the ApiTmdb client, image format transforms and ID resolution."""
from __future__ import annotations

import xbmc
from typing import Optional, Dict, List, Sequence

from lib.data.api.client import ApiSession
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.utilities import tmdb_image_url, is_valid_tmdb_id, decode_key
from lib.kodi.client import log
from lib.data.api.source import RatingSource
from lib.data.api import tracker as usage_tracker
from lib.kodi.settings import KodiSettings


def _get_metadata_language() -> str:
    """Get language code for TMDb API requests."""
    lang = KodiSettings.online_metadata_language()
    # TMDb expects codes like 'zh-CN', 'pt-BR' (region part uppercase)
    if '-' in lang:
        parts = lang.split('-')
        return f"{parts[0]}-{parts[1].upper()}"
    return lang


def _fill_episode_runtime(data: dict) -> None:
    """Fill a missing episode runtime from the first season's median, dropping that season."""
    season = data.pop("season/1", None) or {}
    if data.get("episode_run_time"):
        return
    runtimes = sorted(e["runtime"] for e in season.get("episodes") or [] if e.get("runtime"))
    if runtimes:
        data["episode_run_time"] = [runtimes[(len(runtimes) - 1) // 2]]


def format_tmdb_image(image: dict, preview_size: str, rank: int) -> Optional[dict]:
    """Format a TMDB image entry to the common artwork format, keeping its place in TMDB's order."""
    file_path = image.get('file_path')
    if not file_path:
        return None

    # Kodi cannot render SVG
    if file_path.lower().endswith('.svg'):
        return None

    return {
        'url': tmdb_image_url(file_path),
        'previewurl': tmdb_image_url(file_path, preview_size),
        'width': image.get('width', 0),
        'height': image.get('height', 0),
        'rating': image.get('vote_average', 0),
        'language': image.get('iso_639_1') or '',
        'source': 'TMDB',
        'rank': rank,
    }


def transform_tmdb_images(data: dict) -> Dict[str, List[dict]]:
    """Transform a TMDB images response to common format; untagged posters double as keyart."""
    result: Dict[str, List[dict]] = {}

    logos = data.get('logos') or []
    formatted_logos = [format_tmdb_image(entry, 'w500', i) for i, entry in enumerate(logos)]
    formatted_logos = [entry for entry in formatted_logos if entry]
    if formatted_logos:
        result['clearlogo'] = formatted_logos

    posters = data.get('posters') or []
    keyart = []
    all_posters = []
    for i, poster in enumerate(posters):
        formatted = format_tmdb_image(poster, 'w500', i)
        if formatted:
            all_posters.append(formatted)
            if not poster.get('iso_639_1'):
                keyart.append(formatted)
    if all_posters:
        result['poster'] = all_posters
    if keyart:
        result['keyart'] = keyart

    backdrops = data.get('backdrops') or []
    if not backdrops:
        return result

    user_lang = _get_metadata_language().split('-')[0].lower()

    formatted_backdrops: List[tuple[dict, str | None]] = []
    for i, backdrop in enumerate(backdrops):
        formatted = format_tmdb_image(backdrop, 'w780', i)
        if formatted:
            lang = backdrop.get('iso_639_1')
            formatted_backdrops.append((formatted, lang.lower() if lang else None))

    def lang_sort_key(item: tuple[dict, str | None]) -> tuple[int, str]:
        """Order artwork by language: the user's first, then English, then untagged."""
        lang = item[1]
        if lang == user_lang:
            return (0, '')
        if lang == 'en' and user_lang != 'en':
            return (1, '')
        if lang is None or lang == 'xx':
            return (2, '')
        return (3, lang or '')

    formatted_backdrops.sort(key=lang_sort_key)

    all_backdrops = [item[0] for item in formatted_backdrops]

    if all_backdrops:
        result['fanart'] = all_backdrops
        result['landscape'] = all_backdrops

    return result


def resolve_tmdb_id(tmdb_id: str | None, imdb_id: str | None, media_type: str) -> str | None:
    """Resolve a valid TMDB ID, correcting invalid ones via IMDB lookup if possible."""
    if is_valid_tmdb_id(tmdb_id):
        return tmdb_id

    if not imdb_id:
        return None

    from lib.data.database.mapping import (
        get_tmdb_id_by_imdb, is_known_find_miss, save_find_miss, save_id_mapping,
    )
    mapped = get_tmdb_id_by_imdb(imdb_id, media_type)
    if mapped:
        return mapped

    if is_known_find_miss(imdb_id, media_type):
        return None

    api = ApiTmdb()
    found_id = api.find_by_imdb(imdb_id, media_type)
    if found_id:
        save_id_mapping(str(found_id), media_type, imdb_id=imdb_id)
        log("TMDB", f"Corrected invalid TMDB ID for {imdb_id} -> {found_id}", xbmc.LOGDEBUG)
        return str(found_id)

    save_find_miss(imdb_id, media_type)
    return None


class ApiTmdb(RatingSource):
    """TMDB client for artwork, ratings, details, search and discovery lists."""

    BASE_URL = "https://api.themoviedb.org/3"

    API_KEY = decode_key("MDE0MmEyMmM1NjBjZTNlZmIxY2ZkNmYzYjJmYWFiNzc=")
    MAX_APPEND_SEASONS = 20

    def __init__(self):
        super().__init__("tmdb")
        self.session = ApiSession(
            service_name="TMDB",
            base_url=self.BASE_URL,
            timeout=(5.0, 10.0),
            max_retries=3,
            backoff_factor=0.5,
            rate_limit=(35, 1.0),
            default_headers={
                "Accept": "application/json"
            }
        )

    def get_api_key(self) -> str:
        """Get TMDB API key. Uses user's custom key if enabled, else falls back to built-in."""
        use_custom = KodiSettings.tmdb_use_custom_key()
        if use_custom:
            user_key = KodiSettings.tmdb_api_key()
            if user_key:
                return user_key

        return self.API_KEY.strip()

    def _make_request(
        self,
        endpoint: str,
        abort_flag=None
    ) -> Optional[dict]:
        """Make HTTP request to TMDB API with rate limiting and retry."""
        api_key = self.get_api_key()
        return self.session.get(
            endpoint,
            params={"api_key": api_key},
            abort_flag=abort_flag
        )

    def get_collection_images(self, collection_id: int) -> dict:
        """Get all available images for a movie collection from TMDB."""
        return self._fetch_images('collection', collection_id)

    def get_collection(self, collection_id: int, abort_flag=None) -> list:
        """Member movies of a TMDB collection (franchise parts); cached ~30 days."""
        from lib.data.database import cache as db_cache
        key = str(collection_id)
        cached = db_cache.get_cached_metadata('collection', key)
        if cached:
            return cached.get('parts', [])
        data = self._make_request(f"/collection/{collection_id}", abort_flag)
        if not data:
            return []
        parts = data.get('parts', [])
        db_cache.cache_metadata('collection', key, {'parts': parts}, None, ttl_hours=720)
        return parts

    def get_season_images(self, tmdb_id: int, season_number: int, abort_flag=None) -> dict:
        """Get all available images for a TV season from TMDB."""
        data = self._make_request(
            f"/tv/{tmdb_id}/season/{season_number}/images",
            abort_flag
        )

        if not data:
            return {}

        return transform_tmdb_images(data)

    def get_episode_images(
        self,
        tmdb_id: int,
        season_number: int,
        episode_number: int,
        abort_flag=None
    ) -> dict:
        """Get all available images for a TV episode from TMDB."""
        data = self._make_request(
            f"/tv/{tmdb_id}/season/{season_number}/episode/{episode_number}/images",
            abort_flag
        )

        if not data:
            return {}

        stills = data.get('stills', [])
        result = {}
        if stills:
            formatted = [format_tmdb_image(img, 'w300', i) for i, img in enumerate(stills)]
            result['thumb'] = [img for img in formatted if img]

        return result

    def _fetch_images(self, media_kind: str, tmdb_id: int, abort_flag=None) -> dict:
        """Fetch images for any TMDB media kind, transformed to common format."""
        data = self._make_request(f"/{media_kind}/{tmdb_id}/images", abort_flag)

        if not data:
            return {}

        return transform_tmdb_images(data)

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from TMDB (RatingSource interface); episodes read the prefetch cache."""
        if abort_flag and abort_flag.is_requested():
            return None

        if usage_tracker.is_provider_skipped("tmdb"):
            return None

        tmdb_id_str = ids.get("tmdb") or ""
        if not is_valid_tmdb_id(tmdb_id_str):
            return None

        if media_type == "episode":
            return self._episode_ratings(int(tmdb_id_str), ids, abort_flag, force_refresh)

        try:
            complete_data = self.get_complete_data(
                media_type, int(tmdb_id_str), abort_flag=abort_flag, force_refresh=force_refresh
            )

            if not complete_data:
                return None

            rating = complete_data.get("vote_average")
            votes = complete_data.get("vote_count")

            if rating is None or votes is None:
                return None

            rating_key = "themoviedb" if media_type == "movie" else "tmdb"
            result = {
                rating_key: {
                    "rating": self.normalize_rating(rating, 10),
                    "votes": float(votes)
                },
                "_source": "tmdb"
            }

            return result

        except (RateLimitHit, RetryableError):
            raise
        except Exception as e:
            log("Ratings", f"TMDB fetch error: {str(e)}", xbmc.LOGWARNING)
            return None

    def test_connection(self) -> bool:
        """Test TMDB API connection."""
        try:
            details = self._make_request("/movie/550")
            return details is not None
        except Exception as e:
            log("Ratings", f"TMDB test connection error: {str(e)}", xbmc.LOGWARNING)
            return False

    _FIND_RESULT_KEYS = {
        "movie": "movie_results",
        "tvshow": "tv_results",
        "episode": "tv_episode_results",
    }

    def find_by_external_id(self, external_id: str, source: str, media_type: str = "movie",
                            abort_flag=None) -> Optional[dict]:
        """Find an external id via the id_mappings cache, then /find; a cache hit is id-only."""
        if media_type in ("movie", "tvshow") and source in ("imdb_id", "tvdb_id"):
            from lib.data.database.mapping import (
                get_tmdb_id_by_imdb, get_tmdb_id_by_tvdb,
            )
            lookup = get_tmdb_id_by_imdb if source == "imdb_id" else get_tmdb_id_by_tvdb
            cached_tmdb_id = lookup(external_id, media_type)
            if cached_tmdb_id:
                return {"id": int(cached_tmdb_id)}

        api_key = self.get_api_key()
        data = self.session.get(
            f"/find/{external_id}",
            params={"api_key": api_key, "external_source": source},
            abort_flag=abort_flag,
        )
        if not data:
            return None
        result_key = self._FIND_RESULT_KEYS.get(media_type, "movie_results")
        results = data.get(result_key, [])
        first = results[0] if results else None

        if first and media_type in ("movie", "tvshow") and source in ("imdb_id", "tvdb_id"):
            from lib.data.database.mapping import save_id_mapping
            tmdb_id = first.get("id")
            if tmdb_id:
                save_id_mapping(
                    str(tmdb_id), media_type,
                    imdb_id=external_id if source == "imdb_id" else None,
                    tvdb_id=external_id if source == "tvdb_id" else None,
                )

        return first

    def find_by_imdb(self, imdb_id: str, media_type: str, abort_flag=None) -> int | None:
        """Find TMDB ID by IMDB ID using TMDB's find endpoint."""
        if not imdb_id or not imdb_id.startswith("tt"):
            return None
        try:
            result = self.find_by_external_id(imdb_id, "imdb_id", media_type, abort_flag)
            return result.get("id") if result else None
        except Exception as e:
            log("TMDB", f"Find by IMDB error: {str(e)}", xbmc.LOGWARNING)
            return None

    def get_complete_data(
        self,
        media_type: str,
        tmdb_id: int,
        release_date: Optional[str] = None,
        abort_flag=None,
        force_refresh: bool = False,
        is_library_item: bool = True
    ) -> Optional[dict]:
        """Get complete movie or tvshow data from cache or TMDB; non-library items cache for 24h."""
        if abort_flag and abort_flag.is_requested():
            return None

        from lib.data.database import cache as db_cache

        if not force_refresh:
            cached = db_cache.get_cached_metadata(media_type, str(tmdb_id))
            if cached:
                return cached

        if abort_flag and abort_flag.is_requested():
            return None

        if media_type == 'movie':
            data = self.get_movie_details_extended(tmdb_id, abort_flag)
        elif media_type == 'tvshow':
            data = self.get_tv_details_extended(tmdb_id, abort_flag)
            if data and is_library_item:
                self._fix_stale_episodes(data, tmdb_id, abort_flag)
        else:
            return None

        if not data:
            return None

        if not release_date:
            release_date = self._extract_release_date(data, media_type)

        if is_library_item:
            hints = self._build_cache_hints(data, media_type)
        else:
            hints = {"is_library_item": False}

        db_cache.cache_metadata(media_type, str(tmdb_id), data, release_date, hints)

        self._cache_components(media_type, tmdb_id, data, release_date, hints)

        return data

    @staticmethod
    def _episode_rating_key(tmdb_id, season, episode) -> str:
        """Provider-cache key for one episode's TMDB rating."""
        return f"{tmdb_id}_s{season}e{episode}"

    def _episode_ratings(self, tmdb_id: int, ids: Dict[str, str], abort_flag=None,
                         force_refresh: bool = False) -> Optional[Dict]:
        """Episode rating from the provider cache, refetching its season on a forced refresh."""
        season, episode = ids.get("season"), ids.get("episode")
        if not season or not episode:
            return None

        if force_refresh:
            self.prefetch_episode_ratings(tmdb_id, [int(season)], abort_flag)

        cached = self.get_cached_data(
            "episode", self._episode_rating_key(tmdb_id, season, episode))
        if not cached:
            return None

        return {
            "tmdb": {"rating": cached["rating"], "votes": cached["votes"]},
            "_source": "tmdb",
        }

    def prefetch_episode_ratings(self, tmdb_id: int, seasons: List[int], abort_flag=None) -> int:
        """Cache every voted episode rating in these seasons; returns how many were stored."""
        stored = 0
        ordered = sorted(seasons)
        for start in range(0, len(ordered), self.MAX_APPEND_SEASONS):
            if abort_flag and abort_flag.is_requested():
                break
            chunk = ordered[start:start + self.MAX_APPEND_SEASONS]
            data = self._fetch_details_extended(
                f"/tv/{tmdb_id}",
                ",".join(f"season/{n}" for n in chunk),
                abort_flag=abort_flag,
            )
            if not data:
                continue
            for number in chunk:
                season = data.get(f"season/{number}")
                if isinstance(season, dict):
                    stored += self.store_episode_ratings(tmdb_id, number, season)
        return stored

    def store_episode_ratings(self, tmdb_id: int, number: int, season: dict) -> int:
        """Store the rating of every voted episode in a TMDB season response; returns the count."""
        stored = 0
        for ep in season.get("episodes") or []:
            rating, votes = ep.get("vote_average"), ep.get("vote_count")
            if rating is None or not votes:
                continue
            self.cache_data(
                "episode",
                self._episode_rating_key(tmdb_id, number, ep.get("episode_number")),
                {"rating": float(rating), "votes": float(votes)},
                ep.get("air_date") or None,
            )
            stored += 1
        return stored

    def _extract_release_date(self, data: dict, media_type: str) -> Optional[str]:
        """Extract the release, first-air or air date from a TMDb response by media type."""
        if media_type == 'movie':
            return data.get('release_date')
        elif media_type == 'tvshow':
            return data.get('first_air_date')
        elif media_type == 'episode':
            return data.get('air_date')
        return None

    def _fix_stale_episodes(self, data: dict, tmdb_id: int, abort_flag=None) -> None:
        """Fix next and last episode from fresh season data once next_episode_to_air has passed."""
        import datetime
        next_ep = data.get("next_episode_to_air")
        if not next_ep:
            return
        air_date = next_ep.get("air_date") or ""
        if not air_date or air_date >= datetime.date.today().isoformat():
            return

        season_num = next_ep.get("season_number")
        if not season_num:
            return

        season_data = self.get_season_details(tmdb_id, season_num, abort_flag, force_refresh=True)
        if not season_data or "episodes" not in season_data:
            data["next_episode_to_air"] = None
            return

        today = datetime.date.today().isoformat()
        last_aired = None
        next_unaired = None
        for ep in season_data["episodes"]:
            ep_air = ep.get("air_date") or ""
            if not ep_air:
                continue
            if ep_air < today:
                last_aired = ep
            elif not next_unaired:
                next_unaired = ep

        data["next_episode_to_air"] = next_unaired
        if last_aired:
            data["last_episode_to_air"] = last_aired

    def _build_cache_hints(self, data: dict, media_type: str) -> Dict[str, str]:
        """Build TTL hints: status, plus whether a tvshow's aired data is complete."""
        hints: Dict[str, str] = {}

        if data.get("status"):
            hints["status"] = data["status"]

        if media_type != 'tvshow':
            return hints

        has_overview = bool(data.get("overview"))
        has_cast = len(data.get("credits", {}).get("cast", [])) > 0
        has_imdb = bool((data.get("external_ids") or {}).get("imdb_id"))
        has_content_ratings = len(data.get("content_ratings", {}).get("results", [])) > 0
        last_ep = data.get("last_episode_to_air")
        has_last_ep = bool(last_ep and last_ep.get("overview"))
        if has_overview and has_cast and has_imdb and has_content_ratings and has_last_ep:
            hints["aired_data_complete"] = "true"

        return hints

    _IMAGE_COMPONENTS = [
        ('posters', 'poster', 'w500'),
        ('backdrops', 'fanart', 'w780'),
        ('logos', 'clearlogo', 'w500'),
    ]

    def _cache_components(self, media_type: str, tmdb_id: int, data: dict,
                          release_date: Optional[str], hints: Optional[dict] = None) -> None:
        """Cache poster/backdrop/logo lists from a complete TMDB response into artwork_cache."""
        from lib.data.database import cache as db_cache

        ttl_hours = db_cache.get_cache_ttl_hours(release_date, hints)
        images = data.get('images') or {}
        if not images:
            return

        for response_key, art_type, preview_size in self._IMAGE_COMPONENTS:
            entries = images.get(response_key) or []
            if not entries:
                continue
            formatted = [format_tmdb_image(img, preview_size, i) for i, img in enumerate(entries)]
            formatted = [img for img in formatted if img]
            if formatted:
                db_cache.cache_artwork(media_type, str(tmdb_id), 'tmdb', art_type,
                                 formatted, release_date, ttl_hours)

    def _fetch_details_extended(self, endpoint: str, append: str,
                                 include_image_language: bool = False,
                                 abort_flag=None) -> Optional[dict]:
        """Shared `append_to_response` fetch for movie/tv/episode detail endpoints."""
        api_key = self.get_api_key()
        language = _get_metadata_language()
        params = {
            "api_key": api_key,
            "language": language,
            "append_to_response": append,
        }
        if include_image_language:
            lang_code = language.split('-')[0]
            params["include_image_language"] = f"{lang_code},en,null"
        return self.session.get(endpoint, params=params, abort_flag=abort_flag)

    def get_movie_details_extended(self, tmdb_id: int, abort_flag=None) -> Optional[dict]:
        """Fetch complete movie data in one API call. Returns base details plus appended data."""
        return self._fetch_details_extended(
            f"/movie/{tmdb_id}",
            "credits,videos,keywords,release_dates,images,external_ids,recommendations",
            include_image_language=True,
            abort_flag=abort_flag,
        )

    def get_tv_details_extended(self, tmdb_id: int, abort_flag=None) -> Optional[dict]:
        """Fetch complete TV show data in one call, filling a missing runtime from season 1."""
        data = self._fetch_details_extended(
            f"/tv/{tmdb_id}",
            "credits,aggregate_credits,videos,keywords,content_ratings,images,external_ids,"
            "recommendations,season/1",
            include_image_language=True,
            abort_flag=abort_flag,
        )
        if data:
            _fill_episode_runtime(data)
        return data

    def get_episode_details_extended(self, tmdb_id: int, season: int, episode: int,
                                     abort_flag=None) -> Optional[dict]:
        """Fetch complete episode data in one API call. Returns base details plus appended data."""
        return self._fetch_details_extended(
            f"/tv/{tmdb_id}/season/{season}/episode/{episode}",
            "credits,videos,images,external_ids",
            abort_flag=abort_flag,
        )

    def get_season_details(self, tmdb_id: int, season_number: int, abort_flag=None,
                           force_refresh: bool = False) -> Optional[dict]:
        """Get season details (episodes + aggregate_credits) from cache, else API."""
        from lib.data.database import cache as db_cache

        if not force_refresh:
            cached = db_cache.get_cached_season_metadata(str(tmdb_id), season_number)
            if cached:
                return cached

        api_key = self.get_api_key()
        language = _get_metadata_language()
        data = self.session.get(
            f"/tv/{tmdb_id}/season/{season_number}",
            params={
                "api_key": api_key,
                "language": language,
                "append_to_response": "aggregate_credits",
            },
            abort_flag=abort_flag
        )

        if data:
            db_cache.cache_season_metadata(str(tmdb_id), season_number, data)

        return data

    def get_tv_season_credits(self, tmdb_id: int, season_numbers: Sequence[int],
                              abort_flag=None) -> Optional[dict]:
        """Billed cast per season, appended in one call."""
        appends = ",".join(f"season/{n}/credits" for n in season_numbers)
        return self.session.get(
            f"/tv/{tmdb_id}",
            params={
                "api_key": self.get_api_key(),
                "language": _get_metadata_language(),
                "append_to_response": appends,
            },
            abort_flag=abort_flag
        )

    def get_person_details(self, person_id: int, abort_flag=None) -> Optional[dict]:
        """Fetch person details with images, combined_credits, and external_ids appended."""
        append = "images,combined_credits,external_ids"
        api_key = self.get_api_key()
        language = _get_metadata_language()
        return self.session.get(
            f"/person/{person_id}",
            params={"api_key": api_key, "language": language, "append_to_response": append},
            abort_flag=abort_flag
        )

    def search(
        self,
        query: str,
        media_type: str = 'movie',
        year: int = 0,
        abort_flag=None
    ) -> list[dict] | None:
        """Search TMDB movies, TV shows, people or all three; None when the request fails."""
        endpoint_map = {
            'movie': '/search/movie',
            'tv': '/search/tv',
            'person': '/search/person',
            'multi': '/search/multi',
        }

        endpoint = endpoint_map.get(media_type, '/search/movie')
        api_key = self.get_api_key()
        language = _get_metadata_language()

        params: Dict[str, str | int] = {"api_key": api_key, "language": language, "query": query}
        if year > 0 and media_type in ('movie', 'tv'):
            year_param = 'year' if media_type == 'movie' else 'first_air_date_year'
            params[year_param] = year

        data = self.session.get(endpoint, params=params, abort_flag=abort_flag)
        return None if data is None else data.get('results') or []

    def _get_list(
        self,
        endpoint: str,
        page: int = 1,
        extra_params: Optional[Dict[str, str]] = None,
        abort_flag=None
    ) -> list:
        """Paged TMDB list request, carrying the configured metadata language."""
        api_key = self.get_api_key()
        language = _get_metadata_language()
        params: Dict[str, str | int] = {
            "api_key": api_key,
            "language": language,
            "page": page
        }
        if extra_params:
            params.update(extra_params)
        data = self.session.get(endpoint, params=params, abort_flag=abort_flag)
        if not data:
            return []
        if isinstance(data, dict):
            return data.get("results", [])
        return []

    def discover(self, media_type: str, filters: Dict[str, str], page: int = 1,
                 abort_flag=None) -> list:
        """Get TMDB's discover list of movies or shows, filtered and sorted as requested."""
        return self._get_list(f"/discover/{media_type}", page=page, extra_params=filters,
                              abort_flag=abort_flag)

    def get_trending(self, media_type: str, window: str = 'week', page: int = 1,
                     abort_flag=None) -> list:
        """Get TMDB's trending movies or shows for the day or week."""
        return self._get_list(f"/trending/{media_type}/{window}", page=page, abort_flag=abort_flag)

    def get_popular(self, media_type: str, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's popular movies or shows."""
        return self._get_list(f"/{media_type}/popular", page=page, abort_flag=abort_flag)

    def get_top_rated(self, media_type: str, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's top rated movies or shows."""
        return self._get_list(f"/{media_type}/top_rated", page=page, abort_flag=abort_flag)

    def get_now_playing(self, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's movies now in theaters."""
        return self._get_list("/movie/now_playing", page=page, abort_flag=abort_flag)

    def get_upcoming(self, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's upcoming movies."""
        return self._get_list("/movie/upcoming", page=page, abort_flag=abort_flag)

    def get_airing_today(self, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's shows airing today."""
        return self._get_list("/tv/airing_today", page=page, abort_flag=abort_flag)

    def get_on_the_air(self, page: int = 1, abort_flag=None) -> list:
        """Get TMDB's shows with an episode airing this week."""
        return self._get_list("/tv/on_the_air", page=page, abort_flag=abort_flag)

    def get_genre_list(self, media_type: str, force_refresh: bool = False) -> Dict[int, str]:
        """Get the TMDB genre id-to-name mapping for movies or TV, cached 24h."""
        from lib.data.database import cache as db_cache

        if not force_refresh:
            cached = db_cache.get_cached_tmdb_genre_list(media_type)
            if cached is not None:
                return cached

        api_key = self.get_api_key()
        language = _get_metadata_language()
        data = self.session.get(
            f"/genre/{media_type}/list",
            params={"api_key": api_key, "language": language}
        )
        if not data or not isinstance(data, dict):
            return {}
        mapping = {g["id"]: g["name"] for g in data.get("genres", []) if "id" in g and "name" in g}
        if mapping:
            db_cache.cache_tmdb_genre_list(media_type, mapping)
        return mapping

    @staticmethod
    def get_attribution() -> str:
        """Get required TMDB attribution text."""
        return ("This add-on uses TMDB and the TMDB APIs but is not endorsed, certified, "
                "or otherwise approved by TMDB.")

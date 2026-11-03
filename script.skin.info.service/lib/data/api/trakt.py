"""Trakt API client and the standalone IMDb Top 250 fetch."""
from __future__ import annotations

from typing import Any, Optional, Dict, List, Set, Tuple, Final
from datetime import datetime, timedelta
import json
import threading
from urllib.parse import quote
import xbmc
import xbmcvfs

from lib.data.api.client import ApiSession
from lib.data.api.source import RatingSource
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.utilities import decode_key
from lib.data.api import tracker as usage_tracker
from lib.data.database.cache import cache_trakt, get_cached_trakt
from lib.kodi.client import log

_ACTIVITY_MINUTES: Final = 1
_USER_LIST_HOURS: Final = 24
# airing episodes change these without any account activity
_AIRING_HOURS: Final = 6
_MY_SHOWS_STAMPS: Final = ("episodes.watched_at", "episodes.collected_at",
                           "shows.watchlisted_at", "shows.hidden_at")
_TRENDING_HOURS: Final = 1
_CHART_HOURS: Final = 24
_PERIOD_HOURS: Final = {"daily": 1, "weekly": 6}
_LIST_ITEMS_HOURS: Final = 6
_LIST_ITEM_TYPES: Final = {"movie": "movie", "tv": "show"}


def _stamp(activity: dict, path: str) -> str:
    """One last-change stamp from Trakt's activity map, by a path such as `watchlist.updated_at`."""
    section, _, field = path.partition(".")
    return str((activity.get(section) or {}).get(field) or "")


def _as_part(value) -> int:
    """Season or episode number as an int; -1 stands for a row that has neither."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


TRAKT_CLIENT_ID = decode_key(
    "MWM1ZmIxZDZkNjhlODk1ZDRiMmY3MzVlYTc2ODE3NDIy"
    "ZmIzMzM0ZjFlMTZmMzE0YjMyMzg1YzBlNzRmN2M4ZA=="
)
TRAKT_CLIENT_SECRET = decode_key(
    "OTQ1ODY3M2JjMDk1Y2NhZDI3YTVjZDViNzkwNTgxZTZm"
    "ZDE2N2I5ZjZhNWQyYjRlZmQxN2VjZDRiMmMzMmE1ZQ=="
)


class ApiTrakt(RatingSource):
    """Trakt client for ratings, subgenres and discovery lists, with OAuth for recommendations."""

    BASE_URL = "https://api.trakt.tv"

    def __init__(self):
        super().__init__("trakt")
        self.token_path = xbmcvfs.translatePath(
            "special://profile/addon_data/script.skin.info.service/trakt_tokens.json"
        )
        self.session = ApiSession(
            service_name="Trakt",
            base_url=self.BASE_URL,
            timeout=(3.0, 3.0),
            max_retries=2,
            backoff_factor=1.0,
            rate_limit=(3, 2.0),
            default_headers={
                "Content-Type": "application/json",
                "trakt-api-key": TRAKT_CLIENT_ID,
                "trakt-api-version": "2"
            }
        )
        self._season_locks_guard = threading.Lock()
        self._season_locks: Dict[str, threading.Lock] = {}
        self._refreshed_seasons: Set[str] = set()

    def is_authorized(self) -> bool:
        """True when a stored OAuth token exists, expired or not."""
        return self._load_tokens() is not None

    def _load_tokens(self) -> Optional[Dict]:
        """Load the stored OAuth tokens; None when the file is missing or unreadable."""
        if not xbmcvfs.exists(self.token_path):
            return None

        try:
            with open(self.token_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_tokens(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        """Save OAuth tokens with an absolute expiry; a write failure is only logged."""
        expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()

        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at
        }

        try:
            with open(self.token_path, 'w') as f:
                json.dump(tokens, f)
        except Exception as e:
            log("Ratings", f"Failed to save Trakt tokens: {str(e)}", xbmc.LOGERROR)

    def _delete_tokens(self) -> None:
        """Delete the stored OAuth tokens, ignoring failures."""
        if xbmcvfs.exists(self.token_path):
            try:
                xbmcvfs.delete(self.token_path)
            except Exception:
                pass

    def _auth_headers(self, abort_flag=None) -> Dict[str, str]:
        """Build the Authorization header for an authenticated request; empty without a token."""
        token = self._get_valid_token(abort_flag)
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _token_after_failed_refresh(self, sent_refresh: str) -> Optional[str]:
        """Access token a concurrent refresh already stored, else None after deleting the tokens."""
        stored = self._load_tokens()
        if stored and stored.get("refresh_token") != sent_refresh:
            return stored.get("access_token")
        self._delete_tokens()
        return None

    def _get_valid_token(self, abort_flag=None) -> Optional[str]:
        """Get valid access token, refreshing if needed."""
        tokens = self._load_tokens()
        if not tokens:
            return None

        expires_at = datetime.fromisoformat(tokens["expires_at"])

        if datetime.now() >= expires_at - timedelta(minutes=5):
            try:
                new_tokens = self.session.post(
                    "/oauth/token",
                    json_data={
                        "refresh_token": tokens["refresh_token"],
                        "client_id": TRAKT_CLIENT_ID,
                        "client_secret": TRAKT_CLIENT_SECRET,
                        "grant_type": "refresh_token"
                    },
                    abort_flag=abort_flag
                )

                if new_tokens:
                    self._save_tokens(
                        new_tokens["access_token"],
                        new_tokens["refresh_token"],
                        new_tokens.get("expires_in", 86400)
                    )
                    return new_tokens["access_token"]
                return self._token_after_failed_refresh(tokens["refresh_token"])

            except RateLimitHit:
                raise
            except Exception:
                return None

        return tokens["access_token"]

    def fetch_data(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False
    ) -> Optional[dict]:
        """Fetch full Trakt data for an item, cached; an episode fetches its whole season."""
        if usage_tracker.is_provider_skipped("trakt"):
            return None

        trakt_id = ids.get("trakt_slug") or ids.get("imdb")
        tmdb_id = ids.get("tmdb")
        if not trakt_id and not tmdb_id:
            return None

        cache_key = self._get_cache_key(media_type, ids)
        if not force_refresh:
            cached = self.get_cached_data(media_type, *cache_key)
            if cached:
                return cached

        try:
            headers: Dict[str, str] = {}

            if trakt_id:
                if media_type == "episode":
                    season = ids.get("season")
                    episode = ids.get("episode")
                    if not season or not episode:
                        return None
                    return self._fetch_episode_via_season(
                        trakt_id, season, cache_key, headers, abort_flag, force_refresh
                    )
                if media_type == "movie":
                    endpoint = f"/movies/{trakt_id}"
                elif media_type == "tvshow":
                    endpoint = f"/shows/{trakt_id}"
                else:
                    return None

                data = self.session.get(
                    endpoint,
                    params={"extended": "full"},
                    headers=headers,
                    abort_flag=abort_flag
                )
            else:
                if media_type == "episode":
                    return None
                search_type = "show" if media_type == "tvshow" else media_type
                # session.get is typed Dict, but this endpoint returns a JSON array
                raw: Any = self.session.get(
                    f"/search/tmdb/{tmdb_id}",
                    params={"type": search_type, "extended": "full"},
                    headers=headers,
                    abort_flag=abort_flag
                )
                if not isinstance(raw, list) or not raw:
                    return None
                data = raw[0].get(search_type)

            if data:
                self.cache_data(media_type, cache_key[0], data,
                                season=cache_key[1], episode=cache_key[2])

            return data

        except RateLimitHit:
            raise
        except RetryableError:
            raise
        except Exception as e:
            log("Trakt", f"Fetch error: {str(e)}", xbmc.LOGWARNING)
            return None

    def _get_season_lock(self, key: str) -> threading.Lock:
        """Per-(show, season) lock so concurrent episodes of one season fetch it only once."""
        with self._season_locks_guard:
            lock = self._season_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._season_locks[key] = lock
            return lock

    def _fetch_episode_via_season(
        self, trakt_id: str, season: str, cache_key: Tuple[str, int, int],
        headers: Dict[str, str], abort_flag=None, force_refresh: bool = False,
    ) -> Optional[dict]:
        """Fetch and cache the episode's whole season; forced refresh hits each season once."""
        season_key = f"{trakt_id}_s{season}"
        with self._get_season_lock(season_key):
            if not (force_refresh and season_key not in self._refreshed_seasons):
                cached = self.get_cached_data("episode", *cache_key)
                if cached:
                    return cached

            data = self.session.get(
                f"/shows/{trakt_id}/seasons/{season}",
                params={"extended": "full"},
                headers=headers,
                abort_flag=abort_flag
            )

            if not isinstance(data, list):
                return None

            for ep in data:
                if not isinstance(ep, dict):
                    continue
                ep_num = ep.get("number")
                if ep_num is None:
                    continue
                self.cache_data("episode", trakt_id, ep,
                                season=_as_part(season), episode=_as_part(ep_num))

            self._refreshed_seasons.add(season_key)
            log("Trakt", f"Fetched {len(data)} episodes for season {season}", xbmc.LOGDEBUG)

        return self.get_cached_data("episode", *cache_key)

    @staticmethod
    def _get_cache_key(media_type: str, ids: Dict[str, str]) -> Tuple[str, int, int]:
        """Cache identity for Trakt data: the id, plus season and episode for an episode row."""
        trakt_id = str(ids.get("trakt_slug") or ids.get("imdb") or ids.get("tmdb"))
        if media_type != "episode":
            return trakt_id, -1, -1
        return trakt_id, _as_part(ids.get("season")), _as_part(ids.get("episode"))

    def get_trakt_data(self, media_type: str, ids: Dict[str, str]) -> Optional[dict]:
        """Get the full cached Trakt response without fetching; None if not cached."""
        return self.get_cached_data(media_type, *self._get_cache_key(media_type, ids))

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from Trakt (RatingSource interface)."""
        data = self.fetch_data(media_type, ids, abort_flag, force_refresh=force_refresh)
        if not data:
            return None

        return self._extract_ratings(data)

    def _extract_ratings(self, data: dict) -> Optional[Dict[str, Dict[str, float]]]:
        """Extract ratings dict from full Trakt response."""
        rating = data.get("rating")
        votes = data.get("votes")

        if rating is None or votes is None:
            return None

        result: Dict[str, Dict[str, float]] = {
            "trakt": {
                "rating": self.normalize_rating(rating, 10),
                "votes": float(votes)
            }
        }
        result["_source"] = "trakt"  # type: ignore[assignment]
        return result

    def get_subgenres(
        self,
        trakt_id: str,
        media_type: str = "movie",
        abort_flag=None
    ) -> Optional[list]:
        """Get curated subgenres for a movie or show, fetching only when nothing is cached."""
        ids = {"imdb": trakt_id} if trakt_id.startswith("tt") else {"tmdb": trakt_id}

        data = self.get_trakt_data(media_type, ids)
        if not data:
            data = self.fetch_data(media_type, ids, abort_flag)

        if not data:
            return None

        subgenres = data.get("subgenres")
        if subgenres and isinstance(subgenres, list):
            return subgenres

        return None

    def _public_list(self, endpoint: str, max_hours: float, limit: int, page: int,
                     abort_flag=None) -> list:
        """Get a public Trakt list, cached under a caller-set TTL; empty when it fails."""
        cache_key = f"{endpoint}?limit={limit}&page={page}"
        cached = get_cached_trakt(cache_key)
        if isinstance(cached, list):
            return cached
        items = self._request_list(endpoint, limit, page, abort_flag=abort_flag)
        if items is None:
            return []
        cache_trakt(cache_key, items, max_hours)
        return items

    def _request_list(
        self,
        endpoint: str,
        limit: int = 20,
        page: int = 1,
        extended: str = 'full',
        requires_auth: bool = False,
        abort_flag=None
    ) -> Optional[List[dict]]:
        """Request one page of a Trakt list; None when it fails or lacks authorization."""
        headers: Optional[Dict[str, str]] = None
        if requires_auth:
            headers = self._auth_headers(abort_flag)
            if not headers:
                return None

        params: Dict[str, str | int] = {"limit": limit, "page": page}
        if extended:
            params["extended"] = extended

        try:
            data = self.session.get(
                endpoint,
                params=params,
                headers=headers,
                abort_flag=abort_flag
            )
            return data if isinstance(data, list) else None
        except RateLimitHit as e:
            wait = e.retry_after_seconds
            log("Trakt",
                f"Rate limit hit on {endpoint} (Retry-After={wait}); returning empty list",
                xbmc.LOGWARNING)
            return None
        except Exception as e:
            log("Trakt", f"List fetch error for {endpoint}: {e}", xbmc.LOGWARNING)
            return None

    def _activities(self, abort_flag=None) -> Optional[dict]:
        """Get the account's last-change stamps, kept a minute for every user list to share."""
        cached = get_cached_trakt("activities")
        if isinstance(cached, dict):
            return cached
        headers = self._auth_headers(abort_flag)
        if not headers:
            return None
        try:
            data = self.session.get(
                "/sync/last_activities", headers=headers, abort_flag=abort_flag)
        except Exception as e:
            log("Trakt", f"Activity check failed: {e}", xbmc.LOGWARNING)
            return None
        if not isinstance(data, dict):
            return None
        cache_trakt("activities", data, _ACTIVITY_MINUTES / 60)
        return data

    def _user_list(self, endpoint: str, stamp_keys: Tuple[str, ...], max_hours: float,
                   limit: int, page: int, abort_flag=None) -> list:
        """Get a user list, cached while its activity stamps hold, fetched and cached otherwise."""
        cache_key = f"{endpoint}?limit={limit}&page={page}"
        cached = get_cached_trakt(cache_key)
        cached_items = cached.get("items") or [] if isinstance(cached, dict) else []
        activity = self._activities(abort_flag)
        if activity is None:
            return cached_items
        stamps = [_stamp(activity, key) for key in stamp_keys]
        if isinstance(cached, dict) and cached.get("stamps") == stamps:
            return cached_items
        items = self._request_list(
            endpoint, limit, page, requires_auth=True, abort_flag=abort_flag)
        if items is None:
            return cached_items
        cache_trakt(cache_key, {"stamps": stamps, "items": items}, max_hours)
        return items

    def get_trending(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get Trakt's trending movies or shows."""
        return self._public_list(
            f"/{media_type}s/trending", _TRENDING_HOURS, limit, page, abort_flag)

    def get_popular(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get Trakt's popular movies or shows."""
        return self._public_list(
            f"/{media_type}s/popular", _CHART_HOURS, limit, page, abort_flag)

    def get_anticipated(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get Trakt's most anticipated movies or shows."""
        return self._public_list(
            f"/{media_type}s/anticipated", _CHART_HOURS, limit, page, abort_flag)

    def get_most_watched(
        self, media_type: str, period: str = 'weekly', limit: int = 20, page: int = 1,
        abort_flag=None
    ) -> list:
        """Get Trakt's most watched movies or shows for a period."""
        return self._public_list(
            f"/{media_type}s/watched/{period}", _PERIOD_HOURS.get(period, _CHART_HOURS),
            limit, page, abort_flag)

    def get_most_played(
        self, media_type: str, period: str = 'weekly', limit: int = 20, page: int = 1,
        abort_flag=None
    ) -> list:
        """Get Trakt's most played movies or shows for a period."""
        return self._public_list(
            f"/{media_type}s/played/{period}", _PERIOD_HOURS.get(period, _CHART_HOURS),
            limit, page, abort_flag)

    def get_watchlist(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get the user's Trakt watchlist of movies or shows; empty without authorization."""
        return self._user_list(
            f"/sync/watchlist/{media_type}s", ("watchlist.updated_at",),
            _USER_LIST_HOURS, limit, page, abort_flag)

    def get_history(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get the user's Trakt watch history, newest first; empty without authorization."""
        stamp = "movies.watched_at" if media_type == "movie" else "episodes.watched_at"
        return self._user_list(
            f"/sync/history/{media_type}s", (stamp,), _USER_LIST_HOURS, limit, page, abort_flag)

    def get_up_next(self, limit: int = 20, page: int = 1, abort_flag=None) -> list:
        """Get the user's shows with aired episodes left to watch, most recently watched first."""
        return self._user_list(
            "/sync/progress/up_next",
            ("episodes.watched_at", "shows.hidden_at", "shows.dropped_at"),
            _AIRING_HOURS, limit, page, abort_flag)

    def get_most_collected(
        self, media_type: str, period: str = 'weekly', limit: int = 20, page: int = 1,
        abort_flag=None
    ) -> list:
        """Get Trakt's most collected movies or shows for a period."""
        return self._public_list(
            f"/{media_type}s/collected/{period}", _PERIOD_HOURS.get(period, _CHART_HOURS),
            limit, page, abort_flag)

    def get_box_office(self, limit: int = 20, abort_flag=None) -> list:
        """Get Trakt's weekend box office movies."""
        return self._public_list("/movies/boxoffice", _CHART_HOURS, limit, 1, abort_flag)

    def get_recommendations(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        """Get Trakt's recommendations for the user; empty without authorization."""
        return self._user_list(
            f"/recommendations/{media_type}s", ("recommendations.updated_at",),
            _USER_LIST_HOURS, limit, page, abort_flag)

    def get_lists(self, kind: str, limit: int = 20, page: int = 1, abort_flag=None) -> list:
        """Get the account's own or liked Trakt lists, or Trakt's popular or trending ones."""
        if kind == "mine":
            entries = self._user_list("/users/me/lists", ("lists.updated_at",),
                                      _USER_LIST_HOURS, limit, page, abort_flag)
        elif kind == "liked":
            entries = self._user_list("/users/likes/lists", ("lists.liked_at",),
                                      _USER_LIST_HOURS, limit, page, abort_flag)
        else:
            hours = _TRENDING_HOURS if kind == "trending" else _CHART_HOURS
            entries = self._public_list(f"/lists/{kind}", hours, limit, page, abort_flag)
        return [entry.get("list", entry) for entry in entries if isinstance(entry, dict)]

    def get_list_items(self, user: str, list_id: str, media_type: str = "", limit: int = 20,
                       page: int = 1, abort_flag=None) -> list:
        """Get the movies and shows on a Trakt list in rank order; `me` is the signed-in account."""
        types = _LIST_ITEM_TYPES.get(media_type, "movie,show")
        path = f"/lists/{quote(list_id, safe='')}/items/{types}"
        if user == "me":
            return self._user_list(f"/users/me{path}", ("lists.updated_at",),
                                   _USER_LIST_HOURS, limit, page, abort_flag)
        return self._public_list(f"/users/{quote(user, safe='')}{path}", _LIST_ITEMS_HOURS,
                                 limit, page, abort_flag)

    def get_show_calendar(self, start_date: str, days: int, abort_flag=None) -> Optional[list]:
        """Get every show episode airing in a span from a UTC date; None when the fetch fails."""
        endpoint = f"/calendars/all/shows/{start_date}/{days}"
        try:
            data = self.session.get(
                endpoint, params={"extended": "full"}, abort_flag=abort_flag
            )
        except RateLimitHit as e:
            log("Trakt", f"Rate limit hit on {endpoint} (Retry-After={e.retry_after_seconds})",
                xbmc.LOGWARNING)
            return None
        except Exception as e:
            log("Trakt", f"Calendar fetch error: {e}", xbmc.LOGWARNING)
            return None
        return data if isinstance(data, list) else None

    def get_my_calendar(self, start_date: str, days: int, abort_flag=None) -> list:
        """Get the account's show episodes airing in a span from a UTC date; empty without one."""
        return self._user_list(f"/calendars/my/shows/{start_date}/{days}", _MY_SHOWS_STAMPS,
                               _AIRING_HOURS, 100, 1, abort_flag)

    def test_connection(self) -> bool:
        """Test Trakt API connection; requires a valid OAuth token."""
        token = self._get_valid_token()
        if not token:
            return False

        try:
            data = self.session.get(
                "/users/settings",
                headers={"Authorization": f"Bearer {token}"}
            )
            return data is not None
        except Exception as e:
            log("Ratings", f"Trakt test connection error: {str(e)}", xbmc.LOGWARNING)
            return False


_top250_session: Optional[ApiSession] = None


def _get_top250_session() -> ApiSession:
    """Get or create the singleton session for Top 250 list fetches."""
    global _top250_session
    if _top250_session is None:
        _top250_session = ApiSession(
            service_name="Trakt Top250",
            base_url="https://api.trakt.tv",
            timeout=(10.0, 30.0),
            max_retries=2,
            backoff_factor=1.0,
            default_headers={
                "Content-Type": "application/json",
                "trakt-api-key": TRAKT_CLIENT_ID,
                "trakt-api-version": "2"
            }
        )
    return _top250_session


def fetch_top250_list(abort_flag=None) -> Optional[list[dict]]:
    """Fetch the IMDb Top 250 from Justin Nemeth's daily Trakt list; no OAuth needed."""
    session = _get_top250_session()

    try:
        data = session.get(
            "/users/justin/lists/imdb-top-rated-movies/items",
            params={"limit": 250},  # Trakt pages at 100 by default
            abort_flag=abort_flag,
        )
        if data and isinstance(data, list):
            return data
        return None
    except RateLimitHit as e:
        wait = e.retry_after_seconds
        log("Trakt", f"Rate limit hit fetching Top 250 (Retry-After={wait})", xbmc.LOGWARNING)
        return None
    except Exception as e:
        log("Trakt", f"Failed to fetch Top 250 list: {e}", xbmc.LOGERROR)
        return None

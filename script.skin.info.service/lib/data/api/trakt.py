"""Trakt ratings source with OAuth support."""
from __future__ import annotations

from typing import Any, Optional, Dict, Set
from datetime import datetime, timedelta
import json
import threading
import xbmc
import xbmcvfs

from lib.data.api.client import ApiSession
from lib.data.api.source import RatingSource
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api.utilities import decode_key
from lib.data.api import tracker as usage_tracker
from lib.kodi.client import log


TRAKT_CLIENT_ID = decode_key(
    "MWM1ZmIxZDZkNjhlODk1ZDRiMmY3MzVlYTc2ODE3NDIy"
    "ZmIzMzM0ZjFlMTZmMzE0YjMyMzg1YzBlNzRmN2M4ZA=="
)
TRAKT_CLIENT_SECRET = decode_key(
    "OTQ1ODY3M2JjMDk1Y2NhZDI3YTVjZDViNzkwNTgxZTZm"
    "ZDE2N2I5ZjZhNWQyYjRlZmQxN2VjZDRiMmMzMmE1ZQ=="
)


class ApiTrakt(RatingSource):
    """Trakt ratings source implementation with OAuth."""

    BASE_URL = "https://api.trakt.tv"

    def __init__(self):
        super().__init__("trakt")
        self.token_path = xbmcvfs.translatePath(
            "special://profile/addon_data/script.skin.info.service/trakt_tokens.json"
        )
        self.session = ApiSession(
            service_name="Trakt",
            base_url=self.BASE_URL,
            timeout=(5.0, 10.0),
            max_retries=2,
            backoff_factor=1.0,
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
        """True when a stored OAuth token exists; auth-gated widgets check this before fetching."""
        return self._load_tokens() is not None

    def _load_tokens(self) -> Optional[Dict]:
        """Load tokens from file."""
        if not xbmcvfs.exists(self.token_path):
            return None

        try:
            with open(self.token_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def _save_tokens(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        """Save tokens to file."""
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
        """Delete token file."""
        if xbmcvfs.exists(self.token_path):
            try:
                xbmcvfs.delete(self.token_path)
            except Exception:
                pass

    def _auth_headers(self, abort_flag=None) -> Dict[str, str]:
        """Build the Authorization header dict for an authenticated Trakt request."""
        token = self._get_valid_token(abort_flag)
        return {"Authorization": f"Bearer {token}"} if token else {}

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
                else:
                    self._delete_tokens()
                    return None

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
        """Fetch complete Trakt data (extended=full); episodes fetch their whole season in one
        call, so a season's episodes cost a single request."""
        if usage_tracker.is_provider_skipped("trakt"):
            return None

        trakt_id = ids.get("trakt_slug") or ids.get("imdb")
        tmdb_id = ids.get("tmdb")
        if not trakt_id and not tmdb_id:
            return None

        cache_key = self._get_cache_key(media_type, ids)
        if not force_refresh:
            cached = self.get_cached_data(cache_key)
            if cached:
                return cached

        try:
            headers = self._auth_headers(abort_flag)

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
                self.cache_data(cache_key, data)

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
        self, trakt_id: str, season: str, cache_key: str,
        headers: Dict[str, str], abort_flag=None, force_refresh: bool = False,
    ) -> Optional[dict]:
        """Fetch the episode's whole season in one call, caching every episode so only the
        first hits the API.

        `force_refresh` re-fetches a season once per run, not once per episode; the latter
        costs one request per episode and blows Trakt's rate limit on a long-running show.
        """
        season_key = f"{trakt_id}_s{season}"
        with self._get_season_lock(season_key):
            if not (force_refresh and season_key not in self._refreshed_seasons):
                cached = self.get_cached_data(cache_key)
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
                ep_key = self._get_cache_key("episode", {
                    "imdb": trakt_id,
                    "season": str(season),
                    "episode": str(ep_num),
                })
                self.cache_data(ep_key, ep)

            self._refreshed_seasons.add(season_key)
            log("Trakt", f"Fetched {len(data)} episodes for season {season}", xbmc.LOGDEBUG)

        return self.get_cached_data(cache_key)

    def _get_cache_key(self, media_type: str, ids: Dict[str, str]) -> str:
        """Generate cache key for Trakt data."""
        trakt_id = ids.get("trakt_slug") or ids.get("imdb") or ids.get("tmdb")
        if media_type == "episode":
            season = ids.get("season", "")
            episode = ids.get("episode", "")
            return f"{trakt_id}_s{season}e{episode}"
        return str(trakt_id)

    def get_trakt_data(self, media_type: str, ids: Dict[str, str]) -> Optional[dict]:
        """Return the full cached Trakt response, or None if not cached."""
        cache_key = self._get_cache_key(media_type, ids)
        return self.get_cached_data(cache_key)

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
        pause_reporter=None,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from Trakt (RatingSource interface)."""
        self.session.set_pause_context(pause_reporter, self.provider_name)
        try:
            data = self.fetch_data(media_type, ids, abort_flag, force_refresh=force_refresh)
            if not data:
                return None

            return self._extract_ratings(data)
        finally:
            self.session.clear_pause_context()

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
        """Get curated subgenres for a movie/show; reuses the fetch_data/fetch_ratings cache,
        no extra API call if ratings were already fetched."""
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

    def _get_list(
        self,
        endpoint: str,
        limit: int = 20,
        page: int = 1,
        extended: str = 'full',
        requires_auth: bool = False,
        abort_flag=None
    ) -> list:
        headers: Optional[Dict[str, str]] = None
        if requires_auth:
            headers = self._auth_headers(abort_flag)
            if not headers:
                return []

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
            if data and isinstance(data, list):
                return data
            return []
        except RateLimitHit as e:
            wait = e.retry_after_seconds
            log("Trakt",
                f"Rate limit hit on {endpoint} (Retry-After={wait}); returning empty list",
                xbmc.LOGWARNING)
            return []
        except Exception as e:
            log("Trakt", f"List fetch error for {endpoint}: {e}", xbmc.LOGWARNING)
            return []

    def get_trending(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        return self._get_list(
            f"/{media_type}s/trending", limit=limit, page=page, abort_flag=abort_flag
        )

    def get_popular(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        return self._get_list(
            f"/{media_type}s/popular", limit=limit, page=page, abort_flag=abort_flag
        )

    def get_anticipated(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        return self._get_list(
            f"/{media_type}s/anticipated", limit=limit, page=page, abort_flag=abort_flag
        )

    def get_most_watched(
        self, media_type: str, period: str = 'weekly', limit: int = 20, page: int = 1,
        abort_flag=None
    ) -> list:
        return self._get_list(
            f"/{media_type}s/watched/{period}", limit=limit, page=page, abort_flag=abort_flag
        )

    def get_most_collected(
        self, media_type: str, period: str = 'weekly', limit: int = 20, page: int = 1,
        abort_flag=None
    ) -> list:
        return self._get_list(
            f"/{media_type}s/collected/{period}", limit=limit, page=page, abort_flag=abort_flag
        )

    def get_box_office(self, limit: int = 20, abort_flag=None) -> list:
        return self._get_list("/movies/boxoffice", limit=limit, abort_flag=abort_flag)

    def get_recommendations(
        self, media_type: str, limit: int = 20, page: int = 1, abort_flag=None
    ) -> list:
        return self._get_list(
            f"/recommendations/{media_type}s",
            limit=limit, page=page,
            requires_auth=True, abort_flag=abort_flag
        )

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
    """Fetch IMDb Top 250 from Trakt's daily-updated list, maintained by Trakt founder Justin
    Nemeth; no OAuth needed."""
    # Trakt paginates at 100/page by default; limit=250 gets the full list in one request
    session = _get_top250_session()

    try:
        data = session.get(
            "/users/justin/lists/imdb-top-rated-movies/items",
            params={"limit": 250},
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

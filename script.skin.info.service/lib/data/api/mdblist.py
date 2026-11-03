"""MDBList API client; single items use the batch endpoint too, so every reply has one shape."""
from __future__ import annotations

from typing import Optional, Dict, List, Set, Final
import xbmc

from lib.data.api.client import ApiSession
from lib.data.api.source import RatingSource
from lib.data.api.client import RateLimitHit
from lib.data.api import tracker as usage_tracker
from lib.kodi.client import get_api_key, log
from lib.kodi.formatters import RATING_SOURCE_NORMALIZE, RT_SOURCE_TOMATOES, RT_SOURCE_POPCORN


BATCH_SIZE: Final = 100
STATUS_KEYWORDS = frozenset({
    "certified-fresh", "certified-hot", "fresh", "rotten", "metacritic-must-see",
    "roger-ebert-thumbs-down",
})

AWARD_KEYWORDS = frozenset({
    "oscar-winner", "oscar-nominated",
    "best-picture-winner", "best-picture-nominated",
    "oscar-best-director-winner", "oscar-best-director-nominee",
    "golden-globe-winner", "golden-globe-nominated",
    "razzie-winner", "razzie-nominee",
    "emmy-award-winner", "emmy-award-nominated",
    "festival-cannes-winner", "festival-venice-winner",
    "festival-sundance-winner", "festival-toronto-winner",
    "national-film-preservation-board-winner", "national-film-registry",
})

_KEPT_KEYWORDS = STATUS_KEYWORDS | AWARD_KEYWORDS


def _keep_status_keywords(item: dict) -> None:
    """Strip the keyword list to the status and award tags."""
    keywords = item.get("keywords")
    if not isinstance(keywords, list):
        return
    item["keywords"] = [
        k for k in keywords
        if isinstance(k, dict) and k.get("name", "").lower() in _KEPT_KEYWORDS
    ]


class ApiMdblist(RatingSource):
    """MDBList rating source that also serves the site's extra metadata."""

    BASE_URL = "https://api.mdblist.com"

    def __init__(self):
        super().__init__("mdblist")
        self.api_key = get_api_key("mdblist_api_key")
        self.session = ApiSession(
            service_name="MDBList",
            base_url=self.BASE_URL,
            timeout=(5.0, 10.0),
            max_retries=3,
            backoff_factor=1.0,
            retry_statuses=[500, 502, 503, 504]
        )

    def _get_cache_key(self, provider: str, media_id: str) -> str:
        """Cache identity for MDBList data: the id provider and the id."""
        return f"{provider}_{media_id}"

    def _batch_request(
        self,
        media_type: str,
        ids: List[str],
        provider: str = "tmdb",
        abort_flag=None
    ) -> List[dict]:
        """POST one batch of ids; [] without a key, while MDBList is skipped, or on a bad reply."""
        if not self.api_key or not ids:
            return []

        if usage_tracker.is_provider_skipped("mdblist"):
            return []

        endpoint_type = "show" if media_type == "tvshow" else "movie"
        endpoint = f"/{provider}/{endpoint_type}"

        log("MDBList", f"Batch request: {len(ids)} {media_type}s", xbmc.LOGDEBUG)

        data = self.session.post(
            endpoint,
            json_data={"ids": ids, "append_to_response": ["keyword"]},
            params={"apikey": self.api_key},
            abort_flag=abort_flag
        )

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    _keep_status_keywords(item)
            return data
        return []

    def supports(self, media_type: str) -> bool:
        """MDBList rates movies and shows only; episode ratings ride the show append."""
        return media_type in ("movie", "tvshow")

    def fetch_data(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False
    ) -> Optional[dict]:
        """Fetch full MDBList data for one item by TMDB id, else IMDb id; a refresh still caches."""
        if not self.supports(media_type):
            return None

        media_id = ids.get("tmdb")
        if media_id:
            provider = "tmdb"
        else:
            media_id = ids.get("imdb")
            if not media_id:
                return None
            provider = "imdb"

        cache_key = self._get_cache_key(provider, str(media_id))

        if not force_refresh:
            cached = self.get_cached_data(media_type, cache_key)
            if cached:
                return cached

        results = self._batch_request(media_type, [str(media_id)], provider, abort_flag)

        if not results:
            return None

        for item_data in results:
            ids_obj = item_data.get("ids", {})
            result_id = str(ids_obj.get(provider, ""))

            if result_id == str(media_id):
                self.cache_data(media_type, cache_key, item_data)
                return item_data

        return None

    def get_mdblist_data(self, media_type: str, ids: Dict[str, str]) -> Optional[dict]:
        """Get cached MDBList data, never fetching."""
        if not self.supports(media_type):
            return None

        media_id = ids.get("tmdb")
        if media_id:
            cache_key = self._get_cache_key("tmdb", str(media_id))
        else:
            media_id = ids.get("imdb")
            if not media_id:
                return None
            cache_key = self._get_cache_key("imdb", str(media_id))

        return self.get_cached_data(media_type, cache_key)

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from MDBList (RatingSource interface)."""
        data = self.fetch_data(media_type, ids, abort_flag, force_refresh=force_refresh)
        if not data:
            return None

        return self._extract_ratings(data, media_type)

    def _extract_ratings(self, data: dict, media_type: str) -> Dict[str, Dict[str, float]]:
        """Extract ratings from the MDBList response, every scale converted to 0-10."""
        result: Dict[str, Dict[str, float]] = {}

        ratings_data = data.get("ratings", [])
        if not isinstance(ratings_data, list):
            return result

        for rating_entry in ratings_data:
            if not isinstance(rating_entry, dict):
                continue

            source = rating_entry.get("source", "").lower()
            score = rating_entry.get("score")
            votes = rating_entry.get("votes") or 0

            if not source:
                continue

            if source == "rogerebert":
                value = rating_entry.get("value")
                if value is not None:
                    result["rogerebert"] = {
                        "rating": self.normalize_rating(float(value), 4),
                        "votes": float(votes)
                    }
                continue

            if score is None:
                continue

            rating = float(score) / 10.0

            if source == "imdb":
                result["imdb"] = {"rating": rating, "votes": float(votes)}
            elif source == "tmdb":
                # Kodi's TMDB scrapers key the rating themoviedb for movies and tmdb for shows
                key = "themoviedb" if media_type == "movie" else "tmdb"
                result[key] = {"rating": rating, "votes": float(votes)}
            elif source == "trakt":
                result["trakt"] = {"rating": rating, "votes": float(votes)}
            elif source == "metacritic":
                result["metacritic"] = {"rating": rating, "votes": float(votes)}
            elif source == "metacriticuser":
                result["metacriticuser"] = {"rating": rating, "votes": float(votes)}
            elif source == "letterboxd":
                result["letterboxd"] = {"rating": rating, "votes": float(votes)}
            elif RATING_SOURCE_NORMALIZE.get(source, source) == RT_SOURCE_TOMATOES:
                result[RT_SOURCE_TOMATOES] = {"rating": rating, "votes": float(votes)}
            elif RATING_SOURCE_NORMALIZE.get(source, source) == RT_SOURCE_POPCORN:
                result[RT_SOURCE_POPCORN] = {"rating": rating, "votes": float(votes)}
            elif source == "myanimelist":
                result["myanimelist"] = {"rating": rating, "votes": float(votes)}

        if result:
            result["_source"] = "mdblist"  # type: ignore[assignment]

        return result

    def _get_or_fetch(
        self, media_type: str, ids: Dict[str, str], abort_flag=None
    ) -> Optional[dict]:
        """Cached MDBList data, fetched from the API when absent."""
        data = self.get_mdblist_data(media_type, ids)
        if not data:
            data = self.fetch_data(media_type, ids, abort_flag)
        return data

    def get_extra_data(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Optional[dict]:
        """Get the trailer and certification from MDBList, fetching if not cached."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return None

        result = {}

        trailer = data.get("trailer")
        if trailer:
            result["trailer"] = trailer

        certification = data.get("certification")
        if certification:
            result["certification"] = certification

        return result if result else None

    def get_common_sense_data(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Optional[dict]:
        """Get Common Sense Media data from MDBList, fetching if not cached."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return None

        cs = data.get("commonsense_media")
        if not cs or not isinstance(cs, dict):
            return None

        age = cs.get("common_sense")
        if age is None:
            return None

        # the sub-scores arrive present but null when only an overall age is rated
        return {
            "age": int(age),
            "selection": bool(cs.get("common_sense_selection")),
            "violence": int(cs.get("parental_violence") or 0),
            "nudity": int(cs.get("parental_nudity") or 0),
            "language": int(cs.get("parental_language") or 0),
            "drinking": int(cs.get("parental_drinking") or 0)
        }

    def get_rating_status(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Optional[Dict[str, str]]:
        """The status each rating source reports, keyed by source."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return None

        keywords = {
            k.get("name", "").lower() for k in data.get("keywords", []) if isinstance(k, dict)}

        result: Dict[str, str] = {}

        if "certified-fresh" in keywords:
            result[RT_SOURCE_TOMATOES] = "Certified"
        elif "fresh" in keywords:
            result[RT_SOURCE_TOMATOES] = "Fresh"
        elif "rotten" in keywords:
            result[RT_SOURCE_TOMATOES] = "Rotten"

        if "metacritic-must-see" in keywords:
            result["metacritic"] = "MustSee"

        if "roger-ebert-thumbs-down" in keywords:
            result["rogerebert"] = "ThumbsDown"

        if "certified-hot" in keywords:
            result[RT_SOURCE_POPCORN] = "Hot"
        else:
            # certified-hot is the only audience keyword
            for r in data.get("ratings", []):
                if not isinstance(r, dict):
                    continue
                source = r.get("source", "").lower()
                if RATING_SOURCE_NORMALIZE.get(source, source) == RT_SOURCE_POPCORN:
                    score = r.get("score")
                    if score is not None:
                        result[RT_SOURCE_POPCORN] = "Fresh" if score >= 60 else "Spilled"
                    break

        return result or None

    def get_score(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Optional[float]:
        """MDBList's own aggregate on a 0-10 scale, their plain mean when there is none."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return None
        score = data.get("score") or data.get("score_average")
        return float(score) / 10.0 if score else None

    def get_award_tags(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Set[str]:
        """The award tags MDBList carries for a title; booleans, never counts."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return set()
        return {
            k.get("name", "").lower() for k in data.get("keywords", [])
            if isinstance(k, dict) and k.get("name", "").lower() in AWARD_KEYWORDS
        }

    def get_service_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Get all ratings from MDBList (fetches if not cached)."""
        data = self._get_or_fetch(media_type, ids, abort_flag)
        if not data:
            return None

        return self._extract_ratings(data, media_type)

    def fetch_batch(
        self,
        media_type: str,
        items: List[Dict[str, str]],
        provider: str = "tmdb",
        abort_flag=None
    ) -> Dict[str, dict]:
        """Fetch many items in 100-id batches, cache first, keyed by provider id."""
        if not self.api_key or not items:
            return {}

        if usage_tracker.is_provider_skipped("mdblist"):
            return {}

        if not self.supports(media_type):
            return {}

        results: Dict[str, dict] = {}

        for i in range(0, len(items), BATCH_SIZE):
            batch = items[i:i + BATCH_SIZE]
            ids_to_fetch: List[str] = []
            id_map: Dict[str, str] = {}

            for item in batch:
                item_id = item.get("id")
                if not item_id:
                    continue

                cache_key = self._get_cache_key(provider, str(item_id))
                cached = self.get_cached_data(media_type, cache_key)
                if cached:
                    results[str(item_id)] = cached
                else:
                    ids_to_fetch.append(str(item_id))
                    id_map[str(item_id)] = cache_key

            if not ids_to_fetch:
                continue

            try:
                batch_results = self._batch_request(media_type, ids_to_fetch, provider, abort_flag)

                for item_data in batch_results:
                    ids_obj = item_data.get("ids", {})
                    item_id = str(ids_obj.get(provider, ""))

                    if item_id and item_id in id_map:
                        self.cache_data(media_type, id_map[item_id], item_data)
                        results[item_id] = item_data

                fetched_count = len([r for r in ids_to_fetch if r in results])
                log("MDBList", f"Batch: {len(ids_to_fetch)} requested, {fetched_count} returned")

            except RateLimitHit:
                raise
            except Exception as e:
                log("MDBList", f"Batch error: {str(e)}", xbmc.LOGWARNING)
                continue

        return results

    def test_connection(self) -> bool:
        """Test MDBList API connection."""
        if not self.api_key:
            return False

        try:
            results = self._batch_request("movie", ["603"], "tmdb")
            return len(results) > 0 and "title" in results[0]
        except Exception as e:
            log("MDBList", f"Test connection error: {str(e)}", xbmc.LOGWARNING)
            return False

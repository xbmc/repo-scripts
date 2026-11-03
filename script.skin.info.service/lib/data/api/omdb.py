"""OMDb ratings and awards for a title, looked up by IMDb id."""
from __future__ import annotations

from typing import Optional, Dict
import xbmc

from lib.data.api.client import ApiSession
from lib.data.api.source import RatingSource
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api import tracker as usage_tracker
from lib.kodi.client import get_api_key, log
from lib.kodi.formatters import RT_SOURCE_TOMATOES


class ApiOmdb(RatingSource):
    """OMDb rating source that also serves a title's awards and short plot."""

    BASE_URL = "https://www.omdbapi.com"

    def __init__(self):
        super().__init__("omdb")
        self.api_key = get_api_key("omdb_api_key")
        self.session = ApiSession(
            service_name="OMDb",
            base_url=self.BASE_URL,
            timeout=(3.0, 3.0),
            max_retries=0,
            rate_limit=(20, 1.0)
        )

    def fetch_data(self, media_type: str, imdb_id: str, abort_flag=None,
                   force_refresh: bool = False) -> Optional[dict]:
        """Fetch full OMDb data for an item; a forced refresh still caches."""
        if not self.api_key:
            return None

        if usage_tracker.is_provider_skipped("omdb"):
            return None

        if not force_refresh:
            cached = self.get_cached_data(media_type, imdb_id)
            if cached:
                return cached

        try:
            data = self.session.get(
                "/",
                params={"i": imdb_id, "apikey": self.api_key},
                abort_flag=abort_flag
            )

            if not data:
                return None

            if data.get("Response") == "False":
                error = data.get("Error", "Unknown error")
                if "limit" in error.lower():
                    raise RateLimitHit("omdb")
                log("OMDb", f"API error for {imdb_id}: {error}", xbmc.LOGDEBUG)
                return None

            self.cache_data(media_type, imdb_id, data)
            return data

        except RateLimitHit:
            raise
        except RetryableError:
            raise
        except Exception as e:
            log("OMDb", f"Fetch error for {imdb_id}: {str(e)}", xbmc.LOGWARNING)
            return None

    def get_omdb_data(self, media_type: str, imdb_id: str) -> Optional[dict]:
        """Get cached OMDb data, never fetching."""
        return self.get_cached_data(media_type, imdb_id)

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from OMDb (RatingSource interface); needs an IMDb id."""
        if not self.supports(media_type):
            return None
        imdb_id = ids.get("imdb")
        if not imdb_id:
            return None

        data = self.fetch_data(media_type, imdb_id, abort_flag, force_refresh=force_refresh)
        if not data:
            return None

        return self._extract_ratings(data)

    def supports(self, media_type: str) -> bool:
        """OMDb rates the parent title only; it has no per-episode entry."""
        return media_type != "episode"

    def _extract_ratings(self, data: dict) -> Dict[str, Dict[str, float]]:
        """Extract ratings from the OMDb response, every scale converted to 0-10."""
        result: Dict[str, Dict[str, float]] = {}

        imdb_rating = data.get("imdbRating")
        imdb_votes = data.get("imdbVotes")
        if imdb_rating and imdb_rating != "N/A":
            try:
                rating_val = float(imdb_rating)
                votes_val = (float(imdb_votes.replace(",", ""))
                             if imdb_votes and imdb_votes != "N/A" else 0.0)
                result["imdb"] = {
                    "rating": self.normalize_rating(rating_val, 10),
                    "votes": votes_val
                }
            except (ValueError, AttributeError):
                pass

        metascore = data.get("Metascore", "").replace("N/A", "")
        if metascore:
            try:
                rating = self.normalize_rating(float(metascore), 100)
                if rating > 0:
                    result["metacritic"] = {"rating": rating, "votes": 0.0}
            except (ValueError, AttributeError):
                pass

        ratings_list = data.get("Ratings", [])
        if isinstance(ratings_list, list):
            for rating_entry in ratings_list:
                if not isinstance(rating_entry, dict):
                    continue

                source = rating_entry.get("Source", "")
                value = rating_entry.get("Value", "")

                if ("Rotten Tomatoes" in source and value and value != "N/A"
                        and RT_SOURCE_TOMATOES not in result):
                    try:
                        rating = self.normalize_rating(float(value.rstrip("%")), 100)
                        if rating > 0:
                            result[RT_SOURCE_TOMATOES] = {"rating": rating, "votes": 0.0}
                    except ValueError:
                        pass

                elif ("Metacritic" in source and value and value != "N/A"
                        and "metacritic" not in result):
                    try:
                        parts = value.split("/")
                        if len(parts) >= 1:
                            rating = self.normalize_rating(float(parts[0]), 100)
                            if rating > 0:
                                result["metacritic"] = {"rating": rating, "votes": 0.0}
                    except ValueError:
                        pass

        if result:
            result["_source"] = "omdb"  # type: ignore[assignment]

        return result

    def test_connection(self) -> bool:
        """Test OMDb API connection."""
        if not self.api_key:
            return False

        try:
            data = self.session.get(
                "/",
                params={"i": "tt0133093", "apikey": self.api_key}
            )
            return data is not None and data.get("Response") == "True"
        except Exception as e:
            log("OMDb", f"Test connection error: {str(e)}", xbmc.LOGWARNING)
            return False

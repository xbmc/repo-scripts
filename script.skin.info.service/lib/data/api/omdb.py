"""OMDb API integration."""
from __future__ import annotations

from typing import Optional, Dict
import re
import xbmc

from lib.data.api.client import ApiSession
from lib.data.api.source import RatingSource
from lib.data.api.client import RateLimitHit, RetryableError
from lib.data.api import tracker as usage_tracker
from lib.kodi.client import get_api_key, log
from lib.kodi.formatters import RT_SOURCE_TOMATOES, RT_SOURCE_POPCORN


class ApiOmdb(RatingSource):
    """OMDb API implementation."""

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

    def fetch_data(self, imdb_id: str, abort_flag=None,
                   force_refresh: bool = False) -> Optional[dict]:
        """Fetch full OMDb data for an item; `force_refresh` skips cache read but still writes."""
        if not self.api_key:
            return None

        if usage_tracker.is_provider_skipped("omdb"):
            return None

        if not force_refresh:
            cached = self.get_cached_data(imdb_id)
            if cached:
                return cached

        try:
            data = self.session.get(
                "/",
                params={"i": imdb_id, "apikey": self.api_key, "tomatoes": "true"},
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

            self.cache_data(imdb_id, data)
            return data

        except RateLimitHit:
            raise
        except RetryableError:
            raise
        except Exception as e:
            log("OMDb", f"Fetch error for {imdb_id}: {str(e)}", xbmc.LOGWARNING)
            return None

    def get_omdb_data(self, imdb_id: str) -> Optional[dict]:
        """Get full cached OMDb response."""
        return self.get_cached_data(imdb_id)

    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
        pause_reporter=None,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Fetch ratings from OMDb (RatingSource interface). ids must contain 'imdb'."""
        if media_type == "episode":
            return None
        imdb_id = ids.get("imdb")
        if not imdb_id:
            return None

        self.session.set_pause_context(pause_reporter, self.provider_name)
        try:
            data = self.fetch_data(imdb_id, abort_flag, force_refresh=force_refresh)
            if not data:
                return None

            return self._extract_ratings(data)
        finally:
            self.session.clear_pause_context()

    def get_awards(self, imdb_id: str, abort_flag=None) -> Optional[dict]:
        """Extract awards data from OMDb (fetches if not cached)."""
        data = self.get_omdb_data(imdb_id)
        if not data:
            data = self.fetch_data(imdb_id, abort_flag)

        if not data or not data.get('Awards'):
            return None

        media_type = data.get('Type', 'movie')
        return self._parse_awards(data['Awards'], media_type)

    def _extract_ratings(self, data: dict) -> Dict[str, Dict[str, float]]:
        """Extract ratings dict from full OMDb response."""
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

        tomato_meter = data.get("tomatoMeter", "").replace("N/A", "")
        tomato_reviews = data.get("tomatoReviews", "0").replace("N/A", "0").replace(",", "")

        if tomato_meter:
            try:
                rating = self.normalize_rating(float(tomato_meter), 100)
                if rating > 0:
                    result[RT_SOURCE_TOMATOES] = {"rating": rating, "votes": float(tomato_reviews)}
            except (ValueError, AttributeError):
                pass

        tomato_user_meter = data.get("tomatoUserMeter", "").replace("N/A", "")
        tomato_user_reviews = (
            data.get("tomatoUserReviews", "0").replace("N/A", "0").replace(",", "")
        )

        if tomato_user_meter:
            try:
                rating = self.normalize_rating(float(tomato_user_meter), 100)
                if rating > 0:
                    result[RT_SOURCE_POPCORN] = {
                        "rating": rating, "votes": float(tomato_user_reviews)
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

    def _parse_awards(self, awards_string: str, media_type: str) -> dict:
        """Parse OMDb Awards field into structured data."""
        result = {
            "oscar_wins": 0,
            "oscar_nominations": 0,
            "emmy_wins": 0,
            "emmy_nominations": 0,
            "other_wins": 0,
            "other_nominations": 0,
            "awards_text": ""
        }

        if not awards_string or awards_string == "N/A":
            return result

        result["awards_text"] = awards_string

        if media_type == "series":
            emmy_wins_match = re.search(r'Won (\d+) Primetime Emmys?', awards_string)
            if emmy_wins_match:
                result["emmy_wins"] = int(emmy_wins_match.group(1))

            emmy_noms_match = re.search(r'Nominated for (\d+) Primetime Emmys?', awards_string)
            if emmy_noms_match:
                result["emmy_nominations"] = int(emmy_noms_match.group(1))
        else:
            oscar_wins_match = re.search(r'Won (\d+) Oscars?', awards_string)
            if oscar_wins_match:
                result["oscar_wins"] = int(oscar_wins_match.group(1))

            oscar_noms_match = re.search(r'Nominated for (\d+) Oscars?', awards_string)
            if oscar_noms_match:
                result["oscar_nominations"] = int(oscar_noms_match.group(1))

        total_match = re.search(r'(\d+) wins? & (\d+) nominations? total', awards_string)
        if total_match:
            total_wins = int(total_match.group(1))
            total_noms = int(total_match.group(2))

            if media_type == "series":
                result["other_wins"] = total_wins - result["emmy_wins"]
                result["other_nominations"] = total_noms - result["emmy_nominations"]
            else:
                result["other_wins"] = total_wins - result["oscar_wins"]
                result["other_nominations"] = total_noms - result["oscar_nominations"]

        return result

    def test_connection(self) -> bool:
        """Test OMDb API connection."""
        if not self.api_key:
            return False

        try:
            data = self.session.get(
                "/",
                params={"i": "tt0133093", "apikey": self.api_key, "tomatoes": "true"}
            )
            return data is not None and data.get("Response") == "True"
        except Exception as e:
            log("OMDb", f"Test connection error: {str(e)}", xbmc.LOGWARNING)
            return False

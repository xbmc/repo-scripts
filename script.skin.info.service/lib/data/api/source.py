"""Base class for ratings API sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict

from lib.data.database.rating import get_provider_cache, save_provider_cache


class RatingSource(ABC):
    """Base for every ratings provider: the calls each implements, plus cache and scale helpers."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Ratings for one item, keyed by source; implemented per provider."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Whether the provider answers; implemented per provider."""

    def supports(self, media_type: str) -> bool:
        """Whether this source can return ratings for the media type at all."""
        return True

    def normalize_rating(self, value: float, scale_max: int) -> float:
        """Scale a rating to the 0-10 range Kodi stores."""
        if scale_max == 10:
            return round(float(value), 1)
        return round(float(value) / float(scale_max) * 10.0, 1)

    def get_cached_data(self, media_type: str, media_id: str,
                        season: int = -1, episode: int = -1) -> Optional[dict]:
        """Cached provider response for one item."""
        return get_provider_cache(self.provider_name, media_type, media_id, season, episode)

    def cache_data(self, media_type: str, media_id: str, data: dict,
                   release_date: Optional[str] = None,
                   season: int = -1, episode: int = -1) -> None:
        """Store a provider response for later reuse, its release date driving the TTL."""
        save_provider_cache(self.provider_name, media_type, media_id, data, release_date,
                            season, episode)

"""Base class for ratings API sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict

from lib.data.database.rating import get_provider_cache, save_provider_cache
from lib.data.api.client import PauseReporter


class RatingSource(ABC):
    """Abstract base class for ratings sources."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    def fetch_ratings(
        self,
        media_type: str,
        ids: Dict[str, str],
        abort_flag=None,
        force_refresh: bool = False,
        pause_reporter: Optional[PauseReporter] = None,
    ) -> Optional[Dict[str, Dict[str, float]]]:
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        pass

    def normalize_rating(self, value: float, scale_max: int) -> float:
        if scale_max == 10:
            return round(float(value), 1)
        return round(float(value) / float(scale_max) * 10.0, 1)

    def get_cached_data(self, media_id: str) -> Optional[dict]:
        return get_provider_cache(self.provider_name, media_id)

    def cache_data(self, media_id: str, data: dict, release_date: Optional[str] = None) -> None:
        save_provider_cache(self.provider_name, media_id, data, release_date)

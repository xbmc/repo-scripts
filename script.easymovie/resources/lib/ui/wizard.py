"""
Filter wizard flow controller.

Manages the sequence of filter dialogs, back navigation,
answer persistence, and building the final FilterConfig.

Logging:
    Logger: 'wizard'
    Key events:
        - filter.ask (DEBUG): Filter step presented to user
        - filter.preset (DEBUG): Filter using preset value
        - filter.skip (DEBUG): Filter step skipped
    See LOGGING.md for full guidelines.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from resources.lib.constants import (
    FILTER_ASK, FILTER_PRESET, FILTER_SKIP,
    WATCHED_BOTH,
    YEAR_FILTER_RECENCY,
)
from resources.lib.data.filters import FilterConfig
from resources.lib.utils import get_logger

log = get_logger('wizard')


# The ordered list of filter types in the wizard
FILTER_ORDER = ["ignore_genre", "genre", "watched", "mpaa", "runtime", "year", "score"]

# Mapping from filter type to settings mode key
_MODE_KEYS = {
    "ignore_genre": "ignore_genre_mode",
    "genre": "genre_mode",
    "watched": "watched_mode",
    "mpaa": "mpaa_mode",
    "runtime": "runtime_mode",
    "year": "year_mode",
    "score": "score_mode",
}


@dataclass
class WizardStep:
    """A single step in the wizard flow."""
    filter_type: str
    index: int


def _get_preset_value(settings: Dict[str, Any], filter_type: str) -> Any:
    """Get the preset value for a filter type, for logging."""
    key_map = {
        "ignore_genre": "preset_ignore_genres",
        "genre": "preset_genres",
        "watched": "watched_preset",
        "mpaa": "preset_mpaa",
        "runtime": ("runtime_min", "runtime_max"),
        "year": ("year_from", "year_to"),
        "score": "min_score",
    }
    key = key_map.get(filter_type)
    if isinstance(key, tuple):
        return {k: settings.get(k) for k in key}
    if key:
        return settings.get(key)
    return None


class WizardFlow:
    """Manages the wizard flow for filter selection.

    Reads filter mode settings to determine which steps to show,
    maintains answer stack for back navigation, and builds a
    FilterConfig from combined preset + user answers.
    """

    def __init__(self, settings: Dict[str, Any]) -> None:
        """Initialize wizard from settings.

        Args:
            settings: Dict containing filter mode settings
                (genre_mode, watched_mode, etc.) and preset values.
        """
        self._settings = settings
        self._answers: Dict[str, Any] = {}
        self._current_index = 0

        # Build step list: only filters set to ASK
        self.steps: List[WizardStep] = []
        for i, filter_type in enumerate(FILTER_ORDER):
            mode_key = _MODE_KEYS[filter_type]
            mode = settings.get(mode_key, FILTER_SKIP)
            if mode == FILTER_ASK:
                log.debug("Filter step will be presented",
                          event="filter.ask", filter_type=filter_type)
                self.steps.append(WizardStep(
                    filter_type=filter_type,
                    index=len(self.steps),
                ))
            elif mode == FILTER_PRESET:
                preset_value = _get_preset_value(settings, filter_type)
                log.debug("Filter using preset value",
                          event="filter.preset", filter_type=filter_type,
                          value=preset_value)
            else:
                log.debug("Filter step skipped",
                          event="filter.skip", filter_type=filter_type)

    @property
    def current_step_index(self) -> int:
        """Current position in the wizard."""
        return self._current_index

    @property
    def current_step(self) -> Optional[WizardStep]:
        """Get the current step, or None if complete."""
        if self._current_index < len(self.steps):
            return self.steps[self._current_index]
        return None

    @property
    def is_complete(self) -> bool:
        """Whether the wizard has no more steps."""
        return self._current_index >= len(self.steps)

    def advance(self) -> bool:
        """Move to the next step.

        Returns:
            True if there is a next step, False if wizard is now complete.
        """
        self._current_index += 1
        return self._current_index < len(self.steps)

    def go_back(self) -> bool:
        """Move to the previous step.

        Returns:
            True if moved back, False if already at start (signals cancel).
        """
        if self._current_index <= 0:
            return False
        self._current_index -= 1
        return True

    def set_answer(self, filter_type: str, value: Any) -> None:
        """Record the user's answer for a filter step."""
        self._answers[filter_type] = value

    def get_answers(self) -> Dict[str, Any]:
        """Get all recorded answers."""
        return dict(self._answers)

    def load_last_answers(self, answers: Dict[str, Any]) -> None:
        """Pre-populate answers from a previous session."""
        self._answers.update(answers)

    def build_partial_filter_config(self) -> FilterConfig:
        """Build a FilterConfig using only answers for steps before the current one.

        Used for cumulative counting: when showing step N, counts should
        reflect filters from steps 0..N-1 only, not pre-loaded future answers.
        """
        # Determine which filter types have been answered in this session
        completed_types = set()
        for i, step in enumerate(self.steps):
            if i >= self._current_index:
                break
            completed_types.add(step.filter_type)

        # Temporarily mask answers for uncompleted steps
        saved_answers = dict(self._answers)
        for key in list(self._answers.keys()):
            if key not in completed_types:
                del self._answers[key]

        config = self.build_filter_config()

        # Restore all answers
        self._answers = saved_answers
        return config

    def build_filter_config(self) -> FilterConfig:
        """Build a FilterConfig from combined preset values and wizard answers.

        For each filter type:
        - ASK: use the wizard answer
        - PRESET: use the preset value from settings
        - SKIP: use default (no filter)
        """
        config = FilterConfig()

        # Ignore genres
        ignore_genre_mode = self._settings.get("ignore_genre_mode", FILTER_SKIP)
        if ignore_genre_mode == FILTER_ASK:
            config.ignore_genres = self._answers.get("ignore_genre")
        elif ignore_genre_mode == FILTER_PRESET:
            config.ignore_genres = self._settings.get("preset_ignore_genres")
        config.ignore_genre_match_and = self._settings.get(
            "ignore_genre_match_and", False)

        # Genre
        genre_mode = self._settings.get("genre_mode", FILTER_SKIP)
        if genre_mode == FILTER_ASK:
            config.genres = self._answers.get("genre")
        elif genre_mode == FILTER_PRESET:
            config.genres = self._settings.get("preset_genres")
        config.genre_match_and = self._settings.get("genre_match_and", False)

        # Watched
        watched_mode = self._settings.get("watched_mode", FILTER_SKIP)
        if watched_mode == FILTER_ASK:
            config.watched = self._answers.get("watched", WATCHED_BOTH)
        elif watched_mode == FILTER_PRESET:
            config.watched = self._settings.get("watched_preset", WATCHED_BOTH)

        # MPAA
        mpaa_mode = self._settings.get("mpaa_mode", FILTER_SKIP)
        if mpaa_mode == FILTER_ASK:
            config.mpaa_ratings = self._answers.get("mpaa")
        elif mpaa_mode == FILTER_PRESET:
            config.mpaa_ratings = self._settings.get("preset_mpaa")

        # Runtime
        runtime_mode = self._settings.get("runtime_mode", FILTER_SKIP)
        if runtime_mode == FILTER_ASK:
            rt = self._answers.get("runtime", {})
            config.runtime_min = rt.get("min", 0)
            config.runtime_max = rt.get("max", 0)
        elif runtime_mode == FILTER_PRESET:
            config.runtime_min = self._settings.get("runtime_min", 0)
            config.runtime_max = self._settings.get("runtime_max", 0)

        # Year
        year_mode = self._settings.get("year_mode", FILTER_SKIP)
        if year_mode == FILTER_ASK:
            yr = self._answers.get("year", {})
            config.year_from = yr.get("from", 0)
            config.year_to = yr.get("to", 0)
        elif year_mode == FILTER_PRESET:
            year_filter_type = self._settings.get("year_filter_type", 0)
            if year_filter_type == YEAR_FILTER_RECENCY:
                import datetime
                recency = self._settings.get("year_recency", 5)
                config.year_from = datetime.datetime.now().year - recency
            else:
                config.year_from = self._settings.get("year_from", 0)
                config.year_to = self._settings.get("year_to", 0)

        # Score
        score_mode = self._settings.get("score_mode", FILTER_SKIP)
        if score_mode == FILTER_ASK:
            config.min_score = self._answers.get("score", 0)
        elif score_mode == FILTER_PRESET:
            config.min_score = self._settings.get("min_score", 0)

        return config

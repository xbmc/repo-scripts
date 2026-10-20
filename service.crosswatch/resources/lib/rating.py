# SPDX-License-Identifier: GPL-2.0-only
"""Ask for a rating after a finished watch: whether to ask, whom, and what an answer means.

Free of Kodi windows, like prompt.py, so every rule is unit testable and every suppression
is logged with a reason.

A watch is rated only when Kodi itself counts it as watched, its kind is switched on, and it
has an id CrossWatch can use: nothing is asked about an item that is never sent. Each
credited viewer gets their own question, or the household one question with shared rating.
Skip, Back, the countdown and playback starting send nothing; a score is sent only when one
is chosen, and 0 only for a deliberate Remove (contract, Ratings).
"""

from dataclasses import dataclass, replace

from resources.lib.config import Settings
from resources.lib.kodi import WINDOW_INVALID
from resources.lib.log import get_logger
from resources.lib.models import MediaItem, Viewer

_log = get_logger("rating")


@dataclass(frozen=True)
class Watch:
    session_id: str
    media: MediaItem
    # Credited when the stop went out, by whichever rule credited the playback.
    viewers: tuple[str, ...]
    # Who-watched was asked and skipped or timed out: nobody wants a second question.
    declined: bool


@dataclass(frozen=True)
class Question:
    # Named in the question; None asks the household.
    viewer: str | None
    # Who the score goes to, one rate event each; () sends one event for nobody.
    targets: tuple[str, ...]


def rateable(settings: Settings, media: MediaItem, completes_watch: bool, has_usable_id: bool) -> bool:
    return completes_watch and has_usable_id and media.media_type in settings.rating_kinds


def may_ask(watch: Watch, dialog_id: int, shutting_down: bool, playing: bool) -> str:
    """The reason not to ask now, or "" to ask."""
    if watch.declined:
        reason = "declined"
    elif shutting_down:
        # Before the window: during shutdown Kodi refuses to draw one and says nothing.
        reason = "shutting_down"
    elif playing:
        reason = "playing"
    elif dialog_id != WINDOW_INVALID:
        reason = "dialog_busy"
    else:
        return ""
    _log.info("rating.suppressed", reason=reason, media_type=watch.media.media_type, library_id=watch.media.library_id)
    return reason


def questions(watch: Watch, configured: list[Viewer], shared: bool) -> list[Question]:
    """The questions for one watch, in the order the viewers are configured.

    A name credited at the stop but no longer configured is left out: that viewer is gone,
    and their route with them. A watch whose credited viewers are all gone gets no question
    rather than becoming a question for nobody, which would send a score nobody gave.
    """
    if not watch.viewers:
        return [Question(None, ())]
    credited = {name.casefold() for name in watch.viewers}
    names = tuple(v.name for v in configured if v.name.casefold() in credited)
    if not names:
        _log.info("rating.suppressed", reason="viewers_gone", media_type=watch.media.media_type)
        return []
    if shared:
        return [Question(None, names)]
    return [Question(name, (name,)) for name in names]


def _renamed(names: tuple[str, ...], old: str, new: str) -> tuple[str, ...]:
    return tuple(new if n == old else n for n in names)


def single_score(scores: list[int]) -> int | None:
    """The one score to write into Kodi's library, which holds one rating per item.

    Only when every score given agrees: several different ones would put one viewer's rating
    on everyone. A Remove with no other score is a score of 0, which clears Kodi's.
    """
    distinct = set(scores)
    return distinct.pop() if len(distinct) == 1 else None


class RatingQueue:
    """Finished watches waiting for the end of a session, in memory only.

    Nothing has been sent for them yet, so a Kodi restart that drops the queue loses no event.
    Touched only by the service thread, so it needs no lock.
    """

    def __init__(self) -> None:
        self._watches: list[Watch] = []

    def add(self, watch: Watch) -> None:
        self._watches.append(watch)

    def take_all(self) -> list[Watch]:
        """Newest first, the episode just watched before the ones autoplay passed over."""
        taken, self._watches = list(reversed(self._watches)), []
        return taken

    def clear(self) -> int:
        dropped, self._watches = len(self._watches), []
        return dropped

    def rename_viewer(self, old: str, new: str) -> None:
        self._watches = [replace(w, viewers=_renamed(w.viewers, old, new)) for w in self._watches]

    def __len__(self) -> int:
        return len(self._watches)

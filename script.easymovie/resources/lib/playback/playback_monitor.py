"""
Playback monitor for movie set continuation.

Monitors playback during playlist sessions and prompts
the user when a set-member movie finishes.

Logging:
    Logger: 'playback'
    Key events:
        - continuation.playback_ended (DEBUG): Playback ended callback received
        - continuation.prompt (INFO): Showing continuation dialog
        - continuation.accepted (INFO): User chose to watch next in set
        - continuation.declined (INFO): User declined, continuing playlist
        - continuation.fail (WARNING): No movieid for next movie in set
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional, cast

import xbmc
import xbmcgui
import xbmcaddon

from resources.lib.constants import (
    ACTION_NAV_BACK,
    ACTION_PREVIOUS_MENU,
    ADDON_ID,
    CONTINUATION_DEFAULT_CONTINUE_SET,
)
from resources.lib.utils import get_logger, json_query, lang
from resources.lib.data.queries import build_add_movie_query
from resources.lib.data.movie_sets import get_next_in_set

# Control IDs for the continuation dialog
CONT_HEADING = 1
CONT_MESSAGE = 2
CONT_TIMER = 3
CONT_SUBTITLE = 4
CONT_YES = 10
CONT_NO = 11
CONT_POSTER = 20

# Module-level logger
log = get_logger('playback')


class ContinuationDialog(xbmcgui.WindowXMLDialog):
    """Countdown dialog for movie set continuation and set warning prompts.

    Args:
        *args: Positional args passed to WindowXMLDialog.
        **kwargs: Keyword args. Custom kwargs:
            - message: str - Dialog message text
            - subtitle: str - Secondary message text
            - yes_label: str - Label for the Yes button (left)
            - no_label: str - Label for the No button (right)
            - duration: int - Countdown seconds (0 = no timer)
            - heading: str - Static heading text (e.g. addon/clone name)
            - timer_template: str - Timer format with %s for seconds
            - default_yes: bool - True if Yes is the default on timeout
            - poster: str - Optional poster image path
            - addon_id: str - Addon ID for theming
            - logger: StructuredLogger - Optional logger instance
    """

    def __new__(cls, *args, **kwargs):
        """Create instance, filtering out custom kwargs for parent class."""
        for key in ('message', 'subtitle', 'yes_label', 'no_label',
                    'duration', 'heading', 'timer_template',
                    'default_yes', 'poster', 'addon_id', 'logger'):
            kwargs.pop(key, None)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        self._message = kwargs.pop('message', '')
        self._subtitle = kwargs.pop('subtitle', '')
        self._yes_label = kwargs.pop('yes_label', '')
        self._no_label = kwargs.pop('no_label', '')
        self._duration = kwargs.pop('duration', 0)
        self._heading = kwargs.pop('heading', '')
        self._timer_template = kwargs.pop('timer_template', 'Auto-selecting in %ss')
        self._default_yes = kwargs.pop('default_yes', True)
        self._poster = kwargs.pop('poster', '')
        self._addon_id: str = kwargs.pop('addon_id', ADDON_ID)
        self._log = kwargs.pop('logger', None) or log
        super().__init__(*args, **kwargs)
        self._closed = False
        self._button_clicked: Optional[int] = None
        self._timer_thread: Optional[threading.Thread] = None

    @property
    def result(self) -> bool:
        """Whether the affirmative action was chosen.

        Returns True if:
        - User clicked Yes button, OR
        - Timer expired and default_yes is True

        Returns False otherwise (No button, ESC, or timer expired with
        default_yes False).
        """
        if self._button_clicked == CONT_YES:
            return True
        if self._button_clicked == CONT_NO:
            return False
        return self._default_yes

    def onInit(self) -> None:
        """Set up the dialog."""
        from resources.lib.ui import apply_theme
        apply_theme(self, self._addon_id)

        heading = self._heading or xbmcaddon.Addon(self._addon_id).getAddonInfo('name')
        cast(xbmcgui.ControlLabel, self.getControl(CONT_HEADING)).setLabel(heading)
        cast(xbmcgui.ControlLabel, self.getControl(CONT_MESSAGE)).setLabel(self._message)
        cast(xbmcgui.ControlLabel, self.getControl(CONT_SUBTITLE)).setLabel(self._subtitle)
        cast(xbmcgui.ControlButton, self.getControl(CONT_YES)).setLabel(self._yes_label)
        cast(xbmcgui.ControlButton, self.getControl(CONT_NO)).setLabel(self._no_label)

        if self._poster:
            try:
                cast(xbmcgui.ControlImage, self.getControl(CONT_POSTER)).setImage(self._poster)
            except RuntimeError:
                pass

        if self._duration > 0:
            try:
                cast(xbmcgui.ControlLabel, self.getControl(CONT_TIMER)).setLabel(
                    self._timer_template % self._duration
                )
            except RuntimeError:
                pass

            # Focus the non-default button
            if self._default_yes:
                self.setFocus(self.getControl(CONT_NO))
            else:
                self.setFocus(self.getControl(CONT_YES))

            # Start countdown
            self._timer_thread = threading.Thread(
                target=self._countdown_loop, daemon=True
            )
            self._timer_thread.start()
        else:
            try:
                cast(xbmcgui.ControlLabel, self.getControl(CONT_TIMER)).setLabel('')
            except RuntimeError:
                pass  # Timer control not in this skin XML (e.g. set warning)
            self.setFocus(self.getControl(CONT_YES))

    def _countdown_loop(self) -> None:
        """Countdown timer that auto-closes the dialog."""
        remaining = self._duration
        while remaining > 0 and not self._closed:
            xbmc.sleep(1000)
            if self._closed:
                return
            remaining -= 1
            try:
                cast(xbmcgui.ControlLabel, self.getControl(CONT_TIMER)).setLabel(
                    self._timer_template % remaining
                )
            except RuntimeError:
                return

        if not self._closed:
            self._log.debug("Countdown expired", event="continuation.timeout")
            self.close()

    def onClick(self, controlId: int) -> None:
        """Handle button clicks."""
        if controlId in (CONT_YES, CONT_NO):
            self._button_clicked = controlId
            self._closed = True
            self.close()

    def onAction(self, action: xbmcgui.Action) -> None:
        """Handle back/escape."""
        if action.getId() in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            self._button_clicked = CONT_NO
            self._closed = True
            self.close()


class PlaybackMonitor(xbmc.Player):
    """Monitors playback during playlist sessions for set continuation.

    Subclasses xbmc.Player to detect when a movie finishes playing.
    When a set-member movie completes, checks for the next movie in
    the set and shows a continuation prompt.
    """

    def __init__(
        self,
        set_cache: Dict[int, Dict[str, Any]],
        movies: Dict[int, Dict[str, Any]],
        continuation_duration: int = 20,
        continuation_default: int = CONTINUATION_DEFAULT_CONTINUE_SET,
        addon_id: str = ADDON_ID,
    ) -> None:
        super().__init__()
        self._set_cache = set_cache
        self._movies = movies  # movieid -> movie dict
        self._continuation_duration = continuation_duration
        self._continuation_default = continuation_default
        self._addon_id = addon_id
        self._current_movie_id: Optional[int] = None
        self._active = True

    def set_current_movie(self, movie_id: int) -> None:
        """Set the currently playing movie ID."""
        self._current_movie_id = movie_id

    def stop_monitoring(self) -> None:
        """Stop the monitor."""
        self._active = False

    def onPlayBackEnded(self) -> None:
        """Called when playback ends naturally (movie finished)."""
        log.debug("Playback ended callback",
                  event="continuation.playback_ended",
                  movie_id=self._current_movie_id,
                  active=self._active)
        if not self._active or self._current_movie_id is None:
            return
        self._check_continuation()

    def _check_continuation(self) -> None:
        """Check if we should prompt for set continuation."""
        movie_id = self._current_movie_id
        if movie_id is None:
            return

        movie = self._movies.get(movie_id)
        if not movie:
            return

        set_id = movie.get("setid", 0)
        if not set_id or set_id not in self._set_cache:
            return

        set_details = self._set_cache[set_id]
        next_movie = get_next_in_set(set_details, movie_id)
        if not next_movie:
            return

        log.info("Showing continuation prompt", event="continuation.prompt",
                 finished_title=movie.get("title", ""),
                 next_title=next_movie.get("title", ""),
                 set_name=set_details.get("title", ""))

        # Show continuation dialog
        addon_path = xbmcaddon.Addon(self._addon_id).getAddonInfo('path')

        finished_title = movie.get("title", "")
        next_title = next_movie.get("title", "")
        set_name = set_details.get("title", "")

        # Get poster art for next movie
        next_art = next_movie.get("art", {})
        poster = next_art.get("poster", "") if isinstance(next_art, dict) else ""

        dialog = ContinuationDialog(
            'script-easymovie-continuation.xml',
            addon_path, 'Default', '1080i',
            message=f"{lang(32333)}[CR][B]{finished_title}[/B]",
            subtitle=f"{lang(32332)} [B]{set_name}[/B]:[CR]{next_title}",
            yes_label=lang(32330),
            no_label=lang(32331),
            poster=poster,
            duration=self._continuation_duration,
            default_yes=(self._continuation_default == CONTINUATION_DEFAULT_CONTINUE_SET),
            heading=xbmcaddon.Addon(self._addon_id).getAddonInfo('name'),
            addon_id=self._addon_id,
        )
        dialog.doModal()

        if dialog.result:
            log.info("Continuation accepted", event="continuation.accepted",
                     next_title=next_title)
            # Insert next movie at front of playlist
            next_id = next_movie.get("movieid", 0)
            if next_id:
                query = build_add_movie_query(next_id, position=0)
                json_query(query, return_result=False)
            else:
                log.warning("No movieid for next movie in set", event="continuation.fail",
                            next_title=next_movie.get("title", ""))
        else:
            log.info("Continuation declined", event="continuation.declined")

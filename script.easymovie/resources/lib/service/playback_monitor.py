"""
Background playback monitor for movie set awareness.

Monitors all movie playback in Kodi. When a user plays a movie
that belongs to a set with earlier unwatched entries, pauses
playback and offers to play the earlier movie instead.

Skips the check when playback was initiated by EasyMovie
(which handles set ordering via substitution).

Logging:
    Logger: 'service'
    Key events:
        - setcheck.found (INFO): Earlier unwatched movie found
        - setcheck.accepted (INFO): User chose to switch
        - setcheck.declined (INFO): User chose to continue
        - setcheck.skip (DEBUG): Check skipped (reason logged)
        - setcheck.error (ERROR): Query or dialog error
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Any, Dict

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.constants import (
    ADDON_ID,
    PLAYER_STOP_DELAY_MS,
    PROP_PLAYLIST_RUNNING,
)
from resources.lib.utils import get_bool_setting, get_logger, json_query, lang
from resources.lib.data.queries import (
    get_movie_details_with_art_query,
    get_movie_set_details_query,
)
from resources.lib.data.movie_sets import find_first_unwatched_before
from resources.lib.playback.playback_monitor import ContinuationDialog

log = get_logger('service')


class MoviePlaybackMonitor(xbmc.Player):
    """Monitors playback for movie set awareness.

    Uses onAVStarted with xbmc.Player().getVideoInfoTag() to get
    the playing movie's database ID and media type immediately
    (no JSON-RPC timing issues), then queries GetMovieDetails
    for set membership.
    """

    def onAVStarted(self) -> None:
        """Handle AV stream start — check for earlier unwatched set movies."""
        try:
            self._check_set_awareness()
        except Exception:
            log.exception("Set check failed", event="setcheck.error")

    def _check_set_awareness(self) -> None:
        """Run the set awareness check."""
        # Check setting
        if not get_bool_setting('previous_movie_check'):
            log.debug("Set check disabled by setting", event="setcheck.skip")
            return

        # Skip EasyMovie-initiated playback
        window = xbmcgui.Window(10000)
        if window.getProperty(PROP_PLAYLIST_RUNNING) == 'true':
            log.debug("EasyMovie session active, skipping",
                       event="setcheck.skip")
            return

        # Get playing item info from the player directly (no JSON-RPC delay)
        try:
            info_tag = self.getVideoInfoTag()
            media_type = info_tag.getMediaType()
            movie_id = info_tag.getDbId()
        except RuntimeError:
            log.debug("No video info tag available", event="setcheck.skip")
            return

        if media_type != 'movie':
            log.debug("Not a movie", event="setcheck.skip",
                       media_type=media_type)
            return

        if not movie_id:
            log.debug("No movie ID", event="setcheck.skip")
            return

        # Query movie details for set membership
        movie_result = json_query(
            get_movie_details_with_art_query(movie_id), return_result=True
        )
        if not movie_result:
            log.debug("No movie details returned", event="setcheck.skip")
            return

        movie_details = movie_result.get("moviedetails", movie_result)
        set_id = movie_details.get("setid", 0)
        if not set_id or set_id <= 0:
            log.debug("Movie not in a set", event="setcheck.skip")
            return

        # Query set details
        log.debug("Querying set details", event="setcheck.query",
                   set_id=set_id)
        set_result = json_query(
            get_movie_set_details_query(set_id), return_result=True
        )
        if not set_result:
            log.debug("No set details returned", event="setcheck.skip")
            return

        set_details = set_result.get("setdetails", set_result)

        # Check for earlier unwatched
        earlier = find_first_unwatched_before(set_details, movie_id)
        if earlier is None:
            log.debug("No earlier unwatched movie", event="setcheck.skip",
                       set_name=movie_details.get('set', ''))
            return

        # Found an earlier unwatched movie
        earlier_title = earlier.get("title", "")
        earlier_year = str(earlier.get("year", ""))
        set_name = movie_details.get("set", set_details.get("title", ""))

        log.info("Earlier unwatched movie found",
                  event="setcheck.found",
                  current_title=movie_details.get('title', ''),
                  earlier_title=earlier_title,
                  set_name=set_name)

        self._show_set_warning(earlier, earlier_title, earlier_year, set_name)

    def _show_set_warning(
        self,
        earlier_movie: Dict[str, Any],
        earlier_title: str,
        earlier_year: str,
        set_name: str,
    ) -> None:
        """Pause playback and show dialog for earlier unwatched movie."""
        # Pause playback
        try:
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":false},"id":1}'
            )
        except Exception:
            log.exception("Failed to pause playback", event="setcheck.error")
            return

        # Build dialog
        addon_path = xbmcaddon.Addon(ADDON_ID).getAddonInfo('path')

        # Get poster art
        art = earlier_movie.get("art", {})
        poster = art.get("poster", "") if isinstance(art, dict) else ""

        dialog = ContinuationDialog(
            'script-easymovie-setwarning.xml',
            addon_path, 'Default', '1080i',
            message=(
                f"[B]{earlier_title}[/B] ({earlier_year})[CR]"
                f"{lang(32340)} [B]{set_name}[/B][CR]"
                f"{lang(32341)}"
            ),
            subtitle=lang(32342),
            yes_label=lang(32300),
            no_label=lang(32301),
            poster=poster,
            duration=0,
            default_yes=True,
            heading=xbmcaddon.Addon(ADDON_ID).getAddonInfo('name'),
            addon_id=ADDON_ID,
        )
        dialog.doModal()

        if dialog.result:
            log.info("User chose earlier movie",
                      event="setcheck.accepted",
                      earlier_title=earlier_title,
                      set_name=set_name)
            self._play_earlier_movie(earlier_movie)
        else:
            log.info("User declined, continuing",
                      event="setcheck.declined",
                      earlier_title=earlier_title,
                      set_name=set_name)
            self._unpause()

    def _play_earlier_movie(self, movie: Dict[str, Any]) -> None:
        """Stop current playback and start the earlier movie."""
        movie_id = movie.get("movieid", 0)
        if not movie_id:
            log.warning("No movieid for earlier movie",
                         event="setcheck.error")
            self._unpause()
            return

        try:
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.Stop",'
                '"params":{"playerid":1},"id":1}'
            )
            xbmc.sleep(PLAYER_STOP_DELAY_MS)
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.Open",'
                '"params":{"item":{"movieid":%d},'
                '"options":{"resume":true}},"id":1}' % movie_id
            )
        except Exception:
            log.exception("Failed to start earlier movie",
                           event="setcheck.error")

    @staticmethod
    def _unpause() -> None:
        """Resume paused playback."""
        try:
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":true},"id":1}'
            )
        except Exception:
            log.exception("Failed to unpause playback",
                           event="setcheck.error")

"""
Browse window for displaying movie results.

Supports 5 viewing modes via different XML files.
Handles movie selection, Surprise Me, Re-roll, and context menu.

Logging:
    Logger: 'browse'
    Key events:
        - ui.browse (INFO): Browse window opened
        - ui.select (INFO): Movie selected by user
        - ui.surprise (INFO): Surprise Me triggered
        - ui.reroll (INFO): Re-roll triggered
        - ui.browse_close (DEBUG): User closed browse window
    See LOGGING.md for full guidelines.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, cast

import xbmcgui
import xbmcaddon

from resources.lib.constants import (
    ACTION_CONTEXT_MENU,
    ACTION_NAV_BACK,
    ACTION_PREVIOUS_MENU,
    ACTION_TELETEXT_BLUE,
    ADDON_ID,
    THEME_COLORS,
    THEME_NAMES,
    VIEW_SHOWCASE,
    VIEW_CARD_LIST,
    VIEW_POSTERS,
    VIEW_BIG_SCREEN,
    VIEW_SPLIT_VIEW,
)
from resources.lib.utils import get_logger

# Control IDs (shared across all view XMLs)
LIST_CONTROL_ID = 655
SURPRISE_BUTTON_ID = 10
REROLL_BUTTON_ID = 11

# Result signals
RESULT_REROLL = "__reroll__"
RESULT_SURPRISE = "__surprise__"
# View style to XML filename mapping
VIEW_XML_MAP = {
    VIEW_SHOWCASE: "script-easymovie-postergrid.xml",
    VIEW_CARD_LIST: "script-easymovie-cardlist.xml",
    VIEW_POSTERS: "script-easymovie-main.xml",
    VIEW_BIG_SCREEN: "script-easymovie-BigScreenList.xml",
    VIEW_SPLIT_VIEW: "script-easymovie-splitlist.xml",
}

# Module-level logger
log = get_logger('browse')


class BrowseWindow(xbmcgui.WindowXMLDialog):
    """Browse window for displaying and selecting movies.

    Supports all 5 viewing modes via different XML files.
    The same control IDs are used across all views.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._movies: List[Dict[str, Any]] = []
        self._result: Optional[Any] = None
        self._addon_id: str = ADDON_ID
        self._preview_mode: bool = False
        self._theme_index: int = 0

    def set_movies(self, movies: List[Dict[str, Any]]) -> None:
        """Set the movies to display."""
        self._movies = movies

    def set_addon_id(self, addon_id: str) -> None:
        """Set the addon ID (for clone support)."""
        self._addon_id = addon_id

    def set_preview_mode(self, theme_index: int) -> None:
        """Enable preview mode with live theme cycling via blue button."""
        self._preview_mode = True
        self._theme_index = theme_index

    @property
    def result(self) -> Optional[Any]:
        """The result after the window closes.

        Returns:
            - A movie dict if user selected a movie
            - RESULT_REROLL if user pressed Re-roll
            - RESULT_SURPRISE if user pressed Surprise Me
            - None if user closed/backed out
        """
        return self._result

    def onInit(self):
        """Populate the list when the window opens."""
        from resources.lib.ui import apply_theme
        apply_theme(self, self._addon_id)

        # Set addon name for skin heading (shows clone name for clones)
        self.setProperty(
            'EasyMovie.AddonName',
            xbmcaddon.Addon(self._addon_id).getAddonInfo('name'),
        )

        log.info("Browse window opened", event="ui.browse",
                 movie_count=len(self._movies))

        list_control = cast(xbmcgui.ControlList, self.getControl(LIST_CONTROL_ID))
        list_control.reset()

        for movie in self._movies:
            li = xbmcgui.ListItem(movie.get("title", ""))

            # Set video info via InfoTagVideo (Kodi 21+)
            info_tag = li.getVideoInfoTag()
            info_tag.setTitle(movie.get("title", ""))
            info_tag.setYear(movie.get("year", 0))
            info_tag.setGenres(movie.get("genre", []))
            info_tag.setRating(movie.get("rating", 0.0))
            info_tag.setDuration(movie.get("runtime", 0))
            info_tag.setPlot(movie.get("plot", ""))
            info_tag.setMpaa(movie.get("mpaa", ""))

            # Set art
            art = movie.get("art", {})
            if art:
                li.setArt({
                    'poster': art.get("poster", ""),
                    'fanart': art.get("fanart", ""),
                    'thumb': art.get("poster", ""),
                })

            # Set custom properties
            runtime_secs = movie.get("runtime", 0)
            minutes = runtime_secs // 60
            if minutes >= 60:
                li.setProperty("runtime_min", f"{minutes // 60}h {minutes % 60}m")
            else:
                li.setProperty("runtime_min", f"{minutes}m")

            set_name = movie.get("set", "")
            if set_name:
                li.setProperty("set_name", set_name)

            li.setProperty("movieid", str(movie.get("movieid", 0)))

            if movie.get("playcount", 0) > 0:
                li.setProperty("watched", "true")

            list_control.addItem(li)

        if self._movies:
            self.setFocusId(LIST_CONTROL_ID)

    def onClick(self, controlId):
        """Handle control clicks."""
        if controlId == LIST_CONTROL_ID:
            list_control = cast(xbmcgui.ControlList, self.getControl(LIST_CONTROL_ID))
            idx = list_control.getSelectedPosition()
            if 0 <= idx < len(self._movies):
                self._result = self._movies[idx]
                log.info("Movie selected", event="ui.select",
                         title=self._movies[idx].get("title", ""),
                         movieid=self._movies[idx].get("movieid", 0))
            self.close()

        elif controlId == SURPRISE_BUTTON_ID:
            log.info("Surprise Me pressed", event="ui.surprise")
            self._result = RESULT_SURPRISE
            self.close()

        elif controlId == REROLL_BUTTON_ID:
            log.info("Re-roll pressed", event="ui.reroll")
            self._result = RESULT_REROLL
            self.close()

    def _get_focused_movie(self) -> Optional[Dict[str, Any]]:
        """Get the currently focused movie, or None."""
        list_control = cast(xbmcgui.ControlList, self.getControl(LIST_CONTROL_ID))
        idx = list_control.getSelectedPosition()
        if 0 <= idx < len(self._movies):
            return self._movies[idx]
        return None

    def onAction(self, action):
        """Handle navigation actions."""
        action_id = action.getId()
        if action_id in (ACTION_NAV_BACK, ACTION_PREVIOUS_MENU):
            log.debug("Browse window closed by user", event="ui.browse_close")
            self._result = None
            self.close()
        elif self._preview_mode and (
            action_id == ACTION_TELETEXT_BLUE
            or action.getButtonCode() == 0xF054
        ):
            self._theme_index = (self._theme_index + 1) % len(THEME_COLORS)
            for prop, value in THEME_COLORS[self._theme_index].items():
                self.setProperty(prop, value)
            xbmcgui.Dialog().notification(
                "Theme", THEME_NAMES[self._theme_index], time=1500)
        elif action_id == ACTION_CONTEXT_MENU:
            movie = self._get_focused_movie()
            if movie:
                from resources.lib.ui.context_menu import (
                    show_context_menu, CONTEXT_PLAY, CONTEXT_PLAY_SET,
                )
                result = show_context_menu(movie, self._addon_id)
                if result == CONTEXT_PLAY:
                    self._result = movie
                    self.close()
                elif result == CONTEXT_PLAY_SET:
                    self._result = {"__play_set__": True, "movie": movie}
                    self.close()


def show_browse_window(
    movies: List[Dict[str, Any]],
    view_style: int,
    addon_id: str = ADDON_ID,
) -> Optional[Any]:
    """Show the browse window with the specified view style.

    Args:
        movies: List of movie dicts (with art) to display.
        view_style: View style constant (VIEW_SHOWCASE, etc.)
        addon_id: Addon ID (for clone support).

    Returns:
        Selected movie dict, RESULT_REROLL, RESULT_SURPRISE, or None.
    """
    xml_file = VIEW_XML_MAP.get(view_style, VIEW_XML_MAP[VIEW_SHOWCASE])
    addon_path = xbmcaddon.Addon(addon_id).getAddonInfo('path')

    window = BrowseWindow(xml_file, addon_path, 'Default', '1080i')
    window.set_movies(movies)
    window.set_addon_id(addon_id)
    window.doModal()

    return window.result

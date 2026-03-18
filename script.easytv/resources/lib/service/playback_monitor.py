#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Original work Copyright (C) 2013 KODeKarnage
#  Modified work Copyright (C) 2024-2026 Rouzax
#
#  SPDX-License-Identifier: GPL-3.0-or-later
#  See LICENSE.txt for more information.
#

"""
EasyTV Playback Monitor.

Monitors playback events and handles episode transitions, previous episode
checks, and next episode prompts.
Extracted from service.py as part of modularization.

Logging:
    Module: playback_monitor
    Events: None (debug/info logging only, no formal events)
"""
from __future__ import annotations

import ast
import json
import os
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.constants import (
    NOTIFICATION_DURATION_MS,
    PLAYER_STOP_DELAY_MS,
    PLAYLIST_ADD_DELAY_MS,
    PLAYLIST_START_DELAY_MS,
    MOVIE_RANDOM_SEEK_MAX_RATIO,
    MOVIE_RANDOM_SEEK_MIN_PERCENT,
    PERCENT_MULTIPLIER,
    RANDOM_PERCENT_MAX,
    RESUME_REWIND_SECONDS,
    PROP_PLAYLIST_CONFIG,
    PROP_PLAYLIST_REGENERATE,
    PROP_SOURCE_ADDON_ID,
    PROP_PLAYLIST_RUNNING,
    PROP_SERVICE_PATH,
)
from resources.lib.utils import (
    get_bool_setting,
    get_int_setting,
    get_logger,
    json_query,
    lang,
    log_timing,
    runtime_converter,
)
from resources.lib.data.queries import (
    build_add_episode_query,
    build_add_movie_query,
    build_player_seek_query,
    build_player_seek_time_query,
    get_playing_item_query,
)
from resources.lib.data.shows import (
    parse_season_episode_string,
    resolve_istream_episode,
)
from resources.lib.data.storage import get_storage
from resources.lib.playback.playlist_session import PlaylistSession

if TYPE_CHECKING:
    from resources.lib.utils import StructuredLogger


@dataclass
class PlaybackSettings:
    """
    Settings relevant to playback monitoring.
    
    Provides a snapshot of current settings to avoid accessing globals.
    """
    previous_episode_check: bool = False
    nextprompt: bool = False
    nextprompt_in_playlist: bool = False
    playlist_notifications: bool = True
    resume_partials_tv: bool = True
    resume_partials_movies: bool = True
    movies_random_start: bool = False
    promptdefaultaction: int = 0
    promptduration: int = 0
    playlist_continuation: bool = False
    playlist_continuation_duration: int = 20
    playlist_continuation_default_action: int = 0


# Type aliases for callbacks
# Note: Use List/Dict instead of list/dict for Python 3.8 compatibility (Kodi uses 3.8)
SettingsGetter = Callable[[], PlaybackSettings]
RandomShowsGetter = Callable[[], List[int]]
RefreshShowCallback = Callable[[List[int]], None]
ClearTargetCallback = Callable[[], None]
GetNextPromptInfoCallback = Callable[[], Dict]
SetNextPromptInfoCallback = Callable[[Dict], None]


class PlaybackMonitor(xbmc.Player):
    """
    Monitors playback events for TV episodes and movies.
    
    Handles:
    - Episode playback detection and tracking
    - Previous episode warnings
    - Resume point handling
    - Next episode prompts at end of playback
    - Movie notifications and random start positions
    
    Args:
        window: The Kodi home window for property access.
        get_settings: Callback to get current playback settings.
        get_random_order_shows: Callback to get random order shows list.
        on_refresh_show: Callback to refresh show episode data.
        clear_target: Callback to clear the playback target.
        get_nextprompt_info: Callback to get next prompt episode info.
        set_nextprompt_info: Callback to set next prompt episode info.
        logger: Optional logger instance.
    """

    def __init__(
        self,
        window: xbmcgui.Window,
        get_settings: SettingsGetter,
        get_random_order_shows: RandomShowsGetter,
        on_refresh_show: RefreshShowCallback,
        clear_target: ClearTargetCallback,
        get_nextprompt_info: GetNextPromptInfoCallback,
        set_nextprompt_info: SetNextPromptInfoCallback,
        logger: Optional[StructuredLogger] = None,
    ):
        """Initialize the playback monitor with callbacks."""
        super().__init__()

        self._window = window
        self._get_settings = get_settings
        self._get_random_order_shows = get_random_order_shows
        self._on_refresh_show = on_refresh_show
        self._clear_target = clear_target
        self._get_nextprompt_info = get_nextprompt_info
        self._set_nextprompt_info = set_nextprompt_info
        self._log = logger or get_logger('playback_monitor')
        
        # Playback tracking state
        self._pending_next_episode: Union[int, bool] = False
        self._pl_running: str = ''
        self._playing_showid: Union[int, bool] = False
        self._playing_epid: Union[int, bool] = False
        self._last_playing_showid: Union[int, bool] = False
        self._nextprompt_trigger: bool = False
        self._nextprompt_trigger_override: bool = True
        
        # Additional instance state
        self._ep_details: dict = {}
        self._pl_running_local: str = ''
        self._pending_movie_random_start: bool = False
        self._pending_resume_seek: Optional[int] = None
        self._on_last_playlist_item: bool = False
    
    def onPlayBackStarted(self) -> None:
        """
        Handle playback start events.
        
        Detects what is playing (episode or movie) and:
        - Checks for previous episode warnings
        - Shows playlist notifications
        - Handles resume points
        - Sets up episode tracking
        """
        self._log.debug("Playback started")
        self._pending_movie_random_start = False  # Reset for new playback
        settings = self._get_settings()
        
        self._clear_target()
        self._nextprompt_trigger_override = True
        
        # Check what is playing
        self._ep_details = json_query(get_playing_item_query(), True)
        self._log.debug("Now playing details", details=self._ep_details)
        
        self._pl_running_local = self._window.getProperty(PROP_PLAYLIST_RUNNING)
        
        if 'item' not in self._ep_details or 'type' not in self._ep_details['item']:
            self._log.debug("Playback started handler complete (no item)")
            return
        
        playlist_length = xbmc.getInfoLabel('VideoPlayer.PlaylistLength')
        
        # Check if this is a playlist - suppress next_ep_notify when there are
        # more than 1 items unless it IS a EasyTV playlist and user wants prompts
        if playlist_length != '1' and not all([
            self._pl_running_local == 'true',
            settings.nextprompt_in_playlist
        ]):
            self._log.debug("Next prompt suppressed (playlist mode)")
            self._nextprompt_trigger_override = False
        
        item_type = self._ep_details['item']['type']
        
        if item_type in ['unknown', 'episode']:
            self._handle_episode_playback(settings)
        elif item_type == 'movie' and self._pl_running_local == 'true':
            self._handle_movie_playback(settings)
        
        # Replenish lazy queue buffer on every item start
        # This handles rapid skipping (Page Up) which doesn't fire onPlayBackEnded
        if self._pl_running_local == 'true':
            self._replenish_lazy_queue()
            # Track whether this is the last item (for continuation logic)
            playlist = xbmc.PlayList(1)
            pos = playlist.getposition()
            size = playlist.size()
            self._on_last_playlist_item = (pos >= 0 and pos + 1 >= size)

        self._log.debug("Playback started handler complete")
    
    def onAVStarted(self) -> None:
        """
        Handle audio/video stream start.
        
        This fires when the actual A/V stream begins, at which point
        video metadata like duration is available. Used for deferred
        seeking operations (resume points, movie random start).
        """
        # Handle pending resume seek (uses absolute time)
        if self._pending_resume_seek is not None:
            seek_seconds = self._pending_resume_seek
            self._pending_resume_seek = None
            self._log.debug("AV started - executing resume seek", seek_seconds=seek_seconds)
            json_query(build_player_seek_time_query(seek_seconds), True)
            return
        
        # Handle pending movie random start (uses percentage)
        if not self._pending_movie_random_start:
            return
        
        self._pending_movie_random_start = False
        self._log.debug("AV started - processing pending movie random start")
        
        time = runtime_converter(xbmc.getInfoLabel('VideoPlayer.Duration'))
        self._log.debug("Movie duration retrieved", duration_seconds=time)
        
        if time > 0:
            # Calculate random seek point between MIN and MAX percent
            # Squared random factor biases toward earlier positions
            max_percent = int(MOVIE_RANDOM_SEEK_MAX_RATIO * PERCENT_MULTIPLIER)
            random_factor = (random.randint(0, RANDOM_PERCENT_MAX) / 100.0) ** 2
            seek_point = MOVIE_RANDOM_SEEK_MIN_PERCENT + int(
                (max_percent - MOVIE_RANDOM_SEEK_MIN_PERCENT) * random_factor
            )
            self._log.debug("Seeking to random point", seek_percent=seek_point)
            json_query(build_player_seek_query(seek_point), True)
        else:
            self._log.warning("Movie duration unavailable, skipping random start")
    
    def _handle_episode_playback(self, settings: PlaybackSettings) -> None:
        """
        Handle episode playback started.
        
        Args:
            settings: Current playback settings.
        """
        episode_np = parse_season_episode_string(self._ep_details['item']['episode'])
        season_np = parse_season_episode_string(self._ep_details['item']['season'])
        showtitle = self._ep_details['item']['showtitle']
        now_playing_show_id = int(self._ep_details['item']['tvshowid'])
        
        previous_episode_check = settings.previous_episode_check
        random_order_shows = self._get_random_order_shows()
        
        try:
            now_playing_episode_id = int(self._ep_details['item']['id'])
        except KeyError:
            if self._ep_details['item']['episode'] < 0:
                previous_episode_check = False
                now_playing_episode_id = False
                now_playing_show_id = False
            else:
                previous_episode_check, now_playing_show_id, now_playing_episode_id = resolve_istream_episode(
                    now_playing_show_id, showtitle, episode_np, season_np,
                    random_order_shows, refresh_callback=self._on_refresh_show
                )
        
        self._log.debug("Previous episode check", enabled=previous_episode_check)
        
        # Check for previous episode warning
        if (previous_episode_check and 
            now_playing_show_id not in random_order_shows and 
            self._pl_running_local != 'true'):
            # Refresh from shared storage if stale (multi-instance sync)
            # This ensures we use fresh ondeck data before warning about missed episodes
            storage = get_storage()
            if storage.needs_refresh():
                self._log.debug("Cache stale, refreshing before previous episode check",
                               event="playback.refresh", show_id=now_playing_show_id)
                try:
                    _, revision = storage.get_ondeck_bulk([now_playing_show_id])
                    storage.mark_refreshed(revision)
                except Exception as e:
                    self._log.warning("Refresh failed, using cached data",
                                     event="playback.refresh_error", error=str(e))
            
            self._check_previous_episode(
                now_playing_show_id, now_playing_episode_id, showtitle
            )
        
        # Show playlist notification
        if self._pl_running_local == 'true' and settings.playlist_notifications:
            source_id = self._window.getProperty(PROP_SOURCE_ADDON_ID) or None
            source_addon = xbmcaddon.Addon(source_id) if source_id else xbmcaddon.Addon()
            icon = os.path.join(source_addon.getAddonInfo('path'), 'icon.png')
            xbmc.executebuiltin(
                'Notification(%s,%s S%sE%s,%i,%s)' % (
                    lang(32163), showtitle, season_np, episode_np,
                    NOTIFICATION_DURATION_MS, icon
                )
            )
        
        # Handle resume point
        if (self._pl_running_local == 'true' and settings.resume_partials_tv) or \
           self._pl_running_local == 'listview':
            self._handle_resume_point()
        
        # Set up episode tracking
        self._playing_epid = now_playing_episode_id
        self._playing_showid = now_playing_show_id
        self._last_playing_showid = now_playing_show_id
        self._log.debug(
            "PlaybackMonitor detected episode",
            show_id=self._playing_showid,
            episode_id=self._playing_epid
        )
    
    def _check_previous_episode(
        self, 
        show_id: int, 
        episode_id: int, 
        showtitle: str
    ) -> None:
        """
        Check if user is playing a later episode than the stored next episode.
        
        If so, offer to play the stored (earlier) episode instead.
        
        Args:
            show_id: The TV show ID.
            episode_id: The currently playing episode ID.
            showtitle: The show title for display.
        """
        self._log.debug("Previous episode check passed, checking ondeck")
        
        try:
            ondeck_list = ast.literal_eval(
                self._window.getProperty(f"EasyTV.{show_id}.ondeck_list")
            )
            stored_epid = int(
                self._window.getProperty(f"EasyTV.{show_id}.EpisodeID")
            )
            stored_seas = parse_season_episode_string(
                int(self._window.getProperty(f"EasyTV.{show_id}.Season"))
            )
            stored_epis = parse_season_episode_string(
                int(self._window.getProperty(f"EasyTV.{show_id}.Episode"))
            )
        except (ValueError, SyntaxError):
            return
        
        if episode_id in ondeck_list[1:] and stored_epid:
            # Pause playback
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":false},"id":1}'
            )
            
            # Show notification dialog
            from resources.lib.ui.dialogs import show_confirm
            msg = (lang(32161) % (showtitle, stored_seas, stored_epis)) + '\n' + lang(32162)
            source_addon_id = self._window.getProperty(PROP_SOURCE_ADDON_ID) or None
            dialog_result = show_confirm(lang(32160), msg, addon_id=source_addon_id)
            self._log.debug("User dialog result", result=dialog_result)

            if not dialog_result:
                # User chose to continue with current episode - unpause
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                    '"params":{"playerid":1,"play":true},"id":1}'
                )
            else:
                # User chose to play stored episode
                xbmc.executeJSONRPC(
                    '{"jsonrpc": "2.0", "method": "Player.Stop", '
                    '"params": { "playerid": 1 }, "id": 1}'
                )
                xbmc.sleep(PLAYER_STOP_DELAY_MS)
                xbmc.executeJSONRPC(
                    '{ "jsonrpc": "2.0", "method": "Player.Open", '
                    '"params": { "item": { "episodeid": %d }, '
                    '"options":{ "resume": true }  }, "id": 1 }' % stored_epid
                )
    
    def _handle_resume_point(self) -> None:
        """Handle resuming playback from a saved position with slight rewind."""
        res_point = self._ep_details['item'].get('resume', {})
        if res_point.get('position', 0) > 0 and res_point.get('total', 0) > 0:
            # Rewind slightly to help catch context
            seek_seconds = int(max(0, res_point['position'] - RESUME_REWIND_SECONDS))
            self._log.debug(
                "Resume seek pending",
                resume_position=res_point['position'],
                seek_seconds=seek_seconds
            )
            # Defer seek to onAVStarted when player is ready
            self._pending_resume_seek = seek_seconds
    
    def _handle_movie_playback(self, settings: PlaybackSettings) -> None:
        """
        Handle movie playback in EasyTV playlist.
        
        Shows notification and handles resume/random start.
        Seeking is deferred to onAVStarted when video metadata is available.
        
        Args:
            settings: Current playback settings.
        """
        if settings.playlist_notifications:
            source_id = self._window.getProperty(PROP_SOURCE_ADDON_ID) or None
            source_addon = xbmcaddon.Addon(source_id) if source_id else xbmcaddon.Addon()
            icon = os.path.join(source_addon.getAddonInfo('path'), 'icon.png')
            xbmc.executebuiltin(
                'Notification(%s,%s,%i,%s)' % (
                    lang(32163),
                    self._ep_details['item']['label'],
                    NOTIFICATION_DURATION_MS, icon
                )
            )

        resume_info = self._ep_details['item'].get('resume', {})
        
        if settings.resume_partials_movies and resume_info.get('position', 0) > 0 and resume_info.get('total', 0) > 0:
            # Rewind slightly to help catch context
            seek_seconds = int(max(0, resume_info['position'] - RESUME_REWIND_SECONDS))
            self._log.debug(
                "Movie resume seek pending",
                resume_position=resume_info['position'],
                seek_seconds=seek_seconds
            )
            # Defer seek to onAVStarted when player is ready
            self._pending_resume_seek = seek_seconds
        elif settings.movies_random_start and self._ep_details['item'].get('playcount', 0) != 0:
            # Defer random seek to onAVStarted when duration is available
            self._pending_movie_random_start = True
            self._log.debug("Movie random start pending (will seek on AV start)")
    
    def onPlayBackStopped(self) -> None:
        """Handle playback stopped events (user-initiated stop)."""
        self._pending_movie_random_start = False  # Reset any pending random start
        self._pending_resume_seek = None  # Reset any pending resume seek
        self._handle_playback_end(user_stopped=True)

    def onPlayBackEnded(self) -> None:
        """Handle playback ended events (natural end of item)."""
        self._handle_playback_end(user_stopped=False)

    def _handle_playback_end(self, user_stopped: bool) -> None:
        """
        Handle playback end events.

        Shows next episode prompt if configured and conditions are met.
        Also handles playlist continuation prompt when a playlist ends naturally.

        Captures all ended-episode state before sleeping, because
        onPlayBackStarted for the next playlist item may fire during the
        sleep and overwrite _playing_showid, _nextprompt_trigger_override,
        and nextprompt_info.

        Args:
            user_stopped: True if the user explicitly stopped playback,
                False if playback ended naturally.
        """
        self._log.debug("Playback ended", user_stopped=user_stopped)

        # Capture ended-episode state BEFORE sleep — onPlayBackStarted for
        # the next playlist item may fire during the delay and overwrite these
        ended_showid = self._last_playing_showid
        ended_trigger = self._nextprompt_trigger
        ended_override = self._nextprompt_trigger_override
        ended_prompt_info = self._get_nextprompt_info()

        # Give the playlist a chance to start the next item
        xbmc.sleep(PLAYLIST_START_DELAY_MS)

        # Check if something new is playing
        now_name = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
        now_title = xbmc.getInfoLabel('VideoPlayer.Title')
        is_something_playing = now_name != '' or now_title != ''

        # Get current settings
        settings = self._get_settings()

        # Check if playlist truly ended (nothing playing + was EasyTV playlist)
        if not is_something_playing and self._pl_running_local == 'true':
            self._window.setProperty(PROP_PLAYLIST_RUNNING, 'false')

            # Clear any active lazy queue session
            PlaylistSession.clear()

            if not self._on_last_playlist_item:
                # Stopped mid-playlist — clear config
                self._window.clearProperty(PROP_PLAYLIST_CONFIG)
                self._log.debug("Playlist ended mid-playlist, clearing config")
            else:
                # Check continuation settings from the addon that created the playlist
                stored_config = self._window.getProperty(PROP_PLAYLIST_CONFIG)
                if stored_config:
                    try:
                        state = json.loads(stored_config)
                        source_addon_id = state.get('addon_id')
                    except (json.JSONDecodeError, ValueError):
                        source_addon_id = None

                    if get_bool_setting('playlist_continuation', source_addon_id):
                        continuation_duration = get_int_setting(
                            'playlist_continuation_duration', source_addon_id,
                            default=20
                        )
                        continuation_default_action = get_int_setting(
                            'playlist_continuation_default_action',
                            source_addon_id, default=0
                        )
                        self._show_playlist_continuation_prompt(
                            settings, continuation_duration,
                            continuation_default_action
                        )

        # If no episode was being tracked (e.g., movie playback), we're done
        if ended_showid is False:
            self._set_nextprompt_info({})
            return

        # Get info for previously played episode (captured before sleep)
        pre_seas = ended_prompt_info.get('season', None)
        pre_ep = ended_prompt_info.get('episode', None)
        pre_title = ended_prompt_info.get('showtitle', None)
        pre_epid = ended_prompt_info.get('episodeid', None)
        pre_ep_title = ended_prompt_info.get('title', '')

        if any([pre_seas is None, pre_ep is None, pre_title is None, pre_epid is None]):
            self._log.warning(
                "Next prompt info incomplete",
                event="playback.prompt_incomplete",
                season=pre_seas, episode=pre_ep, title=pre_title, episode_id=pre_epid
            )
            self._set_nextprompt_info({})
            return

        # Type narrowing: all values are guaranteed non-None after the guard above
        assert pre_seas is not None
        assert pre_ep is not None
        assert pre_title is not None
        assert pre_epid is not None

        # If nothing playing, or playlist mode with next prompt enabled
        if not is_something_playing or all([
            self._pl_running_local == 'true',
            settings.nextprompt_in_playlist
        ]):
            # Show next episode prompt if conditions are met (using captured state)
            if ended_trigger and ended_override:
                self._show_next_episode_prompt(
                    now_name, pre_seas, pre_ep, pre_title, pre_epid, settings,
                    ended_showid, pre_ep_title
                )

            self._set_nextprompt_info({})

        self._log.debug("Playback ended handler complete")

    def _get_source_addon_info(self):
        # type: () -> tuple
        """Get (path, name, addon_id) of the addon that started playback.

        Checks multiple sources in priority order:
        1. PROP_PLAYLIST_CONFIG — has addon_id for playlist mode (set by
           random_player.py in the clone's process, works without clone update)
        2. PROP_SOURCE_ADDON_ID — window property set by default.py entry point
           (for browse mode, requires clone to have updated code)
        3. Fallback to main addon

        Returns:
            Tuple of (addon_path, addon_name, addon_id_or_none).
        """
        # Try playlist config first (set by random_player.py in clone's process)
        stored_config = self._window.getProperty(PROP_PLAYLIST_CONFIG)
        if stored_config:
            try:
                state = json.loads(stored_config)
                source_id = state.get('addon_id')
                if source_id:
                    source_addon = xbmcaddon.Addon(source_id)
                    return (
                        str(source_addon.getAddonInfo('path')),
                        source_addon.getAddonInfo('name'),
                        source_id
                    )
            except Exception:
                pass

        # Try window property (set by default.py entry point)
        source_id = self._window.getProperty(PROP_SOURCE_ADDON_ID)
        if source_id:
            try:
                source_addon = xbmcaddon.Addon(source_id)
                return (
                    str(source_addon.getAddonInfo('path')),
                    source_addon.getAddonInfo('name'),
                    source_id
                )
            except Exception:
                pass

        # Fallback to main addon
        return (
            self._window.getProperty(PROP_SERVICE_PATH),
            xbmcaddon.Addon().getAddonInfo('name'),
            None
        )

    def _show_next_episode_prompt(
        self,
        now_name: str,
        pre_seas: int,
        pre_ep: int,
        pre_title: str,
        pre_epid: int,
        settings: PlaybackSettings,
        ended_showid: Union[int, bool] = False,
        pre_ep_title: str = '',
    ) -> None:
        """
        Show the next episode prompt dialog.

        Args:
            now_name: Currently playing show name (empty if nothing playing).
            pre_seas: Season number of next episode.
            pre_ep: Episode number of next episode.
            pre_title: Show title.
            pre_epid: Episode ID of next episode.
            settings: Current playback settings.
            ended_showid: Show ID of the ended episode (for poster lookup).
            pre_ep_title: Episode title (e.g., "I See You").
        """
        from resources.lib.ui.dialogs import CountdownDialog

        paused = False

        if now_name != '':
            # Something is playing (EasyTV playlist with prompts enabled)
            # Pause it to show the prompt
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":false},"id":1}'
            )
            paused = True

        self._nextprompt_trigger = False

        SE = 'S%02dE%02d' % (int(pre_seas), int(pre_ep))

        self._log.debug("Prompt default action", action=settings.promptdefaultaction)

        # Always: Yes="Play", No="Don't Play"
        # default_yes determines what happens on timeout
        default_yes = (settings.promptdefaultaction != 1)

        # Primary message: just the show title
        msg = pre_title
        # Subtitle: SE code + episode title (shown in smaller, dimmer font)
        subtitle = SE
        if pre_ep_title:
            subtitle += ' \u2014 ' + pre_ep_title
        addon_path, addon_name, addon_id = self._get_source_addon_info()

        # Get show poster from cached window property
        # Use ended_showid (captured before sleep) to avoid reading the NEW episode's show
        poster = ''
        if ended_showid:
            poster = self._window.getProperty(
                "EasyTV.%s.Art(tvshow.poster)" % ended_showid
            )

        dlg = CountdownDialog(
            'script-easytv-nextepisode.xml', addon_path, 'Default',
            message=msg,
            subtitle=subtitle,
            yes_label=lang(32092),   # "Play"
            no_label=lang(32091),    # "Don't Play"
            duration=settings.promptduration,
            heading=addon_name,
            timer_template=lang(32167),  # "(auto-closing in %s seconds)"
            default_yes=default_yes,
            poster=poster,
            addon_id=addon_id,
            logger=self._log,
        )
        dlg.doModal()
        play = dlg.result
        del dlg

        self._log.debug("Next episode prompt result", play=play)

        if play:
            # Clear playlist config — this replacement episode is not a
            # continuation-eligible playlist, so prevent the continuation
            # prompt from showing when it ends.
            self._window.clearProperty(PROP_PLAYLIST_CONFIG)
            self._window.setProperty(PROP_PLAYLIST_RUNNING, 'false')
            # User chose to play next episode
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0","id": 1, "method": "Playlist.Clear",'
                '"params": {"playlistid": 1}}'
            )
            json_query(build_add_episode_query(int(pre_epid)), False)
            xbmc.sleep(PLAYLIST_ADD_DELAY_MS)
            xbmc.Player().play(xbmc.PlayList(1))
            if paused:
                self._log.debug("Unpausing playback after prompt")
                xbmc.executeJSONRPC(
                    '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                    '"params":{"playerid":1,"play":true},"id":1}'
                )
        elif now_name != '' and paused:
            # User declined - unpause if we paused
            self._log.debug("Unpausing playback (user declined prompt)")
            xbmc.executeJSONRPC(
                '{"jsonrpc":"2.0","method":"Player.PlayPause",'
                '"params":{"playerid":1,"play":true},"id":1}'
            )
    
    def _replenish_lazy_queue(self) -> None:
        """
        Replenish the lazy queue playlist buffer.
        
        Called after each episode completes to maintain a buffer of upcoming
        items. This enables on-deck progression in Both mode - as episodes
        are watched, the on-deck advances and can appear again in the playlist.
        
        The method:
        1. Loads the active session from window property
        2. If session complete or exhausted, clears and returns
        3. Picks next item and adds to playlist
        4. Saves updated session state
        
        Error handling ensures playlist continues even if replenishment fails.
        """
        try:
            with log_timing(self._log, "lazy_queue_replenish") as timer:
                # Load the active session
                session = PlaylistSession.load()
                timer.mark("load")
                
                if session is None:
                    # No active lazy queue session
                    return
                
                # Check if session has reached target length
                if session.is_complete:
                    self._log.debug("Lazy queue complete, clearing session",
                                    event="lazy_queue.complete",
                                    items_added=session.items_added,
                                    target=session.target_length)
                    PlaylistSession.clear()
                    return
                
                # Pick next item to add
                result = session.pick_next_item()
                timer.mark("pick")
                
                if result is None:
                    # All candidates exhausted before reaching target
                    self._log.debug("Lazy queue exhausted, clearing session",
                                    event="lazy_queue.exhausted",
                                    items_added=session.items_added,
                                    target=session.target_length)
                    PlaylistSession.clear()
                    return
                
                item_type, item_id = result
                
                # Add to playlist
                if item_type == 'episode':
                    json_query(build_add_episode_query(item_id), False)
                elif item_type == 'movie':
                    json_query(build_add_movie_query(item_id), False)
                timer.mark("add")
                
                # Save updated session state
                session.save()
                
                self._log.debug("Lazy queue replenished",
                                event="lazy_queue.replenish",
                                item_type=item_type,
                                item_id=item_id,
                                items_added=session.items_added,
                                remaining=session.items_remaining)
        except Exception as e:
            # Log error but don't interrupt playlist playback
            self._log.exception("Lazy queue replenishment failed",
                                event="lazy_queue.replenish_error",
                                error=str(e))
    
    def _show_playlist_continuation_prompt(
        self,
        settings: PlaybackSettings,
        duration_override: Optional[int] = None,
        default_action_override: Optional[int] = None,
    ) -> None:
        """
        Show the playlist continuation prompt dialog.

        Asks the user whether to generate another playlist with the same settings.
        If accepted, sets the PROP_PLAYLIST_REGENERATE window property for the
        daemon to pick up and regenerate the playlist.

        Button layout depends on default_action setting:
        - default_action == 0 (Stop): Yes="Generate", No="Stop" (normal)
        - default_action == 1 (Generate): Yes="Stop", No="Generate" (swapped)
        Timeout always triggers the default action.

        Args:
            settings: Current playback settings.
            duration_override: Optional duration from source addon settings.
            default_action_override: Optional default action from source addon settings.
        """
        from resources.lib.ui.dialogs import CountdownDialog

        default_action = default_action_override if default_action_override is not None else settings.playlist_continuation_default_action
        duration = duration_override if duration_override is not None else settings.playlist_continuation_duration

        self._log.debug("Showing playlist continuation prompt",
                        default_action=default_action)
        addon_path, addon_name, addon_id = self._get_source_addon_info()

        # Always: Yes="Generate", No="Stop"
        # default_yes = True when Generate is the default on timeout
        dlg = CountdownDialog(
            'script-easytv-countdown.xml', addon_path, 'Default',
            message=lang(32618),              # "Playlist finished.\nGenerate another playlist..."
            yes_label=lang(32619),            # "Generate"
            no_label=lang(32620),             # "Stop"
            duration=duration,
            heading=addon_name,
            timer_template=lang(32167),       # "(auto-closing in %s seconds)"
            default_yes=(default_action == 1),
            addon_id=addon_id,
            logger=self._log,
        )
        dlg.doModal()
        generate = dlg.result
        del dlg

        self._log.debug("Continuation prompt decision", generate=generate)

        if generate:
            self._window.setProperty(PROP_PLAYLIST_REGENERATE, 'true')
            self._log.info("Playlist continuation requested", event="playlist.continuation")
        else:
            self._window.clearProperty(PROP_PLAYLIST_CONFIG)
            self._log.debug("Playlist continuation declined, config cleared")

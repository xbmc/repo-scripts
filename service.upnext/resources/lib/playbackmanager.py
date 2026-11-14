# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from math import ceil
from time import monotonic
from xbmc import getCondVisibility, sleep
from api import Api, credits_autoplay_deadline, get_watched_state, mark_watched, playing_episode_id
from demo import DemoOverlay
from player import UpNextPlayer
from playitem import PlayItem
from state import State
from stillwatching import StillWatching
from upnext import UpNext
from utils import (addon_path, calculate_progress_steps, clear_property, event, get_int, get_setting_bool, get_setting_int,
                   log as ulog, set_property)

# How long to let Kodi save the previous episode's own watched state before checking it (seconds)
WATCHED_CHECK_DELAY = 10
# How long the next episode may take to start before the previous one is left as Kodi saved it (seconds)
WATCHED_SWITCH_TIMEOUT = 60
# Don't seek when the next episode already started this close to its resume point (seconds)
RESUME_MARGIN = 10


class PlaybackManager:
    _shared_state = {}
    popup_shown = False  # whether the last launch_up_next() actually showed a popup

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.play_item = PlayItem()
        self.state = State()
        self.player = UpNextPlayer()
        self.demo = DemoOverlay(12005)
        self._watch_limit_check_at = 0
        self._popup_wake_pending = False
        self._watched_checks = []  # episodes Up Next moved on from, to check once Kodi saved them
        self._pending_resume = None  # partly watched next episode, to resume once it plays

    def log(self, msg, level=2):
        ulog(msg, name=self.__class__.__name__, level=level)

    def handle_demo(self):
        if get_setting_bool('enableDemoMode'):
            self.log('Up Next DEMO mode enabled, skipping automatically to the end', 0)
            self.demo.show()
            try:
                total_time = self.player.getTotalTime()
                self.player.seekTime(total_time - 15)
            except RuntimeError as exc:
                self.log('Failed to seekTime(): %s' % exc, 0)
        else:
            self.demo.hide()

    def launch_up_next(self):
        """Show the popup and act on it. Returns True if other playback replaced the episode while the popup was open"""
        self.popup_shown = False
        enable_playlist = get_setting_bool('enablePlaylist')
        episode, source = self.play_item.get_next()
        self.log('Playlist setting: %s' % enable_playlist)
        if source == 'playlist' and not enable_playlist:
            self.log('Playlist integration disabled', 2)
            return False
        if not episode:
            # No episode get out of here
            self.log('Error: no episode could be found to play next...exiting', 1)
            return False
        self.log('episode details %s' % episode, 2)
        try:
            playing_file = self.player.getPlayingFile()
        except RuntimeError:
            self.log('No active playback for the next-episode popup', 2)
            return False
        play_next, keep_playing = self.launch_popup(episode, source)
        if not play_next:
            try:
                current_file = self.player.getPlayingFile()
            except RuntimeError:
                current_file = None
            if current_file != playing_file:
                self.log('Playback changed while the popup was open; skipping stale cleanup', 2)
                # Another file is playing now, its tracking must stay enabled
                return current_file is not None
        self.state.playing_next = play_next

        # Dequeue and stop playback if not playing next file
        if not play_next and self.state.queued:
            self.state.queued = self.api.dequeue_next_item()
        if not keep_playing:
            self.log('Stopping playback', 2)
            self.player.stop()

        self.api.reset_addon_data()
        return False

    def launch_popup(self, episode, source=None):
        episode_id = episode.get('episodeid')
        no_play_count = episode.get('playcount') is None or episode.get('playcount') == 0
        include_play_count = True if self.state.include_watched else no_play_count
        if not include_play_count or self.state.current_episode_id == episode_id:
            # play_next = False
            # keep_playing = True
            # return play_next, keep_playing
            # Don't play next file, but keep playing current file
            return False, True

        # Add next file to playlist if existing playlist is not being used
        if source != 'playlist':
            queued = self.state.queued = self.api.queue_next_item(episode)
        else:
            queued = False

        # We have a next up episode choose mode
        if get_setting_int('simpleMode') == 0:
            next_up_page = UpNext('script-upnext-upnext-simple.xml', addon_path(), 'default', '1080i')
            still_watching_page = StillWatching('script-upnext-stillwatching-simple.xml', addon_path(), 'default', '1080i')
        else:
            next_up_page = UpNext('script-upnext-upnext.xml', addon_path(), 'default', '1080i')
            still_watching_page = StillWatching('script-upnext-stillwatching.xml', addon_path(), 'default', '1080i')

        showing_next_up_page, showing_still_watching_page = self._show_popup(episode, next_up_page, still_watching_page)
        should_play_default, should_play_non_default = self.extract_play_info(next_up_page,
                                                                              showing_next_up_page,
                                                                              showing_still_watching_page,
                                                                              still_watching_page)
        if not self.state.track:
            self.log('exit launch_popup early due to disabled tracking', 2)
            # play_next = False
            # keep_playing = showing_next_up_page
            # return play_next, keep_playing
            # Don't play next file
            # Stop if Still Watching? popup was shown to prevent unwanted playback when using FF or skip
            return False, showing_next_up_page

        play_item_option_1 = (should_play_default and self.state.play_mode == 0)
        play_item_option_2 = (should_play_non_default and self.state.play_mode == 1)
        if not play_item_option_1 and not play_item_option_2:
            if next_up_page.is_dismissed() if showing_next_up_page else still_watching_page.is_dismissed():
                # Back dismisses the prompt without stopping the current video.
                return False, True
            # play_next = False
            # keep_playing = next_up_page.is_cancel() if showing_next_up_page else still_watching_page.is_cancel()
            # keep_playing = keep_playing and not get_setting_bool('stopAfterClose')
            # return play_next, keep_playing
            # Don't play next file, and stop current file if no playback option selected
            return False, (
                (next_up_page.is_cancel() if showing_next_up_page else still_watching_page.is_cancel())
                and not get_setting_bool('stopAfterClose')
            )

        self.log('playing media episode', 2)
        # Signal to trakt previous episode watched
        event(message='NEXTUPWATCHEDSIGNAL', data={'episodeid': self.state.current_episode_id}, encoding='base64')
        self.remember_watched_state(self.state.current_episode_id, source, episode.get('episodeid'))
        self.remember_resume_point(episode, source)
        self._play_next(episode, source, queued, should_play_non_default or next_up_page.is_auto_advance())

        # play_next = True
        # keep_playing = True
        # return play_next, keep_playing
        # Play next file, and keep playing current file
        return True, True

    def _play_next(self, episode, source, queued, advance_queued):
        """Play the next episode: the queued or playlist item, the add-on's episode or the library one"""
        if source == 'playlist' or queued:
            # Play playlist media
            if advance_queued:
                # Early credits expiry must also advance an already queued item.
                if queued and self.pause_until_next():
                    # Kodi resumes the video when it advances the playlist, before the add-on resolves
                    # the queued URL; opening the URL resolves it first and keeps the video paused.
                    self.state.queued = False
                    self.api.play_addon_item()
                else:
                    self.player.playnext()
        elif self.api.has_addon_data():
            # Play add-on media
            self.pause_until_next()
            self.api.play_addon_item()
        else:
            # Play local media
            self.api.play_kodi_item(episode)

    def pause_until_next(self):
        """Pause the video while an add-on starts the next episode (e.g. a source search), if enabled"""
        if not self.api.has_addon_data() or not get_setting_bool('pauseUntilNext'):
            return False
        if not getCondVisibility('Player.Paused'):
            self.player.pause()
        return True

    def _show_popup(self, episode, next_up_page, still_watching_page):
        """Show the popup and wait for it, closing it again if anything goes wrong while it is open"""
        try:
            return self.show_popup_and_wait(episode, next_up_page, still_watching_page)
        except Exception:
            # Don't leave a frozen popup on screen, the service loop logs the error and carries on
            next_up_page.close()
            still_watching_page.close()
            clear_property('service.upnext.dialog')
            raise

    def show_popup_and_wait(self, episode, next_up_page, still_watching_page):
        try:
            play_time = self.player.getTime()
            total_time = self.player.getTotalTime()
            playing_file = self.player.getPlayingFile()
        except RuntimeError:
            self.log('exit early because player is no longer running', 2)
            return False, False
        self._popup_wake_pending = False
        progress_step_size = calculate_progress_steps(total_time - play_time)
        credits_deadline = (credits_autoplay_deadline(self.api.has_addon_data(), play_time, total_time)
                            if self.state.play_mode == 0 else None)
        credits_duration = credits_deadline - play_time if credits_deadline is not None else 0
        next_up_page.set_item(episode)
        next_up_page.set_progress_step_size(progress_step_size)
        still_watching_page.set_item(episode)
        still_watching_page.set_progress_step_size(progress_step_size)
        # Set the countdown before the popup opens, so the skin never shows an empty or stale time
        next_up_page.set_remaining(credits_duration if credits_deadline is not None else total_time - play_time)
        still_watching_page.set_remaining(total_time - play_time)
        played_in_a_row_number = get_setting_int('playedInARow')
        self.log('played in a row settings %s' % played_in_a_row_number, 2)
        self.log('played in a row %s' % self.state.played_in_a_row, 2)
        showing_next_up_page = False
        showing_still_watching_page = False
        self._watch_limit_check_at = 0
        if not self.still_watching_due(played_in_a_row_number):
            self.log('showing next up page as played in a row is %s' % self.state.played_in_a_row, 2)
            next_up_page.set_credits_countdown(int(ceil(credits_duration)) if credits_deadline is not None else None)
            next_up_page.show()
            self.popup_shown = True
            set_property('service.upnext.dialog', 'true')
            showing_next_up_page = True
        else:
            self.log('showing still watching page as played in a row %s' % self.state.played_in_a_row, 2)
            still_watching_page.show()
            self.popup_shown = True
            set_property('service.upnext.dialog', 'true')
            showing_still_watching_page = True
        while (self.player.isPlaying() and (total_time - play_time > 1)
               and not next_up_page.is_cancel() and not next_up_page.is_watch_now() and not next_up_page.is_auto_advance()
               and not still_watching_page.is_still_watching() and not still_watching_page.is_cancel()):
            position = self._playback_position(playing_file)
            if position is None:
                self.log('Playback stopped or changed while the popup was open, closing it', 2)
                if showing_next_up_page:
                    next_up_page.close()
                    showing_next_up_page = False
                if showing_still_watching_page:
                    still_watching_page.close()
                    showing_still_watching_page = False
                break
            play_time, total_time = position
            self.state.watch_timer.observe(playing_file, play_time, self.state.pause)
            self.restore_popup_after_wake(next_up_page if showing_next_up_page else still_watching_page)

            remaining = total_time - play_time
            showing_next_up_page, showing_still_watching_page, credits_deadline = self.check_late_watch_limit(
                next_up_page, still_watching_page, showing_next=showing_next_up_page,
                showing_still=showing_still_watching_page, episode_limit=played_in_a_row_number,
                remaining=remaining, credits_deadline=credits_deadline, play_time=play_time)
            if not self.state.pause:
                if showing_next_up_page:
                    if credits_deadline is not None:
                        remaining = max(0, min(remaining, credits_deadline - play_time))
                        self._update_credits_progress(next_up_page, remaining, credits_duration)
                    else:
                        next_up_page.update_progress_control(remaining=remaining, runtime=episode.get('runtime'))
                elif showing_still_watching_page:
                    still_watching_page.update_progress_control(remaining=remaining, runtime=episode.get('runtime'))
            sleep(100)
        return showing_next_up_page, showing_still_watching_page

    def request_popup_wake(self):
        """Retry a hidden active popup when Kodi wakes."""
        self._popup_wake_pending = True

    def restore_popup_after_wake(self, page):
        """Wait for playback controls to close before restoring a hidden popup."""
        if not getattr(self, '_popup_wake_pending', False) or getCondVisibility('Window.IsVisible(videoosd)'):
            return
        dialog_id = page.playback_dialog_id
        if dialog_id:
            if not getCondVisibility('Window.IsVisible(%d)' % dialog_id):
                page.show()
            self._popup_wake_pending = False

    def check_late_watch_limit(self, next_page, still_page, *, showing_next, showing_still,
                               episode_limit, remaining, credits_deadline, play_time):
        if showing_next:
            next_page.restore_after_playback_controls()
        if (not showing_next or self.state.pause or next_page.is_cancel() or next_page.is_watch_now()
                or next_page.is_auto_advance()):
            return showing_next, showing_still, credits_deadline
        if not self.late_watch_limit_due(episode_limit, remaining, credits_deadline, play_time):
            return showing_next, showing_still, credits_deadline
        # Do not override an explicit action that arrived while settings were read.
        if next_page.is_cancel() or next_page.is_watch_now() or next_page.is_auto_advance():
            return showing_next, showing_still, credits_deadline
        next_page.close()
        still_page.show()
        return False, True, None

    def still_watching_due(self, episode_limit):
        return (bool(episode_limit and int(self.state.played_in_a_row) >= int(episode_limit))
                or self.state.watch_timer.due(get_setting_int('stillWatchingMinutes') or 0,
                                              get_setting_bool('bedtimeEnabled'),
                                              get_setting_int('bedtimeHour') or 0,
                                              get_setting_int('bedtimeMinute') or 0))

    def late_watch_limit_due(self, episode_limit, remaining, credits_deadline, play_time):
        now = monotonic()
        critical = remaining <= 2 or (credits_deadline is not None and credits_deadline - play_time <= 1)
        if now < self._watch_limit_check_at and not critical:
            return False
        self._watch_limit_check_at = now + 1
        return self.still_watching_due(episode_limit)

    def _playback_position(self, playing_file):
        """Return (play_time, total_time) while the popup's own file is playing, otherwise None"""
        try:
            # Times and the credits deadline only apply to the file the popup was opened for
            if self.player.getPlayingFile() != playing_file:
                return None
            return self.player.getTime(), self.player.getTotalTime()
        except RuntimeError:
            return None

    @staticmethod
    def _update_credits_progress(page, remaining, duration):
        progress = 100 * remaining / duration if duration > 0 else 0
        page.set_credits_countdown(int(ceil(remaining)))
        page.update_progress_control(remaining=int(ceil(remaining)), runtime=page.item.get('runtime'), progress=progress)
        if remaining <= 0:
            # Keep autoplay distinct from Watch Now so Still Watching counts survive.
            page.set_auto_advance()

    def remember_watched_state(self, episodeid, source, next_episodeid=None):
        """Note a library episode's play count as Up Next moves on, so it can be marked watched if Kodi doesn't"""
        # Add-on episodes keep their watched state in the add-on, and only library lookups have a library ID
        if source != 'library' or get_int(episodeid, default=0) < 1 or not get_setting_bool('markWatchedEarly', default=True):
            return
        watched = get_watched_state(episodeid)
        try:
            playing_file = self.player.getPlayingFile()
        except RuntimeError:
            playing_file = None
        if watched is not None and playing_file:
            self._watched_checks.append({'episodeid': episodeid, 'playcount': watched[0], 'file': playing_file,
                                         'next': next_episodeid, 'started': monotonic(), 'switched': None})

    def check_previous_watched(self):
        """Mark episodes Up Next moved on from as watched when Kodi didn't count them"""
        # Kodi only counts an episode stopped after playcountminimumpercent (90% by default), so Watch Now or
        # the credits delay can leave it unwatched with a resume point. Only act once the next episode is
        # playing, and only after Kodi has saved the previous one: that avoids counting it twice, and Kodi's
        # resume point overwriting this.
        if not self._watched_checks:
            return
        now = monotonic()
        try:
            playing_file = self.player.getPlayingFile()
        except RuntimeError:
            playing_file = None
        for check in list(self._watched_checks):
            if check['switched'] is None:
                playing = playing_episode_id() if playing_file and playing_file != check['file'] else None
                if playing is not None and playing == check['next']:
                    check['switched'] = now
                elif playing not in (None, check['episodeid']) or now - check['started'] > WATCHED_SWITCH_TIMEOUT:
                    # Another episode is playing, or the next one never started: Up Next didn't move on.
                    # Without item details yet, or for a video that isn't a library episode, keep waiting.
                    self._watched_checks.remove(check)
                continue
            if now < check['switched'] + WATCHED_CHECK_DELAY:
                continue
            self._watched_checks.remove(check)
            watched = get_watched_state(check['episodeid'])
            if watched is None or watched[0] > check['playcount']:
                continue
            self.log('Marking episode %s as watched, as Kodi did not count it when Up Next moved on' % check['episodeid'], 2)
            mark_watched(check['episodeid'], check['playcount'] + 1)

    def remember_resume_point(self, episode, source):
        """Note where a partly watched library episode was left, so it continues there when Up Next plays it"""
        self._pending_resume = None
        if source != 'library' or not get_setting_bool('resumeNextEpisode', default=True):
            return
        episodeid = get_int(episode.get('episodeid'), default=0)
        position = (episode.get('resume') or {}).get('position') or 0
        if not isinstance(episodeid, int) or episodeid < 1 or position <= 0:
            return
        self._pending_resume = {'episodeid': episodeid, 'previous': self.state.current_episode_id,
                                'position': position, 'started': monotonic(), 'stops': UpNextPlayer.stop_count}

    def resume_next_episode(self):
        """Seek a partly watched next episode to its resume point once it plays"""
        # Up Next plays a library episode as a queued playlist item (Watch Now, autoplay or the end of
        # the file), which doesn't use its resume point, so seek once it plays. If Kodi did resume it,
        # the position is already there and nothing happens.
        pending = self._pending_resume
        if not pending:
            return
        if (monotonic() - pending['started'] > WATCHED_SWITCH_TIMEOUT
                or UpNextPlayer.stop_count != pending['stops']):
            # The next episode never started, or the viewer stopped playback: leave a later start alone
            self._pending_resume = None
            return
        playing = playing_episode_id()
        if playing in (None, pending['previous']):
            return  # still opening, no item details yet, or the previous episode is still reported
        if playing != pending['episodeid']:
            self._pending_resume = None  # something else plays instead
            return
        try:
            play_time = self.player.getTime()
            if play_time > pending['position'] + RESUME_MARGIN:
                return  # still the previous episode's time, wait for the new one
            if play_time < pending['position'] - RESUME_MARGIN:
                self.log('Resuming episode %s at %d secs' % (playing, pending['position']), 2)
                self.player.seekTime(pending['position'])
        except RuntimeError as exc:
            self.log('Waiting to resume the next episode: %s' % exc, 2)
            return  # try again on the next pass, until the timeout
        self._pending_resume = None

    def extract_play_info(self, next_up_page, showing_next_up_page, showing_still_watching_page, still_watching_page):
        if showing_next_up_page:
            next_up_page.close()
            should_play_default = not next_up_page.is_cancel()
            should_play_non_default = next_up_page.is_watch_now()
        elif showing_still_watching_page:
            still_watching_page.close()
            should_play_default = still_watching_page.is_still_watching()
            should_play_non_default = still_watching_page.is_still_watching()
        else:
            # FIXME: This is a workaround until we handle this better (see comments in #142)
            # The popup was already closed because playback stopped or changed
            clear_property('service.upnext.dialog')
            return False, False

        if next_up_page.is_watch_now() or still_watching_page.is_still_watching():
            self.state.played_in_a_row = 1
            timer = getattr(self.state, 'watch_timer', None)
            if timer:
                timer.reset(acknowledge_bedtime=still_watching_page.is_still_watching())
        else:
            self.state.played_in_a_row += 1
        clear_property('service.upnext.dialog')
        return should_play_default, should_play_non_default

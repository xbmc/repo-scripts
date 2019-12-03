# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from datetime import datetime, timedelta
import xbmc
from . import pages
from . import utils
from .api import Api
from .player import Player
from .playitem import PlayItem
from .state import State


class PlaybackManager:  # pylint: disable=invalid-name
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.play_item = PlayItem()
        self.state = State()
        self.player = Player()

    def log(self, msg, level=2):
        utils.log(msg, name=self.__class__.__name__, level=level)

    def launch_up_next(self):
        playlist_item = True
        episode = self.play_item.get_next()
        if not episode:
            playlist_item = False
            episode = self.play_item.get_episode()
            if episode is None:
                # No episode get out of here
                self.log('Error: no episode could be found to play next...exiting', 1)
                return
        self.log('episode details %s' % episode, 2)
        self.launch_popup(episode, playlist_item)
        self.api.reset_addon_data()

    def launch_popup(self, episode, playlist_item):
        episode_id = episode.get('episodeid')
        no_play_count = episode.get('playcount') is None or episode.get('playcount') == 0
        include_play_count = True if self.state.include_watched else no_play_count
        if not include_play_count or self.state.current_episode_id == episode_id:
            return
        # We have a next up episode choose mode
        next_up_page, still_watching_page = pages.set_up_pages()
        showing_next_up_page, showing_still_watching_page, total_time = (
            self.show_popup_and_wait(episode, next_up_page, still_watching_page))
        should_play_default, should_play_non_default = (
            self.extract_play_info(next_up_page, showing_next_up_page, showing_still_watching_page,
                                   still_watching_page, total_time))
        if not self.state.track:
            self.log('exit launch_popup early due to disabled tracking', 2)
            return
        play_item_option_1 = (should_play_default and self.state.play_mode == '0')
        play_item_option_2 = (should_play_non_default and self.state.play_mode == '1')
        if not play_item_option_1 and not play_item_option_2:
            return

        self.log('playing media episode', 2)
        # Signal to trakt previous episode watched
        utils.event(message='NEXTUPWATCHEDSIGNAL', data=dict(episodeid=self.state.current_episode_id), encoding='base64')
        # Play media
        if playlist_item:
            self.player.seekTime(self.player.getTotalTime())
        elif self.api.has_addon_data():
            self.api.play_addon_item()
        else:
            self.api.play_kodi_item(episode)

    def show_popup_and_wait(self, episode, next_up_page, still_watching_page):
        play_time = self.player.getTime()
        total_time = self.player.getTotalTime()
        progress_step_size = utils.calculate_progress_steps(total_time - play_time)
        episode_runtime = episode.get('runtime') is not None
        next_up_page.set_item(episode)
        next_up_page.set_progress_step_size(progress_step_size)
        still_watching_page.set_item(episode)
        still_watching_page.set_progress_step_size(progress_step_size)
        played_in_a_row_number = utils.settings('playedInARow')
        self.log('played in a row settings %s' % played_in_a_row_number, 2)
        self.log('played in a row %s' % self.state.played_in_a_row, 2)
        showing_next_up_page = False
        showing_still_watching_page = False
        hide_for_short_videos = bool(self.state.short_play_notification == 'false'
                                     and self.state.short_play_length >= total_time
                                     and self.state.short_play_mode == 'true')
        if int(self.state.played_in_a_row) <= int(played_in_a_row_number) and not hide_for_short_videos:
            self.log('showing next up page as played in a row is %s' % self.state.played_in_a_row, 2)
            next_up_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_next_up_page = True
        elif not hide_for_short_videos:
            self.log('showing still watching page as played in a row %s' % self.state.played_in_a_row, 2)
            still_watching_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_still_watching_page = True
        while (self.player.isPlaying() and (total_time - play_time > 1)
               and not next_up_page.is_cancel() and not next_up_page.is_watch_now()
               and not still_watching_page.is_still_watching() and not still_watching_page.is_cancel()):
            play_time = self.player.getTime()
            total_time = self.player.getTotalTime()
            if episode_runtime:
                end_time = total_time - play_time + episode.get('runtime')
                end_time = datetime.now() + timedelta(seconds=end_time)
                time_format = xbmc.getRegion('time').replace(':%S', '')  # Strip off seconds
                end_time = end_time.strftime(time_format).lstrip('0')  # Remove leading zero on all platforms
            else:
                end_time = None
            if not self.state.pause:
                if showing_next_up_page:
                    next_up_page.update_progress_control(end_time)
                elif showing_still_watching_page:
                    still_watching_page.update_progress_control(end_time)
            xbmc.sleep(100)
        return showing_next_up_page, showing_still_watching_page, total_time

    def extract_play_info(self, next_up_page, showing_next_up_page, showing_still_watching_page, still_watching_page, total_time):
        if self.state.short_play_length >= total_time and self.state.short_play_mode == 'true':
            # Play short video and don't add to playcount
            self.state.played_in_a_row += 0
            if next_up_page.is_watch_now() or still_watching_page.is_still_watching():
                self.state.played_in_a_row = 1
            should_play_default = not next_up_page.is_cancel()
            should_play_non_default = next_up_page.is_watch_now()
        else:
            if showing_next_up_page:
                next_up_page.close()
                should_play_default = not next_up_page.is_cancel()
                should_play_non_default = next_up_page.is_watch_now()
            elif showing_still_watching_page:
                still_watching_page.close()
                should_play_default = still_watching_page.is_still_watching()
                should_play_non_default = still_watching_page.is_still_watching()

            if next_up_page.is_watch_now() or still_watching_page.is_still_watching():
                self.state.played_in_a_row = 1
            else:
                self.state.played_in_a_row += 1
        utils.window('service.upnext.dialog', clear=True)
        return should_play_default, should_play_non_default

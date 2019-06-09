import xbmc
import json
import resources.lib.utils as utils
import resources.lib.pages as pages
from resources.lib.api import Api
from resources.lib.playItem import PlayItem
from resources.lib.state import State
from resources.lib.player import Player


class PlaybackManager:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.play_item = PlayItem()
        self.state = State()
        self.player = Player()

    def log(self, msg, lvl=2):
        class_name = self.__class__.__name__
        utils.log("%s %s" % (utils.addon_name(), class_name), msg, int(lvl))

    def launch_up_next(self):
        episode = self.play_item.get_episode()
        if episode is None:
            # no episode get out of here
            self.log("Error: no episode could be found to play next...exiting", 1)
            return
        self.log("episode details %s" % json.dumps(episode), 2)
        self.launch_popup(episode)
        self.api.reset_addon_data()

    def launch_popup(self, episode):
        episode_id = episode["episodeid"]
        no_play_count = episode["playcount"] is None or episode["playcount"] == 0
        include_play_count = True if self.state.include_watched else no_play_count
        if include_play_count and self.state.current_episode_id != episode_id:
            # we have a next up episode choose mode
            next_up_page, still_watching_page = pages.set_up_pages()
            showing_next_up_page, showing_still_watching_page, total_time = (
                self.show_popup_and_wait(episode, next_up_page, still_watching_page))
            should_play_default, should_play_non_default = (
                self.extract_play_info(next_up_page, showing_next_up_page, showing_still_watching_page,
                                       still_watching_page, total_time))
            if not self.state.track:
                self.log("exit launch_popup early due to disabled tracking", 2)
                return
            play_item_option_1 = (should_play_default and self.state.playMode == "0")
            play_item_option_2 = (should_play_non_default and self.state.playMode == "1")
            if play_item_option_1 or play_item_option_2:
                self.log("playing media episode", 2)
                # Signal to trakt previous episode watched
                utils.event("NEXTUPWATCHEDSIGNAL", {'episodeid': self.state.current_episode_id})
                # Play media
                if not self.api.has_addon_data():
                    self.api.play_kodi_item(episode)
                else:
                    self.api.play_addon_item()

    def show_popup_and_wait(self, episode, next_up_page, still_watching_page):
        play_time = self.player.getTime()
        total_time = self.player.getTotalTime()
        progress_step_size = utils.calculate_progress_steps(total_time - play_time)
        next_up_page.setItem(episode)
        next_up_page.setProgressStepSize(progress_step_size)
        still_watching_page.setItem(episode)
        still_watching_page.setProgressStepSize(progress_step_size)
        played_in_a_row_number = utils.settings("playedInARow")
        self.log("played in a row settings %s" % json.dumps(played_in_a_row_number), 2)
        self.log("played in a row %s" % json.dumps(self.state.played_in_a_row), 2)
        showing_next_up_page = False
        showing_still_watching_page = False
        hide_for_short_videos = (self.state.short_play_notification == "false") and (
                self.state.short_play_length >= total_time) and (
                                        self.state.short_play_mode == "true")
        if int(self.state.played_in_a_row) <= int(played_in_a_row_number) and not hide_for_short_videos:
            self.log(
                "showing next up page as played in a row is %s" % json.dumps(self.state.played_in_a_row), 2)
            next_up_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_next_up_page = True
        elif not hide_for_short_videos:
            self.log(
                "showing still watching page as played in a row %s" % json.dumps(self.state.played_in_a_row), 2)
            still_watching_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_still_watching_page = True
        while (self.player.isPlaying() and (
                total_time - play_time > 1) and not next_up_page.isCancel() and not next_up_page.isWatchNow() and
                not still_watching_page.isStillWatching() and not still_watching_page.isCancel()):
            xbmc.sleep(100)
            try:
                play_time = self.player.getTime()
                total_time = self.player.getTotalTime()
                if not self.state.pause:
                    if showing_next_up_page:
                        next_up_page.updateProgressControl()
                    elif showing_still_watching_page:
                        still_watching_page.updateProgressControl()
            except Exception as e:
                self.log("error show_popup_and_wait  %s" % repr(e), 1)
        return showing_next_up_page, showing_still_watching_page, total_time

    def extract_play_info(self, next_up_page, showing_next_up_page, showing_still_watching_page, still_watching_page,
                          total_time):
        if self.state.short_play_length >= total_time and self.state.short_play_mode == "true":
            # play short video and don't add to playcount
            self.state.played_in_a_row += 0
            if next_up_page.isWatchNow() or still_watching_page.isStillWatching():
                self.state.played_in_a_row = 1
            should_play_default = not next_up_page.isCancel()
            should_play_non_default = next_up_page.isWatchNow()
        else:
            if showing_next_up_page:
                next_up_page.close()
                should_play_default = not next_up_page.isCancel()
                should_play_non_default = next_up_page.isWatchNow()
            elif showing_still_watching_page:
                still_watching_page.close()
                should_play_default = still_watching_page.isStillWatching()
                should_play_non_default = still_watching_page.isStillWatching()

            if next_up_page.isWatchNow() or still_watching_page.isStillWatching():
                self.state.played_in_a_row = 1
            else:
                self.state.played_in_a_row += 1
        utils.window('service.upnext.dialog', clear=True)
        return should_play_default, should_play_non_default

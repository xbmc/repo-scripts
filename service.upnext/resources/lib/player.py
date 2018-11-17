import xbmc
import resources.lib.utils as utils
from resources.lib.api import api
from resources.lib.upnext import UpNext
from resources.lib.stillwatching import StillWatching


# service class for playback monitoring
class Player(xbmc.Player):
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.log("Starting playback monitor service", 1)
        self.playMode = utils.settings("autoPlayMode")
        self.short_play_mode = utils.settings("shortPlayMode")
        self.short_play_notification = utils.settings("shortPlayNotification")
        self.short_play_length = int(utils.settings("shortPlayLength")) * 60
        self.include_watched = utils.settings("includeWatched") == "true"
        self.current_tvshow_id = None
        self.current_episode_id = None
        self.tv_show_id = None
        self.played_in_a_row = 1
        self.api = api()
        xbmc.Player.__init__(self)

    def log(self, msg, lvl=2):
        class_name = self.__class__.__name__
        utils.log("%s %s" % (utils.addon_name(), class_name), msg, int(lvl))

    def onAVStarted(self):
        # Will be called when kodi starts playing a file
        self.api.reset_addon_data()
        if utils.settings("developerMode") == "true":
            self.developer_play_back()

    def handle_now_playing_result(self, result):
        if 'result' in result:
            item_type = result["result"]["item"]["type"]
            current_episode_number = result["result"]["item"]["episode"]
            current_season_id = result["result"]["item"]["season"]
            current_show_title = result["result"]["item"]["showtitle"].encode('utf-8')
            current_show_title = utils.unicodetoascii(current_show_title)
            self.tv_show_id = result["result"]["item"]["tvshowid"]
            if item_type == "episode":
                # Try to get tvshowid by showtitle from kodidb if tvshowid is -1 like in strm streams which are added to kodi db
                if int(self.tv_show_id) == -1:
                    self.tv_show_id = self.api.showtitle_to_id(title=current_show_title)
                    self.log("Fetched missing tvshowid " + str(self.tv_show_id), 2)

                # Get current episodeid
                current_episode_id = self.api.get_episode_id(showid=str(self.tv_show_id), showseason=current_season_id,
                                                           showepisode=current_episode_number)
                self.current_episode_id = current_episode_id
                if self.current_tvshow_id != self.tv_show_id:
                    self.current_tvshow_id = self.tv_show_id
                    self.played_in_a_row = 1

    def calculateProgressSteps(self, period):
        self.log("calculateProgressSteps notification time %s" % period, 2)
        part1 = (100.0 / int(period))
        self.log("calculateProgressSteps 100 / notification time %s" % part1, 2)
        part2 = (100.0 / int(period)) / 10
        self.log("calculateProgressSteps (100 / notification time) / 10 %s" % part2, 2)
        return (100.0 / int(period)) / 10

    def autoPlayPlayback(self):
        episode = self.get_episode()
        if episode is None:
            # no episode get out of here
            self.log("Error: no episode could be found to play next...exiting", 1)
            return
        self.log("episode details %s" % str(episode), 2)
        self.handle_play_back(episode)

    def handle_play_back(self, episode):
        episode_id = episode["episodeid"]
        no_play_count = episode["playcount"] is None or episode["playcount"] == 0
        include_play_count = True if self.include_watched else no_play_count
        if include_play_count and self.current_episode_id != episode_id:
            # we have a next up episode choose mode
            next_up_page, still_watching_page = self.set_up_pages()
            showing_next_up_page, showing_still_watching_page, total_time = self.show_popup_and_wait(episode,
                                                                                                     next_up_page,
                                                                                                     still_watching_page)
            should_play_default, should_play_non_default = self.extract_play_info(next_up_page, showing_next_up_page,
                                                                                  showing_still_watching_page,
                                                                                  still_watching_page, total_time)

            if (should_play_default and self.playMode == "0") or (should_play_non_default and self.playMode == "1"):
                self.log("playing media episode id %s" % str(episode_id), 2)
                # Signal to trakt previous episode watched
                utils.event("NEXTUPWATCHEDSIGNAL", {'episodeid': self.current_episode_id})
                # Play media
                if not self.api.has_addon_data():
                    self.api.play_kodi_item(episode)
                else:
                    self.api.play_addon_item()

    def set_up_pages(self):
        if utils.settings("simpleMode") == "0":
            next_up_page = UpNext("script-upnext-upnext-simple.xml",
                                  utils.addon_path(), "default", "1080i")
            still_watching_page = StillWatching(
                "script-upnext-stillwatching-simple.xml",
                utils.addon_path(), "default", "1080i")
        else:
            next_up_page = UpNext("script-upnext-upnext.xml",
                                  utils.addon_path(), "default", "1080i")
            still_watching_page = StillWatching(
                "script-upnext-stillwatching.xml",
                utils.addon_path(), "default", "1080i")
        return next_up_page, still_watching_page

    def show_popup_and_wait(self, episode, next_up_page, still_watching_page):
        play_time = xbmc.Player().getTime()
        total_time = xbmc.Player().getTotalTime()
        progress_step_size = self.calculateProgressSteps(total_time - play_time)
        next_up_page.setItem(episode)
        next_up_page.setProgressStepSize(progress_step_size)
        still_watching_page.setItem(episode)
        still_watching_page.setProgressStepSize(progress_step_size)
        played_in_a_row_number = utils.settings("playedInARow")
        self.log("played in a row settings %s" % str(played_in_a_row_number), 2)
        self.log("played in a row %s" % str(self.played_in_a_row), 2)
        showing_next_up_page = False
        showing_still_watching_page = False
        hide_for_short_videos = (self.short_play_notification == "false") and (
                    self.short_play_length >= total_time) and (
                                        self.short_play_mode == "true")
        if int(self.played_in_a_row) <= int(played_in_a_row_number) and not hide_for_short_videos:
            self.log(
                "showing next up page as played in a row is %s" % str(self.played_in_a_row), 2)
            next_up_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_next_up_page = True
        elif not hide_for_short_videos:
            self.log(
                "showing still watching page as played in a row %s" % str(self.played_in_a_row), 2)
            still_watching_page.show()
            utils.window('service.upnext.dialog', 'true')
            showing_still_watching_page = True
        while xbmc.Player().isPlaying() and (
                total_time - play_time > 1) and not next_up_page.isCancel() and not next_up_page.isWatchNow() and not still_watching_page.isStillWatching() and not still_watching_page.isCancel():
            xbmc.sleep(100)
            try:
                play_time = xbmc.Player().getTime()
                total_time = xbmc.Player().getTotalTime()
                if showing_next_up_page:
                    next_up_page.updateProgressControl()
                elif showing_still_watching_page:
                    still_watching_page.updateProgressControl()
            except:
                pass
        return showing_next_up_page, showing_still_watching_page, total_time

    def extract_play_info(self, next_up_page, showing_next_up_page, showing_still_watching_page, still_watching_page,
                          total_time):
        if self.short_play_length >= total_time and self.short_play_mode == "true":
            # play short video and don't add to playcount
            self.played_in_a_row += 0
            self.log("Continuing short video autoplay - %s")
            if next_up_page.isWatchNow() or still_watching_page.isStillWatching():
                self.played_in_a_row = 1
            should_play_default = not next_up_page.isCancel()
        else:
            if showing_next_up_page:
                next_up_page.close()
                utils.window('service.upnext.dialog', clear=True)
                should_play_default = not next_up_page.isCancel()
                should_play_non_default = next_up_page.isWatchNow()
            elif showing_still_watching_page:
                still_watching_page.close()
                utils.window('service.upnext.dialog', clear=True)
                should_play_default = still_watching_page.isStillWatching()
                should_play_non_default = still_watching_page.isStillWatching()

            if next_up_page.isWatchNow() or still_watching_page.isStillWatching():
                self.played_in_a_row = 1
            else:
                self.played_in_a_row += 1
        return should_play_default, should_play_non_default

    def get_episode(self):
        current_file = xbmc.Player().getPlayingFile()
        if not self.api.has_addon_data():
            # Get the active player
            result = self.api.getNowPlaying()
            self.handle_now_playing_result(result)
            # get the next episode from kodi
            episode = self.api.handle_kodi_lookup_of_episode(self.tv_show_id, current_file, self.include_watched,
                                                             self.current_episode_id)
        else:
            episode = self.api.handle_addon_lookup_of_next_episode()
            current_episode = self.api.handle_addon_lookup_of_current_episode()
            self.current_episode_id = current_episode["episodeid"]
            if self.current_tvshow_id != current_episode["tvshowid"]:
                self.current_tvshow_id = current_episode["tvshowid"]
                self.played_in_a_row = 1
        return episode

    def developer_play_back(self):
        episode = utils.loadTestData()
        next_up_page, next_up_page_simple, still_watching_page, still_watching_page_simple = self.developer_pages_setup(
            episode)
        if utils.settings("windowMode") == "0":
            next_up_page.show()
        elif utils.settings("windowMode") == "1":
            next_up_page_simple.show()
        elif utils.settings("windowMode") == "2":
            still_watching_page.show()
        elif utils.settings("windowMode") == "3":
            still_watching_page_simple.show()
        utils.window('service.upnext.dialog', 'true')

        while xbmc.Player().isPlaying() and not next_up_page.isCancel() and not next_up_page.isWatchNow() and not still_watching_page.isStillWatching() and not still_watching_page.isCancel():
            xbmc.sleep(100)
            next_up_page.updateProgressControl()
            next_up_page_simple.updateProgressControl()
            still_watching_page.updateProgressControl()
            still_watching_page_simple.updateProgressControl()

        if utils.settings("windowMode") == "0":
            next_up_page.close()
        elif utils.settings("windowMode") == "1":
            next_up_page_simple.close()
        elif utils.settings("windowMode") == "2":
            still_watching_page.close()
        elif utils.settings("windowMode") == "3":
            still_watching_page_simple.close()
        utils.window('service.upnext.dialog', clear=True)

    def developer_pages_setup(self, episode):
        next_up_page_simple = UpNext("script-upnext-upnext-simple.xml",
                                     utils.addon_path(), "default", "1080i")
        still_watching_page_simple = StillWatching(
            "script-upnext-stillwatching-simple.xml",
            utils.addon_path(), "default", "1080i")
        next_up_page = UpNext("script-upnext-upnext.xml",
                              utils.addon_path(), "default", "1080i")
        still_watching_page = StillWatching(
            "script-upnext-stillwatching.xml",
            utils.addon_path(), "default", "1080i")
        next_up_page.setItem(episode)
        next_up_page_simple.setItem(episode)
        still_watching_page.setItem(episode)
        still_watching_page_simple.setItem(episode)
        notification_time = utils.settings("autoPlaySeasonTime")
        progress_step_size = self.calculateProgressSteps(notification_time)
        self.log("progress_step_size %s" % str(progress_step_size), 2)
        next_up_page.setProgressStepSize(progress_step_size)
        next_up_page_simple.setProgressStepSize(progress_step_size)
        still_watching_page.setProgressStepSize(progress_step_size)
        still_watching_page_simple.setProgressStepSize(progress_step_size)
        return next_up_page, next_up_page_simple, still_watching_page, still_watching_page_simple

import resources.lib.utils as utils


# keeps track of the state parameters
class State:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.playMode = utils.settings("autoPlayMode")
        self.short_play_mode = utils.settings("shortPlayMode")
        self.short_play_notification = utils.settings("shortPlayNotification")
        self.short_play_length = int(utils.settings("shortPlayLength")) * 60
        self.include_watched = utils.settings("includeWatched") == "true"
        self.current_tv_show_id = None
        self.current_episode_id = None
        self.tv_show_id = None
        self.played_in_a_row = 1


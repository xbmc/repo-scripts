import json
import resources.lib.utils as utils
from resources.lib.api import Api
from resources.lib.player import Player
from resources.lib.state import State


class PlayItem:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.api = Api()
        self.player = Player()
        self.state = State()

    def log(self, msg, lvl=2):
        class_name = self.__class__.__name__
        utils.log("%s %s" % (utils.addon_name(), class_name), msg, int(lvl))

    def get_episode(self):
        current_file = self.player.getPlayingFile()
        if not self.api.has_addon_data():
            # Get the active player
            result = self.api.get_now_playing()
            self.handle_now_playing_result(result)
            # get the next episode from kodi
            episode = (
                self.api.handle_kodi_lookup_of_episode(
                    self.state.tv_show_id, current_file, self.state.include_watched, self.state.current_episode_id))
        else:
            episode = self.api.handle_addon_lookup_of_next_episode()
            current_episode = self.api.handle_addon_lookup_of_current_episode()
            self.state.current_episode_id = current_episode["episodeid"]
            if self.state.current_tv_show_id != current_episode["tvshowid"]:
                self.state.current_tv_show_id = current_episode["tvshowid"]
                self.state.played_in_a_row = 1
        return episode

    def handle_now_playing_result(self, result):
        if 'result' in result:
            item_type = result["result"]["item"]["type"]
            current_episode_number = result["result"]["item"]["episode"]
            current_season_id = result["result"]["item"]["season"]
            current_show_title = result["result"]["item"]["showtitle"].encode('utf-8')
            current_show_title = utils.unicode_to_ascii(current_show_title)
            self.state.tv_show_id = result["result"]["item"]["tvshowid"]
            if item_type == "episode":
                if int(self.state.tv_show_id) == -1:
                    self.state.tv_show_id = self.api.showtitle_to_id(title=current_show_title)
                    self.log("Fetched missing tvshowid " + json.dumps(self.state.tv_show_id), 2)

                # Get current episodeid
                current_episode_id = self.api.get_episode_id(
                    showid=str(self.state.tv_show_id), show_season=current_season_id,
                    show_episode=current_episode_number)
                self.state.current_episode_id = current_episode_id
                if self.state.current_tv_show_id != self.state.tv_show_id:
                    self.state.current_tv_show_id = self.state.tv_show_id
                    self.state.played_in_a_row = 1

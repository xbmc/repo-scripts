import xbmc
import json
import resources.lib.utils as utils


class Api:
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self.data = {}

    def log(self, msg, lvl=2):
        class_name = self.__class__.__name__
        utils.log("%s %s" % (utils.addon_name(), class_name), msg, int(lvl))

    def has_addon_data(self):
       return self.data

    def reset_addon_data(self):
        self.data = {}

    def addon_data_received(self, data):
        self.log("addon_data_received called with data %s " % json.dumps(data), 2)
        self.data = data

    @staticmethod
    def play_kodi_item(episode):
        xbmc.executeJSONRPC(
            '{ "jsonrpc": "2.0", "id": 0, "method": "Player.Open", '
            '"params": { "item": {"episodeid": ' + str(episode["episodeid"]) + '} } }')

    def play_addon_item(self):
        self.log("sending data to addon to play:  %s " % json.dumps(self.data['play_info']), 2)
        utils.event(self.data['id'], self.data['play_info'], "upnextprovider")

    def handle_addon_lookup_of_next_episode(self):
        if self.data:
            text = ("handle_addon_lookup_of_next_episode episode returning data %s "
                    % json.dumps(self.data["next_episode"]))
            self.log(text, 2)
            return self.data["next_episode"]

    def handle_addon_lookup_of_current_episode(self):
        if self.data:
            text = ("handle_addon_lookup_of_current episode returning data %s "
                    % json.dumps(self.data["current_episode"]))
            self.log(text, 2)
            return self.data["current_episode"]

    def notification_time(self):
        return self.data.get('notification_time') or utils.settings('autoPlaySeasonTime')

    def get_now_playing(self):
        # Get the active player
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
        self.log("Got active player %s" % json.dumps(result), 2)
        result = json.loads(result)

        # Seems to work too fast loop whilst waiting for it to become active
        while not result["result"]:
            result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Player.GetActivePlayers"}')
            self.log("Got active player %s" % json.dumps(result), 2)
            result = json.loads(result)

        if 'result' in result and result["result"][0] is not None:
            playerid = result["result"][0]["playerid"]

            # Get details of the playing media
            self.log("Getting details of now playing media", 2)
            result = xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "id": 1, "method": "Player.GetItem", "params": {"playerid": %s, '
                '"properties": ["showtitle", "tvshowid", "episode", "season", "playcount","genre","plotoutline"] } }'
                % str(playerid))
            self.log("Got details of now playing media %s" % json.dumps(result), 2)

            result = json.loads(result)
            return result

    def handle_kodi_lookup_of_episode(self, tvshowid, current_file, include_watched, current_episode_id):
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)

        if result:
            result = json.loads(result)
            self.log("Got details of next up episode %s" % json.dumps(result), 2)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                episode = self.find_next_episode(result, current_file, include_watched, current_episode_id)
                return episode

    def handle_kodi_lookup_of_current_episode(self, tvshowid, current_episode_id):
        result = xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": %d, '
            '"properties": [ "title", "playcount", "season", "episode", "showtitle", "plot", '
            '"file", "rating", "resume", "tvshowid", "art", "firstaired", "runtime", "writer", '
            '"dateadded", "lastplayed" , "streamdetails"], "sort": {"method": "episode"}}, "id": 1}'
            % tvshowid)
        self.log("Find current episode called", 2)
        position = 0
        if result:
            result = json.loads(result)
            xbmc.sleep(100)

            # Find the next unwatched and the newest added episodes
            if "result" in result and "episodes" in result["result"]:
                for episode in result["result"]["episodes"]:
                    # find position of current episode
                    if current_episode_id == episode["episodeid"]:
                        # found a match so get out of here
                        break
                    position += 1

                # now return the episode
                self.log("Find current episode found episode in position: %s" % str(position), 2)
                try:
                    episode = result["result"]["episodes"][position]
                except Exception as e:
                    # no next episode found
                    episode = None
                    self.log("error handle_kodi_lookup_of_current_episode  %s" % repr(e), 1)

                return episode

    def showtitle_to_id(self, title):
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetTVShows",
            "params": {
                "properties": ["title"]
            },
            "id": "libTvShows"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'tvshows' in json_result['result']:
                json_result = json_result['result']['tvshows']
                for tvshow in json_result:
                    if tvshow['label'] == title:
                        return tvshow['tvshowid']
            return '-1'
        except Exception as e:
            self.log("error showtitle_to_id  %s" % repr(e), 1)
            return '-1'

    def get_episode_id(self, showid, show_season, show_episode):
        show_season = int(show_season)
        show_episode = int(show_episode)
        episodeid = 0
        query = {
            "jsonrpc": "2.0",
            "method": "VideoLibrary.GetEpisodes",
            "params": {
                "properties": ["season", "episode"],
                "tvshowid": int(showid)
            },
            "id": "1"
        }
        try:
            json_result = json.loads(xbmc.executeJSONRPC(json.dumps(query, encoding='utf-8')))
            if 'result' in json_result and 'episodes' in json_result['result']:
                json_result = json_result['result']['episodes']
                for episode in json_result:
                    if episode['season'] == show_season and episode['episode'] == show_episode:
                        if 'episodeid' in episode:
                            episodeid = episode['episodeid']
            return episodeid
        except Exception as e:
            self.log("error get_episode_id  %s" % repr(e), 1)
            return episodeid

    def find_next_episode(self, result, current_file, include_watched, current_episode_id):
        position = 0
        for episode in result["result"]["episodes"]:
            # find position of current episode
            if current_episode_id == episode["episodeid"]:
                # found a match so add 1 for the next and get out of here
                position += 1
                break
            position += 1
        # check if it may be a multi-part episode
        while result["result"]["episodes"][position]["file"] == current_file:
            position += 1
        # skip already watched episodes?
        while not include_watched and result["result"]["episodes"][position]["playcount"] > 1:
            position += 1

        try:
            episode = result["result"]["episodes"][position]
        except Exception as e:
            self.log("error get_episode_id  %s" % repr(e), 1)
            # no next episode found
            episode = None

        return episode

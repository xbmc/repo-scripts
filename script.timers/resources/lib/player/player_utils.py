import xbmc
import xbmcaddon
import xbmcgui
from resources.lib.player.mediatype import AUDIO, PICTURE, TYPES, VIDEO
from resources.lib.timer.storage import Storage
from resources.lib.utils import picture_utils
from resources.lib.utils.jsonrpc_utils import json_rpc
from resources.lib.utils.vfs_utils import (build_playlist, convert_to_playlist,
                                           get_asset_path, get_files_and_type,
                                           get_longest_common_path, is_script,
                                           is_smart_playlist)

REPEAT_OFF = "off"
REPEAT_ONE = "one"
REPEAT_ALL = "all"


class State():

    def __init__(self) -> None:
        self.playerId: int = None
        self.type: str = None
        self.position: int = -1
        self.time: int = 0
        self.playlistId: int = None
        self.playlist = None
        self.repeat: str = REPEAT_OFF
        self.shuffled: bool = False
        self.speed: float = 1

    def __str__(self) -> str:

        return "State[playerId=%i, type=%s, position=%i, time=%i, playlistId=%i, repeat=%s, shuffled=%s, speed=%f]" % (self.playerId or -1,
                                                                                                                       self.type or "",
                                                                                                                       self.position,
                                                                                                                       self.time,
                                                                                                                       self.playlistId or -1,
                                                                                                                       self.repeat,
                                                                                                                       self.shuffled,
                                                                                                                       self.speed)


def preview(addon: xbmcaddon.Addon, timerid: int, player: 'xbmc.Player') -> None:

    timer = Storage().load_timer_from_storage(timerid)

    if timer.is_playing_media_timer():

        xbmcgui.Dialog().notification(addon.getLocalizedString(32027), timer.label,
                                      icon=get_asset_path("icon_timers.png"))

        if is_script(timer.path):
            run_addon(timer.path)

        elif is_smart_playlist(timer.path):
            play_directory(timer.path)

        elif timer.media_type == PICTURE:
            if timer.shuffle and timer.is_play_at_start_timer() and timer.is_stop_at_end_timer():
                amount = 1 + timer.duration_timedelta.total_seconds() // get_slideshow_staytime()
            else:
                amount = 0

            play_slideshow(timer.path, shuffle=timer.shuffle, amount=amount)

        else:
            playlist = build_playlist(path=timer.path, label=timer.label)
            player.play(playlist.directUrl or playlist)

    else:
        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32109))


def play_directory(url: str) -> None:

    xbmc.executebuiltin('PlayMedia("%s","isdir")' % url)


def play_slideshow(path: str, beginSlide: str = None, shuffle=False, amount=0) -> None:

    if shuffle and amount:
        path, shuffle = picture_utils.get_good_matching_random_folder(
            path=path, wanted_amount=amount)
        beginSlide = None

    cmd = "SlideShow(\"%s\",recursive,%s%s)" % (path,
                                                "random" if shuffle else "notrandom",
                                                (",beginslide=%s" % beginSlide) if beginSlide and "," not in beginSlide else "")
    xbmc.log("[script.timers] %s" % cmd, xbmc.LOGINFO)
    xbmc.executebuiltin(cmd)


def run_addon(path: str) -> None:

    if path.startswith("script://"):
        xbmc.executebuiltin("RunAddon(%s)" % path[9:])

    elif path.startswith("script."):
        xbmc.executebuiltin("RunScript(%s)" % path)

    else:
        xbmc.executebuiltin("PlayMedia(%s)" % path)


def get_volume(or_default=100) -> int:

    try:
        _result = json_rpc("Application.GetProperties",
                           {"properties": ["volume"]})
        return _result["volume"]

    except:
        return or_default


def set_volume(vol: int) -> None:

    xbmc.executebuiltin("SetVolume(%i)" % vol)


def reset_volume(addon: xbmcaddon.Addon) -> None:

    vol_default = addon.getSettingInt("vol_default")
    set_volume(vol_default)
    xbmcgui.Dialog().notification(addon.getLocalizedString(
        32027), addon.getLocalizedString(32112))


def get_active_players_with_playlist(type=None) -> 'dict[str, State]':

    def _get_player_properties(playerId: int) -> dict:

        _params = {
            "playerid": playerId,
            "properties": [
                "type",
                "time",
                "playlistid",
                "position",
                "repeat",
                "shuffled",
                "speed"
            ]
        }
        return json_rpc("Player.GetProperties", _params)

    def _get_playlist(playListID: int) -> dict:

        _params = {
            "playlistid": playListID,
            "properties": [
                "file"
            ],
            "limits": {
                "start": 0
            }
        }
        return json_rpc("Playlist.GetItems", _params)

    def _get_player_item(playListID: int) -> dict:

        _params = [playListID, ["file"]]
        return json_rpc("Player.GetItem", _params)

    result = dict()

    _activePlayers = get_active_players()
    if type:
        if type in _activePlayers:
            _activePlayers = {
                type: _activePlayers[type]
            }
        else:
            return result

    for _type in _activePlayers:
        _playerId = _activePlayers[_type]
        _props = _get_player_properties(_playerId)
        if _props["position"] != -1:
            _playList = _get_playlist(_props["playlistid"])
        else:
            _playList = {
                "items": []
            }
            _player = xbmc.Player()
            if _player.isPlaying():
                _item = _get_player_item(_playerId)
                _playList["items"].append(
                    {
                        "label": _item["item"]["label"],
                        "file": _player.getPlayingFile()
                    })

        state = State()
        state.playerId = _playerId
        state.type = _props["type"]
        state.position = _props["position"]
        state.time = (_props["time"]["hours"] * 3600 + _props["time"]["minutes"] *
                      60 + _props["time"]["seconds"] if _props["position"] >= 0 else 0)
        state.playlistId = _props["playlistid"] if _props["position"] != -1 else None
        state.playlist = _playList["items"]
        state.repeat = _props["repeat"]
        state.shuffled = _props["shuffled"]
        state.speed = _props["speed"]

        result[_type] = state

    return result


def set_repeat(mode: str) -> None:

    _REPEAT_COMMAND = {
        REPEAT_OFF: "RepeatOff",
        REPEAT_ONE: "RepeatOne",
        REPEAT_ALL: "RepeatAll"
    }

    xbmc.executebuiltin("PlayerControl(%s)" % _REPEAT_COMMAND[mode])


def set_shuffled(value: bool) -> None:

    xbmc.executebuiltin("PlayerControl(%s)" %
                        "RandomOn" if value else "RandomOff")


def set_speed(speed: float) -> None:

    xbmc.executebuiltin("PlayerControl(Tempo(%f))" % speed)


def get_active_players() -> 'dict[str,int]':

    _json_active_players = json_rpc("Player.GetActivePlayers")
    active_players = dict()
    for ap in _json_active_players:
        active_players[ap["type"]] = ap["playerid"]

    return active_players


def stop_player(type: str) -> State:

    _activePlayers = get_active_players_with_playlist(type)
    if type not in _activePlayers:
        return None

    json_rpc("Player.Stop", params=[_activePlayers[type].playerId])
    xbmc.sleep(500)

    return _activePlayers[type]


def get_slideshow_staytime() -> int:

    _result = json_rpc("Settings.GetSettingValue", params={
        "setting": "slideshow.staytime"})
    return _result["value"]


def get_types_replaced_by_type(type: str) -> 'list[str]':

    type = type if type else VIDEO
    if type == AUDIO:
        return [VIDEO, AUDIO]

    elif type == VIDEO:
        return [PICTURE, VIDEO, AUDIO]

    elif type == PICTURE:
        return [PICTURE, VIDEO]

    else:
        return []


def add_player_state_to_path(state: State) -> str:

    paths = [item["file"] for item in state.playlist]
    longest_common_path = get_longest_common_path(paths)
    playing_file = xbmc.Player().getPlayingFile()
    if len(paths) > 1 and playing_file:
        files, type = get_files_and_type(longest_common_path)
        state.position = files.index(playing_file)

    return "%s#%i|%i" % (longest_common_path, state.position, state.time)


def parse_player_state_from_path(path: str, label="") -> 'tuple[str,State]':

    if "#" not in path:
        return path, None

    try:
        i = path.rindex("#")
        real_path = path[:i]
        paths, type = get_files_and_type(real_path)
        params = path[i+1:].split("|")

        state = State()
        state.playerId = TYPES.index(type)
        state.type = type
        state.playlistId = TYPES.index(type)
        state.playlist = convert_to_playlist(
            paths=paths, type=type, label=label)

        state.position = int(params[0])
        state.time = int(params[1])

        return real_path, state

    except:
        return path, None

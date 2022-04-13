import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from resources.lib.timer.timer import Timer
from resources.lib.utils import jsonrpc_utils

REPEAT_OFF = "off"
REPEAT_ONE = "one"
REPEAT_ALL = "all"


class State():

    type = None
    position = -1
    time = 0
    playlist = None
    repeat = REPEAT_OFF
    shuffled = False
    speed = 1


def preview(addon: xbmcaddon.Addon, timer: Timer, player: xbmc.Player) -> None:

    addon_dir = xbmcvfs.translatePath(addon.getAddonInfo('path'))

    path = addon.getSettingString("timer_%i_filename" % timer).strip()
    if path != "":
        icon_file = os.path.join(
            addon_dir, "resources", "assets", "icon_sleep.png")

        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32110) % addon.getLocalizedString(32004 + timer),
            icon=icon_file)

        player.play(path)

    else:
        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32109))


def get_volume(or_default=100) -> int:

    try:
        _result = jsonrpc_utils.json_rpc("Application.GetProperties",
                                         {"properties": ["volume"]})
        return _result["volume"]

    except:
        return or_default


def set_volume(vol: int) -> None:

    xbmc.executebuiltin("SetVolume(%i)" % vol)


def reset_volume(addon: xbmcaddon.Addon, ) -> None:

    vol_default = addon.getSettingInt("vol_default")
    set_volume(vol_default)
    xbmcgui.Dialog().notification(addon.getLocalizedString(
        32027), addon.getLocalizedString(32112))


def get_active_player_with_playlist() -> State:

    def _get_player_properties(playerId: int):

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
        return jsonrpc_utils.json_rpc("Player.GetProperties", _params)

    def _get_playlist(playListID: int):

        _params = {
            "playlistid": playListID,
            "properties": [
                "file"
            ],
            "limits": {
                "start": 0
            }
        }
        return jsonrpc_utils.json_rpc("Playlist.GetItems", _params)

    _player = xbmc.Player()
    if not _player.isPlaying():
        return None

    _playerIDs = jsonrpc_utils.json_rpc("Player.GetActivePlayers")
    if not len(_playerIDs):
        return None

    _props = _get_player_properties(_playerIDs[0]["playerid"])
    if _props["position"] != -1:
        _playList = _get_playlist(_props["playlistid"])
    else:
        _playList = {
            "items": [
                {
                    "label": None,
                    "file": _player.getPlayingFile()
                }
            ]
        }

    state = State()
    state.type = _props["type"]
    state.position = _props["position"]
    state.time = _props["time"]["hours"] * 3600 + _props["time"]["minutes"] * \
        60 + _props["time"]["seconds"] if _props["position"] >= 0 else 0
    state.playlist = _playList["items"]
    state.repeat = _props["repeat"]
    state.shuffled = _props["shuffled"]
    state.speed = _props["speed"]
    return state


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

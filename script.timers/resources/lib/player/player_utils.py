import os

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
from resources.lib.player.mediatype import AUDIO, PICTURE, VIDEO
from resources.lib.timer.timer import Timer
from resources.lib.utils.jsonrpc_utils import json_rpc
from resources.lib.utils.vfs_utils import build_playlist, is_script

REPEAT_OFF = "off"
REPEAT_ONE = "one"
REPEAT_ALL = "all"


class State():

    playerId = None
    type = None
    position = -1
    time = 0
    playlistId = None
    playlist = None
    repeat = REPEAT_OFF
    shuffled = False
    speed = 1


def preview(addon: xbmcaddon.Addon, timerid: int, player: 'xbmc.Player') -> None:

    addon_dir = xbmcvfs.translatePath(addon.getAddonInfo('path'))

    timer = Timer.init_from_settings(timerid)

    if timer._is_playing_media_timer():
        icon_file = os.path.join(
            addon_dir, "resources", "assets", "icon.png")

        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32110) % addon.getLocalizedString(32004 + timerid),
            icon=icon_file)

        if is_script(timer.s_path):
            run_addon(timer.s_path)

        elif timer.s_mediatype == PICTURE:
            play_slideshow(timer.s_path, shuffle=timer.b_shuffle)

        else:
            playlist = build_playlist(timer.s_path)
            player.play(playlist)

    else:
        xbmcgui.Dialog().notification(addon.getLocalizedString(
            32027), addon.getLocalizedString(32109))


def play_slideshow(path: str, beginSlide=None, shuffle=False) -> None:

    xbmc.executebuiltin("SlideShow(%s,recursive,%srandom%s)" %
                        (path,
                            "" if shuffle else "not",
                            (",beginslide=\"%s\"" % beginSlide) if beginSlide else ""))


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

    result = dict()

    _activePlayers = get_active_players()
    if type and type in _activePlayers:
        _activePlayers = {
            type: _activePlayers[type]
        }

    for _type in _activePlayers:
        _playerId = _activePlayers[_type]
        _props = _get_player_properties(_playerId)
        if _props["position"] != -1:
            _playList = _get_playlist(_props["playlistid"])
        else:
            _playList = {
                "items": []
            }
            if xbmc.Player().isPlaying():
                _playList["items"].append(
                    {
                        "label": None,
                        "file": xbmc.Player().getPlayingFile()
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

# -*- coding: utf-8 -*-
from resources.lib.kodi import utils


def get_kodi_volume():
    result = utils.kodi_json_request({"jsonrpc": "2.0",
                                      "method": "Application.GetProperties",
                                      "params": {"properties": ["volume"]},
                                      "id": 7})
    return result["volume"]


def set_kodi_volume(volume):
    utils.kodi_json_request({"jsonrpc": "2.0",
                             "method": "Application.SetVolume",
                             "params": {"volume": volume}, "id": 8})


def get_youtube_plugin_path(videoid, seek=0):  # type: (str, str) -> str
    return "plugin://plugin.video.tubed/?mode=play&video_id={}&start_offset={}".format(
        videoid, float(seek))


def remote_connected(name):
    utils.notification(message="{} {}!".format(name, utils.get_string(32006)))


def remote_disconnected(name):
    utils.notification(message="{} {}!".format(name, utils.get_string(32007)))

"""Instant subtitle lookup: the moment a video starts, load the best subtitle for it.

on_play.py starts this with Kodi as the addon's service. It waits for the player to
say a video has started, asks logic.instant whether to look one up and which to load,
and hands Kodi the file. Everything that can be decided without Kodi is in logic.py
and tested there; what is left here is reading the player and loading the file.
"""


import json
import os
import traceback

import kodi_side
import logic
import xbmc
import xbmcaddon
from subtitledb import SubtitleDbError, per_language


class Player(xbmc.Player):
    """Notes each start. The lookup runs on the service's loop, not in the callback."""

    def __init__(self):
        super().__init__()
        self.started = False

    def onAVStarted(self):
        self.started = True


def kodi_languages():
    """The languages the viewer has Kodi download subtitles in, in their order."""
    request = {"jsonrpc": "2.0", "id": 1, "method": "Settings.GetSettingValue",
               "params": {"setting": "subtitles.languages"}}
    try:
        reply = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except (TypeError, ValueError):
        return []
    value = (reply.get("result") or {}).get("value") or []
    return [str(name) for name in value] if isinstance(value, list) else []


def stream_languages(player):
    """The English name of each subtitle stream the video has, "" where it has none."""
    return [xbmc.convertLanguage(code, xbmc.ENGLISH_NAME) if code else ""
            for code in player.getAvailableSubtitleStreams() or []]


def look_up(player, monitor):
    addon = xbmcaddon.Addon()  # a fresh one, so a setting changed since Kodi started is read
    if not addon.getSettingBool("instant") or not player.isPlayingVideo():
        return
    path = kodi_side.playing_file()
    if not path or path.startswith("pvr://") or xbmc.getCondVisibility("Pvr.IsPlayingTv"):
        return
    try:
        seconds = player.getTotalTime()
    except RuntimeError:
        return
    client = logic.make_client(addon.getSetting("api_base") or None,
                               timeout=logic.ON_PLAY_TIMEOUT_S, stopping=monitor.abortRequested,
                               version=addon.getAddonInfo("version"))
    try:
        item, said = logic.instant(
            client, kodi_side.player_info(), kodi_languages(), stream_languages(player),
            limit=per_language(addon.getSetting("per_language")), seconds=seconds,
            log=kodi_side.log)
        if item is None:
            kodi_side.log("on play: nothing loaded, %s" % said)
            return
        content = client.download(item["download_url"])
    except SubtitleDbError as err:
        kodi_side.log("on play: the lookup failed: %s" % err, xbmc.LOGWARNING)
        return
    if kodi_side.playing_file() != path:
        kodi_side.log("on play: the video changed before subtitle %d was loaded" % item["id"])
        return
    saved = kodi_side.save(item, content)
    player.setSubtitles(saved)
    kodi_side.log("on play: loaded %s, %s, for %s" % (
        os.path.basename(saved), item["language_name"], said))
    kodi_side.notify(addon.getLocalizedString(32014).format(item["language_name"]))


def main():
    monitor = xbmc.Monitor()
    player = Player()
    kodi_side.log("lookup on play started")
    while not monitor.waitForAbort(1):
        if not player.started:
            continue
        player.started = False
        try:
            look_up(player, monitor)
        except Exception:  # one bad lookup must not end the service
            kodi_side.log("on play: %s" % traceback.format_exc(), xbmc.LOGERROR)

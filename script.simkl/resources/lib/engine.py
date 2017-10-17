#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import xbmc
import json
import threading

from interface import notify
from utils import log
from utils import get_setting
from utils import get_str

class Player(xbmc.Player):
    def __init__(self, api):
        xbmc.Player.__init__(self)
        self._api = api
        self._tracker = None
        self._playback_lock = threading.Event()

    def onPlayBackStarted(self):
        self._stop_tracker()
        if self._api.isLoggedIn:
            self._detect_item()

    def onPlayBackStopped(self):
        log("Stop clear")
        self._stop_tracker()

    def onPlayBackEnded(self):
        log("End clear")
        self._stop_tracker()

    def _detect_item(self):
        self._item = {}
        _data = json.loads(xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0", "method": "Player.GetItem",
            "params": {
                "properties": ["showtitle", "title", "season", "episode", "file", "tvshowid", "imdbnumber","genre" ,"year"],
                "playerid": 1},
            "id": "VideoGetItem"})))["result"]["item"]
        is_tv = _data["tvshowid"] != -1 and _data["season"] > 0 and _data["episode"] > 0
        if is_tv:
            _data["imdbnumber"] = json.loads(xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails",
                "params": {"tvshowid": _data["tvshowid"], "properties": ["imdbnumber"]},
                "id": 1
            })))["result"]["tvshowdetails"]["imdbnumber"]

        log("Full: {0}".format(_data))
        if ("imdbnumber" not in _data or _data["imdbnumber"] == '') and _data['file']:
            _r = self._api.detect_by_file(filename=_data['file'])
            if isinstance(_r, dict) and "type" in _r:
                if _r["type"] == "episode":
                    # TESTED
                    if "episode" in _r:
                        self._item = {
                            "type": "episodes",
                            "title": _r["show"]["title"],
                            "simkl": _r["episode"]["ids"]["simkl"],
                            "season": _r["episode"]["season"],
                            "episode": _r["episode"]["episode"]
                        }
                elif _r["type"] == "movie" and "movie" in _r:
                    # TESTED
                    self._item = {
                        "type": "movies",
                        "title": _r["movie"]["title"],
                        "year": _r["movie"]["year"],
                        "simkl": _r["movie"]["ids"]["simkl"]
                    }

        if not self._item and (_data["title"] or _data["showtitle"]):
            if is_tv:
                # TESTED
                self._item = {
                    "type": "shows",
                    "title": _data["showtitle"],
                    "tvdb": _data["imdbnumber"],
                    "season": _data["season"],
                    "episode": _data["episode"]
                }
            else:
                # TESTED
                self._item = {
                    "type": "movies",
                    "title": _data["title"],
                    "year": _data["year"],
                    "imdb": _data["imdbnumber"],
                }

        if self._item:
            self._run_tracker()

    def _run_tracker(self):
        self._playback_lock.set()
        self._tracker = threading.Thread(target=self._thread_tracker)
        self._tracker.start()

    def _stop_tracker(self):
        if hasattr(self, '_playback_lock'): self._playback_lock.clear()
        if not hasattr(self, '_tracker'): return
        if self._tracker is None: return
        if self._tracker.isAlive(): self._tracker.join()
        self._tracker = None

    def _thread_tracker(self):
        log("in tracker thread")
        total_time = self.getTotalTime()
        total_time_min = int(get_setting("min-length"))
        perc_mark = int(get_setting("scr-pct"))
        self._is_detected = True
        timeout = 1000
        # if total_time set and is lower than total_time_min then we do not start the loop at all and stop the thread,
        if total_time <= 0 or total_time > total_time_min:
            while self._playback_lock.isSet() and not xbmc.abortRequested:
                try:
                    # The max() assures that the total time is over two minutes
                    # preventing it from scrobbling while buffering and solving #31
                    if min(99, 100 * self.getTime() / max(120, total_time)) >= perc_mark:
                        success = self._api.mark_as_watched(self._item)
                        if not success:
                            if timeout == 1000:
                                log("Failed to scrobble")
                                notify(get_str(32080))
                                timeout = 30000
                            elif (self.getTime() / total_time) > 0.95:
                                log("Stopped scrobbling")
                                notify(get_str(32081))
                                break
                            else:
                                log("Retrying")

                        elif success and bool(get_setting("bubble")):
                            self._show_bubble(self._item)
                            break
                except:
                    pass
                xbmc.sleep(timeout)
        log('track stop')

    def _show_bubble(self, item):
        log("in bubble")
        if "title" in item:
            txt = ''
            title = item["title"]
            if "episode" in item:
                txt = "- S{:02}E{:02}".format(item["season"], item["episode"])
            elif "year" in item:
                title = "".join([title, " (", str(item["year"]), ")"])

            log("Show Bubble")
            notify(get_str(32028).format(txt), title=title)

    @staticmethod
    def getMediaType():
        if xbmc.getCondVisibility('Container.Content(tvshows)'):
            return "show"
        elif xbmc.getCondVisibility('Container.Content(seasons)'):
            return "season"
        elif xbmc.getCondVisibility('Container.Content(episodes)'):
            return "episode"
        elif xbmc.getCondVisibility('Container.Content(movies)'):
            return "movie"
        else:
            return None
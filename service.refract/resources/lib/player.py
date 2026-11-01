"""Watches playback and marks a finished episode or movie as watched on Refract.

A play counts once its furthest position passes the threshold set in the add-on
(90 % by default), checked when it stops or ends, as Refract does for Plex and
Jellyfin: a partial play writes nothing.
"""
import datetime

import xbmc

from resources.lib import api, kodi

ID_ORDER = ("tmdb", "tvdb", "imdb")


def _ids(uniqueid):
    """Kodi's `uniqueid` names a scraper's ids; keep the ones Refract understands, best first."""
    uniqueid = uniqueid or {}
    return [(key, uniqueid[key]) for key in ID_ORDER if uniqueid.get(key)]


class Playing:
    """What is playing, read through JSON-RPC when playback starts."""

    def __init__(self, item):
        self.kind = item.get("type")
        self.title = item.get("showtitle") or item.get("title") or item.get("label") or ""
        self.label = item.get("label") or self.title
        self.season = item.get("season")
        self.episode = item.get("episode")
        self.ids = _ids(item.get("uniqueid"))
        self.show_ids = []
        if self.kind == "episode" and item.get("tvshowid", -1) > 0:
            details = kodi.jsonrpc("VideoLibrary.GetTVShowDetails",
                                   {"tvshowid": item["tvshowid"], "properties": ["uniqueid"]})
            self.show_ids = _ids(((details or {}).get("tvshowdetails") or {}).get("uniqueid"))
        self.total = 0.0
        self.furthest = 0.0
        self.idempotency_key = api.new_idempotency_key()

    def trackable(self):
        if self.kind == "movie":
            return bool(self.ids)
        if self.kind == "episode":
            return bool(self.ids or self.show_ids) and self.season is not None and self.episode is not None
        return False


class RefractPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.playing = None

    # Kodi callbacks ---------------------------------------------------------

    def onAVStarted(self):
        self._finish()
        result = kodi.jsonrpc("Player.GetItem", {
            "playerid": 1,
            "properties": ["uniqueid", "season", "episode", "tvshowid", "showtitle", "title"],
        })
        item = (result or {}).get("item") or {}
        playing = Playing(item)
        if not playing.trackable():
            kodi.log("not tracked: {0} ({1})".format(playing.label, playing.kind))
            return
        try:
            playing.total = self.getTotalTime()
        except RuntimeError:
            playing.total = 0.0
        self.playing = playing

    def onPlayBackEnded(self):
        # Kodi reached the end by itself: the last periodic reading can be seconds short of it.
        if self.playing and self.playing.total:
            self.playing.furthest = self.playing.total
        self._finish()

    def onPlayBackSeek(self, time_ms, seek_offset_ms):
        if self.playing:
            self.playing.furthest = max(self.playing.furthest, time_ms / 1000.0)

    def onPlayBackStopped(self):
        self._finish()

    # Called by the service loop every few seconds ---------------------------

    def tick(self):
        if not self.playing or not self.isPlayingVideo():
            return
        try:
            position = self.getTime()
            if not self.playing.total:
                self.playing.total = self.getTotalTime()
        except RuntimeError:
            return
        self.playing.furthest = max(self.playing.furthest, position)

    # Marking ----------------------------------------------------------------

    def _finish(self):
        playing, self.playing = self.playing, None
        if not playing or not playing.total:
            return
        percent = 100.0 * playing.furthest / playing.total
        if percent < kodi.setting_int("threshold"):
            kodi.log("{0}: {1:.0f}% watched, not marked".format(playing.label, percent))
            return
        if playing.kind == "episode" and not kodi.setting_bool("mark_episodes"):
            return
        if playing.kind == "movie" and not kodi.setting_bool("mark_movies"):
            return
        try:
            marked = self._mark_episode(playing) if playing.kind == "episode" else self._mark_movie(playing)
        except api.NotConnected:
            kodi.notify(kodi.string(32030))
            return
        except Exception as error:  # a scrobble must never break playback
            kodi.log("{0}: not marked, {1}".format(playing.label, error), xbmc.LOGWARNING)
            return
        if not marked:
            kodi.notify(kodi.string(32028, playing.label))
        elif kodi.setting_bool("notify"):
            kodi.notify(kodi.string(32027, playing.label))

    def _mark_episode(self, playing):
        # The episode's own id first: Refract maps it to its show and to TMDB's numbering.
        for id_type, external_id in playing.ids:
            for found in api.search(id_type, external_id, "episode"):
                if self._mark_found_episode(found):
                    return True
        # Else the show with Kodi's season and episode numbers. A library scraped from TMDB numbers
        # episodes as TMDB does; one scraped from TheTVDB has no TMDB id and numbers them as TheTVDB.
        numbering = "tmdb" if any(id_type == "tmdb" for id_type, _ in playing.show_ids) else "tvdb"
        for id_type, external_id in playing.show_ids:
            found_all = api.search(id_type, external_id, "episode",
                                   season=playing.season, number=playing.episode, numbering=numbering)
            for found in found_all:
                if self._mark_found_episode(found):
                    return True
        return False

    @staticmethod
    def _mark_found_episode(found):
        episode = found.get("episode") or {}
        show = (found.get("show") or {}).get("ids") or {}
        if show.get("refract") and episode.get("season") is not None and episode.get("number"):
            api.mark_episode(show["refract"], episode["season"], episode["number"])
            return True
        return False

    def _mark_movie(self, playing):
        for id_type, external_id in playing.ids:
            for found in api.search(id_type, external_id, "movie"):
                movie_id = (found.get("ids") or {}).get("refract")
                if movie_id:
                    watched_at = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
                    api.log_movie(movie_id, watched_at, playing.idempotency_key)
                    return True
        return False

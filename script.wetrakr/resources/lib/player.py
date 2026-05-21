"""
player.py — xbmc.Player subclass that detects playback events
and sends scrobble data to the WeTrakr API.

Callbacks:
  onAVStarted()       — media stream ready → send 'playing' event
  onPlayBackEnded()   — file finished naturally → send 'scrobble' event
  onPlayBackStopped() — user stopped playback → send 'scrobble' if threshold met

All outbound HTTP calls are dispatched on a daemon thread so Kodi's player
callbacks return immediately — otherwise the UI freezes for the duration of
the HTTP round-trip (visible on low-end devices like Vero 4K+ on the
'completed' scrobble).
"""

import threading

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.api import WeTrakrAPI
from resources.lib import utils
from resources.lib import rating as rating_mod
from resources.lib.notification import notify as _notify


def _dispatch_async(target, *args, **kwargs):
    """Run a callable in a daemon thread; never blocks the caller."""
    t = threading.Thread(target=target, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


class WeTrakrPlayer(xbmc.Player):
    """Monitors video playback and scrobbles to WeTrakr."""

    def __init__(self):
        super().__init__()
        self._reset_state()

    def _reset_state(self):
        """Reset all playback tracking state."""
        self.current_item = None
        self.current_show = None
        self.total_time = 0
        self.scrobbled = False
        self.playing_sent = False
        self.media_type = None
        self.last_progress = 0.0
        self.poster_art = None

    def _get_settings(self):
        """Read current add-on settings."""
        addon = xbmcaddon.Addon("script.wetrakr")
        return {
            "api_token": addon.getSetting("api_token"),
            "api_url": addon.getSetting("api_url") or "https://api.wetrakr.com",
            "threshold": int(addon.getSetting("scrobble_threshold") or "80"),
            "track_playing": addon.getSetting("track_playing") == "true",
            "track_watched": addon.getSetting("track_watched") == "true",
            "debug": addon.getSetting("debug") == "true",
            # Notification toggles — default ON for backwards compatibility.
            "notify_playing": addon.getSetting("notify_playing") != "false",
            "notify_paused": addon.getSetting("notify_paused") != "false",
            "notify_scrobble": addon.getSetting("notify_scrobble") != "false",
        }

    def _get_api(self, settings=None):
        """Create a WeTrakrAPI instance from current settings."""
        if settings is None:
            settings = self._get_settings()
        token = settings["api_token"]
        if not token:
            return None
        return WeTrakrAPI(settings["api_url"], token)

    def _log(self, msg, level=xbmc.LOGINFO):
        xbmc.log("[WeTrakr] {}".format(msg), level)

    # -----------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------

    def onAVStarted(self):
        """Called when audio/video stream is ready (preferred over onPlayBackStarted)."""
        self._log("onAVStarted triggered")
        self._reset_state()

        try:
            if not self.isPlayingVideo():
                self._log("Not playing video, ignoring")
                return

            # Small delay — Kodi's JSON-RPC may not have player info ready yet
            xbmc.sleep(1500)

            # Get active player and item metadata
            player_id = utils.get_active_player_id()
            if player_id is None:
                self._log("No active player found")
                return

            item = utils.get_playing_item(player_id)

            # Fallback: if JSON-RPC returns empty, try getVideoInfoTag()
            if not item or item.get("type", "unknown") == "unknown":
                self._log("JSON-RPC empty, trying getVideoInfoTag fallback")
                item = self._get_item_from_info_tag(item or {})

            self._log("Raw item: {}".format(str(item)[:500]))
            item_type = item.get("type", "unknown")
            self._log("Item type: {}, title: {}".format(item_type, item.get("title", "?")))

            if item_type not in ("movie", "episode"):
                self._log("Ignoring non-video type: {}".format(item_type))
                return

            self.current_item = item
            self.media_type = item_type
            self.total_time = self.getTotalTime() if self.isPlayingVideo() else 0
            self.poster_art = xbmc.getInfoLabel('Player.Art(poster)') or None

            # For episodes, fetch show details to get show-level IDs
            if item_type == "episode":
                tvshow_id = item.get("tvshowid", -1)
                self.current_show = utils.get_tvshow_details(tvshow_id)

            settings = self._get_settings()

            self._log("Playing: {} [{}]".format(
                item.get("title", "?"),
                item_type
            ))

            # Send "playing" event (async — don't block player callback)
            if settings["track_playing"]:
                api = self._get_api(settings)
                if api:
                    payload = utils.build_payload(
                        "playing", item, self.current_show, progress=0.0
                    )
                    self.playing_sent = True
                    title_display = item.get("title", "")
                    if item_type == "episode":
                        title_display = "{} S{:02d}E{:02d}".format(
                            item.get("showtitle", ""), item.get("season", 0), item.get("episode", 0)
                        )
                    _dispatch_async(
                        api.send_event, payload, debug=settings["debug"]
                    )
                    if settings["notify_playing"]:
                        _notify("Now Playing", title_display)

        except Exception as e:
            self._log("onAVStarted error: {}".format(str(e)), xbmc.LOGERROR)

    def onPlayBackEnded(self):
        """Called when the file finishes playing naturally — always scrobble."""
        self._log("onPlayBackEnded triggered, current_item={}, scrobbled={}".format(
            bool(self.current_item), self.scrobbled))
        try:
            if self.current_item:
                if not self.scrobbled:
                    self._send_scrobble(progress=100.0)
                self._maybe_show_rating(self._get_api(), 100.0)
        except Exception as e:
            self._log("onPlayBackEnded error: {}".format(str(e)), xbmc.LOGERROR)
        finally:
            self._reset_state()

    def onPlayBackPaused(self):
        """Called when the user pauses playback."""
        self._log("onPlayBackPaused triggered")
        try:
            if self.current_item and not self.scrobbled:
                progress = self._get_progress()
                self.last_progress = progress
                self._send_paused(progress)
        except Exception as e:
            self._log("onPlayBackPaused error: {}".format(str(e)), xbmc.LOGERROR)

    def onPlayBackResumed(self):
        """Called when playback resumes from pause."""
        self._log("onPlayBackResumed triggered")
        try:
            if self.current_item and not self.scrobbled:
                settings = self._get_settings()
                if settings["track_playing"]:
                    api = self._get_api(settings)
                    if api:
                        progress = self._get_progress()
                        payload = utils.build_payload(
                            "playing", self.current_item, self.current_show,
                            progress=progress
                        )
                        _dispatch_async(
                            api.send_event, payload, debug=settings["debug"]
                        )
        except Exception as e:
            self._log("onPlayBackResumed error: {}".format(str(e)), xbmc.LOGERROR)

    def onPlayBackStopped(self):
        """Called when the user stops playback."""
        self._log("onPlayBackStopped triggered, current_item={}, scrobbled={}, last_progress={:.1f}".format(
            bool(self.current_item), self.scrobbled, getattr(self, 'last_progress', 0)))
        try:
            if self.current_item:
                progress = getattr(self, 'last_progress', 0) or self._get_progress()
                settings = self._get_settings()

                if progress >= settings["threshold"]:
                    # Watched — scrobble + rating
                    if not self.scrobbled:
                        self._send_scrobble(progress=progress)
                    self._maybe_show_rating(self._get_api(), progress)
                else:
                    # Paused — send paused event
                    self._send_paused(progress)
        except Exception as e:
            self._log("onPlayBackStopped error: {}".format(str(e)), xbmc.LOGERROR)
        finally:
            self._reset_state()

    # -----------------------------------------------------------------
    # Progress tracking (called from main service loop)
    # -----------------------------------------------------------------

    def check_progress(self):
        """
        Check playback progress, send periodic 'playing' updates,
        and scrobble if threshold is reached.
        Called every 30s from the service.py main loop.
        """
        if not self.current_item or self.scrobbled:
            return

        try:
            if not self.isPlayingVideo():
                return

            progress = self._get_progress()
            self.last_progress = progress
            settings = self._get_settings()

            # Send "playing" update with current progress every 30s (async)
            if settings["track_playing"]:
                api = self._get_api(settings)
                if api:
                    payload = utils.build_payload(
                        "playing", self.current_item, self.current_show,
                        progress=progress
                    )
                    _dispatch_async(
                        api.send_event, payload, debug=settings["debug"]
                    )
                    self._log("Playing update dispatched: {:.1f}%".format(progress))

            # Scrobble once threshold is reached
            if progress >= settings["threshold"] and settings["track_watched"]:
                self._send_scrobble(progress=progress)

        except Exception:
            pass

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _get_item_from_info_tag(self, base_item):
        """Fallback: extract metadata from xbmc.Player.getVideoInfoTag()."""
        try:
            tag = self.getVideoInfoTag()
            if not tag:
                return base_item

            media_type = tag.getMediaType() or ""
            self._log("InfoTag mediaType: {}, title: {}, dbid: {}".format(
                media_type, tag.getTitle(), tag.getDbId()))

            item = dict(base_item)
            item["title"] = tag.getTitle() or item.get("title", "")
            item["year"] = tag.getYear() or item.get("year", 0)

            if media_type == "movie":
                item["type"] = "movie"
                item["uniqueid"] = {}
                imdb = tag.getIMDBNumber()
                if imdb and imdb.startswith("tt"):
                    item["uniqueid"]["imdb"] = imdb
                elif imdb:
                    item["uniqueid"]["tmdb"] = imdb
                item["imdbnumber"] = imdb or ""
            elif media_type == "episode":
                item["type"] = "episode"
                item["season"] = tag.getSeason()
                item["episode"] = tag.getEpisode()
                item["showtitle"] = tag.getTVShowTitle() or ""
                item["tvshowid"] = tag.getDbId()  # may not be show id
                item["uniqueid"] = {}
                imdb = tag.getIMDBNumber()
                if imdb:
                    item["imdbnumber"] = imdb
            elif tag.getTitle():
                # Has title but unknown type — try to infer
                if tag.getEpisode() > 0:
                    item["type"] = "episode"
                    item["season"] = tag.getSeason()
                    item["episode"] = tag.getEpisode()
                    item["showtitle"] = tag.getTVShowTitle() or ""
                elif tag.getDbId() > 0:
                    item["type"] = "movie"
                item["uniqueid"] = {}
                imdb = tag.getIMDBNumber()
                if imdb:
                    item["imdbnumber"] = imdb

            return item
        except Exception as e:
            self._log("InfoTag fallback error: {}".format(str(e)), xbmc.LOGWARNING)
            return base_item

    def _maybe_show_rating(self, api, progress):
        """Show rating dialog if enabled and threshold met."""
        try:
            if not rating_mod.should_show_rating(self.media_type, progress):
                return

            item = self.current_item
            title = item.get("title", "Unknown")
            year = item.get("year")
            ids = utils.extract_ids(item)

            rating_value = rating_mod.show_rating_dialog(title, year, poster_path=self.poster_art)
            if rating_value is None:
                return

            # Send rating to API (async — keep UI responsive)
            if self.media_type == "episode":
                show_ids = utils.extract_ids(self.current_show) if self.current_show else {}
                _dispatch_async(
                    api.send_rating,
                    "episode", title, ids, rating_value,
                    show_title=item.get("showtitle", ""),
                    show_ids=show_ids,
                    season=item.get("season", 0),
                    episode=item.get("episode", 0)
                )
            else:
                _dispatch_async(
                    api.send_rating, "movie", title, ids, rating_value, year=year
                )

            _notify("WeTrakr", "Rated {}/10".format(rating_value))
        except Exception as e:
            self._log("Rating error: {}".format(str(e)), xbmc.LOGWARNING)

    def _get_progress(self):
        """Calculate playback progress as a percentage (0-100)."""
        try:
            if not self.isPlayingVideo():
                return 0.0
            current = self.getTime()
            total = self.total_time or self.getTotalTime()
            if total <= 0:
                return 0.0
            return min((current / total) * 100.0, 100.0)
        except Exception:
            return 0.0

    def _send_paused(self, progress=0.0):
        """Send a 'paused' event to WeTrakr (fire-and-forget)."""
        settings = self._get_settings()
        api = self._get_api(settings)
        if not api:
            return

        payload = utils.build_payload(
            "paused", self.current_item, self.current_show, progress=progress
        )

        title = self.current_item.get("title", "Unknown")
        if self.media_type == "episode":
            show = self.current_item.get("showtitle", "")
            season = self.current_item.get("season", 0)
            episode = self.current_item.get("episode", 0)
            title = "{} S{:02d}E{:02d}".format(show, season, episode)

        _dispatch_async(api.send_event, payload, debug=settings["debug"])
        self._log("Paused dispatched: {} ({:.0f}%)".format(title, progress))
        if settings["notify_paused"]:
            _notify("Paused", "{} ({:.0f}%)".format(title, progress))

    def _send_scrobble(self, progress=0.0):
        """
        Send a 'scrobble' event to WeTrakr (fire-and-forget).

        We mark ``self.scrobbled = True`` *before* dispatching so the player
        callback returns immediately and we never double-scrobble if a second
        callback fires while the HTTP request is still in flight. If the
        request ultimately fails, that's logged from the background thread.
        """
        settings = self._get_settings()

        if not settings["track_watched"]:
            return

        api = self._get_api(settings)
        if not api:
            self._log("Cannot scrobble: no API token configured", xbmc.LOGWARNING)
            return

        payload = utils.build_payload(
            "scrobble", self.current_item, self.current_show, progress=progress
        )

        title = self.current_item.get("title", "Unknown")
        if self.media_type == "episode":
            show = self.current_item.get("showtitle", "")
            season = self.current_item.get("season", 0)
            episode = self.current_item.get("episode", 0)
            title = "{} S{:02d}E{:02d}".format(show, season, episode)

        self.scrobbled = True

        def _send():
            ok = api.send_event(payload, debug=settings["debug"])
            if ok:
                self._log("Scrobbled: {} ({:.0f}%)".format(title, progress))
            else:
                self._log("Scrobble failed: {}".format(title), xbmc.LOGWARNING)

        _dispatch_async(_send)
        if settings["notify_scrobble"]:
            _notify("WeTrakr", "Scrobbled: {}".format(title))

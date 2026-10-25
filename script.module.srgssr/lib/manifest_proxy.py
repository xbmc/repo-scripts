# Copyright (C) 2018 Alexander Seiler
#
#
# This file is part of script.module.srgssr.
#
# script.module.srgssr is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# script.module.srgssr is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with script.module.srgssr.
# If not, see <http://www.gnu.org/licenses/>.

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Safety net only, in case wait_until_playback_stops() never runs (e.g. crash).
IDLE_TIMEOUT_SECONDS = 3 * 60 * 60
WATCHDOG_INTERVAL_SECONDS = 30
STARTUP_TIMEOUT_SECONDS = 60


class ManifestProxyServer:
    """Serves a locally-filtered DASH manifest, re-fetching it on every
    request.

    This keeps the manifest live-updated for the whole playback session, and
    ties its own lifetime to actual playback (stopped/ended/error) instead of a
    fixed timer.

    Kodi stops delivering xbmc.Player callbacks once the invoking plugin
    script exits, which normally happens right after resolving the URL. So
    the caller must block in wait_until_playback_stops() to keep the script
    (and this server) alive for as long as the stream plays.
    """

    def __init__(self, refresh, initial_xml, logger=None):
        """
        refresh     -- callable() -> bytes or None; None means "fetch failed",
                       keep serving the last good manifest.
        initial_xml -- bytes, the manifest already fetched once by the caller.
        logger      -- optional callable(str) for diagnostic logging.
        """
        self._refresh = refresh
        self._log = logger or (lambda msg: None)
        self._lock = threading.Lock()
        self._xml = initial_xml
        self._last_request = time.monotonic()
        self._stopped = threading.Event()

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def _send_headers(self, length):
                self.send_response(200)
                self.send_header("Content-type", "application/dash+xml")
                self.send_header("Content-Length", str(length))
                self.end_headers()

            def do_HEAD(self):
                with outer._lock:
                    body = outer._xml
                self._send_headers(len(body))

            def do_GET(self):
                with outer._lock:
                    outer._last_request = time.monotonic()
                fresh = outer._safe_refresh()
                with outer._lock:
                    if fresh is not None:
                        outer._xml = fresh
                    body = outer._xml
                self._send_headers(len(body))
                self.wfile.write(body)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_port

        threading.Thread(target=self._run_server, daemon=True).start()
        threading.Thread(target=self._watchdog, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}/manifest.mpd"

    def _safe_refresh(self):
        try:
            return self._refresh()
        except Exception as e:
            self._log(f"ManifestProxyServer: refresh failed: {e}")
            return None

    def _run_server(self):
        try:
            self._server.serve_forever(poll_interval=0.5)
        finally:
            self._server.server_close()

    def _watchdog(self):
        while not self._stopped.wait(WATCHDOG_INTERVAL_SECONDS):
            with self._lock:
                idle = time.monotonic() - self._last_request
            if idle > IDLE_TIMEOUT_SECONDS:
                self._log("ManifestProxyServer: idle timeout reached, shutting down")
                self.stop()
                break

    def stop(self):
        if self._stopped.is_set():
            return
        self._stopped.set()
        self._server.shutdown()

    def wait_until_playback_stops(self, player, poll_interval=1.0):
        """Blocks the calling (plugin script) thread until `player` is no
        longer playing our manifest URL, then stops the server.

        Must be called from the plugin script's own thread -- that's the
        only thread Kodi keeps delivering playback state to after
        setResolvedUrl().
        """
        # Wait for playback to start, giving up if it never does.
        start = time.monotonic()
        while not self._stopped.is_set():
            if player.isPlayingVideo() and player.getPlayingFile() == self.url:
                break
            if time.monotonic() - start > STARTUP_TIMEOUT_SECONDS:
                self._log(
                    "ManifestProxyServer: playback never started, " "shutting down"
                )
                self.stop()
                return
            if self._stopped.wait(poll_interval):
                return

        while not self._stopped.is_set():
            if not (player.isPlayingVideo() and player.getPlayingFile() == self.url):
                break
            if self._stopped.wait(poll_interval):
                return

        self.stop()

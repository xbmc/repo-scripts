# -*- coding: utf-8 -*-
import socket
import threading

import requests
from bottle import request, response

from resources.lib.kodi import kodilogging
from resources.lib.kodi.utils import get_device_id, get_setting_as_bool
from resources.lib.tubecast.utils import PY3
from resources.lib.tubecast.youtube import kodibrigde
from resources.lib.tubecast.youtube.player import CastPlayer, STATUS_LOADING, STATUS_STOPPED
from resources.lib.tubecast.youtube.templates import YoutubeTemplates
from resources.lib.tubecast.youtube.utils import CommandParser
from resources.lib.tubecast.youtube.volume import VolumeMonitor

if PY3:
    from urllib.parse import urlencode
else:
    from urllib import urlencode

import xbmc

logger = kodilogging.get_logger()
monitor = xbmc.Monitor()
templates = YoutubeTemplates()

MAX_SEND_RETRIES = 3


class CastState(object):
    def __init__(self):
        self.ctt = None  # type: Optional[str]

        self.playlist_id = None  # type: Optional[str]
        self.playlist = None  # type: List[str]
        self.playlist_index = None  # type: Optional[int]

    @property
    def video_id(self):  # type: () -> Optional[str]
        if not self.has_playlist:
            return None

        return self.playlist[self.playlist_index]

    @property
    def has_playlist(self):  # type: () -> bool
        return bool(self.playlist)

    def handle_set_playlist(self, data):
        if 'ctt' in data:
            self.ctt = data["ctt"]

        self.playlist_id = data["listId"]
        self.playlist = data["videoIds"].split(",")
        self.playlist_index = int(data["currentIndex"])

    def handle_update_playlist(self, data):
        video_ids = data.get("videoIds")
        if not video_ids:
            self.playlist = None
            self.playlist_index = None
            return

        self.playlist = video_ids.split(",")
        if self.playlist_index is not None and self.playlist_index >= len(self.playlist):
            self.playlist_index = len(self.playlist) - 1

    def _change_playlist_index(self, change):  # type: (int) -> bool
        if not self.has_playlist:
            return False

        next_index = self.playlist_index + change
        if not 0 <= next_index < len(self.playlist):
            return False

        self.playlist_index = next_index
        return True

    def playlist_next(self):  # type: () -> bool
        """Advance to the next video in the playlist.

        Returns:
            Whether the operation succeeded.
            `False` if there is no playlist or we're on the last video.
        """
        return self._change_playlist_index(1)

    def playlist_prev(self):  # type: () -> bool
        """Go to the previous video in the playlist.

        Returns:
            Whether the operation succeeded.
            `False` if there is no playlist or we're on the first video.
        """
        return self._change_playlist_index(-1)

    def create_state_data(self):  # type: () -> dict
        if not self.has_playlist:
            return {}

        return {"videoId": self.video_id,
                "ctt": self.ctt,
                "listId": self.playlist_id,
                "currentIndex": self.playlist_index}


class YoutubeCastV1(object):

    def __init__(self, dial=None):
        self.base_url = "https://www.youtube.com"
        self.default_screen_name = get_device_id()
        self.default_screen_app = "kodi-tubecast"
        self.screen_uid = "c8277ac4-ke86-4f8b-8fe2-1236bef43397"

        self.session = requests.Session()
        self.player = None  # type: Optional[CastPlayer]
        self.volume_monitor = None  # type: Optional[VolumeMonitor]
        self.listener = None  # type: Optional[YoutubeListener]

        # Set initial state
        self._initial_app_state()

        # Register routes in the dial server if service discovery is being used
        if dial:
            self._setup_routes(dial)

    def _initial_app_state(self):
        self.current_index = None
        self.screen_id = None
        self.lounge_token = None
        self.ofs = 0
        self.has_client = False
        self.__replace_listener(None)
        self.connected_client = None
        # Hold references to the index of received codes
        self.code = -1
        # Get service announcement data
        self.bind_vals = templates.announcement(self.screen_uid, self.default_screen_name, self.default_screen_app)

        self.state = CastState()

    def __replace_listener(self, listener):  # type: (Optional[YoutubeListener]) -> None
        """Replace the current listener with a new one.

        Takes care of stopping the previous listener in case there already is one.
        """
        if self.listener is not None:
            self.listener.force_stop()

        self.listener = listener
        if listener is not None:
            listener.start()

    def _setup_routes(self, dial):
        dial.route('/apps/YouTube', 'GET', self._state_listener)
        dial.route('/apps/YouTube', 'POST', self._register_listener)
        dial.route('/apps/YouTube/web-1', 'DELETE', self._remove_listener)

    def _state_listener(self):
        response.set_header('Content-Type', 'application/xml')
        response.set_header('Access-Control-Allow-Method', 'GET, POST, DELETE, OPTIONS')
        response.set_header('Access-Control-Expose-Headers', 'Location')
        response.set_header('Cache-control', 'no-cache, must-revalidate, no-store')
        return templates.not_connected if not self.has_client else templates.connected

    def _register_listener(self):
        self.has_client = True
        pairing_code = request.forms.get("pairingCode")
        self._pair(pairing_code)
        response.status = 201
        return ""

    def _remove_listener(self):
        self._initial_app_state()
        response.status = 200
        return ""

    def _pair(self, pairing_code):
        """ called as part of service discovery """
        self._generate_screen_id()
        self._get_lounge_token_batch()
        self._bind()
        self._register_pairing_code(pairing_code)
        # Listen to remote youtube server
        self.__replace_listener(YoutubeListener(app=self, ssdp=True))

    def pair(self):
        """ called from external pairing_code generation script """
        self._generate_screen_id()
        self._get_lounge_token_batch()
        self._bind()
        pairing_code = self._get_pairing_code()
        # Listen to remote youtube server
        self.__replace_listener(YoutubeListener(app=self, ssdp=False))
        return pairing_code

    def _generate_screen_id(self):
        screen_id = self.session.get(
            "{}/api/lounge/pairing/generate_screen_id".format(self.base_url),
            verify=get_setting_as_bool("verify-ssl")
        )
        self.screen_id = screen_id.text
        logger.debug("Screen ID is: {}".format(self.screen_id))
        return self.screen_id

    def _get_lounge_token_batch(self):
        token_info = self.session.post(
            "{}/api/lounge/pairing/get_lounge_token_batch".format(self.base_url),
            data={"screen_ids": self.screen_id},
            verify=get_setting_as_bool("verify-ssl")
        ).json()
        self.lounge_token = token_info["screens"][0]["loungeToken"]
        logger.debug("Lounge Token: {}".format(self.lounge_token))
        self.bind_vals["loungeIdToken"] = self.lounge_token
        return self.lounge_token

    def _bind(self):
        self.ofs += 1
        bind_vals = self.bind_vals
        bind_vals["CVER"] = "1"
        bind_info = self.session.post(
            "{}/api/lounge/bc/bind?{}".format(self.base_url, urlencode(bind_vals)),
            data={"count": "0"},
            verify=get_setting_as_bool("verify-ssl")
        ).text
        for cmd in CommandParser(bind_info):
            self.handle_cmd(cmd)

    def _register_pairing_code(self, pairing_code):  # type: (str) -> None
        r = self.session.post(
            "{}/api/lounge/pairing/register_pairing_code".format(self.base_url),
            data={
                "access_type": "permanent",
                "app": self.default_screen_app,
                "pairing_code": pairing_code,
                "screen_id": self.screen_id,
                "screen_name": self.default_screen_name
            },
            verify=get_setting_as_bool("verify-ssl")
        )
        logger.debug("Registered pairing code status code: {}".format(r.status_code))

    def _get_pairing_code(self):
        r = self.session.post(
            "{}/api/lounge/pairing/get_pairing_code?ctx=pair".format(self.base_url),
            data={
                "access_type": "permanent",
                "app": self.default_screen_app,
                "lounge_token": self.lounge_token,
                "screen_id": self.screen_id,
                "screen_name": self.default_screen_name
            },
            verify=get_setting_as_bool("verify-ssl")
        )
        return "{}-{}-{}-{}".format(r.text[0:3], r.text[3:6], r.text[6:9], r.text[9:12])

    def handle_cmd(self, cmd):  # type: (Command) -> None
        debug_cmds = get_setting_as_bool('debug-cmd')

        if debug_cmds:
            logger.debug("CMD: %s", cmd)

        code, name, data = cmd

        if code <= self.code:
            if debug_cmds:
                logger.debug("Command ignored, already executed before")
            return

        self.code = code

        if name == "c":
            logger.debug("C cmd received")
            self.bind_vals["SID"] = data[0]

        elif name == "S":
            logger.debug("Session established received")
            self.bind_vals["gsessionid"] = data

        elif name == "remoteConnected":
            logger.info("Remote connected: {}".format(data))
            if not self.player:
                # Start "player" thread
                threading.Thread(name="Player",
                                 target=self.__player_thread).start()
            # Start a new volume_monitor if not yet available
            if not self.volume_monitor:
                self.volume_monitor = VolumeMonitor(self)
                self.volume_monitor.start()

            # Disable automatic playback from youtube (this is kodi not youtube :))
            # TODO: see issue #15
            self._disable_autoplay()
            # Check if it is a new association
            if self.connected_client != data:
                self.connected_client = data
                kodibrigde.remote_connected(data["name"])

        elif name == "remoteDisconnected":
            logger.info("Remote disconnected: {}".format(data))
            self._initial_app_state()
            kodibrigde.remote_disconnected(data["name"])

        elif name == "getNowPlaying":
            logger.debug("getNowPlaying received")
            self.report_now_playing()

        elif name == "setPlaylist":
            logger.debug("setPlaylist: {}".format(data))
            self.state.handle_set_playlist(data)
            play_url = kodibrigde.get_youtube_plugin_path(self.state.video_id, seek=data.get("currentTime", 0))
            self.player.play_from_youtube(play_url)

        elif name == "updatePlaylist":
            logger.debug("updatePlaylist: {}".format(data))
            self.state.handle_update_playlist(data)
            if not self.state.has_playlist and self.player.isPlaying():
                self.player.stop()

        elif name == "next":
            logger.debug("Next received")
            self._next()

        elif name == "previous":
            logger.debug("Previous received")
            self._previous()

        elif name == "pause":
            logger.debug("Pause received")
            self._pause()

        elif name == "stopVideo":
            logger.debug("stopVideo received")
            if self.player.isPlaying():
                self.player.stop()

        elif name == "seekTo":
            logger.debug("seekTo: {}".format(data))
            self._seek(int(data["newTime"]))

        elif name == "getVolume":
            logger.debug("getVolume received")
            volume = kodibrigde.get_kodi_volume()
            self.report_volume(volume)

        elif name == "setVolume":
            logger.debug("setVolume: {}".format(data))
            new_volume = data["volume"]
            # Set volume only if it differs from current volume
            if new_volume != kodibrigde.get_kodi_volume():
                self._set_volume(new_volume)

        elif name == "play":
            logger.debug("play received")
            self._resume()

        elif debug_cmds:
            logger.debug("unhandled command: %r", name)

    def _resume(self):
        is_playing = self.player.isPlaying()
        if is_playing and not self.player.playing:
            # Toggle playback to resume
            self.player.pause()
        elif not is_playing and self.state.has_playlist:
            # Start playing after player has been stopped
            self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(self.state.video_id))

    def _seek(self, time_seek):  # type: (int) -> None
        if self.player.isPlaying():
            # Inform the app that we're loading.
            self.report_state_change(STATUS_LOADING, time_seek, self.player.getTotalTime())
            self.player.seekTime(time_seek)

    def _pause(self):
        if self.player.playing:
            self.player.pause()

    def _previous(self):
        if not self.state.playlist_prev():
            return

        self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(self.state.video_id))

    def _next(self):
        if not self.state.playlist_next():
            return

        self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(self.state.video_id))

    def _disable_autoplay(self):
        self.__post_bind("onAutoplayModeChanged", {"autoplayMode": "DISABLED"})

    def _set_volume(self, volume):
        kodibrigde.set_kodi_volume(int(volume))
        self.report_volume(volume)

    def report_now_playing(self):
        logger.debug("Report now playing")
        data = self.state.create_state_data()

        if self.player and self.player.isPlaying():
            data.update(currentTime=str(int(self.player.getTime())), state=str(self.player.status_code))

        self.__post_bind("nowPlaying", data)

    def report_playback_stopped(self):
        logger.debug("Report playback stopped")
        self.report_state_change(STATUS_STOPPED, 0, 0)

    def report_playback_ended(self):
        logger.debug("Report playback ended")
        self.report_state_change(STATUS_STOPPED, 0, 0)
        if self.state.playlist_next():
            self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(self.state.video_id))
        else:
            self.report_now_playing()

    def report_volume(self, volume):  # type: (int) -> None
        logger.debug("Report volume")
        self.__post_bind("onVolumeChanged", {"volume": str(volume), "muted": "false"})

    def report_state_change(self, status_code, current_time, duration):  # type: (int, int, int) -> None
        self.__post_bind("onStateChange",
                         {"currentTime": str(current_time),
                          "state": str(status_code),
                          "duration": str(duration),
                          "cpn": "foo"})

    def __post_bind(self, sc, postdata):  # type: (str, dict) -> None
        self.ofs += 1
        post_data = {"count": "1", "ofs": str(self.ofs), "req0__sc": sc}
        for key in list(postdata.keys()):
            post_data["req0_" + key] = postdata[key]

        if get_setting_as_bool("debug-http"):
            logger.debug("POST %s:\n%r", sc, post_data)

        bind_vals = self.bind_vals
        bind_vals["RID"] = "1337"
        url = "{}/api/lounge/bc/bind?{}".format(self.base_url, urlencode(bind_vals))
        verify_ssl = get_setting_as_bool("verify-ssl")

        last_exc = None
        for i in range(MAX_SEND_RETRIES):
            try:
                self.session.post(url, data=post_data, verify=verify_ssl)
            except requests.ConnectionError as e:
                logger.info("failed to send data on attempt %s/%s", i + 1, MAX_SEND_RETRIES)
                last_exc = e
                continue
            except Exception:
                logger.exception("error sending %s", sc)
                break
            else:
                # request successful
                break
        else:
            # MAX_SEND_RETRIES exceeded
            logger.exception("failed to send data to client", exc_info=last_exc)

    def __player_thread(self):
        self.player = CastPlayer(cast=self)
        while not monitor.abortRequested() and self.has_client:
            monitor.waitForAbort(1)

        self.player = None
        # Stop listener if present
        if self.listener:
            self.listener.force_stop()
            self.listener.join()


class YoutubeListener(threading.Thread):

    def __init__(self, app, ssdp=True):
        super(YoutubeListener, self).__init__(name="YoutubeListener")
        self.app = app  # type: YoutubeCastV1
        self.stop = False
        self.ssdp = ssdp
        self.r = None  # type: Optional[requests.Response]

    def __read_cmd_chunks(self, url):  # type: (str) -> Iterator[str]
        with self.app.session.get(url, stream=True) as self.r:
            try:
                for line in self.r.iter_content(chunk_size=None):
                    if self.stop:
                        break

                    yield line
            except requests.exceptions.ChunkedEncodingError:
                # raised when we forcefully close the socket.
                # If we don't want to stop though, this should raise.
                if not self.stop:
                    raise

    def _listen(self):
        logger.debug("Listening to youtube remote events...")
        self.app.ofs += 1
        bind_vals = self.app.bind_vals.copy()
        bind_vals["RID"] = "rpc"
        bind_vals["CI"] = "0"
        bind_vals["TYPE"] = "xmlhttp"
        bind_vals["AID"] = "3"
        url = "{}/api/lounge/bc/bind?{}".format(self.app.base_url, urlencode(bind_vals))

        debug_http = get_setting_as_bool("debug-http")

        parser = CommandParser()
        for chunk in self.__read_cmd_chunks(url):
            if debug_http:
                logger.debug("received chunk %r", chunk)

            parser.write(chunk.decode("utf-8") if PY3 else chunk)
            for cmd in parser.get_commands():
                self.app.handle_cmd(cmd)

    def run(self):
        while not self.stop and (not self.ssdp or self.app.has_client):
            try:
                self._listen()
            except Exception:
                logger.exception("error while listening")

    def force_stop(self):
        self.stop = True

        if self.r and not self.r.raw.closed:
            # Close the underlying socket to kill the ongoing request.
            sock = socket.fromfd(self.r.raw.fileno(), socket.AF_INET, socket.SOCK_STREAM)
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            # request cleanup is handled by __read_cmd_lines

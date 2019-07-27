# -*- coding: utf-8 -*-
import re
import threading

import urllib

from bottle import request, response

import requests

from resources.lib.kodi import kodilogging
from resources.lib.kodi.utils import get_device_id, get_setting_as_bool
from resources.lib.tubecast.youtube import kodibrigde
from resources.lib.tubecast.youtube.player import CastPlayer
from resources.lib.tubecast.youtube.templates import YoutubeTemplates
from resources.lib.tubecast.youtube.utils import case, parse_cmd
from resources.lib.tubecast.youtube.volume import VolumeMonitor


import xbmc


logger = kodilogging.get_logger()
monitor = xbmc.Monitor()
templates = YoutubeTemplates()


class YoutubeCastV1(object):

    def __init__(self, dial=None):
        self.base_url = "https://www.youtube.com"
        self.default_screen_name = get_device_id()
        self.default_screen_app = "kodi-tubecast"
        self.screen_uid = "c8277ac4-ke86-4f8b-8fe2-1236bef43397"
        self.pairing_code = None
        self.player = None
        self.bind_vals = None

        # Set initial state
        self._initial_app_state()

        # Register routes in the dial server if service discovery is being used
        if dial:
            self._setup_routes(dial)

    def _initial_app_state(self):
        self.session = requests.Session()
        self.ctt = None
        self.cur_list_id = None
        self.cur_video = None
        self.current_index = None
        self.list_info = None
        self.play_state = 0
        self.screen_id = None
        self.lounge_token = None
        self.session_id = None
        self.sid = None
        self.ofs = 0
        self.has_client = False
        self.volume_monitor = None
        self.listener = None
        self.connected_client = None
        # Hold references to the index of received codes
        self.code = -1
        # Get service announcement data
        self.bind_vals = templates.announcement(self.screen_uid, self.default_screen_name, self.default_screen_app)

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
        ''' called as part of service discovery '''
        self.pairing_code = pairing_code
        self._generate_screen_id()
        self._get_lounge_token_batch()
        self._bind()
        self._register_pairing_code()
        # Listen to remote youtube server
        self.listener = YoutubeListener(app=self, ssdp=True)
        self.listener.start()

    def pair(self):
        ''' called from external pairing_code generation script '''
        self._generate_screen_id()
        self._get_lounge_token_batch()
        self._bind()
        self.pairing_code = self._get_pairing_code()
        # Listen to remote youtube server
        self.listener = YoutubeListener(app=self, ssdp=False)
        self.listener.start()
        return self.pairing_code

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
            "{}/api/lounge/bc/bind?{}".format(self.base_url, urllib.urlencode(bind_vals)),
            data={"count": "0"},
            verify=get_setting_as_bool("verify-ssl")
        ).text
        for line in bind_info.split("\n"):
            self.handle_cmd(str(line))

    def _register_pairing_code(self):
        r = self.session.post(
            "{}/api/lounge/pairing/register_pairing_code".format(self.base_url),
            data={
                "access_type": "permanent",
                "app": self.default_screen_app,
                "pairing_code": self.pairing_code,
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

    def handle_cmd(self, cmd):
        if get_setting_as_bool('debug-cmd'):
            logger.debug("CMD: {}".format(cmd))

        if case("c", cmd):
            logger.debug("C cmd received")
            self.sid = re.findall('"c","(.+?)"', cmd)[0]
            self.bind_vals["SID"] = self.sid

        elif case("S", cmd):
            logger.debug("Session established received")
            self.session_id = re.findall('"S","(.+?)"', cmd)[0]
            self.bind_vals["gsessionid"] = self.session_id

        elif case("remoteConnected", cmd):
            # Parse data
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.info("Remote connected: {}".format(data))
                self.has_client = True
                if not self.player:
                    # Start "player" thread
                    threading.Thread(target=self.__player_thread).start()
                # Start a new volume_monitor if not yet available
                if not self.volume_monitor:
                    threading.Thread(target=self.__monitor_volume).start()
                # Disable automatic playback from youtube (this is kodi not youtube :))
                self._set_disabled()
                # Check if it is a new association
                if not self.connected_client or self.connected_client != data:
                    self.connected_client = data
                    kodibrigde.remote_connected(data["name"])
            else:
                logger.debug("Command ignored, already executed before")

        elif case("remoteDisconnected", cmd):
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.info("Remote disconnected: {}".format(data))
                self._initial_app_state()
                kodibrigde.remote_disconnected(data["name"])
                # Kill player if exists
                if self.player and self.player.isPlaying:
                    self._ready()
            else:
                logger.debug("Command ignored, already executed before")

        elif case("getNowPlaying", cmd):
            logger.debug("getNowPlaying received")
            self._ready()

        elif case("setPlaylist", cmd):
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.debug("setPlaylist: {}".format(data))
                cur_video_id = data["videoId"]
                video_ids = data["videoIds"]
                if 'ctt' in data:
                    self.ctt = data["ctt"]
                self.cur_list_id = data["listId"]
                self.current_index = int(data["currentIndex"])
                self.cur_list = video_ids.split(",")
                # Set info on our custom player instance and request playback
                self.player.setInfo(cur_video_id, self.ctt, self.cur_list_id, self.current_index)
                self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(cur_video_id))
            else:
                logger.debug("Command ignored, already executed before")

        elif case("updatePlaylist", cmd):
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.debug("updatePlaylist: {}".format(data))
                if "videoIds" in list(data.keys()):
                    self.cur_list = data["videoIds"].split(",")
                    if self.current_index >= len(self.cur_list):
                        self.current_index -= 1
                else:
                    self.cur_list = []
                    self.current_index = 0
                    # Check if kodi is playing and if so request stop
                    if self.player.playing:
                        self.player.stop()
            else:
                logger.debug("Command ignored, already executed before")

        elif case("next", cmd):
            logger.debug("Next received")
            if self.current_index + 1 < len(self.cur_list):
                self._next()

        elif case("previous", cmd):
            logger.debug("Previous received")
            if self.current_index > 0:
                self._previous()

        elif case("pause", cmd):
            logger.debug("Pause received")
            self._pause()

        elif case("stopVideo", cmd):
            logger.debug("stopVideo received")
            if self.player and self.player.playing:
                self._ready()

        elif case("seekTo", cmd):
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.debug("seekTo: {}".format(data))
                time_seek = data["newTime"]
                self._seek(time_seek)
            else:
                logger.debug("Command ignored, already executed before")

        elif case("getVolume", cmd):
            logger.debug("getVolume received")
            self._get_volume()

        elif case("setVolume", cmd):
            code, data = parse_cmd(cmd)
            if code > self.code:
                self.code = code
                logger.debug("setVolume: {}".format(data))
                new_volume = data["volume"]
                # Set volume only if it differs from current volume
                if new_volume != kodibrigde.get_kodi_volume():
                    self._set_volume(new_volume)
            else:
                logger.debug("Command ignored, already executed before")

        elif case("play", cmd):
            logger.debug("play received")
            self.play_state = 1
            self._resume()

    def _resume(self):
        if not self.player.playing and self.player.isPlaying():
            # Resume playback
            self.player.pause()

    def _seek(self, time_seek):
        if self.player.playing and self.player.isPlaying():
            self.player.seekTime(int(time_seek))

    def _pause(self):
        if self.player.playing:
            self.player.pause()

    def _previous(self):
        self.current_index -= 1
        cur_video_id = self.cur_list[self.current_index]
        self.player.setInfo(cur_video_id, self.ctt, self.cur_list_id, self.current_index)
        self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(cur_video_id))

    def _next(self):
        self.current_index += 1
        cur_video_id = self.cur_list[self.current_index]
        self.player.setInfo(cur_video_id, self.ctt, self.cur_list_id, self.current_index)
        self.player.play_from_youtube(kodibrigde.get_youtube_plugin_path(cur_video_id))

    def _ready(self):
        threading.Thread(target=self.__post_bind, args=["nowPlaying", {}]).start()

    def pause(self, time, duration):
        self.play_state = 2
        self.__post_bind("onStateChange", {"currentTime": str(time), "state": str(self.play_state), "duration": duration, "cpn": "foo"})

    def _set_disabled(self):
        self.__post_bind("onAutoplayModeChanged", {"autoplayMode": "ENABLED"})

    def report_playback_ended(self):
        # Inform current state (stopped)
        self.__post_bind("onStateChange", {"state": "4", "currentTime": "0", "duration": "0", "cpn": "foo"})
        if self.cur_list and self.current_index and self.current_index + 1 < len(self.cur_list):
            self._next()
        else:
            self._ready()

    def report_playback_started(self, video_id, current_time, ctt, list_id, current_index):
        logger.debug("Report playback started")
        self.__post_bind("nowPlaying", {"videoId": video_id, "currentTime": current_time, "ctt": ctt, "listId": list_id, "currentIndex": int(current_index), "state": "3"})

    def report_playing_time(self, play_state, current_time, duration):
        logger.debug("Report playback current time")
        self.play_state = 1
        self.__post_bind("onStateChange", {"currentTime": str(current_time), "state": str(self.play_state), "duration": str(duration), "cpn": "foo"})

    def _get_volume(self):
        volume = kodibrigde.get_kodi_volume()
        threading.Thread(target=self.__post_bind, args=["onVolumeChanged", {"volume": str(volume), "muted": "false"}]).start()

    def set_volume(self, volume):
        self._get_volume()

    def _set_volume(self, volume):
        kodibrigde.set_kodi_volume(int(volume))
        threading.Thread(target=self.__post_bind, args=["onVolumeChanged", {"volume": str(volume), "muted": "false"}]).start()

    def __post_bind(self, sc, postdata):
        self.ofs += 1
        post_data = {"count": "1", "ofs": str(self.ofs)}
        post_data["req0__sc"] = sc
        for key in list(postdata.keys()):
            post_data["req0_" + key] = postdata[key]

        bind_vals = self.bind_vals
        bind_vals["RID"] = "1337"
        self.session.post(
            "{}/api/lounge/bc/bind?{}".format(
                self.base_url,
                urllib.urlencode(bind_vals)
            ),
            data=post_data,
            verify=get_setting_as_bool("verify-ssl")
        )

    def _get_list_info(self, list_id):
        r = self.session.get(
            "{}/list_ajax?style=json&action_get_list=1&list={}".format(self.base_url, list_id),
            verify=get_setting_as_bool("verify-ssl")
        )
        return r.json()["video"]

    def __player_thread(self):
        self.player = CastPlayer(youtubecastv1=self)
        while not monitor.abortRequested() and self.has_client:
            monitor.waitForAbort(1)
        # Del player
        del self.player
        self.player = None
        # Break listener if present
        if self.listener:
            self.listener.force_stop()

    def __monitor_volume(self):
        self.volume_monitor = VolumeMonitor(self)
        while self.has_client and not self.volume_monitor.abortRequested():
            self.volume_monitor.waitForAbort(1)


class YoutubeListener(threading.Thread):

    def __init__(self, app, ssdp=True):
        threading.Thread.__init__(self)
        self.app = app
        self.stop = False
        self.ssdp = ssdp

    def _listen(self):
        logger.debug("Listening to youtube remote events...")
        self.app.ofs += 1
        bind_vals = self.app.bind_vals
        bind_vals["RID"] = "rpc"
        bind_vals["CI"] = "0"
        bind_vals["TYPE"] = "xmlhttp"
        bind_vals["AID"] = "3"
        with self.app.session.get("{}/api/lounge/bc/bind?{}".format(self.app.base_url,
                                                                    urllib.urlencode(bind_vals)), stream=True) as self.r:
            for line in self.r.iter_lines():
                self.app.handle_cmd(line)
        # Restart youtube data input stream if the client is still connected
        if self.app.has_client and not self.stop:
            self._listen()

    def run(self):
        if not self.ssdp or (self.app.has_client and not self.stop):
            self._listen()

    def force_stop(self):
        self.r.raw._fp.close()

# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from copy import deepcopy
from xbmc import Monitor
from api import Api
from playbackmanager import PlaybackManager
from player import UpNextPlayer
from utils import decode_json, get_property, get_setting_bool, log as ulog


class UpNextMonitor(Monitor):
    """Service monitor for Kodi"""

    def __init__(self):
        """Constructor for Monitor"""
        super().__init__()
        self.player = UpNextPlayer()
        self.api = Api()
        self.playback_manager = PlaybackManager()
        self._sleep_state = None
        self._wake_retries = 0
        self._playback_state = None
        self._waiting_for = None

    def log(self, msg, level=1):
        """Log wrapper"""
        ulog(msg, name=self.__class__.__name__, level=level)

    def run(self):  # pylint: disable=too-many-branches
        """Main service loop"""
        self.log('Service started', 0)

        while not self.abortRequested():
            # check every 1 sec
            if self.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break

            self.restore_after_wake()
            if not self.player.is_tracking():
                self._waiting_for = None
                continue

            if bool(get_property('PseudoTVRunning') == 'True'):
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if get_setting_bool('disableNextUp'):
                # Next Up is disabled
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            if self.player.isExternalPlayer():
                self.log('Up Next tracking stopped, external player detected', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            last_file = self.player.get_last_file()
            try:
                current_file = self.player.getPlayingFile()
            except RuntimeError:
                self.wait_for_player('player.getPlayingFile()')
                continue

            if (current_file.startswith((
                    'bluray://', 'dvd://', 'udf://', 'iso9660://', 'cdda://'))
                    or current_file.endswith((
                        '.bdmv', '.iso', '.ifo'))):
                self.log('Up Next tracking stopped, Blu-ray/DVD/CD playing', 2)
                self.player.disable_tracking()
                self.playback_manager.demo.hide()
                continue

            self.remember_playback(current_file)
            if last_file and last_file == current_file:
                # Already processed this playback before
                continue

            try:
                total_time = self.player.getTotalTime()
            except RuntimeError:
                self.wait_for_player('player.getTotalTime()')
                continue

            if total_time == 0:
                self.wait_for_player('playback duration')
                continue

            try:
                play_time = self.player.getTime()
            except RuntimeError:
                self.wait_for_player('player.getTime()')
                continue

            self._waiting_for = None
            notification_time = self.api.notification_time(total_time=total_time)
            if total_time - play_time > notification_time:
                # Media hasn't reach notification time yet, waiting a bit longer...
                continue

            self.player.set_last_file(current_file)
            self.log('Show notification as episode (of length %d secs) ends in %d secs' % (total_time, notification_time), 2)
            self.playback_manager.launch_up_next()
            self.log('Up Next style autoplay succeeded', 2)
            self.player.disable_tracking()
            self.remember_playback()

        self.log('Service stopped', 0)

    def wait_for_player(self, reason):
        if self._waiting_for != reason:
            self.log('Up Next waiting for %s' % reason, 2)
            self.playback_manager.demo.hide()
            self._waiting_for = reason

    def clear_sleep_state(self):
        self._sleep_state = None
        self._wake_retries = 0

    def remember_playback(self, filename=None):
        if filename is None:
            try:
                filename = self.player.getPlayingFile()
            except RuntimeError:
                return
        if (not self._playback_state
                or self._playback_state['filename'] != filename
                or self._playback_state['data'] != self.api.data
                or self._playback_state['encoding'] != self.api.encoding):
            self._playback_state = {'filename': filename, 'data': deepcopy(self.api.data), 'encoding': self.api.encoding}
        self._playback_state.update(last_file=self.player.get_last_file(), tracking=self.player.is_tracking(),
                                    played_in_a_row=self.player.state.played_in_a_row,
                                    current_tv_show_id=self.player.state.current_tv_show_id)

    def remember_for_sleep(self):
        # The queued sleep callback may run after the native player has stopped.
        # System.OnSleep must precede Player.OnStop, which otherwise discards the
        # snapshot so ordinary stops cannot restore stale playback metadata.
        self.clear_sleep_state()
        self._sleep_state = deepcopy(self._playback_state)

    def restore_after_wake(self):
        if not self._sleep_state:
            return
        if not self._wake_retries:
            return
        self._wake_retries -= 1
        try:
            filename = self.player.getPlayingFile()
            ready = bool(filename) and self.player.getTotalTime() > 0
        except RuntimeError:
            ready = False
            filename = None
        if filename and filename != self._sleep_state['filename']:
            self.clear_sleep_state()
            return
        if not ready:
            if not self._wake_retries:
                self.clear_sleep_state()
            return
        saved = self._sleep_state
        if saved['data'] and not self.api.has_addon_data():
            self.api.addon_data_received(saved['data'], encoding=saved['encoding'])
        self.player.state.played_in_a_row = saved['played_in_a_row']
        self.player.state.current_tv_show_id = saved['current_tv_show_id']
        self.player.set_last_file(saved['last_file'])
        if saved['tracking'] or saved['data']:
            self.player.enable_tracking()
        self.clear_sleep_state()
        self.log('Restored playback tracking after wake', 2)

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        """Notification event handler for accepting data from add-ons"""
        if method == 'System.OnSleep':
            self.remember_for_sleep()
            return
        if method == 'System.OnWake':
            self._wake_retries = 30 if self._sleep_state else 0
            return
        if method == 'Player.OnStop':
            self._waiting_for = None
            if not self._sleep_state:
                self._playback_state = None
            return
        if not method.endswith('upnext_data'):  # Method looks like Other.upnext_data
            return

        decoded_data, encoding = decode_json(data)
        if decoded_data is None:
            self.log('Received data from sender %s is not JSON: %s' % (sender, data), 2)
            return

        self.clear_sleep_state()
        self._playback_state = None
        self._waiting_for = None
        self.playback_manager.handle_demo()
        decoded_data.update(id='%s_play_action' % sender.replace('.SIGNAL', ''))
        self.api.addon_data_received(decoded_data, encoding=encoding)
        self.player.enable_tracking()
        self.player.reset_queue()
        self.remember_playback()

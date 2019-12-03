# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
import xbmc
from . import utils
from .api import Api
from .playbackmanager import PlaybackManager
from .player import Player
from .statichelper import from_unicode


class Monitor(xbmc.Monitor):
    ''' Service monitor for Kodi '''

    def __init__(self):
        ''' Constructor for Monitor '''
        self.player = Player()
        self.api = Api()
        self.playback_manager = PlaybackManager()
        xbmc.Monitor.__init__(self)

    def log(self, msg, level=1):
        ''' Log wrapper '''
        utils.log(msg, name=self.__class__.__name__, level=level)

    def run(self):
        ''' Main service loop '''
        self.log('Service started.', 0)

        while not self.abortRequested():
            # check every 1 sec
            if self.waitForAbort(1):
                # Abort was requested while waiting. We should exit
                break

            if not self.player.is_tracking():
                continue

            up_next_disabled = utils.settings('disableNextUp') == 'true'
            if utils.window('PseudoTVRunning') == 'True' or up_next_disabled:
                continue

            last_file = self.player.get_last_file()
            try:
                current_file = self.player.getPlayingFile()
            except RuntimeError as exc:
                if 'not playing any' in str(exc):
                    self.log('No file is playing - stop up next tracking.', 2)
                    self.player.disable_tracking()
                    continue
                raise

            if last_file and last_file == current_file:
                continue

            total_time = self.player.getTotalTime()
            if total_time == 0:
                continue

            play_time = self.player.getTime()
            notification_time = self.api.notification_time()
            if total_time - play_time > int(notification_time):
                continue

            self.player.set_last_file(from_unicode(current_file))
            self.log('Calling autoplayback totaltime - playtime is %s' % (total_time - play_time), 2)
            self.playback_manager.launch_up_next()
            self.log('Up Next style autoplay succeeded.', 2)
            self.player.disable_tracking()

        self.log('Service stopped.', 0)

    def onNotification(self, sender, method, data):  # pylint: disable=invalid-name
        ''' Notification event handler for accepting data from add-ons '''
        if not method.endswith('upnext_data'):  # Method looks like Other.upnext_data
            return

        data, encoding = utils.decode_json(data)
        data.update(id='%s_play_action' % sender.replace('.SIGNAL', ''))
        self.api.addon_data_received(data, encoding=encoding)

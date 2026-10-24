#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
#
# This file is part of Cloud Drive Common Module for Kodi
#
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------
import re
import threading
import urllib

from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils


class PlayerService(object):
    name = 'player'

    def __init__(self, provider_class):
        from clouddrive.common.service.source import SourceService
        self.abort = False
        self._system_monitor = KodiUtils.get_system_monitor()
        self.provider = provider_class()
        self.addonid = KodiUtils.get_addon_info('id')
        self.addon_name = KodiUtils.get_addon_info('name')
        self.url_pattern = 'http.*:%s/%s/%s/.*' % (KodiUtils.get_addon_setting('port_directory_listing'), SourceService.name, urllib.parse.quote(self.addon_name))
        Logger.debug(self.url_pattern)
        self.player = KodiPlayer()
        self.player.set_source_url_matcher(re.compile(self.url_pattern))
        self.player.set_addonid(self.addonid)

    def __del__(self):
        del self._system_monitor

    def start(self):
        Logger.notice('Service \'%s\' started.' % self.name)
        monitor = KodiUtils.get_system_monitor()
        while not self.abort:
            if monitor.waitForAbort(1):
                break
        del monitor
        del self.provider
        Logger.notice('Service stopped.')

    def stop(self):
        self.abort = True

class KodiPlayer(KodiUtils.kodi_player_class()):
    def set_source_url_matcher(self, source_url_matcher):
        self.source_url_matcher = source_url_matcher

    def set_addonid(self, addonid):
        self.addonid = addonid

    def onPlayBackStarted(self):
        if self.isPlaying():
            Logger.debug('playback started: %s' % self.getPlayingFile())
            if self.isPlaying() and KodiUtils.get_addon_setting('set_subtitle') == 'true' and self.source_url_matcher.match(self.getPlayingFile()):
                    t = threading.Thread(target=self.get_subtitles, name='%s-getsubtitles' % threading.current_thread().name, daemon=True)
                    t.start()

    def onPlayBackEnded(self):
        self.player_stopped()

    def onPlayBackStopped(self):
        self.player_stopped()

    def player_stopped(self):
        KodiPlayer.cleanup()

    @staticmethod
    def cleanup():
        KodiUtils.clear_home_property('addonid')
        KodiUtils.clear_home_property('dbid')
        KodiUtils.clear_home_property('dbtype')
        KodiUtils.clear_home_property('playcount')
        KodiUtils.clear_home_property('dbresume_position')
        KodiUtils.clear_home_property('dbresume_total')

    def get_subtitles(self):
        try:
            from clouddrive.common.remote.request import Request
            from clouddrive.common.service.download import DownloadServiceUtil
            response = Request(self.getPlayingFile()+'?subtitles', None).request_json()
            if response and 'driveid' in response and 'subtitles' in response:
                driveid = response['driveid']
                subtitles = response['subtitles']
                for subtitle in subtitles:
                    url = DownloadServiceUtil.build_download_url(driveid, Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid), subtitle['id'], urllib.parse.quote(Utils.str(subtitle['name'])))
                    Logger.debug('subtitle: %s' % url)
                    self.setSubtitles(url)
        except Exception as e:
            Logger.error(e)
            from clouddrive.common.remote.errorreport import ErrorReport
            ErrorReport.handle_exception(e)

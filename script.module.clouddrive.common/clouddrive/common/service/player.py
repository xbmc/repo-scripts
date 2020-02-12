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
import datetime
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
        if KodiUtils.get_info_label('System.BuildVersion').startswith('17.'):
            KodiUtils.set_home_property('iskrypton', 'true')
        self.addon_name = KodiUtils.get_addon_info('name')
        self.url_pattern = 'http.*:%s/%s/%s/.*' % (KodiUtils.get_addon_setting('port_directory_listing'), SourceService.name, urllib.quote(self.addon_name))
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
    def __init__(self, *args):
        self.iskrypton = KodiUtils.get_home_property('iskrypton') == 'true'

    def set_source_url_matcher(self, source_url_matcher):
        self.source_url_matcher = source_url_matcher

    def set_addonid(self, addonid):
        self.addonid = addonid

    def onPlayBackStarted(self):
        Logger.debug('playback started: %s' % self.getPlayingFile())
        if self.isPlaying() and KodiUtils.get_addon_setting('set_subtitle') == 'true' and self.source_url_matcher.match(self.getPlayingFile()):
                t = threading.Thread(target=self.get_subtitles, name='%s-getsubtitles' % threading.current_thread().name)
                t.setDaemon(True)
                t.start()

        if self.isPlaying() and self.iskrypton and KodiUtils.get_addon_setting('save_resume_watched') == 'true':
            dbid = KodiUtils.get_home_property('dbid')
            addonid = KodiUtils.get_home_property('addonid')
            if addonid and addonid == self.addonid and dbid:
                t = threading.Thread(target=self.track_progress, name='%s-trackprogress' % threading.current_thread().name)
                t.setDaemon(True)
                t.start()

    def onPlayBackEnded(self):
        self.player_stopped()

    def onPlayBackStopped(self):
        self.player_stopped()

    def player_stopped(self):
        if self.iskrypton:
            self.saveProgress()
        KodiPlayer.cleanup()

    def saveProgress(self):
        dbid = KodiUtils.get_home_property('dbid')
        addonid = KodiUtils.get_home_property('addonid')
        if addonid and addonid == self.addonid:
            if dbid:
                Logger.debug('ok to save dbid: ' + dbid)
                dbtype = KodiUtils.get_home_property('dbtype')
                position = KodiUtils.get_home_property('dbresume_position')
                total = KodiUtils.get_home_property('dbresume_total')
                if dbtype and position and total:
                    position = float(position)
                    total = float(total)
                    percent = position / total * 100
                    details = {}
                    Logger.debug('position is %d of %d = %d percent' % (position, total, percent))
                    if percent >= 90:
                        position = 0
                        total = 0
                        details['resume'] = {'position': 0, 'total': 0}
                        details['lastplayed'] = KodiUtils.to_db_date_str(datetime.datetime.today())
                        details['playcount'] = int(KodiUtils.get_home_property('playcount')) + 1
                    elif position > 180:
                        details['resume'] = {'position': position, 'total': total}
                    if details:
                        Logger.debug(KodiUtils.save_video_details(dbtype, dbid, details))
                        Logger.debug('details saved to db - %s: %s' % (dbid, Utils.str(details)))

    @staticmethod
    def cleanup():
        KodiUtils.clear_home_property('addonid')
        KodiUtils.clear_home_property('dbid')
        KodiUtils.clear_home_property('dbtype')
        KodiUtils.clear_home_property('playcount')
        KodiUtils.clear_home_property('dbresume_position')
        KodiUtils.clear_home_property('dbresume_total')

    def track_progress(self):
        Logger.debug('tracking progress started...')
        monitor = KodiUtils.get_system_monitor()
        while self.isPlaying():
            KodiUtils.set_home_property('dbresume_position', Utils.str(self.getTime()))
            KodiUtils.set_home_property('dbresume_total', Utils.str(self.getTotalTime()))
            if monitor.waitForAbort(1):
                break
        del monitor
        Logger.debug('tracking progress finished')

    def get_subtitles(self):
        try:
            from clouddrive.common.remote.request import Request
            from clouddrive.common.service.download import DownloadServiceUtil
            response = Request(self.getPlayingFile()+'?subtitles', None).request_json()
            if response and 'driveid' in response and 'subtitles' in response:
                driveid = response['driveid']
                subtitles = response['subtitles']
                for subtitle in subtitles:
                    url = DownloadServiceUtil.build_download_url(driveid, Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid), subtitle['id'], urllib.quote(Utils.str(subtitle['name'])))
                    Logger.debug('subtitle: %s' % url)
                    self.setSubtitles(url)
        except Exception as e:
            Logger.error(e)
            from clouddrive.common.remote.errorreport import ErrorReport
            ErrorReport.handle_exception(e)

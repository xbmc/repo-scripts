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

from clouddrive.common.account import AccountManager
from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.service.base import BaseServerService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from urllib.error import HTTPError


class DownloadService(BaseServerService):
    name = 'download'
    profile_path = Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info('profile')))
    
    def __init__(self, provider_class):
        super(DownloadService, self).__init__(provider_class)
        self._handler = Download
        
    
class Download(BaseHandler):
    def do_GET(self):
        Logger.debug(self.path)
        data = self.path.split('/')
        code = 307
        headers = {}
        content = Utils.get_file_buffer()
        if len(data) > 4 and data[1] == self.server.service.name:
            try:
                driveid = data[2]
                provider = self.server.data()
                account_manager = AccountManager(self.server.service.profile_path)
                provider.configure(account_manager, driveid)
                item = provider.get_item(item_driveid=data[3], item_id=data[4], include_download_info = True)
                headers['location'] = item['download_info']['url']
            except Exception as e:
                httpex = ExceptionUtils.extract_exception(e, HTTPError)
                if httpex:
                    code = httpex.code
                else:
                    code = 500
                
                ErrorReport.handle_exception(e)
                content.write(ExceptionUtils.full_stacktrace(e))
        else:
            code = 404
        self.write_response(code, content=content, headers=headers)
        
class DownloadServiceUtil(object):
    @staticmethod
    def build_download_url(driveid, item_driveid, item_id, name, addonid=None):
        return "http://{host}:{port}/{service}/{driveid}/{item_driveid}/{item_id}/{name}".format(
            host = DownloadService._interface,
            port = KodiUtils.get_service_port(DownloadService.name, addonid),
            service = DownloadService.name,
            driveid = driveid,
            item_driveid = item_driveid, 
            item_id = item_id, 
            name = name
        )

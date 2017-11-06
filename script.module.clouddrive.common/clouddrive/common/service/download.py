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

from urllib2 import HTTPError

from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.service.base import BaseService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.service.rpc import RpcUtil


class DownloadService(BaseService):
    name = 'download'
    
    def __init__(self):
        super(DownloadService, self).__init__()
        self._handler = Download
    
class Download(BaseHandler):
    def do_GET(self):
        Logger.debug(self.path)
        data = self.path.split('/')
        code = 307
        headers = {}
        content = Utils.get_file_buffer()
        if len(data) > 5 and data[1] == self.server.service.name:
            try:
                item = RpcUtil.rpc(data[2], 'get_item', kwargs = {
                    'driveid' : data[3],
                    'item_driveid' : data[4],
                    'item_id' : data[5],
                    'include_download_info' : True
                })
                headers['location'] = item['download_info']['url']
            except Exception as e:
                httpex = ExceptionUtils.extract_exception(e, HTTPError)
                if httpex:
                    code = httpex.code
                else:
                    code = 500
                content.write(ExceptionUtils.full_stacktrace(e))
        else:
            code = 404
        self.write_response(code, content=content, headers=headers)
        
class DownloadServiceUtil(object):
    @staticmethod
    def build_download_url(addonid, driveid, item_driveid, item_id, name):
        return 'http://%s:%s/%s/%s/%s/%s/%s/%s' % (
            DownloadService._interface,
            KodiUtils.get_service_port(DownloadService.name, 'script.module.clouddrive.common'),
            DownloadService.name,
            addonid, driveid, item_driveid, item_id, name
        )

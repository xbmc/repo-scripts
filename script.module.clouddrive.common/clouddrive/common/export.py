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

import json
import os
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
import urllib
from clouddrive.common.remote.request import Request


class ExportManager(object):
    exports = {}
    _export_items_file_format = 'export-%s.items'
    _addon_data_path = None
    _config_file_name = 'exports.cfg'
    _config_path = None
    _strm_extension = '.strm'
    
    def __init__(self, addon_data_path):
        self._addon_data_path = addon_data_path
        self._config_path = os.path.join(addon_data_path, self._config_file_name)
        if not os.path.exists(addon_data_path):
            try:
                os.makedirs(addon_data_path)
            except:
                KodiUtils.get_system_monitor().waitForAbort(3)
                os.makedirs(addon_data_path)

    def load(self):
        self.exports = {}
        if os.path.exists(self._config_path):
            with KodiUtils.lock:
                with open(self._config_path, 'rb') as fo:
                    self.exports = json.loads(fo.read())
        return self.exports
    
    def add_export(self, export):
        self.load()
        self.exports[export['id']] = export
        self.save()
    
    def save(self):
        with KodiUtils.lock:
            with open(self._config_path, 'wb') as fo:
                fo.write(json.dumps(self.exports, sort_keys=True, indent=4))

    def remove_export(self, exportid):
        self.load()
        del self.exports[exportid]
        self.save()
    
    def get_items_info_path(self, exportid):
        return os.path.join(self._addon_data_path, self._export_items_file_format % exportid)
    
    def get_items_info(self, exportid):
        items_info = None
        items_info_path = self.get_items_info_path(exportid)
        if KodiUtils.file_exists(items_info_path):
            with KodiUtils.lock:
                with open(items_info_path, 'rb') as fo:
                    items_info = eval(fo.read())
        return items_info
    
    @staticmethod
    def add_item_info(items_info, item_id, name, full_local_path, parent):
        items_info[item_id] = {'name': name, 'full_local_path': full_local_path, 'parent': parent}
    
    @staticmethod
    def remove_item_info(items_info, item_id):
        if item_id in items_info:
            del items_info[item_id]
    
    @staticmethod
    def create_strm(driveid, item, file_path, content_type, addon_url):
        item_id = Utils.str(item['id'])
        item_drive_id = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
        f = None
        try:
            f = KodiUtils.file(file_path, 'w')
            content = addon_url + '?' + urllib.urlencode({'action':'play', 'content_type': content_type, 'item_driveid': item_drive_id, 'item_id': item_id, 'driveid': driveid})
            if item['name_extension'] == 'strm':
                content = Request(item['download_info']['url'], None).request()
            f.write(content)
        except:
            return False
        finally:
            if f:
                f.close()
        return True
        
    def save_items_info(self, exportid, items_info):
        f = None
        try:
            f = KodiUtils.file(self.get_items_info_path(exportid), 'w')
            f.write(repr(items_info))
        finally:
            if f:
                f.close()

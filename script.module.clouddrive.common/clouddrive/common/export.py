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

from __future__ import unicode_literals

import json
import os
import urllib

from clouddrive.common.remote.request import Request
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils, timeit
from clouddrive.common.db import SimpleKeyValueDb
from _collections import deque
from clouddrive.common.remote.errorreport import ErrorReport


class ExportManager(object):
    _export_items_file_format = 'export-%s.items'
    _strm_extension = '.strm'

    def __init__(self, _base_path):
        self.exports_db = SimpleKeyValueDb(_base_path, 'exports')
        self.export_items_db = SimpleKeyValueDb(_base_path, 'export-items')
        
        # only if not migrated. ignore if fails to read.
        config_path = os.path.join(_base_path, 'exports.cfg')
        if os.path.exists(config_path):
            with KodiUtils.lock:
                try:
                    with open(config_path, 'rb') as fo:
                        exports = json.loads(fo.read())
                        for exportid in exports:
                            self.exports_db.set(exportid, exports[exportid])
                    os.rename(config_path, config_path + '.migrated')
                except Exception as ex:
                    Logger.debug("Error migrating exports.")
                    Logger.debug(ex)
                    os.rename(config_path, config_path + '.failed')
        for filename in os.listdir(_base_path):
            config_path = os.path.join(_base_path, filename)
            with KodiUtils.lock:
                try:
                    if filename[:7] == "export-" and filename[-6:] == ".items": 
                        exportid = filename.split(".")[0].split("-")[1]
                        Logger.debug(exportid)
                        with open(config_path, 'rb') as fo:
                            items_info = json.loads(fo.read())
                            self.export_items_db.set(exportid, items_info)
                        os.rename(config_path, config_path + '.migrated')
                except Exception as ex:
                    Logger.debug("Error migrating export items from %s" % filename)
                    Logger.debug(ex)
                    os.rename(config_path, config_path + '.failed')
                
        
    def get_exports(self):
        return self.exports_db.getall()

    @timeit
    def save_export(self, export):
        self.exports_db.set(export['id'], export)

    def remove_export(self, exportid, keep_local=True):
        export = self.exports_db.get(exportid)
        self.exports_db.remove(exportid)
        self.export_items_db.remove(exportid)
        self.export_items_db.remove('pending-' + exportid)
        self.export_items_db.remove('retry-' + exportid)
        path = os.path.join(export['destination_folder'], Utils.unicode(export['name']), '')
        if not keep_local:
            if KodiUtils.file_exists(path):
                Utils.remove_folder(path)

    def get_items_info(self, exportid):
        return self.export_items_db.get(exportid)

    @timeit
    def save_items_info(self, exportid, items_info):
        self.export_items_db.set(exportid, items_info)
    
    def get_pending_changes(self, exportid):
        return deque(Utils.default(self.export_items_db.get('pending-' + exportid), []))

    @timeit
    def save_pending_changes(self, exportid, changes):
        self.export_items_db.set('pending-' + exportid, list(changes))

    def get_retry_changes(self, exportid):
        return deque(Utils.default(self.export_items_db.get('retry-' + exportid), []))

    @timeit
    def save_retry_changes(self, exportid, changes):
        self.export_items_db.set('retry-' + exportid, list(changes))
                
    @staticmethod
    def add_item_info(items_info, item_id, name, full_local_path, parent, item_type):
        items_info[item_id] = {'name': name, 'full_local_path': full_local_path, 'parent': parent,'type':item_type}

    @staticmethod
    def remove_item_info(items_info, item_id):
        if item_id in items_info:
            del items_info[item_id]

    @staticmethod
    def get_strm_link(driveid, item, content_type, addon_url):
        item_id = Utils.str(item['id'])
        item_drive_id = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
        content = addon_url + '?' + urllib.urlencode(
                {'action': 'play', 'content_type': content_type, 'item_driveid': item_drive_id, 'item_id': item_id,
                 'driveid': driveid})
        return Utils.str(content)
    
    @staticmethod
    def create_text_file(file_path, content):
        f = None
        try:
            f = KodiUtils.file(file_path, 'w')
            f.write(Utils.str(content))
        except Exception as e:
            ErrorReport.handle_exception(e)
            return False
        finally:
            if f:
                f.close()
        return True

    @staticmethod
    def download(item, download_path, provider, on_update_download=None):
        url = item['download_info']['url']
        headers = None
        if provider.download_requires_auth:
            headers = {"Authorization":"Bearer %s"%provider.get_access_tokens()['access_token']}
        try:
            req = Request(url, None, headers, download_path = download_path, on_update_download = on_update_download)
            req.request()
        except Exception as e:
            ErrorReport.handle_exception(e)
            return False
        return req.success

    
                
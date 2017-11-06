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

import urllib
from urllib2 import HTTPError

from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.html import XHTML
from clouddrive.common.service.base import BaseService, BaseHandler
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from clouddrive.common.service.rpc import RpcUtil
from clouddrive.common.ui.logger import Logger


class SourceService(BaseService):
    name = 'source'
    def __init__(self):
        super(SourceService, self).__init__()
        self._handler = Source
    
    def get_port(self):
        return int(KodiUtils.get_addon_setting('port_directory_listing'))
    
    def start(self):
        if KodiUtils.get_addon_setting('allow_directory_listing') == 'true':
            super(SourceService, self).start()
    
class Source(BaseHandler):
    account_manager = None
    kilobyte = 1024.0
    megabyte = kilobyte*kilobyte
    gigabyte = megabyte*kilobyte
    
    def open_table(self, title):
        title = urllib.unquote(title)
        html = XHTML('html')
        html.head.title(title)
        body = html.body
        body.h1(title)
        table = body.table()
        row = table.tr
        row.th.a('Name')
        row.th.a('Last modified')
        row.th.a('Size')
        row.th.a('Description')
        row = table.tr
        row.th(colspan='4').hr()
        return html, table
    
    def add_row(self, table, file_name, date='  - ', size='  - ', description='&nbsp;'):
        row = table.tr
        row.td.a(file_name, href=urllib.quote(file_name))
        row.td(date, align='right')
        row.td(size, align='right')
        row.td(description, escape=False)
    
    def close_table(self, table):
        table.tr.th(colspan='4').hr()
    
    def get_size(self, size):
        unit = ''
        if size > self.gigabyte:
            size = size / self.gigabyte
            unit = 'G'
        elif size > self.megabyte:
            size = size / self.megabyte
            unit = 'M'
        elif size > self.kilobyte:
            size = size / self.kilobyte
            unit = 'K'
        elif size < 0:
            return '-'
        return ("%.2f" % size) + unit
    
    def get_cloud_drive_addons(self):
        addons = []
        addonid = KodiUtils.get_addon_info('id')
        response = KodiUtils.execute_json_rpc('Addons.GetAddons', {'type':'xbmc.python.pluginsource', 'enabled': True, 'properties': ['dependencies', 'name']})
        for addon in Utils.get_safe_value(Utils.get_safe_value(response, 'result', {}), 'addons', []):
            for dependency in addon['dependencies']:
                if dependency['addonid'] == addonid:
                    addons.append(addon)
                    break
        return addons
        
    def show_addon_list(self):
        html, table = self.open_table('Index of /')
        for addon in self.get_cloud_drive_addons():
            self.add_row(table, Utils.str(addon['name']) + '/')
        self.close_table(table)
        response = Utils.get_file_buffer()
        response.write(str(html))
        self.write_response(200, content=response)
    
    def get_drive_list(self, addonid):
        drives = []
        accounts = RpcUtil.rpc(addonid, 'get_accounts')
        for account_id in accounts:
            account = accounts[account_id]
            for drive in account['drives']:
                drives.append(drive)
        return drives
    
    def get_addonid(self, addon_name):
        addons = self.get_cloud_drive_addons()
        addonid = None
        for addon in addons:
            if urllib.quote(Utils.str(addon['name'])) == addon_name:
                addonid = addon['addonid']
                break
        return addonid
    
    def get_driveid(self, addonid, drive_name):
        driveid = None
        drives = self.get_drive_list(addonid)
        for drive in drives:
            if urllib.quote(Utils.str(drive['display_name'])) == drive_name:
                driveid = drive['id']
                break
        return driveid
                
    
    def show_drives(self, addon_name):
        addonid = self.get_addonid(addon_name)
        response_code = 200
        if addonid:
            html, table = self.open_table('Index of /'+addon_name+'/')
            self.add_row(table, '../')
            drives = self.get_drive_list(addonid)
            for drive in drives:
                self.add_row(table, Utils.str(drive['display_name']) + '/')
            self.close_table(table)
        else:
            response_code = 404
            html = 'Cloud Drive addon "%s" does not exist' % addon_name
        response = Utils.get_file_buffer()
        response.write(str(html))
        self.write_response(response_code, content=response)
    
    def process_path(self, addon_name, drive_name, path):
        addonid = self.get_addonid(addon_name)
        headers = {}
        response = Utils.get_file_buffer()
        if addonid:
            driveid = self.get_driveid(addonid, drive_name)
            if driveid:
                parts = self.path.split('/')
                if parts[len(parts)-1]:
                    response_code = 303
                    if path:
                        url = self.get_download_url(addonid, driveid, path)
                    else:
                        url = self.path + '/'
                    headers['location'] = url
                else:
                    response_code = 200
                    response.write(str(self.show_folder(addonid, driveid, path)))
            else:
                response_code = 404
                response.write('Drive "%s" does not exist for addon "%s"' % (drive_name, addon_name))
        else:
            response_code = 404
            response.write('Cloud Drive addon "%s" does not exist' % addon_name)
        self.write_response(response_code, content=response, headers=headers)

    def show_folder(self, addonid, driveid, path):
        path_len = len(path)
        if path_len > 1:
            path = path[:path_len-1]
        items = RpcUtil.rpc(addonid, 'get_folder_items', kwargs={'driveid': driveid, 'path': path})
        html, table = self.open_table('Index of ' + self.path)
        self.add_row(table, '../')
        for item in items:
            file_name = Utils.str(item['name'])
            if 'folder' in item:
                file_name += '/'
            date = Utils.default(self.date_time_string(KodiUtils.to_timestamp(Utils.get_safe_value(item, 'last_modified_date'))), '  - ')
            size = self.get_size(Utils.default(Utils.get_safe_value(item, 'size'), -1))
            description = Utils.default(Utils.get_safe_value(item, 'description'), '&nbsp;')
            self.add_row(table, file_name, date, size, description)
        self.close_table(table)
        return html
    
    def get_download_url(self, addonid, driveid, path):
        item = RpcUtil.rpc(addonid, 'get_item', kwargs={'driveid': driveid, 'path': path, 'include_download_info': True})
        if 'folder' in item:
            return self.path + '/'
        return item['download_info']['url']
        
    def do_GET(self):
        data = self.path.split('/')
        size = len(data)
        if size > 1 and data[1] == self.server.service.name:
            try:
                if size == 2:
                    self.write_response(303, headers={'location': self.path + '/'})
                elif size > 2 and data[2]:
                    addon_name = data[2]
                    if size == 3:
                        self.write_response(303, headers={'location': self.path + '/'})
                    elif size == 4 and not data[3]:
                        self.show_drives(addon_name)
                    else:
                        drive_name = data[3]
                        path = self.path[len(self.server.service.name)+len(addon_name)+len(drive_name)+3:]
                        self.process_path(addon_name, drive_name, path)
                else:
                    self.show_addon_list()
            except Exception as e:
                httpex = ExceptionUtils.extract_exception(e, HTTPError)
                if httpex:
                    response_code = httpex.code
                else:
                    response_code = 500
                content = Utils.get_file_buffer()
                content.write(ExceptionUtils.full_stacktrace(e))
                self.write_response(response_code, content=content)
        else:
            self.write_response(404)
            
        

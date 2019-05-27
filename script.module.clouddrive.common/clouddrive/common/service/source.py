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
import time
from types import NoneType
import urllib
from urllib2 import HTTPError

from clouddrive.common.account import AccountManager
from clouddrive.common.cache.cache import Cache
from clouddrive.common.exception import ExceptionUtils, RequestException
from clouddrive.common.html import XHTML
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.service.base import BaseServerService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
import json
from urlparse import urlparse


class Source(BaseHandler):
    _system_monitor = None
    _account_manager = None

    kilobyte = 1024.0
    megabyte = kilobyte*kilobyte
    gigabyte = megabyte*kilobyte
    
    def __init__(self, request, client_address, server):
        self._system_monitor = KodiUtils.get_system_monitor()
        self._account_manager = AccountManager(server.service.profile_path)
        self._addonid = KodiUtils.get_addon_info('id')
        expiration = datetime.timedelta(minutes=KodiUtils.get_cache_expiration_time())
        self._page_cache = Cache(self._addonid, 'page', expiration)
        self._children_cache = Cache(self._addonid, 'children', expiration)
        self._items_cache = Cache(self._addonid, 'items', expiration)
        BaseHandler.__init__(self, request, client_address, server)
    
    def __del__(self):
        del self._system_monitor
        del self._account_manager
        Logger.debug('Request destroyed.')
    
    def _get_provider(self):
        return self.server.data(source_mode = True)
    
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
        response = KodiUtils.execute_json_rpc('Addons.GetAddons', {'type':'xbmc.python.pluginsource', 'enabled': True, 'properties': ['dependencies', 'name']})
        for addon in Utils.get_safe_value(Utils.get_safe_value(response, 'result', {}), 'addons', []):
            for dependency in addon['dependencies']:
                if dependency['addonid'] == self._addonid:
                    addons.append(addon)
                    break
        return addons
    
    def get_addonid(self, addon_name):
        addons = self.get_cloud_drive_addons()
        addonid = None
        for addon in addons:
            if urllib.quote(Utils.str(addon['name'])) == addon_name:
                addonid = addon['addonid']
                break
        return addonid
    
    def show_addon_list(self):
        html, table = self.open_table('Index of /')
        addons = self.get_cloud_drive_addons()
        if addons:
            for addon in addons:
                self.add_row(table, Utils.str(addon['name']) + '/')
        else:
            self.add_row(table, KodiUtils.get_addon_info('name') + '/')
            
        self.close_table(table)
        response = Utils.get_file_buffer()
        response.write(str(html))
        return {'response_code': 200, 'content': response}
        
    def get_drive_list(self):
        drives = []
        accounts = self._account_manager.load()
        provider = self._get_provider()
        for account_id in accounts:
            account = accounts[account_id]
            for drive in account['drives']:
                drive['display_name'] = self._account_manager.get_account_display_name(account, drive, provider)
                drives.append(drive)
        return drives
    
    def get_driveid(self, drive_name):
        driveid = None
        drives = self.get_drive_list()
        for drive in drives:
            if urllib.quote(Utils.str(drive['display_name'])) == drive_name:
                driveid = drive['id']
                break
        return driveid
    
    def show_drives(self, addon_name):
        html, table = self.open_table('Index of /'+addon_name+'/')
        self.add_row(table, '../')
        drives = self.get_drive_list()
        for drive in drives:
            self.add_row(table, Utils.str(drive['display_name']) + '/')
        self.close_table(table)
        response = Utils.get_file_buffer()
        response.write(str(html))
        return {'response_code': 200, 'content': response}
    
    def process_path(self, addon_name, drive_name, path):
        headers = {}
        response = Utils.get_file_buffer()
        driveid = self.get_driveid(drive_name)
        if driveid:
            parts = self.path.split('/')
            filename = parts[len(parts)-1]
            if filename:
                response_code = 303
                if path:
                    u = urlparse(path)
                    path = u.path
                    Logger.debug('query: %s' % u.query)
                    if u.query == 'subtitles':
                        response_code = 200
                        response.write(json.dumps({'driveid': driveid, 'subtitles': self.get_subtitles(driveid, path)}))
                    else:
                        key = '%s%s:children' % (driveid, path[0:path.rfind('/')],)
                        Logger.debug('reading cache key: ' + key)
                        children = self._children_cache.get(key)
                        if not children and type(children) is NoneType:
                            self.get_folder_items(driveid, path[0:path.rfind('/')+1])
                        url = self.get_download_url(driveid, path)
                        headers['location'] = url
                else:
                    url = self.path + '/'
                    headers['location'] = url
            else:
                response_code = 200
                response.write(str(self.show_folder(driveid, path)))
        else:
            response_code = 404
            response.write('Drive "%s" does not exist for addon "%s"' % (drive_name, addon_name))
        return {'response_code': response_code, 'content': response, 'headers': headers}
    
    def get_folder_items(self, driveid, path):
        provider = self._get_provider()
        provider.configure(self._account_manager, driveid)
        cache_path = path[:len(path)-1]
        request_path = cache_path if len(path) > 1 else path
        self.is_path_possible(driveid, request_path)
        key = '%s%s:items' % (driveid, cache_path,)
        items = self._items_cache.get(key)
        if not items and type(items) is NoneType:
            items = provider.get_folder_items(path=request_path, include_download_info=True)
            self._items_cache.set(key, items)
            children_names = []
            cache_items = []
            for item in items:
                quoted_name = urllib.quote(Utils.str(item['name']))
                children_names.append(quoted_name)
                key = '%s%s%s' % (driveid, path, quoted_name,)
                Logger.debug('Adding item in cache for bulk: %s' % key)
                cache_items.append([key, item])
            self._items_cache.setmany(cache_items)
            Logger.debug('Cache in bulk saved')
            key = '%s%s:children' % (driveid, cache_path,)
            Logger.debug('saving children names for: ' + key)
            self._children_cache.set(key, children_names)
        else:
            Logger.debug('items for %s served from cache' % path)
        return items

    def show_folder(self, driveid, path):
        items = self.get_folder_items(driveid, path)
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
    
    def is_path_possible(self, driveid, path):
        index = path.rfind('/')
        while index >= 0:
            filename = path[index+1:]
            path = path[0:index]
            key = '%s%s:children' % (driveid, path,)
            Logger.debug('testing possible path key: ' + key)
            children = self._children_cache.get(key)
            if children or type(children) is list:
                if filename and not filename in children:
                    Logger.debug('Not found. From cache.') 
                    raise RequestException('Not found. From cache.', HTTPError(self.path, 404, 'Not found.', None, None), 'Request URL: %s' % self.path, None)
                return True
            index = path.rfind('/')
        return True
    
    def get_item(self, driveid, path):
        key = '%s%s' % (driveid, path,)
        Logger.debug('Testing item from cache: %s' % key)
        item = self._items_cache.get(key)
        if not item:
            provider = self._get_provider()
            provider.configure(self._account_manager, driveid)
            self.is_path_possible(driveid, path)
            item = provider.get_item(path=path, include_download_info = True)
            Logger.debug('Saving item in cache: %s' % key)
            self._items_cache.set(key, item)
        return item
    
    def get_download_url(self, driveid, path):
        item = self.get_item(driveid, path) 
        if 'folder' in item:
            return self.path + '/'
        return item['download_info']['url']
    
    def get_subtitles(self, driveid, path):
        item = self.get_item(driveid, path) 
        key = '%s%s-subtitles' % (driveid, path,)
        Logger.debug('Testing subtitles from cache: %s' % key)
        subtitles = self._items_cache.get(key)
        if not subtitles:
            provider = self._get_provider()
            provider.configure(self._account_manager, driveid)
            self.is_path_possible(driveid, path)
            item_driveid = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
            subtitles = provider.get_subtitles(item['parent'], item['name'], item_driveid)
            Logger.debug('Saving subtitles in cache: %s' % key)
            self._items_cache.set(key, item)
        return subtitles
    
    def handle_resource_request(self, data):
        addon_name = data[2]
        size = len(data)
        cached_page = {}
        if size == 3:
            cached_page['response_code'] = 303
            cached_page['headers'] = {'location': self.path + '/'}
        elif size == 4 and not data[3]:
            cached_page = self.show_drives(addon_name)
        else:
            drive_name = data[3]
            path = self.path[len(self.server.service.name)+len(addon_name)+len(drive_name)+3:]
            cached_page = self.process_path(addon_name, drive_name, path)
        return cached_page
            
    def do_GET(self):
        Logger.debug(self.path + ': Requested')
        if self._system_monitor.abortRequested():
            Logger.debug(self.path + ': abort requested')
            return
        data = self.path.split('/')
        size = len(data)
        cached_page = self._page_cache.get(self.path)
        if cached_page:
            if cached_page['pending']:
                Logger.debug(self.path + ': Already requested. Waiting for original request...')
                max_waiting_time = time.time() + 30
                while not self._system_monitor.abortRequested() and max_waiting_time > time.time() and cached_page['pending']:
                    if self._system_monitor.waitForAbort(1):
                        break
                    cached_page = self._page_cache.get(self.path)

            if not self._system_monitor.abortRequested():
                if cached_page['pending']:
                    self.write_response(504)
                    Logger.debug(self.path + ': 504 - Gateway timeout')
                    self._page_cache.remove(self.path)
                else:
                    if 'content' in cached_page and cached_page['content']:
                        content = Utils.get_file_buffer()
                        content.write(cached_page['content'])
                        cached_page['content'] = content
                    self.write_response(cached_page['response_code'], content=Utils.get_safe_value(cached_page, 'content'), headers=Utils.get_safe_value(cached_page, 'headers', {}))
                    Logger.debug(self.path + ': %d - Served from cache' % cached_page['response_code'])
        else:
            cached_page = {'pending': True}
            self._page_cache.set(self.path, cached_page)
            if size > 1 and data[1] == self.server.service.name:
                try:
                    if size == 2:
                        cached_page['response_code'] = 303
                        cached_page['headers'] = {'location': self.path + '/'}
                    elif size > 2 and data[2]:
                        cached_page = self.handle_resource_request(data)
                    else:
                        cached_page = self.show_addon_list()
                except Exception as e:
                    httpex = ExceptionUtils.extract_exception(e, HTTPError)
                    if httpex:
                        cached_page['response_code'] = httpex.code
                    else:
                        cached_page['response_code'] = 500
                    
                    ErrorReport.handle_exception(e)
                    content = Utils.get_file_buffer()
                    content.write(ExceptionUtils.full_stacktrace(e))
                    
                    cached_page['content'] = content
            else:
                cached_page['response_code'] = 404
            cached_page['pending'] = False
            content_value = None
            if 'content' in cached_page:
                content_value = cached_page['content'].getvalue()
            self.write_response(cached_page['response_code'], content=Utils.get_safe_value(cached_page, 'content'), headers=Utils.get_safe_value(cached_page, 'headers', {}))
            cached_page['content'] = content_value
            if Utils.get_safe_value(cached_page, 'response_code', 0) >= 500:
                self._page_cache.remove(self.path)
            else:
                self._page_cache.set(self.path, cached_page)
            Logger.debug(self.path + ': Response code ' + Utils.str(cached_page['response_code']))
 
class SourceRedirector(Source):
    def __init__(self, request, client_address, server):
        Source.__init__(self, request, client_address, server)
    
    def handle_resource_request(self, data):
        size = len(data)
        response = {'response_code': 404}
        if size > 2 and data[2]:
            addon_name = data[2]
            addonid = self.get_addonid(addon_name)
            Logger.debug('Redirector - addon id: %s' % addonid)
            if addonid:
                destination_port = KodiUtils.get_service_port(self.server.service.name, addonid)
                path = 'http://%s:%s' % (self.server.service._interface, destination_port,) + self.path
                Logger.debug('Redirector: %s' % path)
                response['response_code'] = 303
                response['headers'] = {'location': path}

        return response
    
class SourceService(BaseServerService):
    name = 'source'
    profile_path = Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info('profile')))
    
    def __init__(self, provider_class, handler=Source):
        super(SourceService, self).__init__(provider_class)
        self._handler = handler
        addonid = KodiUtils.get_addon_info('id')
        Cache(addonid, 'page', 0).clear()
        Cache(addonid, 'children', 0).clear()
        Cache(addonid, 'items', 0).clear()
    
    def get_port(self):
        return int(KodiUtils.get_addon_setting('port_directory_listing'))
    
    def start(self):
        if KodiUtils.get_addon_setting('allow_directory_listing') == 'true':
            super(SourceService, self).start()
    
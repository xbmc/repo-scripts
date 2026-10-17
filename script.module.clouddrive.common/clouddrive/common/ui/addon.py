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

import inspect
import os
import sys
import threading
import time
import urllib

from clouddrive.common.account import AccountManager
from clouddrive.common.exception import ExceptionUtils, RequestException
from clouddrive.common.export import ExportManager
from clouddrive.common.remote.request import Request
from clouddrive.common.service.download import DownloadServiceUtil
from clouddrive.common.ui.dialog import DialogProgress, DialogProgressBG, ExportMainDialog
from clouddrive.common.ui.errors import ErrorMessage, ErrorMessages
from clouddrive.common.ui.signin import AccountSignin
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils, ARCHIVE_EXTENSIONS
import xbmcgui
import xbmcplugin
import xbmcvfs
from datetime import timedelta, datetime
from clouddrive.common.cache.cache import Cache


class CloudDriveAddon:
    # The methods a plugin URL may run, by its "action" parameter. Plugins list their own in _plugin_actions.
    _actions = ('_add_account', '_clear_cache', '_list_drive', '_list_exports', '_list_folder', '_open_common_settings',
                '_open_export', '_remove_account', '_remove_drive', '_remove_export', '_run_export', '_search', '_slideshow',
                'download', 'play')
    _plugin_actions = ()
    _addon = None
    _addon_handle = None
    _addonid = None
    _addon_name = None
    _addon_params = None
    _addon_url = None
    _addon_version = None
    _common_addon = None
    _cancel_operation = False
    _content_type = None
    _dialog = None
    _export_manager = None
    _child_count_supported = True
    _auto_refreshed_slideshow_supported = True
    _load_target = 0
    _load_count = 0
    _profile_path = None
    _progress_dialog = None
    _progress_dialog_bg = None
    _system_monitor = None
    _video_file_extensions = [x for x in KodiUtils.get_supported_media("video") if x not in ARCHIVE_EXTENSIONS]
    _audio_file_extensions = [x for x in KodiUtils.get_supported_media("music") if x not in ARCHIVE_EXTENSIONS]
    _image_file_extensions = [x for x in KodiUtils.get_supported_media("picture") if x not in ARCHIVE_EXTENSIONS]
    _account_manager = None
    _action = None
    _signin = None
    
    def __init__(self):
        self._addon = KodiUtils.get_addon()
        self._addonid = self._addon.getAddonInfo('id')
        self._addon_name = self._addon.getAddonInfo('name')
        self._addon_url = sys.argv[0]
        self._addon_version = self._addon.getAddonInfo('version')
        self._common_addon_id = 'script.module.clouddrive.common'
        self._common_addon = KodiUtils.get_addon(self._common_addon_id)
        self._common_addon_version = self._common_addon.getAddonInfo('version')
        self._dialog = xbmcgui.Dialog()
        self._profile_path = Utils.unicode(KodiUtils.translate_path(self._addon.getAddonInfo('profile')))
        self._progress_dialog = DialogProgress(self._addon_name)
        self._progress_dialog_bg = DialogProgressBG(self._addon_name)
        self._system_monitor = KodiUtils.get_system_monitor()
        self._account_manager = AccountManager(self._profile_path)
        
        if len(sys.argv) > 1:
            self._addon_handle = int(sys.argv[1])
            self._addon_params = urllib.parse.parse_qs(sys.argv[2][1:])
            for param in self._addon_params:
                self._addon_params[param] = self._addon_params.get(param)[0]
            self._content_type = Utils.get_safe_value(self._addon_params, 'content_type')
            if not self._content_type:
                wid = xbmcgui.getCurrentWindowId()
                if wid == 10005 or wid == 10500 or wid == 10501 or wid == 10502:
                    self._content_type = 'audio'
                elif wid == 10002:
                    self._content_type = 'image'
                else:
                    self._content_type = 'video'
            xbmcplugin.addSortMethod(handle=self._addon_handle, sortMethod=xbmcplugin.SORT_METHOD_LABEL)
            xbmcplugin.addSortMethod(handle=self._addon_handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED ) 
            xbmcplugin.addSortMethod(handle=self._addon_handle, sortMethod=xbmcplugin.SORT_METHOD_SIZE )
            xbmcplugin.addSortMethod(handle=self._addon_handle, sortMethod=xbmcplugin.SORT_METHOD_DATE )
            xbmcplugin.addSortMethod(handle=self._addon_handle, sortMethod=xbmcplugin.SORT_METHOD_DURATION )
    
    def __del__(self):
        del self._addon
        del self._common_addon
        del self._dialog
        del self._progress_dialog
        del self._progress_dialog_bg
        del self._system_monitor
        del self._account_manager
        
    def get_provider(self):
        raise NotImplementedError()
    
    def get_my_files_menu_name(self):
        return self._common_addon.getLocalizedString(32052)
    
    def get_custom_drive_folders(self, driveid):
        return
    
    def cancel_operation(self):
        return self._system_monitor.abortRequested() or self._progress_dialog.iscanceled() or self._cancel_operation or (self._signin is not None and self._signin.cancelled())

    def _get_display_name(self, account, drive=None, with_format=False):
        return self._account_manager.get_account_display_name(account, drive, self.get_provider(), with_format)
    
    def get_accounts(self, with_format=False):
        accounts = self._account_manager.get_accounts()
        for account_id in accounts:
            account = accounts[account_id]
            for drive in account['drives']:
                drive['display_name'] = self._get_display_name(account, drive, with_format)
        return accounts
                    
    def list_accounts(self):
        accounts = self.get_accounts(with_format=True)
        listing = []
        for account_id in accounts:
            account = accounts[account_id]
            size = len(account['drives'])
            for drive in account['drives']:
                context_options = []
                params = {'action':'_search', 'content_type': self._content_type, 'driveid': drive['id']}
                cmd = 'ActivateWindow(%d,%s?%s)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.parse.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                params['action'] = '_remove_account'
                context_options.append((self._common_addon.getLocalizedString(32006), 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'))
                if size > 1:
                    params['action'] = '_remove_drive'
                    cmd =  'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'
                    context_options.append((self._common_addon.getLocalizedString(32007), cmd))
                list_item = xbmcgui.ListItem(drive['display_name'])
                list_item.addContextMenuItems(context_options)
                params = {'action':'_list_drive', 'content_type': self._content_type, 'driveid': drive['id']}
                url = self._addon_url + '?' + urllib.parse.urlencode(params)
                listing.append((url, list_item, True))
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32005))
        params = {'action':'_add_account', 'content_type': self._content_type}
        url = self._addon_url + '?' + urllib.parse.urlencode(params)
        listing.append((url, list_item))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def _add_account(self):
        self._signin = AccountSignin(self.get_provider(), self._account_manager, self._common_addon, self._addon_name,
                                     self._progress_dialog, self._progress_dialog_bg, self._system_monitor)
        if self._signin.run():
            KodiUtils.executebuiltin('Container.Refresh')

    def _remove_drive(self, driveid):
        account = self._account_manager.get_by_driveid('account', driveid)
        drive = self._account_manager.get_by_driveid('drive', driveid, account)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32023) % self._get_display_name(account, drive, True)):
            self._account_manager.remove_drive(driveid, account)
            KodiUtils.executebuiltin('Container.Refresh')
    
    def _remove_account(self, driveid):
        account = self._account_manager.get_by_driveid('account', driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32022) % self._get_display_name(account, with_format=True)):
            self._account_manager.remove_account(account['id'])
            KodiUtils.executebuiltin('Container.Refresh')
        
    def _list_drive(self, driveid):
        drive_folders = self.get_custom_drive_folders(driveid)
        if self.cancel_operation():
            return
        if drive_folders:
            listing = []
            url = self._addon_url + '?' + urllib.parse.urlencode({'action':'_list_folder', 'path': '/', 'content_type': self._content_type, 'driveid': driveid})
            listing.append((url, xbmcgui.ListItem('[B]%s[/B]' % self.get_my_files_menu_name()), True))
            for folder in drive_folders:
                params = {'action':'_list_folder', 'path': folder['path'], 'content_type': self._content_type, 'driveid': driveid}
                if 'params' in folder:
                    params.update(folder['params'])
                url = self._addon_url + '?' + urllib.parse.urlencode(params)
                list_item = xbmcgui.ListItem(Utils.unicode(folder['name']))
                if 'context_options' in folder:
                    list_item.addContextMenuItems(folder['context_options'])
                listing.append((url, list_item, True))
            if self._content_type == 'video' or self._content_type == 'audio':
                url = self._addon_url + '?' + urllib.parse.urlencode({'action':'_list_exports', 'content_type': self._content_type, 'driveid': driveid})
                listing.append((url, xbmcgui.ListItem(self._common_addon.getLocalizedString(32000)), True))
            url = self._addon_url + '?' + urllib.parse.urlencode({'action':'_search', 'content_type': self._content_type, 'driveid': driveid})
            listing.append((url, xbmcgui.ListItem(self._common_addon.getLocalizedString(32039)), True))
            
            xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
            xbmcplugin.endOfDirectory(self._addon_handle, True)
        else:
            self._list_folder(driveid, path='/')

    def _list_exports(self, driveid):
        self._export_manager = ExportManager(self._profile_path)
        exports = self._export_manager.get_exports()
        listing = []
        for exportid in exports:
            export = exports[exportid]
            if export['driveid'] == driveid and export['content_type'] == self._content_type:
                item_name = Utils.unicode(export['name'])
                params = {'action':'_open_export', 'content_type': self._content_type, 'driveid': driveid, 'item_driveid': export['item_driveid'], 'item_id': export['id'], 'name': urllib.parse.quote(Utils.str(item_name))}
                url = self._addon_url + '?' + urllib.parse.urlencode(params)
                list_item = xbmcgui.ListItem(item_name)
                context_options = []
                params['action'] = '_run_export'
                context_options.append((KodiUtils.localize(21479), 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'))
                params['action'] = '_remove_export'
                context_options.append((KodiUtils.localize(1210), 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'))
                list_item.addContextMenuItems(context_options)
                listing.append((url, list_item, True))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def _run_export(self, driveid, item_id):
        self._export_manager = ExportManager(self._profile_path)
        export = self._export_manager.get_exports()[item_id]
        export['run_immediately'] = True
        self._export_manager.save_export(export)
        KodiUtils.show_notification(self._common_addon.getLocalizedString(32055) % '60')
    
    def _remove_export(self, driveid, item_id):
        self._export_manager = ExportManager(self._profile_path)
        exports = self._export_manager.get_exports()
        if item_id in exports:
            item = exports[item_id]
            remove_export = self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32001) % Utils.unicode(item['name']))
            if remove_export:
                keep_locals = self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32086) % Utils.unicode(item['name']))
                if not keep_locals:
                    self._export_manager.remove_export(item_id, False)
                else:
                    self._export_manager.remove_export(item_id)
                KodiUtils.executebuiltin('Container.Refresh')
        else:
            KodiUtils.executebuiltin('Container.Refresh')
    
    def _open_export(self, driveid, item_driveid, item_id, name):
        export_dialog = ExportMainDialog.create(self._content_type, driveid, item_driveid, item_id, name, self._account_manager, self.get_provider())
        export_dialog.doModal()
        if export_dialog.run:
            KodiUtils.show_notification(self._common_addon.getLocalizedString(32055) % '60')
    
    def on_items_page_completed(self, items):
        self._load_count += len(items)
        if self._load_target > self._load_count:
            percent = int(round(float(self._load_count)/self._load_target*100))
            self._progress_dialog_bg.update(percent, self._addon_name, self._common_addon.getLocalizedString(32047) % (Utils.str(self._load_count), Utils.str(self._load_target)))
        else:
            self._progress_dialog_bg.update(100, self._addon_name, self._common_addon.getLocalizedString(32048) % Utils.str(self._load_count))
            
    def _list_folder(self, driveid, item_driveid=None, item_id=None, path=None):
        self.get_provider().configure(self._account_manager, driveid)
        if self._child_count_supported:
            item = self.get_provider().get_item(item_driveid, item_id, path)
            if item:
                self._load_target = item['folder']['child_count']
                self._progress_dialog_bg.create(self._addon_name, self._common_addon.getLocalizedString(32049) % Utils.str(self._load_target))
        
        items = self.get_provider().get_folder_items(item_driveid, item_id, path, on_items_page_completed = self.on_items_page_completed)
        if self.cancel_operation():
            return
        self._process_items(items, driveid)
        
    def _process_items(self, items, driveid):
        listing = []
        for item in items:
            Logger.debug(item)
            item_id = item['id']
            item_name = Utils.unicode(item['name'])
            item_name_extension = item['name_extension']
            item_driveid = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
            list_item = xbmcgui.ListItem(item_name)
            url = None
            is_folder = 'folder' in item
            params = {'content_type': self._content_type, 'item_driveid': item_driveid, 'item_id': item_id, 'driveid': driveid}
            if 'extra_params' in item:
                params.update(item['extra_params'])
            context_options = []
            info = {'size': item['size'], 'date': KodiUtils.to_kodi_item_date_str(KodiUtils.to_datetime(Utils.get_safe_value(item, 'last_modified_date')))}
            if is_folder:
                params['action'] = '_list_folder'
                url = self._addon_url + '?' + urllib.parse.urlencode(params)
                params['action'] = '_search'
                cmd = 'ActivateWindow(%d,%s?%s)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.parse.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                if self._content_type == 'audio' or self._content_type == 'video':
                    params['action'] = '_open_export'
                    params['name'] = urllib.parse.quote(Utils.str(item_name))
                    context_options.append((self._common_addon.getLocalizedString(32004), 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'))
                    del params['name']
                elif self._content_type == 'image' and self._auto_refreshed_slideshow_supported:
                    params['action'] = '_slideshow'
                    context_options.append((self._common_addon.getLocalizedString(32032), 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'))
            elif (('video' in item or (item_name_extension and item_name_extension in self._video_file_extensions)) and self._content_type == 'video') or (('audio' in item or (item_name_extension and item_name_extension in self._audio_file_extensions)) and self._content_type == 'audio'):
                list_item.setProperty('IsPlayable', 'true')
                params['action'] = 'download'
                cmd = 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'
                context_options.append((self._common_addon.getLocalizedString(32051), cmd))
                params['action'] = 'play'
                url = self._addon_url + '?' + urllib.parse.urlencode(params)
                # Kodi's info type for audio is 'music'.
                info_type = 'music' if self._content_type == 'audio' else self._content_type
                if 'audio' in item:
                    info.update(item['audio'])
                    info_type = 'music'
                elif 'video' in item:
                    list_item.addStreamInfo('video', item['video'])
                list_item.setInfo(info_type, info)
                if 'thumbnail' in item:
                    list_item.setArt({'icon': item['thumbnail'], 'thumb': item['thumbnail']})
            elif ('image' in item or (item_name_extension and item_name_extension in self._image_file_extensions)) and self._content_type == 'image':
                Logger.debug('image in item: %s' % (Utils.str('image' in item)),)
                Logger.debug('item_name_extension in self._image_file_extensions: %s' % (Utils.str(item_name_extension in self._image_file_extensions),))
                params['action'] = 'download'
                cmd = 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode(params)+')'
                context_options.append((self._common_addon.getLocalizedString(32051), cmd))
                if 'url' in item:
                    url = item['url']
                else:
                    url = self._get_item_play_url(item_name, driveid, item_driveid, item_id)
                if 'image' in item:
                    info.update(item['image'])
                list_item.setInfo('pictures', info)
                if 'thumbnail' in item and item['thumbnail']:
                    list_item.setArt({'icon': item['thumbnail'], 'thumb': item['thumbnail']})
            if url:
                context_options.extend(self.get_context_options(list_item, params, is_folder))
                list_item.addContextMenuItems(context_options)
                mimetype = Utils.default(Utils.get_mimetype_by_extension(item_name_extension), Utils.get_safe_value(item, 'mimetype'))
                if mimetype:
                    list_item.setProperty('mimetype', mimetype)
                
                listing.append((url, list_item, is_folder))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def get_context_options(self, list_item, params, is_folder):
        return []
        
    def _search(self, driveid, item_driveid=None, item_id=None):
        self.get_provider().configure(self._account_manager, driveid)
        query = self._dialog.input(self._addon_name + ' - ' + self._common_addon.getLocalizedString(32042))
        if query:
            self._progress_dialog_bg.create(self._addon_name, self._common_addon.getLocalizedString(32041))
            items = self.get_provider().search(query, item_driveid, item_id, on_items_page_completed = self.on_items_page_completed)
            if self.cancel_operation():
                return
            self._process_items(items, driveid)
    
    def download(self, driveid, item_driveid=None, item_id=None):
        dest_folder = self._dialog.browse(0, self._common_addon.getLocalizedString(32002), 'files')
        if dest_folder:
            provider = self.get_provider()
            provider.configure(self._account_manager, driveid)
            item = provider.get_item(item_driveid, item_id, include_download_info=True)
            name = Utils.get_safe_value(item,'name', item['id'])
            download_path = os.path.join(dest_folder, Utils.unicode(name))
            download_size = Utils.get_safe_value(item, 'size', 0)
            on_update_download = lambda request: self._progress_dialog_bg.update(int(1.0*request.download_progress/download_size*100), self._addon_name, self._common_addon.getLocalizedString(32056) % name)
            if ExportManager.download(item, download_path, provider, on_update_download = on_update_download):
                msg = self._common_addon.getLocalizedString(32057) % name
            else:
                msg = self._common_addon.getLocalizedString(32087) % name
            KodiUtils.show_notification(msg)
    
    def new_change_token_slideshow(self, change_token, driveid, item_driveid=None, item_id=None, path=None):
        self.get_provider().configure(self._account_manager, driveid)
        item = self.get_provider().get_item(item_driveid, item_id, path)
        if self.cancel_operation():
            return
        return item['folder']['child_count']
    
    def _slideshow(self, driveid, item_driveid=None, item_id=None, path=None, change_token=None):
        new_change_token = self.new_change_token_slideshow(change_token, driveid, item_driveid, item_id, path)
        if self.cancel_operation():
            return
        wait_for_slideshow = False
        if not change_token or change_token != new_change_token:
            Logger.notice('Slideshow will start. change_token: %s, new_change_token: %s' % (change_token, new_change_token))
            params = {'action':'_list_folder', 'content_type': self._content_type,
                      'item_driveid': Utils.default(item_driveid, ''), 'item_id': Utils.default(item_id, ''), 'driveid': driveid, 'path' : Utils.default(path, '')}
            extra_params = ',recursive' if self._addon.getSetting('slideshow_recursive') == 'true' else ''
            KodiUtils.executebuiltin('SlideShow('+self._addon_url + '?' + urllib.parse.urlencode(params) + extra_params + ')')
            wait_for_slideshow = True
        else:
            Logger.notice('Slideshow child count is the same, nothing to refresh...')
        t = threading.Thread(target=self._refresh_slideshow, args=(driveid, item_driveid, item_id, path, new_change_token, wait_for_slideshow,), daemon=True)
        t.start()
    
    def _refresh_slideshow(self, driveid, item_driveid, item_id, path, change_token, wait_for_slideshow):
        if wait_for_slideshow:
            Logger.notice('Waiting up to 10 minutes until the slideshow for folder %s starts...' % Utils.default(item_id, path))
            max_waiting_time = time.time() + 10 * 60
            while not self.cancel_operation() and not KodiUtils.get_cond_visibility('Slideshow.IsActive') and max_waiting_time > time.time():
                if self._system_monitor.waitForAbort(2):
                    break
            self._print_slideshow_info()
        interval = self._addon.getSetting('slideshow_refresh_interval')
        Logger.notice('Waiting up to %s minute(s) to check if it is needed to refresh the slideshow of folder %s...' % (interval, Utils.default(item_id, path)))
        target_time = time.time() + int(interval) * 60
        while not self.cancel_operation() and target_time > time.time() and KodiUtils.get_cond_visibility('Slideshow.IsActive'):
            if self._system_monitor.waitForAbort(10):
                break
        self._print_slideshow_info()
        if not self.cancel_operation() and KodiUtils.get_cond_visibility('Slideshow.IsActive'):
            try:
                self._slideshow(driveid, item_driveid, item_id, path, change_token)
            except Exception as e:
                Logger.error('Slideshow failed to auto refresh. Will be restarted when possible. Error: ')
                Logger.error(ExceptionUtils.full_stacktrace(e))
                self._refresh_slideshow(driveid, item_driveid, item_id, path, None, wait_for_slideshow)
        else:
            Logger.notice('Slideshow is not running anymore or abort requested.')
        
    def _print_slideshow_info(self):
        if KodiUtils.get_cond_visibility('Slideshow.IsActive'):
            Logger.debug('Slideshow is there...')
        elif self.cancel_operation():
            Logger.debug('Abort requested...')
            
    def _get_item_play_url(self, file_name, driveid, item_driveid=None, item_id=None, is_subtitle=False):
        # file_name as it is (not URL-encoded): it is encoded here, once.
        return DownloadServiceUtil.build_download_url(driveid, item_driveid, item_id, urllib.parse.quote(Utils.str(file_name)))
    
    def play(self, driveid, item_driveid=None, item_id=None):
        self.get_provider().configure(self._account_manager, driveid)
        find_subtitles = self._addon.getSetting('set_subtitle') == 'true' and self._content_type == 'video'
        item = self.get_provider().get_item(item_driveid, item_id, find_subtitles=find_subtitles)
        file_name = Utils.unicode(item['name'])
        list_item = xbmcgui.ListItem(file_name)
        succeeded = True
        info = KodiUtils.get_current_library_info()
        if not info:
            info = KodiUtils.find_exported_video_in_library(item_id, file_name + ExportManager._strm_extension)
        if info and info['id']:
            Logger.debug('library info: %s' % Utils.str(info))
            KodiUtils.set_home_property('dbid', Utils.str(info['id']))
            KodiUtils.set_home_property('dbtype', info['type'])
            KodiUtils.set_home_property('addonid', self._addonid)
            details = KodiUtils.get_video_details(info['type'], info['id'])
            Logger.debug('library details: %s' % Utils.str(details))
            if details and 'resume' in details:
                KodiUtils.set_home_property('playcount', Utils.str(details['playcount']))
                resume = details['resume']
                if resume['position'] > 0:
                    play_resume = False
                    if KodiUtils.get_addon_setting('ask_resume') == 'true':
                        d = datetime(1,1,1) + timedelta(seconds=resume['position'])
                        t = '%02d:%02d:%02d' % (d.hour, d.minute, d.second)
                        Logger.debug(t)
                        option = self._dialog.contextmenu([KodiUtils.localize(32054, addon=self._common_addon) % t, KodiUtils.localize(12021)])
                        Logger.debug('selected option: %d' % option)
                        if option == -1:
                            succeeded = False
                        elif option == 0:
                            play_resume = True
                    if play_resume:
                        list_item.setProperty('resumetime', Utils.str(resume['position']))
                        list_item.setProperty('startoffset', Utils.str(resume['position']))
                        list_item.setProperty('totaltime', Utils.str(resume['total']))
        else:
            from clouddrive.common.service.player import KodiPlayer
            KodiPlayer.cleanup()
        if 'audio' in item:
            list_item.setInfo('music', item['audio'])
        elif 'video' in item:
            list_item.addStreamInfo('video', item['video'])
        list_item.select(True)
        list_item.setPath(self._get_item_play_url(file_name, driveid, item_driveid, item_id))
        list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
        if find_subtitles and 'subtitles' in item:
            subtitles = []
            for subtitle in item['subtitles']:
                subtitles.append(self._get_item_play_url(subtitle['name'], driveid, Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid), subtitle['id'], True))
            list_item.setSubtitles(subtitles)
        if not self.cancel_operation():
            xbmcplugin.setResolvedUrl(self._addon_handle, succeeded, list_item)
    
    def _handle_exception(self, ex, show_error_dialog = True):
        stacktrace = ExceptionUtils.full_stacktrace(ex)
        rex = ExceptionUtils.extract_exception(ex, RequestException)
        signin_server = KodiUtils.get_signin_server()
        driveid = Utils.get_safe_value(self._addon_params, 'driveid')
        message = ErrorMessages(self._common_addon, signin_server).describe(
            ex, bool(driveid), self._signin.ip_before_pin if self._signin else None,
            lambda: Request(signin_server + '/ip', None).request())
        add_account_cmd = 'RunPlugin('+self._addon_url + '?' + urllib.parse.urlencode({'action':'_add_account', 'content_type': self._content_type})+')'
        if message.ask == ErrorMessage.ADD_ACCOUNT:
            show_error_dialog = False
            if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32063) % '\n'):
                KodiUtils.executebuiltin(add_account_cmd)
        elif message.ask == ErrorMessage.SIGN_IN_AGAIN:
            show_error_dialog = False
            account = self._account_manager.get_by_driveid('account', driveid)
            drive = self._account_manager.get_by_driveid('drive', driveid, account)
            if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32046) % (self._get_display_name(account, drive, True) + '\n')):
                KodiUtils.executebuiltin(add_account_cmd)

        report = '[%s] [%s]/[%s]\n\n%s\n%s\n%s\n\n%s' % (self._addonid, self._addon_version, self._common_addon_version, message.line1, message.line2, message.line3, stacktrace)
        if rex:
            report += '\n\n%s\nResponse:\n%s' % (rex.request, rex.response)
        report += '\n\nshow_error_dialog: %s' % show_error_dialog
        Logger.error(report)
        if show_error_dialog:
            text = message.line1
            if message.line2:
                text += '\n' + message.line2
            if message.line3:
                text += '\n' + message.line3
            self._dialog.ok(self._addon_name, text)

    def _open_common_settings(self):
        self._common_addon.openSettings()
    
    def _clear_cache(self):
        Cache(self._addonid, 'page', 0).clear()
        Cache(self._addonid, 'children', 0).clear()
        Cache(self._addonid, 'items', 0).clear()
        
    def _rename_action(self):
        pass
        
    def route(self):
        try:
            Logger.debug(self._addon_params)
            self._action = Utils.get_safe_value(self._addon_params, 'action')
            if self._action:
                self._rename_action()
                # URLs can come from anywhere (skins, favourites, other add-ons): only run the known actions.
                if self._action not in self._actions and self._action not in self._plugin_actions:
                    Logger.error('Unknown action: %s' % self._action)
                    return
                method = getattr(self, self._action)
                arguments = {}
                for name in inspect.getfullargspec(method)[0]:
                    if name in self._addon_params:
                        arguments[name] = self._addon_params[name]
                method(**arguments)
            else:
                self.list_accounts()
        except Exception as ex:
            self._handle_exception(ex)
        finally:
            self._progress_dialog.close()
            self._progress_dialog_bg.close()

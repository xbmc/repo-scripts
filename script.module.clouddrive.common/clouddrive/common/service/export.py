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
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
import datetime
from clouddrive.common.utils import Utils
from clouddrive.common.ui.dialog import ExportScheduleDialog
from calendar import weekday
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.export import ExportManager
from clouddrive.common.account import AccountManager
import os

class ExportService(object):
    name = 'export'

    def __init__(self, provider_class):
        self.abort = False
        self._system_monitor = KodiUtils.get_system_monitor()
        self.provider = provider_class()
        self.addonid = KodiUtils.get_addon_info('id')
        self._profile_path = Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info('profile')))
        self._startup_type = Utils.str(ExportScheduleDialog._startup_type)
        self.export_manager = ExportManager(self._profile_path)
        self._account_manager = AccountManager(self._profile_path)
        self._video_file_extensions = [x for x in KodiUtils.get_supported_media("video") if x not in ('','zip')]
        self._audio_file_extensions = KodiUtils.get_supported_media("music")
    
    def __del__(self):
        del self._system_monitor
        del self.export_manager
        del self._account_manager
        
    def cleanup_export_map(self):
        exports = self.export_manager.load()
        for exportid in exports:
            export = exports[exportid]
            export['exporting'] = False
        self.export_manager.save()
    
    def get_export_map(self):
        exports = self.export_manager.load()
        export_map = {}
        for exportid in exports:
            export = exports[exportid]
            schedules = Utils.get_safe_value(export, 'schedules', [])
            exporting = Utils.get_safe_value(export, 'exporting', False)
            if not exporting:
                if Utils.get_safe_value(export, 'schedule', False) and schedules:
                    for schedule in schedules:
                        key = Utils.str(Utils.get_safe_value(schedule, 'type', ''))
                        if key != self._startup_type:
                            key += Utils.get_safe_value(schedule, 'at', '')
                        export_map[key] = Utils.get_safe_value(export_map, key, [])
                        export_map[key].append(export)
                if Utils.get_safe_value(export, 'watch', False):
                    export_map['watch'] = Utils.get_safe_value(export_map, 'watch', [])
                    export_map['watch'].append(export)
        Logger.debug('export_map: %s' % Utils.str(export_map))
        return export_map
        
    def start(self):
        Logger.notice('Service \'%s\' started.' % self.name)
        self.cleanup_export_map()
        monitor = KodiUtils.get_system_monitor()
        startup = True
        while not self.abort:
            try:
                now = datetime.datetime.now()
                export_map = self.get_export_map()
                if export_map:
                    self.process_schedules(export_map, now, startup)
                    self.process_watch(export_map)
            except Exception as e:
                ErrorReport.handle_exception(e)
            startup = False
            if monitor.waitForAbort(60):
                break
        del monitor
        del self.provider
        Logger.notice('Service stopped.')
    
    def process_schedules(self, export_map, now, startup=False):
        Logger.debug('now: %s, startup: %s' % (Utils.str(now), Utils.str(startup)))
        export_list = []
        if startup:
            export_list.extend(Utils.get_safe_value(export_map, self._startup_type, []))
        else:
            at = '%02d:%02d' % (now.hour, now.minute,)
            Logger.debug('at: %s' % Utils.str(at))
            daily_list = Utils.get_safe_value(export_map, Utils.str(ExportScheduleDialog._daily_type) + at, [])
            export_list.extend(daily_list)
            Logger.debug('daily_list: %s' % Utils.str(daily_list))
            weekday = now.weekday() + 11
            weekday_list = Utils.get_safe_value(export_map, Utils.str(weekday) + at, [])
            export_list.extend(weekday_list)
            Logger.debug('weekday_list: %s' % Utils.str(weekday_list))
        Logger.debug('export_list: %s' % Utils.str(export_list) )
        for export in export_list:
            self.run_export(export)
    
    def run_export(self, export):
        export['exporting'] = True
        params = {'action':'_run_export', 'content_type': Utils.get_safe_value(export, 'content_type', ''), 'driveid': Utils.get_safe_value(export, 'driveid', ''), 'item_id': export['id']}
        KodiUtils.run_plugin(self.addonid, params, False)
    
    def process_watch(self, export_map):
        exports = Utils.get_safe_value(export_map, 'watch', [])
        update_library = {}
        changes_by_drive = {}
        for export in exports:
            item_id = export['id']
            driveid = export['driveid']
            if driveid in changes_by_drive:
                changes = changes_by_drive[driveid]
            else:
                self.provider.configure(self._account_manager, export['driveid'])
                changes = self.provider.changes()
                changes_by_drive[driveid] = changes
            items_info = self.export_manager.get_items_info(item_id)
            if items_info:
                if changes and not Utils.get_safe_value(export, 'exporting', False):
                    Logger.debug('*** Processing changes for export "%s" in %s' % (export['name'], export['destination_folder']))
                    while True:
                        changes_retry = []
                        changes_done = []
                        for change in changes:
                            change_type = self.process_change(change, items_info, export)
                            if change_type and change_type != 'retry':
                                changes_done.append(change)
                                self.export_manager.save_items_info(item_id, items_info)
                                if Utils.get_safe_value(export, 'update_library', False):
                                    update_library[Utils.get_safe_value(export, 'content_type', 'None')] = True
                            elif change_type and change_type == 'retry':
                                changes_retry.append(change)
                        for change in changes_done:
                            changes_by_drive[driveid].remove(change)
                        if changes_done and changes_retry:
                            changes = changes_retry
                            Logger.debug('Retrying pending changes...')
                        else:
                            break
            else:
                self.run_export(export)
        if update_library:
            if Utils.get_safe_value(update_library, 'video', False):
                KodiUtils.update_library('video')
            if Utils.get_safe_value(update_library, 'audio', False):
                KodiUtils.update_library('music')
    
    def process_change_delete(self, items_info, item_id, is_folder):
        change_type = 'delete'
        item_info = items_info[item_id]
        item_info_path = item_info['full_local_path']
        if KodiUtils.file_exists(item_info_path):
            if is_folder:
                Logger.debug('Change is delete folder: %s' % item_info_path)
                if not Utils.remove_folder(item_info_path, self._system_monitor):
                    change_type = 'retry'
            else:
                Logger.debug('Change is delete file')
                if not KodiUtils.file_delete(item_info_path):
                    change_type = 'retry'
        if change_type != 'retry':
            ExportManager.remove_item_info(items_info, item_id)
        return change_type
    
    def process_change(self, change, items_info, export):
        change_type = None
        changed_item_id = change['id']
        Logger.debug('Change: %s' % Utils.str(change))
        if changed_item_id != export['id']:
            changed_item_name = Utils.get_safe_value(change,'name','')
            deleted = Utils.get_safe_value(change, 'removed')
            parent_id = Utils.get_safe_value(change,'parent','')
            if changed_item_id in items_info:
                item_info = items_info[changed_item_id]
                item_type = item_info['type']
                is_folder = item_type == 'folder'
                Logger.debug('item_info: %s' % Utils.str(item_info))
                item_info_path = item_info['full_local_path']
                if KodiUtils.file_exists(item_info_path):
                    if deleted:
                        change_type = self.process_change_delete(items_info, changed_item_id, is_folder)
                    elif parent_id != item_info['parent'] or changed_item_name != item_info['name']:
                        if parent_id in items_info:
                            change_type = 'move'
                            Logger.debug('Change is move')
                            parent_item_info = items_info[parent_id]
                            parent_item_path = parent_item_info['full_local_path']
                            new_path = os.path.join(parent_item_path, Utils.unicode(changed_item_name))
                            if is_folder:
                                new_path = os.path.join(new_path, '')
                            if KodiUtils.file_rename(item_info_path, new_path):
                                ExportManager.remove_item_info(items_info, changed_item_id)
                                ExportManager.add_item_info(items_info, changed_item_id, Utils.unicode(changed_item_name), new_path, parent_id,item_type)
                            else:
                                change_type = 'retry'
                        else:
                            Logger.debug('Change is move but parent not in item list. Change is delete')
                            change_type = self.process_change_delete(items_info, changed_item_id, is_folder)
                else:
                    Logger.debug('Invalid state. Changed item not found: %s. Deleting from item list.' % item_info_path)
                    change_type = self.process_change_delete(items_info, changed_item_id, is_folder)
            elif parent_id in items_info and not deleted:
                is_folder = 'application/vnd.google-apps.folder' in change.get('mimetype')
                content_type = export['content_type']
                item_name_extension = change['name_extension']
                is_stream_file = (('video' in change or item_name_extension in self._video_file_extensions) and content_type == 'video') or ('audio' in change and content_type == 'audio')
                item_type = 'folder' if is_folder else 'file'
                if is_folder or is_stream_file or (export['nfo_export'] and ('nfo' in item_name_extension or 'text/x-nfo' in change.get("mimetype"))):
                    change_type = 'add'
                    Logger.debug('Change is new item')
                    parent_item_info = items_info[parent_id]
                    parent_item_path = parent_item_info['full_local_path']
                    new_path = os.path.join(parent_item_path, Utils.unicode(changed_item_name))
                    if is_folder:
                        new_path = os.path.join(new_path, '')
                        if not KodiUtils.mkdirs(new_path):
                            change_type = 'retry'
                    elif is_stream_file:
                        new_path += '.strm'
                        ExportManager.create_strm(export['driveid'], change, new_path, content_type, 'plugin://%s/' % self.addonid)
                    else:
                        ExportManager.create_nfo(changed_item_id, export['item_driveid'], new_path, self.provider)
                    if change_type != 'retry':
                        ExportManager.add_item_info(items_info, changed_item_id, Utils.unicode(changed_item_name), new_path, parent_id, item_type)
        Logger.debug('change type: %s ' % Utils.str(change_type))
        return change_type
    
    def stop(self):
        self.abort = True
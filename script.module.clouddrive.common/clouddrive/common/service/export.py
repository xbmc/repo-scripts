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
from clouddrive.common.utils import Utils, timeit
from clouddrive.common.ui.dialog import ExportScheduleDialog, DialogProgressBG
from calendar import weekday
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.export import ExportManager
from clouddrive.common.account import AccountManager
from _collections import deque
import os

class ExportService(object):
    name = 'export'

    def __init__(self, provider_class):
        self.abort = False
        self._system_monitor = KodiUtils.get_system_monitor()
        self.provider = provider_class()
        self.addonid = KodiUtils.get_addon_info('id')
        self._addon_name = KodiUtils.get_addon_info('name')
        self._common_addon_id = 'script.module.clouddrive.common'
        self._common_addon = KodiUtils.get_addon(self._common_addon_id)
        self._profile_path = Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info('profile')))
        self._startup_type = Utils.str(ExportScheduleDialog._startup_type)
        self.export_manager = ExportManager(self._profile_path)
        self._account_manager = AccountManager(self._profile_path)
        self._video_file_extensions = [x for x in KodiUtils.get_supported_media("video") if x not in ('','zip')]
        self._audio_file_extensions = KodiUtils.get_supported_media("music")
        self._artwork_file_extensions = ['back', 'banner', 'characterart', 'clearart', 'clearlogo', 'discart', 'fanart', 'keyart', 'landscape', 'poster', 'spine', 'thumb', 'folder', 'cover', 'animatedposter', 'animatedfanart']
        self._export_progress_dialog_bg = DialogProgressBG(self._addon_name)
    
    def __del__(self):
        del self._system_monitor
        del self.export_manager
        del self._account_manager
        del self._common_addon
        del self._export_progress_dialog_bg
        
    def cleanup_export_map(self):
        exports = self.export_manager.get_exports()
        for exportid in exports:
            export = exports[exportid]
            export['exporting'] = False
            self.export_manager.save_export(export)
    
    def get_scheduled_export_map(self):
        exports = self.export_manager.get_exports()
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
                key = 'run_immediately'
                if Utils.get_safe_value(export, key, False):
                    export_map[key] = Utils.get_safe_value(export_map, key, [])
                    export_map[key].append(export)
                    export[key] = False
                    self.export_manager.save_export(export)
                    
        Logger.debug('scheduled export_map: %s' % Utils.str(export_map))
        return export_map
        
    def start(self):
        Logger.notice('Service \'%s\' started.' % self.name)
        self.cleanup_export_map()
        monitor = KodiUtils.get_system_monitor()
        startup = True
        while not self.abort:
            try:
                now = datetime.datetime.now()
                export_map = self.get_scheduled_export_map()
                if export_map:
                    self.process_schedules(export_map, now, startup)
                self.process_watch()
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
            key = 'run_immediately'
            run_immediately_list = Utils.get_safe_value(export_map, key, [])
            export_list.extend(run_immediately_list)
            
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
    
    def _get_progress_header(self, export):
        sid = 32024
        if Utils.get_safe_value(export, 'origin', '') == 'watch':
            sid = 32088
        return self._common_addon.getLocalizedString(sid) + ': ' + Utils.unicode(export['name'])
    
    def _get_percent(self, completed, target):
        if target > 0:
            return completed * 100 / target
        return 0
    
    def _show_progress_before_change(self, change, pending_changes, changes_done, retry_changes, ignored, export):
        completed = len(changes_done) + len(retry_changes) + ignored
        target = len(pending_changes) + completed + 1
        self._export_progress_dialog_bg.update(self._get_percent(completed, target), self._addon_name + ' ' + self._get_progress_header(export), Utils.get_safe_value(change,'name','n/a'))

    def _show_progress_after_change(self, change, change_type, pending_changes, changes_done, retry_changes, ignored, export):
        completed = len(changes_done) + len(retry_changes) + ignored
        target = len(pending_changes) + completed
        msg = self._common_addon.getLocalizedString(32041)
        if change_type:
            msg = Utils.get_safe_value(change,'name','n/a')
        self._export_progress_dialog_bg.update(self._get_percent(completed, target), self._addon_name + ' ' + self._get_progress_header(export), msg)
    
    def run_export(self, export):
        exporting = Utils.get_safe_value(export, 'exporting', False)
        Logger.debug('Run export requested. Exporting = %s' % (exporting,))
        if not exporting:
            export['exporting'] = True
            export['origin'] = 'schedule'
            self.export_manager.save_export(export)
            try:
                show_export_progress = KodiUtils.get_addon_setting('hide_export_progress') != 'true'
                if show_export_progress:
                    self._export_progress_dialog_bg.create(self._addon_name + ' ' + self._common_addon.getLocalizedString(32024), self._common_addon.getLocalizedString(32025))
                export_folder = export['destination_folder']
                if not KodiUtils.file_exists(export_folder):
                    Logger.debug('creating folder: %s' % (export_folder,))
                    if not KodiUtils.mkdirs(export_folder):
                        Logger.debug('unable to create folder %s' % (export_folder,))
                if KodiUtils.file_exists(export_folder):
                    driveid = export['driveid']
                    self.provider.configure(self._account_manager, driveid)
                    exportid = export['id']
                    items_info = {}
                    ExportManager.add_item_info(items_info, 'root-folder', None, export_folder, None, 'folder')
                    self.export_manager.save_items_info(exportid, items_info)
                    item = self.provider.get_item(export['item_driveid'], exportid)
                    item.update({
                        'parent': 'root-folder',
                        'origin': 'schedule'
                    })
                    self.export_manager.save_pending_changes(exportid, deque([item]))
                    self.export_manager.save_retry_changes(exportid, deque([]))
                    if show_export_progress:
                        progress_listener = self._show_progress_before_change
                    else:
                        progress_listener = None
                    changes_done = self.process_pending_changes(exportid, on_before_change = progress_listener)
                    if changes_done:
                        if Utils.get_safe_value(export, 'update_library', False):
                            if Utils.get_safe_value(export, 'content_type', '') == 'audio':
                                KodiUtils.update_library('music')
                            else:
                                KodiUtils.update_library('video')
                            
            except Exception as e:
                ErrorReport.handle_exception(e)
                KodiUtils.show_notification(self._common_addon.getLocalizedString(32027) + ' ' + Utils.unicode(e))
            finally:
                export['exporting'] = False
                del export['origin']
                self.export_manager.save_export(export)
                self._export_progress_dialog_bg.close()
        else:
            KodiUtils.show_notification(self._common_addon.getLocalizedString(32059) + ' ' + self._common_addon.getLocalizedString(32038))
    
    def get_folder_changes(self, driveid, folder, on_before_add_item=None):
        return self.provider.get_folder_items(Utils.default(Utils.get_safe_value(folder, 'drive_id'), driveid), folder['id'], include_download_info=True, on_before_add_item=on_before_add_item)
    
    def on_before_add_item(self, export, item):
        item['origin'] = Utils.get_safe_value(export, 'origin', '')
        
    def process_pending_changes(self, exportid, on_after_change = None, on_before_change = None):
        changes_done = []
        pending_changes = self.export_manager.get_pending_changes(exportid)
        if pending_changes:
            export = self.export_manager.get_exports()[exportid]
            Logger.debug('*** Processing all changes for export id: %s' % exportid)
            try:
                Logger.debug('    Exporting "%s" in %s' % (Utils.unicode(export['name']), Utils.unicode(export['destination_folder'])))
            except Exception:
                Logger.debug('    Export name: %s' % Utils.str(export['name']))
                Logger.debug('    Export destination_folder: %s' % Utils.str(export['destination_folder']))
            items_info = Utils.default(self.export_manager.get_items_info(exportid), {})
            retry_changes = []
            processed_changes = set()
            ignored = 0
            while len(pending_changes) > 0:
                change = pending_changes.popleft()
                change_id = change['id']
                if change_id in processed_changes:
                    continue
                processed_changes.add(change_id)
                if on_before_change:
                    on_before_change(change, pending_changes, changes_done, retry_changes, ignored, export)
                
                change_type = self.process_change(change, items_info, export)
                self.export_manager.save_items_info(exportid, items_info)
                self.export_manager.save_pending_changes(exportid, pending_changes)
                is_retry = False
                if change_type:
                    if change_type[-6:] == "_retry":
                        is_retry = True
                        retry_changes.append(change)
                        Logger.debug('change marked for retry')
                    else:
                        changes_done.append(change)
                        if change_type == 'create_folder' or (change_type == 'create_folder_ignored' and Utils.get_safe_value(change, 'origin', '') == 'schedule'):
                            before_add_item = lambda item: self.on_before_add_item(change, item)
                            pending_changes.extendleft(self.get_folder_changes(export['driveid'], change, before_add_item))
                            self.export_manager.save_pending_changes(exportid, pending_changes)
                else:
                    ignored += 1
                if on_after_change:
                    on_after_change(change, change_type, pending_changes, changes_done, retry_changes, ignored, export)
                if is_retry:
                    self.export_manager.save_retry_changes(exportid, deque(retry_changes))
        return changes_done
    
    def process_watch(self):
        exports = self.export_manager.get_exports()
        update_library = {}
        changes_by_drive = {}
        for exportid in exports:
            export = exports[exportid]
            watch = Utils.get_safe_value(export, 'watch', False)
            exporting = Utils.get_safe_value(export, 'exporting', False)
            retry_changes = self.export_manager.get_retry_changes(exportid)
            if (watch or len(retry_changes) > 0) and not exporting:
                items_info = self.export_manager.get_items_info(exportid)
                if items_info:
                    export['exporting'] = True
                    export['origin'] = 'watch'
                    self.export_manager.save_export(export)
                    try:
                        driveid = export['driveid']
                        if driveid in changes_by_drive:
                            changes = changes_by_drive[driveid]
                        else:
                            self.provider.configure(self._account_manager, export['driveid'])
                            changes = self.provider.changes()
                            changes_by_drive[driveid] = []
                            changes_by_drive[driveid].extend(changes)
                        pending_changes = self.export_manager.get_pending_changes(exportid)
                        pending_changes.extend(retry_changes)
                        pending_changes.extend(changes)
                        if len(changes) > 0 or len(retry_changes) > 0:
                            self.export_manager.save_pending_changes(exportid, pending_changes)
                        if len(retry_changes) > 0:
                            self.export_manager.save_retry_changes(exportid, deque([]))
                        show_export_progress = KodiUtils.get_addon_setting('hide_export_progress') != 'true'
                        if pending_changes and show_export_progress:
                            self._export_progress_dialog_bg.update(0, self._addon_name + ' ' + self._common_addon.getLocalizedString(32088), self._common_addon.getLocalizedString(32025))
                        if show_export_progress:
                            progress_listener = self._show_progress_after_change
                        else:
                            progress_listener = None
                        changes_done = self.process_pending_changes(exportid, on_after_change = progress_listener)
                        if changes_done:
                            if Utils.get_safe_value(export, 'update_library', False):
                                update_library[Utils.get_safe_value(export, 'content_type', 'None')] = True
                        for change in changes_done:
                            if change in changes_by_drive[driveid]:
                                changes_by_drive[driveid].remove(change)
                    except Exception as e:
                        ErrorReport.handle_exception(e)
                        KodiUtils.show_notification(self._common_addon.getLocalizedString(32027) + ' ' + Utils.unicode(e))
                    finally:
                        export['exporting'] = False
                        del export['origin']
                        self.export_manager.save_export(export)
                else:
                    self.run_export(export)
        self._export_progress_dialog_bg.close()
        if update_library:
            if Utils.get_safe_value(update_library, 'video', False):
                KodiUtils.update_library('video')
            if Utils.get_safe_value(update_library, 'audio', False):
                KodiUtils.update_library('music')
    
    @timeit
    def process_change(self, change, items_info, export):
        change_type = None
        changed_item_id = change['id']
        Logger.debug('change_object: %s' % Utils.str(change))
        changed_item_name = Utils.get_safe_value(change,'name','')
        deleted = Utils.get_safe_value(change, 'deleted') or Utils.get_safe_value(change, 'removed')
        parent_id = Utils.get_safe_value(change,'parent','')
        if changed_item_id in items_info:
            item_info = items_info[changed_item_id]
            item_info_path = item_info['full_local_path']
            if KodiUtils.file_exists(item_info_path):
                if deleted:
                    change_type = self.process_change_delete(change, items_info)
                elif parent_id != item_info['parent'] or changed_item_name != item_info['name']:
                    if parent_id in items_info:
                        change_type = self.process_change_move(change, items_info)
                    elif changed_item_id != export['id']:
                        Logger.debug('change is move to a parent not in item list. deleting from current export info and ignoring (could be moved to another export info)')
                        self.process_change_delete(change, items_info)
                else:
                    change_type = self.process_change_create(change, items_info, export)
            elif not deleted:
                Logger.debug('changed item not found in its location: %s. creating...' % item_info_path)
                change_type = self.process_change_create(change, items_info, export)
        elif parent_id in items_info and not deleted:
            change_type = self.process_change_create(change, items_info, export)
        Logger.debug('change_type: %s ' % Utils.str(change_type))
        return change_type
    
    def process_change_delete(self, change, items_info):
        change_type = 'delete'
        changed_item_id = change['id']
        item_info = items_info[changed_item_id]
        item_info_path = item_info['full_local_path']
        item_type = item_info['type']
        is_folder = item_type == 'folder'
        Logger.debug('deleting: %s' % item_info_path)
        if KodiUtils.file_exists(item_info_path):
            if is_folder:
                change_type += '_folder'
                if not Utils.remove_folder(item_info_path, self._system_monitor):
                    change_type += '_retry'
            else:
                change_type += '_file'
                if not KodiUtils.file_delete(item_info_path):
                    change_type += '_retry'
        else:
            Logger.debug('file already deleted: %s' % item_info_path)
            change_type +='_ignored'
        ExportManager.remove_item_info(items_info, changed_item_id)
        return change_type
    
    def process_change_move(self, change, items_info):
        change_type = 'move'
        parent_id = Utils.get_safe_value(change,'parent','')
        parent_item_info = items_info[parent_id]
        parent_item_path = parent_item_info['full_local_path']
        changed_item_id = change['id']
        changed_item_name = Utils.get_safe_value(change,'name','')
        changed_item_extension = Utils.get_safe_value(change,'name_extension','')
        changed_item_mimetype = Utils.get_safe_value(change,'mimetype','')
        item_info = items_info[changed_item_id]
        item_type = item_info['type']
        is_folder = item_type == 'folder'
        item_info_path = item_info['full_local_path']
        new_path = os.path.join(Utils.unicode(parent_item_path), Utils.unicode(changed_item_name))
        if is_folder:
            change_type += '_folder'
            new_path = os.path.join(new_path, '')
        else:
            change_type += '_file'
            if changed_item_extension in self._video_file_extensions or 'video' in changed_item_mimetype or 'video' in change:
                new_path +='.strm'
        Logger.debug('%s from: %s to: %s' % (change_type, item_info_path,new_path,))
        if KodiUtils.file_exists(new_path):
            Logger.debug('location already exists: %s. removing...' % (new_path,))
            if is_folder:
                Utils.remove_folder(item_info_path, self._system_monitor)
            else:
                KodiUtils.file_delete(item_info_path)
        if not KodiUtils.file_rename(item_info_path, new_path):
            change_type += '_retry'
        ExportManager.add_item_info(items_info, changed_item_id, Utils.unicode(changed_item_name), new_path, parent_id, item_type)
        return change_type
    
    def process_change_create(self, change, items_info, export):
        content_type = export['content_type']
        changed_item_id = change['id']
        changed_item_name = Utils.get_safe_value(change,'name','')
        changed_item_extension = Utils.get_safe_value(change,'name_extension','')
        parent_id = Utils.get_safe_value(change,'parent','')
        is_folder = 'folder' in change
        item_type = 'folder' if is_folder else 'file'
        parent_item_info = Utils.get_safe_value(items_info,parent_id)
        if parent_item_info:
            parent_item_path = parent_item_info['full_local_path']
            new_path = os.path.join(Utils.unicode(parent_item_path), Utils.unicode(changed_item_name))
            change_type = 'create'
            if is_folder:
                change_type += '_folder'
                new_path = os.path.join(new_path, '')
                if parent_id == 'root-folder' and KodiUtils.get_addon_setting('clean_folder') == 'true' and KodiUtils.file_exists(new_path):
                    if not Utils.remove_folder(new_path):
                        error = self._common_addon.getLocalizedString(32066) % new_path
                        KodiUtils.show_notification(error)
                        Logger.debug(error)
                if not KodiUtils.file_exists(new_path):
                    Logger.debug('creating folder: %s' % (new_path,))
                    if not KodiUtils.mkdir(new_path):
                        change_type += '_retry'
                        Logger.debug('unable to create folder %s' % (new_path,))
                else:
                    change_type +='_ignored'
                    Logger.debug('folder %s already exists' % (new_path,))
            else:
                download_artwork = 'download_artwork' in export and export['download_artwork']
                is_download = changed_item_extension \
                              and (
                                  changed_item_extension in ['strm', 'nomedia']
                                  or (
                                      download_artwork 
                                      and (
                                          changed_item_extension in ['nfo']
                                          or (
                                              changed_item_extension in ['jpg', 'png']
                                              and (
                                                  any(s in changed_item_name for s in self._artwork_file_extensions)
                                                  or parent_item_info['name'] in ['.actors', 'extrafanart']
                                              )
                                          ) 
                                      )
                                  )
                              )
                if is_download:
                    Logger.debug('downloading file: %s' % (new_path,))
                    change_type = 'download_file'
                    cloud_size = Utils.get_safe_value(change, 'size', 0)
                    local_size = KodiUtils.file(new_path).size()
                    if cloud_size != local_size:
                        Logger.debug('Download requested. File changed: Local file size (%s) - cloud file size (%s)' % (Utils.str(local_size), Utils.str(cloud_size),))
                        if not ExportManager.download(change, new_path, self.provider):
                            change_type += "_retry"
                            Logger.debug('Unable to download file: %s' % (new_path,))
                    else:
                        change_type +='_ignored'
                        Logger.debug('Download ignored: Local file size (%s) is equal to cloud file size (%s)' % (Utils.str(local_size), Utils.str(cloud_size),))
                else:
                    is_stream_file = (('video' in change or (changed_item_extension and changed_item_extension in self._video_file_extensions)) and content_type == 'video') \
                                     or (('audio' in change or (changed_item_extension and changed_item_extension in self._audio_file_extensions)) and content_type == 'audio')
                    if is_stream_file:
                        change_type += '_file'
                        if KodiUtils.get_addon_setting('no_extension_strm') == 'true':
                            new_path = Utils.remove_extension(new_path)
                        new_path += ExportManager._strm_extension
                        strm_content = ExportManager.get_strm_link(export['driveid'], change, content_type, 'plugin://%s/' % self.addonid)
                        Logger.debug('creating strm file: %s' % (new_path,))
                        if not KodiUtils.file_exists(new_path) or KodiUtils.file(new_path).size() != len(strm_content):
                            if not ExportManager.create_text_file(new_path, strm_content):
                                change_type += '_retry'
                        else:
                            change_type +='_ignored'
                            Logger.debug('ignoring strm creation: %s, strm file already exists. same expected size.' % (new_path,))
                    else:
                        change_type = None
                        Logger.debug('ignoring file: %s' % (new_path,))
            if change_type:
                ExportManager.add_item_info(items_info, changed_item_id, Utils.unicode(changed_item_name), new_path, parent_id, item_type)
        else:
            Logger.debug('invalid state. no parent info found')
            change_type = None
        return change_type
        
    def stop(self):
        self.abort = True
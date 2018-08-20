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

import xbmcgui, xbmcvfs
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
import os
from clouddrive.common.ui.logger import Logger
from clouddrive.common.account import AccountManager
from clouddrive.common.export import ExportManager
import urllib

class DialogProgressBG (xbmcgui.DialogProgressBG):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
                 
    def create(self, heading, message=None):
        if self.created:
            self.update(heading=heading, message=message)
        else:
            super(DialogProgressBG, self).create(heading, message)
            self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgressBG, self).close()
            self.created = False
    
    def update(self, percent=0, heading=None, message=None):
        if not self.created:
            if not heading: heading = self._default_heading
            self.create(heading=heading, message=message)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgressBG, self).update(percent=percent, heading=heading, message=message)
    
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
    
class DialogProgress (xbmcgui.DialogProgress):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
        
    def create(self, heading, line1="", line2="", line3=""):
        if self.created:
            self.close()
            
        super(DialogProgress, self).create(heading, line1, line2, line3)
        self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgress, self).close()
            self.created = False
    
    def update(self, percent, line1="", line2="", line3=""):
        if not self.created:
            self.create(self._default_heading, line1, line2, line3)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgress, self).update(percent, line1, line2, line3)
        
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
        
        
class QRDialogProgress(xbmcgui.WindowXMLDialog):
    _heading_control = 1000
    _qr_control = 1001
    _text_control = 1002
    _cancel_btn_control = 1003
    def __init__(self, *args, **kwargs):
        self.heading = kwargs["heading"]
        self.qr_code = kwargs["qr_code"]
        self.line1 = kwargs["line1"]
        self.line2 = kwargs["line2"]
        self.line3 = kwargs["line3"]
        self.percent = 0
        self._image_path = None
        self.canceled = False

    def __del__(self):
        xbmcvfs.delete(self._image_path)
        pass
    
    @staticmethod
    def create(heading, qr_code, line1="", line2="", line3=""):
        return QRDialogProgress("pin-dialog.xml", KodiUtils.get_common_addon_path(), "default", heading=heading, qr_code=qr_code, line1=line1, line2=line2, line3=line3)
    
    def iscanceled(self):
        return self.canceled
    
    def onInit(self):
        import pyqrcode
        self._image_path = os.path.join(Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info("profile", "script.module.clouddrive.common"))),"qr.png")
        qrcode = pyqrcode.create(self.qr_code)
        qrcode.png(self._image_path, scale=10)
        del qrcode
        self.getControl(self._heading_control).setLabel(self.heading)
        self.getControl(self._qr_control).setImage(self._image_path)
        self.update(self.percent, self.line1, self.line2, self.line3)

    def update(self, percent, line1="", line2="", line3=""):
        self.percent = percent
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        if line1:
            self.line1 = line1
        if line2:
            self.line2 = line2
        if line3:
            self.line3 = line3
        text = self.line1
        if self.line2:
            text = text + "[CR]" + self.line2
        if self.line3:
            text = text + "[CR]" + self.line3   
        self.getControl(self._text_control).setText(text)
        self.setFocus(self.getControl(self._cancel_btn_control))
    
    def onClick(self, control_id):
        if control_id == self._cancel_btn_control:
            self.canceled = True
            self.close()
    
    def onAction(self, action):
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            self.canceled = True
        super(QRDialogProgress, self).onAction(action)
        
class ExportScheduleDialog(xbmcgui.WindowXMLDialog):
    _daily_type = 32082
    _startup_type = 32081
    
    def __init__(self, *args, **kwargs):
        self._common_addon = KodiUtils.get_common_addon()
        self._dialog = xbmcgui.Dialog()
        self.canceled = False
        self._schedule_types = [ExportScheduleDialog._startup_type,self._daily_type,17,11,12,13,14,15,16]
        self._schedule_ats = []
        for hour in range(0,24):
            self._schedule_ats.append('%02d:00' % hour)
        self.schedule = Utils.default(kwargs["schedule"], {'type': self._daily_type, 'at' : self._schedule_ats[0]})
        
    def __del__(self):
        del self._common_addon
        del self._dialog

    @staticmethod
    def create(schedule=None):
        return ExportScheduleDialog("export-schedule-dialog.xml", KodiUtils.get_common_addon_path(), "default", schedule=schedule)
    
    def iscanceled(self):
        return self.canceled
    
    def onInit(self):
        self.title_label = self.getControl(1000)
        self.cancel_button = self.getControl(1002)
        self.save_button = self.getControl(1003)
        self.schedule_type_button = self.getControl(1011)
        self.schedule_at_label = self.getControl(10100)
        self.schedule_at_button = self.getControl(1012)
        self.title_label.setLabel(self._common_addon.getLocalizedString(32083))
        self.setFocus(self.save_button)
        self.setFocus(self.schedule_type_button)
        self.schedule_type_button.setLabel(KodiUtils.localize(self.schedule['type'], addon=self._common_addon))
        self.schedule_at_button.setLabel(self.schedule['at']) 
        self.schedule_at_label.setLabel(KodiUtils.localize(32080, addon=self._common_addon))
        self.check_schedule_type()
    
    def check_schedule_type(self):
        visible = self.schedule['type'] != self._startup_type
        self.at_visible(visible)
        if not visible:
            self.schedule['at'] = self._schedule_ats[0]
            self.schedule_at_button.setLabel(self.schedule['at']) 
            
    def at_visible(self, visible):
        self.schedule_at_label.setVisible(visible)
        self.schedule_at_button.setVisible(visible)
        
    def onClick(self, control_id):
        if control_id == self.cancel_button.getId():
            self.canceled = True
            self.close()
        elif control_id == self.schedule_type_button.getId():
            options = []
            preselect = self._schedule_types.index(self.schedule['type'])
            for schedule_type in self._schedule_types:
                options.append(KodiUtils.localize(schedule_type, addon=self._common_addon))
            title = KodiUtils.localize(32079, addon=self._common_addon) + '...'
            self.schedule['type'] = self._schedule_types[self._dialog.select(title, options, preselect=preselect)]
            self.schedule_type_button.setLabel(KodiUtils.localize(self.schedule['type'], addon=self._common_addon))
            self.check_schedule_type() 
        elif control_id == self.schedule_at_button.getId():
            title = KodiUtils.localize(32079, addon=self._common_addon) + ' ' + KodiUtils.localize(self.schedule['type'], addon=self._common_addon) + ' ' + KodiUtils.localize(32080, addon=self._common_addon) + '...'
            self.schedule['at'] = self._schedule_ats[self._dialog.select(title, self._schedule_ats, preselect=self._schedule_ats.index(self.schedule['at']))]
            self.schedule_at_button.setLabel(self.schedule['at']) 
        elif control_id == self.save_button.getId():
            self.close()
            
    
    def onAction(self, action):
        
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            self.canceled = True
        super(ExportScheduleDialog, self).onAction(action)
        
class ExportMainDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.content_type = urllib.unquote(kwargs["content_type"])
        self.driveid = kwargs["driveid"]
        self.item_driveid = kwargs["item_driveid"]
        self.item_id = kwargs["item_id"]
        self.name = urllib.unquote(kwargs["name"])
        self.account_manager = kwargs["account_manager"]
        self.provider = kwargs["provider"]
        self.provider.configure(self.account_manager, self.driveid)
        self.export_manager = ExportManager(self.account_manager._addon_data_path)
        self._addon_name = KodiUtils.get_addon_info('name')
        self._common_addon = KodiUtils.get_common_addon()
        self._dialog = xbmcgui.Dialog()
        self.editing = False
        self.canceled = False
        self.run = False
        self.schedules = []
        
    def __del__(self):
        del self._common_addon
        del self._dialog

    @staticmethod
    def create(content_type, driveid, item_driveid, item_id, name, account_manager, provider):
        return ExportMainDialog("export-main-dialog.xml", KodiUtils.get_common_addon_path(), "default", content_type=content_type, driveid=driveid, item_driveid=item_driveid, item_id=item_id, name=name, account_manager=account_manager, provider=provider)
    
    def iscanceled(self):
        return self.canceled
    
    def onInit(self):
        self.title_label = self.getControl(1000)
        self.cancel_button = self.getControl(999)
        self.save_button = self.getControl(1001)
        self.save_export_button = self.getControl(1002)
        
        self.drive_name_label = self.getControl(1003)
        self.drive_folder_label = self.getControl(1004)
        self.dest_folder_label = self.getControl(1005)
        self.dest_folder_button = self.getControl(1006)
        
        self.update_library_sw = self.getControl(1007)
        self.watch_drive_sw = self.getControl(1008)
        self.schedule_sw = self.getControl(1009)
        
        self.schedule_label = self.getControl(10100)
        self.schedule_list = self.getControl(1010)
        self.add_schedule_button = self.getControl(1011)
        self.setFocus(self.dest_folder_button)
        
        self.schedule_label.setLabel(self._common_addon.getLocalizedString(32083))
        
        self.title_label.setLabel(self._addon_name + ' - ' + self._common_addon.getLocalizedString(32004))
        self.account_manager.load()
        account = self.account_manager.get_account_by_driveid(self.driveid)
        drive = self.account_manager.get_drive_by_driveid(self.driveid)
        drive_name = self.account_manager.get_account_display_name(account, drive, self.provider, True)
        self.drive_name_label.setLabel(drive_name)
        self.drive_folder_label.setLabel(self.name)
        
        exports = self.export_manager.load()
        export = Utils.get_safe_value(exports, self.item_id, {})
        if export:
            self.editing = True
            self.watch_drive_sw.setSelected(Utils.get_safe_value(export, 'watch', False))
            self.schedule_sw.setSelected(Utils.get_safe_value(export, 'schedule', False))
            self.update_library_sw.setSelected(Utils.get_safe_value(export, 'update_library', False))
            self.schedules = Utils.get_safe_value(export, 'schedules', [])
            for schedule in self.schedules:
                self.add_schedule_item(schedule)
        
        if not self.editing:
            self.select_detination()
        else:
            self.dest_folder_label.setLabel(Utils.get_safe_value(export, 'destination_folder', ''))
        self.schedule_enabled(self.schedule_sw.isSelected())
        
    def is_valid_export(self):
        if not self.dest_folder_label.getLabel():
            self._dialog.ok(self._addon_name, KodiUtils.localize(32084,addon=self._common_addon) % KodiUtils.localize(32085,addon=self._common_addon))
            return False
        return True
    
    def save_export(self):
        self.export_manager.add_export({
            'id': self.item_id,
            'item_driveid': self.item_driveid,
            'driveid': self.driveid,
            'name': self.name,
            'content_type': self.content_type,
            'destination_folder': self.dest_folder_label.getLabel(),
            'watch': self.watch_drive_sw.isSelected(),
            'schedule': self.schedule_sw.isSelected(),
            'update_library': self.update_library_sw.isSelected(),
            'schedules': self.schedules
        })
    
    def schedule_enabled(self, enabled):
        self.schedule_label.setEnabled(enabled)
        self.schedule_list.setEnabled(enabled)
        self.add_schedule_button.setEnabled(enabled)
    
    def select_detination(self, default=''):
        dest_folder = self._dialog.browse(0, self._common_addon.getLocalizedString(32002), 'files', defaultt=default)
        self.dest_folder_label.setLabel(dest_folder)
            
    def add_schedule_item(self, schedule):
        list_item = xbmcgui.ListItem(self.get_schedule_statement(schedule))
        self.schedule_list.addItem(list_item)
        
    def get_schedule_statement(self, schedule):
        statement = self._common_addon.getLocalizedString(32079) + ' ' + KodiUtils.localize(schedule['type'], addon=self._common_addon)
        if schedule['type'] != ExportScheduleDialog._startup_type:
            statement = statement + ' ' + self._common_addon.getLocalizedString(32080) + ' ' + schedule['at']
        return statement
    
    def edit_selected_schedule(self):
        schedule = None
        editing = -1
        if self.getFocusId() == self.schedule_list.getId():
            editing = self.schedule_list.getSelectedPosition()
            schedule = self.schedules[editing]
        schedule_dialog = ExportScheduleDialog.create(schedule)
        schedule_dialog.doModal()
        if not schedule_dialog.iscanceled():
            valid = True
            if editing >= 0:
                schedule = schedule_dialog.schedule
                self.schedules[editing] = schedule
                self.schedule_list.getListItem(editing).setLabel(self.get_schedule_statement(schedule))
            else:
                for schedule in self.schedules:
                    if schedule['type'] == schedule_dialog.schedule['type'] and schedule['at'] == schedule_dialog.schedule['at']:
                        valid = False
                        break
                if valid:
                    self.schedules.append(schedule_dialog.schedule)
                    self.add_schedule_item(schedule_dialog.schedule)
    
    def delete_selected_schedule(self):
        if self.getFocusId() == self.schedule_list.getId():
            index = self.schedule_list.getSelectedPosition()
            self.schedule_list.removeItem(index)
            self.schedules.remove(self.schedules[index])
    
    def onClick(self, control_id):
        if control_id == self.cancel_button.getId():
            self.canceled = True
            self.close()
        elif control_id == self.save_button.getId() or control_id == self.save_export_button.getId():
            if self.is_valid_export():
                self.save_export()
                self.run = control_id == self.save_export_button.getId()
                self.close()
                
        elif control_id == self.dest_folder_button.getId():
            self.select_detination(self.dest_folder_label.getLabel())
        elif control_id == self.schedule_sw.getId():
            self.schedule_enabled(self.schedule_sw.isSelected())
        elif control_id == self.schedule_list.getId() or control_id == self.add_schedule_button.getId():
            self.edit_selected_schedule()
    
    def onAction(self, action):
        
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            self.canceled = True
        elif action.getId() == xbmcgui.ACTION_CONTEXT_MENU:
            if self.getFocusId() == self.schedule_list.getId():
                index = self._dialog.contextmenu(['Edit...', 'Delete'])
                if index == 0:
                    self.edit_selected_schedule()
                elif index == 1:
                    self.delete_selected_schedule()
        super(ExportMainDialog, self).onAction(action)
        


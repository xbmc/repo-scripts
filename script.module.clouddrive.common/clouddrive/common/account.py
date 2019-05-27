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


class AccountManager(object):
    accounts = {}
    _addon_data_path = None
    _config_file_name = 'accounts.cfg'
    _config_path = None
    
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
        self.accounts = {}
        if os.path.exists(self._config_path):
            with KodiUtils.lock:
                with open(self._config_path, 'rb') as fo:
                    self.accounts = json.loads(fo.read())
        return self.accounts
    
    def add_account(self, account):
        self.load()
        self.accounts[account['id']] = account
        self.save()
    
    def get_account_by_driveid(self, driveid):
        for accountid in self.accounts:
            for drive in self.accounts[accountid]['drives']:
                if drive['id'] == driveid:
                    return self.accounts[accountid]
        raise AccountNotFoundException(driveid)
    
    def get_drive_by_driveid(self, driveid):
        for account_id in self.accounts:
            for drive in self.accounts[account_id]['drives']:
                if drive['id'] == driveid:
                    return drive
        raise DriveNotFoundException(driveid)
    
    def save(self):
        with KodiUtils.lock:
            with open(self._config_path, 'wb') as fo:
                fo.write(json.dumps(self.accounts, sort_keys=True, indent=4))
        
    def remove_account(self, accountid):
        self.load()
        del self.accounts[accountid]
        self.save()
    
    def remove_drive(self, driveid):
        self.load()
        account = self.get_account_by_driveid(driveid)
        drive = self.get_drive_by_driveid(driveid)
        account['drives'].remove(drive)
        self.save()
    
    def get_account_display_name(self, account, drive=None, provider=None, with_format=False):
        s = '[B]%s[/B]' if with_format else '%s'
        display = s % Utils.unicode(account['name'])
        if drive:
            if provider and 'type' in drive and drive['type']:
                display += ' | ' + provider.get_drive_type_name(drive['type'])
            if 'name' in drive and drive['name']:
                display += ' | ' + Utils.unicode(drive['name'])
        return display

class AccountNotFoundException(Exception):
    pass

class DriveNotFoundException(Exception):
    pass

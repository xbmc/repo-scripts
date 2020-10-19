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

from clouddrive.common.db import SimpleKeyValueDb
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils


class AccountManager(object):
    db = None
    
    def __init__(self, _base_path):
        self.db = SimpleKeyValueDb(_base_path, 'accounts')
        
        # only if not migrated. ignore if fails to read.
        config_path = os.path.join(_base_path, 'accounts.cfg')
        if os.path.exists(config_path):
            with KodiUtils.lock:
                try:
                    with open(config_path, 'rb') as fo:
                        accounts = json.loads(fo.read())
                        for accountid in accounts:
                            self.db.set(accountid, accounts[accountid])
                    os.rename(config_path, os.path.join(_base_path, 'accounts.cfg.migrated'))
                except Exception as ex:
                    Logger.debug("Error migrating accounts.")
                    Logger.debug(ex)
                    os.rename(config_path, os.path.join(_base_path, 'accounts.cfg.failed'))
    
    def get_accounts(self):
        return self.db.getall()
    
    def save_account(self, account):
        self.db.set(account['id'], account)
    
    def get_by_driveid(self, return_type, driveid, account=None, accounts=None):
        if account:
            accounts = {account['id'] : account}
        if not accounts:
            accounts = self.get_accounts()
        for accountid in accounts:
            for drive in accounts[accountid]['drives']:
                if drive['id'] == driveid:
                    if return_type == 'account':
                        return accounts[accountid]
                    else:
                        return drive
        if return_type == 'account':
            raise AccountNotFoundException(driveid)
        else:
            raise DriveNotFoundException(driveid)
    
    def save_drive(self, drive, account=None, accounts=None):
        account = self.get_by_driveid('account', drive['id'], account, accounts)
        stored_drive = self.get_by_driveid('drive', drive['id'], account, accounts)
        index = account['drives'].index(stored_drive)
        account['drives'][index] = drive
        self.save_account(account)
        
    def remove_account(self, accountid):
        self.db.remove(accountid)
    
    def remove_drive(self, driveid, account=None, accounts=None):
        account = self.get_by_driveid('account', driveid, account, accounts)
        drive = self.get_by_driveid('drive', driveid, account)
        account['drives'].remove(drive)
        self.save_account(account)
    
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

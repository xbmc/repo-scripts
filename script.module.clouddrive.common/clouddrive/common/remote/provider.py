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

import time

from clouddrive.common.remote.oauth2 import OAuth2
from clouddrive.common.remote.signin import Signin
from clouddrive.common.utils import Utils


class Provider(OAuth2):
    name = ''
    source_mode = False
    _signin = Signin()
    _account_manager = None
    _driveid = None
    
    
    def __init__(self, name, source_mode = False):
        self.name = name
        self.source_mode = source_mode
        
    def create_pin(self, request_params=None):
        return self._signin.create_pin(self.name, request_params)
    
    def fetch_tokens_info(self, pin_info, request_params=None):
        tokens_info = self._signin.fetch_tokens_info(pin_info, request_params)
        if tokens_info:
            tokens_info['date'] = time.time()
        return tokens_info
    
    def configure(self, account_manager, driveid):
        self._account_manager = account_manager
        self._driveid = driveid
    
    def validate_configuration(self):
        if not self._account_manager:
            raise Exception('Account Manager not defined')
        if not self._driveid:
            raise Exception('DriveId not defined')
    
    def _account_from_manager(self):
        self.validate_configuration()
        self._account_manager.load()
        return self._account_manager.get_account_by_driveid(self._driveid)

    def _drive_from_manager(self):
        self.validate_configuration()
        self._account_manager.load()
        return self._account_manager.get_drive_by_driveid(self._driveid)
        
    def get_access_tokens(self):
        return self._account_from_manager()['access_tokens']
    
    def get_change_token(self):
        return Utils.get_safe_value(self._drive_from_manager(), 'change_token')
    
    def refresh_access_tokens(self, request_params=None):
        tokens = self.get_access_tokens()
        tokens_info = self._signin.refresh_tokens(self.name, tokens['refresh_token'], request_params)
        if tokens_info:
            tokens_info['date'] = time.time()
        return tokens_info
    
    def persist_access_tokens(self, access_tokens):
        account = self._account_from_manager()
        account['access_tokens'] = access_tokens
        self._account_manager.add_account(account)
    
    def persist_change_token(self, change_token):
        drive = self._drive_from_manager()
        drive['change_token'] = change_token
        self._account_manager.save()
    
    def get_account(self, request_params=None, access_tokens=None):
        raise NotImplementedError()
    
    def get_drives(self, request_params=None, access_tokens=None):
        raise NotImplementedError()
    
    def get_drive_type_name(self, drive_type):
        return drive_type
    
    def cancel_operation(self):
        return False

    def changes(self):
        return []
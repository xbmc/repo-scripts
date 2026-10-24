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
    """
    The cloud service behind an add-on. A plugin subclasses it and implements the methods below; the add-on UI
    (ui/addon.py) and the services (download, source, export, player) only talk to the service through them.

    Items are dicts with these keys. Required for every item:
      id                  unique id of the file or folder; also used in play and download URLs
      name                file or folder name, with its extension
      name_extension      extension without the dot, lowercase not required (Utils.get_extension(name))
      parent              the containing folder, in a form get_folder_items and get_subtitles accept. Items listed
                          with get_folder_items(item_id=...) must use that item_id: library exports link items to
                          their folder through it.
      size                bytes (0 for folders)
      last_modified_date  ISO 8601 string, or None
    Folders:
      folder              {'child_count': number of children, or 0 if unknown}
    Files, when requested with include_download_info=True:
      download_info       {'url': address the download service fetches}. Set download_requires_auth = True when
                          that address needs the Authorization header (it is then added, and refreshed, by
                          prepare_request); leave it False only for pre-authenticated links.
    Optional:
      drive_id            drive of the item when it differs from the account's drive (shared drives, shared items)
      mimetype            used when the extension is unknown to Kodi
      thumbnail           image URL Kodi can open directly
      video               {'width', 'height', 'duration' (seconds)}
      audio               {'tracknumber', 'discnumber', 'duration', 'year', 'genre', 'album', 'artist', 'title'}
      image               {'size', ...}: marks the item as a picture even without a known extension
      description         shown by the source service
      subtitles           list of subtitle items, set by get_item(find_subtitles=True)
      deleted / removed   true for deleted items in changes()
      extra_params        extra URL parameters for the item's play and list actions
    """
    name = ''
    source_mode = False
    # Providers that can revoke an account's tokens (revoke_access) set this, and the company the user signs in
    # with, for messages ("Google").
    revoke_supported = False
    signin_company = ''
    # True when revoking ends every sign-in of the account with this app, on all devices (Google); False when it
    # only ends this device's (Dropbox). The remove dialog warns about other devices only in the first case.
    revoke_ends_all_sign_ins = True
    download_requires_auth = False
    _signin = Signin()
    _account_manager = None
    _driveid = None
    
    
    def __init__(self, name, source_mode = False):
        self.name = name
        self.source_mode = source_mode
        
    def create_pin(self, request_params=None):
        return self._signin.create_pin(self.name, request_params)
    
    def register_networks(self, pin_info):
        return self._signin.register_networks(pin_info)

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
        return self._account_manager.get_by_driveid('account', self._driveid)

    def _drive_from_manager(self):
        self.validate_configuration()
        return self._account_manager.get_by_driveid('drive', self._driveid)
        
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
        self._account_manager.save_account(account)
    
    def persist_change_token(self, change_token):
        drive = self._drive_from_manager()
        drive['change_token'] = change_token
        self._account_manager.save_drive(drive)
    
    def revoke_access(self):
        """
        Revokes the configured account's tokens at the provider, so they stop working everywhere. Raises on failure.
        """
        raise NotImplementedError()

    def get_account(self, request_params=None, access_tokens=None):
        raise NotImplementedError()
    
    def get_drives(self, request_params=None, access_tokens=None):
        raise NotImplementedError()
    
    def get_drive_type_name(self, drive_type):
        return drive_type

    def get_folder_items(self, item_driveid=None, item_id=None, path=None, on_items_page_completed=None, include_download_info=False, on_before_add_item=None):
        """
        The items in a folder, given by item_id, or by path ('/' for the root, or a special path returned by the
        add-on's get_custom_drive_folders). For services that page results: call on_items_page_completed(items) after
        each page, on_before_add_item(item) before adding each item, and return None if cancel_operation() is true.
        """
        raise NotImplementedError()

    def get_item(self, item_driveid=None, item_id=None, path=None, find_subtitles=False, include_download_info=False):
        """One item by id or path. With find_subtitles, also fills 'subtitles' using get_subtitles."""
        raise NotImplementedError()

    def search(self, query, item_driveid=None, item_id=None, on_items_page_completed=None):
        """Files whose name matches query, in the folder item_id (and below) or in the whole drive."""
        raise NotImplementedError()

    def get_subtitles(self, parent, name, item_driveid=None, include_download_info=False):
        """Subtitle items stored next to the video called name, in the folder parent (as given in the item's 'parent')."""
        raise NotImplementedError()
    
    def list_subtree(self, item_driveid, item_id):
        """
        Optional, to make library exports fast: the items, with download info, of the folder item_id and of every
        folder below it, as {folder id: [items]}, in much fewer requests than one per folder. Items use their
        folder's id as 'parent'. Return None when the service can't list a tree at once (folders are then listed one
        by one), or if cancel_operation() is true.
        """
        return None

    # Exports list every folder of a tree. With list_subtree, the first folder's call lists the whole tree and the
    # other folders' items are kept here: each is handed out once, for a few minutes after the listing, so the
    # long-running export service never reuses an old listing.
    _SUBTREE_TTL = 600

    def get_export_folder_items(self, item_driveid, item_id, on_before_add_item=None):
        """The items, with download info, of the folder item_id for a library export."""
        cache = self.__dict__.setdefault('_subtree_cache', {})
        cached = cache.pop(item_id, None)
        if cached and time.time() - cached[0] < self._SUBTREE_TTL:
            items = cached[1]
        else:
            tree = self.list_subtree(item_driveid, item_id)
            if self.cancel_operation():
                return None
            if tree is None:
                return self.get_folder_items(item_driveid, item_id, include_download_info=True, on_before_add_item=on_before_add_item)
            items = tree.pop(item_id, [])
            listed = time.time()
            for folder_id, folder_items in tree.items():
                cache[folder_id] = (listed, folder_items)
        if on_before_add_item:
            for item in items:
                on_before_add_item(item)
        return items

    def cancel_operation(self):
        return False

    def changes(self):
        """
        Items changed since the last call, for exports that watch for changes. The token that marks the position is
        kept with get_change_token and persist_change_token. Providers that can't report changes return [].
        """
        return []
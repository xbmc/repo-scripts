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

from clouddrive.common.exception import UIException
from clouddrive.common.remote.request import Request
from clouddrive.common.ui.dialog import QRDialogProgress
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils


class AccountSignin(object):
    """
    Adds an account: gets a sign-in code from the sign-in server, shows it with a QR code until the user signs in on
    another device, then reads the account and its drives and saves them.
    """
    TIMEOUT = 120

    def __init__(self, provider, account_manager, common_addon, addon_name, progress_dialog, progress_dialog_bg, monitor):
        self._provider = provider
        self._account_manager = account_manager
        self._common_addon = common_addon
        self._addon_name = addon_name
        self._progress_dialog = progress_dialog
        self._progress_dialog_bg = progress_dialog_bg
        self._monitor = monitor
        self.pin_dialog = None
        # The public IP before the code was created, to explain a failed sign-in if it changed.
        self.ip_before_pin = None

    def cancelled(self):
        return self._monitor.abortRequested() or self._progress_dialog.iscanceled() or \
            (self.pin_dialog is not None and self.pin_dialog.iscanceled())

    def _text(self, string_id):
        return self._common_addon.getLocalizedString(string_id)

    def run(self):
        """The saved account, or None when cancelled or timed out."""
        try:
            return self._run()
        finally:
            if self.pin_dialog:
                self.pin_dialog.close()

    def _run(self):
        request_params = {
            'waiting_retry': lambda request, remaining: self._progress_dialog_bg.update(
                int((request.current_delay - remaining)/request.current_delay*100),
                heading=self._text(32043) % ('' if request.current_tries == 1 else ' again'),
                message=self._text(32044) % str(int(remaining)) + ' ' +
                        self._text(32045) % (str(request.current_tries + 1), str(request.tries))
            ),
            'on_complete': lambda request: (self._progress_dialog.close(), self._progress_dialog_bg.close()),
            'cancel_operation': self.cancelled,
            'wait': self._monitor.waitForAbort
        }
        provider = self._provider
        signin_server = KodiUtils.get_signin_server()
        self._progress_dialog.update(0, self._text(32008))

        self.ip_before_pin = Request(signin_server + '/ip', None).request()
        pin_info = provider.create_pin(request_params)
        self._progress_dialog.close()
        if self.cancelled():
            return None
        if not pin_info:
            raise Exception('Unable to retrieve a pin code')
        source_ids = provider.register_networks(pin_info)
        source_id = ', '.join(source_ids) if source_ids else str(Utils.get_source_id(Utils.unicode(self.ip_before_pin)))

        tokens_info = {}
        request_params['on_complete'] = lambda request: self._progress_dialog_bg.close()
        self.pin_dialog = QRDialogProgress.create(self._addon_name,
                                                  signin_server + '/signin/%s' % pin_info['pin'],
                                                  self._text(32009),
                                                  self._text(32010) % ('[B]%s[/B]' % signin_server, '[B][COLOR lime]%s[/COLOR][/B]' % pin_info['pin']))
        self.pin_dialog.show()
        max_waiting_time = time.time() + self.TIMEOUT
        while not self.cancelled() and max_waiting_time > time.time():
            remaining = round(max_waiting_time-time.time())
            percent = int(remaining/self.TIMEOUT*100)
            self.pin_dialog.update(percent, line3='[CR]'+self._text(32011) % str(int(remaining)) + '[CR][CR]Your source id is: %s' % source_id)
            if int(remaining) % 5 == 0 or remaining == 1:
                tokens_info = provider.fetch_tokens_info(pin_info, request_params = request_params)
                if self.cancelled() or tokens_info:
                    break
            if self._monitor.waitForAbort(1):
                break
        self.pin_dialog.close()

        if self.cancelled() or time.time() >= max_waiting_time:
            return None
        if not tokens_info:
            raise Exception('Unable to retrieve the auth2 tokens')

        self._progress_dialog.update(25, self._text(32064),' ',' ')
        try:
            account = provider.get_account(request_params = request_params, access_tokens = tokens_info)
        except Exception as e:
            raise UIException(32065, e)
        if self.cancelled():
            return None

        self._progress_dialog.update(50, self._text(32017))
        try:
            account['drives'] = provider.get_drives(request_params = request_params, access_tokens = tokens_info)
        except Exception as e:
            raise UIException(32018, e)
        if self.cancelled():
            return None

        self._progress_dialog.update(75, self._text(32020))
        try:
            account['access_tokens'] = tokens_info
            self._account_manager.save_account(account)
        except Exception as e:
            raise UIException(32021, e)
        if self.cancelled():
            return None

        self._progress_dialog.update(90)
        try:
            # Accounts of very old versions were stored per drive, with the drive type 'migrated'.
            accounts = self._account_manager.get_accounts()
            for drive in account['drives']:
                driveid = drive['id']
                if driveid in accounts:
                    drive = accounts[driveid]['drives'][0]
                    if drive['id'] == driveid and drive['type'] == 'migrated':
                        Logger.debug('Account %s removed.' % driveid)
                        self._account_manager.remove_account(driveid)
        except Exception:
            pass
        if self.cancelled():
            return None
        self._progress_dialog.close()
        return account

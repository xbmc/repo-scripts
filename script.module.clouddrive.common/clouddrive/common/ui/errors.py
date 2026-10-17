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

from urllib.error import HTTPError, URLError

from clouddrive.common.account import AccountNotFoundException, DriveNotFoundException
from clouddrive.common.exception import ExceptionUtils, RequestException, UIException
from clouddrive.common.utils import Utils


class ErrorMessage(object):
    """What to tell the user: up to three lines, or a question (ask) instead of the message."""
    ADD_ACCOUNT = 'add_account'
    SIGN_IN_AGAIN = 'sign_in_again'

    def __init__(self, line1, line2=None, line3=None, ask=None):
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.ask = ask


class ErrorMessages(object):
    """Turns an exception into the message shown to the user. No dialogs or other side effects here."""

    def __init__(self, common_addon, signin_server):
        self._common_addon = common_addon
        self._signin_server = signin_server

    def _text(self, string_id):
        return self._common_addon.getLocalizedString(string_id)

    def describe(self, ex, drive_selected, ip_before_pin=None, current_ip=None):
        """
        drive_selected: the failed action was on a drive (its account may need a new sign-in).
        ip_before_pin and current_ip (a function): when a sign-in code is rejected, tell whether the public IP changed.
        """
        rex = ExceptionUtils.extract_exception(ex, RequestException)
        uiex = ExceptionUtils.extract_exception(ex, UIException)
        httpex = ExceptionUtils.extract_exception(ex, HTTPError)
        urlex = ExceptionUtils.extract_exception(ex, URLError)
        line1 = self._text(32027)
        line2 = Utils.unicode(ex)
        line3 = self._text(32016)

        if uiex:
            line1 = self._text(int(Utils.str(uiex)))
            line2 = Utils.unicode(uiex.root_exception)
        elif rex and rex.response:
            line1 += ' ' + Utils.unicode(rex)
            line2 = ExceptionUtils.extract_error_message(rex.response)
        if isinstance(ex, (AccountNotFoundException, DriveNotFoundException)):
            return ErrorMessage(line1, line2, line3, ask=ErrorMessage.ADD_ACCOUNT)
        if rex and httpex:
            if httpex.code >= 500:
                line1 = self._text(32035)
                line2 = None
                line3 = self._text(32038)
            elif httpex.code >= 400:
                if drive_selected:
                    if self._signin_server in rex.request or httpex.code == 401:
                        return ErrorMessage(line1, line2, line3, ask=ErrorMessage.SIGN_IN_AGAIN)
                    elif httpex.code == 403:
                        line1 = self._text(32019)
                        line2 = line3 = None
                    elif httpex.code == 404:
                        line1 = self._text(32037)
                        line2 = None
                    else:
                        line1 = self._text(32036)
                        line3 = self._text(32038)
                elif self._signin_server + '/pin/' in rex.request and httpex.code == 404 and ip_before_pin and current_ip:
                    ip_after_pin = current_ip()
                    if ip_before_pin != ip_after_pin:
                        line1 = self._text(32072)
                        line2 = self._text(32073) % (ip_before_pin, ip_after_pin,)
        elif urlex:
            reason = Utils.str(urlex.reason)
            line3 = self._text(32074)
            if '[Errno 101]' in reason:
                line1 = self._text(32076)
            elif '[Errno 11001]' in reason:
                line1 = self._text(32077)
            elif 'CERTIFICATE_VERIFY_FAILED' in reason:
                line1 = self._text(32078)
            else:
                line1 = self._text(32075)
        return ErrorMessage(line1, line2, line3)

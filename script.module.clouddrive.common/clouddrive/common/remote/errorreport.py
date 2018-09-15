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

import threading
import urllib
from urllib2 import HTTPError

from clouddrive.common.exception import ExceptionUtils, RequestException
from clouddrive.common.remote.request import Request
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from clouddrive.common.account import DriveNotFoundException


class ErrorReport(object):
    
    @staticmethod
    def send_report(report):
        if KodiUtils.get_addon_setting('report_error') == 'true':
            report_url = KodiUtils.get_signin_server() + '/report'
            t = threading.Thread(target=Request(report_url, urllib.urlencode({'stacktrace' : report})).request)
            t.setDaemon(True)
            t.start()
    
    @staticmethod
    def handle_exception(ex):
        stacktrace = ExceptionUtils.full_stacktrace(ex)
        rex = ExceptionUtils.extract_exception(ex, RequestException)
        httpex = ExceptionUtils.extract_exception(ex, HTTPError)
        dnf = ExceptionUtils.extract_exception(ex, DriveNotFoundException)
        
        line1 = ''
        line2 = Utils.unicode(ex)
        
        send_report = True
        log_report = True
        if rex and rex.response:
            line1 = Utils.unicode(rex)
            line2 = ExceptionUtils.extract_error_message(rex.response)
        
        if httpex:
            if httpex.code == 401:
                send_report = False
            elif httpex.code == 404:
                send_report = False
                log_report = False
        if dnf:
            send_report = False
            log_report = False
            
        addonid = KodiUtils.get_addon_info('id')
        addon_version = KodiUtils.get_addon_info('version')
        common_addon_version = KodiUtils.get_addon_info('version', 'script.module.clouddrive.common')
        report = '[%s] [%s]/[%s]\n\n%s\n%s\n%s\n\n%s' % (addonid, addon_version, common_addon_version, line1, line2, '', stacktrace)
        if rex:
            report += '\n\n%s\nResponse:\n%s' % (rex.request, rex.response)
        if log_report:
            Logger.debug(report)
        else:
            Logger.debug(ex)
        if send_report:
            Logger.notice(report)
            Logger.notice('Report sent')
            ErrorReport.send_report(report)
    
    
    

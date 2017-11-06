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

import urllib

from clouddrive.common.remote.request import Request
from clouddrive.common.ui.utils import KodiUtils


class ErrorReport(object):
    _report_url = 'https://kodi-login.herokuapp.com/report'
    def send_report(self, report):
        if KodiUtils.get_addon_setting('report_error', 'script.module.clouddrive.common') == 'true':
            Request(self._report_url, urllib.urlencode({'stacktrace' : report})).request()
    

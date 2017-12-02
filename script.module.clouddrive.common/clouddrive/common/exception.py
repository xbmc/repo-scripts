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
import traceback

class WrappedException(Exception):
    root_exception = None
    root_tb = None
    def __init__(self, message, root_exception):
        super(WrappedException, self).__init__(message)
        self.root_exception = root_exception
        if root_exception:
            self.root_tb = traceback.format_exc()

class RequestException(WrappedException):
    request = None
    response = None
    def __init__(self, message, root_exception, request, response):
        super(RequestException, self).__init__(message, root_exception)
        self.request = request
        self.response = response
        
class UIException(WrappedException):
    def __init__(self, message_id, root_exception):
        super(UIException, self).__init__(message_id, root_exception)

class ExceptionUtils:
    @staticmethod
    def full_stacktrace(e):
        tb = traceback.format_exc()
        while e and isinstance(e, WrappedException):
            if e.root_tb:
                tb += 'Root cause:\n' + e.root_tb
            e = e.root_exception
        return tb
    
    @staticmethod
    def extract_exception(e, exception_type):
        exception = None
        while e:
            if isinstance(e, exception_type):
                exception = e
                break
            e = None if not isinstance(e, WrappedException) else e.root_exception
        return exception
    
    
    @staticmethod
    def extract_error_message(response):
        try:
            error = json.loads(response)['error']
            return '%s - %s' % (error['code'], error['message'])
        except:
            return response

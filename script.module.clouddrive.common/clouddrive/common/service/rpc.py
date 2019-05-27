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

import inspect
from urllib2 import HTTPError

from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.service.base import BaseServerService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
import uuid
from clouddrive.common.remote.request import Request
from clouddrive.common.ui.utils import KodiUtils


class RpcService(BaseServerService):
    name = 'rpc'
    def __init__(self, listener):
        super(RpcService, self).__init__(listener)
        self._handler = RpcHandler
    
class RpcHandler(BaseHandler):
    def do_POST(self):
        content = Utils.get_file_buffer()
        data = self.path.split('/')
        if len(data) > 1 and data[1] == self.server.service.name:
            try:
                size = int(self.headers.getheader('content-length', 0))
                cmd = eval(self.rfile.read(size))
                method = Utils.get_safe_value(cmd, 'method')
                if method:
                    code = 200
                    args = Utils.get_safe_value(cmd, 'args', [])
                    kwargs = Utils.get_safe_value(cmd, 'kwargs', {})
                    Logger.debug('Command received:\n%s' % cmd)
                    content.write(repr(self.server.data.rpc(method, args, kwargs)))
                else:
                    code = 400
                    content.write('Method required')
            except Exception as e:
                httpex = ExceptionUtils.extract_exception(e, HTTPError)
                if httpex:
                    code = httpex.code
                else:
                    code = 500
                content.write(ExceptionUtils.full_stacktrace(e))
        else:
            code = 404
        self.write_response(code, content=content)
        

class RemoteProcessCallable(object):
 
    def rpc(self, method, args=None, kwargs=None):
        args = Utils.default(args, [])
        kwargs = Utils.default(kwargs, {})
        method = getattr(self, method)
        fkwargs = {}
        for name in inspect.getargspec(method)[0]:
            if name in kwargs:
                fkwargs[name] = kwargs[name]
        try:
            return method(*args, **fkwargs)
        except Exception as ex:
            handle = True
            httpex = ExceptionUtils.extract_exception(ex, HTTPError)
            if httpex:
                handle = httpex.code != 404
            if handle:
                self._handle_exception(ex, False)
            raise ex

class RpcUtil(object):
    
    @staticmethod
    def rpc(addonid, method, args=None, kwargs=None, request_id=None):
        if not request_id:
            request_id = str(uuid.uuid4())
        cmd = {'method': method}
        if args:
            cmd.update({'args': args})
        if kwargs:
            cmd.update({'kwargs': kwargs})
        cmd = repr(cmd)
        result = eval(Request('http://%s:%s/%s' % (RpcService._interface, KodiUtils.get_service_port(RpcService.name, addonid), RpcService.name),
            cmd, {'content-length': len(cmd), 'request-id': request_id}, tries=1).request()
        )
        return result

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


from BaseHTTPServer import BaseHTTPRequestHandler
from SocketServer import ThreadingTCPServer
import SocketServer
import shutil
import socket
import threading

from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils

class BaseServerService(object):
    _interface = '127.0.0.1'
    _server = None
    name = ''
    _handler = None
    data = None
    
    def __init__(self, data=None):
        SocketServer.TCPServer.allow_reuse_address = True
        self.data = data
    
    def get_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def start(self):
        port = self.get_port()
        KodiUtils.set_service_port(self.name, port)
        self._server = BaseServer((self._interface, port), self._handler, self, self.data)
        Logger.notice('Service \'%s\' started in port %s' % (self.name, port))
        self._server.serve_forever()
    
    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            Logger.notice('Service stopped')
    
class BaseServer(ThreadingTCPServer):
    
    data = None
    service = None
    allow_reuse_address = True
    
    def __init__(self, server_address, RequestHandlerClass, service, data=None):
        self.data = data
        self.service = service
        #HTTPServer.__init__(self, server_address, RequestHandlerClass)
        ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
    
    def process_request(self, request, client_address):
        thread = threading.Thread(target = self.process_request_thread, args = (request, client_address), name='%s-request' % threading.current_thread().name)
        thread.daemon = True
        thread.start()

class BaseHandler(BaseHTTPRequestHandler):
    content_type = 'text/html; charset=UTF-8'
    response_code_sent = False
    response_headers_block_sent = False
    
    def __init__(self, request, client_address, server):
        self.protocol_version = 'HTTP/1.1'
        self.server_version = KodiUtils.get_addon_info('id') + '/' + KodiUtils.get_addon_info('version')
        self.wbufsize = -1
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
    
    def write_response(self, code, message=None, content=None, headers=None):
        headers = Utils.default(headers, {})
        length = 0
        self.send_response(code, message)
        if content:
            length = content.tell()
            content.seek(0)
            self.send_header('Content-Type', self.content_type)
            self.send_header('Content-Length', length)
        self.send_header('Connection', 'close')
        request_id = self.headers.getheader('request-id')
        if request_id:
            self.send_header('request-id', request_id)
        for key in headers:
            self.send_header(key, headers[key])
        self.end_headers()
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            if content:
                shutil.copyfileobj(content, self.wfile)
                content.close()
            Logger.debug('[%s] response code: %s, length: %s' % (request_id, code, length))
    
    def send_response(self, code, message=None):
        if self.response_code_sent:
            raise InvalidResponseException('response code already sent')
        BaseHTTPRequestHandler.send_response(self, code, message)
        self.response_code_sent = True
        
    def send_header(self, keyword, value):
        if self.response_headers_block_sent:
            raise InvalidResponseException('Response headers block already sent')
        BaseHTTPRequestHandler.send_header(self, keyword, value)
    
    def end_headers(self):
        BaseHTTPRequestHandler.end_headers(self)
        self.response_headers_block_sent = True
     
    def log_message(self, format, *args):
        #Logger.notice("[%s.service] %s\n" % (self.server.service.name, format%args))
        return
        
    def log_error(self, format, *args):
        Logger.error("[%s.service] %s\n" % (self.server.service.name, format%args))
        
    def do_HEAD(self):
        self.do_GET()

class InvalidResponseException(Exception):
    pass

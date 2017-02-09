import os
import json
import threading

import BaseHTTPServer

import xbmc
import xbmcgui

from addon import addon
from addon import mpr

from addon import utils
from addon import routes


class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    @property
    def is_authorized(self):
        is_auth_enabled = addon.getSetting('server.auth_enabled')

        if is_auth_enabled == 'false':
            return True

        username = addon.getSetting('server.username')
        password = addon.getSetting('server.password')


        if 'Authorization' in self.headers:
            auth = self.headers['Authorization'].split()[1].decode('base64')
            user = auth.split(':')[0]
            pwd = auth.split(':')[1]

            if user == username and pwd == password:
                return True

        utils.log('Not authorized')
        return False

    def do_POST(self):
        if not self.is_authorized:
            self.send_response(401)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length)
        if data:
            data = json.loads(data)

        resp = mpr.call(url=self.path, args={'data' : data})

        if resp:
            self.send_response(200)

        else:
            self.send_response(404)

        self.end_headers()

    @mpr.s_url('/shutdown/')
    def shutdown(self):
        pass

    def log_message(self, format, *args):
        utils.log("%s - - [%s] %s\n" % (self.address_string(),
                                        self.log_date_time_string(),
                                        format%args),
                  lvl=xbmc.LOGDEBUG)


class Server():
    _host = None
    _port = None
    _handler = None

    _server = None

    _exit = threading.Event()
    _alive = threading.Event()

    def __init__(self, host, port, handler):
        self._host = host
        self._port = port
        self._handler = handler

    def _serve(self):
        try:
            self._server = BaseHTTPServer.HTTPServer((self._host, self._port),
                                                     self._handler)
        except:
            xbmcgui.Dialog().notification(utils.translate(30019),
                                          utils.translate(30020),
                                          addon.getAddonInfo('icon'))

            utils.log('Couldn\'t start backend', lvl=xbmc.LOGERROR)
            return

        self._server.allow_reuse_address = True
        self._server.timeout = 0.2

        self._alive.set()
        utils.log('Server started, handling requests...')
        while not self._exit.is_set():
            self._server.handle_request()

        self._server.socket.close()

        self._alive.clear()

    def serve(self):
        t = threading.Thread(target=self._serve)
        t.daemon = True
        t.start()

    def shutdown(self):
        utils.log('Shutting down!')
        self._exit.set()

    def is_alive(self):
        return self._alive.is_set()


if __name__ == '__main__':
    port = int(addon.getSetting('server.port'))
    server = Server('', port, Handler)
    server.serve()

    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break

    server.shutdown()

import os
import json
import threading
import xmlrpclib

import BaseHTTPServer
from SocketServer import ThreadingMixIn

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

    def log_message(self, format, *args):
        utils.log("%s - - [%s] %s\n" % (self.address_string(),
                                        self.log_date_time_string(),
                                        format%args))


class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    _is_alive = threading.Event()
    _exit = threading.Event()

    def is_alive(self):
        return self._is_alive.is_set()

    def serve_forever(self):
        if self.is_alive():
            utils.log('Server already running. Skipping!')
            return

        t = threading.Thread(target=self._serve)
        t.daemon = True
        t.start()

    def _serve(self):
        utils.log('Server started, handling requests now')
        while not self._exit.is_set():
            self._is_alive.set()
            self.handle_request()

        self._is_alive.clear()

    def exit(self):
        utils.log('Exit requested')
        self._exit.set()
        self._exit.wait()

        utils.log('Exit flag was set')
        try:
            addr = 'http://%s:%i' % (self.server_address[0],
                                     self.server_address[1])

            utils.log('Sending dummy request to:', addr)
            xmlrpclib.Server(addr).ping()
        except:
            pass

        utils.log('Shutdown complete')


if __name__ == '__main__':
    port = int(addon.getSetting('server.port'))

    server = ThreadedHTTPServer(('0.0.0.0', port), Handler)
    server.serve_forever()

    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(60):
            break

    server.exit()

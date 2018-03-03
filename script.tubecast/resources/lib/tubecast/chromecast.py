# -*- coding: utf-8 -*-
from threading import Thread
try:
    from socketserver import ThreadingMixIn
except ImportError:
    from SocketServer import ThreadingMixIn

from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from resources.lib.kodi import kodilogging
from resources.lib.tubecast.dial import app


logger = kodilogging.get_logger()


class SilentWSGIRequestHandler(WSGIRequestHandler):
    """WSGI request handler with logging disabled"""
    def log_message(self, format, *args):
        pass


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-Threaded WSGI server"""
    daemon_threads = True
    allow_reuse_address = True


class Chromecast(object):

    def __init__(self, monitor):
        self._monitor = monitor
        self._server_thread = Thread(target=self._run_server,
                                     args=('0.0.0.0', 8008))
        self._server_thread.daemon = True
        self._server = None
        self._abort_var = False

    def _run_server(self, host, port):
        self._server = make_server(host, port, app,
                                   server_class=ThreadedWSGIServer,
                                   handler_class=WSGIRequestHandler)
        self._server.timeout = 0.1
        while not self._abort_var or not self._monitor.abortRequested():
            self._server.handle_request()

        self._server.socket.close()

    def start(self):
        self._server_thread.start()

    def abort(self):
        self._abort_var = True

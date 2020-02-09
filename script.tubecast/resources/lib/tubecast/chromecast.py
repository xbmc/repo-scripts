# -*- coding: utf-8 -*-
import threading

try:
    from socketserver import ThreadingMixIn
except ImportError:
    from SocketServer import ThreadingMixIn

from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from resources.lib.kodi import kodilogging
from resources.lib.tubecast.dial import app

import socket


logger = kodilogging.get_logger("chromecast")


class SilentWSGIRequestHandler(WSGIRequestHandler):
    """WSGI request handler with logging disabled"""

    def log_message(self, format, *args):
        logger.debug("{} - - {}".format(self.address_string(), format % args))

    def handle(self):
        try:
            WSGIRequestHandler.handle(self)
        except socket.error:
            # Avoid garbage on the kodi log
            pass

    def address_string(self):
        return self.client_address[0]


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-Threaded WSGI server"""
    daemon_threads = True
    allow_reuse_address = True


class Chromecast(object):

    def __init__(self, monitor):
        self._monitor = monitor
        self._server_thread = threading.Thread(name="ChromecastServer",
                                               target=self._run_server,
                                               args=('0.0.0.0', 0))
        self._server_thread.daemon = True
        self._server = None
        self._has_server = threading.Event()
        self._abort_var = False

    def _run_server(self, host, port):
        self._server = make_server(host, port, app,
                                   server_class=ThreadedWSGIServer,
                                   handler_class=SilentWSGIRequestHandler)
        self._has_server.set()
        self._server.timeout = 0.1
        while not self._abort_var or not self._monitor.abortRequested():
            self._server.handle_request()

        self._server.server_close()

    def start(self):  # type: () -> Tuple[int, int]
        self._server_thread.start()
        self._has_server.wait()
        return tuple(self._server.socket.getsockname()[:2])

    def abort(self):
        self._abort_var = True
        self._server_thread.join()

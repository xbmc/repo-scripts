# -*- coding: utf-8 -*-

import logging
import os
import shutil
import threading

from resources.lib.logreader import LogReader
from resources.lib.logviewer import log_location
from resources.lib.utils import ADDON_PATH, encode, PY3

if PY3:
    import urllib.parse as urlparse
    from socketserver import ThreadingMixIn
    from http.server import BaseHTTPRequestHandler, HTTPServer
else:
    import urlparse
    from SocketServer import ThreadingMixIn
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


def base_handler(ctx):
    with open(os.path.join(ADDON_PATH, "resources", "templates", "webtail.html"), "rb") as f:
        html = f.read()

    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/html")
    ctx.send_header('Content-Length', len(html))
    ctx.send_header('Connection', 'keep-alive')
    ctx.end_headers()
    ctx.wfile.write(html)


def tail_handler(ctx):
    if ctx.log_path is None:
        logging.error("Unable to find log path")
        ctx.send_response(500)
        ctx.end_headers()
        return

    offset = int(ctx.request.get('offset', 0))
    reader = LogReader(ctx.log_path)
    reader.set_offset(offset)
    content = encode(reader.tail())

    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/plain")
    ctx.send_header('Content-Length', len(content))
    ctx.send_header('X-Seek-Offset', str(reader.get_offset()))
    ctx.end_headers()
    ctx.wfile.write(content)


def favicon_handler(ctx):
    ctx.send_response(200)
    ctx.send_header("Content-Type", "image/x-icon")
    ctx.end_headers()
    with open(os.path.join(ADDON_PATH, "resources", "images", "favicon.ico"), "rb") as f:
        shutil.copyfileobj(f, ctx.wfile)


class ServerHandler(BaseHTTPRequestHandler):
    log_path = log_location(False)

    get_routes = {
        "/": base_handler,
        "/tail": tail_handler,
        "/favicon.ico": favicon_handler,
    }

    # noinspection PyPep8Naming
    def do_GET(self):
        try:
            # noinspection PyAttributeOutsideInit
            self.url = urlparse.urlsplit(self.path)
            self.request = dict(urlparse.parse_qsl(self.url.query))
            if self.url.path in self.get_routes:
                self.get_routes[self.url.path](self)
            else:
                self.send_response(404)
                self.end_headers()
        except Exception as e:
            logging.error(e)
            self.send_response(500)
            self.end_headers()

    def log_message(self, fmt, *args):
        logging.info(fmt % args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

    def __init__(self, *args, **kwargs):
        self.__shutdown_request = threading.Event()
        self.__is_shut_down = threading.Event()
        self.__is_shut_down.set()
        HTTPServer.__init__(self, *args, **kwargs)

    def shutdown_server(self):
        self.__shutdown_request.set()
        self.__is_shut_down.wait()

    def serve_until_shutdown(self, should_stop=None, timeout=1):
        if should_stop is None:
            def should_stop():
                return False

        if timeout is not None:
            self.timeout = timeout

        self.__is_shut_down.clear()
        self.__shutdown_request.clear()

        while not self.__shutdown_request.is_set() and not should_stop():
            self.handle_request()

        self.__is_shut_down.set()

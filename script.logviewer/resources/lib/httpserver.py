# -*- coding: utf-8 -*-

import logging
import os
import shutil

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
    html_path = os.path.join(ADDON_PATH, "resources", "templates", "webtail.html")
    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/html")
    ctx.send_header("Content-Length", str(os.path.getsize(html_path)))
    ctx.send_header("Connection", "keep-alive")
    ctx.end_headers()
    with open(html_path, "rb") as f:
        shutil.copyfileobj(f, ctx.wfile)


def tail_handler(ctx):
    if ctx.log_path is None:
        logging.error("Unable to find log path")
        ctx.send_response_and_end(500)
        return

    offset = int(ctx.query.get("offset", 0))
    reader = LogReader(ctx.log_path)
    reader.set_offset(offset)
    content = encode(reader.tail())

    ctx.send_response(200)
    ctx.send_header("Content-Type", "text/plain")
    ctx.send_header("Content-Length", len(content))
    ctx.send_header("X-Seek-Offset", str(reader.get_offset()))
    ctx.end_headers()
    ctx.wfile.write(content)


def favicon_handler(ctx):
    favicon_path = os.path.join(ADDON_PATH, "resources", "images", "favicon.ico")
    ctx.send_response(200)
    ctx.send_header("Content-Type", "image/x-icon")
    ctx.send_header("Content-length", str(os.path.getsize(favicon_path)))
    ctx.end_headers()
    with open(favicon_path, "rb") as f:
        shutil.copyfileobj(f, ctx.wfile)


class HTTPRequestHandler(BaseHTTPRequestHandler, object):
    protocol_version = "HTTP/1.1"
    log_path = log_location(False)

    get_routes = {
        "/": base_handler,
        "/tail": tail_handler,
        "/favicon.ico": favicon_handler,
    }

    # noinspection PyPep8Naming, PyAttributeOutsideInit
    def do_GET(self):
        self._response_started = False
        try:
            self.url = urlparse.urlsplit(self.path)
            self.query = dict(urlparse.parse_qsl(self.url.query))

            handler = self.get_routes.get(self.url.path)
            if handler is None:
                self.send_response_and_end(404)
            else:
                handler(self)
        except Exception as e:
            if self._response_started:
                raise e
            else:
                logging.error(e, exc_info=True)
                self.send_response_and_end(500)

    def send_response(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self._response_started = True
        super(HTTPRequestHandler, self).send_response(*args, **kwargs)

    def send_response_and_end(self, code, message=None):
        self.send_response(code, message=message)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt, *args):
        logging.debug(fmt, *args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

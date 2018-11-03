# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com
# License: MIT, see LICENSE.txt
"""
Single-threaded asynchronous WSGI server with WebSockets support

Example::

    from from wsgiref.simple_server import demo_app
    from asyncore_wsgi import AsyncWebSocketHandler, make_server


    class SimpleEchoHandler(AsyncWebSocketHandler):

        def handleMessage(self):
            print('Received WebSocket message: {}'.format(self.data))
            self.sendMessage(self.data)

        def handleConnected(self):
            print('WebSocket connected')

        def handleClose(self):
            print('WebSocket closed')


    httpd = make_server('', 8000, demo_app, ws_handler_class=SimpleEchoHandler)
    httpd.serve_forever()

The server in the preceding example serves a demo WSGI app from
the Standard Library and the echo WebSocket on ``'/ws'`` path.
"""

from __future__ import absolute_import
import asyncore
import select
import socket
from errno import EINTR
from io import BytesIO
from shutil import copyfileobj
from tempfile import TemporaryFile
from wsgiref.simple_server import WSGIServer, ServerHandler, WSGIRequestHandler
from .SimpleWebSocketServer import AsyncWebSocketHandler
from .. import logging

__all__ = ['AsyncWsgiHandler', 'AsyncWebSocketHandler', 'AsyncWsgiServer',
            'make_server']

__version__ = '0.0.6'

logger = logging.getLogger('asyncore_wsgi')


def epoll_poller(timeout=0.0, map=None):
    """
    A poller which uses epoll(), supported on Linux 2.5.44 and newer

    Borrowed from here:
    https://github.com/m13253/python-asyncore-epoll/blob/master/asyncore_epoll.py#L200
    """
    if map is None:
        map = asyncore.socket_map
    pollster = select.epoll()
    if map:
        for fd, obj in map.items():
            flags = 0
            if obj.readable():
                flags |= select.POLLIN | select.POLLPRI
            if obj.writable():
                flags |= select.POLLOUT
            if flags:
                # Only check for exceptions if object was either readable
                # or writable.
                flags |= select.POLLERR | select.POLLHUP | select.POLLNVAL
                pollster.register(fd, flags)
        try:
            r = pollster.poll(timeout)
        except select.error as err:
            if err.args[0] != EINTR:
                raise
            r = []
        for fd, flags in r:
            obj = map.get(fd)
            if obj is None:
                continue
            asyncore.readwrite(obj, flags)


def get_poll_func():
    """Get the best available socket poll function

    :return: poller function
    """
    if hasattr(select, 'epoll'):
        poll_func = epoll_poller
    elif hasattr(select, 'poll'):
        poll_func = asyncore.poll2
    else:
        poll_func = asyncore.poll
    return poll_func


class AsyncServerHandler(ServerHandler):
    """
    Modified ServerHandler class for using with async transfer
    """

    def __init__(self, *args, **kwargs):
        ServerHandler.__init__(self, *args, **kwargs)
        self.iterator = None

    def cleanup_headers(self):
        # Do not add Content-Length and use Transfer-Encoding: chunked instead
        pass

    def finish_response(self):
        """Get WSGI response iterator for sending in handle_write"""
        self.iterator = iter(self.result)


class AsyncWsgiHandler(asyncore.dispatcher, WSGIRequestHandler):
    """
    Asynchronous WSGI request handler with optional WebSocket support

    If ``ws_handler_class`` is set, a request to ``ws_path` is
    upgraded to WebSocket protocol.
    """
    accepting = False
    server_version = 'AsyncWsgiServer/' + __version__
    protocol_version = 'HTTP/1.1'
    max_input_content_length = 1024 * 1024 * 1024
    max_input_in_memory = 16 * 1024
    ws_path = '/ws'
    ws_handler_class = None
    verbose_logging = False

    def __init__(self, request, client_address, server, map):
        self._can_read = True
        self._can_write = False
        self._server_handler = None
        self._transfer_chunked = False
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()
        asyncore.dispatcher.__init__(self, request, map)

    def log_message(self, format, *args):
        if self.verbose_logging:
            WSGIRequestHandler.log_message(self, format, *args)

    def readable(self):
        return self._can_read

    def writable(self):
        return self._can_write

    def handle_read(self):
        self._can_read = False
        try:
            self.raw_requestline = self.rfile.readline(65537)
        except Exception:
            self.handle_error()
            return
        if len(self.raw_requestline) > 65536:
            self.requestline = ''
            self.request_version = ''
            self.command = ''
            self.send_error(414)
            self.handle_close()
            return
        if not self.parse_request():
            self.handle_close()
            return
        if self.path == self.ws_path and self.ws_handler_class is not None:
            self._switch_to_websocket()
            return
        self._input_stream = BytesIO()
        if self.command.lower() in ('post', 'put', 'patch'):
            cont_length = self.headers.get('content-length')
            if cont_length is None:
                self.send_error(411)
                self.handle_close()
                return
            else:
                cont_length = int(cont_length)
                if cont_length > self.max_input_content_length:
                    self.send_error(413)
                    self.handle_close()
                    return
                elif cont_length > self.max_input_in_memory:
                    self._input_stream = TemporaryFile()
                copyfileobj(self.rfile, self._input_stream)
                self._input_stream.seek(0)
        self._server_handler = AsyncServerHandler(
            self._input_stream, self.wfile, self.get_stderr(),
            self.get_environ())
        self._server_handler.server_software = self.server_version
        self._server_handler.http_version = self.protocol_version[5:]
        self._server_handler.request_handler = self  # backpointer for logging
        self._server_handler.wsgi_multiprocess = False
        self._server_handler.wsgi_multithread = False
        try:
            self._server_handler.run(self.server.get_app())
        except Exception:
            self.handle_error()
        else:
            self._server_handler.headers['X-Clacks-Overhead'] = 'GNU Terry Pratchett'
            if 'Content-Length' not in self._server_handler.headers:
                self._transfer_chunked = True
                self._server_handler.headers['Transfer-Encoding'] = 'chunked'
            self._can_write = True

    def handle_write(self):
        self._can_write = False
        try:
            chunk = next(self._server_handler.iterator)
            if self._transfer_chunked:
                chunk = hex(len(chunk)).encode('ascii')[2:] + \
                        b'\r\n' + chunk + b'\r\n'
            self._server_handler.write(chunk)
        except StopIteration:
            if self._transfer_chunked:
                self._server_handler.write(b'0\r\n\r\n')
            self._server_handler.close()
            self._server_handler = None
            self._transfer_chunked = False
            if self.close_connection:
                self.handle_close()
            else:
                try:
                    self.wfile.flush()
                except socket.error:
                    self.handle_error()
                else:
                    self._can_read = True
        except Exception:
            self.handle_error()
        else:
            self._can_write = True

    def handle_error(self):
        logger.exception('Exception in {}!'.format(repr(self)))
        self.handle_close()

    def close(self):
        WSGIRequestHandler.finish(self)
        asyncore.dispatcher.close(self)

    def _switch_to_websocket(self):
        self._can_read = self._can_write = False
        self.ws_handler_class(self.server, self.request,
                              self.client_address, self,
                              self._map)


class AsyncWsgiServer(asyncore.dispatcher, WSGIServer):
    """Asynchronous WSGI server"""
    def __init__(self, server_address,
                 RequestHandlerClass=AsyncWsgiHandler,
                 map=None):
        if map is None:
            map = {}
        asyncore.dispatcher.__init__(self, map=map)
        WSGIServer.__init__(self, server_address, RequestHandlerClass, False)
        self._poll_func = get_poll_func()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(server_address)
        self.listen(5)
        self.server_address = self.socket.getsockname()
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port
        self.setup_environ()

    def writable(self):
        return False

    def handle_accept(self):
        try:
            pair = self.accept()
        except socket.error:
            logger.exception('Exception when accepting a request!')
        else:
            if pair is not None:
                self.RequestHandlerClass(pair[0], pair[1], self, self._map)

    def handle_error(self, *args, **kwargs):
        logger.exception('Exception in {}!'.format(repr(self)))
        self.handle_close()

    def poll_once(self, timeout=0.0):
        """
        Poll active sockets once

        This method can be used to allow aborting server polling loop
        on some condition.

        :param timeout: polling timeout
        """
        if self._map:
            self._poll_func(timeout, self._map)

    def handle_request(self):
        """Call :meth:`poll_once`"""
        self.poll_once(0.5)

    def serve_forever(self, poll_interval=0.5):
        """
        Start serving HTTP requests

        This method blocks the current thread.

        :param poll_interval: polling timeout
        :return:
        """
        logger.info('Starting server on {}:{}...'.format(
            self.server_name, self.server_port)
        )
        while True:
            try:
                self.poll_once(poll_interval)
            except (KeyboardInterrupt, SystemExit):
                break
        self.handle_close()
        logger.info('Server stopped.')

    def close(self):
        asyncore.dispatcher.close(self)
        asyncore.close_all(self._map, True)


def make_server(host, port, app=None,
                server_class=AsyncWsgiServer,
                handler_class=AsyncWsgiHandler,
                ws_handler_class=None,
                ws_path='/ws'):
    """Create server instance with an optional WebSocket handler

    For pure WebSocket server ``app`` may be ``None`` but an attempt to access
    any path other than ``ws_path`` will cause server error.
    
    :param host: hostname or IP
    :type host: str
    :param port: server port
    :type port: int
    :param app: WSGI application
    :param server_class: WSGI server class, defaults to AsyncWsgiServer
    :param handler_class: WSGI handler class, defaults to AsyncWsgiHandler
    :param ws_handler_class: WebSocket hanlder class, defaults to ``None``
    :param ws_path: WebSocket path on the server, defaults to '/ws'
    :type ws_path: str, optional
    :return: initialized server instance
    """
    handler_class.ws_handler_class = ws_handler_class
    handler_class.ws_path = ws_path
    httpd = server_class((host, port), RequestHandlerClass=handler_class)
    httpd.set_app(app)
    return httpd

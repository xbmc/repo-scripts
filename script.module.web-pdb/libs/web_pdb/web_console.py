# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: romanvm@yandex.ua
#
# Copyright (c) 2016 Roman Miroshnychenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
File-like web-based input/output console
"""

from __future__ import absolute_import, unicode_literals
import sys
import weakref
from socket import gethostname
from threading import Thread, Event, RLock
try:
    import queue
except ImportError:
    import Queue as queue
try:
    from socketserver import ThreadingMixIn
except ImportError:
    from SocketServer import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler
import xbmc
from xbmcaddon import Addon
from xbmcgui import DialogProgressBG
from .wsgi_app import app

__all__ = ['WebConsole']

kodi_monitor = xbmc.Monitor()
addon = Addon('script.module.web-pdb')


def ui_string(id_):
    return addon.getLocalizedString(id_).encode('utf-8')


class SilentWSGIRequestHandler(WSGIRequestHandler):
    """WSGI request handler with logging disabled"""
    def log_message(self, format, *args):
        pass


class ThreadedWSGIServer(ThreadingMixIn, WSGIServer):
    """Multi-Threaded WSGI server"""
    daemon_threads = True
    allow_reuse_address = True


class ThreadSafeBuffer(object):
    """
    A buffer for data exchange between threads
    """
    def __init__(self, contents=None):
        self._lock = RLock()
        self._contents = contents
        self._is_dirty = contents is not None

    @property
    def is_dirty(self):
        """Indicates whether a buffer contains unread data"""
        with self._lock:
            return self._is_dirty

    @property
    def contents(self):
        """Get or set buffer contents"""
        with self._lock:
            self._is_dirty = False
            return self._contents

    @contents.setter
    def contents(self, value):
        with self._lock:
            self._contents = value
            self._is_dirty = True


class WebConsole(object):
    """
    A file-like class for exchanging data between PDB and the web-UI
    """
    def __init__(self, host, port, debugger):
        self._debugger = weakref.proxy(debugger)
        self._history = ThreadSafeBuffer('')
        self._globals = ThreadSafeBuffer('')
        self._locals = ThreadSafeBuffer('')
        self._frame_data = ThreadSafeBuffer()
        self._in_queue = queue.Queue()
        self._stop_all = Event()
        self._server_thread = Thread(target=self._run_server, args=(host, port))
        self._server_thread.daemon = True
        self._server_thread.start()

    @property
    def seekable(self):
        return False

    @property
    def writable(self):
        return True

    @property
    def encoding(self):
        return 'utf-8'

    @property
    def closed(self):
        return self._stop_all.is_set()

    def _run_server(self, host, port):
        app.in_queue = self._in_queue
        app.history = self._history
        app.globals = self._globals
        app.locals = self._locals
        app.frame_data = self._frame_data
        httpd = make_server(host, port, app,
                            server_class=ThreadedWSGIServer,
                            handler_class=SilentWSGIRequestHandler)
        httpd.timeout = 0.1
        hostname = gethostname()
        xbmc.log('Web-PDB: starting web-server on {0}:{1}...'.format(hostname, port),
                 xbmc.LOGNOTICE)
        dialog = DialogProgressBG()
        started = False
        while not (self._stop_all.is_set() or kodi_monitor.abortRequested()):
            httpd.handle_request()
            if not started:
                xbmc.log('Web-PDB: web-server started.', xbmc.LOGNOTICE)
                dialog.create(ui_string(32001), ui_string(32002).format(hostname, port))
                dialog.update(100)
                started = True
        httpd.socket.close()
        xbmc.log('Web-PDB: web-server stopped.', xbmc.LOGNOTICE)
        dialog.close()

    def readline(self):
        while not (self._stop_all.is_set() or kodi_monitor.abortRequested()):
            try:
                data = self._in_queue.get(timeout=0.1)
                break
            except queue.Empty:
                continue
        else:
            data = ''
        self.writeline(data)
        return data

    read = readline

    def readlines(self):
        return [self.readline()]

    def writeline(self, data):
        if sys.version_info[0] == 2 and isinstance(data, str):
            data = data.decode('utf-8')
        self._history.contents += data
        try:
            self._globals.contents = self._debugger.get_globals()
            self._locals.contents = self._debugger.get_locals()
            self._frame_data.contents = self._debugger.get_current_frame_data()
        except (IOError, AttributeError):
            self._globals.contents = self._locals.contents = 'No data available'
            self._frame_data.contents = {
                'filename': '',
                'listing': 'No data available',
                'curr_line': -1,
                'breaklist': [],
            }

    write = writeline

    def writelines(self, lines):
        for line in lines:
            self.writeline(line)

    def flush(self):
        """
        Wait until history is read but no more than 5 cycles
        in case a browser session is closed.
        """
        i = 0
        while self._history.is_dirty and i <= 5 and not kodi_monitor.abortRequested():
            i += 1
            xbmc.sleep(200)

    def close(self):
        xbmc.log('Web-PDB: stopping web-server...', xbmc.LOGNOTICE)
        self._stop_all.set()
        self._server_thread.join()

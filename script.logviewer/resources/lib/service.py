# -*- coding: utf-8 -*-

import logging
import threading

import xbmc
import xbmcgui

from resources.lib import logviewer, utils
from resources.lib.httpserver import ThreadedHTTPServer, ServerHandler
from resources.lib.logreader import LogReader


class Monitor(xbmc.Monitor):
    def __init__(self):
        super(Monitor, self).__init__()
        self._port = utils.get_int_setting("port")
        self._error_popup_runner = None
        self._http_server_runner = None
        self._lock = threading.Lock()

    def start(self):
        self.onSettingsChanged()

    def stop(self):
        with self._lock:
            self._stop_error_popup_runner()
            self._stop_http_server_runner()

    def _start_error_popup_runner(self):
        if self._error_popup_runner is None:
            logging.debug("Starting error popup runner")
            self._error_popup_runner = ErrorPopupRunner(self)
            self._error_popup_runner.start()

    def _stop_error_popup_runner(self):
        if self._error_popup_runner is not None:
            logging.debug("Stopping error popup runner")
            self._error_popup_runner.stop()
            self._error_popup_runner.join()
            self._error_popup_runner = None

    def _start_http_server_runner(self):
        if self._http_server_runner is None:
            logging.debug("Starting http server runner")
            self._http_server_runner = HTTPServerRunner(self._port)
            self._http_server_runner.start()

    def _stop_http_server_runner(self):
        if self._http_server_runner is not None:
            logging.debug("Stopping http server runner")
            self._http_server_runner.stop()
            self._http_server_runner.join()
            self._http_server_runner = None

    def onSettingsChanged(self):
        with self._lock:
            http_port = utils.get_int_setting("port")
            run_http_server = utils.get_boolean_setting("http_server")
            run_error_popup = utils.get_boolean_setting("error_popup")

            if run_http_server:
                if http_port != self._port:
                    self._port = http_port
                    self._stop_http_server_runner()
                self._start_http_server_runner()
            else:
                self._stop_http_server_runner()

            if run_error_popup:
                self._start_error_popup_runner()
            else:
                self._stop_error_popup_runner()


class HTTPServerRunner(threading.Thread):
    def __init__(self, port):
        self._port = port
        self._server = None
        super(HTTPServerRunner, self).__init__()

    def run(self):
        self._server = server = ThreadedHTTPServer(("", self._port), ServerHandler)
        logging.debug("Server started at port %d", self._port)
        logging.debug("Local IP is %s", xbmc.getIPAddress())
        server.serve_forever()
        logging.debug("Closing server")
        server.server_close()
        logging.debug("Server terminated")

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None


class ErrorPopupRunner(threading.Thread):
    def __init__(self, monitor):
        self._running = False
        self._monitor = monitor
        super(ErrorPopupRunner, self).__init__()

    def start(self):
        self._running = True
        super(ErrorPopupRunner, self).start()

    def run(self):
        # Start error monitor
        path = logviewer.log_location(False)
        if path is None:
            logging.error("Unable to find log path")
            xbmcgui.Dialog().ok(utils.translate(30016), utils.translate(30017))
            return

        reader = LogReader(path)
        exceptions = utils.parse_exceptions_only()

        # Ignore initial errors
        reader.tail()

        while not self._monitor.waitForAbort(1) and self._running:
            content = reader.tail()
            parsed_errors = logviewer.parse_errors(content, set_style=True, exceptions_only=exceptions)
            if parsed_errors:
                logviewer.window(utils.ADDON_NAME, parsed_errors, default=utils.is_default_window())

    def stop(self):
        self._running = False


def run(start_delay=20):
    monitor = Monitor()
    # Wait a few seconds for Kodi to start
    # This will also ignore initial exceptions
    if monitor.waitForAbort(start_delay):
        return
    # Start the error monitor
    monitor.start()
    # Keep service running
    monitor.waitForAbort()
    # Stop the error monitor
    monitor.stop()

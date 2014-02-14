"""
Creates a HTTP connection
"""

import time
import thread
import threading

try:
    import http.client as httplib  # 3.0+
except ImportError:
    import httplib  # 2.7


class HTTPConn(object):
    """ Handles a HTTP connection """
    def __init__(self, host, port=None):
        self._raw_connection = httplib.HTTPConnection(host, port, None, None)
        self.responce = None
        self.responce_lock = threading.Lock()
        self.closing = False

    def request(self, url, body=None):
        """ Creates a POST request """
        self._raw_connection.request('POST', url, body, {})

    def _run(self):
        """ Wait for response """
        self.responce = self._raw_connection.getresponse()
        self.responce_lock.release()

    def get_response(self):
        """ Wait for response (in a new thread) """
        self.responce_lock.acquire()
        thread.start_new_thread(HTTPConn._run, (self, ))

    def has_result(self):
        """ If the look is free, then we have a response """
        if self.responce_lock.acquire(False):
            self.responce_lock.release()
            return True
        else:
            return False

    def get_result(self):
        """ Get the result """
        while not self.has_result() and not self.closing:
            time.sleep(1)
        return self.responce

    def close(self):
        """ Close the connection """
        self.closing = True
        self._raw_connection.close()

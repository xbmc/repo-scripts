import time
import thread
import threading

try:
    import http.client as httplib  # 3.0+
except ImportError:
    import httplib  # 2.7


class HTTPConn():
    def __init__(self, host, port=None):
        self.rawConnection = httplib.HTTPConnection(host, port, None, None)
        self.responce = None
        self.responceLock = threading.Lock()
        self.closing = False

    def request(self, url, body=None):
        self.rawConnection.request('POST', url, body, {})

    def _run(self):
        self.responce = self.rawConnection.getresponse()
        self.responceLock.release()

    def go(self):
        self.responceLock.acquire()
        thread.start_new_thread(HTTPConn._run, (self, ))

    def hasResult(self):
        if self.responceLock.acquire(False):
            self.responceLock.release()
            return True
        else:
            return False

    def getResult(self):
        while not self.hasResult() and not self.closing:
            time.sleep(1)
        return self.responce

    def close(self):
        self.closing = True
        self.rawConnection.close()

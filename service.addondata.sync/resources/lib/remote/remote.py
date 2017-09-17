from BaseHTTPServer import HTTPServer
import thread

from event import Event
from remote_handler import RemoteRequestHandler


class Remote(HTTPServer):
    HostName = "127.0.0.1"
    Port = 5454

    def __init__(self, logger=None):
        HTTPServer.__init__(self, (Remote.HostName, Remote.Port), RemoteRequestHandler)
        self.onEventReceived = Event()
        self.onSyncTriggered = Event()
        self.__thread = None
        self.__logger = logger

    def start(self):
        if self.__logger:
            self.__logger.info("Starting remote control on %s:%d", self.server_address[0], self.server_address[1])
        self.__thread = thread.start_new_thread(self.serve_forever, ())

    def stop(self):
        self.shutdown()


if __name__ == '__main__':
    def event_received(remote_address, remote_port, path):
        print remote_address, remote_port, path

    server = Remote()
    server.onEventReceived += event_received
    server.serve_forever()
    # # Some stuff to make it not run forever
    # import thread
    # import time
    # # noinspection PyArgumentList
    # worker = thread.start_new_thread(server.serve_forever)
    # i = 0
    # while i < 2:
    #     time.sleep(1)
    #     i += 1
    #
    # server.shutdown()
    # print "Done"

# -*- coding: utf-8 -*-
import contextlib
import operator
import socket
import struct
import threading

from resources.lib.kodi import kodilogging
from resources.lib.kodi.utils import get_setting_as_bool
from resources.lib.tubecast.kodicast import Kodicast
from resources.lib.tubecast.utils import build_template, str_to_bytes, PY3

if PY3:
    from socketserver import DatagramRequestHandler, ThreadingUDPServer
else:
    from SocketServer import DatagramRequestHandler, ThreadingUDPServer


logger = kodilogging.get_logger()


def get_interface_address(if_name):
    import fcntl  # late import as this is only supported on Unix platforms.
    sciocgifaddr = 0x8915
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        return fcntl.ioctl(s.fileno(), sciocgifaddr, struct.pack(b'256s', if_name[:15]))[20:24]


class ControlMixin(object):

    def __init__(self, handler, poll_interval):
        self._thread = None
        self.poll_interval = poll_interval
        self._handler = handler

    def start(self):
        self._thread = t = threading.Thread(name=type(self).__name__,
                                            target=self.serve_forever,
                                            args=(self.poll_interval,))
        t.setDaemon(True)
        t.start()

    def stop(self):
        self.shutdown()
        self._thread.join()
        self._thread = None


class MulticastServer(ControlMixin, ThreadingUDPServer):

    allow_reuse_address = True

    def __init__(self, addr, handler, poll_interval=0.5, bind_and_activate=True, interfaces=None):
        ThreadingUDPServer.__init__(self, ('', addr[1]),
                                    handler,
                                    bind_and_activate)
        ControlMixin.__init__(self, handler, poll_interval)
        self._multicast_address = addr
        self._listen_interfaces = interfaces
        self.set_loopback_mode(1)  # localhost
        self.set_ttl(2)  # localhost and local network
        self.handle_membership(socket.IP_ADD_MEMBERSHIP)

    def set_loopback_mode(self, mode):
        mode = struct.pack("b", operator.truth(mode))
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP,
                               mode)

    def server_bind(self):
        try:
            if hasattr(socket, "SO_REUSEADDR"):
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception as e:
            logger.error(e)
        try:
            if hasattr(socket, "SO_REUSEPORT"):
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except Exception as e:
            logger.error(e)
        ThreadingUDPServer.server_bind(self)

    def handle_membership(self, cmd):
        if self._listen_interfaces is None:
            mreq = struct.pack(
                str("4sI"), socket.inet_aton(self._multicast_address[0]),
                socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   cmd, mreq)
        else:
            for interface in self._listen_interfaces:
                try:
                    if_addr = socket.inet_aton(interface)
                except socket.error:
                    if_addr = get_interface_address(interface)
                mreq = socket.inet_aton(self._multicast_address[0]) + if_addr
                self.socket.setsockopt(socket.IPPROTO_IP,
                                       cmd, mreq)

    def set_ttl(self, ttl):
        ttl = struct.pack("B", ttl)
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def server_close(self):
        self.handle_membership(socket.IP_DROP_MEMBERSHIP)


class SSDPHandler(DatagramRequestHandler):

    header = '''\
HTTP/1.1 200 OK\r
LOCATION: http://{{ ip }}:8008/ssdp/device-desc.xml\r
CACHE-CONTROL: max-age=1800\r
EXT: \r
SERVER: UPnP/1.0\r
BOOTID.UPNP.ORG: 1\r
USN: uuid:{{ uuid }}\r
ST: urn:dial-multiscreen-org:service:dial:1\r
\r
'''

    def handle(self):
        data = self.request[0].strip()
        self.datagram_received(data, self.client_address)

    def reply(self, data, address):
        socket = self.request[1]
        socket.sendto(str_to_bytes(data), address)

    @staticmethod
    def get_remote_ip(address):
        # Create a socket to determine what address the client should use
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(address)
        iface = s.getsockname()[0]
        return iface if PY3 else unicode(iface)

    def datagram_received(self, datagram, address):
        if get_setting_as_bool('debug-ssdp'):
            logger.debug('Datagram received. Address:{}; Content:{}'.format(address, datagram))
        if b"urn:dial-multiscreen-org:service:dial:1" in datagram and b"M-SEARCH" in datagram:
            if get_setting_as_bool('debug-ssdp'):
                logger.debug("Answering datagram")
            data = build_template(self.header).render(
                ip=self.get_remote_ip(address),
                uuid=Kodicast.uuid
            )
            self.reply(data, address)


class SSDPserver(object):
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900

    def start(self, interfaces=None):
        logger.info('Starting SSDP server')
        self.server = MulticastServer((self.SSDP_ADDR, self.SSDP_PORT), SSDPHandler, interfaces=interfaces)
        self.server.start()

    def shutdown(self):
        logger.info('Stopping SSDP server')
        self.server.server_close()
        self.server.stop()

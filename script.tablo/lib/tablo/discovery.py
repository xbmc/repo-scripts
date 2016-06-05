import binascii
import socket
import traceback
import struct
import time
import datetime
import requests

# from lib import util
import util

DEVICE_DISCOVERY_PORT = 8881
DEVICE_REPLY_PORT = 8882

ASSOCIATION_SERVER_DISCOVERY_URL = 'https://api.tablotv.com/assocserver/getipinfo/'


def truncZero(string):
    return string.split('\0')[0]


class TabloDevice:
    port = 8885

    def __init__(self, data):
        self.ID = data.get('serverid')
        self.name = data.get('name')
        self.IP = data.get('private_ip')
        self.publicIP = data.get('public_ip')
        self.SSL = data.get('ssl')
        self.host = data.get('host')
        self.version = data.get('server_version')
        self.boardType = data.get('board_type')
        self.seen = self.processDate(data.get('last_seen'))
        self.inserted = self.processDate(data.get('inserted'))
        self.modified = self.processDate(data.get('modified'))

    def __repr__(self):
        return '<TabloDevice:{0}:{1}>'.format(self.ID, self.IP)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if not isinstance(other, TabloDevice):
            return False
        return self.ID == other.ID or self.IP == other.IP

    def processDate(self, date):
        if not date:
            return None

        try:
            return datetime.datetime.strptime(date[:-6], '%Y-%m-%d %H:%M:%S.%f')
        except:
            traceback.print_exc()
        return None

    def address(self):
        return '{0}:{1}'.format(self.IP, self.port)

    def valid(self):
        return True

    def check(self):
        if not self.name:
            self.updateInfoFromDevice()

    def updateInfoFromDevice(self):
        try:
            data = requests.get('http://{0}/server/info'.format(self.address())).json()
        except:
            traceback.print_exc()
            return

        self.name = data['name']
        self.version = data['version']
        self.ID = self.ID or data.get('server_id')

    @property
    def displayName(self):
        return self.name or self.host


class Devices(object):
    MAX_AGE = 3600

    def __init__(self):
        self.reDiscover()

    def __contains__(self, device):
        for d in self.tablos:
            if d == device:
                return True
        return False

    def reDiscover(self):
        self._discoveryTimestamp = time.time()
        self.tablos = []
        self.discover()
        if self.tablos:
            util.DEBUG_LOG('Device(s) found via local discovery')
        else:
            util.DEBUG_LOG('No devices found via local discovery - trying association server')
            self.associationServerDiscover()

    def discover(self, device=None):
        import netif
        ifaces = netif.getInterfaces()
        sockets = []
        for i in ifaces:
            if not i.broadcast:
                continue
            # if i.ip.startswith('127.'): continue
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.01)  # 10ms
            s.bind((i.ip, 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sockets.append((s, i))
        packet = struct.pack('>4s', 'BnGr')
        util.DEBUG_LOG('  o-> Broadcast Packet({0})'.format(binascii.hexlify(packet)))

        for attempt in (0, 1):
            for s, i in sockets:
                util.DEBUG_LOG('  o-> Broadcasting to {0}: {1}'.format(i.name, i.broadcast))
                try:
                    s.sendto(packet, (i.broadcast, DEVICE_DISCOVERY_PORT))
                except:
                    util.ERROR()

            end = time.time() + 0.25  # 250ms

            # Create reply socket
            rs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rs.settimeout(0.01)  # 10ms
            rs.bind(('', DEVICE_REPLY_PORT))
            rs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            while time.time() < end:
                try:
                    message, address = rs.recvfrom(8096)

                    added = self.add(message, address)

                    if added:
                        util.DEBUG_LOG('<-o   Response Packet({0})'.format(binascii.hexlify(message)))
                    elif added is False:
                        util.DEBUG_LOG('<-o   Response Packet(Duplicate)')
                    elif added is None:
                        util.DEBUG_LOG('<-o   INVALID RESPONSE({0})'.format(binascii.hexlify(message)))
                except socket.timeout:
                    pass
                except:
                    traceback.print_exc()

            for d in self.tablos:
                d.check()

    def createDevice(self, packet, address):
        data = {}

        v = struct.unpack('>4s64s32s20s10s10s', packet)

        # key = v[0]
        data['host'] = truncZero(v[1])
        data['private_ip'] = truncZero(v[2])
        data['serverid'] = truncZero(v[3])
        typ = truncZero(v[4])
        # styp = truncZero(v[5])

        if not typ == 'tablo':
            return None

        return TabloDevice(data)

    def add(self, packet, address):
        device = self.createDevice(packet, address)

        if not device or not device.valid:
            return None
        elif device in self:
            return False

        self.tablos.append(device)

        return True

    def associationServerDiscover(self):
        r = requests.get(ASSOCIATION_SERVER_DISCOVERY_URL)
        try:
            data = r.json()
            if not data.get('success'):
                return False
            deviceData = data.get('cpes')
        except:
            traceback.print_exc()
            return False

        self.tablos = [TabloDevice(d) for d in deviceData]

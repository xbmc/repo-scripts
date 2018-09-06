# -*- coding: utf-8 -*-
import crc32c
import binascii
import socket
import traceback
import struct
import StringIO
import time
import base64
import requests
import errors
from lib import util

DEVICE_DISCOVERY_PORT = 65001

#Packet types
DISCOVER_RESPONSE = 0x0003

#Devices
TUNER_DEVICE = 0x00000001
STORAGE_SERVER = 0x00000005

#Tags
DEVICE_TYPE = 0x01
DEVICE_ID = 0x02
LINEUP_URL = 0x27
STORAGE_URL = 0x28
DEVICE_AUTH = 0x29
DEVICE_AUTH_STRING = 0x2B
STORAGE_SERVER_BASE_URL = 0x2A

LINEUP_URL_BASE = 'http://{ip}/lineup.json'

ID_COUNTER = 0

def getNextID():
    global ID_COUNTER
    ID_COUNTER+=1
    return ID_COUNTER

class Devices(object):
    MAX_AGE = 3600

    def __init__(self):
        self.reDiscover()

    def reDiscover(self):
        self._discoveryTimestamp = time.time()
        self._storageServers = []
        self._tunerDevices = {}
        self._other = []
        self.discover()

    def discover(self, device=None):
        import netif
        ifaces = netif.getInterfaces()
        sockets = []
        for i in ifaces:
            if not i.broadcast: continue
            #if i.ip.startswith('127.'): continue
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.01) #10ms
            s.bind((i.ip, 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sockets.append((s,i))
        payload = struct.pack('>BBI',0x01,0x04,0xFFFFFFFF) #Device Type Filter (any)
        payload += struct.pack('>BBI',0x02,0x04,0xFFFFFFFF) #Device ID Filter (any)
        header = struct.pack('>HH',0x0002,len(payload))
        data = header + payload
        crc = crc32c.cksum(data)
        packet = data + struct.pack('>I',crc)
        util.DEBUG_LOG('  o-> Broadcast Packet({0})'.format(binascii.hexlify(packet)))

        for attempt in (0,1):
            for s,i in sockets:
                util.DEBUG_LOG('  o-> Broadcasting to {0}: {1}'.format(i.name,i.broadcast))
                try:
                    s.sendto(packet, (i.broadcast, DEVICE_DISCOVERY_PORT))
                except:
                    util.ERROR()

            end = time.time() + 0.25 #250ms

            while time.time() < end:
                for s,i in sockets:
                    try:
                        message, address = s.recvfrom(8096)

                        added = self.add(message,address)

                        if added:
                            util.DEBUG_LOG('<-o   Response Packet[{0}]({1})'.format(i.name,binascii.hexlify(message)))
                        elif added == False:
                            util.DEBUG_LOG('<-o   Response Packet[{0}](Duplicate)'.format(i.name))
                        elif added == None:
                            util.DEBUG_LOG('<-o   INVALID RESPONSE[{0}]({1})'.format(i.name,binascii.hexlify(message)))
                    except socket.timeout:
                        pass
                    except:
                        traceback.print_exc()

    def __contains__(self, device):
        for d in self.allDevices:
            if d == device: return True
        return False

    @property
    def storageServers(self):
        return self._storageServers

    @property
    def tunerDevices(self):
        return self._tunerDevices.values()

    @property
    def allDevices(self):
        return self.tunerDevices + self.storageServers + self._other

    def isOld(self):
        return (time.time() - self._discoveryTimestamp) > self.MAX_AGE

    def tunerDevice(self,ID):
        return self._tunerDevices.get('ID')

    def defaultTunerDevice(self):
        #Return device with the most number of channels as default
        highest = None
        for d in self._tunerDevices.values():
            if not highest or highest.channelCount < d.channelCount:
                highest = d
        return highest

    def hasTunerDevices(self):
        return bool(self._tunerDevices)

    def hasStorageServers(self):
        return bool(self._storageServers)

    def createDevice(self,packet,address):
        try:

            header = packet[:4]
            data = packet[4:-4]
            chksum = packet[-4:]

            self.responseType, packetLength = struct.unpack('>HH',header)
            if not self.responseType == DISCOVER_RESPONSE:
                util.DEBUG_LOG('WRONG RESPONSE TYPE')
                return None

            if packetLength != len(data):
                util.DEBUG_LOG('BAD PACKET LENGTH')
                return None

            if chksum != struct.pack('>I',crc32c.cksum(header + data)):
                util.DEBUG_LOG('BAD CRC')
                return None
        except:
            traceback.print_exc()
            return None

        dataIO = StringIO.StringIO(data)

        tag, length = struct.unpack('>BB',dataIO.read(2))
        deviceType = struct.unpack('>I',dataIO.read(length))[0]

        if deviceType == TUNER_DEVICE:
            return self.processData(TunerDevice(address),dataIO)
        elif deviceType == STORAGE_SERVER:
            return self.processData(StorageServer(address),dataIO)
        else:
            return self.processData(Device(address),dataIO)

    def processData(self,device,dataIO):
        while True:
            header = dataIO.read(2)
            if not header: return device
            tag, length = struct.unpack('>BB',header)
            if tag == DEVICE_ID:
                device._id = struct.unpack('>I',dataIO.read(length))[0]
                device.ID = hex(device._id)[2:]
            elif tag == LINEUP_URL:
                device.lineUpURL = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == STORAGE_URL:
                device._storageURL = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == DEVICE_AUTH:
                device._deviceAuth = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == DEVICE_AUTH_STRING:
                device._deviceAuthString = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == STORAGE_SERVER_BASE_URL:
                device._baseURL = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            else:
                dataIO.read(length)
        return device

    def add(self,packet, address):
        device = self.createDevice(packet,address)

        if not device or not device.valid:
            return None
        elif device in self:
            return False

        if isinstance(device,TunerDevice):
            self._tunerDevices[device.ID] = device
        elif isinstance(device,StorageServer):
            self._storageServers.append(device)
        else:
            self._other.append(device)

        return True

    def getDeviceByIP(self,ip):
        for d in self.tunerDevices + self.storageServers:
            if d.ip == ip:
                return d
        return None

    def apiAuthID(self):
        combined = ''
        ids = []
        for d in self.tunerDevices:
            ids.append(d.ID)
            authID = d.deviceAuth
            if not authID: continue
            combined += authID

        if not combined:
            util.LOG('WARNING: No device auth for any devices!')
            raise errors.NoDeviceAuthException()

        #return base64.standard_b64encode(combined)
        return combined

class Device(object):
    typeName = 'Unknown'
    def __init__(self,address): self.ip, self.port = address

    def __ne__(self,other): return not self.__eq__(other)

    def __str__(self): return self.__repr__()

    def __repr__(self): return '<Device type={0}:ip={1}>'.format(getattr(self,'device','?'),self.ip)

    @property
    def valid(self): return False

    @property
    def url(self): return ''

    def display(self): return repr(self)


class TunerDevice(Device):
    typeName = 'TunerDevice'

    def __init__(self,address):
        Device.__init__(self,address)
        self.channelCount = 0

    def __eq__(self,other):
        if not isinstance(other,TunerDevice): return False
        return self._id == other._id

    def __repr__(self):
        return '<TunerDevice id={0}:url={1}>'.format(getattr(self,'ID','?'),self.url or '?')

    @property
    def valid(self):
        return hasattr(self,'ID')

    @property
    def url(self):
        url = getattr(self,'lineUpURL',None)
        if not url:
            url = LINEUP_URL_BASE.format(ip=self.ip)

        if '?' in url:
            url += '&show=demo'
        else:
            url += '?show=demo'

        return url

    @property
    def deviceAuth(self):
        authString = getattr(self,'_deviceAuthString',None)
        if authString:
            return authString

        authBinary = getattr(self,'_deviceAuth',None)
        if authBinary:
            return base64.standard_b64encode(authBinary)

        return None

    def display(self):
        try:
            out = '\nDevice at {ip}:\n    ID: {ID}\n    Type: {dtype}\n    DeviceAuth: {auth}\n    URL: {url}\n    Channels: {chancount}'
            return out.format(ip=self.ip,dtype=self.typeName,ID=getattr(self,'ID','?'),auth=self.deviceAuth,url=self.url,chancount=self.channelCount)
        except:
            util.ERROR('Failed to format {0} info'.format(self.typeName),hide_tb=True)

    def lineUp(self):
        req = requests.get(self.url)

        try:
            lineUp = req.json()
            self.channelCount = len(lineUp)
            return lineUp
        except:
            util.ERROR('Failed to parse lineup JSON data. Older device?',hide_tb=True)
            return None

class StorageServer(Device):
    typeName = 'StorageServer'
    _ruleSyncURI = 'recording_events.post?sync'
    _recordingsURI = 'recorded_files.json'

    def __init__(self,address):
        Device.__init__(self,address)
        self.ID = getNextID()

    def __eq__(self,other):
        if not isinstance(other,StorageServer): return False
        return self._baseURL == other._baseURL

    def __repr__(self):
        return '<StorageServer url={0}>'.format(self._baseURL or '?')

    @property
    def valid(self):
        return hasattr(self,'_baseURL')

    @property
    def storageURL(self):
        return getattr(self,'_storageURL','') or self.url(self._recordingsURI)

    def url(self,path):
        return getattr(self,'_baseURL','') + '/' + path

    def display(self):
        try:
            out = '\nDevice at {ip}:\n    Type: {dtype}\n    URL: {url}'
            return out.format(ip=self.ip,dtype=self.typeName,url=self._baseURL)
        except:
            util.ERROR('Failed to format {0} info'.format(self.typeName),hide_tb=True)

    def recordings(self):
        util.DEBUG_LOG('Getting recordings from: {0}'.format(self.storageURL))
        req = requests.get(self.storageURL)

        try:
            recordings = req.json()
            return recordings
        except:
            util.ERROR('Failed to parse recordings JSON data.',hide_tb=True)
            return None

    def syncRules(self):
        util.DEBUG_LOG('Pinging storage Server: {0}'.format(self._baseURL))

        requests.post(self.url(self._ruleSyncURI))


# -*- coding: utf-8 -*-
import crc32c
import binascii
import socket
import traceback
import struct
import StringIO
import time
import base64

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

LINEUP_URL_BASE = 'http://{ip}/lineup.json'


class DiscoveryResponse(object):
    def __init__(self,packet,address):
        self.ip, self.port = address
        self.tags = {}
        self.valid = self.processPacket(packet)
        self.channelCount = 0

    def __eq__(self,other):
        if self.responseType != other.responseType: return False
        if self.device != other.device: return False
        if self.device == TUNER_DEVICE:
            return self._id == other._id
        elif self.device == STORAGE_SERVER:
            return self.storageURL == other.storageURL
        return True

    def __ne__(self,other):
        return not self.__eq__(other)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<DiscoveryResponse device={0}:id={1}:url={2}>'.format(getattr(self,'device','?'),getattr(self,'ID','?'),self.url or '?')

    @property
    def url(self):
        if self.device == TUNER_DEVICE:
            url = getattr(self,'lineUpURL',None)
            if not url:
                url = LINEUP_URL_BASE.format(ip=self.ip)
            return url
        elif self.device == STORAGE_SERVER:
            return getattr(self,'storageURL','')

    @property
    def deviceAuth(self):
        return getattr(self,'_deviceAuth',None)

    def processPacket(self,packet):
        try:
            header = packet[:4]
            self.responseType, packetLength = struct.unpack('>HH',header)
            if not self.responseType == DISCOVER_RESPONSE:
                util.DEBUG_LOG('WRONG RESPONSE TYPE')
                return False
            data = packet[4:-4]
            chksum = packet[-4:]

            if packetLength != len(data):
                util.DEBUG_LOG('BAD PACKET LENGTH')
                return False

            if chksum != struct.pack('>I',crc32c.cksum(header + data)):
                util.DEBUG_LOG('BAD CRC')
                return False
        except:
            traceback.print_exc()
            return False

        self.processData(data)
        return True

    def processData(self,data):
        dataIO = StringIO.StringIO(data)
        while True:
            header = dataIO.read(2)
            if not header: return
            tag, length = struct.unpack('>BB',header)
            if tag == DEVICE_TYPE:
                self.device = struct.unpack('>I',dataIO.read(length))[0]
            elif tag == DEVICE_ID:
                self._id = struct.unpack('>I',dataIO.read(length))[0]
                self.ID = hex(self._id)[2:]
            elif tag == LINEUP_URL:
                self.lineUpURL = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == STORAGE_URL:
                self.storageURL = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            elif tag == DEVICE_AUTH:
                self._deviceAuth = struct.unpack('>{0}s'.format(length),dataIO.read(length))[0]
            else:
                dataIO.read(length)

    def typeName(self):
        if self.device == TUNER_DEVICE:
            return 'Tuner'
        elif self.device == STORAGE_SERVER:
            return 'Storage Server'
        return 'Unknown'

    def display(self):
        out = '\nDevice at {ip}:\n    ID: {ID}\n    Type: {dtype}\n    DeviceAuth: {auth}\n    URL: {url}\n    Channels: {chancount}'
        try:
            return out.format(ip=self.ip,dtype=self.typeName(),ID=self.ID,auth=base64.standard_b64encode(self.deviceAuth),url=self.url,chancount=self.channelCount)
        except:
            util.ERROR('Failed to format device info',hide_tb=True)
            return repr(self)


def discover(device=None):
    import netif
    ifaces = netif.getInterfaces()
    sockets = []
    for i in ifaces:
        if not i.broadcast: continue
        if i.ip.startswith('127.'): continue
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.01) #10ms
        s.bind((i.ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sockets.append((s,i))
    payload = struct.pack('>BBI',0x01,0x04,0x00000001) #Device Type Filter (tuner)
    payload += struct.pack('>BBI',0x02,0x04,0xFFFFFFFF) #Device ID Filter (any)
    header = struct.pack('>HH',0x0002,len(payload))
    data = header + payload
    crc = crc32c.cksum(data)
    packet = data + struct.pack('>I',crc)
    util.DEBUG_LOG('  o-> Broadcast Packet({0})'.format(binascii.hexlify(packet)))
    responses = []
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
                    response = DiscoveryResponse(message,address)
                    if response.valid and (not device or device == response.device) and not response in responses:
                        responses.append(response)
                        util.DEBUG_LOG('<-o   Response Packet[{0}]({1})'.format(i.name,binascii.hexlify(message)))
                    elif response.valid:
                        util.DEBUG_LOG('<-o   Response Packet[{0}](Duplicate)'.format(i.name))
                    else:
                        util.DEBUG_LOG('<-o   INVALID RESPONSE[{0}]({1})'.format(i.name,binascii.hexlify(message)))
                except socket.timeout:
                    pass
                except:
                    traceback.print_exc()

    return responses


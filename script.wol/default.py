# Wake-On-LAN

import struct, socket
import xbmcaddon

# mac adress example '00:25:11:c4:fb:8a'

def WakeOnLan(mac_address):

  addr_bytes = mac_address.split(':')
  addr = struct.pack('BBBBBB', int(addr_bytes[0], 16),
    int(addr_bytes[1], 16),
    int(addr_bytes[2], 16),
    int(addr_bytes[3], 16),
    int(addr_bytes[4], 16),
    int(addr_bytes[5], 16))

  packet = '\xff' * 6 + addr * 16

  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  s.sendto(packet, ('<broadcast>', 9))
  s.close()

settings = xbmcaddon.Addon(id = 'script.wol')
mac_address = settings.getSetting("macaddress")

WakeOnLan(mac_address)

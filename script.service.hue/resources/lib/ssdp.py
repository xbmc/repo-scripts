#   Copyright 2014 Dan Krause, Python 3 hack 2016 Adam Baxter,
#       Server field addition and Win32 mod 2017 Andre Wagner
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import socket
import http.client
import io
import sys
from urllib.parse import urlsplit


class SSDPResponse(object):
    class _FakeSocket(io.BytesIO):
        def makefile(self, *args, **kw):
            return self
    def __init__(self, response):
        r = http.client.HTTPResponse(self._FakeSocket(response))
        r.begin()
        self.location = r.getheader("location")
        self.usn = r.getheader("usn")
        self.st = r.getheader("st")
        self.cache = r.getheader("cache-control").split("=")[1]
        self.server = r.getheader("server")
    def __repr__(self):
        return "<SSDPResponse({location}, {st}, {usn}, {server})>".format(**self.__dict__)

def discover(service, timeout=5, retries=1, mx=3):
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: {0}:{1}',
        'MAN: "ssdp:discover"',
        'ST: {st}','MX: {mx}','',''])
    socket.setdefaulttimeout(timeout)
    responses = {}
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        message_bytes = message.format(*group, st=service, mx=mx).encode('utf-8')
        sock.sendto(message_bytes, group)


        # see https://stackoverflow.com/questions/32682969
        #if sys.platform == "win32":
        #    hosts = socket.gethostbyname_ex(socket.gethostname())[2]
        #    for host in hosts:
        #        sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host))
        #        sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
        #                        socket.inet_aton(group[0]) + socket.inet_aton(host))
                #logger.debug('M-SEARCH on %s', host)
        #        sock.sendto(message_bytes, group)
        #else:
            #logger.debug('M-SEARCH')
        #    sock.sendto(message_bytes, group)


        while True:
            try:
                response = SSDPResponse(sock.recv(1024))
                responses[response.location] = response
                #logger.debug('Response from %s',urlsplit(response.location).netloc)
            except socket.timeout:
                break
    return list(responses.values())

# Example:
# import ssdp
# ssdp.discover("roku:ecp")

##
##if __name__ == '__main__':
##    logging.basicConfig(level=logging.DEBUG,                                                 \
##        format='%(asctime)s.%(msecs)03d %(levelname)s:%(module)s:%(funcName)s: %(message)s', \
##        datefmt="%Y-%m-%d %H:%M:%S")

##    devices = discover("ssdp:all", timeout=8)
##   print('\nDiscovered {} device{pl}.'.format(len(devices), pl='s' if len(devices)!=1 else ''))
##    for device in devices: print('  {0.location} ==> {0.server}'.format(device))
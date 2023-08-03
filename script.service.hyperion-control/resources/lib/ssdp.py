"""
Hyperion UPnP / SSDP service discovery.

Copyright 2014 Dan Krause
Copyright 2023 Andrea Ghensi

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

All credits to Dan Krause at Github: https://gist.github.com/dankrause/6000248
"""
from __future__ import annotations

import http.client
import socket
from io import BytesIO
from typing import Any


class _FakeSocket(BytesIO):
    """Fake socket to make ssdp response compatible with HTTPResponse."""

    def makefile(self, *_args: Any, **_kw: Any) -> BytesIO:
        """Duck-types the call to make the socket available."""
        return self


def _parse_location(location: str | None) -> tuple[str, int]:
    if location is None:
        return "", 0
    start = location.find("//") + 2
    end = location.rfind("/")
    hostname, port = location[start:end].split(":")
    return hostname, int(port)


class SSDPResponse:
    """
    Response from SSDP discovery.

    Typical Hyperion response:

    CACHE-CONTROL: max-age = 1800
    DATE: Sun, 23 Jul 2023 19:58:01 G7T19444
    EXT:
    LOCATION: http://192.168.2.180:8090/description.xml
    SERVER: LibreELEC (official): 11.0.1/11.0 UPnP/1.0 Hyperion/2.0.16-beta.1+PR1617
    ST: urn:hyperion-project.org:device:basic:1
    USN: uuid:04928741-2192-5c24-93e6-638c9a184443
    HYPERION-FBS-PORT: 19400
    HYPERION-JSS-PORT: 19444
    HYPERION-NAME: My Hyperion Config
    """

    def __init__(self, response: bytes) -> None:
        r = http.client.HTTPResponse(_FakeSocket(response))  # type: ignore
        r.begin()
        hostname, port = _parse_location(r.getheader("location"))
        self.hostname = hostname
        self.port = port
        self.usn = r.getheader("usn")
        self.st = r.getheader("st")
        cache = r.getheader("cache-control")
        self.cache = cache.split("=")[1] if cache else ""


def discover(timeout: int = 3, retries: int = 1, mx: int = 2) -> list[dict[str, Any]]:
    service = "urn:hyperion-project.org:device:basic:1"
    group = ("239.255.255.250", 1900)
    lines = [
        "M-SEARCH * HTTP/1.1",
        f"HOST: {group[0]}:{group[1]}",
        'MAN: "ssdp:discover"',
        f"ST: {service}",
        f"MX: {mx}",
        "",
        "",
    ]
    message = "\r\n".join(lines).encode("utf-8")
    socket.setdefaulttimeout(timeout)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    responses = []
    for _ in range(retries):
        sock.sendto(message, group)
        while True:
            try:
                res_data = SSDPResponse(sock.recv(1024))
                if res_data.st != service:
                    continue
                responses.append(
                    {
                        "ip": res_data.hostname,
                        "port": res_data.port,
                        "usn": res_data.usn,
                    }
                )
            except socket.timeout:
                break
    sock.close()
    return responses

"""Minimal mDNS discovery for Philips Hue bridges.

Uses only Python stdlib (socket, struct) to send a multicast DNS query for
``_hue._tcp.local.`` and parse the first A record from the response.
"""
#      Copyright (C) 2023 Kodi Hue Service (script.service.hue)
#      This file is part of script.service.hue
#      SPDX-License-Identifier: MIT
#      See LICENSE.TXT for more information.

import socket
import struct
import time

from .kodiutils import log

MDNS_ADDR = "224.0.0.251"
MDNS_PORT = 5353
SERVICE_NAME = "_hue._tcp.local."

# DNS record types
TYPE_A = 1
TYPE_PTR = 12

# DNS class
CLASS_IN = 1


def _encode_dns_name(name):
    """Encode a dotted domain name into DNS wire format.

    Args:
        name: Dotted domain name (e.g. ``"_hue._tcp.local."``).

    Returns:
        Bytes in DNS label format.
    """
    parts = name.rstrip(".").split(".")
    result = b""
    for part in parts:
        encoded = part.encode("ascii")
        result += struct.pack("B", len(encoded)) + encoded
    result += b"\x00"
    return result


def _build_query():
    """Build a DNS PTR query packet for the Hue service.

    Returns:
        Bytes containing the complete DNS query packet.
    """
    transaction_id = 0x0000
    flags = 0x0000
    questions = 1
    header = struct.pack("!HHHHHH", transaction_id, flags, questions, 0, 0, 0)
    qname = _encode_dns_name(SERVICE_NAME)
    question = qname + struct.pack("!HH", TYPE_PTR, CLASS_IN)
    return header + question


def _read_name(data, offset):
    """Read a DNS name from a response packet, handling compression pointers.

    Args:
        data: Raw DNS response bytes.
        offset: Starting byte offset.

    Returns:
        Tuple of ``(name_string, new_offset)`` where ``new_offset`` points past
        the name in the original data.
    """
    labels = []
    original_offset = None
    while True:
        if offset >= len(data):
            break
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:
            if original_offset is None:
                original_offset = offset + 2
            pointer = struct.unpack_from("!H", data, offset)[0] & 0x3FFF
            offset = pointer
            continue
        offset += 1
        labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
        offset += length
    name = ".".join(labels)
    return name, (original_offset if original_offset is not None else offset)


def _parse_response(data):
    """Parse a DNS response and extract the first A record IP address.

    Args:
        data: Raw DNS response bytes.

    Returns:
        IP address string from the first A record, or ``None`` if not found.
    """
    if len(data) < 12:
        return None

    qdcount, ancount, nscount, arcount = struct.unpack_from("!HHHH", data, 4)
    offset = 12

    # Skip questions
    for _ in range(qdcount):
        _, offset = _read_name(data, offset)
        offset += 4  # QTYPE + QCLASS

    # Parse all answer, authority, and additional records looking for A records
    total_records = ancount + nscount + arcount
    for _ in range(total_records):
        if offset >= len(data):
            break
        name, offset = _read_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, rclass, ttl, rdlength = struct.unpack_from("!HHIH", data, offset)
        offset += 10
        if rtype == TYPE_A and rdlength == 4:
            ip = socket.inet_ntoa(data[offset:offset + 4])
            log(f"[SCRIPT.SERVICE.HUE] mDNS: A record found: {name} -> {ip}")
            return ip
        offset += rdlength

    return None


def discover_hue_bridge_mdns(timeout=2.0):
    """Discover a Hue bridge on the local network via mDNS.

    Sends a multicast DNS PTR query for ``_hue._tcp.local.`` and waits for a
    response containing an A record with the bridge's IP address.

    Args:
        timeout: Maximum time in seconds to wait for a response (default 2.0).

    Returns:
        Bridge IP address string, or ``None`` if no bridge was found or mDNS
        is unavailable (e.g. Android multicast restrictions).
    """
    log("[SCRIPT.SERVICE.HUE] mDNS: Querying for _hue._tcp.local.")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    except OSError as exc:
        log(f"[SCRIPT.SERVICE.HUE] mDNS: Cannot create socket: {exc}")
        return None

    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)

        # Set multicast TTL to 1 (local network only)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

        query = _build_query()
        sock.sendto(query, (MDNS_ADDR, MDNS_PORT))
        log("[SCRIPT.SERVICE.HUE] mDNS: Query sent, waiting for response...")

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                data, addr = sock.recvfrom(4096)
                log(f"[SCRIPT.SERVICE.HUE] mDNS: Response received from {addr[0]}")
                ip = _parse_response(data)
                if ip:
                    log(f"[SCRIPT.SERVICE.HUE] mDNS: Bridge found at {ip}")
                    return ip
            except socket.timeout:
                break

        log("[SCRIPT.SERVICE.HUE] mDNS: No bridge found within timeout")
        return None

    except OSError as exc:
        log(f"[SCRIPT.SERVICE.HUE] mDNS: Network error: {exc}")
        return None
    finally:
        sock.close()

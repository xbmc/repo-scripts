"""Tiny mDNS browser for ``_sendspin-server._tcp.local`` (standard library only).

Sends one multicast PTR query and parses PTR/SRV/TXT/A answers from replies.
Returns ``ws://host:port/path`` URLs. Good enough for a LAN with a single
Music Assistant; the user can always override the URL in settings.
"""

import logging
import random
import socket
import struct
import time

log = logging.getLogger("sendspin.discovery")

MDNS_ADDR = "224.0.0.251"
MDNS_PORT = 5353
SERVICE = "_sendspin-server._tcp.local"
T_A, T_PTR, T_TXT, T_SRV = 1, 12, 16, 33


def _encode_name(name):
    out = b""
    for label in name.strip(".").split("."):
        out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def _read_name(data, off):
    labels, jumped, end = [], False, off
    for _ in range(64):  # loop guard
        n = data[off]
        if n == 0:
            off += 1
            break
        if n & 0xC0 == 0xC0:
            ptr = struct.unpack(">H", data[off:off + 2])[0] & 0x3FFF
            if not jumped:
                end = off + 2
            off, jumped = ptr, True
            continue
        labels.append(data[off + 1: off + 1 + n].decode("utf-8", "replace"))
        off += 1 + n
    return ".".join(labels), (end if jumped else off)


def _parse(data):
    """Return list of (name, type, rdata_offset, rdlen, data) records."""
    _id, _flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    off = 12
    for _ in range(qd):
        _, off = _read_name(data, off)
        off += 4
    records = []
    for _ in range(an + ns + ar):
        name, off = _read_name(data, off)
        rtype, _cls, _ttl, rdlen = struct.unpack(">HHIH", data[off:off + 10])
        off += 10
        records.append((name.lower(), rtype, off, rdlen))
        off += rdlen
    return records


def discover(timeout=3.0):
    """Return a list of discovered server dicts: {name, url, host, port}."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    sock.settimeout(0.3)
    query = struct.pack(">HHHHHH", random.randint(0, 0xFFFF), 0, 1, 0, 0, 0)
    query += _encode_name(SERVICE) + struct.pack(">HH", T_PTR, 0x8001)  # QU bit: unicast reply
    found = {"instances": set(), "srv": {}, "txt": {}, "addrs": {}}
    try:
        sock.sendto(query, (MDNS_ADDR, MDNS_PORT))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, _ = sock.recvfrom(9000)
            except socket.timeout:
                continue
            _collect(data, found)
            if found["instances"] and all(_complete(i, found) for i in found["instances"]):
                break
    except OSError as exc:
        log.warning("mDNS discovery failed: %s", exc)
    finally:
        sock.close()
    return _servers(found)


def _collect(data, found):
    """Add the records in one mDNS reply to ``found``; malformed packets or records are skipped."""
    try:
        records = _parse(data)
    except (IndexError, ValueError, struct.error):
        return
    for name, rtype, off, rdlen in records:
        try:
            _decode_record(data, name, rtype, off, rdlen, found)
        except (IndexError, ValueError, struct.error):
            continue  # a malformed record from some device on the LAN


def _decode_record(data, name, rtype, off, rdlen, found):
    if off + rdlen > len(data):
        raise ValueError("truncated record")
    if rtype == T_PTR and name == SERVICE.lower():
        inst, _ = _read_name(data, off)
        found["instances"].add(inst.lower())
    elif rtype == T_SRV:
        if rdlen < 7:
            raise ValueError("short SRV record")
        _prio, _weight, port = struct.unpack(">HHH", data[off:off + 6])
        target, _ = _read_name(data, off + 6)
        found["srv"][name] = (target.lower(), port)
    elif rtype == T_TXT:
        entries, p = {}, off
        while p < off + rdlen:
            n = data[p]
            kv = data[p + 1:p + 1 + n].decode("utf-8", "replace")
            k, _, v = kv.partition("=")
            entries[k] = v
            p += 1 + n
        found["txt"][name] = entries
    elif rtype == T_A and rdlen == 4:
        found["addrs"][name] = socket.inet_ntoa(data[off:off + 4])


def _complete(inst, found):
    """True once an instance has its port, TXT (path) and an IPv4 address: no .local lookup needed."""
    srv = found["srv"].get(inst)
    return srv is not None and inst in found["txt"] and srv[0] in found["addrs"]


def _servers(found):
    servers = []
    for inst in found["instances"]:
        if inst not in found["srv"]:
            continue
        target, port = found["srv"][inst]
        host = found["addrs"].get(target) or target.rstrip(".")
        meta = found["txt"].get(inst, {})
        path = meta.get("path", "/sendspin") or "/sendspin"
        servers.append({
            "name": meta.get("name") or inst.split(".")[0],
            "host": host,
            "port": port,
            "url": "ws://%s:%d%s" % (host, port, path if path.startswith("/") else "/" + path),
        })
    return servers

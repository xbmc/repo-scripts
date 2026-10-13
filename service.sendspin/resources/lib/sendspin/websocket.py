"""Minimal, dependency-free WebSocket client (RFC 6455).

Kodi on Android cannot install compiled Python packages, so this module only
uses the standard library. It supports what Sendspin needs: text + binary
frames, fragmentation, ping/pong and close. No extensions, no TLS on purpose
(Sendspin runs on the local network; TLS can be added with ``ssl`` later).
"""

import base64
import hashlib
import os
import socket
import struct
import threading
from urllib.parse import urlparse

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_CONT = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA


# Sendspin messages are small (audio chunks are a few KB); anything bigger is not a real server.
MAX_MESSAGE_BYTES = 4 * 1024 * 1024

class WebSocketError(Exception):
    """Raised for protocol errors or a closed connection."""


class WebSocketClosed(WebSocketError):
    """Raised when the peer closed the connection."""


class WebSocket:
    """Blocking WebSocket client. ``recv()`` from one thread, ``send_*`` from any."""

    def __init__(self, url, timeout=10.0):
        self.url = url
        self._timeout = timeout
        self._sock = None
        self._send_lock = threading.Lock()
        self._rbuf = b""
        self.closed = True

    # -- connection -------------------------------------------------------
    def connect(self):
        u = urlparse(self.url)
        if u.scheme not in ("ws",):
            raise WebSocketError("only ws:// URLs are supported, got %r" % self.url)
        host, port = u.hostname, u.port or 80
        path = u.path or "/"
        if u.query:
            path += "?" + u.query
        sock = socket.create_connection((host, port), timeout=self._timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "User-Agent: kodi-sendspin\r\n\r\n" % (path, host, port, key)
        )
        sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = sock.recv(4096)
            if not chunk:
                raise WebSocketError("connection closed during handshake")
            resp += chunk
            if len(resp) > 65536:
                raise WebSocketError("handshake response too large")
        head, _, rest = resp.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise WebSocketError("handshake failed: %s" % lines[0])
        headers = {}
        for line in lines[1:]:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()
        expect = base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()
        if headers.get("sec-websocket-accept") != expect:
            raise WebSocketError("bad Sec-WebSocket-Accept")
        sock.settimeout(None)
        self._sock = sock
        self._rbuf = rest
        self.closed = False

    def close(self, code=1000):
        if self.closed:
            return
        try:
            self._send_frame(OP_CLOSE, struct.pack(">H", code))
        except Exception:  # noqa: BLE001 - best effort
            pass
        self._shutdown()

    def _shutdown(self):
        self.closed = True
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

    # -- sending ----------------------------------------------------------
    def send_text(self, text):
        self._send_frame(OP_TEXT, text.encode("utf-8"))

    def send_binary(self, data):
        self._send_frame(OP_BINARY, data)

    def _send_frame(self, opcode, payload):
        if self._sock is None:
            raise WebSocketClosed("not connected")
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = _mask(payload, mask)
        with self._send_lock:
            try:
                self._sock.sendall(bytes(header) + masked)
            except OSError as exc:
                self._shutdown()
                raise WebSocketClosed(str(exc)) from exc

    # -- receiving --------------------------------------------------------
    def _read_exact(self, n):
        while len(self._rbuf) < n:
            if self._sock is None:
                raise WebSocketClosed("socket closed")
            try:
                chunk = self._sock.recv(max(65536, n - len(self._rbuf)))
            except OSError as exc:
                self._shutdown()
                raise WebSocketClosed(str(exc)) from exc
            if not chunk:
                self._shutdown()
                raise WebSocketClosed("peer closed")
            self._rbuf += chunk
        data, self._rbuf = self._rbuf[:n], self._rbuf[n:]
        return data

    def recv(self):
        """Return ``(opcode, payload)`` for the next complete TEXT/BINARY message."""
        message_op = None
        parts = []
        total = 0
        while True:
            b1, b2 = self._read_exact(2)
            fin = b1 & 0x80
            opcode = b1 & 0x0F
            masked = b2 & 0x80
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read_exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read_exact(8))[0]
            total += n
            if n > MAX_MESSAGE_BYTES or total > MAX_MESSAGE_BYTES:
                self._shutdown()
                raise WebSocketError("message too large (%d bytes)" % total)
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(n) if n else b""
            if mask:
                payload = _mask(payload, mask)
            if opcode == OP_PING:
                self._send_frame(OP_PONG, payload)
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_CLOSE:
                try:
                    self._send_frame(OP_CLOSE, payload[:2])
                except WebSocketError:
                    pass
                self._shutdown()
                raise WebSocketClosed("close frame received")
            if opcode in (OP_TEXT, OP_BINARY):
                message_op = opcode
                parts = [payload]
                total = n
            elif opcode == OP_CONT:
                parts.append(payload)
            if fin and message_op is not None:
                data = b"".join(parts)
                if message_op == OP_TEXT:
                    return OP_TEXT, data.decode("utf-8")
                return OP_BINARY, data


def _mask(data, mask):
    """XOR-mask ``data`` with the 4-byte ``mask`` (fast path via int arithmetic)."""
    if not data:
        return b""
    n = len(data)
    repeated = (mask * (n // 4 + 1))[:n]
    return (int.from_bytes(data, "little") ^ int.from_bytes(repeated, "little")).to_bytes(n, "little")

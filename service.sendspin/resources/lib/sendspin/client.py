"""Sendspin player client (unencrypted / "legacy transition mode" wire).

Music Assistant 2.10 (aiosendspin 9.x) accepts unencrypted clients when its
"allow legacy clients" option is on (the default). Encrypted Noise sessions
are a TODO - they need X25519 + ChaCha20-Poly1305, which is too slow in pure
Python for a PCM stream on a Fire TV class CPU.

Threading model: one reader thread (``_run``) owns the socket receive side and
dispatches messages; one timer thread sends ``client/time`` probes. Callbacks
are invoked on the reader thread and must be quick.
"""

import json
import logging
import random
import struct
import threading
import time

from .audio import AudioFormat
from .clock import ClockSync, now_us
from .websocket import OP_BINARY, OP_TEXT, WebSocket, WebSocketError

log = logging.getLogger("sendspin.client")

PROTOCOL_VERSION = 1
BIN_AUDIO_CHUNK = 4
SUPPORTED_COMMANDS = ["volume", "mute"]  # set_static_delay is rejected in client/hello by MA 2.10


class Listener:
    """Override what you need. All callbacks run on the client thread."""

    def on_connected(self, server_name):
        pass

    def on_disconnected(self):
        pass

    def output_running(self):
        """True if the output (Kodi) is currently playing our stream."""
        return False

    def on_stream_start(self, fmt, generation, continuous=False):
        pass

    def on_stream_clear(self, generation):
        pass

    def on_stream_end(self):
        pass

    def on_metadata(self, metadata):
        pass

    def on_volume(self, volume, muted):
        pass

    def on_static_delay(self, delay_ms):
        pass

    def on_group(self, payload):
        pass


class SendspinClient:
    def __init__(self, url, client_id, name, pipeline, listener=None, version="0.1.0",
                 product="Kodi", buffer_capacity=2_000_000, formats=None):
        self.url = url
        self.client_id = client_id
        self.name = name
        self.pipeline = pipeline
        self.listener = listener or Listener()
        self.version = version
        self.product = product
        self.buffer_capacity = buffer_capacity
        self.formats = formats or [
            {"codec": "pcm", "channels": 2, "sample_rate": 48000, "bit_depth": 16},
            {"codec": "pcm", "channels": 2, "sample_rate": 44100, "bit_depth": 16},
        ]
        self.clock = pipeline._clock if hasattr(pipeline, "_clock") else ClockSync()
        self.available = True
        self.connected = False
        self.server_name = None
        self.metadata = {}
        self._ws = None
        self._stop = threading.Event()
        self._thread = None

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sendspin-client", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        ws = self._ws
        if ws is not None:
            # Say goodbye if the server is listening, but never let a stalled one hold up shutdown.
            goodbye = threading.Thread(target=self._goodbye, args=(ws,), name="sendspin-goodbye", daemon=True)
            goodbye.start()
            goodbye.join(1.0)
            ws.abort()
        if self._thread is not None:
            self._thread.join(timeout=5)

    @staticmethod
    def _goodbye(ws):
        try:
            ws.send_text(json.dumps({"type": "client/goodbye", "payload": {"reason": "shutdown"}},
                                    separators=(",", ":")))
            ws.close()
        except Exception:  # noqa: BLE001 - best effort
            pass

    def _run(self):
        backoff = 1.0
        while not self._stop.is_set():
            try:
                self._session()
                backoff = 1.0
            except (WebSocketError, OSError, ValueError) as exc:
                if not self._stop.is_set():  # stop() closing the socket is not a failure
                    log.warning("connection to %s failed: %s", self.url, exc)
            except Exception:  # noqa: BLE001 - never let the thread die
                log.exception("unexpected client error")
            finally:
                self._on_disconnect()
            if self._stop.wait(backoff + random.random()):
                break
            backoff = min(backoff * 2, 30.0)

    def _on_disconnect(self):
        was = self.connected
        self.connected = False
        self._ws = None
        self.clock.reset()
        self.pipeline.end()
        if was:
            self.listener.on_disconnected()

    # -- protocol ----------------------------------------------------------
    def _send(self, msg):
        ws = self._ws
        if ws is None:
            return
        ws.send_text(json.dumps(msg, separators=(",", ":")))

    def _hello(self):
        return {
            "type": "client/hello",
            "payload": {
                "client_id": self.client_id,
                "name": self.name,
                "version": PROTOCOL_VERSION,
                "supported_roles": ["player@v1", "metadata@v1", "controller@v1"],
                "device_info": {
                    "product_name": self.product,
                    "manufacturer": "kodi-sendspin",
                    "software_version": self.version,
                },
                "player@v1_support": {
                    "supported_formats": self.formats,
                    "buffer_capacity": self.buffer_capacity,
                    "supported_commands": SUPPORTED_COMMANDS,
                },
            },
        }

    def send_state(self):
        p = self.pipeline
        self._send({
            "type": "client/state",
            "payload": {
                "available": bool(self.available),
                "player": {
                    "volume": int(p.volume),
                    "muted": bool(p.muted),
                    "static_delay_ms": int(p.static_delay_us // 1000),
                    "required_lead_time_ms": int(p.lead_us // 1000) + 200,
                    "min_buffer_ms": int(p.lead_us // 1000) + 500,
                },
            },
        })

    def send_controller(self, command, **extra):
        """Ask the server to act on our group (play/pause/stop/next/previous/...)."""
        if not self.connected:
            return
        payload = {"command": command}
        payload.update({k: v for k, v in extra.items() if v is not None})
        log.info("controller command %s", payload)
        self._send({"type": "client/command", "payload": {"controller": payload}})

    def set_available(self, available):
        if available == self.available:
            return
        self.available = available
        log.info("available=%s", available)
        if self.connected:
            self.send_state()

    def set_volume(self, volume=None, muted=None, notify=True):
        if volume is not None:
            self.pipeline.volume = max(0, min(100, int(volume)))
        if muted is not None:
            self.pipeline.muted = bool(muted)
        if notify and self.connected:
            self.send_state()

    def _timesync_loop(self, ws):
        # burst first for a fast lock, then every 2 s
        delays = [0.05] * 6 + [2.0] * 100000
        for d in delays:
            if self._stop.is_set() or ws.closed:
                return
            try:
                ws.send_text(json.dumps({"type": "client/time", "payload": {"client_transmitted": now_us()}},
                                        separators=(",", ":")))
            except WebSocketError:
                return
            if self._stop.wait(d):
                return

    def _watchdog(self, ws):
        """Diagnostics: dump all thread stacks if the reader stops receiving."""
        import sys
        import traceback
        dumped = False
        while not self._stop.is_set() and not ws.closed:
            if self._stop.wait(2):
                return
            idle = (now_us() - self._last_rx) / 1e6
            if idle > 8 and not dumped:
                dumped = True
                frames = sys._current_frames()
                lines = ["reader idle for %.1fs - thread dump:" % idle]
                for th in threading.enumerate():
                    fr = frames.get(th.ident)
                    if fr is not None:
                        lines.append("--- %s\n%s" % (th.name, "".join(traceback.format_stack(fr)[-6:])))
                log.warning("\n".join(lines))
            elif idle < 3:
                dumped = False

    def _session(self):
        ws = WebSocket(self.url)
        ws.connect()
        try:
            self._ws = ws
            log.info("connected to %s", self.url)
            self._send(self._hello())
            threading.Thread(target=self._timesync_loop, args=(ws,), name="sendspin-time", daemon=True).start()
            self._last_rx = now_us()
            threading.Thread(target=self._watchdog, args=(ws,), name="sendspin-watchdog", daemon=True).start()
            while not self._stop.is_set():
                op, data = ws.recv()
                rx = now_us()
                self._last_rx = rx
                if op == OP_BINARY:
                    self._on_binary(data)
                elif op == OP_TEXT:
                    self._on_text(json.loads(data), rx)
        finally:
            ws.close()  # ends this session's time and watchdog threads before any reconnect

    def _on_binary(self, data):
        if len(data) < 9 or data[0] != BIN_AUDIO_CHUNK:
            return
        ts = struct.unpack(">q", data[1:9])[0]
        pcm = data[9:]
        fmt = getattr(self.pipeline, "fmt", None)
        if fmt is not None and len(pcm) % fmt.frame_bytes:
            return  # not whole sample frames: not audio we can play
        self.pipeline.push(ts, pcm)

    def _accept_format(self, player):
        """The stream format, if it is one we offered in client/hello; otherwise None."""
        chosen = {k: player.get(k) for k in ("codec", "channels", "sample_rate", "bit_depth")}
        if chosen not in self.formats:
            return None
        return AudioFormat(chosen["sample_rate"], chosen["channels"], chosen["bit_depth"])

    def _on_text(self, msg, rx):
        typ = msg.get("type")
        payload = msg.get("payload") or {}
        if typ == "server/time":
            self.clock.add_sample(payload["client_transmitted"], payload["server_received"],
                                  payload["server_transmitted"], rx)
        elif typ == "server/hello":
            self.server_name = payload.get("name")
            self.connected = True
            log.info("server hello: %s roles=%s", self.server_name, payload.get("active_roles"))
            self.send_state()
            self.listener.on_connected(self.server_name)
        elif typ == "stream/start":
            player = payload.get("player")
            if player:
                fmt = self._accept_format(player)
                if fmt is None:
                    log.error("unsupported stream format %s", player)
                    self.pipeline.end()
                    self.listener.on_stream_end()
                    return
                gen, continuous = self.pipeline.start(fmt, continuous=self.listener.output_running())
                self.listener.on_stream_start(fmt, gen, continuous)
        elif typ == "stream/clear":
            roles = payload.get("roles")
            if roles is None or "player" in roles:
                gen = self.pipeline.clear()
                self.listener.on_stream_clear(gen)
        elif typ == "stream/end":
            roles = payload.get("roles")
            if roles is None or "player" in roles:
                self.pipeline.end()
                self.listener.on_stream_end()
        elif typ == "server/state":
            md = payload.get("metadata")
            if isinstance(md, dict):
                self.metadata.update({k: v for k, v in md.items()})
                self.listener.on_metadata(dict(self.metadata))
        elif typ == "server/command":
            self._on_command(payload.get("player") or {})
        elif typ == "group/update":
            self.listener.on_group(payload)
        else:
            log.debug("unhandled message %s", typ)

    def _on_command(self, cmd):
        name = cmd.get("command")
        if name == "volume" and cmd.get("volume") is not None:
            self.set_volume(volume=cmd["volume"])
            self.listener.on_volume(self.pipeline.volume, self.pipeline.muted)
        elif name == "mute" and cmd.get("mute") is not None:
            self.set_volume(muted=cmd["mute"])
            self.listener.on_volume(self.pipeline.volume, self.pipeline.muted)
        elif name == "set_static_delay" and cmd.get("static_delay_ms") is not None:
            self.pipeline.static_delay_us = int(cmd["static_delay_ms"]) * 1000
            self.listener.on_static_delay(int(cmd["static_delay_ms"]))
            self.send_state()
        else:
            log.debug("unhandled command %s", cmd)

"""Timestamped PCM -> continuous WAV stream for Kodi's player.

Sendspin delivers PCM chunks stamped with the server time at which they must
be heard. Kodi can only play a URL, so we expose an endless WAV stream on
localhost and *release* each chunk ``lead`` microseconds before its play time.
Kodi keeps roughly ``lead`` worth of audio in its pipeline, so what comes out
of the speakers is aligned with the server timeline (fine-tuned with the
static delay, which the user / Music Assistant can adjust).

The writer keeps a continuous timeline: gaps are filled with silence, overlaps
are trimmed and audio that is already too late is dropped, so Kodi never
underruns and never drifts behind.
"""

import array
from collections import deque
import logging
import socket
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .clock import now_us

try:  # audioop is C-fast; removed in Python 3.13 but present in Kodi's Python
    import audioop  # type: ignore
except ImportError:  # pragma: no cover - depends on interpreter
    audioop = None

log = logging.getLogger("sendspin.audio")

LATE_DROP_US = 150_000  # drop audio that would play this late
GAP_FILL_US = 2_000  # insert silence for gaps larger than this
STARVE_FILL_US = 120_000  # keep Kodi fed with silence when the network stalls


class AudioFormat:
    def __init__(self, sample_rate, channels, bit_depth):
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.bit_depth = int(bit_depth)

    @property
    def frame_bytes(self):
        return self.channels * self.bit_depth // 8

    @property
    def bytes_per_us(self):
        return self.sample_rate * self.frame_bytes / 1_000_000.0

    def duration_us(self, nbytes):
        return int(nbytes / self.bytes_per_us)

    def bytes_for_us(self, us):
        frames = int(us * self.sample_rate / 1_000_000)
        return max(frames, 0) * self.frame_bytes

    def wav_header(self):
        byte_rate = self.sample_rate * self.frame_bytes
        data_size = 0xFFFFFFFF - 36  # "infinite" stream
        return (
            b"RIFF" + struct.pack("<I", 0xFFFFFFFF) + b"WAVE"
            + b"fmt " + struct.pack("<IHHIIHH", 16, 1, self.channels, self.sample_rate,
                                    byte_rate, self.frame_bytes, self.bit_depth)
            + b"data" + struct.pack("<I", data_size)
        )

    def __eq__(self, other):
        return isinstance(other, AudioFormat) and (
            self.sample_rate, self.channels, self.bit_depth
        ) == (other.sample_rate, other.channels, other.bit_depth)

    def __repr__(self):
        return "%dHz/%dch/%dbit" % (self.sample_rate, self.channels, self.bit_depth)


def apply_gain(pcm, width, gain):
    """Scale 16-bit (or 24/32) little-endian PCM by ``gain`` (0..1)."""
    if gain >= 0.999:
        return pcm
    if gain <= 0.0:
        return bytes(len(pcm))
    if audioop is not None:
        return audioop.mul(pcm, width, gain)
    if width != 2:  # pragma: no cover - fallback only handles 16-bit
        return pcm
    samples = array.array("h")
    samples.frombytes(pcm)
    if sys.byteorder != "little":  # pragma: no cover
        samples.byteswap()
    scaled = array.array("h", (int(s * gain) for s in samples))
    if sys.byteorder != "little":  # pragma: no cover
        scaled.byteswap()
    return scaled.tobytes()


def volume_to_gain(volume, muted):
    """Sendspin volume 0..100 -> perceptual gain (squared curve)."""
    if muted:
        return 0.0
    v = max(0, min(100, int(volume))) / 100.0
    return v * v


class AudioPipeline:
    """Holds timestamped chunks and hands out time-aligned PCM to the HTTP writer."""

    def __init__(self, clock, lead_ms=800, static_delay_ms=0):
        self._clock = clock
        self._cond = threading.Condition()
        self._chunks = deque()  # [server_ts_us, pcm]
        self.fmt = None
        self.generation = 0
        self.active = False
        self.lead_us = int(lead_ms * 1000)
        self.static_delay_us = int(static_delay_ms * 1000)
        self.volume = 100
        self.muted = False
        self._cursor = None  # local µs up to which audio has been written
        self.last_block_start = None  # local play time of the last block returned
        self._adjust_bytes = 0  # >0: drop this much output (Kodi late); <0: insert silence (early)
        self.stats = {"received": 0, "written": 0, "dropped_late": 0, "silence_us": 0, "trimmed": 0}

    # -- control (protocol thread) ----------------------------------------
    def start(self, fmt, continuous=False):
        """New stream. ``continuous``: same format and Kodi is still playing our URL,
        so keep the HTTP stream (generation) and timeline cursor - only drop queued audio.
        Music Assistant schedules new audio >= required_lead_time ahead, which is more
        than our release lead, so the new stream lands after what Kodi already holds.
        """
        with self._cond:
            keep = continuous and self.active and self.fmt == fmt and self._cursor is not None \
                and self._cursor > now_us()
            self._chunks = deque()
            if not keep:
                self.fmt = fmt
                self._cursor = None
                self._adjust_bytes = 0
                self.generation += 1
            self.active = True
            self._cond.notify_all()
        log.info("stream start %r (generation %d, %s)", fmt, self.generation,
                 "continuous" if keep else "new")
        return self.generation, keep

    def clear(self):
        """Seek / skip: drop queued audio but keep Kodi's stream and the timeline."""
        with self._cond:
            self._chunks = deque()
            self._cond.notify_all()
        log.info("stream clear (generation %d)", self.generation)
        return self.generation

    def end(self):
        with self._cond:
            self.active = False
            self._chunks = deque()
            self._cursor = None
            self._cond.notify_all()
        log.info("stream end")

    def push(self, server_ts, pcm):
        with self._cond:
            if not self.active:
                return
            self._chunks.append([server_ts, pcm])
            self.stats["received"] += 1
            self._cond.notify_all()

    def buffered_us(self):
        with self._cond:
            if self.fmt is None:
                return 0
            return sum(self.fmt.duration_us(len(c[1])) for c in self._chunks)

    # -- output (HTTP writer thread) --------------------------------------
    def _local_play_time(self, server_ts):
        local = self._clock.server_to_local(server_ts)
        if local is None:
            return None
        return local + self.static_delay_us

    def adjust_output(self, delta_us):
        """Shift what the output device hears: +delta = it is late, drop audio; - = insert silence."""
        with self._cond:
            if self.fmt is None:
                return
            n = self.fmt.bytes_for_us(abs(int(delta_us)))
            self._adjust_bytes += n if delta_us > 0 else -n
            log.info("sync correction: %s %d ms", "dropping" if delta_us > 0 else "inserting silence",
                     abs(delta_us) // 1000)

    def _apply_adjust(self, block):
        if not self._adjust_bytes or not block:
            return block
        if self._adjust_bytes < 0:  # insert silence before the block
            pad = -self._adjust_bytes
            self._adjust_bytes = 0
            return bytes(pad) + block
        drop = min(self._adjust_bytes, len(block))
        self._adjust_bytes -= drop
        return block[drop:]

    def next_block(self, generation, timeout=0.5):
        block = self._next_block(generation, timeout)
        if block:
            with self._cond:
                return self._apply_adjust(block)
        return block

    def _next_block(self, generation, timeout=0.5):
        """Block until audio for ``generation`` is due; return PCM bytes, b"" or None.

        ``None`` means the generation is over (stream ended / cleared / format
        changed) and the HTTP response should be closed.
        """
        with self._cond:
            while True:
                if generation != self.generation or not self.active:
                    return None
                fmt = self.fmt
                now = now_us()
                release_horizon = now + self.lead_us
                if self._chunks:
                    ts, pcm = self._chunks[0]
                    start = self._local_play_time(ts)
                    if start is None:
                        self._cond.wait(0.05)
                        continue
                    dur = fmt.duration_us(len(pcm))
                    if start + dur < now - LATE_DROP_US:
                        self._chunks.popleft()
                        self.stats["dropped_late"] += 1
                        continue
                    if start <= release_horizon:
                        self._chunks.popleft()
                        return self._emit(fmt, start, dur, pcm)
                    # Not due yet: maybe we must fill silence so Kodi keeps playing.
                    fill = self._starvation_fill(fmt, now, release_horizon)
                    if fill:
                        return fill
                    wait = (start - release_horizon) / 1_000_000.0
                    self._cond.wait(min(max(wait, 0.002), timeout))
                    continue
                fill = self._starvation_fill(fmt, now, release_horizon)
                if fill:
                    return fill
                self._cond.wait(0.02)

    def _starvation_fill(self, fmt, now, release_horizon):
        """Write silence if Kodi would otherwise run dry (network hiccup)."""
        if self._cursor is None:
            return b""
        if self._cursor >= now + STARVE_FILL_US:
            return b""
        target = min(release_horizon, now + STARVE_FILL_US * 2)
        n = fmt.bytes_for_us(target - self._cursor)
        if n <= 0:
            return b""
        self.stats["silence_us"] += fmt.duration_us(n)
        self.last_block_start = self._cursor
        self._cursor += fmt.duration_us(n)
        return bytes(n)

    def _emit(self, fmt, start, dur, pcm):
        out = []
        self.last_block_start = start if self._cursor is None else min(start, self._cursor)
        if self._cursor is not None:
            if start + dur <= self._cursor:  # fully covered by silence fill
                self.stats["trimmed"] += 1
                return b""
            if start < self._cursor - GAP_FILL_US:  # real overlap: trim the front
                cut = fmt.bytes_for_us(self._cursor - start)
                pcm = pcm[cut:]
                start = self._cursor
                self.stats["trimmed"] += 1
            elif start > self._cursor + GAP_FILL_US:  # gap: pad silence
                gap = fmt.bytes_for_us(start - self._cursor)
                out.append(bytes(gap))
                self.stats["silence_us"] += start - self._cursor
        # Sub-ms rounding jitter between chunks is absorbed: the cursor only moves forward.
        self._cursor = max(self._cursor or 0, start) + fmt.duration_us(len(pcm))
        gain = volume_to_gain(self.volume, self.muted)
        out.append(apply_gain(pcm, fmt.bit_depth // 8, gain))
        self.stats["written"] += 1
        return b"".join(out)


class Broadcaster:
    """Pulls time-aligned audio from the pipeline and fans it out to HTTP readers.

    Kodi opens the URL more than once (probe, tag reader, player), so every
    reader gets its own cursor into a short ring of *released* audio. A single
    pump thread owns the timing; readers never consume each other's data.
    """

    RING_SECONDS = 4

    def __init__(self, pipeline, timeline_dir=None):
        self.pipeline = pipeline
        # Debug aid: dump released audio + its intended play times for sync measurement
        self.timeline_dir = timeline_dir
        self._tl = None
        self._cond = threading.Condition()
        self._ring = deque()  # (start_offset, bytes, local_play_time_us)
        self._end = 0  # absolute byte offset of the end of released audio
        self._generation = None
        self._fmt = None
        self._closed = True
        self.active_readers = 0
        self.index = deque()  # (byte_offset, local_play_time_us) for released blocks
        self.reader_starts = []  # byte offsets where each HTTP reader started (newest last)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._pump, name="sendspin-pump", daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def _pump(self):
        while not self._stop.is_set():
            gen = self.pipeline.generation
            if not self.pipeline.active or self.pipeline.fmt is None:
                with self._cond:
                    if not self._closed:
                        self._closed = True
                        self._cond.notify_all()
                self._stop.wait(0.02)
                continue
            with self._cond:
                self._ring.clear()
                self.index.clear()
                self.reader_starts = []
                self._end = 0
                self._generation = gen
                self._fmt = self.pipeline.fmt
                self._closed = False
                self._cond.notify_all()
            ring_limit = int(self._fmt.sample_rate * self._fmt.frame_bytes * self.RING_SECONDS)
            self._open_timeline(gen)
            while not self._stop.is_set():
                block = self.pipeline.next_block(gen)
                if block is None:
                    break
                if not block:
                    continue
                t_start = self.pipeline.last_block_start
                self._log_timeline(t_start, block)
                with self._cond:
                    if t_start is not None:
                        self.index.append((self._end, t_start))
                        while len(self.index) > 4000:
                            self.index.popleft()
                    self._ring.append((self._end, block, t_start))
                    self._end += len(block)
                    while self._ring and self._end - self._ring[0][0] > ring_limit:
                        self._ring.popleft()
                    self._cond.notify_all()
            with self._cond:
                if self._generation == gen:
                    self._closed = True
                    self._cond.notify_all()
            log.debug("pump: generation %d closed (end=%d bytes)", gen, self._end)

    def _open_timeline(self, gen):
        if not self.timeline_dir:
            return
        import json
        import os
        seconds = int(os.environ.get("SENDSPIN_TIMELINE_SECONDS", "90"))
        os.makedirs(self.timeline_dir, exist_ok=True)
        base = os.path.join(self.timeline_dir, "timeline-%d" % gen)
        self._tl = {"raw": open(base + ".raw", "wb"), "idx": open(base + ".jsonl", "w"), "bytes": 0,
                    "limit": self._fmt.sample_rate * self._fmt.frame_bytes * seconds}
        self._tl["idx"].write(json.dumps({"rate": self._fmt.sample_rate, "channels": self._fmt.channels}) + "\n")

    def _log_timeline(self, t_start, block):
        tl = self._tl
        if not tl or tl["bytes"] > tl["limit"]:
            return
        tl["idx"].write("%d %d %d\n" % (tl["bytes"], len(block), t_start or 0))
        tl["raw"].write(block)
        tl["bytes"] += len(block)
        if tl["bytes"] > tl["limit"]:
            tl["raw"].close()
            tl["idx"].close()

    def _live_position(self):
        """Byte offset of the audio that should be heard *now* (so each reader gets the full lead)."""
        now = now_us()
        fmt = self._fmt
        for start, data, t in self._ring:
            if t is None:
                continue
            dur = fmt.duration_us(len(data))
            if t + dur >= now:
                skip = fmt.bytes_for_us(max(0, now - t))
                return start + min(skip, len(data))
        return self._end

    def reader(self, generation):
        """Generator of byte blocks for one HTTP client; starts at the live edge."""
        with self._cond:
            self.active_readers += 1
        try:
            yield from self._reader(generation)
        finally:
            with self._cond:
                self.active_readers -= 1

    def play_time_of(self, offset):
        """Intended local play time (µs) of byte ``offset`` of the current generation."""
        with self._cond:
            fmt = self._fmt
            best = None
            for off, t in self.index:
                if off <= offset:
                    best = (off, t)
                else:
                    break
            if best is None or fmt is None:
                return None
            return best[1] + fmt.duration_us(offset - best[0])

    def wait_readers_closed(self, timeout):
        """Wait until no HTTP reader is connected (returns True if none left)."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self.active_readers > 0 and time.monotonic() < deadline:
                self._cond.wait(0.05)
            return self.active_readers == 0

    def _reader(self, generation):
        with self._cond:
            deadline = time.monotonic() + 5
            while self._generation != generation or self._closed:
                if self._stop.is_set() or time.monotonic() > deadline or (
                        self._generation is not None and self._generation > generation):
                    return
                self._cond.wait(0.1)
            pos = self._live_position()
            self.reader_starts.append(pos)
        while True:
            with self._cond:
                while self._end <= pos and not self._closed and self._generation == generation:
                    self._cond.wait(0.5)
                if self._generation != generation or (self._closed and self._end <= pos):
                    log.debug("reader for generation %d done at %d bytes", generation, pos)
                    return
                if self._ring and pos < self._ring[0][0]:
                    pos = self._ring[0][0]  # reader fell too far behind: skip ahead
                out = []
                for start, data, _t in self._ring:
                    end = start + len(data)
                    if end <= pos:
                        continue
                    out.append(data[max(0, pos - start):])
                pos = self._end
            if out:
                yield b"".join(out)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "kodi-sendspin"

    def log_message(self, fmt, *args):  # route to our logger, quietly
        log.debug("http: " + fmt, *args)

    def _parse_generation(self):
        # /stream/<generation>.wav
        try:
            return int(self.path.rsplit("/", 1)[-1].split(".")[0])
        except ValueError:
            return None

    def _headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

    def do_HEAD(self):  # noqa: N802
        if self.server.pipeline.fmt is None:
            self.send_error(404)
            return
        self._headers()

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/ctl/"):
            # Kodi moved to a neighbour playlist entry: the remote's Next/Previous button.
            action = self.path.split("/")[2]
            callback = self.server.control_callback
            if callback and action in ("next", "previous"):
                callback(action, self.path)
            try:
                self.send_error(404)
            except OSError:
                pass
            return
        pipeline = self.server.pipeline
        generation = self._parse_generation()
        if generation is None or generation != pipeline.generation or pipeline.fmt is None or not pipeline.active:
            try:
                self.send_error(404)
            except OSError:
                pass
            return
        self._headers()
        log.debug("http reader %s for generation %d (range=%s)", self.client_address, generation,
                  self.headers.get("Range"))
        try:
            self.wfile.write(pipeline.fmt.wav_header())
            for block in self.server.broadcaster.reader(generation):
                if self.server.stopping:
                    break
                self.wfile.write(block)
        except (BrokenPipeError, ConnectionResetError, socket.timeout, OSError):
            log.debug("http reader went away")
        log.debug("http handler for generation %d finished", generation)


class WavStreamServer:
    """Serves the pipeline as ``http://127.0.0.1:<port>/stream/<generation>.wav``."""

    def __init__(self, pipeline, host="127.0.0.1", port=0, timeline_dir=None):
        self.pipeline = pipeline
        self.broadcaster = Broadcaster(pipeline, timeline_dir)
        self._httpd = ThreadingHTTPServer((host, port), _Handler)
        self._httpd.daemon_threads = True
        self._httpd.pipeline = pipeline
        self._httpd.broadcaster = self.broadcaster
        self._httpd.control_callback = None
        self._httpd.stopping = False
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="sendspin-http", daemon=True)

    @property
    def port(self):
        return self._httpd.server_address[1]

    def url(self, generation):
        return "http://127.0.0.1:%d/stream/%d.wav" % (self.port, generation)

    def control_url(self, action, generation):
        return "http://127.0.0.1:%d/ctl/%s/%d.wav" % (self.port, action, generation)

    def set_control_callback(self, callback):
        self._httpd.control_callback = callback

    def start(self):
        self.broadcaster.start()
        self._thread.start()

    def stop(self):
        self._httpd.stopping = True
        self.broadcaster.stop()
        self._httpd.shutdown()
        self._httpd.server_close()

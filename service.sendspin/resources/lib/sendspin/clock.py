"""Clock synchronisation between the Sendspin server and this client.

The server stamps audio with *server* microseconds. We keep an estimate of
``offset = server_clock - client_clock`` using NTP-style round trips and keep
only the measurements with the lowest round-trip time (they have the least
queueing noise). A slow exponential filter smooths the result and follows the
small drift between the two clocks.
"""

import threading
import time


def now_us():
    """Monotonic local clock in microseconds."""
    return time.monotonic_ns() // 1000


class ClockSync:
    WINDOW = 12  # recent samples kept
    BEST = 3  # lowest-RTT samples averaged per update
    ALPHA = 0.25  # smoothing once synced

    def __init__(self):
        self._lock = threading.Lock()
        self._samples = []  # (rtt_us, offset_us)
        self._offset = None
        self.rtt_us = None

    @property
    def synced(self):
        return self._offset is not None and len(self._samples) >= 3

    def add_sample(self, client_tx, server_rx, server_tx, client_rx):
        rtt = (client_rx - client_tx) - (server_tx - server_rx)
        offset = ((server_rx - client_tx) + (server_tx - client_rx)) / 2.0
        if rtt < 0:
            return
        with self._lock:
            self._samples.append((rtt, offset))
            self._samples = self._samples[-self.WINDOW:]
            best = sorted(self._samples)[: self.BEST]
            est = sum(o for _, o in best) / len(best)
            if self._offset is None or abs(est - self._offset) > 50_000:
                self._offset = est  # first sync or a large jump: snap
            else:
                self._offset += self.ALPHA * (est - self._offset)
            self.rtt_us = best[0][0]

    def reset(self):
        with self._lock:
            self._samples = []
            self._offset = None
            self.rtt_us = None

    def server_to_local(self, server_us):
        """Convert a server timestamp to the local monotonic clock (µs)."""
        off = self._offset
        if off is None:
            return None
        return int(server_us - off)

    def server_now(self):
        off = self._offset
        return None if off is None else int(now_us() + off)

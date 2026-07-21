"""Single-threaded event dispatcher with a monotonic timer scheduler.

All application state is owned by the dispatcher thread: Kodi bridges (and
any other thread) only ever call post(), a thread-safe enqueue that returns
immediately. Handlers, timers, and every state mutation run serialized on
one thread, so no locks are needed anywhere above this module.

Timers: schedule(delay_s, event, key=...) enqueues a future event.
Scheduling with the same key replaces the pending timer (the supersede
pattern debouncing needs); cancel(key) drops a pending timer. Consumers may
also cancel lazily by dropping stale events on receipt. All interval math
uses the injected clock (time.monotonic by default, never wall-clock time).

Handlers are isolated: an exception in one is logged and does not prevent
later handlers or events. With log_runtimes on, per-handler elapsed time is
logged; the flag is a plain attribute so the runtime can refresh it on
SettingsChanged.

Pure Python, no Kodi imports. The error-log sink is a required constructor
argument (an unwired dispatcher must not silently swallow handler failures);
the debug sink is optional. Tests inject a fake clock and pump manually with
run_pending() instead of starting the thread.
"""

import heapq
import queue
import threading
import time


_STOP = object()
_WAKE = object()


def _noop(_message):
    return None


def _handler_name(handler):
    """Readable handler name for logs, including owner class when bound."""
    try:
        owner = getattr(handler, '__self__', None)
        name = getattr(handler, '__name__', None) or repr(handler)
        if owner is not None:
            return f"{owner.__class__.__name__}.{name}"
        return name
    except Exception:
        return repr(handler)


class Dispatcher:
    def __init__(self, clock=time.monotonic, *, log_error, log_debug=None,
                 log_runtimes=False):
        self._clock = clock
        self._log_debug = log_debug or _noop
        self._log_error = log_error
        self.log_runtimes = log_runtimes
        self._queue = queue.Queue()
        self._subscribers = {}       # event type -> [handlers, ...]
        self._timers = []            # heap of (fire_at, seq, key, event)
        self._timer_lock = threading.Lock()
        self._seq = 0                # unique tie-break + staleness token
        self._active_keys = {}       # key -> seq of the live (non-superseded) timer
        self._thread = None
        self._stopped = False

    # -- subscription ---------------------------------------------------------

    def subscribe(self, event_type, handler):
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type, handler):
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        self._subscribers[event_type] = [h for h in handlers if h != handler]
        if not self._subscribers[event_type]:
            del self._subscribers[event_type]

    # -- posting / scheduling -------------------------------------------------

    def post(self, event):
        """Thread-safe enqueue; returns immediately."""
        self._queue.put(event)

    def schedule(self, delay_s, event, key=None):
        """Dispatch `event` after delay_s seconds.

        Scheduling again with the same `key` replaces the pending timer.
        Returns the key (a generated unique one when key is None), usable
        with cancel().
        """
        with self._timer_lock:
            self._seq += 1
            seq = self._seq
            if key is None:
                key = ('_generated', seq)
            self._active_keys[key] = seq
            heapq.heappush(self._timers,
                           (self._clock() + delay_s, seq, key, event))
        # Wake the loop so it recomputes its wait deadline: the new timer may
        # be nearer than whatever it is currently blocking for.
        self._wake()
        return key

    def cancel(self, key):
        """Cancel the pending timer for `key` (no-op if absent or already fired)."""
        with self._timer_lock:
            cancelled = self._active_keys.pop(key, None) is not None
        if cancelled:
            # Symmetric with schedule(): the loop may be sleeping toward the
            # deadline of the timer we just killed; let it recompute.
            self._wake()

    def _wake(self):
        """Nudge a blocked loop — unless we ARE the loop (then it isn't blocked)."""
        if self._thread is None or threading.current_thread() is not self._thread:
            self._queue.put(_WAKE)

    # -- lifecycle -------------------------------------------------------------

    def start(self):
        """Start the dispatcher thread (no-op if already running)."""
        if self._thread is not None:
            return
        self._stopped = False
        self._thread = threading.Thread(target=self._loop,
                                        name='AOM-Dispatcher', daemon=True)
        self._thread.start()

    def stop(self, timeout=5.0):
        """Stop immediately: pending queue/timers are dropped, thread joined.

        Safe to call from a handler (i.e. from the dispatcher thread itself):
        the loop halts after the current handler returns; no self-join.
        """
        if self._thread is None:
            self._stopped = True
            return
        if threading.current_thread() is self._thread:
            self._stopped = True
            self._thread = None
            return
        self._queue.put(_STOP)
        self._thread.join(timeout)
        self._thread = None
        self._stopped = True

    # -- pumping ----------------------------------------------------------------

    def run_pending(self):
        """Dispatch all queued events and due timers without blocking.

        The manual pump for tests (with an injected fake clock) — production
        uses start()/stop() and never calls this. Loops until a full pass
        makes no progress, so cascades (handlers that post or schedule) are
        fully drained.
        """
        progressed = True
        while progressed and not self._stopped:
            progressed = self._fire_due_timers() > 0
            while True:
                try:
                    item = self._queue.get_nowait()
                except queue.Empty:
                    break
                if item is _STOP:
                    self._stopped = True
                    return
                if item is _WAKE:
                    continue
                self._dispatch(item)
                progressed = True

    def _loop(self):
        while not self._stopped:
            self._fire_due_timers()
            timeout = self._seconds_until_next_timer()
            try:
                item = self._queue.get(timeout=timeout)
            except queue.Empty:
                continue  # a timer came due; top of loop fires it
            if item is _STOP:
                self._stopped = True
                break
            if item is _WAKE:
                continue
            self._dispatch(item)

    # -- internals ---------------------------------------------------------------

    def _seconds_until_next_timer(self):
        """Time until the next live timer, None when no timers exist (block)."""
        with self._timer_lock:
            while self._timers:
                fire_at, seq, key, _event = self._timers[0]
                if self._active_keys.get(key) != seq:
                    heapq.heappop(self._timers)  # superseded or cancelled
                    continue
                return max(0.0, fire_at - self._clock())
            return None

    def _fire_due_timers(self):
        """Dispatch every live timer whose deadline has passed; return count."""
        fired = 0
        while True:
            with self._timer_lock:
                if not self._timers:
                    break
                fire_at, seq, key, event = self._timers[0]
                if self._active_keys.get(key) != seq:
                    heapq.heappop(self._timers)  # superseded or cancelled
                    continue
                if fire_at > self._clock():
                    break
                heapq.heappop(self._timers)
                del self._active_keys[key]
            self._dispatch(event)  # outside the lock: handlers may (re)schedule
            fired += 1
        return fired

    def _dispatch(self, event):
        handlers = list(self._subscribers.get(type(event), ()))
        for handler in handlers:
            # started is read unconditionally: the log_runtimes check happens
            # AFTER the handler so a mid-dispatch flip takes effect for the
            # flipping handler itself (documented, pinned by the test suite).
            # One monotonic read per handler is the accepted cost.
            started = self._clock()
            try:
                handler(event)
            except Exception as exc:  # isolation: one bad handler never starves the rest
                self._log_error(
                    f"AOMe_Dispatcher: {type(event).__name__} handler "
                    f"{_handler_name(handler)} failed: {exc!r}")
            if self.log_runtimes:
                elapsed_ms = (self._clock() - started) * 1000.0
                self._log_debug(
                    f"AOMe_Dispatcher: {type(event).__name__} handled by "
                    f"{_handler_name(handler)} in {elapsed_ms:.1f}ms")

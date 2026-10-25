# SPDX-License-Identifier: GPL-2.0-only
"""Where a finished event goes.

The port is domain-typed: a reporter takes a domain event and builds the payload itself, so
wire keys never leave payload.py and the two reporters. It returns a delivery verdict,
because HTTP 200 is not delivery: CrossWatch answers 200 for a rejected token, for a
disabled webhook source and for a route with no sink configured.

Each event is delivered only within two minutes of being handed over, which is the
contract's retry window measured from the event rather than from the attempt.
"""

import http.client
import json
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from resources.lib.constants import (
    DEFAULT_QUEUE_SIZE,
    HTTP_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
    RETRY_BUDGET_SECONDS,
    SHUTDOWN_DRAIN_SECONDS,
    SHUTDOWN_HTTP_TIMEOUT_SECONDS,
)
from resources.lib.log import get_logger, is_debug, redact
from resources.lib.models import Device, PingEvent, PlaybackEvent
from resources.lib.outbox import Outbox
from resources.lib.payload import build_payload
from resources.lib.routes import RouteFacts, parse_routes

_log = get_logger("reporter")

ALLOWED_SCHEMES = ("http", "https")

Event = PlaybackEvent | PingEvent

# accepted: delivered. refused: a decision, not a hiccup, so never worth sending again.
# unreachable: nothing decided, so a later attempt may still succeed.
Verdict = Literal["accepted", "refused", "unreachable"]

# One attempt's result. foreign: a 3xx or 4xx without CrossWatch's reply shape, such as a
# reverse proxy's login page. Not retried live, like any 4xx, but it says nothing about the
# event, so the outbox keeps a stored watch rather than dropping it.
_Outcome = Literal["delivered", "refused", "foreign", "retry"]


def event_kind(event: Event) -> str:
    """The wire name of an event, for logging and for policy.

    PingEvent has no kind field of its own so that nothing handling playback can be handed
    one by accident; this is the single place that maps either shape to a name.
    """
    return "ping" if isinstance(event, PingEvent) else event.kind


class InvalidWebhookUrl(ValueError):
    pass


def validate_webhook_url(url: str) -> str:
    """Accept only http and https.

    urlopen also handles file:, ftp: and data:, so a mistyped URL would otherwise read a
    local file and report as posted. The error message carries only the redacted URL,
    because the token lives in the query string.
    """
    try:
        parts = urlsplit(url)
        # urlsplit checks the port only when it is read, so a bad one would otherwise surface
        # later as a plain ValueError that no caller of this function expects.
        port = parts.port
    except ValueError as exc:
        raise InvalidWebhookUrl(f"unparseable webhook URL: {redact(url)}") from exc
    if port == 0:
        # A valid number, but no server listens on it: the connect would only fail later.
        raise InvalidWebhookUrl(f"webhook URL has port 0: {redact(url)}")
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.netloc:
        raise InvalidWebhookUrl(f"webhook URL must be http or https: {redact(url)}")
    if parts.fragment:
        # The request is built from path + query, so a fragment would be dropped silently,
        # and a token containing '#' would be truncated to something the receiver rejects.
        raise InvalidWebhookUrl(f"webhook URL must not contain a fragment: {redact(url)}")
    return url


class EventSink(Protocol):
    def report(self, event: Event, device: Device, deadline: float | None = None) -> bool: ...


class EventQueue(Protocol):
    def submit(self, event: Event) -> bool: ...


class LogReporter:
    """The default when no webhook is configured. Mechanism at INFO, identity at DEBUG."""

    def report(self, event: Event, device: Device, deadline: float | None = None) -> bool:
        del deadline  # nothing to retry: writing a log line cannot fail in a way worth waiting for
        if isinstance(event, PingEvent):
            _log.info(
                "reporter.ping",
                viewers_count=len(event.viewers),
                pkc_skipped=event.pkc_skipped,
            )
            return True
        _log.info(
            "reporter.event",
            event=event.kind,
            media_type=event.media.media_type,
            viewers_count=len(event.viewers),
            viewers_source=event.viewers_source or "none",
            percent=event.percent if event.percent is not None else "unknown",
        )
        if is_debug():
            # Guarded because building the payload and serialising it is not free, and this
            # runs for every progress event.
            _log.debug("reporter.payload", body=json.dumps(build_payload(event, device), sort_keys=True))
        return True


def _has_explicit_port(authority: str) -> bool:
    tail = authority.rsplit("]", 1)[-1]
    return ":" in tail


@dataclass(frozen=True)
class Target:
    """A validated URL in the pieces http.client wants."""

    scheme: str
    host: str
    port: int | None
    path: str


def target_of(url: str) -> Target:
    parts = urlsplit(validate_webhook_url(url))
    # Keep the brackets: urlsplit().hostname strips them, and HTTPConnection then re-parses a
    # bare IPv6 address and mis-splits it into host and port.
    authority = parts.netloc.rsplit("@", 1)[-1]
    host = authority.rsplit(":", 1)[0] if _has_explicit_port(authority) else authority
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    return Target(parts.scheme.lower(), host, parts.port, path)


def open_connection(scheme: str, host: str, port: int | None, timeout: float) -> Any:
    if scheme == "https":
        return http.client.HTTPSConnection(host, port, timeout=timeout)
    return http.client.HTTPConnection(host, port, timeout=timeout)


def _asked(body: bytes) -> tuple[str, ...]:
    """The viewer names a ping carried: what CrossWatch's route list answers for."""
    try:
        names = json.loads(body.decode("utf-8")).get("viewers")
    except (ValueError, AttributeError):
        return ()
    return tuple(n for n in names if isinstance(n, str)) if isinstance(names, list) else ()


class HttpReporter:
    def __init__(
        self,
        url: str,
        *,
        token: str,
        abort: threading.Event,
        timeout: float = HTTP_TIMEOUT_SECONDS,
        connection_factory: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], bool] | None = None,
        on_instance: Callable[[str], None] | None = None,
        on_routes: Callable[[RouteFacts], None] | None = None,
    ) -> None:
        target = target_of(url)
        self._scheme = target.scheme
        self._host = target.host
        self._port = target.port
        self._path = target.path
        self._timeout = timeout
        self._factory = connection_factory or open_connection
        self._safe_url = redact(url)
        self._abort = abort
        self._clock = clock
        # Returns True when the wait was cut short by abort, matching Event.wait.
        self._sleep = sleeper if sleeper is not None else abort.wait
        # Called on the worker thread with the instance name a ping's reply carries, which is
        # how a Link, which hands over no name, learns what it connected to.
        self._on_instance = on_instance
        # Likewise with the routes the reply lists, so the viewer list can mark a viewer no
        # route takes.
        self._on_routes = on_routes
        self._headers = {"Content-Type": "application/json"}
        if token:
            # The header only: a token in the query string ends up in proxy and access logs.
            self._headers["X-CrossWatch-Token"] = token

    def _connect(self) -> Any:
        # A connection opened after abort gets the short timeout. Kodi kills the interpreter
        # 5000ms after abort and a ten second socket cannot finish inside that; the
        # contract's timeout applies to normal operation.
        timeout = SHUTDOWN_HTTP_TIMEOUT_SECONDS if self._abort.is_set() else self._timeout
        return self._factory(self._scheme, self._host, self._port, timeout)

    def report(self, event: Event, device: Device, deadline: float | None = None) -> bool:
        """Deliver one event, retrying until the deadline, on this reporter's clock.

        The queue passes the end of the event's freshness window, so time the event spent
        waiting behind others counts against it. Without a deadline the full budget applies.

        Retry lives here rather than in the queue because ordering matters: the receiver
        drives a now-playing card from event order, so a retried stop must never land after
        the next playback's start. Blocking the worker is harmless; nothing waits on it and
        the service thread is a different thread.
        """
        body = json.dumps(build_payload(event, device)).encode("utf-8")
        kind = event_kind(event)
        if deadline is None:
            deadline = self._clock() + RETRY_BUDGET_SECONDS
        attempts = 0
        while True:
            outcome = self._attempt(body, kind)
            attempts += 1
            if outcome != "retry":
                return outcome == "delivered"

            remaining = deadline - self._clock()
            # Refuse to start an attempt the budget cannot pay for. A socket timeout applies
            # per operation, so one attempt against a black-holing peer costs up to three of
            # them; without this check "two minutes" silently becomes two and a half.
            if remaining <= self._timeout:
                _log.warning("reporter.gave_up", event=kind, reason="budget_spent", attempts=attempts)
                return False
            backoff = RETRY_BACKOFF_SECONDS[min(attempts - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
            if self._sleep(min(backoff, remaining)):
                _log.warning("reporter.gave_up", event=kind, reason="aborted", attempts=attempts)
                return False

    def send_once(self, body: dict[str, Any], kind: str) -> Verdict:
        """One attempt with a stored payload, for the outbox.

        One attempt rather than a retry loop: the outbox runs only while the live queue is
        idle, and a live event arriving meanwhile must wait at most one request timeout.
        """
        outcome = self._attempt(json.dumps(body).encode("utf-8"), kind)
        if outcome == "delivered":
            return "accepted"
        return "refused" if outcome == "refused" else "unreachable"

    def _attempt(self, body: bytes, kind: str) -> _Outcome:
        """One request, judged.

        A fresh connection per attempt, closed before returning. Events are a minute or more
        apart and CrossWatch's server closes an idle keep-alive after about five seconds, so
        a reused socket is almost always already dead and every event would start with a
        failed write.
        """
        try:
            connection = self._connect()
        except Exception as exc:
            _log.warning("reporter.failed", url=self._safe_url, event=kind, error=str(exc))
            return "retry"
        try:
            return self._exchange(connection, body, kind)
        finally:
            try:
                connection.close()
            except Exception:
                pass

    def _exchange(self, connection: Any, body: bytes, kind: str) -> _Outcome:
        try:
            connection.request("POST", self._path, body=body, headers=dict(self._headers))
        except Exception as exc:
            # Nothing was necessarily written, so this is safe to retry.
            _log.warning("reporter.failed", url=self._safe_url, event=kind, error=str(exc))
            return "retry"

        try:
            response = connection.getresponse()
            status = int(getattr(response, "status", 0) or 0)
            raw = response.read()
        except Exception as exc:
            # Retried, on the CrossWatch maintainer's decision (issue #1, 2026-09-20): the
            # sinks absorb a duplicate. Everything goes through Trakt and Simkl's
            # /scrobble/* endpoints, which dedupe server side and answer 409, and the media
            # sinks set a watched flag, which is idempotent. So losing the response is worth
            # another attempt, where previously it cost the event.
            _log.warning("reporter.lost_response", url=self._safe_url, event=kind, error=str(exc))
            return "retry"

        if 500 <= status < 600:
            _log.warning("reporter.failed", url=self._safe_url, event=kind, status=status)
            return "retry"
        parsed = _reply_of(raw)
        if status < 200 or status >= 300:
            if "ok" not in parsed:
                # Not retried live either: a login page answers every attempt the same way.
                _log.warning("reporter.failed", url=self._safe_url, event=kind, status=status, reason="not_crosswatch")
                return "foreign"
            # A 4xx is a decision, not a hiccup. 401 is a bad token; retrying for two minutes
            # helps nobody and delays every event behind it.
            _log.warning("reporter.rejected", url=self._safe_url, event=kind, status=status)
            return "refused"
        return self._accepted(kind, status, parsed, body)

    def _accepted(self, kind: str, status: int, parsed: dict[str, Any], body: bytes) -> _Outcome:
        if parsed.get("ignored") is True or parsed.get("activity_recorded") is False:
            _log.warning(
                "reporter.rejected",
                url=self._safe_url,
                event=kind,
                reason=str(parsed.get("error") or "activity_not_recorded"),
            )
            return "refused"
        if "ok" not in parsed:
            # Every CrossWatch reply carries "ok". A 200 without it is a proxy login page or a
            # captive portal answering in CrossWatch's place, so nothing was delivered and a
            # completed watch must stay on disk. The body is not logged: a login page is not
            # ours to copy into kodi.log.
            _log.warning("reporter.failed", url=self._safe_url, event=kind, status=status, reason="not_crosswatch")
            return "retry"
        rated = parsed.get("rated")
        if kind == "rate" and isinstance(rated, list):
            # A write that failed at a destination is still a 200: CrossWatch logs why, and
            # sending the same score again would fail the same way.
            failed = sum(1 for route in rated if isinstance(route, dict) and route.get("ok") is False)
            (_log.warning if failed else _log.info)("reporter.rated", url=self._safe_url, routes=len(rated), failed=failed)
        else:
            _log.info("reporter.posted", url=self._safe_url, event=kind)
        instance = parsed.get("instance")
        if kind == "ping" and self._on_instance is not None and isinstance(instance, str) and instance.strip():
            try:
                self._on_instance(instance.strip())
            except Exception as exc:
                # Cosmetic: a failure to show the name must not turn a delivery into a failure.
                _log.warning("reporter.instance_not_noted", error=str(exc))
        facts = parse_routes(parsed, _asked(body)) if kind == "ping" and self._on_routes is not None else None
        if facts is not None and self._on_routes is not None:
            try:
                self._on_routes(facts)
            except Exception as exc:
                # As for the instance: a hint for the settings screen, never a delivery failure.
                _log.warning("reporter.routes_not_noted", error=str(exc))
        return "delivered"


def _reply_of(raw: bytes) -> dict[str, Any]:
    """The reply as a JSON object, or empty when it is anything else."""
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _kept_on_disk(event: Event) -> bool:
    """A completed watch and a rate: only the add-on knows who watched, or who rated.

    Only a stop can mark something watched, whatever else a caller sets.
    """
    if not isinstance(event, PlaybackEvent):
        return False
    return event.kind == "rate" or (event.kind == "stop" and event.completes_watch)


@dataclass(frozen=True)
class OutboxLane:
    """Completed watches kept on disk, and how to send one stored payload once.

    Paired so a queue has both or neither: a store with no way to send drains nothing, and a
    sender with no store has nothing to send.
    """

    store: Outbox
    send: Callable[[dict[str, Any], str], Verdict]


class ReporterQueue:
    """Keeps the network off the service thread, and delivers each event only while it is true.

    A full queue drops with a warning: blocking here would park the one thread that delivers
    callbacks and observes abort, which is worse than losing a progress event.

    Every event may be sent until RETRY_BUDGET_SECONDS after it was handed over, and not
    after: the contract's two minutes are measured from the event, so time spent waiting
    behind others during an outage counts against it. Without that, an outage queued events
    two minutes apart and delivered them long after they stopped being true.
    """

    def __init__(
        self,
        sink: EventSink,
        device: Device,
        abort: threading.Event,
        maxsize: int = DEFAULT_QUEUE_SIZE,
        clock: Callable[[], float] = time.monotonic,
        outbox: OutboxLane | None = None,
    ) -> None:
        # One attribute, so a reader always gets a sink and the outbox lane that belongs to it:
        # replace() swaps the pair in a single assignment, which needs no lock.
        self._route: tuple[EventSink, OutboxLane | None] = (sink, outbox)
        self._device = device
        # Each item carries its hand-over time on the monotonic clock, never sent_at: a box
        # with no real-time clock steps its wall clock at NTP sync, which would expire or
        # resurrect everything queued at that moment.
        self._queue: queue.Queue[tuple[Event, float, int]] = queue.Queue(maxsize=maxsize)
        self._abort = abort
        self._clock = clock
        self._stopping = threading.Event()
        self._stopped = False
        # Newest sequence number handed over per playback session. Decided at dequeue rather
        # than by editing the queue, so the queue stays a plain queue.Queue.
        self._latest: dict[str, int] = {}
        self._latest_lock = threading.Lock()
        self._sequence = 0
        self._thread = threading.Thread(target=self._run, name="crosswatch-reporter", daemon=True)
        self._thread.start()

    def replace(self, sink: EventSink, outbox: OutboxLane | None) -> None:
        """Send from now on to another server, or to none.

        Nothing queued is dropped: every event not yet taken goes to the new sink. An attempt
        already in flight finishes against the old one, on its own connection.
        """
        self._route = (sink, outbox)

    def submit(self, event: Event) -> bool:
        if self._stopping.is_set():
            _log.warning("reporter.dropped", event=event_kind(event), reason="stopping")
            return False
        outbox = self._route[1]
        if outbox is not None and _kept_on_disk(event):
            # Stored before it is queued, so neither a full queue nor a shutdown between here
            # and the first attempt can lose it.
            outbox.store.add(build_payload(event, self._device), event_kind(event))
        with self._latest_lock:
            self._sequence += 1
            sequence = self._sequence
            # A rate follows its session's stop, which already cleared the entry; recording it
            # would leave the session behind for good.
            if isinstance(event, PlaybackEvent) and event.kind != "rate":
                self._latest[event.session_id] = sequence
        try:
            self._queue.put_nowait((event, self._clock(), sequence))
            return True
        except queue.Full:
            _log.warning("reporter.dropped", event=event_kind(event), reason="queue_full")
            return False

    def _run(self) -> None:
        while True:
            try:
                event, handed_over, sequence = self._queue.get(timeout=0.2)
            except queue.Empty:
                if self._stopping.is_set():
                    return
                self._try_outbox()
                continue
            try:
                self._deliver(event, handed_over, sequence)
            except Exception as exc:
                _log.error("reporter.crashed", error=str(exc))
            finally:
                self._queue.task_done()

    def _deliver(self, event: Event, handed_over: float, sequence: int) -> None:
        kind = event_kind(event)
        age = self._clock() - handed_over
        if self._superseded(event, sequence):
            _log.debug("reporter.superseded", event=kind)
            return
        if age > RETRY_BUDGET_SECONDS:
            _log.debug("reporter.expired", event=kind, age_s=round(age))
            return
        sink, outbox = self._route
        delivered = sink.report(event, self._device, handed_over + RETRY_BUDGET_SECONDS)
        if delivered and outbox is not None and _kept_on_disk(event):
            outbox.store.delivered(event.event_id)

    def _try_outbox(self) -> None:
        """One attempt at the oldest due stored watch, only while no live event is waiting.

        One attempt, not a retry loop, so a live event arriving meanwhile waits at most one
        request timeout; and never after abort, when the contract says to stop trying.
        """
        outbox = self._route[1]
        if outbox is None or self._abort.is_set():
            return
        entry = outbox.store.next_due()
        if entry is None:
            return
        # replayed is contract v1.2's marker for a stop delivered from disk. Added here, not
        # stored, so the file keeps exactly the payload that was built; CrossWatch could
        # otherwise only guess from the gap between sent_at and arrival.
        verdict = outbox.send({**entry.body, "replayed": True}, entry.kind)
        if verdict == "accepted":
            outbox.store.delivered(entry.event_id)
        elif verdict == "refused":
            outbox.store.refused(entry.event_id)
        else:
            outbox.store.defer(entry.event_id)

    def _superseded(self, event: Event, sequence: int) -> bool:
        """Only progress: every other kind is a transition the receiver has to see."""
        if not isinstance(event, PlaybackEvent):
            return False
        with self._latest_lock:
            latest = self._latest.get(event.session_id, sequence)
            if event.kind == "stop" and latest == sequence:
                # The session is over; nothing newer can arrive for it.
                del self._latest[event.session_id]
        return event.kind == "progress" and latest > sequence

    def stop(self, deadline: float = SHUTDOWN_DRAIN_SECONDS) -> int:
        """Drain within a deadline and report what could not be delivered.

        Kodi allows the script 5000ms after abort before killing the interpreter, so a fixed
        join plus a full HTTP timeout cannot both fit.
        """
        if self._stopped:
            return 0
        self._stopped = True
        # Set first: a reporter mid-backoff gives up rather than spending the budget on
        # work the contract says to abandon.
        self._abort.set()
        self._stopping.set()
        limit = time.monotonic() + deadline
        while not self._queue.empty() and time.monotonic() < limit:
            time.sleep(0.02)
        self._thread.join(max(0.0, limit - time.monotonic()))
        undelivered = self._queue.qsize()
        if undelivered:
            _log.warning("reporter.undelivered", count=undelivered)
        outbox = self._route[1]
        if outbox is not None and (pending := outbox.store.pending()):
            _log.warning("reporter.outbox_pending", count=pending)
        if self._thread.is_alive():
            # Still inside an attempt. It is a daemon thread and its connection is its own,
            # so process exit takes both; nothing here may touch the socket underneath it.
            _log.warning("reporter.worker_still_running")
        return undelivered

# SPDX-License-Identifier: GPL-2.0-only
"""Where events go for the current connection settings, rebuilt when they change.

Pairing, a Link, a pasted URL and Unpair all end as a settings change, and this is what
turns one into a new delivery path without a Kodi restart.
"""

import threading
from collections.abc import Callable

from resources.lib import status
from resources.lib.config import Settings
from resources.lib.constants import VIEWER_RENAMED_HEADING
from resources.lib.kodi import KodiApi
from resources.lib.log import get_logger
from resources.lib.outbox import Outbox, config_fingerprint
from resources.lib.people import reconcile
from resources.lib.reporter import EventSink, HttpReporter, InvalidWebhookUrl, LogReporter, OutboxLane
from resources.lib.routes import Person, RouteFacts
from resources.lib.storage import PromptMemory, RouteStore, ViewerStore

_log = get_logger("service")

# The URL the reporter posts to and the token in its header. None for the URL means
# unconfigured, whatever the token says.
Endpoint = tuple[str | None, str]


def _endpoint(settings: Settings) -> Endpoint:
    url = settings.webhook_url()
    return (url, settings.webhook_token if url else "")


class Delivery:
    """Builds the sink and outbox lane for an endpoint, and reports its instance name.

    One Outbox for the life of the service, rebound to each new token: two stores over one
    file would each save their own entries over the other's. An endpoint with no sink, after
    Unpair, leaves the store alone, so its watches are still there if the same token returns.

    The reporter worker notes the instance name from a ping reply; the service thread writes
    it into the status setting, because everything that talks to Kodi runs there.
    """

    def __init__(
        self,
        kodi: KodiApi,
        outbox_path: str,
        abort: threading.Event,
        routes: RouteStore | None = None,
        viewers: ViewerStore | None = None,
        memory: PromptMemory | None = None,
        on_renamed: Callable[[str, str], None] | None = None,
    ) -> None:
        self._kodi = kodi
        self._outbox_path = outbox_path
        self._abort = abort
        self._endpoint: Endpoint | None = None
        self._outbox: Outbox | None = None
        self._lock = threading.Lock()
        self._instance: tuple[Endpoint, str] | None = None
        self._routes = routes
        self._viewers = viewers
        self._memory = memory
        self._on_renamed = on_renamed
        self._route_facts: tuple[Endpoint, RouteFacts] | None = None

    def changed(self, settings: Settings) -> bool:
        return _endpoint(settings) != self._endpoint

    def build(self, settings: Settings) -> tuple[EventSink, OutboxLane | None]:
        endpoint = _endpoint(settings)
        url, token = endpoint
        if url is None:
            status.write(self._kodi, status.not_paired(self._kodi))
            self._endpoint = endpoint
            return LogReporter(), None
        try:
            sink = HttpReporter(
                url,
                token=token,
                abort=self._abort,
                on_instance=lambda instance: self._note_instance(endpoint, instance),
                on_routes=lambda facts: self._note_routes(endpoint, facts),
            )
        except InvalidWebhookUrl as exc:
            # Fall back to logging rather than posting somewhere unexpected.
            _log.error("service.webhook_url_rejected", error=str(exc))
            self._endpoint = endpoint
            return LogReporter(), None
        fingerprint = config_fingerprint(token)
        if self._outbox is None:
            self._outbox = Outbox(self._outbox_path, fingerprint)
            self._outbox.load()
        else:
            self._outbox.rebind(fingerprint)
        # Noted only once a sink exists for it: after a build that raised, the same settings
        # must still count as a change, or the next settings change never builds again.
        self._endpoint = endpoint
        return sink, OutboxLane(self._outbox, sink.send_once)

    def _note_instance(self, endpoint: Endpoint, instance: str) -> None:
        with self._lock:
            self._instance = (endpoint, instance)

    def _note_routes(self, endpoint: Endpoint, facts: RouteFacts) -> None:
        with self._lock:
            self._route_facts = (endpoint, facts)

    def _apply_people(self, people: tuple[Person, ...]) -> None:
        """Link and rename viewers to match CrossWatch's people (contract 1.6).

        On the service thread: the settings script applies each edit to viewers.json as it is
        when saved, so a rename saved here is not overwritten by an open Viewers screen, and
        both hold the store's lock from that read to the save.
        """
        if self._viewers is None:
            return
        with self._viewers.locked():
            result = reconcile(self._viewers.viewers(), people)
            if result.changed:
                self._viewers.save(result.viewers)
        if result.skipped:
            _log.warning("people.rename_skipped", count=result.skipped)
        if not result.changed:
            return
        for old, new in result.renamed:
            answers = self._memory.rename_viewer(old, new) if self._memory is not None else 0
            kept = self._outbox.rename_viewer(old, new) if self._outbox is not None else 0
            if self._on_renamed is not None:
                self._on_renamed(old, new)
            _log.info("people.viewer_renamed", answers=answers, kept=kept)
            # The new name alone: Estuary's toast cuts long text off.
            self._kodi.notify(self._kodi.localised(VIEWER_RENAMED_HEADING), new)
        if result.linked:
            _log.info("people.viewer_linked", count=result.linked)

    def publish_status(self) -> None:
        """Write the instance name a ping reply carried, if it is for the current endpoint.

        A reply that arrives after the connection changed again belongs to the old server.
        """
        with self._lock:
            noted, self._instance = self._instance, None
            routed, self._route_facts = self._route_facts, None
        if routed is not None and self._routes is not None:
            endpoint, facts = routed
            if endpoint == self._endpoint and endpoint[0] is not None:
                self._routes.save(config_fingerprint(endpoint[1]), facts)
                _log.info("service.routes_noted", routes=facts.count, accepted=len(facts.accepted))
                if facts.people is not None:
                    self._apply_people(facts.people)
        if noted is None:
            return
        endpoint, instance = noted
        url = endpoint[0]
        if endpoint != self._endpoint or url is None:
            return
        status.write(self._kodi, status.paired(self._kodi, instance, url))

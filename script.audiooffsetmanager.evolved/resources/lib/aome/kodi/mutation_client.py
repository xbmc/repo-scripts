"""Script-process client for the store mutation channel.

The management view's only write path: one ``JSONRPC.NotifyAll`` request to
the service (broadcast through the injected gateway's ``notify_all``), then
a bounded poll for the matching ack. The service's dispatcher executes the
mutation and acks back over NotifyAll; ``send`` returns that ack dict, or
``None`` when no ack arrives inside the timeout (the view's "service not
running" signal). There is no fallback write path here (report-only).

Request/ack matching uses a per-request ``request_id`` echoed by the
service; acks are ignored while no request is in flight, so a stale or
id-less broadcast cannot pre-seed a reply. ``onNotification`` runs on Kodi's
announce thread while ``send`` polls; the single-reference handoff (assign
whole dict, read whole dict) is safe under the GIL.

An ``aome.kodi`` adapter: the only aome layer permitted to import ``xbmc``.
"""

import uuid

import xbmc

from resources.lib.aome.app.store_mutations import (ACK_MESSAGE,
                                                   MUTATION_MESSAGE)
from resources.lib.aome.kodi.announce import decode_payload, other_method
from resources.lib.aome.kodi.settings import ADDON_ID

_ACK_METHOD = other_method(ACK_MESSAGE)


class MutationClient(xbmc.Monitor):
    """Sends one mutation request at a time and waits for the service's ack."""

    TIMEOUT_SECONDS = 3.0
    POLL_SECONDS = 0.1

    def __init__(self, gateway, *, log):
        """``gateway`` is the process's ``KodiGateway`` (its ``notify_all``
        is the broadcast leg); ``log`` is a REQUIRED ``(message, level)``
        sink (house convention)."""
        super().__init__()
        self._gateway = gateway
        self._log = log
        self._pending_id = None
        self._reply = None

    # -- Kodi announce thread ----------------------------------------------------

    def onNotification(self, sender, method, data):
        if sender != ADDON_ID or method != _ACK_METHOD:
            return
        if self._pending_id is None:
            # No request in flight: nothing on the bus is ours (guards the
            # idle state against an id-less ack matching None).
            return
        payload = decode_payload(data)
        if payload is None:
            return
        if payload.get('request_id') != self._pending_id:
            return
        self._reply = payload

    # -- script thread -------------------------------------------------------------

    def send(self, op, key=None):
        """Broadcast one mutation request; return the ack dict or None.

        ``None`` means the broadcast failed or no ack arrived within
        ``TIMEOUT_SECONDS`` — the caller treats both as "service not
        running" (report-only). The poll uses ``waitForAbort`` slices so
        a Kodi shutdown mid-wait aborts cleanly.
        """
        request_id = uuid.uuid4().hex
        self._pending_id = request_id
        self._reply = None

        payload = {'op': op, 'request_id': request_id}
        if key is not None:
            payload['key'] = key

        if not self._gateway.notify_all(ADDON_ID, MUTATION_MESSAGE, payload):
            # The gateway already logged the RPC failure.
            self._pending_id = None
            return None

        waited = 0.0
        try:
            while waited < self.TIMEOUT_SECONDS:
                if self._reply is not None:
                    return self._reply
                if self.waitForAbort(self.POLL_SECONDS):
                    return None
                waited += self.POLL_SECONDS
        finally:
            self._pending_id = None
        self._log(f"AOMe_MutationClient: No ack for {op} within "
                  f"{self.TIMEOUT_SECONDS}s (service not running?)",
                  xbmc.LOGDEBUG)
        return None

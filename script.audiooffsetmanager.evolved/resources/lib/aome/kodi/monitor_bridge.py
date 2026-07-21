"""Kodi monitor bridge: settings-change and NotifyAll callbacks post to the dispatcher.

Also the service's abort monitor (the runtime blocks on this instance's
``waitForAbort()``). Near-zero logic: ``onNotification`` filters for the
addon's own mutation message and decodes the JSON payload; the fields
travel verbatim on the typed event and the StoreMutationHandler owns all
validation.
"""

import xbmc

from resources.lib.aome.app import events
from resources.lib.aome.app.store_mutations import MUTATION_MESSAGE
from resources.lib.aome.kodi.announce import decode_payload, other_method
from resources.lib.aome.kodi.settings import ADDON_ID

_MUTATION_METHOD = other_method(MUTATION_MESSAGE)


class MonitorBridge(xbmc.Monitor):
    def __init__(self, dispatcher):
        super().__init__()
        self._dispatcher = dispatcher

    def onSettingsChanged(self):
        self._dispatcher.post(events.SettingsChanged())

    def onNotification(self, sender, method, data):
        # Only the addon's own mutation channel (the acks use a different
        # message name); everything else on the bus is not ours.
        if sender != ADDON_ID or method != _MUTATION_METHOD:
            return
        payload = decode_payload(data)
        if payload is None:
            # Undecodable request: post it (op=None) so the handler rejects
            # it loudly instead of the channel silently dropping it.
            self._dispatcher.post(events.StoreMutationRequested(op=None))
            return
        self._dispatcher.post(events.StoreMutationRequested(
            op=payload.get('op'),
            key=payload.get('key'),
            request_id=payload.get('request_id')))

"""Shared NotifyAll transport helpers for the store mutation channel.

Kodi surfaces a custom ``JSONRPC.NotifyAll`` message to monitors as
``Other.<message>`` with a JSON-serialized payload. Both channel endpoints
(the service's ``MonitorBridge`` and the script's ``MutationClient``) must
agree on that envelope, so the method-name composition and payload decode
live here once. The protocol itself (message names, op vocabulary, ack
fields) is app-layer, in ``aome.app.store_mutations``.
"""

import json

_OTHER_PREFIX = 'Other.'


def other_method(message):
    """The ``Monitor.onNotification`` method name for a NotifyAll message."""
    return _OTHER_PREFIX + message


def decode_payload(data):
    """Decode a notification's JSON payload dict; ``None`` when undecodable.

    Empty ``data`` decodes to ``{}`` (the receiver's field validation
    rejects a fieldless request). Invalid JSON or a non-dict returns
    ``None``, leaving the malformed-path behavior to the caller.
    """
    try:
        payload = json.loads(data) if data else {}
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload

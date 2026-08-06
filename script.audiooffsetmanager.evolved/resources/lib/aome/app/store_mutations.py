"""Store mutation handler: the service side of the cross-process channel.

The management view runs in the script process and must never write the
store file (single writer): its mutations travel as ``JSONRPC.NotifyAll``
messages that the monitor bridge turns into typed ``StoreMutationRequested``
events, and this component executes them on the dispatcher thread, the same
thread that owns every other store write.

The op whitelist is the channel's security boundary: only ``delete``,
``clear``, ``import`` and ``copy_device`` exist. There is no value field and
no ``set`` op, so the channel structurally cannot carry a value write; an
unknown op or a malformed payload is rejected loudly (a warning line plus a
failed ack).

``copy_device`` seeds the audio endpoints Kodi outputs to from another
device's stored offsets. It names its SOURCE device and nothing else: the
destinations are resolved here and the values are read out of the store, so
neither crosses the wire. The all-devices bucket is neither a legal source
nor a legal destination, since it is where a device-less read resolves
rather than a device.

``import`` is the backup-restore op and keeps the no-value rule intact,
since it transports values learned during playback rather than typed ones.
The wire carries no path and no payload: the script process stages the
chosen backup at the well-known ``<store>.import`` sibling path, and the
service reads it there, re-validates it, replaces the whole store, and
discards the staging file whatever the outcome. The window a spoofed
``import`` could exploit is small, because the view discards the staged file
before the confirmation dialog and re-stages only after the user confirmed,
and a valid-but-empty staged file is refused here regardless.

Every request is acknowledged through the injected ``ack`` callable, echoing
``request_id`` so the script process can match the reply; no ack within its
timeout is the "service not running" signal (report-only, with no
direct-write fallback).

After a store-changing mutation the handler runs ``_store_changed``.
"Store-changing" means the in-memory store the live session resolves
against, which includes the persist-failed variants, since OffsetStore keeps
the in-memory mutation when only the disk write failed and the ack reports
the durability truth. Nothing here touches Kodi's live delay; the applier
owns that, behind its standing gates.

Protocol constants live here (pure Python) so the monitor bridge and the
script-process client share one definition.
"""

from resources.lib.aome.app import events
from resources.lib.aome.domain.formats import (DEVICE_ALL,
                                               SETTING_AUDIO_DEVICE,
                                               SETTING_PASSTHROUGH_DEVICE,
                                               split_device)
from resources.lib.aome.store import keys
from resources.lib.aome.store.offset_store import (StoreUnreadable,
                                                  discard_import,
                                                  read_import_document)


def _noop(_message):
    return None


# NotifyAll message names. Kodi surfaces custom messages to monitors as
# 'Other.<message>'; senders/receivers on both processes use these names.
MUTATION_MESSAGE = 'store_mutation'
ACK_MESSAGE = 'store_mutation_ack'

# The complete op vocabulary of the channel: removal, the backup restore,
# and the device-to-device copy — never value entry.
ALLOWED_OPS = ('delete', 'clear', 'import', 'copy_device')

# The import staging file: the store path plus this suffix, derived
# identically by both processes (a protocol constant, like the message
# names, so no path ever travels on the wire).
IMPORT_SUFFIX = '.import'


class StoreMutationHandler:
    """Executes whitelisted cross-process store mutations on the dispatcher."""

    def __init__(self, dispatcher, session_tracker, store, gateway, ack, *,
                 import_path, log_debug=None, log_warning=None):
        """``store`` is the raw ``OffsetStore``, since mutations target the
        literal keys the view listed and bypass the ``OffsetTable`` algebra.
        ``gateway`` reads the output device settings a copy lands on. ``ack`` is
        a required callable taking the reply payload dict. ``import_path`` is
        the local staging path the script process copies a backup to; the
        runtime derives it, keeping this module free of Kodi path
        translation."""
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._store = store
        self._gateway = gateway
        self._ack = ack
        self._import_path = import_path
        self._log = log_debug or _noop
        self._warn = log_warning or _noop

        dispatcher.subscribe(events.StoreMutationRequested, self._on_requested)

    # -- handler (dispatcher thread) -------------------------------------------

    def _on_requested(self, event):
        if event.op == 'delete':
            reply = self._delete(event.key)
        elif event.op == 'clear':
            reply = self._clear()
        elif event.op == 'import':
            reply = self._import()
        elif event.op == 'copy_device':
            reply = self._copy_device(event.device)
        else:
            # The loud rejection: anything outside the whitelist, including
            # a would-be value write or a malformed payload, is named in the
            # log, refused, and acked as failed.
            self._warn(f"AOMe_StoreMutations: rejected op {event.op!r} "
                       f"(allowed: {', '.join(ALLOWED_OPS)})")
            reply = {'ok': False, 'detail': 'rejected'}

        reply['op'] = event.op if event.op in ALLOWED_OPS else None
        reply['request_id'] = event.request_id
        self._ack(reply)

    # -- ops --------------------------------------------------------------------

    def _delete(self, key):
        if not isinstance(key, str) or not key:
            self._warn(f"AOMe_StoreMutations: rejected delete with bad key "
                       f"{key!r}")
            return {'ok': False, 'detail': 'rejected'}
        if self._store.read_only:
            self._warn(f"AOMe_StoreMutations: store is read-only; "
                       f"refusing delete({key!r})")
            return {'ok': False, 'detail': 'read_only'}
        if self._store.get(key) is None:
            # Raced away (or a stale view row): nothing to do, and the ack
            # says so instead of pretending a delete happened.
            return {'ok': False, 'detail': 'missing'}
        if not self._store.delete(key):
            # Present, writable, but the persist failed: the entry would
            # resurrect on the next load, so the ack must not claim
            # durability. The in-memory removal stands, so the live store
            # changed: reconcile it like any other mutation.
            self._store_changed(op='delete', key=key)
            return {'ok': False, 'detail': 'persist_failed'}
        self._log(f"AOMe_StoreMutations: deleted stored offset {key}")
        self._store_changed(op='delete', key=key)
        return {'ok': True, 'detail': 'deleted'}

    def _clear(self):
        if self._store.read_only:
            self._warn("AOMe_StoreMutations: store is read-only; "
                       "refusing clear()")
            return {'ok': False, 'detail': 'read_only'}
        expected = len(self._store)
        count = self._store.clear()
        if count != expected:
            # clear() reports 0 on a persist failure; with entries present
            # that means the file still holds them (see OffsetStore.clear).
            # The in-memory removal stands regardless, so the live store
            # changed: reconcile like any other mutation.
            self._store_changed(op='clear')
            return {'ok': False, 'detail': 'persist_failed', 'count': count}
        self._log(f"AOMe_StoreMutations: cleared {count} stored offset(s)")
        if count:
            # An empty clear changed nothing: no dedupe reset, no event.
            self._store_changed(op='clear')
        return {'ok': True, 'detail': 'cleared', 'count': count}

    def _import(self):
        """Replace the whole store from the staged backup file (restore).

        The staging file is validated by the same reader the script process
        ran, as defense in depth: it sat on disk between the two reads, and
        the service must not trust another process's validation. The store
        is then replaced, with reset markers for every key the backup drops
        and every marker the backup carried. A valid-but-empty backup is
        refused here rather than only in the view, since the service is the
        choke point. The staging file is discarded whatever the outcome; the
        user's original backup is untouched.
        """
        try:
            if self._store.read_only:
                self._warn("AOMe_StoreMutations: store is read-only; "
                           "refusing import")
                return {'ok': False, 'detail': 'read_only'}
            try:
                entries, resets = read_import_document(
                    self._import_path, log_debug=self._log)
            except StoreUnreadable as error:
                detail = 'future' if error.future else 'invalid'
                self._warn(f"AOMe_StoreMutations: refusing import of "
                           f"unusable staged backup ({error})")
                return {'ok': False, 'detail': detail}
            if not entries:
                self._warn("AOMe_StoreMutations: refusing import of an "
                           "empty backup (clear-all lives in the manage "
                           "view, never here)")
                return {'ok': False, 'detail': 'empty'}
            if not self._store.replace_all(entries, resets=resets):
                # Read-only was excluded above, so False is a persist
                # failure: the in-memory replacement stands and the live
                # session reconciles against it; only durability failed.
                self._store_changed(op='import')
                return {'ok': False, 'detail': 'persist_failed'}
            count = len(self._store)
            self._log(f"AOMe_StoreMutations: imported {count} stored "
                      f"offset(s), replacing the store")
            self._store_changed(op='import')
            return {'ok': True, 'detail': 'imported', 'count': count}
        finally:
            discard_import(self._import_path, log_warning=self._warn)

    def _copy_device(self, device):
        """Seed the endpoints Kodi is configured for from ``device``'s entries.

        A copy targets EVERY endpoint the two output device settings name,
        deduplicated: nothing is playing at the moment a copy is requested,
        so there is no fact of which of the two the next playback will use,
        and on a split configuration seeding only one strands half the
        profiles.

        Refusals ack their own detail, since the view words them: nothing to
        copy from ('missing'), destinations that already hold every candidate
        ('all_present'), and the two device answers that make the request
        meaningless ('no_device', 'same_device').
        """
        if not isinstance(device, str) or not device or device == DEVICE_ALL:
            self._warn(f"AOMe_StoreMutations: rejected copy_device with bad "
                       f"source {device!r}")
            return {'ok': False, 'detail': 'rejected'}
        if self._store.read_only:
            self._warn(f"AOMe_StoreMutations: store is read-only; refusing "
                       f"copy_device({device!r})")
            return {'ok': False, 'detail': 'read_only'}
        endpoints = self._configured_endpoints()
        if not endpoints:
            self._warn("AOMe_StoreMutations: the audio output settings name "
                       "no device; refusing copy_device")
            return {'ok': False, 'detail': 'no_device'}
        destinations = [(segment, name) for segment, name in endpoints
                        if segment != device]
        if not destinations:
            return {'ok': False, 'detail': 'same_device'}
        result = self._store.copy_device(device, destinations)
        if not result.copied:
            return {'ok': False,
                    'detail': 'all_present' if result.skipped else 'missing'}
        self._store_changed(op='copy_device')
        if not result.durable:
            return {'ok': False, 'detail': 'persist_failed'}
        # Devices are named by their key segment here; the friendly half
        # travels to the view and never to a log line.
        self._log(f"AOMe_StoreMutations: copied {result.copied} stored "
                  f"offset(s) from {device} to "
                  f"{', '.join(entry.device for entry in result.devices)}, "
                  f"keeping {result.skipped} already there")
        names = dict(destinations)
        return {'ok': True, 'detail': 'copied', 'count': result.copied,
                'skipped': result.skipped,
                'devices': [{'device': entry.device,
                             'name': names.get(entry.device),
                             'count': entry.copied,
                             'skipped': entry.skipped}
                            for entry in result.devices if entry.copied]}

    # -- internals ---------------------------------------------------------------

    def _configured_endpoints(self):
        """The distinct endpoints Kodi's two output device settings name.

        One ``(segment, friendly name)`` per endpoint, the ordinary device
        first, dropping a reading that names no device and collapsing the
        usual case where both settings name one endpoint.
        """
        endpoints = []
        seen = set()
        for setting_id in (SETTING_AUDIO_DEVICE, SETTING_PASSTHROUGH_DEVICE):
            raw = self._gateway.setting_value(setting_id)
            segment = keys.device_segment(raw, True)
            if segment == DEVICE_ALL or segment in seen:
                continue
            seen.add(segment)
            endpoints.append((segment, split_device(raw)[1]))
        return endpoints

    def _store_changed(self, op, key=None):
        """The store changed under the session: reconcile and re-log.

        Three consequences, the first two synchronous on purpose:

        - ``miss_announced`` is cleared, since it dedupes the applier's "no
          stored offset" line per consulted chain and a mutation makes any
          remembered chain stale.
        - The watcher's observation state is cleared, because an in-flight
          candidate was dialed against a store that no longer exists. This
          cannot ride on a queued event: a quiescence-deadline WatchTick due
          in the same dispatcher sweep would reach the store first
          (docs/kodi-platform-notes.md) and write the stale candidate under
          the just-deleted key. The settled marker goes with it, or a
          re-teach landing on the value settled before the mutation is
          deduped against it and never posts ``UserOffsetSettled``.
        - A typed ``StoreMutated`` is posted so the applier re-runs its
          decision for the live session.
        """
        session = self._sessions.current
        if session is not None:
            session.miss_announced = None
            session.clear_watch_observation()
        self._dispatcher.post(events.StoreMutated(op=op, key=key))

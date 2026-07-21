"""Store mutation handler: the service side of the cross-process channel.

The management view runs in the script process and must never write the
store file (single writer): its mutations travel as ``JSONRPC.NotifyAll``
messages that the monitor bridge turns into typed ``StoreMutationRequested``
events, and this component executes them on the dispatcher thread, the same
thread that owns every other store write.

The op whitelist is the channel's security boundary: only ``delete``,
``clear``, and ``import`` exist. There is no value field and no ``set`` op,
so the channel structurally cannot carry a value write; an unknown op or a
malformed payload is rejected loudly (a warning line plus a failed ack).

``import`` is the backup-restore op and keeps the no-value rule intact: it
transports values learned during playback, never typed ones. The wire
carries no path and no payload; the script process stages the chosen backup
at the well-known ``<store>.import`` sibling path (a staging file, not the
store file), and the service reads it there, re-validates it with the same
reader, replaces the whole store (restore semantics, never merge; the
backup's reset markers ride along), and discards the staging file whatever
the outcome. The window a spoofed ``import`` could exploit is small: the
view stages the file for its pre-flight read, discards it before the
confirmation dialog, and re-stages only after the user confirmed; outside
that instant a spoofed request finds no staged file, and a valid-but-empty
staged file is refused here regardless.

Every request is acknowledged through the injected ``ack`` callable (wired
to ``KodiGateway.notify_all`` under ``ACK_MESSAGE``), echoing ``request_id``
so the script process can match the reply; no ack within its timeout is the
"service not running" signal (report-only, no direct-write fallback).

After a store-changing mutation the handler runs ``_store_changed``:
synchronous session-state invalidation (miss dedupe + watcher observation)
plus a typed ``StoreMutated`` the applier consumes as a resolve moment, so
deleting the playing profile's offset takes effect immediately.
"Store-changing" means the in-memory store the live session resolves
against: a delete that removed an entry, a clear with entries, or an import
that replaced the store, including their persist-failed variants (OffsetStore
keeps the in-memory mutation when only the disk write failed; the ack reports
the durability truth). A missing-key delete, an empty clear, refused ops, and
an import whose staged backup failed validation trigger nothing. Nothing here
touches Kodi's live delay; the applier owns that, behind its standing gates.

Protocol constants live here (pure Python) so the monitor bridge and the
script-process client share one definition.
"""

from resources.lib.aome.app import events
from resources.lib.aome.store.offset_store import (StoreUnreadable,
                                                  discard_import,
                                                  read_import_document)


def _noop(_message):
    return None


# NotifyAll message names. Kodi surfaces custom messages to monitors as
# 'Other.<message>'; senders/receivers on both processes use these names.
MUTATION_MESSAGE = 'store_mutation'
ACK_MESSAGE = 'store_mutation_ack'

# The complete op vocabulary of the channel: removal and the backup
# restore — never value entry.
ALLOWED_OPS = ('delete', 'clear', 'import')

# The import staging file: the store path plus this suffix, derived
# identically by both processes (a protocol constant, like the message
# names, so no path ever travels on the wire).
IMPORT_SUFFIX = '.import'


class StoreMutationHandler:
    """Executes whitelisted cross-process store mutations on the dispatcher."""

    def __init__(self, dispatcher, session_tracker, store, ack, *,
                 import_path, log_debug=None, log_warning=None):
        """``store`` is the raw ``OffsetStore`` (mutations target literal
        keys the view listed, bypassing the ``OffsetTable`` algebra).
        ``ack`` is a required callable taking the reply payload dict.
        ``import_path`` is the required local staging path the script
        process copies a backup to (store path + ``IMPORT_SUFFIX``; the
        runtime derives it, keeping this module free of Kodi path
        translation)."""
        self._dispatcher = dispatcher
        self._sessions = session_tracker
        self._store = store
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
        else:
            # The loud rejection: anything outside the whitelist —
            # including a would-be value write or a malformed payload —
            # is named in the log, refused, and acked as failed.
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
        ran (defense in depth: it sat on disk between the two reads, and the
        service must not trust another process's validation), then the store
        is replaced, with reset markers for every key the backup drops and
        every marker the backup carried. A valid-but-empty backup is refused
        here, not just in the view ("restore nothing" is clear-all in a
        costume, and the service is the choke point). The staging file is
        discarded whatever the outcome; the user's original backup is
        untouched.
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

    # -- internals ---------------------------------------------------------------

    def _store_changed(self, op, key=None):
        """The store changed under the session: reconcile and re-log.

        Three consequences, the first two synchronous on purpose:

        - ``miss_announced`` is cleared: it dedupes the applier's "no stored
          offset" line per consulted chain, and a mutation makes any
          remembered chain stale.
        - The watcher's observation state is cleared: an in-flight candidate
          was dialed against a store that no longer exists. This cannot ride
          on a queued event, because the dispatcher fires due timers between
          queue items, so a quiescence-deadline WatchTick could land between
          this handler and any event it posts and store the stale candidate
          under the just-deleted key; and the applier's already-0/failed-RPC
          reset branches post no DelayReset. Synchronous assignment on the
          dispatcher thread is race-free.
        - A typed ``StoreMutated`` is posted so the applier re-runs its
          decision for the live session, acting now when the deleted
          profile is playing.
        """
        session = self._sessions.current
        if session is not None:
            session.miss_announced = None
            # The watcher's _clear_observation logic, applied inline
            # (baseline and pending fall together — a pre-mutation baseline
            # must not classify post-mutation readings).
            session.watch_pending = None
            session.watch_baseline_ms = None
        self._dispatcher.post(events.StoreMutated(op=op, key=key))

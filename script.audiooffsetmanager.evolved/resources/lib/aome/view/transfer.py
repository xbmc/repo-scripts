"""TransferView: the script-process offsets backup surface (export/import).

The manage view's sibling: it runs in the script process, honours the same
no-value-entry boundary (a backup transports values learned during playback,
never typed), and never writes the store file. Export is pure read: the
store file is validated through the read-only reader and copied verbatim to
a folder the user picks, so a backup round-trips exactly, resets section and
all. Import is the restore: the picked file is copied to the channel's
staging path (``<store>.import``, a staging file, not the store file),
pre-validated with the same reader the service will use, confirmed, and
requested over the mutation channel as the ``import`` op; the service
re-validates the staged file, replaces the whole store (restore semantics,
never merge; the backup's reset markers are restored too), and discards the
staging file. No path and no values ever travel on the wire.

The seams are injected callables, wired by the script router:

* ``read_entries()`` — validated snapshot of the live store (export's
  count + refuse-to-export-garbage gate); raises :class:`StoreUnreadable`.
* ``read_staged()`` — validated snapshot of the staged backup (import's
  pre-flight); raises :class:`StoreUnreadable`, including for a missing file.
* ``export_file(destination)`` — copy the store file to ``destination``
  (``xbmcvfs.copy``, so network/USB destinations work).
* ``stage_file(source)`` — copy ``source`` to the staging path (again
  ``xbmcvfs.copy``, since the picked source may be a VFS path).
* ``discard_staged()`` — best-effort staging cleanup. The view discards
  before every stage and right after the pre-flight read, so nothing sits
  staged while the confirmation dialog waits; only a confirmed import
  re-stages, just before the send. After a sent request the service owns the
  cleanup: an ack timeout does not mean the request died (it may still be
  queued), and deleting the staging file out from under it would turn a slow
  import into a refused one. A stale staging file is inert (overwritten
  before every request).
* ``send_mutation(op)`` — the channel client's send; ``None`` (no ack) is
  the report-only "service not running" signal, as in the manage view.

Import refuses an empty (but valid) backup before confirming: export refuses
to write one, so an empty file is hand-made, and "restore nothing" is
clear-all in a costume. The service enforces the same refusal (the choke
point); this is the friendly pre-flight.

Every dialog string that is the entire message carries an English fallback,
and the shared ids reuse the manage view's fallback texts. Templates are
format-guarded the same way, so a translation that drops or malforms a
placeholder degrades to the English template.
"""

import time

from resources.lib.aome.store.offset_store import StoreUnreadable
# Same-package reuse of the manage view's fallback texts for the ids both
# surfaces raise — one English wording per string id, never two.
from resources.lib.aome.view.manage import _FALLBACKS as _SHARED_FALLBACKS

# Localized string ids owned by this view (defined in strings.po).
_HEADING_EXPORT = 32149    # "Export stored offsets" (button label + heading)
_HEADING_IMPORT = 32151    # "Import stored offsets" (button label + heading)
_MSG_EXPORTED = 32153      # "Saved {0} to {1}"
_MSG_EXPORT_FAILED = 32154
_MSG_READ_FAILED = 32155   # could not copy the picked file to staging
_MSG_NOT_A_BACKUP = 32156
_MSG_IMPORT_FUTURE = 32157  # backup from a newer schema: cannot import
_MSG_BACKUP_EMPTY = 32158
_MSG_CONFIRM_IMPORT = 32159  # "Import {0}? This replaces all..."
_MSG_IMPORTED = 32160      # "Imported {0}"

# Shared with the manage view (one wording, one fallback):
_MSG_EMPTY = 32122         # export with nothing stored = first-run education
_MSG_NO_SERVICE = 32125
_MSG_UNREADABLE = 32127    # live store corrupt: nothing exportable
_MSG_MUTATION_FAILED = 32128
_MSG_FUTURE = 32131        # live store from a newer version: preserved
_LABEL_ENTRY = 32135       # "{0} entry"
_LABEL_ENTRIES = 32136     # "{0} entries"

_FALLBACKS = {
    string_id: _SHARED_FALLBACKS[string_id]
    for string_id in (_MSG_EMPTY, _MSG_NO_SERVICE, _MSG_UNREADABLE,
                      _MSG_MUTATION_FAILED, _MSG_FUTURE,
                      _LABEL_ENTRY, _LABEL_ENTRIES)
}
_FALLBACKS.update({
    _MSG_EXPORTED: "Saved {0} to {1}",
    _MSG_EXPORT_FAILED: "Could not save the backup file",
    _MSG_READ_FAILED: "Could not read the selected file",
    _MSG_NOT_A_BACKUP: "The selected file is not a stored offsets backup",
    _MSG_IMPORT_FUTURE: ("The selected file was saved by a newer version "
                         "of this addon and cannot be imported"),
    _MSG_BACKUP_EMPTY: "The selected file contains no stored offsets",
    _MSG_CONFIRM_IMPORT: ("Import {0}? This replaces all currently stored "
                          "offsets."),
    _MSG_IMPORTED: "Imported {0}",
})

# The import file picker's extension filter (backups are plain JSON).
_IMPORT_MASK = '.json'

# Service refusal details with dedicated user wordings — the conditions
# the pre-flight also detects, reachable on an ack only when the staged
# file changed between the script's read and the service's (re)read.
# Anything else renders the generic failure line with the raw token.
_DETAIL_MESSAGES = {
    'invalid': _MSG_NOT_A_BACKUP,
    'future': _MSG_IMPORT_FUTURE,
    'empty': _MSG_BACKUP_EMPTY,
}


def _noop(_message):
    return None


def _join(folder, name):
    """Append ``name`` to a browsed folder path.

    Kodi's folder browser answers with a trailing separator; the guard
    covers hand-fed paths without one ('/' is accepted by every VFS protocol
    and by Windows APIs).
    """
    if folder.endswith('/') or folder.endswith('\\'):
        return folder + name
    return folder + '/' + name


class TransferView:
    """Export/import the stored offsets from the script process."""

    def __init__(self, gui, send_mutation, *, read_entries, read_staged,
                 export_file, stage_file, discard_staged, clock=time.time,
                 log_debug=None):
        self._gui = gui
        self._send_mutation = send_mutation
        self._read_entries = read_entries
        self._read_staged = read_staged
        self._export_file = export_file
        self._stage_file = stage_file
        self._discard_staged = discard_staged
        self._clock = clock
        self._log = log_debug or _noop

    # -- export ---------------------------------------------------------------

    def run_export(self):
        """Validate, pick a folder, copy the store file verbatim, report."""
        heading = self._gui.localized(_HEADING_EXPORT)
        try:
            entries = self._read_entries()
        except StoreUnreadable as error:
            self._log("AOMe_TransferView: store unreadable ({0})".format(error))
            # Same split as the manage view: a newer-schema store is
            # preserved, not corrupt — its wording must not promise a reset.
            message = _MSG_FUTURE if getattr(error, 'future', False) \
                else _MSG_UNREADABLE
            self._gui.ok(heading, self._text(message))
            return
        if not entries:
            self._log("AOMe_TransferView: store empty; nothing to export")
            self._gui.ok(heading, self._text(_MSG_EMPTY))
            return

        folder = self._gui.browse_folder(heading)
        if not folder:
            self._log("AOMe_TransferView: export cancelled")
            return
        destination = _join(folder, self._export_name())
        if not self._export_file(destination):
            self._log("AOMe_TransferView: export copy failed ({0})"
                      .format(destination))
            self._gui.ok(heading, self._text(_MSG_EXPORT_FAILED))
            return
        self._log("AOMe_TransferView: exported {0} entries to {1}"
                  .format(len(entries), destination))
        self._gui.ok(heading, self._template(
            _MSG_EXPORTED, self._counted(len(entries)), destination))

    def _export_name(self):
        """Timestamped backup filename, second resolution: repeated exports
        get distinct names (two completions inside one second would collide,
        which the dialog-paced flow cannot produce)."""
        stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(self._clock()))
        return 'aom-evolved-offsets-{0}.json'.format(stamp)

    # -- import ---------------------------------------------------------------

    def run_import(self):
        """Pick a backup, pre-flight it, confirm, stage + request the restore.

        The staged copy lives at the well-known path only in two short
        windows: around the pre-flight read (a finally block discards it, so
        no exit path leaks it into the confirm window) and between the
        post-confirmation re-stage and the service consuming it.
        """
        heading = self._gui.localized(_HEADING_IMPORT)
        source = self._gui.browse_file(heading, _IMPORT_MASK)
        if not source:
            self._log("AOMe_TransferView: import cancelled")
            return

        if not self._stage(source):
            self._gui.ok(heading, self._text(_MSG_READ_FAILED))
            return
        try:
            entries = self._read_staged()
        except StoreUnreadable as error:
            self._log("AOMe_TransferView: staged backup unusable ({0})"
                      .format(error))
            message = _MSG_IMPORT_FUTURE if getattr(error, 'future', False) \
                else _MSG_NOT_A_BACKUP
            self._gui.ok(heading, self._text(message))
            return
        finally:
            # The one cleanup site for the pre-flight copy, covering the
            # unusable path, the guards below, AND the confirm window.
            self._discard_staged()
        if not entries:
            # An empty-but-valid backup is hand-made (export refuses to
            # write one); restoring it would be clear-all in a costume.
            # The service refuses it too — this is the friendly wording.
            self._log("AOMe_TransferView: staged backup holds no entries")
            self._gui.ok(heading, self._text(_MSG_BACKUP_EMPTY))
            return

        if not self._gui.yesno(heading, self._template(
                _MSG_CONFIRM_IMPORT, self._counted(len(entries)))):
            self._log("AOMe_TransferView: import declined")
            return

        # Confirmed: re-stage for the send. The file exists again only
        # for the moments between here and the service consuming it.
        if not self._stage(source):
            self._gui.ok(heading, self._text(_MSG_READ_FAILED))
            return
        self._log("AOMe_TransferView: requesting import of {0} entries"
                  .format(len(entries)))
        ack = self._send_mutation('import')
        self._report(heading, ack, len(entries))

    def _stage(self, source):
        """Copy ``source`` to the staging path, sweeping any stale copy
        first (a leftover must not survive a failed copy and be read as
        if it were the picked file)."""
        self._discard_staged()
        if self._stage_file(source):
            return True
        self._log("AOMe_TransferView: staging copy failed ({0})"
                  .format(source))
        return False

    def _report(self, heading, ack, staged_count):
        """Surface the import ack.

        Once a request was sent the service owns the staging cleanup, even on
        an ack timeout (which means "no reply in time", not "the request
        died"): sweeping the staging file here would turn a slow import into
        a refused one. Refusal details the pre-flight also detects map to the
        same dedicated wordings; unexpected details fall back to the generic
        failure line with the raw token.
        """
        if ack is None:
            self._log("AOMe_TransferView: no ack (service not running)")
            self._gui.ok(heading, self._text(_MSG_NO_SERVICE))
            return
        if not ack.get('ok'):
            detail = ack.get('detail')
            self._log("AOMe_TransferView: import refused ({0})".format(detail))
            message_id = _DETAIL_MESSAGES.get(detail)
            if message_id is not None:
                self._gui.ok(heading, self._text(message_id))
            else:
                self._gui.ok(heading, self._text(_MSG_MUTATION_FAILED)
                             + " (" + str(detail) + ")")
            return
        count = ack.get('count')
        if not isinstance(count, int):
            # A malformed ack count degrades to the pre-flight count rather
            # than rendering "Imported None entries".
            count = staged_count
        self._log("AOMe_TransferView: import ok ({0} entries)".format(count))
        self._gui.ok(heading, self._template(_MSG_IMPORTED,
                                             self._counted(count)))

    # -- strings --------------------------------------------------------------

    def _text(self, string_id):
        """localized() with the English fallback for must-never-blank strings."""
        return self._gui.localized(string_id) or _FALLBACKS[string_id]

    def _template(self, string_id, *values):
        """A format template with the manage view's translation guards: a
        translation missing any of the expected ``{0}..{n}`` placeholders
        (32153 carries two), or one malformed enough to raise, degrades to
        the English fallback."""
        template = self._text(string_id)
        if any('{' + str(index) + '}' not in template
               for index in range(len(values))):
            template = _FALLBACKS[string_id]
        try:
            return template.format(*values)
        except Exception:
            return _FALLBACKS[string_id].format(*values)

    def _counted(self, count):
        """'1 entry' / '14 entries' — the manage view's count vocabulary."""
        string_id = _LABEL_ENTRY if count == 1 else _LABEL_ENTRIES
        return self._template(string_id, count)

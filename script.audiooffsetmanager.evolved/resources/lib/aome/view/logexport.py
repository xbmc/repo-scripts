"""LogExportView: the script-process filtered-log export surface.

The transfer view's sibling for support reports: it reads the Kodi log files
(previous session first, then the current one), keeps only this addon's
entries, and writes them as one file to a folder the user picks. The goal is
a file safe to hand to a stranger: AOMe lines carry stream profiles, offsets
and session ids, never media titles or library paths, and the two leaks the
wider net could reintroduce are scrubbed at render time (absolute install
paths fold back to their ``special://`` form, URL credentials are masked the
way Kodi masks them). The disclaimer lives in the button's help text: some
problems still need a full Kodi debug log.

Filtering works on log entries, not lines: a Kodi log line starts with a
timestamp, and continuation lines (traceback bodies) belong to the
timestamped line before them. An entry is kept when any of its lines mentions
the ``AOMe_`` prefix or the addon id (the id catches unhandled-exception
tracebacks and Kodi's own lifecycle lines, which carry no AOMe prefix). Each
file's opening entries also contribute the Kodi version/platform lines every
report wants, matched only within the first few dozen lines so lookalike text
deep in a log cannot smuggle itself in.

The export is bounded: both files stream through a constant-size pass (a
debug log can run to hundreds of MB and must never be loaded whole), and once
the kept entries pass the size cap the oldest are dropped and the file says
so.

The seams are injected callables, wired by the script router:

* ``read_old_log()`` / ``read_current_log()`` — an iterable of raw lines
  over ``kodi.old.log`` / ``kodi.log``, or ``None`` when that file does not
  exist. A reader that fails mid-stream surrenders what it produced so far
  rather than the whole export.
* ``write_export(destination, text)`` — write the rendered file
  (``xbmcvfs.File``, so network/USB destinations work).
* ``redactions`` — ``(resolved_prefix, special_form)`` pairs computed by the
  router, applied longest-first so ``special://profile`` folds before its
  ``special://home`` parent swallows the match.

Every dialog string carries an English fallback and the manage/transfer
views' format guards.
"""

import re
import time
from collections import deque

# Localized string ids owned by this view (defined in strings.po).
_HEADING = 32161           # "Export addon log" (button label + heading)
_MSG_NO_ENTRIES = 32163
_MSG_SAVED = 32164         # "Saved the filtered log to {0}"
_MSG_SAVE_FAILED = 32165
_MSG_UNREADABLE = 32166    # no Kodi log file readable at all

_FALLBACKS = {
    _HEADING: "Export addon log",
    _MSG_NO_ENTRIES: ("No addon log entries found. Turn on debug logging, "
                      "play something, then export again."),
    _MSG_SAVED: "Saved the filtered log to {0}",
    _MSG_SAVE_FAILED: "Could not save the log file",
    _MSG_UNREADABLE: "Could not read the Kodi log file",
}

# A Kodi log line starts with an ISO timestamp; anything else is a
# continuation of the entry above it (traceback bodies, wrapped dumps).
_TIMESTAMP_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}')

# An entry is the addon's when any line carries the log prefix or the
# addon id — the id catches tracebacks and Kodi's lifecycle lines, and
# cannot match the original Audio Offset Manager's lines (its id lacks
# the ``.evolved``).
_ADDON_TOKENS = ('AOMe_', 'script.audiooffsetmanager.evolved')

# The startup entries every report wants (Kodi version, platform, OS),
# trusted only near the top of a file — the whitelist must not let
# lookalike text deep in a log ride along.
_HEADER_RE = re.compile(r'Starting Kodi|Running on ')
_HEADER_SCAN_LINES = 60

# Oldest-first trim threshold for the rendered export. Far above what a
# real session's filtered entries reach; small enough to attach anywhere.
_MAX_EXPORT_BYTES = 5 * 1024 * 1024

# Kodi's own credential masking for URLs (CURL::GetRedacted does the
# same): anything userinfo-shaped between :// and @ is not for sharing.
_CREDENTIALS_RE = re.compile(r'://[^@/\s]+@')

# The two log files, oldest first — the export reads chronologically.
_SOURCES = ('kodi.old.log', 'kodi.log')


def _noop(_message):
    return None


def _join(folder, name):
    """Append ``name`` to a browsed folder path (the transfer view's guard:
    Kodi's folder browser answers with a trailing separator, the fallback
    covers hand-fed paths without one)."""
    if folder.endswith('/') or folder.endswith('\\'):
        return folder + name
    return folder + '/' + name


def _entries(lines, on_error=None):
    """Group raw lines into ``(entry_lines, start_index)`` tuples.

    A timestamped line opens a new entry; non-timestamped lines attach to the
    entry above them. Lines before the first timestamp form a headless first
    entry rather than being lost. The line pull is guarded: a source failing
    mid-stream ends the file where it stands, the buffered entry still
    flushes, and the error goes to ``on_error``.
    """
    iterator = iter(lines)
    current = []
    start = 0
    index = 0
    while True:
        try:
            line = next(iterator)
        except StopIteration:
            break
        except Exception as error:
            if on_error is not None:
                on_error(error)
            break
        line = line.rstrip('\r\n')
        if current and _TIMESTAMP_RE.match(line):
            yield current, start
            current = []
        if not current:
            start = index
        current.append(line)
        index += 1
    if current:
        yield current, start


def _classify(entry_lines, start_index):
    """``'addon'`` / ``'header'`` / ``None`` for one entry."""
    for line in entry_lines:
        for token in _ADDON_TOKENS:
            if token in line:
                return 'addon'
    if start_index < _HEADER_SCAN_LINES \
            and _HEADER_RE.search(entry_lines[0]):
        return 'header'
    return None


class LogExportView:
    """Export the addon's Kodi-log entries from the script process."""

    def __init__(self, gui, *, read_old_log, read_current_log, write_export,
                 redactions=(), version='', clock=time.time, log_debug=None):
        self._gui = gui
        self._readers = {'kodi.old.log': read_old_log,
                         'kodi.log': read_current_log}
        self._write_export = write_export
        # Longest resolved prefix first: special://profile lives under
        # special://home, and the parent must not swallow the child's
        # match before it runs.
        self._redactions = sorted(
            redactions, key=lambda pair: len(pair[0]), reverse=True)
        self._version = version
        self._clock = clock
        self._log = log_debug or _noop

    def run_export(self):
        """Filter both logs, pick a folder, write one file, report."""
        heading = self._text(_HEADING)
        sources = []
        readable = 0
        matched_total = 0
        for name in _SOURCES:
            collected = self._collect(name)
            if collected is None:
                continue
            readable += 1
            entries, matched = collected
            matched_total += matched
            if entries:
                sources.append((name, entries))
        if not readable:
            self._log("AOMe_LogExportView: no Kodi log file readable")
            self._gui.ok(heading, self._text(_MSG_UNREADABLE))
            return
        if not matched_total:
            # Header-only matches are not a report: nothing the addon
            # logged is in either file (debug just turned on, no playback
            # since restart) — teach the flow instead of writing a shell.
            self._log("AOMe_LogExportView: no addon entries in the logs")
            self._gui.ok(heading, self._text(_MSG_NO_ENTRIES))
            return

        folder = self._gui.browse_folder(heading)
        if not folder:
            self._log("AOMe_LogExportView: export cancelled")
            return
        destination = _join(folder, self._export_name())
        if not self._write_export(destination, self._render(sources)):
            self._log("AOMe_LogExportView: export write failed ({0})"
                      .format(destination))
            self._gui.ok(heading, self._text(_MSG_SAVE_FAILED))
            return
        self._log("AOMe_LogExportView: exported filtered log to {0}"
                  .format(destination))
        self._gui.ok(heading, self._template(_MSG_SAVED, destination))

    # -- collection -----------------------------------------------------------

    def _collect(self, name):
        """``(kept_entries, addon_count)`` for one log file, ``None`` when
        the file does not exist (or its reader could not open it). A
        failure mid-stream keeps what was already collected — a partially
        rotated log still carries the report."""
        try:
            lines = self._readers[name]()
        except Exception as error:
            self._log("AOMe_LogExportView: could not open {0} ({1})"
                      .format(name, error))
            return None
        if lines is None:
            return None
        kept = []
        matched = 0
        errors = []
        for entry, start in _entries(lines, errors.append):
            kind = _classify(entry, start)
            if kind is None:
                continue
            if kind == 'addon':
                matched += 1
            kept.append(entry)
        if errors:
            self._log("AOMe_LogExportView: read of {0} stopped early ({1})"
                      .format(name, errors[0]))
        return kept, matched

    # -- rendering ------------------------------------------------------------

    def _render(self, sources):
        """One text blob: preamble, then each file's kept entries behind a
        labeled divider, oldest file first, redacted line by line. The size
        cap drops whole entries oldest-first (never mid-entry) and announces
        the trim up top.

        The blob leads with a UTF-8 BOM: log lines carry multi-byte
        characters (the notifier's em dash), and without the BOM an editor
        that sniffs encoding can guess ANSI and render them as mojibake.
        """
        combined = deque()
        total = 0
        for name, entries in sources:
            for entry in entries:
                size = sum(len(line) + 1 for line in entry)
                combined.append((name, entry, size))
                total += size
        trimmed = False
        while len(combined) > 1 and total > _MAX_EXPORT_BYTES:
            total -= combined.popleft()[2]
            trimmed = True

        stamp = time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(self._clock()))
        out = ["Audio Offset Manager: Evolved filtered log export"]
        if self._version:
            out.append("Addon version: {0}".format(self._version))
        out.append("Exported: {0}".format(stamp))
        out.append("Contains only this addon's log entries. Local paths "
                   "are shown in special:// or ~/ form.")
        if trimmed:
            out.append("(oldest entries trimmed to keep this file under "
                       "{0} MB)".format(_MAX_EXPORT_BYTES // (1024 * 1024)))
        current = None
        for name, entry, _size in combined:
            if name != current:
                out.append("")
                out.append("==== {0} ====".format(name))
                current = name
            for line in entry:
                out.append(self._redact(line))
        return '\ufeff' + '\n'.join(out) + '\n'

    def _redact(self, line):
        for resolved, special in self._redactions:
            if resolved:
                line = line.replace(resolved, special)
        return _CREDENTIALS_RE.sub('://USERNAME:PASSWORD@', line)

    def _export_name(self):
        """Timestamped filename, second resolution — same collision
        stance as the transfer view's backup name."""
        stamp = time.strftime('%Y%m%d-%H%M%S', time.localtime(self._clock()))
        return 'aome-log-{0}.log'.format(stamp)

    # -- strings --------------------------------------------------------------

    def _text(self, string_id):
        """localized() with the English fallback for must-never-blank strings."""
        return self._gui.localized(string_id) or _FALLBACKS[string_id]

    def _template(self, string_id, *values):
        """The transfer view's format guard: a translation missing any
        expected placeholder, or malformed enough to raise, degrades to
        the English fallback."""
        template = self._text(string_id)
        if any('{' + str(index) + '}' not in template
               for index in range(len(values))):
            template = _FALLBACKS[string_id]
        try:
            return template.format(*values)
        except Exception:
            return _FALLBACKS[string_id].format(*values)

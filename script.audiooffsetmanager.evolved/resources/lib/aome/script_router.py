"""Script-process entry routing (the ``RunScript`` half of the addon).

Like ``runtime.py`` it sits at the ``aome`` package root, outside the layered
subpackages, and composes the Kodi pieces for its own process. The service
and the script run as separate processes whose only shared state is the
on-disk store: the script reads ``offsets.json`` through the read-only reader
and mutates it only over the NotifyAll channel (single writer; report-only
when the service is absent). The import route additionally writes the
``.import`` staging file, a sibling the service consumes, never the store
file itself.

Routes:

- ``manage_offsets`` — the stored-offsets management view (inspection +
  delete/clear only), reached from the settings dialog's action button.
- ``export_offsets`` / ``import_offsets`` — the backup surface (the
  TransferView): verbatim file export to a picked folder, and the staged
  restore over the mutation channel's ``import`` op.
- ``export_log`` — the support-report surface (the LogExportView): the
  addon's entries from both Kodi log files, filtered and redacted, to a
  picked folder. Read-only: it never touches the store or the channel.
- anything else / no argument — open the addon settings (the natural hub).

Every route ends in the settings dialog: the action buttons close it on
press (``<close>true</close>``), so reopening after the view exits returns
the user where they came from. The transfer routes reopen focused on the
Advanced category (their buttons' home), since a plain ``openSettings()``
always lands on the first category, which reads as being teleported away.
"""

import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.aome.app.offset_applier import OffsetApplier
from resources.lib.aome.kodi.gateway import KodiGateway
from resources.lib.aome.kodi.gui import Gui
from resources.lib.aome.kodi.log import KodiLogger
from resources.lib.aome.kodi.mutation_client import MutationClient
from resources.lib.aome.kodi.settings import (ADDON_ID, STORE_PATH, Settings,
                                             import_staging_path)
from resources.lib.aome.store.keys import canonical_key
from resources.lib.aome.store.offset_store import read_import, read_profiles
from resources.lib.aome.view.logexport import LogExportView
from resources.lib.aome.view.manage import ManageView
from resources.lib.aome.view.transfer import TransferView


def handle_script_call(argv=None):
    """Route the RunScript argument (the script process's entry point).

    ``argv`` defaults to ``sys.argv``: RunScript(<id>,manage_offsets)
    arrives as ``argv[1]``.
    """
    args = sys.argv if argv is None else argv
    route = args[1] if len(args) > 1 else ''
    if route == 'manage_offsets':
        _manage_offsets()
        # ...then fall through: the button closed the settings dialog, so
        # every exit from a view lands back in it. The manage button lives in
        # the first category, where a plain reopen lands anyway; the transfer
        # routes reopen focused on Advanced.
    elif route == 'export_offsets':
        _transfer_view().run_export()
        _reopen_settings_at_advanced()
        return
    elif route == 'import_offsets':
        _transfer_view().run_import()
        _reopen_settings_at_advanced()
        return
    elif route == 'export_log':
        _log_export_view().run_export()
        _reopen_settings_at_advanced()
        return
    xbmcaddon.Addon(ADDON_ID).openSettings()


# The settings dialog assigns its category buttons the control ids
# CONTROL_SETTINGS_START_BUTTONS + category index, created by
# CGUIDialogSettingsBase, so skin-independent. The base is -200 (verified in
# xbmc source for Kodi 21 Omega and Kodi 22 master; focusing the button is
# what switches the displayed category). Advanced is the third category in
# settings.xml (index 2) -> -198; the router test derives this constant from
# the XML so a category reorder fails loudly.
CONTROL_SETTINGS_START_BUTTONS = -200
ADVANCED_CATEGORY_FOCUS = CONTROL_SETTINGS_START_BUTTONS + 2

# WINDOW_DIALOG_ADDON_SETTINGS: the wait-for-dialog target below.
SETTINGS_DIALOG_ID = 10140

_FOCUS_WAIT_SECONDS = 2.0    # give the dialog this long to appear
_FOCUS_POLL_SECONDS = 0.05
_FOCUS_SETTLE_MS = 100       # one beat for the dialog's controls to build


def _reopen_settings_at_advanced():
    """Reopen the settings dialog focused on Advanced, where the user was.

    The builtin form is used because ``openSettings()`` always lands on the
    first category. ``Addon.OpenSettings`` only queues the dialog open: a
    ``SetFocus`` issued back-to-back fires while the previous window is still
    active and is silently dropped (observed on Kodi 22), so this waits until
    the addon-settings dialog is the active dialog, lets its controls build
    for a beat, and only then focuses the Advanced category button. Every
    bail-out (dialog never appears, Kodi shutting down) degrades to the
    default first-category landing, never an error.
    """
    xbmc.executebuiltin('Addon.OpenSettings({0})'.format(ADDON_ID))
    monitor = xbmc.Monitor()
    waited = 0.0
    while xbmcgui.getCurrentWindowDialogId() != SETTINGS_DIALOG_ID:
        if waited >= _FOCUS_WAIT_SECONDS:
            return
        if monitor.waitForAbort(_FOCUS_POLL_SECONDS):
            return
        waited += _FOCUS_POLL_SECONDS
    xbmc.sleep(_FOCUS_SETTLE_MS)
    xbmc.executebuiltin('SetFocus({0})'.format(ADVANCED_CATEGORY_FOCUS))


def _script_graph():
    """The per-route composition preamble, written once for every route:
    one logger (with the same debug escalation the service uses), the live
    settings proxy, the plain-dialog gui, the gateway (window-property
    reads), and the mutation client as the only write path to the store."""
    logger = KodiLogger()
    settings = Settings(log=logger)
    logger.debug_escalation = settings.debug_logging_enabled()
    gui = Gui(log=logger)
    gateway = KodiGateway(log=logger)
    client = MutationClient(gateway, log=logger)
    return logger, settings, gui, gateway, client


def _manage_offsets():
    """Compose the management view's process graph and run it: the shared
    preamble plus the read-only reader pointed at the shared STORE_PATH and
    the playing-profile read off the service's published window property
    (canonicalized here so the view compares keys verbatim)."""
    logger, settings, gui, gateway, client = _script_graph()
    store_path = xbmcvfs.translatePath(STORE_PATH)
    view = ManageView(
        lambda: read_profiles(store_path, log_debug=logger.debug),
        gui, client.send,
        per_fps=settings.per_fps_offsets_enabled(),
        distinct_spatial=settings.distinct_spatial_enabled(),
        distinct_channels=settings.distinct_channels_enabled(),
        current_key=lambda: canonical_key(
            gateway.window_property(OffsetApplier.PROFILE_PROPERTY)),
        log_debug=logger.debug)
    view.run()


def _transfer_view():
    """Compose the backup surface's process graph (export/import routes).

    The shared preamble plus the file seams: the read-only readers on the
    shared store/staging paths, and ``xbmcvfs`` as the copy/delete engine so
    VFS sources and destinations (smb://, nfs://, USB mounts) work. The
    staging path comes from ``import_staging_path()``, shared by both
    processes.
    """
    logger, _settings, gui, _gateway, client = _script_graph()
    store_path = xbmcvfs.translatePath(STORE_PATH)
    staging_path = import_staging_path()
    return TransferView(
        gui, client.send,
        read_entries=lambda: read_profiles(store_path,
                                           log_debug=logger.debug),
        read_staged=lambda: read_import(staging_path,
                                        log_debug=logger.debug),
        export_file=lambda destination: bool(
            xbmcvfs.copy(store_path, destination)),
        stage_file=lambda source: bool(xbmcvfs.copy(source, staging_path)),
        discard_staged=lambda: xbmcvfs.delete(staging_path),
        log_debug=logger.debug)


def _log_export_view():
    """Compose the filtered-log export surface (the ``export_log`` route).

    The shared preamble minus the mutation client (the flow never touches the
    store), plus the log seams: line streams over the two Kodi log files, an
    ``xbmcvfs`` writer so VFS destinations work, and the redaction pairs that
    fold resolved ``special://`` roots back to their portable form.
    """
    logger, _settings, gui, _gateway, _client = _script_graph()
    log_dir = xbmcvfs.translatePath('special://logpath/')
    version = xbmcaddon.Addon(ADDON_ID).getAddonInfo('version')
    return LogExportView(
        gui,
        read_old_log=lambda: _log_lines(os.path.join(log_dir,
                                                     'kodi.old.log')),
        read_current_log=lambda: _log_lines(os.path.join(log_dir,
                                                         'kodi.log')),
        write_export=_write_text,
        redactions=_path_redactions(),
        version=version,
        log_debug=logger.debug)


def _log_lines(path):
    """A line stream over one Kodi log file, ``None`` when it is absent.

    Plain ``open`` on purpose: ``special://logpath`` is always a local
    directory, and streaming keeps a multi-hundred-MB debug log out of
    memory (``xbmcvfs.File`` can only hand back whole buffers).
    """
    if not os.path.exists(path):
        return None

    def lines():
        with open(path, 'r', encoding='utf-8', errors='replace') as handle:
            for line in handle:
                yield line
    return lines()


def _write_text(destination, text):
    """Write ``text`` to ``destination`` through xbmcvfs (VFS-capable)."""
    handle = xbmcvfs.File(destination, 'w')
    try:
        return bool(handle.write(text))
    finally:
        handle.close()


def _path_redactions():
    """``(resolved_prefix, folded_form)`` pairs for the export's path
    redaction: the profile root and the Kodi home fold to their
    ``special://`` forms, and the OS user profile folds to ``~/``. A picked
    export destination (Desktop, Downloads) sits under the OS profile but
    outside Kodi's home, and the addon logs such destinations in its own
    lines, so without this pair the username rides into the next export.
    Every prefix also appears in its alternate-separator spelling (Windows
    logs mix ``\\`` and ``/``). The view orders all pairs longest-first, so
    the Kodi roots fold before the ``~/`` pair swallows their prefix."""
    pairs = []
    for special in ('special://profile/', 'special://home/'):
        resolved = xbmcvfs.translatePath(special)
        if not resolved or resolved == special:
            continue
        for variant in _separator_variants(resolved):
            pairs.append((variant, special))
    user_home = os.path.expanduser('~')
    if user_home and user_home != '~':
        if not user_home.endswith(('/', '\\')):
            user_home += os.sep
        for variant in _separator_variants(user_home):
            pairs.append((variant, '~/'))
    return pairs


def _separator_variants(prefix):
    """The prefix itself plus its swapped-separator spelling (if any)."""
    yield prefix
    alternate = (prefix.replace('\\', '/') if '\\' in prefix
                 else prefix.replace('/', '\\'))
    if alternate != prefix:
        yield alternate

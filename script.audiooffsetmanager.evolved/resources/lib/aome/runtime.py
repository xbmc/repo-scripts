"""Composition root for the service process.

Builds the full typed graph (the dispatcher, the Kodi adapters, and the app
components) with explicit, required constructor dependencies: no fallback
construction, exactly one instance of each adapter. Blocks on the monitor
until Kodi aborts, then stops the dispatcher.

Every component subscribes during construction, before the dispatcher thread
starts, so events the bridges queue during construction are dispatched to a
complete graph (matters when the service (re)starts while playback is
already active).

Subscription order is load-bearing, since dispatch follows it per event
type:

1. tracker — the session exists, or is torn down, before any other handler
   of the same lifecycle event runs;
2. detector — owns ``session.profile`` and the stream-state machine, so the
   facts every later handler of the same event reads are settled first. It
   deliberately does NOT handle ``SettingsChanged``; see its module
   docstring;
3. applier — applies the offset and records ``session.applied`` before
   anything downstream reads it;
4. notifier — its StreamStabilized release runs after the applier's retry
   pass for the same stabilization;
5. seek scheduler — seeks are planned only after the offset work is done;
6. adjustment watcher — its ProfileChanged and SettingsChanged passes run
   after the applier's, so ``session.applied`` is current when eligibility
   is evaluated and every delay the applier sets drops an in-flight
   observation;
7. device watcher — last by convention only. Its only output is a posted
   ``AudioDeviceChanged``, dispatched after the current event's handlers
   have all run, so its position does not bind; it does need the tracker
   ahead of it for the session its ticks are stamped with.

One exception precedes that order: the runtime's own ``SettingsChanged``
debug-flag refresh subscribes first, so the passes for the very save that
toggles debug logging already log at the fresh escalation level.
"""

import xbmcvfs

from resources.lib.aome.app import events
from resources.lib.aome.app.adjustment_watcher import AdjustmentWatcher
from resources.lib.aome.app.device_watcher import DeviceWatcher
from resources.lib.aome.app.dispatcher import Dispatcher
from resources.lib.aome.app.notifier import Notifier
from resources.lib.aome.app.offset_applier import OffsetApplier
from resources.lib.aome.app.seek_scheduler import (ExternalSeekCoordinator,
                                                  SeekScheduler)
from resources.lib.aome.app.session import SessionTracker
from resources.lib.aome.app.store_mutations import (ACK_MESSAGE,
                                                   StoreMutationHandler)
from resources.lib.aome.app.stream_detector import StreamDetector
from resources.lib.aome.kodi.gateway import KodiGateway
from resources.lib.aome.kodi.gui import Gui
from resources.lib.aome.kodi.log import KodiLogger
from resources.lib.aome.kodi.monitor_bridge import MonitorBridge
from resources.lib.aome.kodi.player_bridge import PlayerBridge
from resources.lib.aome.kodi.settings import (ADDON_ID, STORE_PATH, Settings,
                                             import_staging_path)
from resources.lib.aome.store.offset_store import (CORRUPTION_RECOVERED,
                                                  OffsetStore)
from resources.lib.aome.store.table import OffsetTable

# The original addon this one supersedes. Both enabled at once can apply
# audio offsets twice, so the service warns once per install.
CLASSIC_ADDON_ID = 'script.audiooffsetmanager'
STRING_COEXISTENCE_HEADING = 32129
STRING_COEXISTENCE_BODY = 32130


class ServiceRuntime:
    def __init__(self):
        # Adapters first: one instance each, injected everywhere.
        self.logger = KodiLogger()
        self.settings = Settings(log=self.logger)
        self.logger.debug_escalation = self.settings.debug_logging_enabled()
        self.gateway = KodiGateway(log=self.logger)
        self.gui = Gui(log=self.logger)

        # Loaded once at service start, owned by the dispatcher thread
        # thereafter (single writer). load() quarantines a corrupt file to
        # .bad; the typed StoreCorrupted event is posted after the graph is
        # built, so the Notifier owns the notice.
        self.store = OffsetStore(
            xbmcvfs.translatePath(STORE_PATH),
            log_debug=self.logger.debug, log_warning=self.logger.warning)
        self.store.load()
        self.offsets = OffsetTable(self.store, self.settings)

        self.dispatcher = Dispatcher(
            log_debug=self.logger.debug,
            log_error=self.logger.error,
            log_runtimes=self.logger.debug_escalation)

        # Debug-flag refresh subscribes first (before any component), so the
        # applier/watcher passes for the very save that toggles debug logging
        # already run at the fresh escalation level.
        self.dispatcher.subscribe(events.SettingsChanged,
                                  self._on_settings_changed)

        # App components, in the load-bearing subscription order (docstring).
        self.session_tracker = SessionTracker(
            self.dispatcher, log_debug=self.logger.debug)
        self.detector = StreamDetector(
            self.dispatcher, self.session_tracker, self.gateway,
            self.settings, log_debug=self.logger.debug,
            log_warning=self.logger.warning)
        self.offset_applier = OffsetApplier(
            self.dispatcher, self.session_tracker, self.gateway,
            self.settings, self.offsets, log_debug=self.logger.debug,
            log_warning=self.logger.warning)
        # The table is the notifier's device-label source (the store knows
        # every device, and only the set can say whether two share a name).
        self.notifier = Notifier(
            self.dispatcher, self.session_tracker, self.settings, self.gui,
            self.offsets, log_debug=self.logger.debug)
        self.seek_coordinator = ExternalSeekCoordinator(
            self.gateway, log_debug=self.logger.debug)
        self.seek_scheduler = SeekScheduler(
            self.dispatcher, self.session_tracker, self.settings,
            self.seek_coordinator, log_debug=self.logger.debug,
            log_warning=self.logger.warning)
        self.adjustment_watcher = AdjustmentWatcher(
            self.dispatcher, self.session_tracker, self.gateway,
            self.settings, self.offsets, log_debug=self.logger.debug,
            log_warning=self.logger.warning)
        # Last, and unordered with respect to everything above: it only
        # posts AudioDeviceChanged, which the detector treats like Kodi's own
        # AvChanged. Dormant unless the distinct-devices toggle is on.
        self.device_watcher = DeviceWatcher(
            self.dispatcher, self.session_tracker, self.gateway,
            self.settings, log_debug=self.logger.debug)
        # The cross-process mutation channel's executor: requests arrive via
        # the monitor bridge as typed events, mutate the store on this
        # dispatcher, and ack back over NotifyAll so the script process can
        # tell "done" from "no service".
        self.store_mutations = StoreMutationHandler(
            self.dispatcher, self.session_tracker, self.store, self.gateway,
            lambda payload: self.gateway.notify_all(
                ADDON_ID, ACK_MESSAGE, payload),
            import_path=import_staging_path(),
            log_debug=self.logger.debug, log_warning=self.logger.warning)

        self.player_bridge = PlayerBridge(self.dispatcher)
        self.monitor = MonitorBridge(self.dispatcher)

        # Retract any published-profile property a crashed predecessor left
        # behind: window properties persist until Kodi exits, and a stale
        # key would tag a dead playback in the management view.
        self.offset_applier.clear_published_profile()

        # Surface the one-shot corruption flag through the graph. Posted
        # here and queued until the dispatcher starts, so the Notifier
        # raises the notice rather than this composition root.
        corruption = self.store.pop_corruption()
        if corruption is not None:
            self.dispatcher.post(events.StoreCorrupted(
                recovered=corruption == CORRUPTION_RECOVERED))

    def _on_settings_changed(self, _event):
        """Refresh the cached debug flags; never write settings from here."""
        debug = self.settings.debug_logging_enabled()
        self.logger.debug_escalation = debug
        self.dispatcher.log_runtimes = debug

    def _maybe_warn_coexistence(self):
        """One-time warning when the original addon is enabled alongside.

        Probes only while the once-flag is unset, and writes the flag only
        after the dialog actually showed, so a transient probe failure still
        warns on a future start. Runs from ``run()`` after the dispatcher
        starts, where the modal blocks only this service thread.
        """
        if self.settings.coexistence_warned():
            return
        if not self.gateway.addon_enabled(CLASSIC_ADDON_ID):
            return
        # localized() degrades to '' on failure and a blank warning teaches
        # nothing, so both strings carry English fallbacks.
        heading = self.gui.localized(STRING_COEXISTENCE_HEADING) or (
            "Classic Audio Offset Manager detected")
        body = self.gui.localized(STRING_COEXISTENCE_BODY) or (
            "Audio Offset Manager: Evolved and the classic Audio Offset "
            "Manager are both "
            "enabled. Running both can apply audio offsets twice. "
            "Consider disabling the classic addon.")
        if not self.gui.ok(heading, body):
            # The dialog never rendered, so leave the flag unset: it means
            # "the user has seen this", not "we tried".
            return
        if self.gateway.settings_dialog_open():
            # Never write a setting while the settings dialog is open, since
            # its save-on-close clobbers the write. A service restart can
            # land under an open dialog, so skip the write and let the
            # warning re-fire on a later start.
            self.logger.debug("AOMe_Runtime: deferring coexistence flag "
                              "(settings dialog open)")
            return
        self.settings.store_boolean_if_changed('coexistence_warned', True)
        self.logger.debug("AOMe_Runtime: coexistence warning shown")

    def run(self):
        self.dispatcher.start()
        self.logger.debug("AOMe_Runtime: service started")

        self._maybe_warn_coexistence()
        self.monitor.waitForAbort()

        self.logger.debug("AOMe_Runtime: abort requested; shutting down")
        # Joining the dispatcher thread is the whole shutdown: every
        # subscription lives on the dispatcher, and posts arriving after stop
        # are dropped by design.
        self.dispatcher.stop()
        # After the join no publish can race this final retract, without
        # which the property would outlive the service until Kodi exits.
        self.offset_applier.clear_published_profile()

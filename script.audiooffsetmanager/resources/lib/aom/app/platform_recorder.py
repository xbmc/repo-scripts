"""Platform capability recorder: the detection side effects, made explicit.

This component performs the platform-capability writes as an event-driven
consumer of ``StreamProbed``, so detection itself stays pure:

- ``platform_hdr_full`` / ``advanced_hlg`` — store-if-changed on every probe.
- ``new_install`` — read once at service start and cleared on the first
  observed probe of this service lifetime. Queue order gives the
  flip-before-apply sequence: the detector posts ``StreamProbed`` before
  ``ProfileChanged``, so the flag is cleared before the offset applier's
  ``is_new_install`` gate reads it.

No session guard on purpose: platform facts are session-independent — a
probe stamped with a superseded session still observed the real platform.

Writes defer while the addon settings dialog is open (settings-state
doctrine: its save-on-close would clobber them). A skipped probe is not
retried explicitly — the values are re-observed and re-stored by the next
gather, and the ``new_install`` latch is only consumed after its store
succeeds (a deferred or failed write leaves it armed for the next probe),
so nothing is lost, only delayed.

Pure app layer: no Kodi imports; settings via the injected adapter, the
dialog question via the injected gateway.
"""

from resources.lib.aom.app import events


class PlatformRecorder:
    def __init__(self, dispatcher, gateway, settings, *, log_debug):
        self._gateway = gateway
        self._settings = settings
        self._log = log_debug
        self._new_install = settings.is_new_install()
        dispatcher.subscribe(events.StreamProbed, self._on_probed)

    def _on_probed(self, event):
        if self._gateway.settings_dialog_open():
            # Deferred, not dropped: the next probe re-observes everything,
            # and the new-install latch below stays armed.
            self._log("AOM_PlatformRecorder: settings dialog open; "
                      "deferring platform writes")
            return
        self._settings.store_boolean_if_changed('platform_hdr_full',
                                                event.platform_hdr_full)
        self._settings.store_boolean_if_changed('advanced_hlg',
                                                event.advanced_hlg)
        if self._new_install:
            if self._settings.store_boolean_if_changed('new_install', False):
                self._new_install = False
                self._log("AOM_PlatformRecorder: new-install flag cleared on "
                          "first playback")

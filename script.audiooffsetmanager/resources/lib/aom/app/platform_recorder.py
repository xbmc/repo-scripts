"""Platform capability recorder: the detection side effects, made explicit.

This component performs the platform-capability writes
(``platform_hdr_full`` / ``advanced_hlg``, store-if-changed on every probe)
as an event-driven consumer of ``StreamProbed``, so detection itself stays
pure. The flags drive settings-UI visibility: capability-gated elements
appear once the first playback stores them.

``platform_hdr10plus`` is a sticky latch, never written False: it means
"this platform can detect HDR10+". Three proofs latch it, checked in the
order they can occur:

- the Kodi build version — Kodi 22+ presents ``hdr10plus`` natively through
  ``VideoPlayer.HdrType`` (Kodi 20/21 reported plain ``hdr10``), so the
  ``ServiceStarted`` check unlocks the HDR10+ settings at startup with no
  playback required;
- the full HDR label on any probe (that label distinguishes HDR10+ from
  HDR10, whatever the Kodi version);
- an actually observed ``hdr10plus`` profile — the field-proof fallback for
  builds the version check does not anticipate.

Latching (rather than mirroring the live probe) keeps the capability true
across the non-HDR10+ streams that follow.

No session guard on purpose: platform facts are session-independent — a
probe stamped with a superseded session still observed the real platform.

Writes defer while the addon settings dialog is open (settings-state
doctrine: its save-on-close would clobber them). A skipped probe is not
retried explicitly — the values are re-observed and re-stored by the next
gather, so nothing is lost, only delayed. A deferred startup check (only
possible on a service restart, never on Kodi startup) recovers the same
way: the next Kodi start or HDR10+ observation re-latches.

Pure app layer: no Kodi imports; settings via the injected adapter, the
dialog question and the build-version InfoLabel via the injected gateway.
"""

import re

from resources.lib.aom.app import events


INFOLABEL_BUILD_VERSION = 'System.BuildVersion'

# First Kodi major that reports 'hdr10plus' natively via VideoPlayer.HdrType.
NATIVE_HDR10PLUS_MAJOR = 22


def parse_kodi_major(raw):
    """Leading major version of a System.BuildVersion reading, or None.

    Real readings look like ``"22.0 (22.0.0) Git:20260101-abcdef"``; anything
    that does not start with digits (empty, label echo) parses to None.
    """
    match = re.match(r'\s*(\d+)', raw or '')
    return int(match.group(1)) if match else None


class PlatformRecorder:
    def __init__(self, dispatcher, gateway, settings, *, log_debug):
        self._gateway = gateway
        self._settings = settings
        self._log = log_debug
        dispatcher.subscribe(events.ServiceStarted, self._on_service_started)
        dispatcher.subscribe(events.StreamProbed, self._on_probed)

    def _on_service_started(self, _event):
        if self._gateway.settings_dialog_open():
            self._log("AOM_PlatformRecorder: settings dialog open; "
                      "deferring startup capability check")
            return
        major = parse_kodi_major(
            self._gateway.infolabel(INFOLABEL_BUILD_VERSION))
        if major is not None and major >= NATIVE_HDR10PLUS_MAJOR:
            self._log(f"AOM_PlatformRecorder: Kodi {major} detects HDR10+ "
                      f"natively; latching platform_hdr10plus")
            self._settings.store_boolean_if_changed('platform_hdr10plus',
                                                    True)

    def _on_probed(self, event):
        if self._gateway.settings_dialog_open():
            # Deferred, not dropped: the next probe re-observes everything.
            self._log("AOM_PlatformRecorder: settings dialog open; "
                      "deferring platform writes")
            return
        self._settings.store_boolean_if_changed('platform_hdr_full',
                                                event.platform_hdr_full)
        self._settings.store_boolean_if_changed('advanced_hlg',
                                                event.advanced_hlg)
        if event.platform_hdr_full or event.hdr_type == 'hdr10plus':
            self._settings.store_boolean_if_changed('platform_hdr10plus', True)

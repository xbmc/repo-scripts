"""Script-side onboarding: the test-video flow, the bypass, and settings.

The composition glue for the ``RunScript`` entry point (``script.py``). Like
``runtime.py`` it sits at the ``aom`` package root, outside the layered
subpackages, and wires the Kodi adapters for its own process: the service
and the script run as SEPARATE processes whose only shared state is the live
on-disk settings store (settings doctrine — no manual reload exists or is
needed).

Write-ordering doctrine (load-bearing): the bypass button in
settings.xml uses ``<close>true</close>``, so the settings dialog is already
CLOSED when ``bypass_test_video`` writes ``new_install`` — writing while the
dialog is open would let its save-on-close overwrite us. The short sleep
afterwards lets the write settle before the dialog reopens and re-reads it.

User-facing strings resolve through the ``Gui`` adapter's
``getLocalizedString``; error toasts pass Gui a custom title/icon.
"""

import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.aom.kodi.gui import Gui
from resources.lib.aom.kodi.log import KodiLogger
from resources.lib.aom.kodi.settings import ADDON_ID, Settings

STRING_ERROR = 32094
STRING_TEST_VIDEO_NOT_FOUND = 32095
STRING_PLEASE_WAIT = 32096
STRING_TEST_VIDEO_COMPLETED = 32097
STRING_BYPASSED = 32098
STRING_BYPASS_FAILED = 32099

TEST_VIDEO_RELATIVE_PATH = '/resources/media/test-video.mp4'


def handle_script_call():
    """Route the RunScript argument (the script process's entry point)."""
    if len(sys.argv) > 1 and sys.argv[1] == 'play_test_video':
        _Onboarding().play_test_video()
    elif len(sys.argv) > 1 and sys.argv[1] == 'bypass_test_video':
        _Onboarding().bypass_test_video()
    else:
        # No (or unknown) argument: just open the addon settings.
        xbmcaddon.Addon(ADDON_ID).openSettings()


class _Onboarding:
    """One script invocation's worth of wiring (constructed per call)."""

    def __init__(self):
        self._log = KodiLogger()
        self._settings = Settings(log=self._log)
        self._log.debug_escalation = self._settings.debug_logging_enabled()
        self._gui = Gui(log=self._log)
        addon = xbmcaddon.Addon(ADDON_ID)
        addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self._test_video_path = xbmcvfs.translatePath(
            addon_path + TEST_VIDEO_RELATIVE_PATH)

    def play_test_video(self):
        """Play the test video for 5 seconds and return to addon settings.

        The blocking sleep is fine HERE: this is the short-lived script
        process, not the service's dispatcher thread.
        """
        if not xbmcvfs.exists(self._test_video_path):
            self._gui.notification(
                self._gui.localized(STRING_TEST_VIDEO_NOT_FOUND),
                duration_ms=5000,
                title=self._gui.localized(STRING_ERROR),
                icon=xbmcgui.NOTIFICATION_ERROR)
            return

        xbmc.Player().play(self._test_video_path)
        self._gui.notification(
            f"{self._gui.localized(STRING_PLEASE_WAIT)}...",
            duration_ms=10000)

        xbmc.sleep(5000)
        self._stop_if_still_test_video()

        self._gui.notification(
            self._gui.localized(STRING_TEST_VIDEO_COMPLETED),
            duration_ms=10000)
        xbmc.executebuiltin(f'Addon.OpenSettings({ADDON_ID})')

    def _stop_if_still_test_video(self):
        """Stop playback only while the test video is still the playing item.

        The stop fires 5s after play() on wall time, not on a playback
        handle: by then the test video may have failed to open, or the user
        may have started something else, and a blind ``Player().stop()``
        would kill that instead. Paths compare separator/case-normalized
        (Kodi reports either slash direction on Windows), and the
        isPlaying/getPlayingFile pair can race a natural stop, so a raise
        reads as "not our video".
        """
        player = xbmc.Player()
        try:
            playing = player.getPlayingFile() if player.isPlaying() else None
        except Exception:
            playing = None
        if playing is None:
            self._log("AOM_Onboarding: test video no longer playing; "
                      "nothing to stop", xbmc.LOGDEBUG)
            return
        if (os.path.normcase(os.path.normpath(playing))
                != os.path.normcase(os.path.normpath(self._test_video_path))):
            self._log(f"AOM_Onboarding: another item is playing ({playing}); "
                      f"leaving it alone", xbmc.LOGDEBUG)
            return
        player.stop()

    def bypass_test_video(self):
        """Clear new_install without playing the test video.

        Runs from the bypass action button, which uses ``<close>true</close>``
        so the settings dialog is already closed by the time we write — the
        ordering that makes the write stick (see the module docstring).
        """
        if not self._settings.store_boolean_if_changed('new_install', False):
            self._log("AOM_Onboarding: Failed to bypass test video "
                      "requirement", xbmc.LOGWARNING)
            self._gui.notification(
                self._gui.localized(STRING_BYPASS_FAILED),
                duration_ms=3000,
                title=self._gui.localized(STRING_ERROR),
                icon=xbmcgui.NOTIFICATION_ERROR)
            return

        self._log("AOM_Onboarding: Successfully bypassed test video "
                  "requirement", xbmc.LOGINFO)
        self._gui.notification(self._gui.localized(STRING_BYPASSED),
                               duration_ms=3000)

        # Let the write settle to disk before the dialog reopens and reads it.
        xbmc.sleep(500)
        xbmc.executebuiltin(f'Addon.OpenSettings({ADDON_ID})')

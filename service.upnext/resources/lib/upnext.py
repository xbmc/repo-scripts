# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from time import monotonic
from xbmc import executebuiltin, getCondVisibility
from xbmcgui import ControlButton, getCurrentWindowDialogId
from popup import Popup
from utils import get_setting_bool, localize

ACTION_SHOW_OSD = 24
ACTION_MOVE_UP = 3


class UpNext(Popup):
    watchnow = False
    auto_advance = False
    playback_control = None
    playback_dialog_id = None
    controls_pending = False
    controls_seen = False
    controls_check_at = 0

    def onInit(self):  # pylint: disable=invalid-name
        super().onInit()
        if get_setting_bool('stopAfterClose'):
            self.getControl(3013).setLabel(localize(30033))  # Stop
        else:
            self.getControl(3013).setLabel(localize(30034))  # Close
        self.playback_dialog_id = getCurrentWindowDialogId()
        if get_setting_bool('selectOpensPlaybackControls'):
            if self.playback_control is None:
                self.prepare_playback_controls()
            else:
                self.setFocus(self.playback_control)

    def prepare_playback_controls(self):
        """Let Select open the player until navigation enters the popup buttons."""
        # A neutral focus target works with existing skin overrides too. It adds
        # no visible button and leaves every existing button's action unchanged.
        self.playback_control = ControlButton(
            -1000, -1000, 1, 1, '', focusTexture='', noFocusTexture='')
        self.addControl(self.playback_control)
        try:
            target = self.getControl(20)  # Default skin's visible button group.
        except RuntimeError:
            target = self.getControl(3012)  # Skins with a direct Watch now button.
        self.playback_control.setNavigation(target, target, target, target)
        self.setFocus(self.playback_control)

    def open_playback_controls(self):
        # The native OSD takes input while the next-episode popup stays visible.
        # Returning from the OSD restores the popup without cancelling playback.
        self.controls_pending = True
        self.controls_seen = False
        self.controls_check_at = 0
        executebuiltin('ActivateWindow(videoosd)')

    def restore_after_playback_controls(self):
        """Restore a hidden popup after Kodi closes the playback controls."""
        if (not self.controls_pending or not self.playback_dialog_id or self.is_cancel()
                or self.is_watch_now() or self.is_auto_advance()):
            return
        now = monotonic()
        if now < self.controls_check_at:
            return
        if getCondVisibility('Window.IsVisible(videoosd)'):
            self.controls_seen = True
            self.controls_check_at = now + .5
        elif self.controls_seen:
            self.controls_pending = False
            if not getCondVisibility('Window.IsVisible(%d)' % self.playback_dialog_id):
                self.show()

    def onClick(self, controlId):  # pylint: disable=invalid-name
        if self.playback_control is not None and controlId == self.playback_control.getId():
            self.open_playback_controls()
        else:
            super().onClick(controlId)

    def onAction(self, action):  # pylint: disable=invalid-name
        if action == ACTION_SHOW_OSD:
            self.open_playback_controls()
        elif (action == ACTION_MOVE_UP and self.playback_control is not None
              and self.getFocusId() != self.playback_control.getId()):
            # Return from the horizontal Next/Close buttons to the neutral
            # target so Select can open playback controls again.
            self.setFocus(self.playback_control)
        else:
            super().onAction(action)

    def set_credits_countdown(self, remaining=None):
        self.setProperty('credits_countdown', 'true' if remaining is not None else '')
        self.setProperty('credits_remaining', str(remaining) if remaining is not None else '')
        if remaining is not None:
            self.setProperty('remaining', '%02d' % remaining)

    def set_watch_now(self, watchnow):
        self.watchnow = watchnow

    def is_watch_now(self):
        return self.watchnow

    def set_auto_advance(self):
        self.auto_advance = True

    def is_auto_advance(self):
        return self.auto_advance

    def confirm(self):
        self.set_watch_now(True)

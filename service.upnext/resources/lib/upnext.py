# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from popup import Popup
from utils import get_setting_bool, localize


class UpNext(Popup):
    watchnow = False
    auto_advance = False

    def onInit(self):  # pylint: disable=invalid-name
        super().onInit()
        if get_setting_bool('stopAfterClose'):
            self.getControl(3013).setLabel(localize(30033))  # Stop
        else:
            self.getControl(3013).setLabel(localize(30034))  # Close

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

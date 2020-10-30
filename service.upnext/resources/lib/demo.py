# -*- coding: utf-8 -*-
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)

from __future__ import absolute_import, division, unicode_literals
from xbmcgui import ControlLabel, getScreenHeight, getScreenWidth, Window
from utils import localize, log as ulog


class DemoOverlay():
    def __init__(self, windowid):
        self.window = Window(windowid)
        self._demolabel = None
        self.log('initialized')

    def log(self, msg, level=2):
        ulog(msg, name=self.__class__.__name__, level=level)

    def show(self):
        if self._demolabel is not None:
            return
        # FIXME: Using a different font does not seem to have much of an impact
        self._demolabel = ControlLabel(0, getScreenHeight() // 4, getScreenWidth(), 100, localize(30060) + '\n' + localize(30061), font='font36_title', textColor='0xddee9922', alignment=0x00000002)
        self.window.addControl(self._demolabel)
        self.log('show', 0)

    def hide(self):
        if self._demolabel is None:
            return
        self.window.removeControl(self._demolabel)
        self._demolabel = None
        self.log('hide', 0)

    def _close(self):
        self.hide()
        self.log('closed', 0)

    def __del__(self):
        self.hide()
        self.log('destroy', 0)

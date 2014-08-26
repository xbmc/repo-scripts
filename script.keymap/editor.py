# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from threading import Timer
from collections_backport import OrderedDict
from xbmcgui import Dialog, WindowXMLDialog
from actions import ACTIONS, WINDOWS
from utils import tr


class Editor(object):
    def __init__(self, defaultkeymap, userkeymap):
        self.defaultkeymap = defaultkeymap
        self.userkeymap = userkeymap
        self.dirty = False

    def start(self):
        while True:
            idx = Dialog().select(tr(30007), WINDOWS.values())
            if idx == -1:
                break
            window = WINDOWS.keys()[idx]

            while True:
                idx = Dialog().select(tr(30008), ACTIONS.keys())
                if idx == -1:
                    break
                category = ACTIONS.keys()[idx]

                while True:
                    curr_keymap = self._current_keymap(window, category)
                    labels = ["%s - %s" % (name, key) for _, key, name in curr_keymap]
                    idx = Dialog().select(tr(30009), labels)
                    if idx == -1:
                        break
                    action, oldkey, _ = curr_keymap[idx]
                    newkey = KeyListener.record_key()
                    if newkey is None:
                        continue

                    old = (window, action, oldkey)
                    new = (window, action, newkey)
                    if old in self.userkeymap:
                        self.userkeymap.remove(old)
                    self.userkeymap.append(new)
                    if old != new:
                        self.dirty = True

    def _current_keymap(self, window, category):
        actions = OrderedDict([(action, "") for action in ACTIONS[category].keys()])
        for w, a, k in self.defaultkeymap:
            if w == window:
                if a in actions.keys():
                    actions[a] = k
        for w, a, k in self.userkeymap:
            if w == window:
                if a in actions.keys():
                    actions[a] = k
        names = ACTIONS[category]
        return [(action, key, names[action]) for action, key in actions.iteritems()]


class KeyListener(WindowXMLDialog):
    TIMEOUT = 5

    def __new__(cls):
        return super(KeyListener, cls).__new__(cls, "DialogKaiToast.xml", "")

    def __init__(self):
        self.key = None

    def onInit(self):
        try:
            self.getControl(401).addLabel(tr(30002))
            self.getControl(402).addLabel(tr(30010) % self.TIMEOUT)
        except AttributeError:
            self.getControl(401).setLabel(tr(30002))
            self.getControl(402).setLabel(tr(30010) % self.TIMEOUT)

    def onAction(self, action):
        code = action.getButtonCode()
        self.key = None if code == 0 else str(code)
        self.close()

    @staticmethod
    def record_key():
        dialog = KeyListener()
        timeout = Timer(KeyListener.TIMEOUT, dialog.close)
        timeout.start()
        dialog.doModal()
        timeout.cancel()
        key = dialog.key
        del dialog
        return key

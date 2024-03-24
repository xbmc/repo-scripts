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

import xbmc
import xbmcaddon
from threading import Timer
from collections import OrderedDict
from xbmcgui import Dialog, WindowXMLDialog
from resources.lib.actions import ACTIONS, WINDOWS
from resources.lib.utils import tr

KODIMONITOR = xbmc.Monitor()


class Editor(object):
    def __init__(self, defaultkeymap, userkeymap):
        """Create the editor object."""
        self.defaultkeymap = defaultkeymap
        self.userkeymap = userkeymap
        self.dirty = False

    def start(self):
        while not KODIMONITOR.abortRequested():
            # Select context menu
            idx = Dialog().select(tr(30007), list(WINDOWS.values()))
            if idx == -1:
                break
            window = list(WINDOWS.keys())[idx]

            while not KODIMONITOR.abortRequested():
                # Select category menu
                idx = Dialog().select(tr(30008), list(ACTIONS.keys()))
                if idx == -1:
                    break
                category = list(ACTIONS.keys())[idx]

                while not KODIMONITOR.abortRequested():
                    # Select action menu
                    current_keymap = self._current_keymap(window, category)
                    labels = ["%s - %s" % (name, key)
                              for _, key, name in current_keymap]
                    idx = Dialog().select(tr(30009), labels)
                    if idx == -1:
                        break
                    action, current_key, _ = current_keymap[idx]
                    old_mapping = (window, action, current_key)

                    # Ask what to do
                    idx = Dialog().select(tr(30000), [tr(30011), tr(30012)])
                    if idx == -1:
                        continue
                    elif idx == 1:
                        # Remove
                        if old_mapping in self.userkeymap:
                            self.userkeymap.remove(old_mapping)
                            self.dirty = True
                    elif idx == 0:
                        # Edit key
                        newkey = KeyListener.record_key()
                        if newkey is None:
                            continue

                        new_mapping = (window, action, newkey)
                        if old_mapping in self.userkeymap:
                            self.userkeymap.remove(old_mapping)
                        self.userkeymap.append(new_mapping)
                        if old_mapping != new_mapping:
                            self.dirty = True

    def _current_keymap(self, window, category):
        actions = OrderedDict([(action, "")
                              for action in ACTIONS[category].keys()])
        for w, a, k in self.defaultkeymap:
            if w == window:
                if a in actions.keys():
                    actions[a] = k
        for w, a, k in self.userkeymap:
            if w == window:
                if a in actions.keys():
                    actions[a] = k
        names = ACTIONS[category]
        return [(action, key, names[action]) for action, key in actions.items()]


class KeyListener(WindowXMLDialog):
    TIMEOUT = 5

    def __new__(cls):
        gui_api = tuple(map(int, xbmcaddon.Addon(
            'xbmc.gui').getAddonInfo('version').split('.')))
        file_name = "DialogNotification.xml" if gui_api >= (
            5, 11, 0) else "DialogKaiToast.xml"
        return super(KeyListener, cls).__new__(cls, file_name, "")

    def __init__(self):
        """Initialize key variable."""
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

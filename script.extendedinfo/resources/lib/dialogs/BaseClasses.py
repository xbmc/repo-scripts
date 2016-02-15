# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui


class WindowXML(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXML.__init__(self)
        self.window_type = "window"

    def onInit(self):
        self.window_id = xbmcgui.getCurrentWindowId()
        self.window = xbmcgui.Window(self.window_id)

    def setProperty(self, key, value):
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        self.window.clearProperty(key)


class DialogXML(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.window_type = "dialog"

    def onInit(self):
        self.window_id = xbmcgui.getCurrentWindowDialogId()
        self.window = xbmcgui.Window(self.window_id)

    def setProperty(self, key, value):
        self.window.setProperty(key, value)

    def clearProperty(self, key):
        self.window.clearProperty(key)

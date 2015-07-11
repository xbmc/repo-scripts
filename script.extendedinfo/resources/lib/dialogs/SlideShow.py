# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from ..Utils import *


class SlideShow(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_LEFT = [1]
    ACTION_RIGHT = [2]

    def __init__(self, *args, **kwargs):
        self.imagelist = kwargs.get('imagelist')
        self.index = kwargs.get('index')
        self.image = kwargs.get('image')
        self.action = None

    def onInit(self):
        if self.imagelist:
            self.getControl(10000).addItems(create_listitems(self.imagelist))
            xbmc.executebuiltin("Control.SetFocus(10000,%s)" % self.index)
        else:
            listitem = {"label": self.image,
                        "thumb": self.image}
            self.getControl(10000).addItems(create_listitems([listitem]))

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()
        elif action in self.ACTION_LEFT:
            self.action = "left"
            self.close()
        elif action in self.ACTION_RIGHT:
            self.action = "right"
            self.close()


# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from ..Utils import *
from .BaseClasses import DialogXML


class SlideShow(DialogXML):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    C_LIST_PICTURES = 5000

    def __init__(self, *args, **kwargs):
        self.imagelist = kwargs.get('listitems')
        self.index = kwargs.get('index')
        self.image = kwargs.get('image')
        self.action = None

    def onInit(self):
        super(SlideShow, self).onInit()
        if self.imagelist:
            self.getControl(self.C_LIST_PICTURES).addItems(create_listitems(self.imagelist))
            self.getControl(self.C_LIST_PICTURES).selectItem(self.index)
            self.setFocusId(self.C_LIST_PICTURES)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.position = self.getControl(self.C_LIST_PICTURES).getSelectedPosition()
            self.close()

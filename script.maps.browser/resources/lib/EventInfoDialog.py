# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from Eventful import Eventful


class EventInfoDialog(xbmcgui.WindowXMLDialog):
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    C_TEXT_FIELD = 200
    C_TITLE = 201
    C_BIG_IMAGE = 211
    C_ARTIST_LIST = 500

    def __init__(self, *args, **kwargs):
        super(EventInfoDialog, self).__init__(*args, **kwargs)
        self.eventful_id = kwargs.get('eventful_id')
        if self.eventful_id:
            EF = Eventful()
            self.props = EF.get_venue_info(self.eventful_id)
            self.events = self.props["events"]["event"]
        self.pins = ""

    def onInit(self):
        self.getControl(self.C_TEXT_FIELD).setText(self.props["description"])
        self.getControl(self.C_TITLE).setLabel(self.props["name"])
        self.getControl(self.C_BIG_IMAGE).setImage(self.props["thumb"])

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, controlID):
        if controlID == self.C_ARTIST_LIST:
            self.close()

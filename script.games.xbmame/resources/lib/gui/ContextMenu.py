# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
#
# The Original Code is plugin.games.xbmame.
#
# The Initial Developer of the Original Code is Olivier LODY aka Akira76.
# Portions created by the XBMC team are Copyright (C) 2003-2010 XBMC.
# All Rights Reserved.

import xbmcgui

class ContextMenu(xbmcgui.WindowXMLDialog):

    CONTROL_BORDER = 30322
    CONTROL_BOX = 30323
    CONTROL_BEVEL = 30324
    CONTROL_LIST = 30321
    CONTROL_OK = 10

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.menu = kwargs["menu"].split(",")
        self.doModal()

    def onInit(self):
        # Autosizing
        box = self.getControl(self.CONTROL_BORDER)
        box.setHeight(32 + len(self.menu)*16)
        box.setWidth(320)
        box = self.getControl(self.CONTROL_BOX)
        box.setHeight(16 + len(self.menu)*16)
        box.setWidth(304)
        box = self.getControl(self.CONTROL_BEVEL)
        box.setHeight(16 + len(self.menu)*16)
        box.setWidth(304)
        self._LIST = self.getControl(self.CONTROL_LIST)
        self._LIST.setHeight(len(self.menu)*16)
        for i in range(len(self.menu)/2):
            menuitem = xbmcgui.ListItem(self.menu[i * 2])
            menuitem.setProperty("action", self.menu[i * 2 + 1])
            self._LIST.addItem(menuitem)

    def onClick( self, controlId ):
        obj = self._LIST.getSelectedItem()
        self.action = obj.getProperty("action")
        self.close()

    def onFocus( self, controlId ):
        pass

    def onAction(self, action):
        if action.getId()==10 or action.getId()==117:
            self.action = ""
            self.close()

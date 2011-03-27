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

class Dialog(xbmcgui.WindowXMLDialog):

    CONTROL_BORDER = 30322
    CONTROL_BOX = 30323
    CONTROL_BEVEL = 30324
    CONTROL_LIST = 30321
    CONTROL_OK = 10

    CONTROL_TITLE = 30351
    CONTROL_LABEL1 = 30352
    CONTROL_LABEL2 = 30353
    CONTROL_LABEL3 = 30354
    CONTROL_OK_BUTTONS = 30355
    CONTROL_YESNO_BUTTONS = 30357

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.title=""
        self.label1=""
        self.label2=""
        self.label3=""
        self.buttons=0

    def ok(self, title="", line1="", line2="", line3=""):
        self.buttons = self.CONTROL_OK_BUTTONS
        self.title = title
        self.label1 = line1
        self.label2 = line2
        self.label3 = line3
        self.doModal()
        return True

    def onInit(self):
        self.getControl(self.CONTROL_OK_BUTTONS).setVisible(False)
        self.getControl(self.CONTROL_YESNO_BUTTONS).setVisible(False)
        self.getControl(self.CONTROL_TITLE).setLabel(self.title)
        self.getControl(self.CONTROL_LABEL1).setLabel(self.label1)
        self.getControl(self.CONTROL_LABEL2).setLabel(self.label2)
        self.getControl(self.CONTROL_LABEL3).setLabel(self.label3)
        self.getControl(self.buttons).setVisible(True)

    def onClick( self, controlId ):

        self.close()

    def onFocus( self, controlId ):
        pass

    def onAction(self, action):
        print action.getId()
    	if action.getId()==10:
            self.close()

class Progress(xbmcgui.WindowXMLDialog):

    CONTROL_BORDER = 30422
    CONTROL_BOX = 30423
    CONTROL_BEVEL = 30424
    CONTROL_LIST = 30421
    CONTROL_OK = 10

    CONTROL_TITLE = 30451
    CONTROL_LABEL1 = 30452
    CONTROL_LABEL2 = 30453
    CONTROL_LABEL3 = 30454
    CONTROL_BAR = 30457

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.title=""
        self.label1 = ""
        self.label2 = ""
        self.label3 = ""
        self.percent = 0
        self.canceled = False
        self.buttons=0

    def create(self, title="", line1="", line2="", line3=""):
        self.canceled = False
        self.title = title
        self.label1 = line1
        self.label2 = line2
        self.label3 = line3
        self.show()

    def update(self, percent=0, line1="", line2="", line3=""):
        self.percent = percent
        self.label1 = line1
        self.label2 = line2
        self.label3 = line3
        self.updateDisplay()

    def onInit(self):
        self.updateDisplay()

    def updateDisplay(self):
        self.getControl(self.CONTROL_TITLE).setLabel(self.title)
        self.getControl(self.CONTROL_LABEL1).setLabel(self.label1)
        self.getControl(self.CONTROL_LABEL2).setLabel(self.label2)
        self.getControl(self.CONTROL_LABEL3).setLabel(self.label3)
        self.getControl(self.CONTROL_BAR).setWidth(int(float(self.percent)*3.68))

    def iscanceled(self):
        return self.canceled
    
    def onClick(self, controlId):
        print "clicked"
        self.canceled = True

    def onFocus(self, controlId):
        pass

    def onAction(self, action):
        print action.getId()
    	if action.getId()==10:
            self.close()

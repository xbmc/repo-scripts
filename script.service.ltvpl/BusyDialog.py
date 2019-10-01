import xbmc
import xbmcgui
import xbmcaddon
import os
from datetime import datetime, timedelta

from resources.lib.Utilities.DebugPrint import DbgPrint
from util import GETTEXT

__Version__ = "1.0.0"

PROGRESSBARID = 10
WORKING = GETTEXT(30047)

class BusyDialog(xbmcgui.WindowXMLDialog):
    def __new__(cls, addonID):
        return super(BusyDialog, cls).__new__(cls, 'BusyDialog.xml',
                                                  xbmcaddon.Addon(addonID).getAddonInfo('path'))

    def __init__(self, addonID):
        super(BusyDialog, self).__init__()
        self.addonID = addonID

    def onInit(self):
        self.setProperty('working', WORKING)

    def update(self, pct):
        pb = self.getControl(PROGRESSBARID)
        DbgPrint("***progressCtrl: {}->pct:{}".format(pb, pct))
        pb.setPercent(pct)


    def iscanceled(self):
        return False



class BusyDialog2(xbmcgui.WindowXMLDialog):
    def __new__(cls, addonID):
        return super(BusyDialog2, cls).__new__(cls, 'BusyDialog2.xml',
                                                  xbmcaddon.Addon(addonID).getAddonInfo('path'))

    def __init__(self, addonID):
        super(BusyDialog2, self).__init__()
        self.addonID = addonID

    def onInit(self):
        self.setProperty('working', WORKING)

    def update(self, pct):
        pb = self.getControl(PROGRESSBARID)
        DbgPrint("***progressCtrl: {}->pct:{}".format(pb, pct))
        pb.setPercent(pct)


    def iscanceled(self):
        return False

#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import threading
import xbmc, xbmcgui, xbmcaddon

from utils import get_str
from utils import log
from utils import __addon__

__icon__ = __addon__.getAddonInfo("icon")
xbmc.log("Icon = " + str(__icon__))


PIN_LABEL = 201
INSTRUCTION_ID = 202
CANCEL_BUTTON = 203
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92

not_dialog = xbmcgui.Dialog()


def notify(txt="", title="Simkl", icon=__icon__):
    not_dialog.notification(title, txt, icon)


class LoginDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, pin, url, pin_check=None, pin_success=None):
        self.pin = pin
        self.url = url
        self.canceled = False
        self.pin_check = pin_check
        self.success = pin_success

    def threaded(self):
        """ A loop threaded function, so you can do another things meanwhile """
        log("login thread start = {0}".format(self))
        cnt = 0
        while True:
            log("Still waiting... {0}".format(cnt))
            if self.pin_check(self.pin):
                self.success()
                self.close()
                break
            if self.canceled or cnt >= 220:
                notify(get_str(32031))
                break
            cnt += 1
            xbmc.Monitor().waitForAbort(4)

        log("Stop waiting")

    def onInit(self):
        """The function that is loaded on Window init"""
        instruction = self.getControl(INSTRUCTION_ID)
        instruction.setLabel(get_str(32022).format("[COLOR ffffbf00]" + self.url + "[/COLOR]"))
        self.getControl(PIN_LABEL).setLabel(self.pin)
        t = threading.Thread(target=self.threaded)
        t.start()

    def onControl(self, controlID):
        pass

    def onFocus(self, controlID):
        pass

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
            self.canceled = True
            self.close()

    def onClick(self, controlID):
        log("onclick {0}, {1}".format(controlID, self))
        if controlID == CANCEL_BUTTON:
            self.canceled = True
            self.close()

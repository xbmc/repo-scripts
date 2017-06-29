#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import threading
import xbmc, xbmcgui, xbmcaddon
import utils

__addon__ = xbmcaddon.Addon("script.simkl")
from simklapi import api as API
tmp = time.time()

__icon__ = __addon__.getAddonInfo("icon")
def getstr(strid): return __addon__.getLocalizedString(strid)

xbmc.log("Simkl: Icon: "+str(__icon__))

not_dialog = xbmcgui.Dialog()
def notify(txt="Test", title="Simkl", icon=__icon__):
    not_dialog.notification(title, txt, icon)

PIN_LABEL      = 201
INSTRUCTION_ID = 202
CANCEL_BUTTON  = 203
ACTION_PREVIOUS_MENU = 10
ACTION_BACK = 92

#xmlfile = ""
#script  = __addon__.getAddonInfo("path").decode("utf-8")
def login(logged):
    """Change the things that need to be changed. E.g: The settings dialog"""
    __addon__.setSetting("loginbool", str(bool(1)).lower())

class loginDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, pin, url, check_login, log,
        exp=900, inter=5, api=None):
        self.pin = pin
        self.url = url
        self.check_login = check_login
        self.log = log
        self.exp = exp
        self.inter = inter
        self.api = api
        self.waiting = True
        self.canceled = False

    def threaded(self):
        """ A loop threaded function, so you can do another things meanwhile """
        xbmc.log("Simkl: threaded: {0}".format(self))
        cnt = 0
        while self.waiting:
            if cnt % (self.inter+1) == 0 and cnt>1:
                xbmc.log("Simkl: Still waiting... {0}".format(cnt))
                if self.check_login(self.pin, self.log):

                    xbmc.log(str(self.api.USERSETTINGS))
                    notify(getstr(32030).format(self.api.USERSETTINGS["user"]["name"]))
                    self.waiting = False
                    #Now check that the user has done what it has to be done

            cnt += 1
            time.sleep(1)
            if self.canceled or cnt >= self.exp:
                self.waiting = False
                notify(getstr(32031))

        utils.systemUnlockDelay("SimklTrackerRunLogin", 1)
        xbmc.log("Simkl: Stop waiting")
        self.close()

    def onInit(self):
        """The function that is loaded on Window init"""
        instruction = self.getControl(INSTRUCTION_ID)
        instruction.setLabel(
            getstr(32022).format("[COLOR ffffbf00]" + self.url + "[/COLOR]"))
        self.getControl(PIN_LABEL).setLabel(self.pin)
        xbmc.log("Simkl: Visible: {0}".format(self.getProperty("visible")))

        t = threading.Thread(target=self.threaded)
        t.start()

        if API.is_user_logged(): #If user is alredy logged in
            dialog = xbmcgui.Dialog()
            username = API.USERSETTINGS["user"]["name"]
            ret = dialog.yesno("Simkl LogIn Warning", getstr(32032).format(username),
                nolabel=getstr(32034), yeslabel=getstr(32033), autoclose=30000)
            #xbmc.log("Ret: {0}".format(ret))
            xbmc.log("Simkl:ret: {0}".format(ret))
            if ret == 1: pass
            elif ret == 0:
                self.onClick(CANCEL_BUTTON)
            return

    def onControl(self, controlID):
        pass
    def onFocus(self, controlID):
        pass

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_BACK:
            self.canceled = True
            self.close()

    def onClick(self, controlID):
        xbmc.log("Simkl: onclick {0}, {1}".format(controlID, self))
        if controlID == CANCEL_BUTTON:
            self.canceled = True
# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.game.filmwise')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


def os_path_join(dir, file):
    # Check if it ends in a slash
    if dir.endswith("/") or dir.endswith("\\"):
        # Remove the slash character
        dir = dir[:-1]

    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


##############################
# Stores Various Settings
##############################
class Settings():

    @staticmethod
    def getLastViewed():
        return ADDON.getSetting("lastViewedUrl")

    @staticmethod
    def setLastViewed(url):
        ADDON.setSetting("lastViewedUrl", url)

    @staticmethod
    def isSaveUserAnswers():
        return ADDON.getSetting("saveUserAnswers") == 'true'

    @staticmethod
    def isNotifyNewQuiz():
        return ADDON.getSetting("notifyNewQuiz") == 'true'

    @staticmethod
    def isAutoOpenNewQuiz():
        return ADDON.getSetting("autoOpenNewQuiz") == 'true'

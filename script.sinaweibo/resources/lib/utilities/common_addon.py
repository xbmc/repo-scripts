
import xbmc
import xbmcaddon
import xbmcvfs
import os


addon = xbmcaddon.Addon(id='script.sinaweibo')
addon_path = addon.getAddonInfo('path')
addon_userdata = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
addon_name = addon.getAddonInfo('name')

# cache folders

twitter_update_time = int(addon.getSetting("twitter-update-time"))
save_history_during_playback = addon.getSetting("save_history_during_playback")
twitter_history_enabled = addon.getSetting("twitter_history_enabled")

tweet_file = os.path.join(addon_userdata, "twitter.txt")
twitter_history_file = os.path.join(addon_userdata, "twitter_history.txt")
weibo_file = os.path.join(addon_userdata, "weibo.txt")
weibo_history_file = os.path.join(addon_userdata, "weibo_history.txt")

def getskinfolder():
    # if "skin.aeon.nox" in xbmc.getSkinDir(): return "skin.aeon.nox.5"
    # else:
    return "default"


def removeNonAscii(s):
    return "".join(filter(lambda x: ord(x) < 128, s))


def translate(text):
    return addon.getLocalizedString(text).encode('utf-8')

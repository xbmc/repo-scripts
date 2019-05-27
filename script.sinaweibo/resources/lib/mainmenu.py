
import xbmcgui
import xbmcaddon
import xbmc
import sys
import os
import tweets
import weibo
from utilities import tweet
from utilities import sina_tweet
from utilities import ssutils
from utilities.common_addon import *

MAIN_MENU = {
    "weibo": {"label": translate(30006), "icon": os.path.join(addon_path, "resources", "images", "weibo-500.png")},
    "settings": {"label": translate(32007), "icon": os.path.join(addon_path, "resources", "images", "tables.png")},
    "twitter": {"label": translate(32010), "icon": os.path.join(addon_path, "resources", "images", "twitter.png")}
}


class Main(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        items = []
        for menuentry in MAIN_MENU.keys():
            item = xbmcgui.ListItem(MAIN_MENU[menuentry]["label"])
            item.setProperty("thumb", str(MAIN_MENU[menuentry]["icon"]))
            item.setProperty("identifier", str(menuentry))
            items.append(item)
        self.getControl(32500).addItems(items)

    def onClick(self, controlId):
        if controlId == 32500:
            identifier = self.getControl(32500).getSelectedItem().getProperty("identifier")
            if identifier == "weibo":
                self.close()
                weibo.start()
            elif identifier == "settings":
                self.close()
                xbmcaddon.Addon().openSettings()
            elif identifier == "twitter":
                self.close()
                tweets.start()

    def onAction(self, action):
        # exit
        if action.getId() == 92 or action.getId() == 10:
            self.close()
        # contextmenu
        if action.getId() == 117:
            identifier = self.getControl(32500).getSelectedItem().getProperty("identifier")
            if identifier == "twitter":
                twitter_history = tweet.get_twitter_history()
                if twitter_history:
                    twitter_history = list(reversed(twitter_history))
                    choice = xbmcgui.Dialog().select(translate(32076), twitter_history)
                    if choice > -1:
                        self.close()
                        tweets.start(twitterhash=twitter_history[choice])
                else:
                    xbmcgui.Dialog().ok(translate(32000), translate(32075))
            if identifier == "weibo":
                weibo_history = sina_tweet.get_twitter_history()
                if weibo_history:
                    weibo_history = list(reversed(weibo_history))
                    choice = xbmcgui.Dialog().select(translate(32076), weibo_history)
                    if choice > -1:
                        self.close()
                        weibo.start(twitterhash=weibo_history[choice])
                else:
                    xbmcgui.Dialog().ok(translate(32000), translate(32075))


def start():
    main = Main(
        'script-sinaweibo-MainMenu.xml',
        addon_path,
        getskinfolder(),
        '',
    )
    main.doModal()
    del main


import xbmcgui
import xbmc
import datetime
import json
import mainmenu
import os
from resources.lib.utilities import tweet
from resources.lib.utilities import sina_tweet
from resources.lib.utilities.addonfileio import FileIO
from resources.lib.utilities import ssutils
from resources.lib.utilities.common_addon import *


class TwitterDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        self.isRunning = True
        self.hash = kwargs["hash"]
        self.standalone = kwargs["standalone"]
        self.teamObjs = {}

    def onInit(self):
        xbmc.log(msg="weibo center  cycle started", level=xbmc.LOGDEBUG)
        self.getControl(32540).setImage(os.path.join(addon_path, "resources", "images", "weibo_sm.png"))
        self.refresh()
        i = 0
        while self.isRunning:
            if (float(i * 200) / (twitter_update_time * 60 * 1000)).is_integer() and ((i * 200) / (3 * 60 * 1000)) != 0:
                self.getTweets()
            xbmc.sleep(200)
            i += 1
        xbmc.log(msg="[Match Center] Twitter cycle stopped", level=xbmc.LOGDEBUG)

    def getTweets(self):
        self.getControl(32500).setLabel("#" + self.hash)
        self.getControl(32503).setImage(os.path.join(addon_path, "resources", "images", "weibo_sm.png"))
        tweetitems = []
        tweets = sina_tweet.get_uid_tweets(self.hash)
        if tweets:
            for _tweet in tweets:
                #td = ssutils.get_timedelta_string(datetime.datetime.utcnow() - _tweet["date"])
                td = _tweet["date"]
                item = xbmcgui.ListItem(_tweet["text"].replace("\n", ""))
                item.setProperty("profilepic", _tweet["profilepic"])
                item.setProperty("author", "[B]" + "@" + _tweet["author"] + "[/B]")
                item.setProperty("timedelta", td)
                tweetitems.append(item)

        self.getControl(32501).reset()
        self.getControl(32501).addItems(tweetitems)
        if tweetitems:
            self.setFocusId(32501)
        return

    def getSubscriptions(self):
        self.getControl(32500).setLabel("#" + "Subscriptions")
        self.getControl(32503).setImage(os.path.join(addon_path, "resources", "images", "weibo_sm.png"))
        tweetitems = []
        #self.hash = ['1784827665', '2323370715']
        for username in self.hash:
            tweets = sina_tweet.get_uid_tweets(username)
            if tweets:
                for _tweet in tweets:
                    #td = ssutils.get_timedelta_string(datetime.datetime.utcnow() - _tweet["date"])
                    td = _tweet["date"]
                    item = xbmcgui.ListItem(_tweet["text"].replace("\n", ""))
                    item.setProperty("profilepic", _tweet["profilepic"])
                    item.setProperty("author", "[B]" + "@" + _tweet["author"] + "[/B]")
                    item.setProperty("timedelta", td)
                    tweetitems.append(item)

        self.getControl(32501).reset()
        self.getControl(32501).addItems(tweetitems)
        if tweetitems:
            self.setFocusId(32501)
        return

    def reset(self):
        xbmcgui.Dialog().ok(translate(32000), translate(32045))
        if os.path.exists(tweet_file):
            os.remove(tweet_file)
            xbmcgui.Dialog().ok(translate(32000), translate(32045))
        return

    def refresh(self):
        xbmc.executebuiltin("SetProperty(loading-script-sinaweibo-weibo,1,home)")
        if type(self.hash) == type(list()):
            self.getSubscriptions()
        else:
            self.getTweets()
        xbmc.executebuiltin("ClearProperty(loading-script-sinaweibo-weibo,Home)")

    def stopRunning(self):
        self.isRunning = False
        self.close()
        if not self.standalone:
            mainmenu.start()

    def onAction(self, action):
        if action.getId() == 92 or action.getId() == 10:
            self.stopRunning()

    def onClick(self, controlId):
        """
        if controlId == 32501:
            teamid = self.getControl(controlId).getSelectedItem().getProperty("teamid")
            matchhistory.start(teamid)
        elif controlId == 32514:
            self.reset()
        """
        if controlId == 32514:
            self.refresh()


def start(twitterhash=None, standalone=False):
    if not twitterhash:
        userInput = True
        if os.path.exists(tweet_file):
            twitter_data = json.loads(FileIO.fileread(weibo_file))
            twitterhash = twitter_data["hash"]
            twitter_mediafile = twitter_data["file"]
            if twitter_mediafile == xbmc.getInfoLabel('Player.Filenameandpath'):
                userInput = False
    else:
        userInput = False

    if userInput:
        dialog = xbmcgui.Dialog()
        twitterhash = dialog.input(translate(32048), type=xbmcgui.INPUT_NUMERIC)
        if len(twitterhash) > 0:
            # search for the given user's weibo
            twitterhash = twitterhash.replace("#", "")
        else:
            # show the following accounts in settings
            userList = list()
            for i in range(1, 11):
                username = addon.getSetting('UID%d' % i).replace('@', '')
                if len(username) > 0:
                    userList.append(username)
            main = TwitterDialog('script-sinaweibo-Weibo.xml', addon_path, getskinfolder(), '', hash=userList,
                                 standalone=False)
            main.doModal()
            del main

    if twitterhash:
        # Save twitter hashtag
        if twitter_history_enabled == 'true':
            sina_tweet.add_hashtag_to_twitter_history(twitterhash)
        if xbmc.getCondVisibility("Player.HasMedia") and save_history_during_playback == 'true':
            sina_tweet.savecurrenthash(twitterhash)

        main = TwitterDialog('script-sinaweibo-Weibo.xml', addon_path, getskinfolder(), '', hash=twitterhash,
                             standalone=standalone)
        main.doModal()
        del main

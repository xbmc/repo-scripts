
import datetime
import time
import os
import xbmcgui
import xbmc
import json
from twitter import *
from common_addon import *
from addonfileio import FileIO

con_secret = 'h7hSFO1BNKzyB2EabYf7RXXd5'
con_secret_key = 'tVbNWktkILCHu9CcENhXaUnLOrZWhJIHvBNcSEwgaczR8adZwU'
token = '1226187432-3Tn0Euwt604LvNXGsVYWrgBrXa2xboo3UFgbrha'
token_key = 'KccVJ7kUFJhG7uZgJeQNizEbf9Z9spZDhEKGP3b3ogrH2'

t = Twitter(
    auth=OAuth(token, token_key, con_secret, con_secret_key))


def get_tweets(twitter_user):
    return_twitter = []
    tweet_list = t.statuses.user_timeline(screen_name=twitter_user, count=10)
    for tweet in tweet_list:
        return_twitter.append([tweet['text'], tweet['created_at']])
    return return_twitter


def get_hashtag_tweets(twitter_hash):
    return_twitter = []
    tweet_list = t.search.tweets(q=twitter_hash.replace('#', ''), count=20)['statuses']
    for tweet in tweet_list:
        tweet['created_at'] = tweet['created_at'].replace(" +0000", "")
        tweet['date'] = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S %Y")))
        return_twitter.append({"author": tweet['user']['name'],
                               "profilepic": tweet['user']['profile_image_url_https'].replace('_normal', ''),
                               "text": tweet['text'], "date": tweet['date']})
        # xbmc.log(msg=tweet['text'].encode('ascii', 'ignore'), level=xbmc.LOGDEBUG)
    return return_twitter


def get_twitter_history():
    twitter_history = []
    if os.path.exists(twitter_history_file):
        twitter_history = FileIO.fileread(twitter_history_file)
        twitter_history = [hashtag for hashtag in twitter_history.split('\n') if hashtag]
    return twitter_history


def savecurrenthash(_hash):
    media_file = xbmc.getInfoLabel('Player.Filenameandpath')
    media_dict = {"file": media_file, "hash": _hash}
    if not os.path.exists(tweet_file):
        if not os.path.exists(addon_userdata):
            os.mkdir(addon_userdata)
    FileIO.filewrite(tweet_file, json.dumps(media_dict))
    return


def add_hashtag_to_twitter_history(hashtag):
    history = get_twitter_history()
    if hashtag.lower() in history:
        history.remove(hashtag.lower())
    history.append(hashtag.lower())
    return FileIO.filewrite(twitter_history_file, "\n".join(history))


def remove_twitter_hashtag_history():
    if os.path.exists(twitter_history_file):
        os.remove(twitter_history_file)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,3000,%s)" % (
        translate(32000), translate(32071), os.path.join(addon_path, "resources/images/weibo-500.png")))
    else:
        xbmcgui.Dialog().ok(translate(32000), translate(32075))

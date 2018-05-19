
import datetime
import time
import os
import xbmcgui
import xbmc
import json
from twitter import *
from common_addon import *
from addonfileio import FileIO
from pyweibo import APIClient
import traceback
import urllib2
import re


APP_KEY = "3726251905"
APP_SECRET = "6673ae2beb1d836af4f9142802fa4357"
CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html'
client = APIClient(app_key=APP_KEY, app_secret=APP_SECRET, redirect_uri=CALLBACK_URL)
client.set_access_token('2.006ctQRCL2yKEE588ff1b69a06mbKW', 1525805999)


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

def get_username_tweets(weibo_username):
    return_twitter = []
    header = {'accept': 'application/json, text/plain, */*', 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
    url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value={}&containerid=107603{}'
    try:
        u = client.get.users__show(screen_name=weibo_username)
        xbmc.log(msg='!!!!!!!!!!!!!!!!!!!!!!get_username_tweets load finish!!!!!!!!!!!!!!!!', level=xbmc.LOGDEBUG)
        id = u['uid']
        profile_image_url = u['profile_image_url']
        site = url.format(id, id)
        req = urllib2.Request(site, headers=header)
        page = urllib2.urlopen(req)
        json_string = page.read()
        json_obj = json.loads(json_string)
        for i in len(json_obj['data']['cards']):
            dic = json_obj['data']['cards'][i]['mblog']
            html_text = dic['text']
            date = dic['created_at']
            target_string_list = re.findall(r'<([^>]+)', html_text)
            for s in target_string_list:
                target_string = '<' + s + '>'
                html_text = html_text.replace(target_string, '')
                date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d")))
                return_twitter.append({
                    "author": weibo_username,
                    "profilepic": profile_image_url.replace('_normal', ''),
                    "text": html_text, "date": date
                })
    except:
        xbmc.log(traceback.format_exc())
        xbmc.executebuiltin(
            "Notification(%s, %s, %d, %s)" % (weibo_username, 'Weibo User Not Exists', 4000, xbmcaddon.Addon().getAddonInfo('icon')))
    finally:
        return return_twitter


def get_uid_tweets(weibo_uid):
    return_twitter = []
    header = {'accept': 'application/json, text/plain, */*', 'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
    url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value={}&containerid=107603{}'
    try:

        id = weibo_uid
        site = url.format(id, id)
        req = urllib2.Request(site, headers=header)
        page = urllib2.urlopen(req)
        json_string = page.read()
        json_obj = json.loads(json_string)
        xbmc.log(msg='!!!!!!!!!!!!!!!!!!!!!!get_uid_tweets' + weibo_uid + 'load finish!!!!!!!!!!!!!!!!', level=xbmc.LOGDEBUG)
        if json_obj['ok'] is 0:
            xbmc.executebuiltin(
                "Notification(%s, %s, %d, %s)" % (
                weibo_uid, 'Weibo User ID Not Exists', 4000, xbmcaddon.Addon().getAddonInfo('icon')))
        for i in range(0,len(json_obj['data']['cards'])):
            if json_obj['data']['cards'][i]['card_type'] != 9:
                continue
            dic = json_obj['data']['cards'][i]['mblog']
            weibo_username = dic['user']['screen_name']
            profile_image_url = dic['user']['profile_image_url']
            html_text = dic['text']
            mydate = dic['created_at']
            target_string_list = re.findall(r'<([^>]+)', html_text)
            for s in target_string_list:
                target_string = '<' + s + '>'
                html_text = html_text.replace(target_string, '')
            date = datetime.datetime.now()

            try:
                if len(mydate) == 5:
                    date = datetime.datetime.strptime(mydate, "%m-%d")
                    date.replace(year=datetime.datetime.now().year)
                else:
                    date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(mydate, "%Y-%m-%d")))
            except:
                date = datetime.datetime.now()
            return_twitter.append({
                "author": weibo_username,
                "profilepic": profile_image_url.replace('_normal', ''),
                "text": html_text, "date": mydate
            })
    except:
        xbmc.log(traceback.format_exc())
        xbmc.executebuiltin(
            "Notification(%s, %s, %d, %s)" % (weibo_uid, 'Weibo User ID Not Exists', 4000, xbmcaddon.Addon().getAddonInfo('icon')))
    finally:
        return return_twitter


def get_hashtag_tweets(weibo_hash):
    return_twitter = []
    tweet_list = client.statuses__home_timeline()['statuses']
    xbmc.log(msg='******************************sinaweibo load finish****************', level=xbmc.LOGDEBUG)
    for tweet in tweet_list:
        try:
            #xbmc.log(tweet['text'].encode('utf-8'), level=xbmc.LOGDEBUG)
            tweet['created_at'] = tweet['created_at'].replace(" +0800", "")
            tweet['date'] = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S %Y")))
            return_twitter.append({"author": tweet['user']['name'],
                                   "profilepic": tweet['user']['profile_image_url'].replace('_normal', ''),
                                   "text": tweet['text'], "date": tweet['date']})
        except:
            xbmc.log(traceback.format_exc())
    return return_twitter


def get_twitter_history():
    twitter_history = []
    if os.path.exists(weibo_history_file):
        twitter_history = FileIO.fileread(weibo_history_file)
        twitter_history = [hashtag for hashtag in twitter_history.split('\n') if hashtag]
    return twitter_history

weibo_file = os.path.join(addon_userdata, "weibo.txt")
weibo_history = os.path.join(addon_userdata, "weibo_history.txt")

def savecurrenthash(_hash):
    media_file = xbmc.getInfoLabel('Player.Filenameandpath')
    media_dict = {"file": media_file, "hash": _hash}
    if not os.path.exists(weibo_file):
        if not os.path.exists(addon_userdata):
            os.mkdir(addon_userdata)
    FileIO.filewrite(weibo_file, json.dumps(media_dict))
    return


def add_hashtag_to_twitter_history(hashtag):
    history = get_twitter_history()
    if hashtag.lower() in history:
        history.remove(hashtag.lower())
    history.append(hashtag.lower())
    return FileIO.filewrite(weibo_history_file, "\n".join(history))


def remove_twitter_hashtag_history():
    if os.path.exists(weibo_history_file):
        os.remove(weibo_history_file)
        xbmc.executebuiltin("XBMC.Notification(%s,%s,3000,%s)" % (
        translate(32000), translate(32071), os.path.join(addon_path, "icon.png")))
    else:
        xbmcgui.Dialog().ok(translate(32000), translate(32075))

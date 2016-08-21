# -*- coding: utf-8 -*-
'''
    script.matchcenter - Football information for Kodi
    A program addon that can be mapped to a key on your remote to display football information.
    Livescores, Event details, Line-ups, League tables, next and previous matches by team. Follow what
    others are saying about the match in twitter.
    Copyright (C) 2016 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import datetime
import time
from twitter import *

con_secret='h7hSFO1BNKzyB2EabYf7RXXd5'
con_secret_key='tVbNWktkILCHu9CcENhXaUnLOrZWhJIHvBNcSEwgaczR8adZwU'
token='1226187432-3Tn0Euwt604LvNXGsVYWrgBrXa2xboo3UFgbrha'
token_key='KccVJ7kUFJhG7uZgJeQNizEbf9Z9spZDhEKGP3b3ogrH2'

t = Twitter(
    auth=OAuth(token, token_key, con_secret, con_secret_key))

def get_tweets(twitter_user):
    return_twitter = []
    tweet_list = t.statuses.user_timeline(screen_name=twitter_user,count=10)
    for tweet in tweet_list:
        return_twitter.append([tweet['text'],tweet['created_at']])
    return return_twitter
    
def get_hashtag_tweets(twitter_hash):
    return_twitter = []
    tweet_list = t.search.tweets(q=twitter_hash.replace('#',''),count=20)['statuses']
    for tweet in tweet_list:
        tweet['created_at'] = tweet['created_at'].replace(" +0000","")
        tweet['date'] = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet['created_at'], "%a %b %d %H:%M:%S %Y")))
        return_twitter.append({"author":tweet['user']['name'],"profilepic":tweet['user']['profile_image_url_https'].replace('_normal',''),"text":tweet['text'],"date":tweet['date']})
    return return_twitter

#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2010 analogue@yahoo.com
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import twitter

from mythbox.bus import Event

twitterApi = twitter.Api()


class FeedHose(object):

    def __init__(self, settings, bus):
        self.settings = settings
        bus.register(self)
        self.initFeeds()
        
    def initFeeds(self):
        self.feeds = []
        twits = self.settings.get('feeds_twitter').split(',')
        for twit in twits:
            self.feeds.append(TwitterFeed(twit))
        
    def getLatestEntries(self):
        entries = []
        for feed in self.feeds[:]:
            entries.extend(feed.getEntries())
        entries.sort(key=lambda e: e.when, reverse=True)
        return entries[:10]

    def onEvent(self, event):
        if event['id'] == Event.SETTING_CHANGED and event['tag'] == 'feeds_twitter':
            self.initFeeds()
            

class FeedEntry(object):
    
    def __init__(self, username=None, text=None, when=None):
        self.username = username
        self.text = text
        self.when = when
    
    def __repr__(self):
        return "%s {user = %s, when = %s, text = %s}" % (
            type(self).__name__,                                                  
            self.username,
            self.when,
            self.text)


class TwitterFeed(object):

    def __init__(self, user, api=twitterApi):
        self.user = user
        self.api = twitterApi
        
    def getEntries(self):
        #  The Status structure exposes the following properties:
        #    status.created_at
        #    status.created_at_in_seconds # read only
        #    status.favorited
        #    status.in_reply_to_screen_name
        #    status.in_reply_to_user_id
        #    status.in_reply_to_status_id
        #    status.truncated
        #    status.source
        #    status.id
        #    status.text
        #    status.relative_created_at # read only
        #    status.user
        
        entries = []
        tweets = self.api.GetUserTimeline(user=self.user, count=3)
        for tweet in tweets:
            entries.append(FeedEntry(tweet.user.screen_name, tweet.text, tweet.created_at_in_seconds))
        return entries
    

class RssFeed(object):
    pass

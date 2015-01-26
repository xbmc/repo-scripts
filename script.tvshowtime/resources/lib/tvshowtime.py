#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cookielib
import re
import urllib, urllib2
import json

request_uri = "https://api.tvshowtime.com/v1/"

class FindEpisode(object):
    def __init__(self, token, filename):
        self.token = token
        self.filename = filename
        self.action = 'episode?access_token=%s&filename=%s' % (self.token, self.filename)

        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
           urllib2.HTTPRedirectHandler(),
           urllib2.HTTPHandler(debuglevel=0),
           urllib2.HTTPSHandler(debuglevel=0),
           urllib2.HTTPCookieProcessor(self.cj)
        )

        self.opener.addheaders = [
            ('User-agent', 'Lynx/2.8.1pre.9 libwww-FM/2.14')
        ]

        self.opener.get_method = lambda: 'GET'
        
        request_url = "%s%s" % (request_uri, self.action)
        try:
            response = self.opener.open(request_url, None)
            data = json.loads(''.join(response.readlines()))
        except:
            data = None
        
        if (data is None) or (data['result'] == "KO"):
           self.is_found = False
        else:
           self.is_found = True
           self.resultdata = data['result']
           self.showname = data['episode']['show']['name']
           self.episodename = data['episode']['name']
           self.season_number = data['episode']['season_number']
           self.number = data['episode']['number']

class MarkAsWatched(object):
    def __init__(self, token, filename, facebook=0, twitter=0):
        self.token = token
        self.filename = filename
        self.facebook = facebook
        self.twitter = twitter
        self.action = 'checkin'
        request_data = urllib.urlencode({
            'access_token' : self.token,
            'filename' : self.filename,
            'publish_on_ticker' : self.facebook,
            'publish_on_twitter' : self.twitter
            })
        
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', 'Lynx/2.8.1pre.9 libwww-FM/2.14')
        ]
                           
        self.opener.get_method = lambda: 'POST'
             
        request_url = "%s%s" % (request_uri, self.action)
        try:
            response = self.opener.open(request_url, request_data)
            data = json.loads(''.join(response.readlines()))
        except:
            data = None
        
        if (data is None) or (data['result'] == "KO"):
           self.is_marked = False
        else:
           self.is_marked = True
            
class GetUserInformations(object):
    def __init__(self, token):
        self.token = token
        self.action = 'user?access_token=%s' % self.token
        
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', 'Lynx/2.8.1pre.9 libwww-FM/2.14')
        ]
             
        self.opener.get_method = lambda: 'GET'
        
        request_url = "%s%s" % (request_uri, self.action)
        try:
            response = self.opener.open(request_url, None)
            data = json.loads(''.join(response.readlines()))
        except:
            data = None
        
        if (data is None) or (data['result'] == "KO"):
           self.is_connected = False
        else:
           self.is_connected = True
           self.resultdata = data['result']
           self.username = data['user']['name']


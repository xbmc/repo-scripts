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
           
class IsChecked(object):
    def __init__(self, token, filename):
        self.token = token
        self.filename = filename
        self.action = 'checkin?access_token=%s&filename=%s' % (self.token, self.filename)

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
           self.is_watched = data['code']

class MarkAsWatched(object):
    def __init__(self, token, filename, facebook=0, twitter=0):
        self.token = token
        self.filename = filename
        self.facebook = facebook
        if self.facebook == True: self.facebook = 1
        else: self.facebook = 0
        self.twitter = twitter
        if self.twitter == True: self.twitter = 1
        else: self.twitter = 0
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
           
class MarkAsUnWatched(object):
    def __init__(self, token, filename):
        self.token = token
        self.filename = filename
        self.action = 'checkout'
        request_data = urllib.urlencode({
            'access_token' : self.token,
            'filename' : self.filename
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
           self.is_unmarked = False
        else:
           self.is_unmarked = True
            
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
           self.is_authenticated = False
        else:
           self.is_authenticated = True
           self.username = data['user']['name']
           
class GetCode(object):
    def __init__(self):
        self.client_id = '845mHJx5-CxI8dSlStHB'
        self.action = 'oauth/device/code'
        request_data = urllib.urlencode({
            'client_id' : self.client_id
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
           self.is_code = False
        else:
           self.is_code = True
           self.device_code = data['device_code']
           self.user_code = data['user_code']
           self.verification_url = data['verification_url']
           self.expires_in = data['expires_in']
           self.interval = data['interval']

class Authorize(object):
    def __init__(self, code):
        self.client_id = '845mHJx5-CxI8dSlStHB'
        self.client_secret = 'lvN6LZOZkUAH8aa_WAbvAJ4AXGcSo7irZyAPdRQj'
        self.action = 'oauth/access_token'
        self.code = code
        request_data = urllib.urlencode({
            'client_id' : self.client_id,
            'client_secret' : self.client_secret,
            'code' : self.code
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
           self.is_authorized = False
           self.message = data['message']
        else:
           self.is_authorized = True
           self.access_token = data['access_token']

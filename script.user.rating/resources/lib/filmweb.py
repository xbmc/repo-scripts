# -*- coding: utf-8 -*-

import xbmcaddon
import xbmc
import xbmcgui
import os
import urllib
import urllib2
import json
import re
import hashlib
import datetime
from cookielib import CookieJar

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__lang__                = __addon__.getLocalizedString

import debug

API_URL         = 'https://ssl.filmweb.pl/api'
API_KEY         = 'qjcGhW2JnvGT9dfCt3uT_jozR3s'
API_ID          = 'android'
API_VER         = '2.2'

class FILMWEB:
    def __init__(self, master):
        self.login = __addon__.getSetting('loginFILMWEB') if master is True else __addon__.getSetting('loginFILMWEBsec')
        self.passwd  = __addon__.getSetting('passFILMWEB') if master is True else __addon__.getSetting('passFILMWEBsec')
        
        cj = CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        
    def sendRating(self, items):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'FILMWEB')
            return
        
        item_count = len(items)
        item_added = 0
        bar = xbmcgui.DialogProgress()
        bar.create(__addonname__, '')
    
        for item in items:
            # bar
            item_added += 1
            p = int((float(100) / float(item_count)) * float(item_added))
            bar.update(p, str(item_added) + ' / ' + str(item_count) + ' - ' + item['title'])
            
            # search id
            if item['mType'] == 'movie':
                id = self.searchMovieID(item)
                self.prepareRequest(id, item['new_rating'])
            
            if bar.iscanceled():
                bar.close()
                return
                
        bar.close()
        
        debug.debug('Rate sended to Filmweb')
        debug.notify(self.login + ' - ' + __lang__(32101), False, 'Filmweb')
        
    def prepareRequest(self, id, rating):
        if id == 0:
            debug.debug('No filmweb id found')
            debug.notify(__lang__(32102), True, 'FILMWEB')
            return
        
        # send rating
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        if rating > 0:
            method = 'addUserFilmVote [[' + str(id) + ',' + str(rating) + ',"",0]]\nupdateUserFilmVoteDate [' + str(id) + ', ' + date + ']\n'.encode('string_escape')
        else:
            method = 'removeUserFilmVote [' + str(id) + ']\n'.encode('string_escape')
        
        ret = self.sendRequest(method, 'POST')
        
        if ret is not False and re.search('^err', ret) is None:
            debug.debug('Rate sended to FILMWEB')
            debug.notify(self.login + ' - ' + __lang__(32101), False, 'FILMWEB')
        
    def getRated(self, type):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'TMDB')
            return
        
        rated = {}
        ret = self.sendRequest('getUserFilmVotes [null, null]\n'.encode('string_escape'), 'GET')
        matches = re.findall('\[([0-9]+),[^,]+,([0-9]+),', ret)
        if len(matches) > 0:
            for m in matches:
                rated[m[0]] = int(m[1])
                
        # transform tmdb ids to KODI DB ids
        kodiID = {}
        if 'movie' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "imdbnumber", "art", "trailer"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'movies' in jsonGet['result']:
                for m in jsonGet['result']['movies']:
                    patterns = [
                        'fwcdn.pl/po/[^/]+/[^/]+/([0-9]+)/',
                        'fwcdn.pl/ph/[^/]+/[^/]+/([0-9]+)/',
                        'http://mm.filmweb.pl/([0-9]+)/'
                    ]
                    for pattern in patterns:
                        filmweb_search = re.search(pattern, urllib.unquote(str(m)))
                        if filmweb_search is not None:
                            filmweb_id = filmweb_search.group(1)
                            if filmweb_id in rated.keys():
                                kodiID[m['movieid']] = {'title': m['title'], 'rating': rated[filmweb_id]}
                                break
        return kodiID
        
    def searchMovieID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": ' + str(item['dbID']) + ', "properties": ["file", "art", "trailer"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        
        result = re.findall('fwcdn.pl/po/[^/]+/[^/]+/([0-9]+)/', urllib.unquote(str(jsonGetResponse)))
        if len(result) > 0:
            return result[0]
            
        result = re.findall('fwcdn.pl/ph/[^/]+/[^/]+/([0-9]+)/', urllib.unquote(str(jsonGetResponse)))
        if len(result) > 0:
            return result[0]
                
        result = re.findall('http://mm.filmweb.pl/([0-9]+)/', urllib.unquote(str(jsonGetResponse)))
        if len(result) > 0:
            return result[0]
        
        filePath, fileExt = os.path.splitext(jsonGetResponse['result']['moviedetails']['file'])
        fileNfo = filePath + '.nfo'
        
        if os.path.isfile(fileNfo):
        
            file = open(fileNfo, 'r')
            file_data = file.read()
            file.close()
            
            result = re.findall('fwcdn.pl/po/[^/]+/[^/]+/([0-9]+)/', file_data)
            if len(result) > 0:
                return result[0]
            
            result = re.findall('fwcdn.pl/ph/[^/]+/[^/]+/([0-9]+)/', file_data)
            if len(result) > 0:
                return result[0]
                
            result = re.findall('<trailer>http://mm.filmweb.pl/([0-9]+)/', file_data)
            if len(result) > 0:
                return result[0]
                
            result = re.findall('http://www.filmweb.pl/Film?id=([0-9]+)', file_data)
            if len(result) > 0:
                return result[0]
                
        return 0
    
    def tryLogin(self):
        method = 'login [' + self.login + ',' + self.passwd + ',1]\n'.encode('string_escape')
        ret = self.sendRequest(method, 'POST')
        if re.search('^err', ret) is not None:
            return False
        return True
    
    def sendRequest(self, method, http_method, get={}, post={}):
        
        # prepare values
        signature = '1.0,' + hashlib.md5(method + API_ID + API_KEY).hexdigest()
        
        data = { 'methods': method, 'signature': signature, 'appId': API_ID, 'version': API_VER }
        data = urllib.urlencode(data)
        
        # send request
        try:
            if 'GET' in http_method:
                response = self.opener.open(API_URL + '?' + data)
            else:
                response = self.opener.open(API_URL, data)
        
        except HTTPError as er:
            debug.debug('[ERROR ' + str(er.code) + ']: ' + er.read())
            return False
        html = response.read()
        debug.debug('Request: ' + html)
        
        return html
    
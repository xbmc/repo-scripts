# -*- coding: utf-8 -*-

import xbmcaddon
import xbmc
import xbmcvfs
import xbmcgui
import os
import urllib
import httplib
import json
import re

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__lang__                = __addon__.getLocalizedString
__datapath__            = xbmc.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/') + '/'

import debug

API_KEY     = '1009b5cde25c7b0692d51a7db6e49cbd'
API_URL     = 'https://api.themoviedb.org/3/'
API_HOST    = 'api.themoviedb.org'

class TMDB:
    def __init__(self, master):
        self.login = __addon__.getSetting('loginTMDB') if master is True else __addon__.getSetting('loginTMDBsec')
        self.passwd  = __addon__.getSetting('passTMDB') if master is True else __addon__.getSetting('passTMDBsec')
        
        # load user data
        self.loadUSERdata()
        
    def sendRating(self, items):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'TMDB')
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
            
            # search id and send rate
            if item['mType'] == 'movie':
                id = self.searchMovieID(item)
                ret = self.prepareRequest(id, 'movie/' + str(id) + '/rating', item['new_rating'])
                if ret is False:
                    bar.close()
                    return False
                    
            if item['mType'] == 'tvshow':
                id = self.searchTVshowID(item)
                ret = self.prepareRequest(id, 'tv/' + str(id) + '/rating', item['new_rating'])
                if ret is False:
                    bar.close()
                    return False
                    
            if item['mType'] == 'episode':
                episodeData = self.searchEpisodeID(item)
                tvshowid = self.searchTVshowID({'dbID': str(episodeData['tvshowid'])})
                ret = self.prepareRequest(tvshowid, 'tv/' + str(tvshowid) + '/season/' + str(episodeData['season']) + '/episode/' + str(episodeData['episode']) + '/rating', item['new_rating'])
                if ret is False:
                    bar.close()
                    return False
            
            if bar.iscanceled():
                bar.close()
                return
                
        bar.close()
        
        debug.debug('Rate sended to TMDB')
        debug.notify(self.login + ' - ' + __lang__(32101), False, 'TMDB')
        
    def prepareRequest(self, id, method, rating):
        if id == 0:
            debug.debug('No tmdb/imdb id found')
            debug.notify(__lang__(32102), True, 'TMDB')
            return
        
        # send rating
        if rating > 0:
            ret = self.sendRequest(method, 'POST', {'session_id': self.session_id}, {'value': rating})
        else:
            ret = self.sendRequest(method, 'DELETE', {'session_id': self.session_id})
        
        return ret
    
    def getRated(self, type):
        # check login
        if self.tryLogin() is False:
            debug.notify(self.login + ' - ' + __lang__(32110), True, 'TMDB')
            return
        
        if 'movie' in type:
            method = 'movies'
        if 'tvshow' in type:
            method = 'tv'
        if 'episode' in type:
            method = 'tv/episodes'
        
        # read all pages from API
        page = 1
        rated = {}
        while True:
            ret = self.sendRequest('account/' + self.account + '/rated/' + method, 'GET', {'session_id': self.session_id, 'page': page})
            if ret is False or 'total_pages' not in ret or 'page' not in ret or 'results' not in ret:
                return False
                
            for item in ret['results']:
                rating = int(round(float(item['rating'])))
                if rating > 0:
                    if 'movie' in type:
                        # get external source
                        ext = self.sendRequest('movie/' + str(item['id']), 'GET', {'session_id': self.session_id})
                        if 'imdb_id' in ext:
                            rated[str(ext['imdb_id'])] = rating
                    if 'tvshow' in type:
                        rated[str(item['id'])] = rating
                    if 'episode' in type:
                        if str(item['show_id']) in rated.keys():
                            rated[str(item['show_id'])].append({'season': item['season_number'], 'episode': item['episode_number'], 'rating': rating})
                        else:
                            rated[str(item['show_id'])] = [{'season': item['season_number'], 'episode': item['episode_number'], 'rating': rating}]
                        
            if page >= ret['total_pages']:
                break
            page = ret['page'] + 1
            
        # transform tmdb ids to KODI DB ids
        kodiID = {}
        if 'movie' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'movies' in jsonGet['result']:
                for m in jsonGet['result']['movies']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        kodiID[m['movieid']] = {'title': m['title'], 'rating': rated[m['imdbnumber']]}
        
        if 'tvshow' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        kodiID[m['tvshowid']] = {'title': m['title'], 'rating': rated[m['imdbnumber']]}
                        
        if 'episode' in type:
            # KODI don't have site IDs for episodes
            # To get KODI IDs we must get TVshow ID and sseason and episode enum
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber", "art"]}, "id": 1}')
            jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
            if 'result' in jsonGet and 'tvshows' in jsonGet['result']:
                for m in jsonGet['result']['tvshows']:
                    tmdb_search = re.search('tmdb', str(m))
                    if tmdb_search is not None and m['imdbnumber'] in rated.keys():
                        tvshowid = str(m['tvshowid'])
                        
                        # for each tvshow that have rated episode get episodes list
                        jsonGetE = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": ' + tvshowid + ', "properties": ["title", "episode", "season"]}, "id": 1}')
                        jsonGetE = json.loads(unicode(jsonGetE, 'utf-8', errors='ignore'))
                        if 'result' in jsonGetE and 'episodes' in jsonGetE['result']:
                            for epi in jsonGetE['result']['episodes']:
                                
                                # for each episode check it exist in rated table
                                if m['imdbnumber'] in rated.keys():
                                    for r in rated[m['imdbnumber']]:
                                        if epi['season'] == r['season'] and epi['episode'] == r['episode']:
                                            kodiID[epi['episodeid']] = {'title': m['title'] + ' - ' + epi['title'], 'rating': r['rating']}
        return kodiID
    
    def searchMovieID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieDetails", "params": {"movieid": ' + str(item['dbID']) + ', "properties": ["imdbnumber"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        debug.debug('searchMovieID: ' + str(jsonGetResponse))
        if 'result' in jsonGetResponse and 'moviedetails' in jsonGetResponse['result'] and 'imdbnumber' in jsonGetResponse['result']['moviedetails'] and jsonGetResponse['result']['moviedetails']['imdbnumber'][:2] == 'tt':
            id = jsonGetResponse['result']['moviedetails']['imdbnumber']
        else:
            id = 0
        return id
        
    def searchTVshowID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(item['dbID']) + ', "properties": ["imdbnumber", "art"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        debug.debug('searchTVshowID: ' + str(jsonGetResponse))
        tmdb_search = re.search('tmdb', str(jsonGetResponse))
        if tmdb_search is not None and 'result' in jsonGetResponse and 'tvshowdetails' in jsonGetResponse['result'] and 'imdbnumber' in jsonGetResponse['result']['tvshowdetails']:
            id = jsonGetResponse['result']['tvshowdetails']['imdbnumber']
        else:
            id = 0
        return id
    
    def searchEpisodeID(self, item):
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodeDetails", "params": {"episodeid": ' + str(item['dbID']) + ', "properties": ["season", "episode", "tvshowid"]}, "id": 1}')
        jsonGet = unicode(jsonGet, 'utf-8', errors='ignore')
        jsonGetResponse = json.loads(jsonGet)
        debug.debug('searchEpisodeID: ' + str(jsonGetResponse))
        if 'result' in jsonGetResponse and 'episodedetails' in jsonGetResponse['result'] and 'tvshowid' in jsonGetResponse['result']['episodedetails']:
            epiosdeData = jsonGetResponse['result']['episodedetails']
        else:
            episodeData = {}
        return epiosdeData
        
    def tryLogin(self):
        #get account id
        ret = self.sendRequest('account', 'GET', {'session_id': self.session_id})
        if ret is not False and 'id' in ret:
            self.account = str(ret['id'])
            debug.debug('TMDB Session exist. No logging needed')
            return True
        
        # login if session not exist
        # get new token
        ret = self.sendRequest('authentication/token/new', 'GET')
        if ret is not False and 'success' in ret:
            self.request_token = ret['request_token']
        else:
            return False
            
        # validate token
        ret = self.sendRequest('authentication/token/validate_with_login', 'GET', {'request_token': self.request_token, 'username': self.login, 'password': self.passwd})
        if ret is False:
            return False
        
        #get session id
        ret = self.sendRequest('authentication/session/new', 'GET', {'request_token': self.request_token})
        if ret is not False and 'success' in ret:
            self.session_id = ret['session_id']
        else:
            return False
        
        #get account id
        ret = self.sendRequest('account', 'GET', {'session_id': self.session_id})
        if ret is not False and 'id' in ret:
            self.account = str(ret['id'])
            self.saveUSERdata()
        else:
            return False
       
        return True
    
    def sendRequest(self, method, http_method, get={}, post={}):
        # prepare values
        get['api_key'] = API_KEY
        
        get = urllib.urlencode(get)
        post = urllib.urlencode(post)
        
        # send request
        req = httplib.HTTPSConnection(API_HOST)
        req.request(http_method, API_URL + method + '?' + get, post)
        response = req.getresponse()
        html = response.read()
        debug.debug('Request: ' + html)
        if response.status != 200 and response.status != 201:
            debug.debug('[ERROR ' + str(response.status) + ']: ' + html)
            return False
        
        # get json
        try:
            output = unicode(html, 'utf-8', errors='ignore')
            output = json.loads(output)
        except Exception as Error:
            debug.debug('[GET JSON ERROR]: ' + str(Error))
            return {}
            
        return output
    
    def loadUSERdata(self):
        if xbmcvfs.exists(__datapath__ + 'tmdb'):
            file = open(__datapath__ + 'tmdb', 'r')
            self.accounts_data = json.loads(file.read())
            file.close()
        else:
            self.accounts_data = {}
        if self.login in self.accounts_data.keys():
            self.session_id = self.accounts_data[self.login]
        else:
            self.session_id = ''
                
    def saveUSERdata(self):
        self.accounts_data[self.login] = self.session_id
        file = open(__datapath__ + 'tmdb', 'w')
        file.write(json.dumps(self.accounts_data))
        file.close()
    
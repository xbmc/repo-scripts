# -*- coding: utf-8 -*-

import xbmcgui
import xbmcaddon
import xbmc
import os
import json

__addon__               = xbmcaddon.Addon()
__addon_id__            = __addon__.getAddonInfo('id')
__addonname__           = __addon__.getAddonInfo('name')
__lang__                = __addon__.getLocalizedString
__datapath__            = xbmc.translatePath(os.path.join('special://profile/addon_data/', __addon_id__)).replace('\\', '/') + '/'

import debug
import dialog

__LANGTYPE__ = {'movies': __lang__(32122), 'tvshows': __lang__(32123), 'tvshows': __lang__(32124)}

class SYNC:
    
    def start(self):
    
        ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32143)}, buttons=['TMDb', 'TVDb', 'Filmweb'], list=10050)
        # TMDB
        if ret == 0:
            ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32120)}, buttons=['KODI => TMDb', 'TMDb => KODI'], list=10050)
            if ret == 0:
                ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32121)}, buttons=[__lang__(32122), __lang__(32123), __lang__(32124)], list=10050)
                if ret == 0:
                    self.syncKODItoSITE('movie', 'tmdb')
                if ret == 1:
                    self.syncKODItoSITE('tvshow', 'tmdb')
                if ret == 2:
                    self.syncKODItoSITE('episode', 'tmdb')
                return
            
            if ret == 1:
                ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32121)}, buttons=[__lang__(32122), __lang__(32123), __lang__(32124)], list=10050)
                if ret == 0:
                    self.syncSITEtoKODI('movie', 'tmdb')
                if ret == 1:
                    self.syncSITEtoKODI('tvshow', 'tmdb')
                if ret == 2:
                    self.syncSITEtoKODI('episode', 'tmdb')
                return
            return
        
        # TVDB
        if ret == 1:
            ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32120)}, buttons=['KODI => TVDB', 'TVDB => KODI'], list=10050)
            if ret == 0:
                ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32121)}, buttons=[__lang__(32123), __lang__(32124)], list=10050)
                if ret == 0:
                    self.syncKODItoSITE('tvshow', 'tvdb')
                if ret == 1:
                    self.syncKODItoSITE('episode', 'tvdb')
                return
                
            if ret == 1:
                ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32121)}, buttons=[__lang__(32123), __lang__(32124)], list=10050)
                if ret == 0:
                    self.syncSITEtoKODI('tvshow', 'tvdb')
                if ret == 1:
                    self.syncSITEtoKODI('episode', 'tvdb')
                return
            return
            
        # Filmweb
        if ret == 2:
            ret = dialog.DIALOG().start('script-user-rating-menu.xml', labels={10060: __lang__(32120)}, buttons=['KODI => Filmweb', 'Filmweb => KODI'], list=10050)
            if ret == 0:
                self.syncKODItoSITE('movie', 'filmweb')
            if ret == 1:
                self.syncSITEtoKODI('movie', 'filmweb')
            return
        return
    
    def syncKODItoSITE(self, type, site):
        
        if 'tmdb' in site:
            import tmdb
            siteClass = tmdb.TMDB(True)
            siteLabel = 'TMDB'
        if 'tvdb' in site:
            import tvdb
            siteClass = tvdb.TVDB(True)
            siteLabel = 'TVDB'
        if 'filmweb' in site:
            import filmweb
            siteClass = filmweb.FILMWEB(True)
            siteLabel = 'FILMWEB'
        
        # set bar
        bar = xbmcgui.DialogProgress()
        bar.create(__addonname__, '')
        bar.update(50, __lang__(32125) + ' ' + __LANGTYPE__[type + 's'] + ' ' + __lang__(32127) + ' KODI')
        
        # get rated from KODI
        KODIrated = self.getRatedKODI(type)
        debug.debug('KODIrated' + type.title() + 's: ' + str(KODIrated))
        
        if len(KODIrated) == 0:
            bar.close()
            debug.notify(__lang__(32126) + ' ' + __LANGTYPE__[type + 's'])
            return
        
        bar.update(100, __lang__(32125) + ' ' + __LANGTYPE__[type + 's'] + ' ' + __lang__(32127) + ' ' + siteLabel)
        
        # get rated from Site
        SITErated = siteClass.getRated(type)
        debug.debug(siteLabel + 'rated' + type.title() + 's: ' + str(SITErated))
        
        bar.close()
        
        # try find siteIDs for KODIrated
        KODIratedWithIDExistRate = {}
        KODIratedWithIDNotxistRate = {}
        KODIratedWithoutID = {}
        
        for key, item in KODIrated.items():
            if 'movie' in type:
                siteID = siteClass.searchMovieID(item)
            if 'tvshow' in type:
                siteID = siteClass.searchTVshowID(item)
            if 'episode' in type:
                siteID = siteClass.searchEpisodeID(item)
                if len(siteID) == 0: siteID = 0
            
            if siteID == 0:
                KODIratedWithoutID[key] = item
            else:
                if key in SITErated.keys():
                    KODIratedWithIDExistRate[key] = item
                else:
                    KODIratedWithIDNotxistRate[key] = item
                    
        debug.debug('KODIrated' + type.title() + 'sWithoutID: ' + str(KODIratedWithoutID))
        debug.debug('KODIrated' + type.title() + 'sWithIDExistRate: ' + str(KODIratedWithIDExistRate))
        debug.debug('KODIrated' + type.title() + 'sWithIDNotexistRate: ' + str(KODIratedWithIDNotxistRate))
        
        # prepare labels with siteID and not exist rate
        labels_title = __lang__(32128) + ' (' + str(len(KODIratedWithIDExistRate) + len(KODIratedWithIDNotxistRate)) + ') ' + __lang__(32129) + ' ' + siteLabel + ' ' + __lang__(32130) + ':\r\n'
        labels_title = labels_title + '    ' + __lang__(32128) + ' (' + str(len(KODIratedWithIDNotxistRate)) + ') ' + __lang__(32131) + ':\r\n'
        for id, data in KODIratedWithIDNotxistRate.items():
            labels_title = labels_title + '[COLOR=green]    >>[/COLOR] '
            labels_title = labels_title + data['title'] + ' (' + __lang__(32132) + ': ' + str(data['new_rating']) + ')\r\n'
        labels_title = labels_title + '\r\n'
        
        # prepare labels with siteID and exist rate
        labels_title = labels_title + '    ' + __lang__(32128) + ' (' + str(len(KODIratedWithIDExistRate)) + ') ' + __lang__(32133) + ':\r\n'
        for id, data in KODIratedWithIDExistRate.items():   
            labels_title = labels_title + '[COLOR=green]    >>[/COLOR] '
            color = 'green' if data['new_rating'] == SITErated[id]['rating'] else "red"
            labels_title = labels_title + data['title'] + ' (' + __lang__(32132) + ': ' + str(data['new_rating']) + ' - ' + __lang__(32134) + ': [COLOR=' + color + ']' + str(SITErated[id]['rating']) + '[/COLOR])\r\n'
        labels_title = labels_title + '\r\n'
            
        # prepare labels without siteID
        labels_title = labels_title + __lang__(32128) + ' (' + str(len(KODIratedWithoutID)) + ') ' + __lang__(32135) + ' ' + siteLabel + ' ' + __lang__(32136) + ':\r\n'
        for id, data in KODIratedWithoutID.items():
            labels_title = labels_title + '[COLOR=red]>>[/COLOR] '
            labels_title = labels_title + data['title'] + ' (' + __lang__(32132) + ': ' + str(data['new_rating']) + ')\r\n'
                
        ret = dialog.DIALOG().start('script-user-rating-text.xml', labels={10062: __lang__(32137) + ' KODI ' + __lang__(32142) + ' ' + siteLabel}, textboxes={10063: labels_title}, buttons=[__lang__(32138), __lang__(32139), __lang__(32140)], list=10050)
        
        toUpdate = []
        if ret == 0:
            siteClass.sendRating(KODIratedWithIDExistRate.values() + KODIratedWithIDNotxistRate.values())
        if ret == 1:
            siteClass.sendRating(KODIratedWithIDNotxistRate.values())
        if ret == 2:
            return
    
    def syncSITEtoKODI(self, type, site):
        
        if 'tmdb' in site:
            import tmdb
            siteClass = tmdb.TMDB(True)
            siteLabel = 'TMDB'
        if 'tvdb' in site:
            import tvdb
            siteClass = tvdb.TVDB(True)
            siteLabel = 'TVDB'
        if 'filmweb' in site:
            import filmweb
            siteClass = filmweb.FILMWEB(True)
            siteLabel = 'FILMWEB'
            
        # set bar
        bar = xbmcgui.DialogProgress()
        bar.create(__addonname__, '')
        bar.update(50, __lang__(32125) + ' ' + __LANGTYPE__[type + 's'] + ' ' + __lang__(32127) + ' ' + siteLabel)
        
        # get rated from SITE
        SITErated = siteClass.getRated(type)
        debug.debug(siteLabel + 'rated' + type.title() + 's: ' + str(SITErated))
        if SITErated is False:
            bar.close()
            debug.notify(__lang__(32141))
            return
        
        if len(SITErated) == 0:
            bar.close()
            debug.notify(__lang__(32126) + ' ' + __LANGTYPE__[type + 's'])
            return
        
        if bar.iscanceled():
            bar.close()
            return
        
        bar.update(100, __lang__(32125) + ' ' + __LANGTYPE__[type + 's'] + ' ' + __lang__(32127) + ' KODI')
        
        # get rated from KODI
        KODIrated = self.getRatedKODI(type)
        debug.debug('KODIrated' + type.title() + 's: ' + str(KODIrated))
        
        bar.close()
        
        # check for existed ratings
        SITEratedExistRate = {}
        SITEratedNotexistRate = {}
        for key, item in SITErated.items():
            if key in KODIrated.keys():
                SITEratedExistRate[key] = item
            else:
                SITEratedNotexistRate[key] = item
                
        # prepare labels for not existed ratings
        labels_title = __lang__(32128) + ' (' +  str(len(SITEratedNotexistRate)) + ') ' + __lang__(32131) + ':\r\n'
        for id, data in SITEratedNotexistRate.items():
            labels_title = labels_title + '[COLOR=green]>>[/COLOR] '
            labels_title = labels_title + data['title'] + ' (' + __lang__(32132) + ': ' + str(data['rating']) + ')\r\n'
        labels_title = labels_title + '\r\n'
        
        # prepare labels for existed ratings
        labels_title = labels_title + __lang__(32128) + ' (' +  str(len(SITEratedExistRate)) + ') ' + __lang__(32133) + ':\r\n'
        for id, data in SITEratedExistRate.items():
            labels_title = labels_title + '[COLOR=red]>>[/COLOR] '
            color = 'green' if data['rating'] == KODIrated[id]['new_rating'] else "red"
            labels_title = labels_title + data['title'] + ' (' + __lang__(32132) + ': ' + str(data['rating']) + ' - ' + __lang__(32134) + ': [COLOR=' + color + ']' + str(KODIrated[id]['new_rating']) + '[/COLOR])\r\n'
            
        ret = dialog.DIALOG().start('script-user-rating-text.xml', labels={10062: __lang__(32137) + ' ' + siteLabel + ' ' + __lang__(32142) + ' KODI'}, textboxes={10063: labels_title}, buttons=[__lang__(32138), __lang__(32139), __lang__(32140)], list=10050)
        
        if ret == 0:
            self.saveRatings(SITErated, type)
        if ret == 1:
            self.saveRatings(SITEratedNotexistRate, type)
        if ret == 2:
            return
    
    # FUNCTIONS
    def getRatedKODI(self, type):
        if 'episode' in type:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Get' + type.title() + 's", "params": {"properties": ["title", "userrating", "season", "episode", "tvshowid"]}, "id": 1}')
        else:
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Get' + type.title() + 's", "params": {"properties": ["title", "userrating"]}, "id": 1}')
        jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
        debug.debug('search' + type.title() + 'ID: ' + str(jsonGet))
        
        tvshowTitle = {}
        
        KODIrated = {}
        if 'result' in jsonGet and type + 's' in jsonGet['result']:
            for i in jsonGet['result'][type + 's']:
                if i['userrating'] > 0:
                    
                    title = i['title']
                    
                    # get tvshow title for episode
                    if 'episode' in type:
                        if i['tvshowid'] not in tvshowTitle.keys():
                            jsonGet2 = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShowDetails", "params": {"tvshowid": ' + str(i['tvshowid']) + ', "properties": ["title"]}, "id": 1}')
                            jsonGet2 = json.loads(unicode(jsonGet2, 'utf-8', errors='ignore'))
                            if 'result' in jsonGet2 and 'tvshowdetails' in jsonGet2['result'] and 'title' in jsonGet2['result']['tvshowdetails']:
                                tvshowTitle[i['tvshowid']] = jsonGet2['result']['tvshowdetails']['title'] + ' - '
                            else:
                                tvshowTitle[i['tvshowid']] = ''
                            
                        title = tvshowTitle[i['tvshowid']] + str(i['season']) + 'x' + str(i['episode']) + ' ' + title
                    
                    KODIrated[i[type + 'id']] = {
                        'mType': type,
                        'dbID': i[type + 'id'],
                        'new_rating': i['userrating'],
                        'title': title
                    }
        return KODIrated
    
    def checkToUpdate(self, type, rated):
        toUpdate = {}
        jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Get' + type.title() + 's", "params": {"properties": ["title", "imdbnumber"]}, "id": 1}')
        jsonGet = json.loads(unicode(jsonGet, 'utf-8', errors='ignore'))
        debug.debug('search' + type.title() + 'ID: ' + str(jsonGet))
        if 'result' in jsonGet and type + 's' in jsonGet['result']:
            for i in jsonGet['result'][type + 's']:
                if i['imdbnumber'] in rated.keys():
                    toUpdate[i[type + 'id']] = {'title': i['title'], 'data': rated[i['imdbnumber']]}
        return toUpdate
    
    def saveRatings(self, toUpdate, type):
        item_count = len(toUpdate.keys())
        item_added = 0
        bar = xbmcgui.DialogProgress()
        bar.create(__addonname__, '')
        
        for id, data in toUpdate.items():
            item_added += 1
            p = int((float(100) / float(item_count)) * float(item_added))
            bar.update(p, str(item_added) + ' / ' + str(item_count) + ' - ' + data['title'])
            jsonGet = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Set' + type.title() + 'Details", "params": {"' + type + 'id": ' + str(id) + ', "userrating": ' + str(data['rating']) + '}, "id": 1}')
        
            if bar.iscanceled():
                break
        
        debug.notify(__lang__(32144) + ' ' + str(item_added) + ' ' + __lang__(32128))
        bar.close()
        
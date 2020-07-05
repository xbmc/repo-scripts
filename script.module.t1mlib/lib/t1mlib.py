# -*- coding: utf-8 -*-
# Framework Video Addon Routines for Kodi
# For Kodi Matrix (v19) and above
#  
#
import sys
import os
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import urllib.parse
import calendar
import datetime
import requests

qp = urllib.parse.quote_plus
uqp = urllib.parse.unquote_plus
USERAGENT = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
httpHeaders = {'User-Agent': USERAGENT,
               'Accept':"application/json, text/javascript, text/html,*/*",
               'Accept-Encoding':'gzip,deflate,sdch',
               'Accept-Language':'en-US,en;q=0.8'
               }


class t1mAddon(object):

    def __init__(self, aname):
        self.addon = xbmcaddon.Addon(''.join(['plugin.video.', aname]))
        self.addonName = self.addon.getAddonInfo('name')
        self.localLang = self.addon.getLocalizedString
        self.homeDir = self.addon.getAddonInfo('path')
        self.addonIcon = xbmc.translatePath(os.path.join(self.homeDir, 'resources', 'icon.png'))
        self.addonFanart = xbmc.translatePath(os.path.join(self.homeDir,'resources' 'fanart.jpg'))
        self.defaultHeaders = httpHeaders
        self.defaultVidStream = {'codec': 'h264', 'width': 1280, 'height': 720, 'aspect': 1.78}
        self.defaultAudStream = {'codec': 'aac', 'language': 'en'}
        self.defaultSubStream = {'language': 'en'}

    def log(self, txt):
            message = ''.join([self.addonName, ' : ', txt])
            xbmc.log(msg=message, level=xbmc.LOGDEBUG)


    def addMenuItem(self, name, mode, ilist=None, url=None, thumb=None, fanart=None,
                    videoInfo=None, videoStream=None, audioStream=None,
                    subtitleStream=None, cm=None, isFolder=True):
        videoStream = self.defaultVidStream
        audioStream = self.defaultAudStream
        subtitleStream = self.defaultSubStream
        liz = xbmcgui.ListItem(name, offscreen=True)
        liz.setArt({'thumb': thumb, 'fanart': fanart})
        liz.setInfo('Video', videoInfo)
        liz.addStreamInfo('video', videoStream)
        liz.addStreamInfo('audio', audioStream)
        liz.addStreamInfo('subtitle', subtitleStream)
        if cm is not None:
            liz.addContextMenuItems(cm)
        if not isFolder:
            liz.setProperty('IsPlayable', 'true')
        u = ''.join([sys.argv[0], '?mode=', str(mode), '&url='])
        if url is not None:
            u = ''.join([u, qp(url)])
        ilist.append((u, liz, isFolder))
        return ilist

    # override or extend these functions in the specific addon default.py

    def getAddonMenu(self, url, ilist):
        return ilist

    def getAddonCats(self, url, ilist):
        return ilist

    def getAddonMovies(self, url, ilist):
        return ilist

    def getAddonShows(self, url, ilist):
        return ilist

    def getAddonEpisodes(self, url, ilist):
        return ilist

    def getAddonSearch(self, url, ilist):
        return ilist

    def getAddonListing(self, url, ilist):
        url, sta, sids = url.split('|')
        d = datetime.datetime.utcnow()
        now = calendar.timegm(d.utctimetuple())
        a = requests.get(''.join(['http://mobilelistings.tvguide.com/Listingsweb/ws/rest/airings/',sta,'/start/',str(now),'/duration/20160?channelsourceids=',sids,'&formattype=json']), headers=self.defaultHeaders).json()
        for b in a[:10]:
            b = b['ProgramSchedule']
            st = datetime.datetime.fromtimestamp(float(b['StartTime'])).strftime('%H:%M')
            et = datetime.datetime.fromtimestamp(float(b['EndTime'])).strftime('%H:%M')
            duration = int(float(b['EndTime']) - float(b['StartTime']))
            name = ''.join([st,' - ',et,'  ',str(b.get('Title'))])
            infoList = {'mediatype':'episode',
                        'Title': name,
                        'duration': duration,
                        'Plot':  ''.join([st,' - ',et,'        ',str(duration/60),' min.\n\n[COLOR blue]',str(b.get('Title')),'\n',str(b.get('EpisodeTitle')),'[/COLOR]\n\n',str(b.get('CopyText'))]),
                        'MPAA': b.get('Rating')
                       }
            c = requests.get(''.join(['https://mapi.tvguide.com/listings/expanded_details?v=1.5&program=',str(b.get('ProgramId'))]), headers=self.defaultHeaders).json()
            thumb = self.addonIcon
            fanart = self.addonFanart
            if not (c.get('tvobject') is None):
                img = c['tvobject'].get('image')
                if not (img is None):
                    thumb = img.get('url')
                img = c['tvobject'].get('backgroundImages')
                if not (img is None):
                    fanart = img[0].get('url')
            ilist = self.addMenuItem(name,'LV', ilist, url, thumb, fanart, infoList, isFolder=False)
        return(ilist)

    def getAddonLiveVideo(self, url):
        liz = xbmcgui.ListItem(path = url, offscreen=True)
        liz.setProperty('inputstream','inputstream.adaptive')
        liz.setProperty('inputstream.adaptive.manifest_type','hls')
        liz.setMimeType('application/x-mpegURL')
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)


    def getAddonVideo(self, url):
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, xbmcgui.ListItem(path=uqp(url), offscreen=True))

    def doFunction(self, url):
        return

    # internal functions for views, cache and directory management

    def procDir(self, dirFunc, url, content, cache2Disc=True):
        ih = int(sys.argv[1])
        xbmcplugin.setContent(ih, content)
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_EPISODE)
        ilist = dirFunc(url, [])
        xbmcplugin.addDirectoryItems(ih, ilist, len(ilist))
        xbmcplugin.endOfDirectory(ih, cacheToDisc=cache2Disc)

    def getVideo(self, url, ilist):
        self.getAddonVideo(url)


    def processAddonEvent(self):
        mtable = {None : [self.getAddonMenu, 'files'],
                  'GC' : [self.getAddonCats, 'files'],
                  'GM' : [self.getAddonMovies, 'movies'],
                  'GS' : [self.getAddonShows, 'tvshows'],
                  'GE' : [self.getAddonEpisodes, 'episodes'],
                  'SE' : [self.getAddonSearch, 'movies'],
                  'GL' : [self.getAddonListing, 'episodes']}
        ftable = {'GV' : self.getAddonVideo,
                  'LV' : self.getAddonLiveVideo,
                  'DF' : self.doFunction}
        parms = {}
        if len((sys.argv[2][1:])) > 0:
            parms = dict(arg.split("=") for arg in ((sys.argv[2][1:]).split("&")))
            for key in parms:
                parms[key] = uqp(parms[key])
        fun = mtable.get(parms.get('mode'))
        if fun != None:
            self.procDir(fun[0],parms.get('url'),fun[1])
        else:
            fun = ftable.get(parms.get('mode'))
            if fun != None:
                fun(parms.get('url'))

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

    def getAddonVideo(self, url):
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, xbmcgui.ListItem(path=uqp(url), offscreen=True))

    def doFunction(self, url):
        return

    # internal functions for views, cache and directory management

    def procDir(self, dirFunc, url, cache2Disc=True):
        ih = int(sys.argv[1])
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(ih, xbmcplugin.SORT_METHOD_EPISODE)
        ilist = dirFunc(url, [])
        xbmcplugin.addDirectoryItems(ih, ilist, len(ilist))
        xbmcplugin.endOfDirectory(ih, cacheToDisc=cache2Disc)

    def getVideo(self, url, ilist):
        self.getAddonVideo(url)


    def processAddonEvent(self):
        mtable = {None : self.getAddonMenu,
                  'GC' : self.getAddonCats,
                  'GM' : self.getAddonMovies,
                  'GS' : self.getAddonShows,
                  'GE' : self.getAddonEpisodes}
        ftable = {'GV' : self.getAddonVideo,
                  'DF' : self.doFunction}
        parms = {}
        if len((sys.argv[2][1:])) > 0:
            parms = dict(arg.split("=") for arg in ((sys.argv[2][1:]).split("&")))
            for key in parms:
                parms[key] = uqp(parms[key])
        fun = mtable.get(parms.get('mode'))
        if fun != None:
            self.procDir(fun,parms.get('url'))
        else:
            fun = ftable.get(parms.get('mode'))
            if fun != None:
                fun(parms.get('url'))
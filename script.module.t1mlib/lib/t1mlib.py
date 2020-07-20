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
import xbmcvfs
import urllib.parse
import calendar
import datetime
import requests
import string
import json
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import tostring
import html.parser
from xml.dom import minidom

qp = urllib.parse.quote_plus
uqp = urllib.parse.unquote_plus
UNESCAPE = html.parser.HTMLParser().unescape
USERAGENT = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'
httpHeaders = {'User-Agent': USERAGENT,
               'Accept':"application/json, text/javascript, text/html,*/*",
               'Accept-Encoding':'gzip,deflate,sdch',
               'Accept-Language':'en-US,en;q=0.8'
               }


class t1mAddon(object):

    def __init__(self, aname):
        self.script = xbmcaddon.Addon('script.module.t1mlib')
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
        liz.setArt({'thumb': thumb, 'fanart': fanart, 'poster':thumb})
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


    def cleanFilename(self, filename):
        whitelist = "-_.() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in filename if c in whitelist)
        return filename


    def makeLibraryPath(self, ftype, name=None):
        if name is None:
            name  = self.cleanFilename(xbmc.getInfoLabel('ListItem.Title').replace('(Series)','',1).strip())
        profile = self.script.getAddonInfo('profile')
        moviesDir  = xbmc.translatePath(os.path.join(profile,str(ftype)))
        movieDir  = xbmc.translatePath(os.path.join(moviesDir, name))
        if not os.path.isdir(movieDir):
            os.makedirs(movieDir)
        return movieDir

    def doScan(self,movieDir):
        json_cmd = '{"jsonrpc":"2.0","method":"VideoLibrary.Scan", "params": {"directory":"%s/"},"id":1}' % movieDir.replace('\\','/')
        jsonRespond = xbmc.executeJSONRPC(json_cmd)


    def addMusicVideoToLibrary(self, url):
        url, infoList = urllib.parse.unquote_plus(url).split('||',1)
        infoList = eval(infoList)
        artist = infoList.get('artist')
        title = infoList.get('title')
        movieDir = self.makeLibraryPath('music_videos', name=self.cleanFilename(artist))
        strmFile = xbmc.translatePath(os.path.join(movieDir, ''.join([self.cleanFilename(title),'.strm'])))
        url = ''.join([sys.argv[0],'?mode=GV&url=',url])
        with open(strmFile, 'w') as outfile:
            outfile.write(url)
        nfoFile = xbmc.translatePath(os.path.join(movieDir, ''.join([self.cleanFilename(title),'.nfo'])))
        nfoData = Element('musicvideo')
        for key, val in infoList.items():
            child = Element(key)
            child.text = str(val)
            nfoData.append(child)

        nfoData = UNESCAPE(minidom.parseString(tostring(nfoData)).toprettyxml(indent="   "))

        with open(nfoFile, 'w') as outfile:
            outfile.write(nfoData)
        self.doScan(movieDir)


    def addMovieToLibrary(self, url):
        name  = self.cleanFilename(''.join([xbmc.getInfoLabel('ListItem.Title'),'.strm']))
        movieDir = self.makeLibraryPath('movies')
        strmFile = xbmc.translatePath(os.path.join(movieDir, name))
        url = ''.join([sys.argv[0],'?mode=GV&url=',url])
        with open(strmFile, 'w') as outfile:
            outfile.write(url)
        self.doScan(movieDir)


    def addShowByDate(self,url):
        url = uqp(url)
        movieDir = self.makeLibraryPath('shows')
        ilist = []
        ilist = self.getAddonEpisodes(url, ilist)
        for url, liz, isFolder in ilist:
            pdate = str(liz.getVideoInfoTag().getFirstAired())
            pdate = pdate.split('/')
            pdate = ''.join([pdate[2],'-',pdate[0],'-',pdate[1]])
            title = self.cleanFilename(str(liz.getVideoInfoTag().getTitle()))
            TVShowTitle = self.cleanFilename(str(liz.getVideoInfoTag().getTVShowTitle()))
            se = ''.join([TVShowTitle,' ',pdate,' [',title,'].strm'])
            strmFile = xbmc.translatePath(os.path.join(movieDir, se))
            with open(strmFile, 'w') as outfile:
                outfile.write(url)
        self.doScan(movieDir)


    def addShowToLibrary(self,url):
        movieDir = self.makeLibraryPath('shows')
        ilist = []
        ilist = self.getAddonEpisodes(url, ilist)
        for url, liz, isFolder in ilist:
            season = str(liz.getVideoInfoTag().getSeason())
            episode = str(liz.getVideoInfoTag().getEpisode())
            title = self.cleanFilename(str(liz.getVideoInfoTag().getTitle()))
            se = ''.join(['S',season,'E',episode,'  ',title,'.strm'])
            strmFile = xbmc.translatePath(os.path.join(movieDir, se))
            with open(strmFile, 'w') as outfile:
                outfile.write(url)
        self.doScan(movieDir)


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
                  'AM' : self.addMovieToLibrary,
                  'AS' : self.addShowToLibrary,
                  'AD' : self.addShowByDate,
                  'MU' : self.addMusicVideoToLibrary,
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

# -*- coding: utf-8 -*-
# Framework Video Addon Routines for Kodi
# Needs at least Kodi 14.2, preferably 15.0 and above
#  
#
import sys
import os
import re
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import urllib
import urllib2
import zlib
import json
import HTMLParser

h = HTMLParser.HTMLParser()
qp  = urllib.quote_plus
uqp = urllib.unquote_plus
USERAGENT   = 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36'

httpHeaders = {'User-Agent': USERAGENT,
                        'Accept':"application/json, text/javascript, text/html,*/*",
                        'Accept-Encoding':'gzip,deflate,sdch',
                        'Accept-Language':'en-US,en;q=0.8'
                       }


UTF8 = 'utf-8'

class t1mAddon(object):

  def __init__(self, aName):
    return('')

  def log(self, txt):
    try:
      message = '%s: %s' % (self.addonName, txt.encode('ascii', 'ignore'))
      xbmc.log(msg=message, level=xbmc.LOGDEBUG)
    except:
      pass


  def getRequest(self, url, udata=None, headers = httpHeaders, dopost = False, rmethod = None):
    return('')

  def getAddonMeta(self):
    return('')

  def updateAddonMeta(self, meta):

      
  def addMenuItem(self, name, mode, ilist=[], url=None, thumb=None, fanart=None, 
                  videoInfo={}, videoStream=None, audioStream=None,
                  subtitleStream=None, cm=None, isFolder=True ):
      return('')

#override or extend these functions in the specific addon default.py

  def getAddonMenu(self,url,ilist):
      return('')

  def getAddonCats(self,url,ilist):
      return('')

  def getAddonMovies(self,url,ilist):
      return('')

  def getAddonShows(self,url,ilist):
      ilist = []
      return('')

  def getAddonEpisodes(self,url,ilist):
      ilist = []
      return('')

  def getAddonVideo(self, url):
      return('')

  def doFunction(self,url):
      return('')


#internal functions for views, cache and directory management

  def procDir(self, dirFunc, url, contentType='files', viewType='default_view', cache2Disc=True):
      return('')

  def getVideo(self,url):
      return('')
          
  def doResolve(self, liz, subtitles = []):
      return('')

  def procConvertSubtitles(self, suburl):
      return('')

  def getAddonParms(self):
    parms = {}
    try:
       parms = dict( arg.split( "=" ) for arg in ((sys.argv[2][1:]).split( "&" )) )
       for key in parms:
         try:    parms[key] = urllib.unquote_plus(parms[key]).decode(UTF8)
         except: pass
    except:
       parms = {}
    return(parms.get)


  def processAddonEvent(self):
    p = self.getAddonParms()
    mode = p('mode',None)

    if mode==  None:  self.procDir(self.getAddonMenu,    p('url'), 'files', 'default_view')
    elif mode=='GC':  self.procDir(self.getAddonCats,    p('url'), 'files', 'default_view')
    elif mode=='GM':  self.procDir(self.getAddonMovies,  p('url'), 'movies', 'movie_view')
    elif mode=='GS':  self.procDir(self.getAddonShows,   p('url'), 'tvshows', 'show_view')
    elif mode=='GE':  self.procDir(self.getAddonEpisodes,p('url'), 'episodes', 'episode_view')
    elif mode=='GV':  self.getVideo(p('url'))
    elif mode=='DF':  self.doFunction(p('url'))
    return(p)

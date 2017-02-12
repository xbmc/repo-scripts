#!/usr/bin/python
# -*- coding: utf-8 -*-

import xbmc,xbmcaddon
import sys,urllib,os
import xbmcgui,xbmcplugin
import cookielib,urllib2

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('path') )


icon = os.path.join(xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')),'icon.png').decode('utf-8')
background = os.path.join(__addondir__,"fanart.jpg")
defaultBackground = background
defaultThumb = ""

  
def debug(content):
    log(content, xbmc.LOGDEBUG)
    
def notice(content):
    log(content, xbmc.LOGNOTICE)

def log(msg, level=xbmc.LOGDEBUG):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level) 

   
def parameters_string_to_dict(parameters):
  paramDict = {}
  if parameters:
    paramPairs = parameters[1:].split("&")
    for paramsPair in paramPairs:
      paramSplits = paramsPair.split('=')
      if (len(paramSplits)) == 2:
        paramDict[paramSplits[0]] = paramSplits[1]
  return paramDict  
    
def addDir(name, url, mode, iconimage, desc="",sortname=""):
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok = True
    liz = xbmcgui.ListItem(name)
    liz.setArt({ 'thumb' : iconimage })
    liz.setArt({ 'fanart': icon })
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc,"TrackNumber":sortname})  
    if not iconimage or iconimage==icon or iconimage==defaultThumb:
        iconimage = defaultBackground
        liz.setProperty("fanart_image", iconimage)
    else:
        liz.setProperty("fanart_image", defaultBackground)
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok
  
def addLink(name, url, mode, iconimage, duration="", desc="", genre=''):
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok = True
    liz = xbmcgui.ListItem(name)
    liz.setArt({ 'thumb' : iconimage })
    liz.setArt({ 'fanart': icon })
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc, "Genre": genre})    
    liz.setProperty('IsPlayable', 'true')
    liz.addStreamInfo('video', { 'duration' : duration })
    liz.setProperty("fanart_image", iconimage)
    #liz.setProperty("fanart_image", defaultBackground)
    xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)
    return ok

def geturl(url):
   debug("geturl url : "+url)
   cj = cookielib.CookieJar()
   opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
   req = urllib2.Request(url)
   inhalt = urllib2.urlopen(req).read()   
   return inhalt    
debug("Loaded funktions") 
   
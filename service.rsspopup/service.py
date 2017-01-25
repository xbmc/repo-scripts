#!/usr/bin/python
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, sys, os, urlparse,json
import xbmc ,xbmcgui, xbmcaddon,xbmcvfs
import urllib2,urllib,json
import shutil
import re,md5
import socket, cookielib
import feedparser
import popupwindow
import HTMLParser
from dateutil import parser

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('path') )
background = os.path.join(__addondir__,"bg.png")

profile    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp', '') ).decode("utf-8")
translation = __addon__.getLocalizedString


  
wid = xbmcgui.getCurrentWindowId()
window=xbmcgui.Window(wid)
window.show()
        
def debug(content):
    log(content, xbmc.LOGDEBUG)
    
def notice(content):
    log(content, xbmc.LOGNOTICE)

def log(msg, level=xbmc.LOGNOTICE):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level) 
    
    
# Einlesen von Parametern, Notwendig fuer Reset der Twitter API
def parameters_string_to_dict(parameters):
	paramDict = {}
	if parameters:
		paramPairs = parameters[1:].split("&")
		for paramsPair in paramPairs:
			paramSplits = paramsPair.split('=')
			if (len(paramSplits)) == 2:
				paramDict[paramSplits[0]] = paramSplits[1]
	return paramDict

if not xbmcvfs.exists(temp):
   xbmcvfs.mkdirs(temp)

    
def addrss():
    dialog = xbmcgui.Dialog()
    d = dialog.input("Url des Feeds", type=xbmcgui.INPUT_ALPHANUM)
    filename       = xbmc.translatePath( os.path.join( temp, 'urlliste.txt') ).decode("utf-8")
    if xbmcvfs.exists(filename) :
      fp=open(filename,"r") 
      content=fp.read()
      fp.close()    
      content=content+"\n"+d
    else :
       content=d
    fp = open(filename, 'w')    
    fp.write(content)
    fp.close()    
      
def deleterss():
   filename       = xbmc.translatePath( os.path.join( temp, 'urlliste.txt') ).decode("utf-8")
   if xbmcvfs.exists(filename) :
      fp=open(filename,"r") 
      content=fp.read()
      fp.close()          
      liste=content.split("\n")
      dialog = xbmcgui.Dialog()
      nr=dialog.select(translation(30001), liste)
      if nr<0:
        return
      liste.remove(liste[nr])
      content="\n"
      content=content.join(liste)
      fp = open(filename, 'w')    
      fp.write(content)
      fp.close()    
      
   
   
# Soll Twitter Api Resetter Werden
if len(sys.argv) > 1:
    params = parameters_string_to_dict(sys.argv[2])
    mode = urllib.unquote_plus(params.get('mode', ''))
    if mode=="addrss":
      addrss()
    if mode=="deleterss":
      deleterss()
    



def geturl(url):
   req = urllib2.Request(url)
   inhalt = urllib2.urlopen(req).read()   
   return inhalt    
          
    
if __name__ == '__main__':
    cimg=""
    xbmc.log("Twitter:  Starte Plugin")

    schown=[]
    monitor = xbmc.Monitor()   
    
    while not monitor.abortRequested():
      titlelist=[]
      cimglist=[]
      greyoutlist=[]
      lesezeitlist=[]
      timelist=[] 
      xbmc.log("Hole Umgebung")
      bild=__addon__.getSetting("bild") 
      lesezeit=__addon__.getSetting("lesezeit")
      greyout=__addon__.getSetting("greyout")
      xmessage=__addon__.getSetting("x-message")  
      ymessage=__addon__.getSetting("y-message")  
      hoehemessage=__addon__.getSetting("hoehe-message")  
      breitemessage=__addon__.getSetting("breite-message")  
      hoehebild=__addon__.getSetting("hoehe-bild")  
      breitebild=__addon__.getSetting("breite-bild")  
      font=__addon__.getSetting("font")  
      fontcolor=__addon__.getSetting("fontcolor") 
      filename       = xbmc.translatePath( os.path.join( temp, 'urlliste.txt') ).decode("utf-8")
      gesamtliste=[]
      if xbmcvfs.exists(filename) :
        fp=open(filename,"r") 
        content=fp.read()
        fp.close()          
        liste=content.split("\n")                
        for Feed in liste:                                
            feed = feedparser.parse(Feed)      
            debug("--Feed--")
            debug(feed)
            debug("----")
            for ii, item in enumerate(feed.entries):   
                if 'description' in item:
                        inhalt = item.description 
                if 'content' in item:                         
                    inhalt=item.content[0].value
                #convert news text into plain text
                inhalt = re.sub('<p[^>\\n]*>','\n\n',inhalt)
                inhalt = re.sub('<br[^>\\n]*>','\n',inhalt)
                inhalt = re.sub('<[^>\\n]+>','',inhalt)
                inhalt = re.sub('\\n\\n+','\n\n',inhalt)
                inhalt = re.sub('(\\w+,?) *\\n(\\w+)','\\1 \\2',inhalt)  
                inhalt = HTMLParser.HTMLParser().unescape(inhalt)
                title=item.title
                if 'published_parsed' in item:
                        sdate=time.strftime('%d %b %H:%M',item.published_parsed)
                else:
                    sdate=''            
                try:
                    maxwidth=0
                    if 'media_thumbnail' in item:
                        for img in item.media_thumbnail:
                                w=1
                                if 'width' in img: w=img['width']
                                if w>maxwidth:
                                    cimg=img['url']
                                    maxwidth=w
                    if 'enclosures' in item:
                        for img in item.enclosures:
                                if re.search('\.(png|jpg|jpeg|gif)',img.href.lower()):
                                    cimg = img.href
                                elif 'type' in img:
                                    if img.type.lower().find('image') >= 0:
                                        cimg = img.href
                except:                
                        pass
                if cimg:
                        cimg = cimg.replace('&amp;','&') #workaround for bug in feedparser                   
                #debug("Content:" + inhalt)
                debug("-----------------")
                debug("Datum"+ sdate)
                debug("-----------------")
                debug("Immage"+ cimg)
                debug("-----------------")
                if not bild=="true":
                    cimg=""
                if title not in schown:
                    #savemessage(title,cimg,greyout,lesezeit) 
                    titlelist.append(title)
                    cimglist.append(cimg)
                    greyoutlist.append(greyout)
                    lesezeitlist.append(lesezeit) 
                    #Donnerstag, 4. August 2016 16:07                           
                    dt = parser.parse(sdate)                    
                    day_string = dt.strftime('%Y-%m-%d %H:%M')                    
                    timelist.append(day_string)
                    timelist,titlelist,cimglist,lesezeitlist,greyoutlist = (list(x) for x in zip(*sorted(zip(timelist,titlelist,cimglist,lesezeitlist,greyoutlist))))
        for i in range(len(titlelist)):  
                   if not titlelist[i] in schown:
                      popupwindow.savemessage(__addon__,titlelist[i],cimglist[i],greyoutlist[i],lesezeitlist[i],xmessage,ymessage,breitemessage,hoehemessage,breitebild,hoehebild,font,fontcolor)             
                      schown.append(title)                   
      if monitor.waitForAbort(60):
        break            
      
           
      

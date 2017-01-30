#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, sys, os, urlparse,json
import xbmc ,xbmcgui, xbmcaddon,xbmcvfs
import urllib2,urllib,json
import shutil
import re,md5
import socket, cookielib
import feedparser
import HTMLParser,xbmcplugin
from dateutil import parser
from django.utils.encoding import smart_str

xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TRACKNUM)


__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('path') )
background = os.path.join(__addondir__,"fanart.jpg")

profile    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp', '') ).decode("utf-8")
translation = __addon__.getLocalizedString

popupaddon=xbmcaddon.Addon("service.popwindow")
popupprofile    = xbmc.translatePath( popupaddon.getAddonInfo('profile') ).decode("utf-8")
popuptemp       = xbmc.translatePath( os.path.join( popupprofile, 'temp', '') ).decode("utf-8")
  
icon = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path')+'/icon.png').decode('utf-8')

defaultBackground = background
defaultThumb = ""




        
def debug(content):
    log(content, xbmc.LOGDEBUG)
    
def notice(content):
    log(content, xbmc.LOGNOTICE)

def log(msg, level=xbmc.LOGNOTICE):
    addon = xbmcaddon.Addon()
    addonID = addon.getAddonInfo('id')
    xbmc.log('%s: %s' % (addonID, msg), level) 
    
    
# Einlesen von Parametern, Notwendig für Reset der Twitter API
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

def ersetze(text):
#
    text=text.replace ("</p>","").replace("<p>","").replace("<div id='articleTranscript'>","").replace("<br />","").replace('<div id="image-caption">',"").replace("	","").replace("<p","")
    text=text.replace ("<em>","").replace("</em>","")
    text=text.replace ("<h3>","").replace("</h3>","")
    text=text.replace ("<hr>","")
    text = text.replace("&quot;", "\"")
    text = text.replace("&apos;", "'")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&laquo;", "<<")
    text = text.replace("&raquo;", ">>")
    text = text.replace("&#039;", "'")
    text = text.replace("&#8220;", "\"")
    text = text.replace("&#8221;", "\"")
    text = text.replace("&#8211;", "-")
    text = text.replace("&#8216;", "\'")
    text = text.replace("&#8217;", "\'")
    text = text.replace("&#9632;", "")
    text = text.replace("&#8226;", "-")
    text = text.replace('<span class="caps">', "")
    text = text.replace('</span>', "")
    text = text.replace('\u00fc', "ü")  
    text = text.replace('\u00e4', "ä")     
    text = text.replace('\u00df', "ß")      
    text = text.replace('\u00f6', "ö")      
    text = text.replace('\/', "/")    
    #text = text.replace('\n', "")    
    text = text.strip()
    return text

def addDir(name, url, mode, iconimage, desc="",sortname=""):
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage=icon, thumbnailImage=iconimage)
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
    liz = xbmcgui.ListItem(name, iconImage=defaultThumb, thumbnailImage=iconimage)
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
  
def liega(lieganr,nname):
   oldi=0
   content=geturl("https://api.sport1.de/api/sports/competition/co"+lieganr)
   struktur = json.loads(content) 
   debug("Liega Matchday Content :"+ content)
   day=struktur["current_matchday"]   
   debug("Liega Day :"+ day)
   debug("url day "+"https://api.sport1.de/api/sports/matches-by-season/co"+lieganr+"/se/")
   content=geturl("https://api.sport1.de/api/sports/matches-by-season/co"+lieganr+"/se/")
   struktur = json.loads(content)    
   tage=struktur["round"]
   
   filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")
   if xbmcvfs.exists(filename) :
      fp=open(filename,"r") 
      spielfile=fp.read()
      fp.close()   
   else:
      spielfile="" 
   if not "Alle Spiele "+nname in spielfile:
      url="Alle Spiele "+nname+"##-##"+ str(lieganr) +"##"+ str(day) +"##-1##-##-##-##-"
      addDir("Alle Spiele "+nname, url, mode="savespiel", iconimage="" )            
      url=""
   for tag in tage:
    spiele=tag["match"]
    for spiel in spiele:
      #debug("#############")
      #debug(spiel)
      # full oder data
      live_status=smart_str(spiel["live_status"])
      aus=smart_str(spiel["away"]["name"])
      ins=smart_str(spiel["home"]["name"])
      ende=spiel["finished"]
      match_date=smart_str(spiel["match_date"])
      match_time=smart_str(spiel["match_time"])
      if match_time=="unknown":
          match_time=""     
      id=spiel["id"]      
      name=match_date +" "+ match_time +" : "+ins +" - "+ aus 
      url=str(id) 
      debug("   ende : "+ende)      
      debug("   live_status : "+live_status)
      if ende=="no" and not live_status=="none" and not live_status=="result" or oldi==1:
       url=name+"##"+live_status +"##"+ str(lieganr) +"##"+ str(day) +"##"+str(id)+"##"+aus+"##"+ins+"##"+match_date+"##"+match_time       
       debug("URL :::: ")
       debug(url)
       if url not in spielfile:
         addDir(name, url, mode="savespiel", iconimage="" )  
   xbmcplugin.endOfDirectory(addon_handle,succeeded=True,updateListing=False,cacheToDisc=True)  
def savespiel(zeile)  :
    debug("savespiel start")
    filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")
    if xbmcvfs.exists(filename) :
      fp=open(filename,"r") 
      content=fp.read()
      fp.close()   
      content=content+"\n"+zeile      
    else :
       content=zeile   
    fp = open(filename, 'w')    
    fp.write(content)
    fp.close()   
    xbmc.executebuiltin("Container.Refresh")    
 
def add_game(url):
      debug("Start Add Game")      
      content=geturl(url)
      match=re.compile('a href="/liga/(.+?)" title="Zur Seite von (.+?)"><span class="s1-logo-team"><img src="(.+?)"', re.DOTALL).findall(content)
      doppelteweg=[]
      count=0
      for url,name,image in match:        
        if not url in doppelteweg :
            count=count+1            
            doppelteweg.append(url)
            newimg=os.path.join(xbmcaddon.Addon().getAddonInfo('path'),"grafix",name +".png")
            debug("newimg : "+newimg)
            if xbmcvfs.exists(newimg):
               image=newimg
            addDir(name, url, mode="liega", iconimage=image ,sortname=str(count))         
            debug ("Adde Name:" + name)
            debug ("Adde url:" + url)
            debug ("Adde mode:" + mode)
            debug ("Adde iconimage:" + image)            
      xbmcplugin.endOfDirectory(addon_handle,succeeded=True,updateListing=False,cacheToDisc=True)
      
def delgame():
    filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")
    if xbmcvfs.exists(filename) :
        fp=open(filename,"r") 
        spielfile=fp.read()
        fp.close()               
        if "##" in spielfile:
            lines=spielfile.split("\n")
            for line in lines:
                if "##" in line:
                    debug("???? line "+line)
                    arr=line.split("##")
                    name=arr[0]
                    live_status=arr[1]
                    lieganr=arr[2]
                    dayid=arr[3]
                    spielnr=arr[4]
                    aus=arr[5]
                    ins=arr[6]
                    match_date=arr[7]
                    match_time=arr[8]
                    addDir(name, line, mode="delspiel", iconimage="" )  
    xbmcplugin.endOfDirectory(addon_handle,succeeded=True,updateListing=False,cacheToDisc=True) 
def delspiel(zeile)   :
    filename       = xbmc.translatePath( os.path.join( temp, 'spiel.txt') ).decode("utf-8")
    fp=open(filename,"r") 
    spielfile=fp.read()
    fp.close()       
    lines=spielfile.split("\n")
    fileinhalt=""
    for line in lines:
       if not zeile==line and "##" in line:
         fileinhalt=fileinhalt+"\n"+line          
    fp = open(filename, 'w')    
    fp.write(fileinhalt)
    fp.close()    
def menu1():    
    debug("Start Menu")
    addDir(name=translation(30061), url="", mode="menu2", iconimage="" )
    addDir(name=translation(30060), url="", mode="delgame", iconimage="" )       
    addDir(translation(30059), "Settings", 'Settings', "") 
    xbmcplugin.endOfDirectory(addon_handle,succeeded=True,updateListing=False,cacheToDisc=True)

def menu2():
     addDir(name=translation(30058),url="http://www.sport1.de/fussball/alle-ligen-und-wettbewerbe", mode="add_game", iconimage="" )
     addDir(name=translation(30057),url="http://www.sport1.de/fussball/alle-ligen-und-wettbewerbe/nationale-ligen", mode="add_game", iconimage="" )
     addDir(name=translation(30056),url="http://www.sport1.de/fussball/alle-ligen-und-wettbewerbe/internationale-ligen-und-pokalwettbewerbe", mode="add_game", iconimage="" )
     addDir(name=translation(30055),url="http://www.sport1.de/fussball/alle-ligen-und-wettbewerbe/internationale-turniere", mode="add_game", iconimage="" )
     addDir(name=translation(30054),url="http://www.sport1.de/fussball/alle-ligen-und-wettbewerbe/internationale-klubwettbewerbe", mode="add_game", iconimage="" )
     xbmcplugin.endOfDirectory(addon_handle,succeeded=True,updateListing=False,cacheToDisc=True)
     

# Soll Twitter Api Resetter Werden
          
        
def savemessage(message,image,grey,lesezeit)  :
    message=unicode(message).encode('utf-8')
    image=unicode(image).encode('utf-8')
    debug("message :"+message)
    debug("image :"+image)
    debug("grey :"+grey)
    debug("popuptemp :"+popuptemp)
    debug("lesezeit :"+str(lesezeit))
    filename=md5.new(message).hexdigest()  
    f = open(popuptemp+"/"+filename, 'w')    
    f.write(message+"###"+image+"###"+grey+"###"+str(lesezeit))
    f.close()   
    

  
addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
params = parameters_string_to_dict(sys.argv[2])
mode = urllib.unquote_plus(params.get('mode', ''))
url = urllib.unquote_plus(params.get('url', ''))
name=urllib.unquote_plus(params.get('name', ''))
debug("Mode Is:"+mode)
if mode=='':
    menu1()  
if mode=="menu2":
    menu2()
if mode=="add_game":
    add_game(url)
if mode=="liega":
    liega(url,name)
if mode=="savespiel":
    savespiel(url)        
if mode=="delgame":
    delgame()   
if mode=="delspiel":
    delspiel(url)       
if mode == 'Settings':
          addon.openSettings()
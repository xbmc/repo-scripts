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
from resources.lib.funktionen import *

from dateutil import parser
from resources.lib.django.utils.encoding import smart_str




__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__addondir__    = xbmc.translatePath( __addon__.getAddonInfo('path') )

xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_TRACKNUM)
xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)




profile    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
temp       = xbmc.translatePath( os.path.join( profile, 'temp', '') ).decode("utf-8")


popupaddon=xbmcaddon.Addon("service.popwindow")
popupprofile    = xbmc.translatePath( popupaddon.getAddonInfo('profile') ).decode("utf-8")
popuptemp       = xbmc.translatePath( os.path.join( popupprofile, 'temp', '') ).decode("utf-8")
  

def translation(text):
  text=__addon__.getLocalizedString(text).encode("utf-8")
  return text



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
      with open(filename, 'r') as fp :
        spielfile=fp.read()      
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
      debug("NAME :"+name)
      url=str(id) 
      debug("   end : "+ende)      
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
      with open(filename, 'r') as fp :
        content=fp.read()      
      content=content+"\n"+zeile      
    else :
       content=zeile   
    with open(filename, 'w') as fp :
        fp.write(content)
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
        with open(filename, 'r') as fp :
          spielfile=fp.read()        
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
    with open(filename, 'r') as fp :
      spielfile=fp.read()    
    lines=spielfile.split("\n")
    fileinhalt=""
    for line in lines:
       if not zeile==line and "##" in line:
         fileinhalt=fileinhalt+"\n"+line          
    with open(filename, 'w') as fp :
      fp.write(fileinhalt)    
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
    with open(os.path.join(popuptemp,filename), 'w') as fp :  
      fp.write(message+"###"+image+"###"+grey+"###"+str(lesezeit))
      
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

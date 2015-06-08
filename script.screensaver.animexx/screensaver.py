#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#   Fanart Screen saver 
#
#GNU GENERAL PUBLIC LICENSE
#
#Copyright (c) 2015 Andreas Vogler
#
import xbmcaddon
import xbmcgui
import xbmc
import xbmcvfs
import urllib, urllib2, re, os, json

#Global Settings
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path')
addon_id = addon.getAddonInfo('id')
global addon_data
global translation
translation = addon.getLocalizedString



class Animexx(xbmcgui.WindowXMLDialog):

    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
	self.handle_settings()

    def exit(self):
        self.exit_monitor = None
        self.abort_requested = True
        self.close()

#Loads JSON FEED
    def Feedladen(self,seitenr):
       self.url="https://ws.animexx.de/json/7-0328ijel/fanart/get_new/?seite=" + str(seitenr)
       if self.debug=="true":
          xbmc.log("Fanartsaver - Feedladen - Get Page: "+ str(seitenr))
       # JSON will be loaded in "Struktur"
       try: 
         req = urllib2.Request(self.url)
         req.add_header('Referer', 'http://repo.l0re.com')
         r = urllib2.urlopen(req).read()
         r=r.replace("\/","/")
         struktur = json.loads(r)
         if self.debug=="true":
            xbmc.log("Fanartsaver - Feedladen - Anzahl: "+ str(len(struktur['return'])))       
         anzahl=len(struktur['return'])
         # Loads Every Picture in URL, Picture Name in bildname,Author in author
         for element in range (0,anzahl):
	   # Whenn Small Images, only add them when it is activated in the Settings
           if ((self.klein == 'true') or  (self.klein == 'false') and ("gross" in struktur['return'][element]['item_image_big'])) :
             self.urls.append(struktur['return'][element]['item_image_big'])
             self.bildname.append(struktur['return'][element]['titel'])
             self.author.append(struktur['return'][element]['mitglied']['username'])
             if self.debug=="true":
               xbmc.log("Element: "+ struktur['return'][element]['item_image_big'])         
       except:
	 self.error_load=1
 

    def zeigebild(self,rul):
            url=self.urls[rul]
            title=self.bildname[rul]
            kuenstler=self.author[rul]
            self.getControl(30002).setLabel(title +" ( "+ translation(45004) +" "+ kuenstler +")")
            self.getControl(30001).setImage(url)

    def handle_settings(self):
      self.getControl(30002).setLabel(translation(45005))
      xbmc.log("Fanartsaver - handle_settings - Start")
      #Read Settings
      self.delayTime=int(addon.getSetting('Time'));
      self.debug=addon.getSetting('debug')
      self.klein=addon.getSetting('kleine')
      self.abort_requested = False
      self.error_load=0
      # Initial Array of one page
      self.urls = [];
      self.author = [];
      self.bildname = [];
      # Page Countewr
      self.seite=1
      # When Pictures would start from 1  Load Next Page      
      self.oldbild=self.seite
      # Counter what Picure of the Page is shown (initial with 0)
      self.bild=0
      # Load First Page
      self.Feedladen(self.seite)
      self.anz_bilder=len(self.urls)
      if self.debug=="true":
        xbmc.log("Fanartsaver -  handle_settings - Nr Of Pictures: "+ str(len(self.urls)))
      while not self.abort_requested:
	  # Coutn Picture  +1 
          self.bild=(self.bild + 1) % self.anz_bilder
          if self.debug=="true":
            xbmc.log("Fanartsaver -  handle_settings - Nr of the Picture: " + str(self.bild))
          # When Page Changes 
          if self.bild < self.oldbild :
            #Alle Arrays deleting
            self.urls = []
            self.author = []
            self.bildname = []
            # Count Page 1 Nr Up Max 5000
            self.seite=(self.seite+1) % 5000
            #Load New Page
            self.Feedladen(self.seite)
            self.anz_bilder=len(self.urls)
          if self.error_load==0:
            # Show Bild with nr self.bild
            self.zeigebild(self.bild)
          else:
            self.error_load=0
	    self.bild=self.oldbild
            self.anz_bilder=1
          # Sleep X Seconds (Set from sthe Settings
          xbmc.sleep(self.delayTime*1000)
   

# Initial Screen Saver
screensaver = Animexx(
        'fanart_screensaver.xml' ,
        addon_path,
        'default',
)
screensaver.doModal()
del screensaver
sys.modules.clear()


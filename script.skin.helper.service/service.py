#!/usr/bin/python
# -*- coding: utf-8 -*-

from resources.lib.Utils import *
from resources.lib.BackgroundsUpdater import BackgroundsUpdater
from resources.lib.ListItemMonitor import ListItemMonitor
from resources.lib.KodiMonitor import Kodi_Monitor
from resources.lib.WebService import WebService



class Main:
    
    def __init__(self):
        
        KodiMonitor = Kodi_Monitor()
        listItemMonitor = ListItemMonitor()
        backgroundsUpdater = BackgroundsUpdater()
        webService = WebService()
        lastSkin = None
                   
        #start the extra threads
        listItemMonitor.start()
        backgroundsUpdater.start()
        webService.start()
        
        while not KodiMonitor.abortRequested():
            
            #set skin info
            currentSkin = xbmc.getSkinDir()
            if lastSkin != currentSkin:
                setSkinVersion()
                lastSkin = currentSkin
            
            KodiMonitor.waitForAbort(10)
        else:
            # Abort was requested while waiting. We should exit
            xbmc.log('SKIN HELPER SERVICE --> shutdown requested !')
            #stop the extra threads
            backgroundsUpdater.stop()
            listItemMonitor.stop()
            webService.stop()

xbmc.log('skin helper service version %s started' % ADDON_VERSION)
Main()
xbmc.log('skin helper service version %s stopped' % ADDON_VERSION)


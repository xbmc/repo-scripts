#!/usr/bin/python
# -*- coding: utf-8 -*-

import resources.lib.Utils as utils
import resources.lib.MainModule as mainmodule
from resources.lib.BackgroundsUpdater import BackgroundsUpdater
from resources.lib.ListItemMonitor import ListItemMonitor
from resources.lib.KodiMonitor import Kodi_Monitor
from resources.lib.WebService import WebService
import xbmc, xbmcaddon


class Main:
    
    lastSkin = ""

    def checkSkinVersion(self):
        try:
            skin = xbmc.getSkinDir()
            skinLabel = xbmcaddon.Addon(id=skin).getAddonInfo('name').decode("utf-8")
            skinVersion = xbmcaddon.Addon(id=skin).getAddonInfo('version').decode("utf-8")
            if self.lastSkin != skinLabel+skinVersion:
                #auto correct skin settings
                self.lastSkin = skinLabel+skinVersion
                utils.WINDOW.setProperty("SkinHelper.skinTitle",skinLabel + " - " + xbmc.getLocalizedString(19114) + ": " + skinVersion)
                utils.WINDOW.setProperty("SkinHelper.skinVersion",xbmc.getLocalizedString(19114) + ": " + skinVersion)
                utils.WINDOW.setProperty("SkinHelper.Version",utils.ADDON_VERSION.replace(".",""))
                mainmodule.correctSkinSettings()
        except Exception as e:
            utils.logMsg("Error in setSkinVersion --> " + str(e), 0)
    
    def __init__(self):
        
        KodiMonitor = Kodi_Monitor()
        listItemMonitor = ListItemMonitor()
        backgroundsUpdater = BackgroundsUpdater()
        webService = WebService()
        lastSkin = None
                   
        #start the extra threads
        utils.WINDOW.clearProperty("SkinHelperShutdownRequested")
        listItemMonitor.start()
        backgroundsUpdater.start()
        webService.start()
        
        while not KodiMonitor.abortRequested():
            
            self.checkSkinVersion()
            KodiMonitor.waitForAbort(10)
        else:
            # Abort was requested while waiting. We should exit
            utils.WINDOW.setProperty("SkinHelperShutdownRequested","shutdown")
            utils.logMsg('Shutdown requested !',0)
            #stop the extra threads
            backgroundsUpdater.stop()
            listItemMonitor.stop()
            webService.stop()

utils.logMsg('skin helper service version %s started' % utils.ADDON_VERSION,0)
Main()
utils.logMsg('skin helper service version %s stopped' % utils.ADDON_VERSION,0)


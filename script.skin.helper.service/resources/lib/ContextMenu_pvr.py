# -*- coding: utf-8 -*-
from Utils import *
import ArtworkUtils as artworkutils

#Kodi contextmenu item to configure the artwork 
if __name__ == '__main__':
    
    ##### PVR Artwork ########
    artwork = {}
    logMsg("Context menu artwork settings for PVR artwork",0)
    WINDOW.setProperty("artworkcontextmenu", "busy")
    options=[]
    options.append(ADDON.getLocalizedString(32144)) #Refresh item (auto lookup)
    options.append(ADDON.getLocalizedString(32145)) #Refresh item (manual lookup)
    options.append(xbmc.getLocalizedString(13511)) #Choose art
    options.append(ADDON.getLocalizedString(32149)) #Add channel to ignore list
    options.append(ADDON.getLocalizedString(32150)) #Add title to ignore list
    options.append(ADDON.getLocalizedString(32148)) #Open addon settings
    header = ADDON.getLocalizedString(32143) + " - " + ADDON.getLocalizedString(32120)
    title = xbmc.getInfoLabel("ListItem.Title").decode('utf-8')
    if not title: title = xbmc.getInfoLabel("ListItem.Label").decode('utf-8')
    channel = xbmc.getInfoLabel("ListItem.ChannelName").decode('utf-8')
    path = xbmc.getInfoLabel("ListItem.FileNameAndPath").decode('utf-8')
    genre = xbmc.getInfoLabel("ListItem.Genre").decode('utf-8')
    year = xbmc.getInfoLabel("ListItem.Year").decode('utf-8')
    ret = xbmcgui.Dialog().select(header, options)
    if ret == 0:
        #Refresh item (auto lookup)
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year,ignoreCache=True, manualLookup=False)
    elif ret == 1:
        #Refresh item (manual lookup)
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year,ignoreCache=True, manualLookup=True)
    elif ret == 2:
        #Choose art
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year)

        import Dialogs as dialogs
        abort = False
        while not abort:
            listitems = []
            for art in ["thumb","poster","fanart","banner","clearart","clearlogo","discart","landscape","characterart"]:
                listitem = xbmcgui.ListItem(label=art)
                listitem.setProperty("icon",artwork.get(art,""))
                listitems.append(listitem)
            w = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=listitems, windowtitle=xbmc.getLocalizedString(13511),multiselect=False )
            w.doModal()
            selectedItem = w.result
            if selectedItem == -1:
                abort = True
            else:
                artoptions = []
                selectedItem = listitems[selectedItem]
                image = selectedItem.getProperty("icon")
                label = selectedItem.getLabel()
                heading = "%s: %s" %(xbmc.getLocalizedString(13511),label)
                if image:
                    listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(13512))
                    listitem.setProperty("icon",image)
                    artoptions.append(listitem)
                    
                    listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(231))
                    listitem.setProperty("icon","DefaultAddonNone.png")
                    artoptions.append(listitem)
                
                listitem = xbmcgui.ListItem(label=xbmc.getLocalizedString(1024))
                listitem.setProperty("icon","DefaultFolder.png")
                artoptions.append(listitem)
                
                w2 = dialogs.DialogSelectBig( "DialogSelect.xml", ADDON_PATH, listing=artoptions, windowtitle=heading,multiselect=False )
                w2.doModal()
                selectedItem = w2.result
                if image and selectedItem == 1:
                    artwork[label] = ""
                elif (image and selectedItem == 2) or not image and selectedItem == 0:
                    #manual browse...
                    image = xbmcgui.Dialog().browse( 2 , ADDON.getLocalizedString(32176), 'files', mask='.gif|.png|.jpg').decode("utf-8")
                    if image:
                        artwork[label] = image
        #save modifications
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year,ignoreCache=False, manualLookup=False,override=artwork)
        
    elif ret == 3:
        #Add channel to ignore list
        ignorechannels = WINDOW.getProperty("SkinHelper.ignorechannels").decode("utf-8")
        if ignorechannels: ignorechannels += ";"
        ignorechannels += channel
        ADDON.setSetting("ignorechannels",ignorechannels)
        WINDOW.setProperty("SkinHelper.ignorechannels",ignorechannels)
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year,ignoreCache=True, manualLookup=False)
    elif ret == 4:
        #Add title to ignore list
        ignoretitles = WINDOW.getProperty("SkinHelper.ignoretitles").decode("utf-8")
        if ignoretitles: ignoretitles += ";"
        ignoretitles += title
        ADDON.setSetting("ignoretitles",ignoretitles)
        WINDOW.setProperty("SkinHelper.ignoretitles",ignoretitles)
        artwork = artworkutils.getPVRThumbs(title,channel,type,path,genre,year,ignoreCache=True, manualLookup=False)
    elif ret == 5:
        #Open addon settings
        xbmc.executebuiltin("Addon.OpenSettings(script.skin.helper.service)")
        
    #flush properties and set new ones (if any)
    if artwork or ret==3 or ret==4:
        xbmc.sleep(150)
        WINDOW.setProperty("resetPvrArtCache","reset")
        WINDOW.clearProperty("SkinHelper.PVR.Thumb") 
        WINDOW.clearProperty("SkinHelper.PVR.FanArt") 
        WINDOW.clearProperty("SkinHelper.PVR.ChannelLogo")
        WINDOW.clearProperty("SkinHelper.PVR.Poster")
        WINDOW.clearProperty("SkinHelper.PVR.Landscape")
        WINDOW.clearProperty("SkinHelper.PVR.ClearArt")
        WINDOW.clearProperty("SkinHelper.PVR.CharacterArt") 
        WINDOW.clearProperty("SkinHelper.PVR.ClearLogo")
        WINDOW.clearProperty("SkinHelper.PVR.Banner")
        WINDOW.clearProperty("SkinHelper.PVR.DiscArt")
        WINDOW.clearProperty("SkinHelper.PVR.Plot")
        WINDOW.clearProperty("SkinHelper.PVR.Channel")
        WINDOW.clearProperty("SkinHelper.PVR.Genre")
        WINDOW.clearProperty("SkinHelper.PVR.ExtraFanArt")
        #set new properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.PVR." + key,value)
    WINDOW.clearProperty("artworkcontextmenu")

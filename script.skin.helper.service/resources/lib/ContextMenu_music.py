# -*- coding: utf-8 -*-
from Utils import *
import ArtworkUtils as artworkutils

#Kodi contextmenu item to configure the artwork 
if __name__ == '__main__':
    
    ##### Music Artwork ########
    
    logMsg("Context menu artwork settings for PVR artwork",0)
    WINDOW.setProperty("artworkcontextmenu", "busy")
    options=[]
    options.append(ADDON.getLocalizedString(32144)) #Refresh item (auto lookup)
    options.append(ADDON.getLocalizedString(32157)) #cache all artwork
    options.append(ADDON.getLocalizedString(32126)) #Reset Cache
    options.append(ADDON.getLocalizedString(32148)) #Open addon settings
    header = ADDON.getLocalizedString(32143) + " - " + ADDON.getLocalizedString(32122)
    ret = xbmcgui.Dialog().select(header, options)
    if ret == 0:
        #refresh item
        artwork = artworkutils.getMusicArtwork(xbmc.getInfoLabel("ListItem.Artist").decode('utf-8'),xbmc.getInfoLabel("ListItem.Album").decode('utf-8'),xbmc.getInfoLabel("ListItem.Title").decode('utf-8'),ignoreCache=True)
        
        #clear properties
        WINDOW.clearProperty("SkinHelper.Music.Banner") 
        WINDOW.clearProperty("SkinHelper.Music.ClearLogo") 
        WINDOW.clearProperty("SkinHelper.Music.DiscArt")
        WINDOW.clearProperty("SkinHelper.Music.FanArt")
        WINDOW.clearProperty("SkinHelper.Music.Thumb")
        WINDOW.clearProperty("SkinHelper.Music.Info")
        WINDOW.clearProperty("SkinHelper.Music.TrackList")
        WINDOW.clearProperty("SkinHelper.Music.SongCount")
        WINDOW.clearProperty("SkinHelper.Music.albumCount")
        WINDOW.clearProperty("SkinHelper.Music.AlbumList")
        WINDOW.clearProperty("SkinHelper.Music.ExtraFanArt")
        
        #set new properties
        for key, value in artwork.iteritems():
            WINDOW.setProperty("SkinHelper.Music." + key,value)
    
    if ret == 1:
        #cache all artwork
        ret = xbmcgui.Dialog().yesno(heading=ADDON.getLocalizedString(32157), line1=ADDON.getLocalizedString(32158))
        if ret:
            artworkutils.preCacheAllMusicArt(skipOnCache=True)
    
    if ret == 2:
        #Reset cache
        xbmc.executebuiltin("RunScript(script.skin.helper.service,action=RESETCACHE,path=music)")
    
    if ret == 3:
        #Open addon settings
        xbmc.executebuiltin("Addon.OpenSettings(script.skin.helper.service)")
    
    WINDOW.clearProperty("artworkcontextmenu")
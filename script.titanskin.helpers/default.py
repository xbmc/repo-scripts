import xbmcplugin
import xbmcgui
import shutil
import xbmcaddon
import os
import time

def setHomeItems(curPoslabel, idToChange, moveDirection):

    win = xbmcgui.Window( 10000 )
    
    curPosId = int(curPoslabel.split("-")[1]);
    nextPosId = curPosId +1
    prevPosId = curPosId -1    

    curItemId = int(xbmc.getInfoLabel("Skin.String(HomeMenuPos-" + str(curPosId) + ")"))
    nextItemId = int(xbmc.getInfoLabel("Skin.String(HomeMenuPos-" + str(nextPosId) + ")"))
    prevItemId = int(xbmc.getInfoLabel("Skin.String(HomeMenuPos-" + str(prevPosId) + ")"))
    
    curWinPos = int(win.getProperty("CurrentPos"))
    
    if (moveDirection == "DOWN"):
        if curPosId != 0:
            xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(curPosId) + "," + str(prevItemId) + ")")
            xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(prevPosId) + "," + str(curItemId) + ")")
            curWinPos = curWinPos -1
        
    if (moveDirection == "UP"):
        if curPosId != 45:
            xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(curPosId) + "," + str(nextItemId) + ")")
            xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(nextPosId) + "," + str(curItemId) + ")")
            curWinPos = curWinPos +1
    
    xbmc.executebuiltin('xbmc.ReloadSkin')
    xbmc.executebuiltin('Control.SetFocus(100,2)')
    xbmc.executebuiltin('Control.SetFocus(300, ' + str(curWinPos) + ')')    


def setView(containerType,viewId):
    
    if viewId=="00":
        curView = xbmc.getInfoLabel("Container.Viewmode")
        if curView == "Showcase":
            viewId="51"
        if curView == "Panel details":
            viewId="53"  
        if curView == "Showcase Details":
            viewId="54"
        if curView == "Panel":
            viewId="52"
        if curView == "Titan Banner details":
            viewId="505"
        if curView == "Banner list":
            viewId="55"
        if curView == "Extended":
            viewId="506"           
        if curView == "Banner Plex":
            viewId="56"
        if curView == "Titan Banner":
            viewId="501"
        if curView == "list":
            viewId="50"
    else:
        viewId=viewId    
      
    if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' + containerType, viewId)
        
    if xbmc.getCondVisibility("System.HasAddon(plugin.video.netflixbmc)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.netflixbmc')
        
        if containerType=="MOVIES":
            __settings__.setSetting('viewIdVideos', viewId)
        elif containerType=="SERIES":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        elif containerType=="SEASONS":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        elif containerType=="EPISODES":
            __settings__.setSetting('viewIdEpisodesNew', viewId)
        else:
            __settings__.setSetting('viewIdActivity', viewId) 
        
        #xbmc.executebuiltin("Container.Refresh")
    

def showSubmenu(showOrHide,doFocus):

    win = xbmcgui.Window( 10000 )
    submenu = win.getProperty("submenutype")
    submenuloading = ""
    if xbmc.getCondVisibility("Skin.HasSetting(AutoShowSubmenu)"):
        submenuloading = win.getProperty("submenuloading")
        
    # SHOW SUBMENU    
    if showOrHide == "SHOW":
        if submenuloading != "loading":
            if submenu != "":
                win.setProperty("submenu", "show")
                if doFocus != None:
                    xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
                    time.sleep(0.2)
                    xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')
            else:
                win.setProperty("submenu", "hide")
        else:
            win.setProperty("submenuloading", "")
    
    #HIDE SUBMENU
    elif showOrHide == "HIDE":
        win.setProperty("submenuloading", "loading")
        win.setProperty("submenu", "hide")
        if doFocus != None:
            time.sleep(0.8)
            xbmc.executebuiltin('Control.SetFocus('+ doFocus +',0)')


   

        
#script init
action = ""
argument1 = ""
argument2 = ""
argument3 = ""

# get arguments
try:
    action = str(sys.argv[1])
except: 
    pass

try:
    argument1 = str(sys.argv[2])
except: 
    pass
   
try:
    argument2 = str(sys.argv[3])
except: 
    pass

try:
    argument3 = str(sys.argv[4])
except: 
    pass  

# select action
if action == "SETHOMEITEMS":
    setHomeItems(argument1, argument2, argument3)
elif action == "SETVIEW":
    setView(argument1, argument2)
elif action == "RESTORE":
    restoreHomeItems()
elif action == "SHOWSUBMENU":
    showSubmenu(argument1,argument2)
else:
    xbmc.executebuiltin("Notification(Titan Mediabrowser,you can not run this script directly)") 
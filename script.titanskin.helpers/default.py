import xbmcplugin
import xbmcgui
import shutil
import xbmcaddon
import os

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
        xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(curPosId) + "," + str(prevItemId) + ")")
        xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(prevPosId) + "," + str(curItemId) + ")")
        curWinPos = curWinPos -1
        
    if (moveDirection == "UP"):
        xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(curPosId) + "," + str(nextItemId) + ")")
        xbmc.executebuiltin("Skin.SetString(HomeMenuPos-" + str(nextPosId) + "," + str(curItemId) + ")")
        curWinPos = curWinPos +1
    
    xbmc.executebuiltin('xbmc.ReloadSkin')
    xbmc.executebuiltin('Control.SetFocus(100,4)')
    xbmc.executebuiltin('Control.SetFocus(300, ' + str(curWinPos) + ')')    


def setView(viewId, containerType):
    
    if xbmc.getCondVisibility("System.HasAddon(plugin.video.xbmb3c)"):
        __settings__ = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        
        __settings__.setSetting(xbmc.getSkinDir()+ '_VIEW_' + viewId, containerType)
        xbmc.executebuiltin("Container.Refresh")     

  
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
else:
    xbmc.executebuiltin("Notification(Titan Mediabrowser,you can not run this script directly)") 
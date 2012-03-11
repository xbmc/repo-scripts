import xbmc
import xbmcaddon
import xbmcgui
from service import AutoUpdater
addon_id = "service.libraryautoupdate"
Addon = xbmcaddon.Addon(addon_id)

autoUpdate = AutoUpdater()

nextRun = autoUpdate.calcNextRun()
#check if we should run updates
runUpdate = xbmcgui.Dialog().yesno(Addon.getLocalizedString(30010),Addon.getLocalizedString(30011) + nextRun,Addon.getLocalizedString(30012))

if(runUpdate):
    #run the program
    xbmc.log("Update Library Manual Run...")
    autoUpdate.runUpdates()

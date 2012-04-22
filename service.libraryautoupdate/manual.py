import xbmc
import xbmcaddon
import xbmcgui
from service import AutoUpdater
addon_id = "service.libraryautoupdate"
Addon = xbmcaddon.Addon(addon_id)

autoUpdate = AutoUpdater()

nextRun = autoUpdate.showNotify(False)
#check if we should run updates
runUpdate = xbmcgui.Dialog().yesno(Addon.getLocalizedString(30010),Addon.getLocalizedString(30011) + nextRun,Addon.getLocalizedString(30012))

if(runUpdate):
    #run the program
    autoUpdate.log("Update Library Manual Run...")

    #trick the auto updater into resetting the last_run time
    autoUpdate.last_run = 0
    autoUpdate.writeLastRun()

    #update the schedules and evaluate them
    autoUpdate.createSchedules(True)
    autoUpdate.evalSchedules()

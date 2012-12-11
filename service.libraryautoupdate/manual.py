import xbmcgui
import resources.lib.utils as utils
from service import AutoUpdater

autoUpdate = AutoUpdater()

nextRun = autoUpdate.showNotify(False)
#check if we should run updates
runUpdate = xbmcgui.Dialog().yesno(utils.getString(30000),utils.getString(30060) + nextRun,utils.getString(30061))

if(runUpdate):
    #run the program
    utils.log("Update Library Manual Run...")

    #trick the auto updater into resetting the last_run time
    autoUpdate.last_run = 0
    autoUpdate.writeLastRun()

    #update the schedules and evaluate them
    autoUpdate.createSchedules(True)
    autoUpdate.evalSchedules()

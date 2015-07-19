import xbmcgui
import resources.lib.utils as utils
from service import AutoUpdater

autoUpdate = AutoUpdater()
runUpdate = False

if(utils.getSetting('disable_manual_prompt') == 'false'):
    nextRun = autoUpdate.showNotify(False)
    #check if we should run updates
    runUpdate = xbmcgui.Dialog().yesno(utils.getString(30000),utils.getString(30060) + nextRun,line2=utils.getString(30061),autoclose=6000)
else:
    #the user has elected to skip the prompt
    runUpdate = True

if(runUpdate):
    #run the program
    utils.log("Update Library Manual Run...")

    #trick the auto updater into resetting the last_run time
    autoUpdate.last_run = 0
    autoUpdate.writeLastRun()

    #update the schedules and evaluate them
    autoUpdate.createSchedules(True)
    autoUpdate.evalSchedules()

    #delete the monitor before exiting
    del autoUpdate.monitor

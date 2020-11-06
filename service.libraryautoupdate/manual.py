from kodi_six import xbmcgui
import resources.lib.utils as utils
from resources.lib.service import AutoUpdater

autoUpdate = AutoUpdater()
runUpdate = False

if(not utils.getSettingBool('disable_manual_prompt')):
    nextRun = autoUpdate.showNotify(False)
    # check if we should run updates
    runUpdate = xbmcgui.Dialog().yesno(utils.getString(30000), "%s %s \n %s" % (utils.getString(30060), nextRun, utils.getString(30061)), autoclose=6000)
else:
    # the user has elected to skip the prompt
    runUpdate = True

if(runUpdate):
    # run the program
    utils.log("Update Library Manual Run...")

    # trick the auto updater into resetting the last_run time
    autoUpdate.last_run = 0
    autoUpdate.writeLastRun()

    # update the schedules and evaluate them in manual override mode
    autoUpdate.createSchedules(True)
    autoUpdate.evalSchedules(True)

    # delete the monitor before exiting
    del autoUpdate.monitor

import xbmc
import xbmcgui
import resources.lib.utils as utils
from resources.lib.backup import XbmcBackup


def get_params():
    param = {}
    try:
        for i in sys.argv:
            args = i
            if('=' in args):
                if(args.startswith('?')):
                    args = args[1:]  # legacy in case of url params
                splitString = args.split('=')
                param[splitString[0]] = splitString[1]
    except:
        pass

    return param


# the program mode
mode = -1
params = get_params()


if("mode" in params):
    if(params['mode'] == 'backup'):
        mode = 0
    elif(params['mode'] == 'restore'):
        mode = 1


# if mode wasn't passed in as arg, get from user
if(mode == -1):
    # by default, Backup,Restore,Open Settings
    options = [utils.getString(30016), utils.getString(30017), utils.getString(30099)]

    # find out if we're using the advanced editor
    if(utils.getSettingInt('backup_selection_type') == 1):
        options.append(utils.getString(30125))

    # figure out if this is a backup or a restore from the user
    mode = xbmcgui.Dialog().select(utils.getString(30010) + " - " + utils.getString(30023), options)

# check if program should be run
if(mode != -1):
    # run the profile backup
    backup = XbmcBackup()

    if(mode == 2):
        # open the settings dialog
        utils.openSettings()
    elif(mode == 3 and utils.getSettingInt('backup_selection_type') == 1):
        # open the advanced editor
        xbmc.executebuiltin('RunScript(special://home/addons/script.xbmcbackup/launcher.py, action=advanced_editor)')
    elif(backup.remoteConfigured()):

        if(mode == backup.Restore):
            # get list of valid restore points
            restorePoints = backup.listBackups()
            pointNames = []
            folderNames = []

            for aDir in restorePoints:
                pointNames.append(aDir[1])
                folderNames.append(aDir[0])

            selectedRestore = -1

            if("archive" in params):
                # check that the user give archive exists
                if(params['archive'] in folderNames):
                    # set the index
                    selectedRestore = folderNames.index(params['archive'])
                    utils.log(str(selectedRestore) + " : " + params['archive'])
                else:
                    utils.showNotification(utils.getString(30045))
                    utils.log(params['archive'] + ' is not a valid restore point')
            else:
                # allow user to select the backup to restore from
                selectedRestore = xbmcgui.Dialog().select(utils.getString(30010) + " - " + utils.getString(30021), pointNames)

            if(selectedRestore != -1):
                backup.selectRestore(restorePoints[selectedRestore][0])

            if('sets' in params):
                backup.restore(selectedSets=params['sets'].split('|'))
            else:
                backup.restore()
        else:
            backup.backup()
    else:
        # can't go any further
        xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30045))
        utils.openSettings()

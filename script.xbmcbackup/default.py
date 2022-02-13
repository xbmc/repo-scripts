import xbmcgui
import xbmcvfs
import resources.lib.utils as utils
from resources.lib.backup import XbmcBackup
from resources.lib.authorizers import DropboxAuthorizer
from resources.lib.advanced_editor import AdvancedBackupEditor

# mode constants
BACKUP = 0
RESTORE = 1
SETTINGS = 2
ADVANCED_EDITOR = 3
LAUNCHER = 4


def authorize_cloud(cloudProvider):
    # dropbox
    if(cloudProvider == 'dropbox'):
        authorizer = DropboxAuthorizer()

        if(authorizer.authorize()):
            xbmcgui.Dialog().ok(utils.getString(30010), '%s %s' % (utils.getString(30027), utils.getString(30106)))
        else:
            xbmcgui.Dialog().ok(utils.getString(30010), '%s %s' % (utils.getString(30107), utils.getString(30027)))


def remove_auth():
    # triggered from settings.xml - asks if user wants to delete OAuth token information
    shouldDelete = xbmcgui.Dialog().yesno(utils.getString(30093), '%s\n%s' % (utils.getString(30094), utils.getString(30095)), autoclose=7000)

    if(shouldDelete):
        # delete any of the known token file types
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "tokens.txt"))  # dropbox
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "google_drive.dat"))  # google drive


def get_params():
    param = {}
    try:
        for i in sys.argv:
            args = i
            if('=' in args):
                if(args.startswith('?')):
                    args = args[1:]  # legacy in case of url params
                splitString = args.split('=')
                utils.log(splitString[1])
                param[splitString[0]] = splitString[1]
    except:
        pass

    return param


# the program mode
mode = -1
params = get_params()

if("mode" in params):
    if(params['mode'] == 'backup'):
        mode = BACKUP
    elif(params['mode'] == 'restore'):
        mode = RESTORE
    elif(params['mode'] == 'launcher'):
        mode = LAUNCHER

# if mode wasn't passed in as arg, get from user
if(mode == -1):
    # by default, Backup,Restore,Open Settings
    options = [utils.getString(30016), utils.getString(30017), utils.getString(30099)]

    # find out if we're using the advanced editor
    if(utils.getSettingInt('backup_selection_type') == 1):
        options.append(utils.getString(30125))

    # figure out if this is a backup or a restore from the user
    mode = xbmcgui.Dialog().select(utils.getString(30010) + " - " + utils.getString(30023), options)

# check which mode should be run
if(mode != -1):

    if(mode == SETTINGS):
        # open the settings dialog
        utils.openSettings()
    elif(mode == ADVANCED_EDITOR and utils.getSettingInt('backup_selection_type') == 1):
        # open the advanced editor but only if in advanced mode
        editor = AdvancedBackupEditor()
        editor.showMainScreen()
    elif(mode == LAUNCHER):
        # copied from old launcher.py
        if(params['action'] == 'authorize_cloud'):
            authorize_cloud(params['provider'])
        elif(params['action'] == 'remove_auth'):
            remove_auth()
        elif(params['action'] == 'advanced_editor'):
            editor = AdvancedBackupEditor()
            editor.showMainScreen()
        elif(params['action'] == 'advanced_copy_config'):
            editor = AdvancedBackupEditor()
            editor.copySimpleConfig()

    elif(mode == BACKUP or mode == RESTORE):
        backup = XbmcBackup()

        # if mode was RESTORE
        if(mode == RESTORE and backup.remoteConfigured()):
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
        elif(mode == BACKUP and backup.remoteConfigured()):
            # mode was BACKUP
            backup.backup()
        else:
            # can't go any further
            xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30045))
            utils.openSettings()
    else:
        xbmcgui.Dialog().ok(utils.getString(30010), "%s %s" % (utils.getString(30159), params['mode']))

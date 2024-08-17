from __future__ import unicode_literals
import time
import json
import xbmc
import xbmcgui
import xbmcvfs
import os.path
from . import utils as utils
from datetime import datetime
from . vfs import XBMCFileSystem, DropboxFileSystem, ZipFileSystem
from . progressbar import BackupProgressBar
from resources.lib.guisettings import GuiSettingsManager
from resources.lib.extractor import ZipExtractor


def folderSort(aKey):
    result = aKey[0]

    if(len(result) < 8):
        result = result + "0000"

    return result


class XbmcBackup:
    # constants for initiating a back or restore
    Backup = 0
    Restore = 1

    ZIP_TEMP_PATH = None

    # list of dirs for the "simple" file selection
    simple_directory_list = ['addons', 'addon_data', 'database', 'game_saves', 'playlists', 'profiles', 'thumbnails', 'config']

    # file systems
    xbmc_vfs = None
    remote_vfs = None
    saved_remote_vfs = None

    restoreFile = None
    remote_base_path = None

    # for the progress bar
    progressBar = None
    transferSize = 0
    transferLeft = 0

    restore_point = None
    skip_advanced = False   # if we should check for the existance of advancedsettings in the restore

    def __init__(self):
        self.xbmc_vfs = XBMCFileSystem(xbmcvfs.translatePath('special://home'))
        self.ZIP_TEMP_PATH = xbmcvfs.translatePath(utils.getSetting('zip_temp_path'))

        self.configureRemote()
        utils.log(utils.getString(30046))

    def configureRemote(self):
        if(utils.getSetting('remote_selection') == '1'):
            self.remote_vfs = XBMCFileSystem(utils.getSetting('remote_path_2'))
            utils.setSetting("remote_path", "")
        elif(utils.getSetting('remote_selection') == '0'):
            self.remote_vfs = XBMCFileSystem(utils.getSetting("remote_path"))
        elif(utils.getSetting('remote_selection') == '2'):
            self.remote_vfs = DropboxFileSystem("/")

        self.remote_base_path = self.remote_vfs.root_path

    def remoteConfigured(self):
        result = True

        if(self.remote_base_path == "" or not xbmcvfs.exists(self.ZIP_TEMP_PATH)):
            result = False

        return result

    # reverse - should reverse the resulting, default is true - newest to oldest
    def listBackups(self, reverse=True):
        result = []

        # get all the folders in the current root path
        dirs, files = self.remote_vfs.listdir(self.remote_base_path)

        for aDir in dirs:
            if(self.remote_vfs.exists(self.remote_base_path + aDir + "/xbmcbackup.val")):

                # format the name according to regional settings
                folderName = self._dateFormat(aDir)

                result.append((aDir, folderName))

        for aFile in files:
            file_ext = aFile.split('.')[-1]
            folderName = aFile.split('.')[0]

            if(file_ext == 'zip' and len(folderName) >= 12 and folderName[0:12].isdigit()):

                # format the name according to regional settings and display the file size
                folderName = "%s - %s" % (self._dateFormat(folderName), utils.diskString(self.remote_vfs.fileSize(self.remote_base_path + aFile)))

                result.append((aFile, folderName))

        result.sort(key=folderSort, reverse=reverse)

        return result

    def selectRestore(self, restore_point):
        self.restore_point = restore_point

    def skipAdvanced(self):
        self.skip_advanced = True

    def backup(self, progressOverride=False):
        shouldContinue = self._setupVFS(self.Backup, progressOverride)

        if(shouldContinue):
            utils.log(utils.getString(30023) + " - " + utils.getString(30016))
            # check if remote path exists
            if(self.remote_vfs.exists(self.remote_vfs.root_path)):
                # may be data in here already
                utils.log(utils.getString(30050))
            else:
                # make the remote directory
                self.remote_vfs.mkdir(self.remote_vfs.root_path)

            utils.log(utils.getString(30051))
            utils.log('File Selection Type: ' + str(utils.getSetting('backup_selection_type')))
            allFiles = []

            if(utils.getSettingInt('backup_selection_type') == 0):
                # read in a list of the directories to backup
                selectedDirs = self._readBackupConfig(utils.addon_dir() + "/resources/data/default_files.json")

                # simple mode - get file listings for all enabled directories
                for aDir in self.simple_directory_list:
                    # if this dir enabled
                    if(utils.getSettingBool('backup_' + aDir)):
                        # get a file listing and append it to the allfiles array
                        allFiles.append(self._addBackupDir(aDir, selectedDirs[aDir]['root'], selectedDirs[aDir]['dirs']))
            else:
                # advanced mode - load custom paths
                selectedDirs = self._readBackupConfig(utils.data_dir() + "/custom_paths.json")

                # get the set names
                keys = list(selectedDirs.keys())

                # go through the custom sets
                for aKey in keys:
                    # get the set
                    aSet = selectedDirs[aKey]

                    # get file listing and append
                    allFiles.append(self._addBackupDir(aKey, aSet['root'], aSet['dirs']))

            # create a validation file for backup rotation
            writeCheck = self._createValidationFile(allFiles)

            if(not writeCheck):
                # we may not be able to write to this destination for some reason
                shouldContinue = xbmcgui.Dialog().yesno(utils.getString(30089), "%s\n%s" % (utils.getString(30090), utils.getString(30044)), autoclose=25000)

                if(not shouldContinue):
                    return

            orig_base_path = self.remote_vfs.root_path

            # backup all the files
            self.transferLeft = self.transferSize
            for fileGroup in allFiles:
                self.xbmc_vfs.set_root(xbmcvfs.translatePath(fileGroup['source']))
                self.remote_vfs.set_root(fileGroup['dest'] + fileGroup['name'])
                filesCopied = self._copyFiles(fileGroup['files'], self.xbmc_vfs, self.remote_vfs)

                if(not filesCopied):
                    utils.showNotification(utils.getString(30092))
                    utils.log(utils.getString(30092))

            # reset remote and xbmc vfs
            self.xbmc_vfs.set_root("special://home/")
            self.remote_vfs.set_root(orig_base_path)

            if(utils.getSettingBool("compress_backups")):
                fileManager = FileManager(self.xbmc_vfs)

                # send the zip file to the real remote vfs
                zip_name = os.path.join(self.ZIP_TEMP_PATH, self.remote_vfs.root_path[:-1] + ".zip")
                self.remote_vfs.cleanup()
                self.xbmc_vfs.rename(os.path.join(self.ZIP_TEMP_PATH, "xbmc_backup_temp.zip"), zip_name)
                fileManager.addFile(zip_name)

                # set root to data dir home and reset remote
                self.xbmc_vfs.set_root(self.ZIP_TEMP_PATH)
                self.remote_vfs = self.saved_remote_vfs

                # update the amount to transfer
                self.transferSize = fileManager.fileSize()
                self.transferLeft = self.transferSize
                fileCopied = self._copyFiles(fileManager.getFiles(), self.xbmc_vfs, self.remote_vfs)

                if(not fileCopied):
                    # zip archive copy filed, inform the user
                    shouldContinue = xbmcgui.Dialog().ok(utils.getString(30089), '%s\n%s' % (utils.getString(30090), utils.getString(30091)))

                # delete the temp zip file
                self.xbmc_vfs.rmfile(zip_name)

            # remove old backups
            self._rotateBackups()

            # close any files
            self._closeVFS()

    def restore(self, progressOverride=False, selectedSets=None):
        shouldContinue = self._setupVFS(self.Restore, progressOverride)

        if(shouldContinue):
            utils.log(utils.getString(30023) + " - " + utils.getString(30017))

            # catch for if the restore point is actually a zip file
            if(self.restore_point.split('.')[-1] == 'zip'):
                self.progressBar.updateProgress(2, utils.getString(30088))
                utils.log("copying zip file: " + self.restore_point)

                # set root to data dir home
                self.xbmc_vfs.set_root(self.ZIP_TEMP_PATH)
                restore_path = os.path.join(self.ZIP_TEMP_PATH, self.restore_point)
                if(not self.xbmc_vfs.exists(restore_path)):
                    # copy just this file from the remote vfs
                    self.transferSize = self.remote_vfs.fileSize(self.remote_base_path + self.restore_point)
                    zipFile = []
                    zipFile.append({'file': self.remote_base_path + self.restore_point, 'size': self.transferSize, 'is_dir': False})

                    # set transfer size
                    self.transferLeft = self.transferSize
                    self._copyFiles(zipFile, self.remote_vfs, self.xbmc_vfs)
                else:
                    utils.log("zip file exists already")

                # extract the zip file
                zip_vfs = ZipFileSystem(restore_path, 'r')
                extractor = ZipExtractor()

                if(not extractor.extract(zip_vfs, self.ZIP_TEMP_PATH, self.progressBar)):
                    # we had a problem extracting the archive, delete everything
                    zip_vfs.cleanup()
                    self.xbmc_vfs.rmfile(restore_path)

                    xbmcgui.Dialog().ok(utils.getString(30010), utils.getString(30101))
                    return

                zip_vfs.cleanup()

                self.progressBar.updateProgress(0, utils.getString(30049) + "......")
                # set the new remote vfs and fix xbmc path
                self.remote_vfs = XBMCFileSystem(os.path.join(self.ZIP_TEMP_PATH, self.restore_point.split(".")[0]))
                self.xbmc_vfs.set_root(xbmcvfs.translatePath("special://home/"))

            # for restores remote path must exist
            if(not self.remote_vfs.exists(self.remote_vfs.root_path)):
                xbmcgui.Dialog().ok(utils.getString(30010), '%s\n%s' % (utils.getString(30045), self.remote_vfs.root_path))
                return

            valFile = self._checkValidationFile(self.remote_vfs.root_path)
            if(valFile is None):
                # don't continue
                return

            utils.log(utils.getString(30051))
            allFiles = []
            fileManager = FileManager(self.remote_vfs)

            # check for the existance of an advancedsettings file
            if(self.remote_vfs.exists(self.remote_vfs.root_path + "config/advancedsettings.xml") and not self.skip_advanced):
                # let the user know there is an advanced settings file present
                restartXbmc = xbmcgui.Dialog().yesno(utils.getString(30038), "%s\n%s\n%s" % (utils.getString(30039), utils.getString(30040), utils.getString(30041)))

                if(restartXbmc):
                    # add only this file to the file list
                    self.transferSize = 1
                    self.transferLeft = 1
                    fileManager.addFile(self.remote_vfs.root_path + "config/advancedsettings.xml")
                    self._copyFiles(fileManager.getFiles(), self.remote_vfs, self.xbmc_vfs)

                    # let the service know to resume this backup on startup
                    self._createResumeBackupFile()

                    # do not continue running
                    if(xbmcgui.Dialog().yesno(utils.getString(30077), utils.getString(30078), autoclose=15000)):
                        xbmc.executebuiltin('Quit')

                    return

            # check if settings should be restored from this backup
            restoreSettings = not utils.getSettingBool('always_prompt_restore_settings')
            if(not restoreSettings and 'system_settings' in valFile):
                # prompt the user to restore settings yes/no
                restoreSettings = xbmcgui.Dialog().yesno(utils.getString(30149), utils.getString(30150))

            # use a multiselect dialog to select sets to restore
            restoreSets = [n['name'] for n in valFile['directories']]

            # if passed in list, skip selection
            if(selectedSets is None):
                selectedSets = xbmcgui.Dialog().multiselect(utils.getString(30131), restoreSets)
            else:
                selectedSets = [restoreSets.index(n) for n in selectedSets if n in restoreSets]  # if set name not found just skip it

            if(selectedSets is not None):

                # go through each of the directories in the backup and write them to the correct location
                for index in selectedSets:

                    # add this directory
                    aDir = valFile['directories'][index]

                    self.xbmc_vfs.set_root(xbmcvfs.translatePath(aDir['path']))
                    if(self.remote_vfs.exists(self.remote_vfs.root_path + aDir['name'] + '/')):
                        # walk the directory
                        self.progressBar.updateProgress(0, f"{utils.getString(30049)}....{utils.getString(30162)}\n{utils.getString(30163)}: {aDir['name']}")
                        fileManager.walkTree(self.remote_vfs.root_path + aDir['name'] + '/')
                        self.transferSize = self.transferSize + fileManager.fileSize()

                        allFiles.append({"source": self.remote_vfs.root_path + aDir['name'], "dest": self.xbmc_vfs.root_path, "files": fileManager.getFiles()})
                    else:
                        utils.log("error path not found: " + self.remote_vfs.root_path + aDir['name'])
                        xbmcgui.Dialog().ok(utils.getString(30010), '%s\n%s' % (utils.getString(30045), self.remote_vfs.root_path + aDir['name']))

                # restore all the files
                self.transferLeft = self.transferSize
                for fileGroup in allFiles:
                    self.remote_vfs.set_root(fileGroup['source'])
                    self.xbmc_vfs.set_root(fileGroup['dest'])
                    self._copyFiles(fileGroup['files'], self.remote_vfs, self.xbmc_vfs)

            # update the Kodi settings - if we can
            if('system_settings' in valFile and restoreSettings):
                self.progressBar.updateProgress(98, "Restoring Kodi settings")
                gui_settings = GuiSettingsManager()
                gui_settings.restore(valFile['system_settings'])

            self.progressBar.updateProgress(99, "Clean up operations .....")

            if(self.restore_point.split('.')[-1] == 'zip'):
                # delete the zip file and the extracted directory
                self.xbmc_vfs.rmfile(os.path.join(self.ZIP_TEMP_PATH, self.restore_point))
                xbmc.sleep(1000)
                self.xbmc_vfs.rmdir(self.remote_vfs.clean_path(os.path.join(self.ZIP_TEMP_PATH, self.restore_point.split(".")[0])))
                xbmc.sleep(1000)

            # call update addons to refresh everything
            xbmc.executebuiltin('UpdateLocalAddons')

            # notify user that restart is recommended
            if(xbmcgui.Dialog().yesno(utils.getString(30077), utils.getString(30078), autoclose=15000)):
                xbmc.executebuiltin('Quit')


    def _setupVFS(self, mode=-1, progressOverride=False):
        # set windows setting to true
        window = xbmcgui.Window(10000)
        window.setProperty(utils.__addon_id__ + ".running", "true")

        # append backup folder name
        progressBarTitle = utils.getString(30010) + " - "
        if(mode == self.Backup and self.remote_vfs.root_path != ''):
            if(utils.getSettingBool("compress_backups")):
                # delete old temp file
                zip_path = os.path.join(self.ZIP_TEMP_PATH, 'xbmc_backup_temp.zip')
                if(self.xbmc_vfs.exists(zip_path)):
                    if(not self.xbmc_vfs.rmfile(zip_path)):
                        # we had some kind of error deleting the old file
                        xbmcgui.Dialog().ok(utils.getString(30010), '%s\n%s' % (utils.getString(30096), utils.getString(30097)))
                        return False

                # save the remote file system and use the zip vfs
                self.saved_remote_vfs = self.remote_vfs
                self.remote_vfs = ZipFileSystem(zip_path, "w")

            self.remote_vfs.set_root(self.remote_vfs.root_path + time.strftime("%Y%m%d%H%M") + utils.getSetting('backup_suffix').strip() + "/")
            progressBarTitle = progressBarTitle + utils.getString(30023) + ": " + utils.getString(30016)
        elif(mode == self.Restore and self.restore_point is not None and self.remote_vfs.root_path != ''):
            if(self.restore_point.split('.')[-1] != 'zip'):
                self.remote_vfs.set_root(self.remote_vfs.root_path + self.restore_point + "/")
            progressBarTitle = progressBarTitle + utils.getString(30023) + ": " + utils.getString(30017)
        else:
            # kill the program here
            self.remote_vfs = None
            return False

        utils.log(utils.getString(30047) + ": " + self.xbmc_vfs.root_path)
        utils.log(utils.getString(30048) + ": " + self.remote_vfs.root_path)
        utils.log(utils.getString(30152) + ": " + utils.getSetting('zip_temp_path'))

        # setup the progress bar
        self.progressBar = BackupProgressBar(progressOverride)
        self.progressBar.create(progressBarTitle, utils.getString(30049) + "......")

        # if we made it this far we're good
        return True

    def _closeVFS(self):
        self.xbmc_vfs.cleanup()
        self.remote_vfs.cleanup()
        self.progressBar.close()

        # reset the window setting
        window = xbmcgui.Window(10000)
        window.setProperty(utils.__addon_id__ + ".running", "")

    def _copyFiles(self, fileList, source, dest):
        result = True

        utils.log("Source: " + source.root_path)
        utils.log("Destination: " + dest.root_path)

        # make sure the dest folder exists - can cause write errors if the full path doesn't exist
        if(not dest.exists(dest.root_path)):
            dest.mkdir(dest.root_path)

        for aFile in fileList:
            if(not self.progressBar.checkCancel()):
                if(utils.getSettingBool('verbose_logging')):
                    utils.log('Writing file: ' + aFile['file'])

                if(aFile['is_dir']):
                    self._updateProgress('%s remaining\nwriting %s' % (utils.diskString(self.transferLeft), os.path.basename(aFile['file'][len(source.root_path):]) + "/"))
                    dest.mkdir(dest.root_path + aFile['file'][len(source.root_path):])
                else:
                    self._updateProgress('%s remaining\nwriting %s' % (utils.diskString(self.transferLeft), os.path.basename(aFile['file'][len(source.root_path):])))
                    self.transferLeft = self.transferLeft - aFile['size']

                    # copy the file
                    wroteFile = self._copyFile(source, dest, aFile['file'], dest.root_path + aFile['file'][len(source.root_path):])

                    # if result is still true but this file failed
                    if(not wroteFile and result):
                        utils.log("Failed to write " + aFile['file'])
                        result = False

        return result

    def _copyFile(self, source, dest, sourceFile, destFile):
        result = True

        if(isinstance(source, DropboxFileSystem)):
            # if copying from cloud storage we need the file handle, use get_file
            result = source.get_file(sourceFile, destFile)
        else:
            # copy using normal method
            result = dest.put(sourceFile, destFile)

        return result

    def _addBackupDir(self, folder_name, root_path, dirList):
        utils.log('Backup set: ' + folder_name)
        fileManager = FileManager(self.xbmc_vfs)

        self.xbmc_vfs.set_root(xbmcvfs.translatePath(root_path))
        for aDir in dirList:
            fileManager.addDir(aDir)

        # walk all the root trees
        fileManager.walk()

        # update total size
        self.transferSize = self.transferSize + fileManager.fileSize()

        return {"name": folder_name, "source": root_path, "dest": self.remote_vfs.root_path, "files": fileManager.getFiles()}

    def _dateFormat(self, dirName):
        # create date_time object from foldername YYYYMMDDHHmm
        date_time = datetime(int(dirName[0:4]), int(dirName[4:6]), int(dirName[6:8]), int(dirName[8:10]), int(dirName[10:12]))

        # format the string based on region settings
        result = utils.getRegionalTimestamp(date_time, ['dateshort', 'time'])

        return result

    def _updateProgress(self, message=None):
        self.progressBar.updateProgress(int((float(self.transferSize - self.transferLeft) / float(self.transferSize)) * 100), message)

    def _rotateBackups(self):
        total_backups = utils.getSettingInt('backup_rotation')

        if(total_backups > 0):
            # get a list of valid backup folders
            dirs = self.listBackups(reverse=False)

            if(len(dirs) > total_backups):
                # remove backups to equal total wanted
                remove_num = 0

                # update the progress bar if it is available
                while(remove_num < (len(dirs) - total_backups) and not self.progressBar.checkCancel()):
                    self._updateProgress(utils.getString(30054) + " " + dirs[remove_num][1])
                    utils.log("Removing backup " + dirs[remove_num][0])

                    if(dirs[remove_num][0].split('.')[-1] == 'zip'):
                        # this is a file, remove it that way
                        self.remote_vfs.rmfile(self.remote_vfs.clean_path(self.remote_base_path) + dirs[remove_num][0])
                    else:
                        self.remote_vfs.rmdir(self.remote_vfs.clean_path(self.remote_base_path) + dirs[remove_num][0] + "/")

                    remove_num = remove_num + 1

    def _createValidationFile(self, dirList):
        valInfo = {"name": "XBMC Backup Validation File", "xbmc_version": xbmc.getInfoLabel('System.BuildVersion'), "type": 0, "system_settings": [], "addons": []}
        valDirs = []

        # save list of file sets
        for aDir in dirList:
            valDirs.append({"name": aDir['name'], "path": aDir['source']})
        valInfo['directories'] = valDirs

        # dump all current Kodi settings
        gui_settings = GuiSettingsManager()
        valInfo['system_settings'] = gui_settings.backup()

        # save all currently installed addons
        valInfo['addons'] = gui_settings.list_addons()

        vFile = xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup.val"), 'w')
        vFile.write(json.dumps(valInfo))
        vFile.write("")
        vFile.close()

        success = self._copyFile(self.xbmc_vfs, self.remote_vfs, xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup.val"), self.remote_vfs.root_path + "xbmcbackup.val")

        # remove the validation file
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup.val"))

        if(success):
            # android requires a .nomedia file to not index the directory as media
            if(not xbmcvfs.exists(xbmcvfs.translatePath(utils.data_dir() + ".nomedia"))):
                nmFile = xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + ".nomedia"), 'w')
                nmFile.close()

            success = self._copyFile(self.xbmc_vfs, self.remote_vfs, xbmcvfs.translatePath(utils.data_dir() + ".nomedia"), self.remote_vfs.root_path + ".nomedia")

        return success

    def _checkValidationFile(self, path):
        result = None

        # copy the file and open it
        self._copyFile(self.remote_vfs, self.xbmc_vfs, path + "xbmcbackup.val", xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup_restore.val"))

        with xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup_restore.val"), 'r') as vFile:
            jsonString = vFile.read()

        # delete after checking
        xbmcvfs.delete(xbmcvfs.translatePath(utils.data_dir() + "xbmcbackup_restore.val"))

        try:
            result = json.loads(jsonString)

            if(xbmc.getInfoLabel('System.BuildVersion') != result['xbmc_version']):
                shouldContinue = xbmcgui.Dialog().yesno(utils.getString(30085), "%s\n%s" % (utils.getString(30086), utils.getString(30044)))

                if(not shouldContinue):
                    result = None

        except ValueError:
            # may fail on older archives
            result = None

        return result

    def _createResumeBackupFile(self):
        with xbmcvfs.File(xbmcvfs.translatePath(utils.data_dir() + "resume.txt"), 'w') as f:
            f.write(self.restore_point)

    def _readBackupConfig(self, aFile):
        with xbmcvfs.File(xbmcvfs.translatePath(aFile), 'r') as f:
            jsonString = f.read()
        return json.loads(jsonString)


class FileManager:
    not_dir = ['.zip', '.xsp', '.rar']
    exclude_dir = []
    root_dirs = []
    pathSep = '/'
    totalSize = 1

    def __init__(self, vfs):
        self.vfs = vfs
        self.fileArray = []
        self.exclude_dir = []
        self.root_dirs = []

    def walk(self):

        for aDir in self.root_dirs:
            self.addFile(xbmcvfs.translatePath(aDir['path']), True)
            self.walkTree(xbmcvfs.translatePath(aDir['path']), aDir['recurse'])

    def walkTree(self, directory, recurse=True):
        if(utils.getSettingBool('verbose_logging')):
            utils.log('walking ' + directory + ', recurse: ' + str(recurse))

        if(directory[-1:] == '/' or directory[-1:] == '\\'):
            directory = directory[:-1]

        if(self.vfs.exists(directory + self.pathSep)):
            dirs, files = self.vfs.listdir(directory)

            if(recurse):
                # create all the subdirs first
                for aDir in dirs:
                    dirPath = xbmcvfs.validatePath(xbmcvfs.translatePath(directory + self.pathSep + aDir))
                    file_ext = aDir.split('.')[-1]

                    # check if directory is excluded
                    if(not any(dirPath.startswith(exDir) for exDir in self.exclude_dir)):

                        self.addFile(dirPath, True)

                        # catch for "non directory" type files
                        shouldWalk = True

                        for s in file_ext:
                            if(s in self.not_dir):
                                shouldWalk = False

                        if(shouldWalk):
                            self.walkTree(dirPath)

            # copy all the files
            for aFile in files:
                filePath = xbmcvfs.translatePath(directory + self.pathSep + aFile)
                self.addFile(filePath)

    def addDir(self, dirMeta):
        if(dirMeta['type'] == 'include'):
            self.root_dirs.append({'path': dirMeta['path'], 'recurse': dirMeta['recurse']})
        else:
            self.excludeFile(xbmcvfs.translatePath(dirMeta['path']))

    def addFile(self, filename, is_dir = False):
        # write the full remote path name of this file
        if(utils.getSettingBool('verbose_logging')):
            utils.log("Add File: " + filename)

        # get the file size
        fSize = self.vfs.fileSize(filename)
        self.totalSize = self.totalSize + fSize

        self.fileArray.append({'file': filename, 'size': fSize, 'is_dir': is_dir})

    def excludeFile(self, filename):
        # remove trailing slash
        if(filename[-1] == '/' or filename[-1] == '\\'):
            filename = filename[:-1]

        # write the full remote path name of this file
        utils.log("Exclude File: " + filename)
        self.exclude_dir.append(filename)

    def getFiles(self):
        result = self.fileArray
        self.fileArray = []
        self.root_dirs = []
        self.exclude_dir = []
        self.totalSize = 0

        return result

    def totalFiles(self):
        return len(self.fileArray)

    def fileSize(self):
        return self.totalSize

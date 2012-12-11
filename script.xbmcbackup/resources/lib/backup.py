import xbmc
import xbmcgui
import xbmcvfs
import utils as utils
import os.path
import time
from vfs import XBMCFileSystem,DropboxFileSystem

class FileManager:
    fileArray = None
    verbose_log = False
    not_dir = ['.zip','.xsp','.rar']
    vfs = None
    
    def __init__(self,vfs):
        self.vfs = vfs
        
    def createFileList(self):
        self.fileArray = []
        self.verbose_log = utils.getSetting("verbose_log") == 'true'
       
        #figure out which syncing options to run
        if(utils.getSetting('backup_addons') == 'true'):
            self.addFile("-addons")
            self.walkTree(self.vfs.root_path + "addons/")

        self.addFile("-userdata")
        
        if(utils.getSetting('backup_addon_data') == 'true'):
            self.addFile("-userdata/addon_data")
            self.walkTree(self.vfs.root_path + "userdata/addon_data/")
           
        if(utils.getSetting('backup_database') == 'true'):
	    self.addFile("-userdata/Database")
            self.walkTree(self.vfs.root_path + "userdata/Database")
        
        if(utils.getSetting("backup_playlists") == 'true'):
	    self.addFile("-userdata/playlists")
	    self.walkTree(self.vfs.root_path + "userdata/playlists")
			
        if(utils.getSetting("backup_thumbnails") == "true"):
	    self.addFile("-userdata/Thumbnails")
	    self.walkTree(self.vfs.root_path + "userdata/Thumbnails")
		
        if(utils.getSetting("backup_config") == "true"):
            self.addFile("-userdata/keymaps")
            self.walkTree(self.vfs.root_path + "userdata/keymaps")

            self.addFile("-userdata/peripheral_data")
            self.walkTree(self.vfs.root_path + "userdata/peripheral_data")
            
	    #this part is an oddity
            dirs,configFiles = self.vfs.listdir(self.vfs.root_path + "userdata/")
	    for aFile in configFiles:
		if(aFile.endswith(".xml")):
		    self.addFile("userdata/" + aFile)
        
    def walkTree(self,directory):
        dirs,files = self.vfs.listdir(directory)
        
        #create all the subdirs first
        for aDir in dirs:
            dirPath = xbmc.translatePath(directory + "/" + aDir)
            file_ext = aDir.split('.')[-1]

            self.addFile("-" + dirPath[len(self.vfs.root_path):].decode("UTF-8"))  
            #catch for "non directory" type files
            if (not any(file_ext in s for s in self.not_dir)):
                self.walkTree(dirPath)  
            
        #copy all the files
        for aFile in files:
            filePath = xbmc.translatePath(directory + "/" + aFile)
            self.addFile(filePath[len(self.vfs.root_path):].decode("UTF-8"))
                    
    def addFile(self,filename):
        #write the full remote path name of this file
        utils.log("Add File: " + filename,xbmc.LOGDEBUG)
        self.fileArray.append(filename)

    def getFileList(self):
       return self.fileArray

class XbmcBackup:
    #constants for initiating a back or restore
    Backup = 0
    Restore = 1

    #remote file system
    local_vfs = None
    remote_vfs = None
    restoreFile = None
    
    #for the progress bar
    progressBar = None
    filesLeft = 0
    filesTotal = 1

    fileManager = None
    restore_point = None
    
    def __init__(self):
        self.local_vfs = XBMCFileSystem()
        self.local_vfs.set_root(xbmc.translatePath("special://home"))

        self.configureVFS()
        
        utils.log(utils.getString(30046))

    def configureVFS(self):
        if(utils.getSetting('remote_selection') == '1'):
            self.remote_vfs = XBMCFileSystem()
            self.remote_vfs.set_root(utils.getSetting('remote_path_2'))
	    utils.setSetting("remote_path","")
        elif(utils.getSetting('remote_selection') == '0'):
            self.remote_vfs = XBMCFileSystem()
            self.remote_vfs.set_root(utils.getSetting("remote_path"))
        elif(utils.getSetting('remote_selection') == '2'):
            self.remote_vfs = DropboxFileSystem()
            self.remote_vfs.set_root('/')

    def listBackups(self):
        result = list()

        #get all the folders in the current root path
        dirs,files = self.remote_vfs.listdir(self.remote_vfs.root_path)
        
        for aDir in dirs:
            result.append(aDir)

        return result

    def selectRestore(self,restore_point):
        self.restore_point = restore_point

    def run(self,mode=-1,runSilent=False):

        #append backup folder name
        remote_base_path = ""
        progressBarTitle = utils.getString(30010) + " - "
        if(mode == self.Backup and self.remote_vfs.root_path != ''):
            #capture base path for backup rotation
            remote_base_path = self.remote_vfs.set_root(self.remote_vfs.root_path + time.strftime("%Y%m%d") + "/")
            progressBarTitle = progressBarTitle + utils.getString(30016)
	elif(mode == self.Restore and self.restore_point != None and self.remote_vfs.root_path != ''):
	    self.remote_vfs.set_root(self.remote_vfs.root_path + self.restore_point + "/")
	    progressBarTitle = progressBarTitle + utils.getString(30017)
	else:
            #kill the program here
	    self.remote_vfs = None
	    return

        utils.log(utils.getString(30047) + ": " + self.local_vfs.root_path)
        utils.log(utils.getString(30048) + ": " + self.remote_vfs.root_path)

        #check if we should use the progress bar
        if(utils.getSetting('run_silent') == 'false' and not runSilent):
            self.progressBar = xbmcgui.DialogProgress()
            self.progressBar.create(progressBarTitle,utils.getString(30049) + "......")

        #run the correct mode
        if(mode == self.Backup):
            utils.log(utils.getString(30023) + " - " + utils.getString(30016))
            self.fileManager = FileManager(self.local_vfs)

            #for backups check if remote path exists
            if(self.remote_vfs.exists(self.remote_vfs.root_path)):
                #this will fail - need a disclaimer here
                utils.log(utils.getString(30050))

            self.syncFiles()

            #remove old backups
            total_backups = int(utils.getSetting('backup_rotation'))
            if(total_backups > 0):
                
                dirs,files = self.remote_vfs.listdir(remote_base_path)
                if(len(dirs) > total_backups):
                    #remove backups to equal total wanted
                    dirs.sort()
                    remove_num = len(dirs) - total_backups - 1
                    self.filesTotal = self.filesTotal + remove_num + 1

                    #update the progress bar if it is available
                    while(remove_num >= 0 and not self.checkCancel()):
                        self.updateProgress(utils.getString(30054) + " " + dirs[remove_num])
                        utils.log("Removing backup " + dirs[remove_num])
                        self.remote_vfs.rmdir(remote_base_path + dirs[remove_num] + "/")
                        remove_num = remove_num - 1
                        
                
        else:
            utils.log(utils.getString(30023) + " - " + utils.getString(30017))
            self.fileManager = FileManager(self.remote_vfs)

            #for restores remote path must exist
            if(self.remote_vfs.exists(self.remote_vfs.root_path)):
                self.restoreFiles()
            else:
                xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30045),self.remote_vfs.root_path)

        if(utils.getSetting('run_silent') == 'false' and not runSilent):
            self.progressBar.close()
        
    def syncFiles(self):
        
        #make the remote directory
        self.remote_vfs.mkdir(self.remote_vfs.root_path)

        utils.log(utils.getString(30051))
        self.fileManager.createFileList()

        allFiles = self.fileManager.getFileList()

        #write list from local to remote
        self.writeFiles(allFiles,self.local_vfs,self.remote_vfs)
        
    def restoreFiles(self):
        self.fileManager.createFileList()

        utils.log(utils.getString(30051))
        allFiles = self.fileManager.getFileList()

        #write list from remote to local
        self.writeFiles(allFiles,self.remote_vfs,self.local_vfs)

        #call update addons to refresh everything
        xbmc.executebuiltin('UpdateLocalAddons')
        
    def writeFiles(self,fileList,source,dest):
        utils.log("Writing files to: " + dest.root_path)
        self.filesTotal = len(fileList)
        self.filesLeft = self.filesTotal

        #write each file from source to destination
        for aFile in fileList:
            if(not self.checkCancel()):
                utils.log('Writing file: ' + source.root_path + aFile,xbmc.LOGDEBUG)
                self.updateProgress(aFile)
                if (aFile.startswith("-")):
                    dest.mkdir(dest.root_path + aFile[1:])
                else:
                    if(isinstance(source,DropboxFileSystem)):
                        #if copying from dropbox we need the file handle, use get_file
                        source.get_file(source.root_path + aFile,dest.root_path + aFile)
                    else:
                        #copy using normal method
                        dest.put(source.root_path + aFile,dest.root_path + aFile)

    def updateProgress(self,message=''):
        self.filesLeft = self.filesLeft - 1

        #update the progress bar
        if(self.progressBar != None):
            self.progressBar.update(int((float(self.filesTotal - self.filesLeft)/float(self.filesTotal)) * 100),message)
            
    def checkCancel(self):
        result = False

        if(self.progressBar != None):
            result = self.progressBar.iscanceled()

        return result

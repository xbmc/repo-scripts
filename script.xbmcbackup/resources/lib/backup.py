import xbmc
import xbmcgui
import vfs as vfs
import utils as utils
import os
import time

class FileManager:
    walk_path = ''
    fileArray = None
    verbose_log = False
    
    def __init__(self,path):
        self.walk_path = path

    def createFileList(self):
        self.fileArray = []
        self.verbose_log = utils.getSetting("verbose_log") == 'true'
       
        #figure out which syncing options to run
        if(utils.getSetting('backup_addons') == 'true'):
            self.addFile("-addons")
            self.walkTree(self.walk_path + "addons/")

        self.addFile("-userdata")
        
        if(utils.getSetting('backup_addon_data') == 'true'):
            self.addFile("-userdata/addon_data")
            self.walkTree(self.walk_path + "userdata/addon_data/")
           
        if(utils.getSetting('backup_database') == 'true'):
	    self.addFile("-userdata/Database")
            self.walkTree(self.walk_path + "userdata/Database")
        
        if(utils.getSetting("backup_playlists") == 'true'):
	    self.addFile("-userdata/playlists")
	    self.walkTree(self.walk_path + "userdata/playlists")
			
        if(utils.getSetting("backup_thumbnails") == "true"):
	    self.addFile("-userdata/Thumbnails")
	    self.walkTree(self.walk_path + "userdata/Thumbnails")
		
        if(utils.getSetting("backup_config") == "true"):
            self.addFile("-userdata/keymaps")
            self.walkTree(self.walk_path + "userdata/keymaps")

            self.addFile("-userdata/peripheral_data")
            self.walkTree(self.walk_path + "userdata/peripheral_data")
            
	    #this part is an oddity
            configFiles = vfs.listdir(self.walk_path + "userdata/",extra_metadata=True)
	    for aFile in configFiles:
		if(aFile['file'].endswith(".xml")):
		    self.addFile(aFile['file'][len(self.walk_path):])
        
    def walkTree(self,directory):
        for (path, dirs, files) in vfs.walk(directory):
            
            #create all the subdirs first
            for aDir in dirs:
                self.addFile("-" + aDir[len(self.walk_path):])
            #copy all the files
            for aFile in files:
                filePath = aFile[len(self.walk_path):]
                self.addFile(filePath)
                    
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
    
    local_path = ''
    remote_path = ''
    restoreFile = None
    
    #for the progress bar
    progressBar = None
    filesLeft = 0
    filesTotal = 1

    fileManager = None
    
    def __init__(self):
        self.local_path = xbmc.makeLegalFilename(xbmc.translatePath("special://home"),False);
      
	if(utils.getSetting('remote_selection') == '1'):
	    self.remote_path = utils.getSetting('remote_path_2')
	    utils.setSetting("remote_path","")
        elif(utils.getSetting('remote_selection') == '0'):
            self.remote_path = utils.getSetting("remote_path")

        #fix slashes
        self.remote_path = self.remote_path.replace("\\","/")
        
        #check if trailing slash is included
        if(self.remote_path[-1:] != "/"):
            self.remote_path = self.remote_path + "/"
        
        utils.log(utils.getString(30046))

    def run(self,mode=-1,runSilent=False):
	#check if we should use the progress bar
        if(utils.getSetting('run_silent') == 'false' and not runSilent):
            self.progressBar = xbmcgui.DialogProgress()
            self.progressBar.create(utils.getString(30010),utils.getString(30049) + "......")

        #determine backup mode
        if(mode == -1):
            mode = int(utils.getSetting('addon_mode'))

        #append backup folder name
        if(mode == self.Backup and self.remote_path != ''):
            self.remote_path = self.remote_path + time.strftime("%Y%m%d") + "/"
	elif(mode == self.Restore and utils.getSetting("backup_name") != '' and self.remote_path != ''):
	    self.remote_path = self.remote_path + utils.getSetting("backup_name") + "/"
	else:
	    self.remote_path = ""

        utils.log(utils.getString(30047) + ": " + self.local_path)
        utils.log(utils.getString(30048) + ": " + self.remote_path)

        #run the correct mode
        if(mode == self.Backup):
            utils.log(utils.getString(30023) + " - " + utils.getString(30016))
            self.fileManager = FileManager(self.local_path)

            #for backups check if remote path exists
            if(vfs.exists(self.remote_path)):
                #this will fail - need a disclaimer here
                utils.log(utils.getString(30050))

            self.syncFiles()
        else:
            utils.log(utils.getString(30023) + " - " + utils.getString(30017))
            self.fileManager = FileManager(self.remote_path)

            #for restores remote path must exist
            if(vfs.exists(self.remote_path)):
                self.restoreFiles()
            else:
                xbmcgui.Dialog().ok(utils.getString(30010),utils.getString(30045),self.remote_path)

        if(utils.getSetting('run_silent') == 'false' and not runSilent):
            self.progressBar.close()
        
    def syncFiles(self):
        
        #make the remote directory
        vfs.mkdir(self.remote_path)

        utils.log(utils.getString(30051))
        self.fileManager.createFileList()

        allFiles = self.fileManager.getFileList()

        #write list from local to remote
        self.writeFiles(allFiles,self.local_path,self.remote_path)
        
    def restoreFiles(self):
        self.fileManager.createFileList()

        utils.log(utils.getString(30051))
        allFiles = self.fileManager.getFileList()

        #write list from remote to local
        self.writeFiles(allFiles,self.remote_path,self.local_path)

        #call update addons to refresh everything
        xbmc.executebuiltin('UpdateLocalAddons')
        
    def writeFiles(self,fileList,source,dest):
        utils.log("Writing files to: " + dest)
        self.filesTotal = len(fileList)
        self.filesLeft = self.filesTotal

        #write each file from source to destination
        for aFile in fileList:
            if(not self.checkCancel()):
                utils.log('Writing file: ' + source + aFile,xbmc.LOGDEBUG)
                self.updateProgress(aFile)
                if (aFile.startswith("-")):
                    vfs.mkdir(xbmc.makeLegalFilename(dest + aFile[1:],False))
                else:
                    vfs.copy(xbmc.makeLegalFilename(source + aFile),xbmc.makeLegalFilename(dest + aFile,False))

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

    def isReady(self):
        return True if self.remote_path != '' else False

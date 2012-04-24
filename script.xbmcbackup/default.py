import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os

class FileManager:
    local_path = ''
    addonDir = ''
    fHandle = None

    def __init__(self,addon_dir):
        self.local_path = xbmc.translatePath("special://home")
        self.addonDir = addon_dir

        #create the addon folder if it doesn't exist
        if(not os.path.exists(unicode(xbmc.translatePath(self.addonDir),'utf-8'))):
            os.makedirs(unicode(xbmc.translatePath(self.addonDir),'utf-8'))

    def createFileList(self,Addon):
        self.fHandle = open(unicode(xbmc.translatePath(self.addonDir + "restore.txt"),'utf-8'),"w")
        
        #figure out which syncing options to run
        if(Addon.getSetting('backup_addons') == 'true'):
            self.addFile("-addons")
            self.walkTree(self.local_path + "addons/")

        self.addFile("-userdata")
        
        if(Addon.getSetting('backup_addon_data') == 'true'):
            self.addFile("-userdata/addon_data")
            self.walkTree(self.local_path + "userdata/addon_data/")
           
        if(Addon.getSetting('backup_database') == 'true'):
	    self.addFile("-userdata/Database")
            self.walkTree(self.local_path + "userdata/Database")
        
        if(Addon.getSetting("backup_playlists") == 'true'):
	    self.addFile("-userdata/playlists")
	    self.walkTree(self.local_path + "userdata/playlists")
			
        if(Addon.getSetting("backup_thumbnails") == "true"):
	    self.addFile("-userdata/Thumbnails")
	    self.walkTree(self.local_path + "userdata/Thumbnails")
		
        if(Addon.getSetting("backup_config") == "true"):
	    #this one is an oddity
            configFiles = os.listdir(self.local_path + "userdata/")
	    for aFile in configFiles:
		if(aFile.endswith(".xml")):
		    self.addFile("userdata/" + aFile)

	if(self.fHandle != None):
            self.fHandle.close()
        
    def walkTree(self,directory):
        for (path, dirs, files) in os.walk(directory):
            
            #get the relative part of this path
            path = path[len(self.local_path):]

            #create all the subdirs first
            for aDir in dirs:
                self.addFile("-" + path + os.sep +  aDir)
            #copy all the files
            for aFile in files:
                filePath = path + os.sep + aFile
                self.addFile(filePath)
                    
    def addFile(self,filename):
        #write the full remote path name of this file
        if(self.fHandle != None):
            self.fHandle.write(str(filename) + "\n")

    def readFileList(self):
        allFiles = open(unicode(xbmc.translatePath(self.addonDir + "restore.txt"),'utf-8'),"r").read().splitlines()

        return allFiles

class XbmcBackup:
    __addon_id__ = 'script.xbmcbackup'
    Addon = xbmcaddon.Addon(__addon_id__)
    local_path = ''
    remote_path = ''
    restoreFile = None
    
    #for the progress bar
    progressBar = None
    filesLeft = 0
    filesTotal = 0

    fileManager = None
    
    def __init__(self):
        self.local_path = xbmc.translatePath("special://home")

        if(self.Addon.getSetting('remote_path') != '' and self.Addon.getSetting("backup_name") != ''):
            self.remote_path = self.Addon.getSetting("remote_path") + self.Addon.getSetting('backup_name') + "/"

        self.fileManager = FileManager(self.Addon.getAddonInfo('profile'))
        
        self.log("Starting")
        self.log('Local Dir: ' + self.local_path)
        self.log('Remote Dir: ' + self.remote_path)

    def run(self):
        #check what mode were are in
        if(int(self.Addon.getSetting('addon_mode')) == 0):
            self.syncFiles()
        else:
            self.restoreFiles()
        
    def syncFiles(self):
        if(xbmcvfs.exists(self.remote_path)):
            #this will fail - need a disclaimer here
            self.log("Remote Path exists - may have old files in it!")

        #make the remote directory
        xbmcvfs.mkdir(self.remote_path)
        
        self.fileManager.createFileList(self.Addon)

        allFiles = self.fileManager.readFileList()

        #write list from local to remote
        self.writeFiles(allFiles,self.local_path,self.remote_path)

        #write the restore list
        xbmcvfs.copy(self.Addon.getAddonInfo('profile') + "restore.txt",self.remote_path + "restore.txt")
        
    def restoreFiles(self):
        #copy the restore file
        xbmcvfs.copy(self.remote_path + "restore.txt",self.Addon.getAddonInfo('profile') + "restore.txt")

        allFiles = self.fileManager.readFileList()

        #write list from remote to local
        self.writeFiles(allFiles,self.remote_path,self.local_path)
        
    def writeFiles(self,fileList,source,dest):
        self.filesTotal = len(fileList)
        self.filesLeft = self.filesTotal

        #check if we should use the progress bar
        if(self.Addon.getSetting('run_silent') == 'false'):
            self.progressBar = xbmcgui.DialogProgress()
            self.progressBar.create('XBMC Backup','Running......')

        #write each file from source to destination
        for aFile in fileList:
            if(not self.checkCancel()):
                self.updateProgress(aFile)
                if (aFile.startswith("-")):
                    xbmcvfs.mkdir(dest + aFile[1:])
                else:
                    xbmcvfs.copy(source + aFile,dest + aFile)

        if(self.Addon.getSetting('run_silent') == 'false'):
            self.progressBar.close()

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
      
    def log(self,message):
        xbmc.log(self.__addon_id__ + ": " + message)

    def isReady(self):
        return True if self.remote_path != '' else False

#run the profile backup
backup = XbmcBackup()

if(backup.isReady()):
    backup.run()
else:
    xbmcgui.Dialog().ok('XBMC Backup','Error: Remote path cannot be empty')

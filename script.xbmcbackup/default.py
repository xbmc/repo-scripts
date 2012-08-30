import xbmc
import xbmcaddon
import xbmcgui
import resources.lib.vfs as vfs
import os
import time

__addon_id__ = 'script.xbmcbackup'
__Addon = xbmcaddon.Addon(__addon_id__)

class FileManager:
    walk_path = ''
    addonDir = ''
    fileArray = None
    verbose_log = False
    
    def __init__(self,path,addon_dir):
        self.walk_path = path
        self.addonDir = addon_dir

        #create the addon folder if it doesn't exist
        if(not os.path.exists(unicode(xbmc.translatePath(self.addonDir),'utf-8'))):
            os.makedirs(unicode(xbmc.translatePath(self.addonDir),'utf-8'))

    def createFileList(self,Addon):
        self.fileArray = []
        self.verbose_log = Addon.getSetting("verbose_log") == 'true'
       
        #figure out which syncing options to run
        if(Addon.getSetting('backup_addons') == 'true'):
            self.addFile("-addons")
            self.walkTree(self.walk_path + "addons/")

        self.addFile("-userdata")
        
        if(Addon.getSetting('backup_addon_data') == 'true'):
            self.addFile("-userdata/addon_data")
            self.walkTree(self.walk_path + "userdata/addon_data/")
           
        if(Addon.getSetting('backup_database') == 'true'):
	    self.addFile("-userdata/Database")
            self.walkTree(self.walk_path + "userdata/Database")
        
        if(Addon.getSetting("backup_playlists") == 'true'):
	    self.addFile("-userdata/playlists")
	    self.walkTree(self.walk_path + "userdata/playlists")
			
        if(Addon.getSetting("backup_thumbnails") == "true"):
	    self.addFile("-userdata/Thumbnails")
	    self.walkTree(self.walk_path + "userdata/Thumbnails")
		
        if(Addon.getSetting("backup_config") == "true"):
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
        log("Add File: " + filename,xbmc.LOGDEBUG)
        self.fileArray.append(filename)

    def getFileList(self):
       return self.fileArray

class XbmcBackup:
    addon = None
    local_path = ''
    remote_path = ''
    restoreFile = None
    
    #for the progress bar
    progressBar = None
    filesLeft = 0
    filesTotal = 1

    fileManager = None
    
    def __init__(self,__Addon):
        self.addon = __Addon
        self.local_path = xbmc.makeLegalFilename(xbmc.translatePath("special://home"),False);
      
	if(self.addon.getSetting('remote_selection') == '1'):
	    self.remote_path = self.addon.getSetting('remote_path_2')
	    self.addon.setSetting("remote_path","")
        elif(self.addon.getSetting('remote_selection') == '0'):
            self.remote_path = self.addon.getSetting("remote_path")

        #check if trailing slash is included
        if(self.remote_path[-1:] != "/"):
            self.remote_path = self.remote_path + "/"

	#append backup folder name
        if(int(self.addon.getSetting('addon_mode')) == 0 and self.remote_path != ''):
            self.remote_path = self.remote_path + time.strftime("%Y%m%d") + "/"
	elif(int(self.addon.getSetting('addon_mode')) == 1 and self.addon.getSetting("backup_name") != '' and self.remote_path != ''):
	    self.remote_path = self.remote_path + self.addon.getSetting("backup_name") + "/"
	else:
	    self.remote_path = ""
        
        log(self.addon.getLocalizedString(30046))
        log(self.addon.getLocalizedString(30047) + ": " + self.local_path)
        log(self.addon.getLocalizedString(30048) + ": " + self.remote_path)

    def run(self):
	#check if we should use the progress bar
        if(self.addon.getSetting('run_silent') == 'false'):
            self.progressBar = xbmcgui.DialogProgress()
            self.progressBar.create(self.addon.getLocalizedString(30010),self.addon.getLocalizedString(30049) + "......")
	    
        #check what mode were are in
        if(int(self.addon.getSetting('addon_mode')) == 0):
            self.fileManager = FileManager(self.local_path,self.addon.getAddonInfo('profile'))

            #for backups check if remote path exists
            if(vfs.exists(self.remote_path)):
                #this will fail - need a disclaimer here
                log(self.addon.getLocalizedString(30050))

            self.syncFiles()
        else:
            self.fileManager = FileManager(self.remote_path,self.addon.getAddonInfo('profile'))

            #for restores remote path must exist
            if(vfs.exists(self.remote_path)):
                self.restoreFiles()
            else:
                xbmcgui.Dialog().ok(self.addon.getLocalizedString(30010),self.addon.getLocalizedString(30045))
        
    def syncFiles(self):
        
        #make the remote directory
        vfs.mkdir(self.remote_path)

        log(self.addon.getLocalizedString(30051))
        self.fileManager.createFileList(self.addon)

        allFiles = self.fileManager.getFileList()

        #write list from local to remote
        self.writeFiles(allFiles,self.local_path,self.remote_path)
        
    def restoreFiles(self):
        self.fileManager.createFileList(self.addon)

        log(self.addon.getLocalizedString(30051))
        allFiles = self.fileManager.getFileList()

        #write list from remote to local
        self.writeFiles(allFiles,self.remote_path,self.local_path)

        #call update addons to refresh everything
        xbmc.executebuiltin('UpdateLocalAddons')
        
    def writeFiles(self,fileList,source,dest):
        log("Writing files to: " + dest)
        self.filesTotal = len(fileList)
        self.filesLeft = self.filesTotal

        #write each file from source to destination
        for aFile in fileList:
            if(not self.checkCancel()):
                log('Writing file: ' + source + aFile,xbmc.LOGDEBUG)
                self.updateProgress(aFile)
                if (aFile.startswith("-")):
                    vfs.mkdir(xbmc.makeLegalFilename(dest + aFile[1:],False))
                else:
                    vfs.copy(xbmc.makeLegalFilename(source + aFile),xbmc.makeLegalFilename(dest + aFile,False))

        if(self.addon.getSetting('run_silent') == 'false'):
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

    def isReady(self):
        return True if self.remote_path != '' else False

#global functions for logging and encoding
def log(message,loglevel=xbmc.LOGNOTICE):
    xbmc.log(encode(__Addon.getLocalizedString(30010) + ": " + message),level=loglevel)

def encode(string):
    return string.encode('UTF-8','replace')


#run the profile backup
backup = XbmcBackup(__Addon)

if(backup.isReady()):
    backup.run()
else:
    xbmcgui.Dialog().ok(__Addon.getLocalizedString(30010),__Addon.getLocalizedString(30045))

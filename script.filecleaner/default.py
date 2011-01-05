import xbmc, xbmcgui, xbmcaddon, os, math, time
from pysqlite2 import dbapi2 as sqlite

# Addon info
__title__ = 'XBMC File Cleaner'
__author__ = 'Andrew Higginson <azhigginson@gmail.com>'
__addonID__	= "script.filecleaner"
__settings__ = xbmcaddon.Addon(__addonID__)

# Autoexec info
AUTOEXEC_PATH = xbmc.translatePath('special://home/userdata/autoexec.py')
AUTOEXEC_FOLDER_PATH = xbmc.translatePath('special://home/userdata/')
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/script.filecleaner/default.py,-startup)")\n'

class Main:
    def __init__(self):
        # Refreh settings
        self.refreshSettings()
        
        if self.serviceEnabled:
            # Monitoring library
            self.notify(__settings__.getLocalizedString(30013))
            
        # Main service loop
        while self.refreshSettings() and self.serviceEnabled:
            self.cleanup()
            time.sleep(60)

        # Service disabled
        self.notify(__settings__.getLocalizedString(30015))
            
    # Run cleanup routine
    def cleanup(self):
        self.log(__settings__.getLocalizedString(30009))
        if not self.deleteOnDiskLow or (self.deleteOnDiskLow and self.isDiskSpaceLow()):
            doClean = False
            
            # Delete any expired movies
            if self.deleteMovies:
                movies = self.getExpired('movie')
                if movies:
                    doClean = True
                    for file in movies:
                        self.deleteFile(file)
                    
            # Delete any expired TV shows
            if self.deleteTVShows:
                episodes = self.getExpired('episode')
                if episodes:
                    doClean = True
                    for file in episodes:
                        self.deleteFile(file)                    
                        
            # Finally clean the library to account for any deleted videos
            if doClean and self.cleanLibrary:
                xbmc.executebuiltin("XBMC.CleanLibrary(video)")
            
    # Get all expired videos from the library database
    def getExpired(self, option):
        try:
            con = sqlite.connect(xbmc.translatePath('special://database/MyVideos34.db'))
            cur = con.cursor()
            
            sql = "SELECT path.strPath || files.strFilename FROM files, path, %s WHERE %s.idFile = files.idFile AND files.idPath = path.idPath AND files.lastPlayed < datetime('now', '-%d days') AND playCount > 0" % (option, option, self.expireAfter)
            
            cur.execute(sql)
            
            # Return list of files to delete
            return [element[0] for element in cur.fetchall()]
        except:
            # Error opening video library database
            self.notify(__settings__.getLocalizedString(30012))
            raise

    # Refreshes current settings
    def refreshSettings(self):
        __settings__ = xbmcaddon.Addon(__addonID__)
        
        self.serviceEnabled = bool(__settings__.getSetting('service_enabled') == "true")
        self.showNotifications = bool(__settings__.getSetting('show_notifications') == "true")
        self.expireAfter = float(__settings__.getSetting('expire_after'))
        self.deleteOnDiskLow = bool(__settings__.getSetting('delete_on_low_disk') == "true")
        self.lowDiskPercentage = float(__settings__.getSetting('low_disk_percentage'))
        self.lowDiskPath = __settings__.getSetting('low_disk_path')
        self.cleanLibrary = bool(__settings__.getSetting('clean_library') == "true")
        self.deleteMovies = bool(__settings__.getSetting('delete_movies') == "true")
        self.deleteTVShows = bool(__settings__.getSetting('delete_tvshows') == "true")
        # Set or remove autoexec.py line
        autoStart(self.serviceEnabled)
        return True

    # Returns true if running out of disk space
    def isDiskSpaceLow(self):
        diskStats = os.statvfs(xbmc.translatePath(self.lowDiskPath))
        diskCapacity = diskStats.f_frsize * diskStats.f_blocks
        diskFree = diskStats.f_frsize * diskStats.f_bavail
        diskFreePercent = math.ceil(float(100) / float(diskCapacity) * float(diskFree))

        return (float(diskFreePercent) < float(self.lowDiskPercentage))

    # Delete file from the OS
    def deleteFile(self, file):
        if os.path.exists(file):
            os.remove(file)
            # Deleted
            self.notify(__settings__.getLocalizedString(30014) + ' ' + file)

    # Display notification on screen and send to log
    def notify(self, message):
        self.log(message)
        if self.showNotifications:
            xbmc.executebuiltin('XBMC.Notification(%s, %s)' % (__title__, message))
    
    # Log message
    def log(self, message):
        xbmc.log('::' + __title__ + '::' + message)

    # Sets or removes autostart line in special://home/userdata/autoexec.py
    def autoStart(self, option):
        # See if the autoexec.py file exists
        if (os.path.exists(AUTOEXEC_PATH)):
	        # Var to check if we're in autoexec.py
	        found = False
	        autoexecfile = file(AUTOEXEC_PATH, 'r')
	        filecontents = autoexecfile.readlines()
	        autoexecfile.close()

	        # Check if we're in it
	        for line in filecontents:
		        if line.find(__addonID__) > 0:
			        found = True

	        # If the autoexec.py file is found and we're not in it,
	        if (not found and option):
		        autoexecfile = file(AUTOEXEC_PATH, 'w')
		        filecontents.append(AUTOEXEC_SCRIPT)
		        autoexecfile.writelines(filecontents)            
		        autoexecfile.close()

	        # Found that we're in it and it's time to remove ourselves
	        if (found and not option):
		        autoexecfile = file(AUTOEXEC_PATH, 'w')
		        for line in filecontents:
			        if not line.find(__addonID__) > 0:
				        autoexecfile.write(line)
		        autoexecfile.close()
        else:
	        if (os.path.exists(AUTOEXEC_FOLDER_PATH)):
		        autoexecfile = file(AUTOEXEC_PATH, 'w')
		        autoexecfile.write (AUTOEXEC_SCRIPT.strip())
		        autoexecfile.close()
	        else:
		        os.makedirs(AUTOEXEC_FOLDER_PATH)
		        autoexecfile = file(AUTOEXEC_PATH, 'w')
		        autoexecfile.write (AUTOEXEC_SCRIPT.strip())
		        autoexecfile.close()

run = Main()

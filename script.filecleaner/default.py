import xbmc, xbmcgui, xbmcaddon, os, shutil, math, time
from pysqlite2 import dbapi2 as sqlite

""" Addon info """
__title__ = 'XBMC File Cleaner'
__author__ = 'Andrew Higginson <azhigginson@gmail.com>'
__addonID__ = "script.filecleaner"
__settings__ = xbmcaddon.Addon(__addonID__)

""" Autoexec info """
AUTOEXEC_PATH = xbmc.translatePath('special://home/userdata/autoexec.py')
AUTOEXEC_FOLDER_PATH = xbmc.translatePath('special://home/userdata/')
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/script.filecleaner/default.py,-startup)")\n'

class Main:
    def __init__(self):
        """ Refreh settings """
        self.refresh_settings()
        
        if self.serviceEnabled:
            """ Monitoring library """
            self.notify(__settings__.getLocalizedString(30013))
            
        """ Main service loop """
        while self.refresh_settings() and self.serviceEnabled:
            self.cleanup()
            time.sleep(60)

        """ Service disabled """
        self.notify(__settings__.getLocalizedString(30015))
            
            
    """ Run cleanup routine """
    def cleanup(self):
        self.debug(__settings__.getLocalizedString(30009))
        if not self.deleteOnDiskLow or (self.deleteOnDiskLow and self.disk_space_low()):
            doClean = False
            
            """ Delete any expired movies """
            if self.deleteMovies:
                movies = self.get_expired('movie')
                if movies:
                    for file, path in movies:
                        if os.path.exists(path):
                            doClean = True
                        if self.enableHolding:
                            self.debug("Moving %s to %s..." % (file, self.holdingFolder))
                            self.move_file(path, self.holdingFolder)
                        else:
                            self.debug("Deleting %s..." % (file))
                            self.delete_file(path)
                    
            """ Delete any expired TV shows """
            if self.deleteTVShows:
                episodes = self.get_expired('episode')
                if episodes:
                    for file, path in episodes:
                        if os.path.exists(path):
                            doClean = True
                        if self.enableHolding:
                            self.debug("Moving %s to %s..." % (file, self.holdingFolder))
                            self.move_file(path, self.holdingFolder)
                        else:
                            self.debug("Deleting %s..." % (file))
                            self.delete_file(path)                    
                        
            """ Finally clean the library to account for any deleted videos """
            if doClean and self.cleanLibrary:
                xbmc.executebuiltin("XBMC.CleanLibrary(video)")
            
            
    """ Get all expired videos from the library database """
    def get_expired(self, option):
        try:
            con = sqlite.connect(xbmc.translatePath('special://database/MyVideos34.db'))
            cur = con.cursor()
            
            if option == 'movie':
                sql = "SELECT files.strFilename as filename,\
                              path.strPath || files.strFilename as full_path\
                         FROM files, path, %s\
                        WHERE %s.idFile = files.idFile\
                          AND files.idPath = path.idPath\
                          AND files.lastPlayed < datetime('now', '-%f days')\
                          AND playCount > 0" % (option, option, self.expireAfter)
                if self.deleteLowRating:
                    sql += ' AND c05+0 < %f' % (self.lowRatingFigure)
                    if self.ignoreNoRating:
                      sql += ' AND c05 > 0'

            elif option == 'episode':
                sql = "SELECT files.strFilename as filename,\
                              path.strPath || files.strFilename as full_path\
                         FROM files, path, %s\
                        WHERE %s.idFile = files.idFile\
                          AND files.idPath = path.idPath\
                          AND files.lastPlayed < datetime('now', '-%f days')\
                          AND playCount > 0" % (option, option, self.expireAfter)
                if self.deleteLowRating:
                    sql += ' AND c03+0 < %f' % (self.lowRatingFigure)
                    if self.ignoreNoRating:
                      sql += ' AND c03 > 0'
            
            self.debug('Executing ' + str(sql))
                
            cur.execute(sql)
            
            """ Return list of files to delete """
            return cur.fetchall()
        except:
            """ Error opening video library database """
            self.notify(__settings__.getLocalizedString(30012))
            raise


    """ Refreshes current settings """
    def refresh_settings(self):
        __settings__ = xbmcaddon.Addon(__addonID__)
        
        self.serviceEnabled = bool(__settings__.getSetting('service_enabled') == "true")
        self.showNotifications = bool(__settings__.getSetting('show_notifications') == "true")
        self.expireAfter = float(__settings__.getSetting('expire_after'))
        self.deleteOnDiskLow = bool(__settings__.getSetting('delete_on_low_disk') == "true")
        self.lowDiskPercentage = float(__settings__.getSetting('low_disk_percentage'))
        self.lowDiskPath = xbmc.translatePath(__settings__.getSetting('low_disk_path'))
        self.cleanLibrary = bool(__settings__.getSetting('clean_library') == "true")
        self.deleteMovies = bool(__settings__.getSetting('delete_movies') == "true")
        self.deleteTVShows = bool(__settings__.getSetting('delete_tvshows') == "true")
        self.deleteLowRating = bool(__settings__.getSetting('delete_low_rating') == "true")
        self.lowRatingFigure = float(__settings__.getSetting('low_rating_figure'))
        self.ignoreNoRating = bool(__settings__.getSetting('ignore_no_rating') == "true")
        self.enableHolding = bool(__settings__.getSetting('enable_holding') == "true")
        self.holdingFolder = xbmc.translatePath(__settings__.getSetting('holding_folder'))
        #self.holdingExpire = int(__settings__.getSetting('holding_expire'))
        self.enableDebug = bool(xbmc.translatePath(__settings__.getSetting('enable_debug')) == "true")
        
        """ Set or remove autoexec.py line """
        self.toggle_auto_start(self.serviceEnabled)
        return True


    """ Returns true if running out of disk space """
    def disk_space_low(self):
        diskStats = os.statvfs(self.lowDiskPath)
        diskCapacity = diskStats.f_frsize * diskStats.f_blocks
        diskFree = diskStats.f_frsize * diskStats.f_bavail
        diskFreePercent = math.ceil(float(100) / float(diskCapacity) * float(diskFree))

        return (float(diskFreePercent) < float(self.lowDiskPercentage))


    """ Delete file from the OS """
    def delete_file(self, file):
        if os.path.exists(file):
            os.remove(file)
            """ Deleted """
            self.notify(__settings__.getLocalizedString(30014) + ' ' + file)

    """ Move file """
    def move_file(self, file, destination):
        if os.path.exists(file):
            shutil.move(file, destination)
            """ Deleted """
            self.notify(__settings__.getLocalizedString(30025) % (file))

    """ Display notification on screen and send to log """
    def notify(self, message):
        self.debug(message)
        if self.showNotifications:
            xbmc.executebuiltin('XBMC.Notification(%s, %s)' % (__title__, message))
    
    
    """ Log debug message """
    def debug(self, message):
        if self.enableDebug:
            xbmc.log('::' + __title__ + '::' + message)


    """ Sets or removes auto start line in special://home/userdata/autoexec.py """
    def toggle_auto_start(self, option):
        """ See if the autoexec.py file exists """
        if (os.path.exists(AUTOEXEC_PATH)):
	        """ Var to check if we're in autoexec.py """
	        found = False
	        autoexecfile = file(AUTOEXEC_PATH, 'r')
	        filecontents = autoexecfile.readlines()
	        autoexecfile.close()

	        """ Check if we're in it """
	        for line in filecontents:
		        if line.find(__addonID__) > 0:
			        found = True

	        """ If the autoexec.py file is found and we're not in it """
	        if (not found and option):
		        autoexecfile = file(AUTOEXEC_PATH, 'w')
		        filecontents.append(AUTOEXEC_SCRIPT)
		        autoexecfile.writelines(filecontents)            
		        autoexecfile.close()

	        """ Found that we're in it and it's time to remove ourselves """
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

# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon
import os
import xbmcvfs

__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, debug_logging_enabled=True):
    if (__addon__.getSetting( "logEnabled" ) == "true") and debug_logging_enabled:
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

def normalize_string( text ):
    try:
        text = text.replace(":","")
        text = text.replace("/","-")
        text = text.replace("\\","-")
        text = unicodedata.normalize( 'NFKD', unicode( text, 'utf-8' ) ).encode( 'ascii', 'ignore' )
    except:
        pass
    return text


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join( dir, file ):
    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)

# Splits a path the same way as os.path.split but supports paths of a different
# OS than that being run on
def os_path_split( fullpath ):
    # Check if it ends in a slash
    if fullpath.endswith("/") or fullpath.endswith("\\"):
        # Remove the slash character
        fullpath = fullpath[:-1]

    try:
        slash1 = fullpath.rindex("/")
    except:
        slash1 = -1
    
    try:
        slash2 = fullpath.rindex("\\")
    except:
        slash2 = -1

    # Parse based on the last type of slash in the string
    if slash1 > slash2:
        return fullpath.rsplit("/", 1)
    
    return fullpath.rsplit("\\", 1)


# Get the contents of the directory
def list_dir(dirpath):
    # There is a problem with the afp protocol that means if a directory not ending
    # in a / is given, an error happens as it just appends the filename to the end
    # without actually checking there is a directory end character
    #    http://forum.xbmc.org/showthread.php?tid=192255&pid=1681373#pid1681373
    if dirpath.startswith('afp://') and (not dirpath.endswith('/')):
        dirpath = os_path_join(dirpath, '/')
    return xbmcvfs.listdir( dirpath )


##############################
# Stores Various Settings
##############################
class Settings():
    # Value to calculate which version of XBMC we are using
    xbmcMajorVersion = 0
    # The time the screensaver is set to (-1 for not set)
    screensaverTime = 0


    # Loads the Screensaver settings
    # In Frodo there is no way to get the time before the screensaver
    # is set to start, this means that the only way open to us is to
    # load up the XML config file and read it from there.
    # One of the many down sides of this is that the XML file will not
    # be updated to reflect changes until the user exits XMBC
    # This isn't a big problem as screensaver times are not changed
    # too often
    #
    # Unfortunately the act of stopping the theme is seem as "activity"
    # so it will reset the time, in Gotham, there will be a way to
    # actually start the screensaver again, but until then there is
    # not mush we can do
    @staticmethod
    def loadScreensaverSettings():
        Settings.screensaverTime = -1
        return -1

#####################################################################
## IMPORTANT NOTE
## --------------
## The method _loadScreensaverSettings has been commented out
## because it breaks the rules for getting Add-ons accepted into
## the official repository, the bug still exists but can be solved
## in one of two ways:
## 1) After installation of the addon, uncomment the following method
## 2) Set the "Fade out after playing for (minutes)" to less than the
##    screen saver value in TvTunes setting
## Option 2 is recommended as will not need re-applying after updates
#####################################################################

#     def loadScreensaverSettings():
#         if Settings.screensaverTime == 0:
#             Settings.screenTimeOutSeconds = -1
#             pguisettings = xbmc.translatePath('special://profile/guisettings.xml')
#      
#             log("Settings: guisettings.xml location = %s" % pguisettings)
#      
#             # Make sure we found the file and it exists
#             if os.path.exists(pguisettings):
#                 # Create an XML parser
#                 elemTree = ET.ElementTree()
#                 elemTree.parse(pguisettings)
#                 
#                 # First check to see if any screensaver is set
#                 isEnabled = elemTree.findtext('screensaver/mode')
#                 if (isEnabled == None) or (isEnabled == ""):
#                     log("Settings: No Screensaver enabled")
#                 else:
#                     log("Settings: Screensaver set to %s" % isEnabled)
#     
#                     # Get the screensaver setting in minutes
#                     result = elemTree.findtext('screensaver/time')
#                     if result != None:
#                         log("Settings: Screensaver timeout set to %s" % result)
#                         # Convert from minutes to seconds, also reduce by 30 seconds
#                         # as we want to ensure we have time to stop before the
#                         # screensaver kicks in
#                         Settings.screenTimeOutSeconds = (int(result) * 60) - 10
#                     else:
#                         log("Settings: No Screensaver timeout found")
#                  
#                 del elemTree
#         return Settings.screenTimeOutSeconds

    @staticmethod
    def isCustomPathEnabled():
        return __addon__.getSetting("custom_path_enable") == 'true'
    
    @staticmethod
    def getCustomPath():
        return __addon__.getSetting("custom_path").decode("utf-8")
    
    @staticmethod
    def getDownVolume():
        return int(float(__addon__.getSetting("downvolume")))

    @staticmethod
    def isLoop():
        return __addon__.getSetting("loop") == 'true'
    
    @staticmethod
    def isFadeOut():
        return __addon__.getSetting("fadeOut") == 'true'

    @staticmethod
    def isFadeIn():
        return __addon__.getSetting("fadeIn") == 'true'
    
    @staticmethod
    def isSmbEnabled():
        if __addon__.getSetting("smb_share"):
            return True
        else:
            return False

    @staticmethod
    def getSmbUser():
        if __addon__.getSetting("smb_login"):
            return __addon__.getSetting("smb_login")
        else:
            return "guest"
    
    @staticmethod
    def getSmbPassword():
        if __addon__.getSetting("smb_psw"):
            return __addon__.getSetting("smb_psw")
        else:
            return "guest"
    
    # Calculates the regular expression to use to search for theme files
    @staticmethod
    def getThemeFileRegEx(searchDir=None, extensionOnly=False):
        fileTypes = "mp3" # mp3 is the default that is always supported
        if(__addon__.getSetting("wma") == 'true'):
            fileTypes = fileTypes + "|wma"
        if(__addon__.getSetting("flac") == 'true'):
            fileTypes = fileTypes + "|flac"
        if(__addon__.getSetting("m4a") == 'true'):
            fileTypes = fileTypes + "|m4a"
        if(__addon__.getSetting("wav") == 'true'):
            fileTypes = fileTypes + "|wav"
        themeRegEx = '(theme[ _A-Za-z0-9.-]*.(' + fileTypes + ')$)'
        # If using the directory method then remove the requirement to have "theme" in the name
        if (searchDir != None) and Settings.isThemeDirEnabled():
            # Make sure this is checking the theme directory, not it's parent
            if searchDir.endswith(Settings.getThemeDirectory()):
                extensionOnly = True
        # See if we do not want the theme keyword
        if extensionOnly:
            themeRegEx = '(.(' + fileTypes + ')$)'
        return themeRegEx
    
    @staticmethod
    def isTimout():
        screensaverTime = Settings.loadScreensaverSettings()
        if screensaverTime == -1:
            return False
        # It is a timeout if the idle time is larger that the time stored
        # for when the screensaver is due to kick in
        if (xbmc.getGlobalIdleTime() > screensaverTime):
            log("Settings: Stopping due to screensaver")
            return True
        else:
            return False

    @staticmethod
    def isShuffleThemes():
        return __addon__.getSetting("shuffle") == 'true'
    
    @staticmethod
    def isRandomStart():
        return __addon__.getSetting("random") == 'true'
    
    @staticmethod
    def isPlayMovieList():
        return __addon__.getSetting("movielist") == 'true'

    @staticmethod
    def isPlayTvShowList():
        return __addon__.getSetting("tvlist") == 'true'

    @staticmethod
    def isPlayMusicVideoList():
        return __addon__.getSetting("musicvideolist") == 'true'

    @staticmethod
    def getPlayDurationLimit():
        return int(float(__addon__.getSetting("endafter")))

    @staticmethod
    def getTrackLengthLimit():
        return int(float(__addon__.getSetting("trackLengthLimit")))

    # Check if the video info button should be hidden
    @staticmethod
    def hideVideoInfoButton():
        return __addon__.getSetting("showVideoInfoButton") != 'true'

    # Check the delay start value
    @staticmethod
    def getStartDelaySeconds():
        return int(float(__addon__.getSetting("delayStart")))

    @staticmethod
    def getXbmcMajorVersion():
        if Settings.xbmcMajorVersion == 0:
            xbmcVer = xbmc.getInfoLabel('system.buildversion')
            log("Settings: XBMC Version = %s" % xbmcVer)
            Settings.xbmcMajorVersion = 12
            try:
                # Get just the major version number
                Settings.xbmcMajorVersion = int(xbmcVer.split(".", 1)[0])
            except:
                # Default to frodo as the default version if we fail to find it
                log("Settings: Failed to get XBMC version")
            log("Settings: XBMC Version %d (%s)" % (Settings.xbmcMajorVersion, xbmcVer))
        return Settings.xbmcMajorVersion

    @staticmethod
    def isThemeDirEnabled():
        # Theme sub directory only supported when not using a custom path
        if Settings.isCustomPathEnabled():
            return False
        return __addon__.getSetting("searchSubDir") == 'true'

    @staticmethod
    def getThemeDirectory():
        # Load the information about storing themes in sub-directories
        # Only use the Theme dir if custom path is not used
        return __addon__.getSetting("subDirName")

    @staticmethod
    def isExactMatchEnabled():
        return __addon__.getSetting("exact_match") == 'true'

    @staticmethod
    def isMultiThemesSupported():
        return __addon__.getSetting("multiThemeDownload") == 'true'
    
    @staticmethod
    def isMovieDownloadEnabled():
        return __addon__.getSetting("searchMovieDownload") == 'true'

    @staticmethod
    def getSearchEngine():
        return __addon__.getSetting("themeSearchSource")



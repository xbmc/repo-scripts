# -*- coding: utf-8 -*-
#Modules General
from traceback import print_exc
import os
import re
import unicodedata
import random
import threading
import time
import traceback
import xml.etree.ElementTree as ET
#Modules XBMC
import xbmc
import xbmcgui
import sys
import xbmcvfs
import xbmcaddon

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')

#
# Output logging method, if global logging is enabled
#
def log(txt):
    if __addon__.getSetting( "logEnabled" ) == "true":
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
        return __addon__.getSetting("custom_path")
    
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
        return __addon__.getSetting("subDirName")

#############################################
# Reads TvTunes information from an NFO file
#############################################
class NfoReader():
    def __init__( self, directory ):
        self.themeFiles = []
        self.themeDirs = []
        self._loadNfoInfo(directory)

    # Get any themes that were in the NFO file
    def getThemeFiles(self):
        return self.themeFiles

    # Get any theme directories that were in the NFO file
    def getThemeDirs(self):
        return self.themeDirs

    # Check for an NFO file for this show and reads details out of it
    # if it exists
    def _loadNfoInfo(self, directory):
        # Find out the name of the NFO file
        nfoFileName = os_path_join(directory, "tvtunes.nfo")
        
        log("NfoReader: Searching for NFO file: %s" % nfoFileName)
        
        # Return False if file does not exist
        if not xbmcvfs.exists( nfoFileName ):
            log("NfoReader: No NFO file found: %s" % nfoFileName)
            return False

        returnValue = False

        try:
            # Need to first load the contents of the NFO file into
            # a string, this is because the XML File Parse option will
            # not handle formats like smb://
            nfoFile = xbmcvfs.File(nfoFileName)
            nfoFileStr = nfoFile.read()
            nfoFile.close()

            # Create an XML parser
            nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr))
            rootElement = nfoXml.getroot()
            
            log("NfoReader: Root element is = %s" % rootElement.tag)
            
            # Check which format if being used
            if rootElement.tag == "tvtunes":
                log("NfoReader: TvTunes format NFO detected")
                #    <tvtunes>
                #        <file>theme.mp3</file>
                #        <directory>c:\my\themes</directory>
                #        <playlistfile>playlist.m3u</playlistfile>
                #    </tvtunes>

                # There could be multiple file entries, so loop through all of them
                for fileElem in nfoXml.findall('file'):
                    file = None
                    if fileElem != None:
                        file = fileElem.text

                    if (file != None) and (file != ""):
                        if (not "/" in file) and (not "\\" in file):
                            # Make it a full path if it is not already
                            file = os_path_join(directory, file)
                        log("NfoReader: file = %s" % file)
                        self.themeFiles.append(file)

                # There could be multiple directory entries, so loop through all of them
                for dirElem in nfoXml.findall('directory'):
                    dir = None
                    if dirElem != None:
                        dir = dirElem.text

                    if (dir != None) and (dir != ""):
                        if (not "/" in dir) and (not "\\" in dir):
                            # Make it a full path if it is not already
                            dir = os_path_join(directory, dir)
                        log("NfoReader: directory = %s" % dir)
                        self.themeDirs.append(dir)

                # Check for the playlist files
                for playlistFileElem in nfoXml.findall('playlistfile'):
                    playlistFile = None
                    if playlistFileElem != None:
                        playlistFile = playlistFileElem.text

                    self._addFilesFromPlaylist(playlistFile, directory)

                returnValue = True
            else:
                self.displayName = None
                self.orderKey = None
                log("NfoReader: Unknown NFO format")
    
            del nfoXml

        except:
            log("NfoReader: Failed to process NFO: %s" % nfoFileName)
            log("NfoReader: %s" % traceback.format_exc())
            returnValue = False

        return returnValue

    # Adds tracks in a playlist to the list of theme files to play
    def _addFilesFromPlaylist(self, playlistFile, directory):
        if (playlistFile == None) or (playlistFile == ""):
            return

        fileExt = os.path.splitext( playlistFile )[1]
        
        # Check if dealing with a Smart Playlist
        if fileExt == ".xsp":
            # Process the Smart Playlist
            self._addFilesFromSmartPlaylist(playlistFile)
            return
        
        if (not "/" in playlistFile) and (not "\\" in playlistFile):
            # There is just the filename of the playlist without
            # a path, check if the file is local or if we should
            # read it from the user directory
            # Check if there is an extension on the name
            if fileExt == None or fileExt == "":
                playlistFile = playlistFile + ".m3u"
            localFile = os_path_join(directory, playlistFile)
            if xbmcvfs.exists(localFile):
                # Make it a full path if it is not already
                playlistFile = localFile
            else:
                # default to the music playlist directory if not local
                playlistFile = os_path_join(xbmc.translatePath("special://musicplaylists"), playlistFile)
                
        log("NfoReader: playlist file = %s" % playlistFile)

        if xbmcvfs.exists(playlistFile):
            # Load the playlist into the Playlist object
            # An exception if thrown if the file does not exist
            try:
                xbmcPlaylist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                xbmcPlaylist.load(playlistFile)
                i = 0
                while i < xbmcPlaylist.size():  
                    # get the filename from the playlist
                    file = xbmcPlaylist[i].getfilename()
                    i = i + 1
                    if (file != None) and (file != ""):
                        log("NfoReader: file from playlist = %s" % file)
                        self.themeFiles.append(file)      
            except:
                log("NfoReader: playlist file processing error = %s" % playlistFile)
        else:
            log("NfoReader: playlist file not found = %s" % playlistFile)


    # Adds tracks in a Smart playlist to the list of theme files to play
    def _addFilesFromSmartPlaylist(self, playlistFile):
        if not "/" in playlistFile:
            playlistFile = "special://musicplaylists/" + playlistFile

        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": { "directory": "%s", "media": "music" },  "id": 1}' % playlistFile)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)

        if "result" in json_query and json_query['result'].has_key('files'):
            # Get the list of movies paths from the movie set
            items = json_query['result']['files']
            for item in items:
                log("NfoReader: Adding From Smart Playlist: %s" % item['file'])
                self.themeFiles.append(item['file'])


##############################
# Calculates file locations
##############################
class ThemeFiles():
    def __init__(self, rawPath, pathList=None):
        self.forceShuffle = False
        self.rawPath = rawPath
        if rawPath == "":
            self.clear()
        elif (pathList != None) and (len(pathList) > 0):
            self.themeFiles = []
            for aPath in pathList:
                subThemeList = self._generateThemeFilelistWithDirs(aPath)
                # add these files to the existing list
                self.themeFiles = self._mergeThemeLists(self.themeFiles, subThemeList)
            # If we were given a list, then we should shuffle the themes
            # as we don't always want the first path playing first
            self.forceShuffle = True
        else:
            self.themeFiles = self._generateThemeFilelistWithDirs(rawPath)

    # Define the equals to be based off of the list of theme files
    def __eq__(self, other):
        try:
            if isinstance(other, ThemeFiles):
                # If the lengths are not the same, there is no chance of a match
                if len(self.themeFiles) != len(other.themeFiles):
                    return False
                # Make sure each file in the list is also in the source list
                for aFile in other.themeFiles:
                    if( self.themeFiles.count(aFile) < 1 ):
                        return False
            else:
                return NotImplemented
        except AttributeError:
            return False
        # If we reach here then the theme lists are equal
        return True

    # Define the not equals to be based off of the list of theme files
    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def hasThemes(self):
        return (len(self.themeFiles) > 0)
    
    def getPath(self):
        return self.rawPath
    
    def clear(self):
        self.rawPath == ""
        self.themeFiles = []

    # Returns the playlist for the themes
    def getThemePlaylist(self):
        # Take the list of files and create a playlist from them
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        for aFile in self.themeFiles:
            # Add the theme file to a playlist
            playlist.add( url=aFile )

        if (Settings.isShuffleThemes() or self.forceShuffle) and playlist.size() > 1:
            playlist.shuffle()
        
        # Now we have the playlist, and it has been shuffled if needed
        # Check if we need to have a random start time for the first track
        # Note: The following method (rather than seek) should prevent
        # the seek dialog being displayed on the screen and also prevent
        # the need to start the theme playing before changing the start point
        if Settings.isRandomStart() and playlist.size() > 0:
            filename = playlist[0].getfilename()
            duration = int(playlist[0].getduration())

            log("ThemeFiles: Duration is %d for file %s" % (duration, filename))
            
            if duration > 10:
                listitem = xbmcgui.ListItem()
                # Record if the theme should start playing part-way through
                randomStart = random.randint(0, int(duration * 0.75))
                listitem.setProperty('StartOffset', str(randomStart))

                log("ThemeFiles: Setting Random start of %d for %s" % (randomStart, filename))

                # Remove the old item from the playlist
                playlist.remove(filename)
                # Add the new item at the start of the list
                playlist.add(filename, listitem, 0)

        return playlist

    #
    # Gets the usable path after alterations like network details
    #
    def _getUsablePath(self, rawPath):
        workingPath = rawPath
        
        # Start by removing the stack details
        if workingPath.startswith("stack://"):
            workingPath = workingPath.replace("stack://", "").split(" , ", 1)[0]
        
        if Settings.isSmbEnabled() and workingPath.startswith("smb://") : 
            log( "### Try authentication share" )
            workingPath = workingPath.replace("smb://", "smb://%s:%s@" % (Settings.getSmbUser(), Settings.getSmbPassword()) )
            log( "### %s" % workingPath )
    
        #######hack for episodes stored as rar files
        if workingPath.startswith("rar://"):
            workingPath = workingPath.replace("rar://","")
        
        # Support special paths like smb:// means that we can not just call
        # os.path.isfile as it will return false even if it is a file
        # (A bit of a shame - but that's the way it is)
        fileExt = os.path.splitext( workingPath )[1]
        # If this is a file, then get it's parent directory
        if fileExt != None and fileExt != "":
            workingPath = os.path.dirname(workingPath)

        # If the path currently ends in the directory separator
        # then we need to clear an extra one
        if (workingPath[-1] == os.sep) or (workingPath[-1] == os.altsep):
            workingPath = workingPath[:-1]

        return workingPath
    #
    # Handles the case where there is a theme directory set
    #
    def _generateThemeFilelistWithDirs(self, rawPath):
        themeFiles = []
        # Check the theme directory if it is set up
        if Settings.isThemeDirEnabled():
            themeDir = self._getUsablePath(rawPath)
            themeDir = os_path_join( themeDir, Settings.getThemeDirectory() )
            themeFiles = self._generateThemeFilelist(themeDir)
        
        # If no themes were found in the directory then search the normal location
        if len(themeFiles) < 1:
            themeFiles = self._generateThemeFilelist(rawPath)
        return themeFiles

    #
    # Calculates the location of the theme file
    #
    def _generateThemeFilelist(self, rawPath):
        # Get the full path with any network alterations
        workingPath = self._getUsablePath(rawPath)

        #######hack for TV shows stored as ripped disc folders
        if 'VIDEO_TS' in workingPath:
            log( "### FOUND VIDEO_TS IN PATH: Correcting the path for DVDR tv shows" )
            workingPath = self._updir( workingPath, 3 )
            themeList = self._getThemeFiles(workingPath)
            if len(themeList) < 1:
                workingPath = self._updir(workingPath,1)
                themeList = self._getThemeFiles(workingPath)
        #######end hack
        else:
            themeList = self._getThemeFiles(workingPath)
            # If no theme files were found in this path, look at the parent directory
            if len(themeList) < 1:
                workingPath = self._updir( workingPath, 1 )
                themeList = self._getThemeFiles(workingPath)

        log("ThemeFiles: Playlist size = %d" % len(themeList))
        log("ThemeFiles: Working Path = %s" % workingPath)
        
        return themeList

    def _updir(self, thepath, x):
        # move up x directories on the path
        while x > 0:
            x -= 1
            thepath = (os.path.split(thepath))[0]
        return thepath

    # Search for theme files in the given directory
    def _getThemeFiles(self, directory, extensionOnly=False):
        # First read from the NFO file if it exists
        nfoRead = NfoReader(directory)
        themeFiles = nfoRead.getThemeFiles()
        
        # Get the theme directories that are referenced and process the data in them
        for nfoDir in nfoRead.getThemeDirs():
            # Do not want the theme keyword if looking at an entire directory
            themeFiles = themeFiles + self._getThemeFiles(nfoDir, True)
        
        log( "ThemeFiles: Searching %s for %s" % (directory, Settings.getThemeFileRegEx(directory,extensionOnly)) )
        # check if the directory exists before searching
        if xbmcvfs.exists(directory):
            dirs, files = xbmcvfs.listdir( directory )
            for aFile in files:
                m = re.search(Settings.getThemeFileRegEx(directory,extensionOnly), aFile, re.IGNORECASE)
                if m:
                    path = os_path_join( directory, aFile )
                    log("ThemeFiles: Found match: %s" % path)
                    # Add the theme file to the list
                    themeFiles.append(path)

        return themeFiles

    # Merges lists making sure there are no duplicates
    def _mergeThemeLists(self, list_a, list_b):
        mergedList = list_a
        for b_item in list_b:
            # check if the item is already in the list
            if mergedList.count(b_item) < 1:
                # Not in the list, add it
                mergedList.append(b_item)
        return mergedList

###################################
# Custom Player to play the themes
###################################
class Player(xbmc.Player):
    def __init__(self, *args):
        # Save the volume from before any alterations
        self.original_volume = self._getVolume()
        
        # Record the time that playing was started
        # 0 is not playing
        self.startTime = 0

        # Record the number of items in the playlist
        self.playlistSize = 1
        
        # Time the track started playing
        self.trackEndTime = -1
        
        # Record the number of tracks left to play in the playlist
        # (Only used if skipping through tracks)
        self.remainingTracks = -1
        
        # Save off the current repeat state before we started playing anything
        if xbmc.getCondVisibility('Playlist.IsRepeat'):
            self.repeat = "all"
        elif xbmc.getCondVisibility('Playlist.IsRepeatOne'):
            self.repeat = "one"
        else:
            self.repeat = "off"

        xbmc.Player.__init__(self, *args)
        
    def onPlayBackStopped(self):
        log("Player: Received onPlayBackStopped")
        self.restoreSettings()
        xbmc.Player.onPlayBackStopped(self)

    def onPlayBackEnded(self):
        log("Player: Received onPlayBackEnded")
        self.restoreSettings()
        xbmc.Player.onPlayBackEnded(self)

    def restoreSettings(self):
        log("Player: Restoring player settings" )
        while self.isPlayingAudio():
            xbmc.sleep(1)
        # Force the volume to the starting volume
        self._setVolume(self.original_volume)
        # restore repeat state
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "%s" }, "id": 1 }' % self.repeat)
        # Record the time that playing was started (0 is stopped)
        self.startTime = 0
        log("Player: Restored volume to %d" % self.original_volume )


    def stop(self):
        log("Player: stop called")
        # Only stop if playing audio
        if self.isPlayingAudio():
            xbmc.Player.stop(self)
        self.restoreSettings()

    def play(self, item=None, listitem=None, windowed=False, fastFade=False):
        # if something is already playing, then we do not want
        # to replace it with the theme
        if not self.isPlaying():
            # Perform and lowering of the sound for theme playing
            self._lowerVolume()

            if Settings.isFadeIn():
                # Get the current volume - this is out target volume
                targetVol = self._getVolume()
                cur_vol_perc = 1

                # Calculate how fast to fade the theme, this determines
                # the number of step to drop the volume in
                numSteps = 10
                if fastFade:
                    numSteps = numSteps/2

                vol_step = targetVol / numSteps
                # Reduce the volume before starting
                # do not mute completely else the mute icon shows up
                self._setVolume(1)
                # Now start playing before we start increasing the volume
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

                # Wait until playing has started
                while not self.isPlayingAudio():
                    xbmc.sleep(30)

                for step in range (0,(numSteps-1)):
                    # If the system is going to be shut down then we need to reset
                    # everything as quickly as possible
                    if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                        log("Player: Shutdown menu detected, cancelling fade in")
                        break
                    vol = cur_vol_perc + vol_step
                    log( "Player: fadeIn_vol: %s" % str(vol) )
                    self._setVolume(vol)
                    cur_vol_perc = vol
                    xbmc.sleep(200)
                # Make sure we end on the correct volume
                self._setVolume(targetVol)
            else:
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

            if Settings.isLoop():
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "all" }, "id": 1 }')
                # If we had a random start and we are looping then we need to make sure
                # when it comes to play the theme for a second time it starts at the beginning
                # and not from the same mid-point
                if Settings.isRandomStart():
                    item[0].setProperty('StartOffset', "0")
            else:
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')

            # Record the time that playing was started
            self.startTime = int(time.time())
            
            # Save off the number of items in the playlist
            if item != None:
                self.playlistSize = item.size()
                log("Player: Playlist size = %d" % self.playlistSize)
                # Check if we are limiting each track in the list
                if not Settings.isLoop():
                    # Already started laying the first, so the remaining number of
                    # tracks is one less than the total
                    self.remainingTracks = self.playlistSize - 1;
                self._setNextSkipTrackTime(self.startTime)
            else:
                self.playlistSize = 1


    # This will return the volume in a range of 0-100
    def _getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = simplejson.loads(result)
        if "result" in json_query and json_query['result'].has_key('volume'):
            # Get the volume value
            volume = json_query['result']['volume']

        log( "Player: current volume: %s%%" % str(volume) )
        return volume

    # Sets the volume in the range 0-100
    def _setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % newvolume, True)


    def _lowerVolume( self ):
        try:
            if Settings.getDownVolume() != 0:
                current_volume = self._getVolume()
                vol = current_volume- Settings.getDownVolume()
                # Make sure the volume still has a value
                if vol < 1 :
                    vol = 1
                log( "Player: volume goal: %d%% " % vol )
                self._setVolume(vol)
            else:
                log( "Player: No reduced volume option set" )
        except:
            print_exc()

    # Graceful end of the playing, will fade if set to do so
    def endPlaying(self, fastFade=False, slowFade=False):
        if self.isPlayingAudio() and Settings.isFadeOut():
            cur_vol = self._getVolume()
            
            # Calculate how fast to fade the theme, this determines
            # the number of step to drop the volume in
            numSteps = 10
            if fastFade:
                numSteps = numSteps/2
            elif slowFade:
                numSteps = numSteps * 4

            vol_step = cur_vol / numSteps
            # do not mute completely else the mute icon shows up
            for step in range (0,(numSteps-1)):
                # If the system is going to be shut down then we need to reset
                # everything as quickly as possible
                if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                    log("Player: Shutdown menu detected, cancelling fade out")
                    break
                vol = cur_vol - vol_step
                log( "Player: fadeOut_vol: %s" % str(vol) )
                self._setVolume(vol)
                cur_vol = vol
                xbmc.sleep(200)
            # The final stop and reset of the settings will be done
            # outside of this "if"
        # Need to always stop by the end of this
        self.stop()

    # Checks if the play duration has been exceeded and then stops playing 
    def checkEnding(self):
        if self.isPlayingAudio() and (self.startTime > 0):
            # Get the current time
            currTime = int(time.time())

            # Time in minutes to play for
            durationLimit = Settings.getPlayDurationLimit();
            if durationLimit > 0:
                expectedEndTime = self.startTime + (60 * durationLimit)
                
                if currTime > expectedEndTime:
                    self.endPlaying(slowFade=True)
                    return

            # Check for the case where only a given amount of time of the track will be played
            # Only skip forward if there is a track left to play - otherwise just keep
            # playing the last track
            if (self.playlistSize > 1) and (self.remainingTracks != 0):
                trackLimit = Settings.getTrackLengthLimit()
                if trackLimit > 0:
                    if currTime > self.trackEndTime:
                        log("Player: Skipping to next track after %s" % self.getPlayingFile())
                        self.playnext()
                        if self.remainingTracks != -1:
                            self.remainingTracks = self.remainingTracks - 1
                        self._setNextSkipTrackTime(currTime)

    # Calculates the next time that "playnext" on a playlist should be called
    def _setNextSkipTrackTime(self, currentTime):
        trackLimit = Settings.getTrackLengthLimit()
        if trackLimit < 1:
            self.trackEndTime = -1
            return
        self.trackEndTime = currentTime + trackLimit
        trackLength = int(self.getTotalTime())
        log("Player: track length = %d" % trackLength)
        if trackLimit > trackLength and (Settings.isLoop() or self.remainingTracks > 0):
            self.remainingTracks = self.remainingTracks - 1
            self.trackEndTime = self.trackEndTime + trackLength
        
        

###############################################################
# Class to make it easier to see which screen is being checked
###############################################################
class WindowShowing():
    @staticmethod
    def isHome():
        return xbmc.getCondVisibility("Window.IsVisible(home)")

    @staticmethod
    def isVideoLibrary():
        return xbmc.getCondVisibility("Window.IsVisible(videolibrary)") or WindowShowing.isTvTunesOverrideTvShows() or WindowShowing.isTvTunesOverrideMovie()

    @staticmethod
    def isMovieInformation():
        return xbmc.getCondVisibility("Window.IsVisible(movieinformation)") or WindowShowing.isTvTunesOverrideMovie()

    @staticmethod
    def isTvShows():
        return xbmc.getCondVisibility("Container.Content(tvshows)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isSeasons():
        return xbmc.getCondVisibility("Container.Content(Seasons)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isEpisodes():
        return xbmc.getCondVisibility("Container.Content(Episodes)") or WindowShowing.isTvTunesOverrideTvShows()

    @staticmethod
    def isMovies():
        return xbmc.getCondVisibility("Container.Content(movies)") or WindowShowing.isTvTunesOverrideMovie()

    @staticmethod
    def isScreensaver():
        return xbmc.getCondVisibility("System.ScreenSaverActive")

    @staticmethod
    def isShutdownMenu():
        return xbmc.getCondVisibility("Window.IsVisible(shutdownmenu)")

    @staticmethod
    def isTvTunesOverrideTvShows():
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return win.getProperty("TvTunesSupported").lower() == "tvshows"

    @staticmethod
    def isTvTunesOverrideMovie():
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return win.getProperty("TvTunesSupported").lower() == "movies"

    # Works out if the custom window option to play the TV Theme is set
    # and we have just opened a dialog over that
    @staticmethod
    def isTvTunesOverrideContinuePrevious():
        if WindowShowing.isTvTunesOverrideTvShows() or WindowShowing.isTvTunesOverrideMovie():
            # Check if this is a dialog, in which case we just continue playing
            try: dialogid = xbmcgui.getCurrentWindowDialogId()
            except: dialogid = 9999
            if dialogid != 9999:
                # Is a dialog so return True
                return True
        return False

    @staticmethod
    def isRecentEpisodesAdded():
        folderPathId = "videodb://5/"
        # The ID for the Recent Episodes changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://recentlyaddedepisodes/"
        return xbmc.getInfoLabel( "container.folderpath" ) == folderPathId

    @staticmethod
    def isTvShowTitles(currentPath=None):
        folderPathId = "videodb://2/2/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://tvshows/titles/"
        if currentPath == None:
            return xbmc.getInfoLabel( "container.folderpath" ) == folderPathId
        else:
            return currentPath == folderPathId

    @staticmethod
    def isPluginPath():
        return "plugin://" in xbmc.getInfoLabel( "ListItem.Path" )

    @staticmethod
    def isMovieSet():
        folderPathId = "videodb://1/7/"
        # The ID for the TV Show Title changed in Gotham
        if Settings.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://movies/sets/"
        return xbmc.getCondVisibility("!IsEmpty(ListItem.DBID) + SubString(ListItem.Path," + folderPathId + ",left)")


###############################################################
# Class to make it easier to see the current state of TV Tunes
###############################################################
class TvTunesStatus():
    @staticmethod
    def isAlive():
        return xbmcgui.Window( 10025 ).getProperty( "TvTunesIsAlive" ) == "true"
    
    @staticmethod
    def setAliveState(state):
        if state:
            xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
        else:
            xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

    @staticmethod
    def clearRunningState():
        xbmcgui.Window( 10025 ).clearProperty('TvTunesIsRunning')

    # Check if the is a different version running
    @staticmethod
    def isOkToRun():
        # Get the current thread ID
        curThreadId = threading.currentThread().ident
        log("TvTunesStatus: Thread ID = %d" % curThreadId)

        # Check if the "running state" is set
        existingvalue = xbmcgui.Window( 10025 ).getProperty("TvTunesIsRunning")
        if existingvalue == "":
            log("TvTunesStatus: Current running state is empty, setting to %d" % curThreadId)
            xbmcgui.Window( 10025 ).setProperty( "TvTunesIsRunning", str(curThreadId) )
        else:
            # If it is check if it is set to this thread value
            if existingvalue != str(curThreadId):
                log("TvTunesStatus: Running ID already set to %s" % existingvalue)
                return False
        # Default return True unless we have a good reason not to run
        return True

# Class to handle delaying the start of playing a theme 
class DelayedStartTheme():
    def __init__(self):
        self.themesToStart = None
        self.anchorTime = 0

    def shouldStartPlaying(self, themes):
        delaySeconds = Settings.getStartDelaySeconds()

        # Check is the start playing should be delayed
        if delaySeconds < 1:
            # Start playing straight away, but check for List playing built in delay first
            return self._checkListPlayingDelay(themes)

        currentTime = int(time.time())

        if themes != self.themesToStart:
            log("DelayedStartTheme: Themes do not match, new anchor = %s" % str(currentTime))
            self.themesToStart = themes
            # Reset the current time as we need the delay from here
            self.anchorTime = currentTime
        else:
            log("DelayedStartTheme: Target time = %s current time = %s" % (str(self.anchorTime + delaySeconds), str(currentTime)) )
            # Themes are the same, see if it is time to play the the theme yet
            if currentTime > (self.anchorTime + delaySeconds):
                log("DelayedStartTheme: Start playing")
                # Now we are going to start the theme, clear the values
                self.clear()
                return True
        return False
    
    def clear(self):
        self.themesToStart = None
        self.anchorTime = 0

    # Method to support a small delay if running on the list screen
    def _checkListPlayingDelay(self, themes):
        # Check if we are playing themes on the list view, in which case we will want to delay them
        if (Settings.isPlayMovieList() and WindowShowing.isMovies()) or (Settings.isPlayTvShowList() and WindowShowing.isTvShowTitles()):
            log("DelayedStartTheme: Movie List playing delay detected, anchorTime = %s" % str(self.anchorTime))
            if themes != self.themesToStart:
                # Theme selection has changed
                self.themesToStart = themes
                # Reset the current time as we need the delay from here
                self.anchorTime = 2 # for movie list delay, it is just a counter
            else:
                # reduce the anchor by one
                self.anchorTime = self.anchorTime - 1
                if self.anchorTime < 1:
                    self.clear()
                    return True
            return False

        # Default is to allow playing
        return True

#
# Thread to run the program back-end in
#
class TunesBackend( ):
    def __init__( self ):
        self.themePlayer = Player()
        self._stop = False
        log( "### starting TvTunes Backend ###" )
        self.newThemeFiles = ThemeFiles("")
        self.oldThemeFiles = ThemeFiles("")
        self.prevThemeFiles = ThemeFiles("")
        self.delayedStart = DelayedStartTheme()
        
    def run( self ):
        try:
            # Before we actually start playing something, make sure it is OK
            # to run, need to ensure there are not multiple copies running
            if not TvTunesStatus.isOkToRun():
                return

            while (not self._stop):
                # If shutdown is in progress, stop quickly (no fade out)
                if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                    self.stop()
                    break

                # We only stop looping and exit this script if we leave the Video library
                # We get called when we enter the library, and the only times we will end
                # will be if:
                # 1) A Video is selected to play
                # 2) We exit to the main menu away from the video view
                if (not WindowShowing.isVideoLibrary()) or WindowShowing.isScreensaver() or Settings.isTimout():
                    log("TunesBackend: Video Library no longer visible")
                    # End playing cleanly (including any fade out) and then stop everything
                    if TvTunesStatus.isAlive():
                        self.themePlayer.endPlaying()
                    self.stop()
                    
                    # It may be possible that we stopped for the screen-saver about to kick in
                    # If we are using Gotham or higher, it is possible for us to re-kick off the
                    # screen-saver, otherwise the action of us stopping the theme will reset the
                    # timeout and the user will have to wait longer
                    if Settings.isTimout() and (Settings.getXbmcMajorVersion() > 12):
                        xbmc.executebuiltin("xbmc.ActivateScreensaver", True)
                    break

                # There is a valid page selected and there is currently nothing playing
                if self.isPlayingZone() and not WindowShowing.isTvTunesOverrideContinuePrevious():
                    newThemes = self.getThemes()
                    if( self.newThemeFiles != newThemes):
                        self.newThemeFiles = newThemes

                # Check if the file path has changed, if so there is a new file to play
                if self.newThemeFiles != self.oldThemeFiles and self.newThemeFiles.hasThemes():
                    log( "TunesBackend: old path: %s" % self.oldThemeFiles.getPath() )
                    log( "TunesBackend: new path: %s" % self.newThemeFiles.getPath() )
                    if self.start_playing():
                        self.oldThemeFiles = self.newThemeFiles

                # There is no theme at this location, so make sure we are stopped
                if not self.newThemeFiles.hasThemes() and self.themePlayer.isPlayingAudio() and TvTunesStatus.isAlive():
                    self.themePlayer.endPlaying()
                    self.oldThemeFiles.clear()
                    self.prevThemeFiles.clear()
                    self.delayedStart.clear()
                    TvTunesStatus.setAliveState(False)

                # This will occur when a theme has stopped playing, maybe is is not set to loop
                if TvTunesStatus.isAlive() and not self.themePlayer.isPlayingAudio():
                    log( "TunesBackend: playing ends" )
                    self.themePlayer.restoreSettings()
                    TvTunesStatus.setAliveState(False)

                # This is the case where the user has moved from within an area where the themes
                # to an area where the theme is no longer played, so it will trigger a stop and
                # reset everything to highlight that nothing is playing
                # Note: TvTunes is still running in this case, just not playing a theme
                if not self.isPlayingZone():
                    log( "TunesBackend: reinit condition" )
                    self.newThemeFiles.clear()
                    self.oldThemeFiles.clear()
                    self.prevThemeFiles.clear()
                    self.delayedStart.clear()
                    log( "TunesBackend: end playing" )
                    if self.themePlayer.isPlaying() and TvTunesStatus.isAlive():
                        self.themePlayer.endPlaying()
                    TvTunesStatus.setAliveState(False)

                self.themePlayer.checkEnding()

                # Wait a little before starting the check again
                xbmc.sleep(200)

        except:
            print_exc()
            self.stop()

    # Works out if the currently displayed area on the screen is something
    # that is deemed a zone where themes should be played
    def isPlayingZone(self):
        if WindowShowing.isRecentEpisodesAdded():
            return False
        if WindowShowing.isPluginPath():
            return False
        if WindowShowing.isMovieInformation():
            return True
        if WindowShowing.isSeasons():
            return True
        if WindowShowing.isEpisodes():
            return True
        # Only valid is wanting theme on movie list
        if WindowShowing.isMovies() and Settings.isPlayMovieList():
            return True
        # Only valid is wanting theme on TV list
        if WindowShowing.isTvShowTitles() and Settings.isPlayTvShowList():
            return True
        # Any other area is deemed to be a non play area
        return False

    # Locates the path to look for a theme to play based on what is
    # currently being displayed on the screen
    def getThemes(self):
        themePath = ""

        # Check if the files are stored in a custom path
        if Settings.isCustomPathEnabled():
            if not WindowShowing.isMovies():
                videotitle = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            else:
                videotitle = xbmc.getInfoLabel( "ListItem.Title" )
            videotitle = normalize_string( videotitle )
            themePath = os_path_join(Settings.getCustomPath(), videotitle)

        # Looking at the TV Show information page
        elif WindowShowing.isMovieInformation() and (WindowShowing.isTvShowTitles() or WindowShowing.isTvShows()):
            themePath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" )
        else:
            themePath = xbmc.getInfoLabel( "ListItem.Path" )

        log("TunesBackend: themePath = %s" % themePath)

        # Check if the selection is a Movie Set
        if WindowShowing.isMovieSet():
            movieSetMap = self._getMovieSetFileList()

            if Settings.isCustomPathEnabled():
                # Need to make the values part (the path) point to the custom path
                # rather than the video file
                for aKey in movieSetMap.keys():
                    videotitle = normalize_string(aKey)
                    movieSetMap[aKey] = os_path_join(Settings.getCustomPath(), videotitle)
 
            if len(movieSetMap) < 1:
                themefile = ThemeFiles("")
            else:
                themefile = ThemeFiles(themePath, movieSetMap.values())

        # When the reference is into the database and not the file system
        # then don't return it
        elif themePath.startswith("videodb:"):
            # If in either the Tv Show List or the Movie list then
            # need to stop the theme is selecting the back button
            if WindowShowing.isMovies() or WindowShowing.isTvShowTitles():
                themefile = ThemeFiles("")
            else:
                # Load the previous theme
                themefile = self.newThemeFiles
        else:
            themefile = ThemeFiles(themePath)

        return themefile

    # Gets the list of movies in a movie set
    def _getMovieSetFileList(self):
        # Create a map for Program name to video file
        movieSetMap = dict()
        
        # Check if the selection is a Movie Set
        if WindowShowing.isMovieSet():
            # Get Movie Set Data Base ID
            dbid = xbmc.getInfoLabel( "ListItem.DBID" )
            # Get movies from Movie Set
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovieSetDetails", "params": {"setid": %s, "properties": [ "thumbnail" ], "movies": { "properties":  [ "file", "title"], "sort": { "order": "ascending",  "method": "title" }} },"id": 1 }' % dbid)
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = simplejson.loads(json_query)
            if "result" in json_query and json_query['result'].has_key('setdetails'):
                # Get the list of movies paths from the movie set
                items = json_query['result']['setdetails']['movies']
                for item in items:
                    log("TunesBackend: Movie Set file (%s): %s" % (item['title'], item['file']))
                    movieSetMap[item['title']] = item['file']

        return movieSetMap


    # Returns True is started playing, False is delayed
    def start_playing( self ):
        playlist = self.newThemeFiles.getThemePlaylist()

        if self.newThemeFiles.hasThemes():
            if self.newThemeFiles == self.prevThemeFiles: 
                log("TunesBackend: Not playing the same files twice %s" % self.newThemeFiles.getPath() )
                return True # don't play the same tune twice (when moving from season to episodes etc)
            # Value that will force a quicker than normal fade in and out
            # this is needed if switching from one theme to the next, we
            # do not want a long pause starting and stopping
            fastFadeNeeded = False
            # Check if a theme is already playing, if there is we will need
            # to stop it before playing the new theme
            # Stop any audio playing
            if self.themePlayer.isPlayingAudio(): # and self.prevThemeFiles.hasThemes()
                fastFadeNeeded = True
                log("TunesBackend: Stopping previous theme: %s" % self.prevThemeFiles.getPath())
                self.themePlayer.endPlaying(fastFade=fastFadeNeeded)
            
            # Check if this should be delayed
            if not self.delayedStart.shouldStartPlaying(self.newThemeFiles):
                return False

            # Store the new theme that is being played
            self.prevThemeFiles = self.newThemeFiles
            TvTunesStatus.setAliveState(True)
            log("TunesBackend: start playing %s" % self.newThemeFiles.getPath() )
            self.themePlayer.play( playlist, fastFade=fastFadeNeeded )
        else:
            log("TunesBackend: no themes found for %s" % self.newThemeFiles.getPath() )
        return True


    def stop( self ):
        log("TunesBackend: ### Stopping TvTunes Backend ###")
        if TvTunesStatus.isAlive() and not self.themePlayer.isPlayingVideo(): 
            log("TunesBackend: stop playing")
            self.themePlayer.stop()
            while self.themePlayer.isPlayingAudio():
                xbmc.sleep(50)
        TvTunesStatus.setAliveState(False)
        TvTunesStatus.clearRunningState()

        # If currently playing a video file, then we have been overridden,
        # and we need to restore all the settings, the player callbacks
        # will not be called, so just force it on stop
        self.themePlayer.restoreSettings()

        log("TunesBackend: ### Stopped TvTunes Backend ###")
        self._stop = True


#########################
# Main
#########################


# Make sure that we are not already running on another thread
# we do not want two running at the same time
if TvTunesStatus.isOkToRun():
    # Check if the video info button should be hidden, we do this here as this will be
    # called when the video info screen is loaded, it can then be read by the skin
    # when it comes to draw the button
    if Settings.hideVideoInfoButton():
        xbmcgui.Window( 12003 ).setProperty( "TvTunes_HideVideoInfoButton", "true" )
    else:
        xbmcgui.Window( 12003 ).clearProperty("TvTunes_HideVideoInfoButton")
    
    # Create the main class to control the theme playing
    main = TunesBackend()

    # Start the themes running
    main.run()
else:
    log("TvTunes Already Running")



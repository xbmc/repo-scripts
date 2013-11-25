# -*- coding: utf-8 -*-
#Modules General
from traceback import print_exc
import os
import re
import random
import threading
import time
from xml.etree.ElementTree import ElementTree
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
    try: text = unicodedata.normalize( 'NFKD', _unicode( text ) ).encode( 'ascii', 'ignore' )
    except: pass
    return text

##############################
# Stores Various Settings
##############################
class Settings():
    xbmcMajorVersion = 0
    
    def __init__( self ):
        # Load the other settings from the addon setting menu
        self.enable_custom_path = __addon__.getSetting("custom_path_enable")
        if self.enable_custom_path == "true":
            self.custom_path = __addon__.getSetting("custom_path")
        self.themeRegEx = self._loadThemeFileRegEx()
        self.screensaverTime = self._loadScreensaverSettings()


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
    def _loadScreensaverSettings(self):
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

#     def _loadScreensaverSettings(self):
#         screenTimeOutSeconds = -1
#         pguisettings = xbmc.translatePath('special://profile/guisettings.xml')
# 
#         log("Settings: guisettings.xml location = " + pguisettings)
# 
#         # Make sure we found the file and it exists
#         if os.path.exists(pguisettings):
#             # Create an XML parser
#             elemTree = ElementTree()
#             elemTree.parse(pguisettings)
#             
#             # First check to see if any screensaver is set
#             isEnabled = elemTree.findtext('screensaver/mode')
#             if (isEnabled == None) or (isEnabled == ""):
#                 log("Settings: No Screensaver enabled")
#             else:
#                 log("Settings: Screensaver set to " + isEnabled)
# 
#                 # Get the screensaver setting in minutes
#                 result = elemTree.findtext('screensaver/time')
#                 if result != None:
#                     log("Settings: Screensaver timeout set to " + result)
#                     # Convert from minutes to seconds, also reduce by 30 seconds
#                     # as we want to ensure we have time to stop before the
#                     # screensaver kicks in
#                     screenTimeOutSeconds = (int(result) * 60) - 10
#                 else:
#                     log("Settings: No Screensaver timeout found")
#             
#             del elemTree
#         return screenTimeOutSeconds

    # Calculates the regular expression to use to search for theme files
    def _loadThemeFileRegEx(self):
        fileTypes = "mp3" # mp3 is the default that is always supported
        if(__addon__.getSetting("wma") == 'true'):
            fileTypes = fileTypes + "|wma"
        if(__addon__.getSetting("flac") == 'true'):
            fileTypes = fileTypes + "|flac"
        if(__addon__.getSetting("m4a") == 'true'):
            fileTypes = fileTypes + "|m4a"
        if(__addon__.getSetting("wav") == 'true'):
            fileTypes = fileTypes + "|wav"
        return '(theme[ _A-Za-z0-9.-]*.(' + fileTypes + ')$)'

    def isCustomPathEnabled(self):
        return self.enable_custom_path == 'true'
    
    def getCustomPath(self):
        return self.custom_path
    
    def getDownVolume(self):
        return int(float(__addon__.getSetting("downvolume")))

    def isLoop(self):
        return __addon__.getSetting("loop") == 'true'
    
    def isFadeOut(self):
        return __addon__.getSetting("fadeOut") == 'true'

    def isFadeIn(self):
        return __addon__.getSetting("fadeIn") == 'true'
    
    def isSmbEnabled(self):
        if __addon__.getSetting("smb_share"):
            return True
        else:
            return False

    def getSmbUser(self):
        if __addon__.getSetting("smb_login"):
            return __addon__.getSetting("smb_login")
        else:
            return "guest"
    
    def getSmbPassword(self):
        if __addon__.getSetting("smb_psw"):
            return __addon__.getSetting("smb_psw")
        else:
            return "guest"
    
    def getThemeFileRegEx(self):
        return self.themeRegEx
    
    def isShuffleThemes(self):
        return __addon__.getSetting("shuffle") == 'true'
    
    def isRandomStart(self):
        return __addon__.getSetting("random") == 'true'

    def isTimout(self):
        if self.screensaverTime == -1:
            return False
        # It is a timeout if the idle time is larger that the time stored
        # for when the screensaver is due to kick in
        if (xbmc.getGlobalIdleTime() > self.screensaverTime):
            log("Settings: Stopping due to screensaver")
            return True
        else:
            return False
    
    def isPlayMovieList(self):
        return __addon__.getSetting("movielist") == 'true'

    def isPlayTvShowList(self):
        return __addon__.getSetting("tvlist") == 'true'

    def getPlayDurationLimit(self):
        return int(float(__addon__.getSetting("endafter")))

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
            log("Settings: XBMC Version = " + xbmcVer)
            Settings.xbmcMajorVersion = 12
            try:
                # Get just the major version number
                Settings.xbmcMajorVersion = int(xbmcVer.split(".", 1)[0])
            except:
                # Default to frodo as the default version if we fail to find it
                log("Settings: Failed to get XBMC version")
            log("Settings: XBMC Version %d (%s)" % (Settings.xbmcMajorVersion, xbmcVer))
        return Settings.xbmcMajorVersion


##############################
# Calculates file locations
##############################
class ThemeFiles():
    def __init__(self, settings, rawPath, pathList=None):
        self.settings = settings
        self.forceShuffle = False
        self.rawPath = rawPath
        if rawPath == "":
            self.clear()
        elif (pathList != None) and (len(pathList) > 0):
            self.themeFiles = []
            for aPath in pathList:
                subThemeList = self._generateThemeFilelist(aPath)
                # add these files to the existing list
                self.themeFiles = self._mergeThemeLists(self.themeFiles, subThemeList)
            # If we were given a list, then we should shuffle the themes
            # as we don't always want the first path playing first
            self.forceShuffle = True
        else:
            self.themeFiles = self._generateThemeFilelist(rawPath)

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

        if (self.settings.isShuffleThemes() or self.forceShuffle) and playlist.size() > 1:
            playlist.shuffle()
        
        # Now we have the playlist, and it has been shuffled if needed
        # Check if we need to have a random start time for the first track
        # Note: The following method (rather than seek) should prevent
        # the seek dialog being displayed on the screen and also prevent
        # the need to start the theme playing before changing the start point
        if self.settings.isRandomStart() and playlist.size() > 0:
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
        
        if self.settings.isSmbEnabled() and workingPath.startswith("smb://") : 
            log( "### Try authentication share" )
            workingPath = workingPath.replace("smb://", "smb://%s:%s@" % (self.settings.getSmbUser(), self.settings.getSmbPassword()) )
            log( "### %s" % workingPath )
    
        #######hack for episodes stored as rar files
        if 'rar://' in str(workingPath):
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
    # Calculates the location of the theme file
    #
    def _generateThemeFilelist(self, rawPath):
        # Get the full path with any network alterations
        workingPath = self._getUsablePath(rawPath)

        #######hack for TV shows stored as ripped disc folders
        if 'VIDEO_TS' in str(workingPath):
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

        log("ThemeFiles: Playlist size = " + str(len(themeList)))
        log("ThemeFiles: Working Path = " + workingPath)
        
        return themeList

    def _updir(self, thepath, x):
        # move up x directories on the path
        while x > 0:
            x -= 1
            thepath = (os.path.split(thepath))[0]
        return thepath

    # Search for theme files in the given directory
    def _getThemeFiles(self, directory):
        log( "ThemeFiles: Searching " + directory + " for " + self.settings.getThemeFileRegEx() )
        themeFiles = []
        # check if the directory exists before searching
        if xbmcvfs.exists(directory):
            dirs, files = xbmcvfs.listdir( directory )
            for aFile in files:
                m = re.search(self.settings.getThemeFileRegEx(), aFile, re.IGNORECASE)
                if m:
                    path = os.path.join( directory, aFile ).decode("utf-8")
                    log("ThemeFiles: Found match: " + path)
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
    def __init__(self, settings, *args):
        self.settings = settings
        # Save the volume from before any alterations
        self.original_volume = ( 100 + (self._getVolume() *(100/60.0)))
        
        # Record the time that playing was started
        # 0 is not playing
        self.startTime = 0
        
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
        # restore repeat state
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "%s" }, "id": 1 }' % self.repeat)
        # Force the volume to the starting volume
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % self.original_volume, True)
        # Record the time that playing was started (0 is stopped)
        self.startTime = 0


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

            if self.settings.isFadeIn():
                # Get the current volume - this is out target volume
                targetVol = self._getVolume()
                cur_vol_perc = 1

                # Calculate how fast to fade the theme, this determines
                # the number of step to drop the volume in
                numSteps = 10
                if fastFade:
                    numSteps = numSteps/2

                vol_step = (100 + (targetVol * (100/60.0))) / numSteps
                # Reduce the volume before starting
                # do not mute completely else the mute icon shows up
                xbmc.executebuiltin('XBMC.SetVolume(1)', True)
                # Now start playing before we start increasing the volume
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

                # Wait until playing has started
                while not self.isPlayingAudio():
                    xbmc.sleep(30)

                for step in range (0,(numSteps-1)):
                    vol = cur_vol_perc + vol_step
                    log( "Player: fadeIn_vol: %s" % str(vol) )
                    xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol, True)
                    cur_vol_perc = vol
                    xbmc.sleep(200)
                # Make sure we end on the correct volume
                xbmc.executebuiltin('XBMC.SetVolume(%d)' % ( 100 + (targetVol *(100/60.0))), True)
            else:
                xbmc.Player.play(self, item=item, listitem=listitem, windowed=windowed)

            if self.settings.isLoop():
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "all" }, "id": 1 }')
                # If we had a random start and we are looping then we need to make sure
                # when it comes to play the theme for a second time it starts at the beginning
                # and not from the same mid-point
                if self.settings.isRandomStart():
                    item[0].setProperty('StartOffset', "0")
            else:
                xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Player.SetRepeat", "params": {"playerid": 0, "repeat": "off" }, "id": 1 }')

            # Record the time that playing was started
            self.startTime = time.time()
    

    def _getVolume(self):
        try:
            volume = float(xbmc.getInfoLabel('player.volume').split(".")[0])
        except:
            volume = float(xbmc.getInfoLabel('player.volume').split(",")[0])
        log( "Player: current volume: %s%%" % (( 60 + volume )*(100/60.0)) )
        return volume


    def _lowerVolume( self ):
        try:
            if self.settings.getDownVolume() != 0:
                current_volume = self._getVolume()
                vol = ((60+current_volume- self.settings.getDownVolume() )*(100/60.0))
                if vol < 0 :
                    vol = 0
                log( "Player: volume goal: %d%% " % vol )
                xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol, True)
            else:
                log( "Player: No reduced volume option set" )
        except:
            print_exc()

    # Graceful end of the playing, will fade if set to do so
    def endPlaying(self, fastFade=False, slowFade=False):
        if self.isPlayingAudio() and self.settings.isFadeOut():
            cur_vol = self._getVolume()
            cur_vol_perc = 100 + (cur_vol * (100/60.0))
            
            # Calculate how fast to fade the theme, this determines
            # the number of step to drop the volume in
            numSteps = 10
            if fastFade:
                numSteps = numSteps/2
            elif slowFade:
                numSteps = numSteps * 4

            vol_step = cur_vol_perc / numSteps
            # do not mute completely else the mute icon shows up
            for step in range (0,(numSteps-1)):
                # If the system is going to be shut down then we need to reset
                # everything as quickly as possible
                if WindowShowing.isShutdownMenu() or xbmc.abortRequested:
                    log("Player: Shutdown menu detected, cancelling fade")
                    break
                vol = cur_vol_perc - vol_step
                log( "Player: fadeOut_vol: %s" % str(vol) )
                xbmc.executebuiltin('XBMC.SetVolume(%d)' % vol, True)
                cur_vol_perc = vol
                xbmc.sleep(200)
            # The final stop and reset of the settings will be done
            # outside of this "if"
        # Need to always stop by the end of this
        self.stop()

    # Checks if the play duration has been exceeded and then stops playing 
    def checkEnding(self):
        if self.isPlayingAudio() and (self.startTime > 0):
            # Time in minutes to play for
            durationLimit = self.settings.getPlayDurationLimit();
            if durationLimit > 0:
                # Get the current time
                currTime = time.time()

                expectedEndTime = self.startTime + (60 * durationLimit)
                
                if currTime > expectedEndTime:
                    self.endPlaying(slowFade=True)



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
        log("TvTunesStatus: Thread ID = " + str(curThreadId))

        # Check if the "running state" is set
        existingvalue = xbmcgui.Window( 10025 ).getProperty("TvTunesIsRunning")
        if existingvalue == "":
            log("TvTunesStatus: Current running state is empty, setting to " + str(curThreadId))
            xbmcgui.Window( 10025 ).setProperty( "TvTunesIsRunning", str(curThreadId) )
        else:
            # If it is check if it is set to this thread value
            if existingvalue != str(curThreadId):
                log("TvTunesStatus: Running ID already set to " + existingvalue)
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
            # Start playing straight away
            return True

        currentTime = int(time.time())

        if themes != self.themesToStart:
            log("DelayedStartTheme: Themes do not match, new anchor = " + str(currentTime))
            self.themesToStart = themes
            # Reset the current time as we need the delay from here
            self.anchorTime = currentTime
        else:
            log("DelayedStartTheme: Target time = " + str(self.anchorTime + delaySeconds) + " current time =" + str(currentTime))
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

#
# Thread to run the program back-end in
#
class TunesBackend( ):
    def __init__( self ):
        self.settings = Settings()
        self.themePlayer = Player(settings=self.settings)
        self._stop = False
        log( "### starting TvTunes Backend ###" )
        self.newThemeFiles = ThemeFiles(self.settings, "")
        self.oldThemeFiles = ThemeFiles(self.settings, "")
        self.prevThemeFiles = ThemeFiles(self.settings, "")
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
                if (not WindowShowing.isVideoLibrary()) or WindowShowing.isScreensaver() or self.settings.isTimout():
                    log("TunesBackend: Video Library no longer visible")
                    # End playing cleanly (including any fade out) and then stop everything
                    self.themePlayer.endPlaying()
                    self.stop()
                    
                    # It may be possible that we stopped for the screen-saver about to kick in
                    # If we are using Gotham or higher, it is possible for us to re-kick off the
                    # screen-saver, otherwise the action of us stopping the theme will reset the
                    # timeout and the user will have to wait longer
                    if self.settings.isTimout() and (Settings.getXbmcMajorVersion() > 12):
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
                    if self.themePlayer.isPlaying():
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
        if WindowShowing.isMovies() and self.settings.isPlayMovieList():
            return True
        # Only valid is wanting theme on TV list
        if WindowShowing.isTvShowTitles() and self.settings.isPlayTvShowList():
            return True
        # Any other area is deemed to be a non play area
        return False

    # Locates the path to look for a theme to play based on what is
    # currently being displayed on the screen
    def getThemes(self):
        themePath = ""

        # Check if the files are stored in a custom path
        if self.settings.isCustomPathEnabled():
            if not WindowShowing.isMovies():
                videotitle = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            else:
                videotitle = xbmc.getInfoLabel( "ListItem.Title" )
            videotitle = normalize_string( videotitle.replace(":","") )
            themePath = os.path.join(self.settings.getCustomPath(), videotitle).decode("utf-8")

        # Looking at the TV Show information page
        elif WindowShowing.isMovieInformation() and (WindowShowing.isTvShowTitles() or WindowShowing.isTvShows()):
            themePath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" )
        else:
            themePath = xbmc.getInfoLabel( "ListItem.Path" )

        log("TunesBackend: themePath = " + themePath)

        # Check if the selection is a Movie Set
        if WindowShowing.isMovieSet():
            movieSetMap = self._getMovieSetFileList()

            if self.settings.isCustomPathEnabled():
                # Need to make the values part (the path) point to the custom path
                # rather than the video file
                for aKey in movieSetMap.keys():
                    videotitle = normalize_string(aKey.replace(":","") )
                    movieSetMap[aKey] = os.path.join(self.settings.getCustomPath(), videotitle).decode("utf-8")
 
            if len(movieSetMap) < 1:
                themefile = ThemeFiles(self.settings, "")
            else:
                themefile = ThemeFiles(self.settings, themePath, movieSetMap.values())

        # When the reference is into the database and not the file system
        # then don't return it
        elif themePath.startswith("videodb:"):
            # If in either the Tv Show List or the Movie list then
            # need to stop the theme is selecting the back button
            if WindowShowing.isMovies() or WindowShowing.isTvShowTitles():
                themefile = ThemeFiles(self.settings, "")
            else:
                # Load the previous theme
                themefile = self.newThemeFiles
        else:
            themefile = ThemeFiles(self.settings, themePath)

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
            if self.prevThemeFiles.hasThemes() and self.themePlayer.isPlayingAudio():
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



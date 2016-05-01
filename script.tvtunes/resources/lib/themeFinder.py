# -*- coding: utf-8 -*-
import os
import re
import random
import traceback
import xml.etree.ElementTree as ET
import xbmc
import xbmcgui
import sys
import xbmcvfs

# Add JSON support for queries
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import list_dir
from settings import dir_exists
from settings import os_path_isfile
from settings import normalize_string


#############################################
# Reads TvTunes information from an NFO file
#############################################
class NfoReader():
    def __init__(self, directory, debug_logging_enabled=True):
        self.debug_logging_enabled = debug_logging_enabled
        self.themeFiles = []
        self.themeDirs = []
        self.excludeFromScreensaver = False
        self._loadNfoInfo(directory)

    # Get any themes that were in the NFO file
    def getThemeFiles(self):
        return self.themeFiles

    # Get any theme directories that were in the NFO file
    def getThemeDirs(self):
        return self.themeDirs

    # Check if this theme directory should be excluded from the screensaver
    def getExcludeFromScreensaver(self):
        return self.excludeFromScreensaver

    # Check for an NFO file for this show and reads details out of it
    # if it exists
    def _loadNfoInfo(self, directory):
        # Find out the name of the NFO file
        nfoFileName = os_path_join(directory, "tvtunes.nfo")

        # If this is a plugin path, then don't try and get the NFO file
        if "plugin://" in nfoFileName:
            log("NfoReader: Plugin paths do not support NFO files: %s" % nfoFileName, self.debug_logging_enabled)
            return

        log("NfoReader: Searching for NFO file: %s" % nfoFileName, self.debug_logging_enabled)

        # Return False if file does not exist
        if not xbmcvfs.exists(nfoFileName):
            log("NfoReader: No NFO file found: %s" % nfoFileName, self.debug_logging_enabled)
            return False

        returnValue = False
        checkThemeExists = False

        try:
            # Need to first load the contents of the NFO file into
            # a string, this is because the XML File Parse option will
            # not handle formats like smb://
            nfoFile = xbmcvfs.File(nfoFileName, 'r')
            nfoFileStr = nfoFile.read()
            nfoFile.close()

            # Create an XML parser
            nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr))
            rootElement = nfoXml.getroot()

            log("NfoReader: Root element is = %s" % rootElement.tag, self.debug_logging_enabled)

            # Check which format if being used
            if rootElement.tag == "tvtunes":
                log("NfoReader: TvTunes format NFO detected", self.debug_logging_enabled)
                #    <tvtunes>
                #        <file>theme.mp3</file>
                #        <directory>c:\my\themes</directory>
                #        <playlistfile>playlist.m3u</playlistfile>
                #        <excludeFromScreensaver/>
                #    </tvtunes>

                # There could be multiple file entries, so loop through all of them
                for fileElem in nfoXml.findall('file'):
                    file = None
                    if fileElem is not None:
                        file = fileElem.text

                    if (file is not None) and (file != ""):
                        if file.startswith('..') or (("/" not in file) and ("\\" not in file)):
                            # Make it a full path if it is not already
                            file = os_path_join(directory, file)
                        log("NfoReader: file = %s" % file, self.debug_logging_enabled)
                        self.themeFiles.append(file)

                # There could be multiple directory entries, so loop through all of them
                for dirElem in nfoXml.findall('directory'):
                    dir = None
                    if dirElem is not None:
                        dir = dirElem.text

                    if (dir is not None) and (dir != ""):
                        if dir.startswith('..') or (("/" not in dir) and ("\\" not in dir)):
                            # Make it a full path if it is not already
                            dir = os_path_join(directory, dir)
                        log("NfoReader: directory = %s" % dir, self.debug_logging_enabled)
                        self.themeDirs.append(dir)

                # Check for the playlist files
                for playlistFileElem in nfoXml.findall('playlistfile'):
                    playlistFile = None
                    if playlistFileElem is not None:
                        playlistFile = playlistFileElem.text

                    self._addFilesFromPlaylist(playlistFile, directory)

                # Check if this directory should be excluded from the screensaver
                for playlistFileElem in nfoXml.findall('excludeFromScreensaver'):
                    self.excludeFromScreensaver = True

                # Check if there may be theme paths that do not exist and we should
                # check each theme to see if they they can be accessed
                for playlistFileElem in nfoXml.findall('checkThemeExists'):
                    checkThemeExists = True

                returnValue = True
            else:
                self.displayName = None
                self.orderKey = None
                log("NfoReader: Unknown NFO format", self.debug_logging_enabled)

            del nfoXml
        except:
            log("NfoReader: Failed to process NFO: %s" % nfoFileName, True, xbmc.LOGERROR)
            log("NfoReader: %s" % traceback.format_exc(), True, xbmc.LOGERROR)
            returnValue = False

        # Not that the entire NFO file has been read, see if we need to verify
        # that each of the themes exists
        if checkThemeExists:
            # Check the theme files to make sure they all exist
            existingThemeFiles = []
            for nfoThemeFile in self.themeFiles:
                if xbmcvfs.exists(nfoThemeFile):
                    existingThemeFiles.append(nfoThemeFile)
                else:
                    log("NfoReader: File does not exists, removing %s" % nfoThemeFile, self.debug_logging_enabled)
            self.themeFiles = existingThemeFiles

            # Check the theme directories to make sure they all exist
            existingThemeDir = []
            for nfoThemeDir in self.themeDirs:
                if dir_exists(nfoThemeDir):
                    existingThemeDir.append(nfoThemeDir)
                else:
                    log("NfoReader: Directory does not exists, removing %s" % nfoThemeDir, self.debug_logging_enabled)
            self.themeDirs = existingThemeDir

        return returnValue

    # Adds tracks in a playlist to the list of theme files to play
    def _addFilesFromPlaylist(self, playlistFile, directory):
        if (playlistFile is None) or (playlistFile == ""):
            return

        fileExt = os.path.splitext(playlistFile)[1]

        # Check if dealing with a Smart Playlist
        if fileExt == ".xsp":
            # Process the Smart Playlist
            self._addFilesFromSmartPlaylist(playlistFile)
            return

        if ("/" not in playlistFile) and ("\\" not in playlistFile):
            # There is just the filename of the playlist without
            # a path, check if the file is local or if we should
            # read it from the user directory
            # Check if there is an extension on the name
            if fileExt is None or fileExt == "":
                playlistFile = playlistFile + ".m3u"
            localFile = os_path_join(directory, playlistFile)
            if xbmcvfs.exists(localFile):
                # Make it a full path if it is not already
                playlistFile = localFile
            else:
                # default to the music playlist directory if not local
                playlistFile = os_path_join(xbmc.translatePath("special://musicplaylists"), playlistFile)

        log("NfoReader: playlist file = %s" % playlistFile, self.debug_logging_enabled)

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
                    if (file is not None) and (file != ""):
                        log("NfoReader: file from playlist = %s" % file, self.debug_logging_enabled)
                        self.themeFiles.append(file)
            except:
                log("NfoReader: playlist file processing error = %s" % playlistFile, True, xbmc.LOGERROR)
        else:
            log("NfoReader: playlist file not found = %s" % playlistFile, self.debug_logging_enabled)

    # Adds tracks in a Smart playlist to the list of theme files to play
    def _addFilesFromSmartPlaylist(self, playlistFile):
        if "/" not in playlistFile:
            playlistFile = "special://musicplaylists/" + playlistFile

        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": { "directory": "%s", "media": "music" },  "id": 1}' % playlistFile)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_query = simplejson.loads(json_query)

        if ("result" in json_query) and ('files' in json_query['result']):
            # Get the list of movies paths from the movie set
            items = json_query['result']['files']
            for item in items:
                log("NfoReader: Adding From Smart Playlist: %s" % item['file'], self.debug_logging_enabled)
                self.themeFiles.append(item['file'])


##############################
# Calculates file locations
##############################
class ThemeFiles():
    def __init__(self, rawPath, pathList=None, videotitle=None, debug_logging_enabled=True, audioOnly=False):
        self.debug_logging_enabled = debug_logging_enabled
        self.forceShuffle = False
        self.doNotShuffle = False
        self.audioOnly = audioOnly
        self.rawPath = rawPath
        if rawPath in [None, ""]:
            self.clear()
        else:
            # Check for the case where there is a custom path set so we need to use
            # the custom location rather than the rawPath
            if Settings.isCustomPathEnabled() and (videotitle not in [None, ""]):
                customRoot = Settings.getCustomPath()
                # Make sure that the path passed in has not already been converted
                if customRoot not in self.rawPath:
                    self.rawPath = os_path_join(customRoot, normalize_string(videotitle))
                    log("ThemeFiles: Setting custom path to %s" % self.rawPath, self.debug_logging_enabled)

            if (pathList is not None) and (len(pathList) > 0):
                self.themeFiles = []
                for aPath in pathList:
                    subThemeList = self._generateThemeFilelistWithDirs(aPath)
                    # add these files to the existing list
                    self.themeFiles = self._mergeThemeLists(self.themeFiles, subThemeList)
                # If we were given a list, then we should shuffle the themes
                # as we don't always want the first path playing first
                self.forceShuffle = True
            else:
                self.themeFiles = self._generateThemeFilelistWithDirs(self.rawPath)

        # Check if we need to handle the ordering for video themes
        if not audioOnly:
            self.doNotShuffle = self._filterForVideoThemesRule()
            self.forceShuffle = False

    # Define the equals to be based off of the list of theme files
    def __eq__(self, other):
        try:
            if isinstance(other, ThemeFiles):
                # If the lengths are not the same, there is no chance of a match
                if len(self.themeFiles) != len(other.themeFiles):
                    return False
                # Make sure each file in the list is also in the source list
                for aFile in other.themeFiles:
                    if self.themeFiles.count(aFile) < 1:
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

    # Get the list of themes with their full paths
    def getThemeLocations(self):
        return self.themeFiles

    # Returns the playlist for the themes
    def getThemePlaylist(self):
        # Take the list of files and create a playlist from them
        # Needs to be a Music playlist otherwise repeat will not work
        # via the JSON interface
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        for aFile in self.themeFiles:
            # Add the theme file to a playlist
            playlist.add(url=aFile)

        # Check if we have more than one item in the playlist
        if playlist.size() > 1:
            # Check if we need to perform a shuffle of the available themes
            if (not self.doNotShuffle) and (Settings.isShuffleThemes() or self.forceShuffle):
                playlist.shuffle()
            # Check if we are only supposed to play one theme when there are multiple
            # available
            if Settings.onlyPlaySingleTheme():
                firstTheme = playlist[0].getfilename()
                playlist.clear()
                playlist.add(url=firstTheme)

        # Now we have the playlist, and it has been shuffled if needed
        # Check if we need to have a random start time for the first track
        # Note: The following method (rather than seek) should prevent
        # the seek dialog being displayed on the screen and also prevent
        # the need to start the theme playing before changing the start point
        if Settings.isRandomStart() and playlist.size() > 0:
            filename = playlist[0].getfilename()
            duration = int(playlist[0].getduration())

            log("ThemeFiles: Duration is %d for file %s" % (duration, filename), self.debug_logging_enabled)

            if duration > 10:
                listitem = xbmcgui.ListItem()
                # Record if the theme should start playing part-way through
                randomStart = random.randint(0, int(duration * 0.75))
                listitem.setProperty('StartOffset', str(randomStart))

                log("ThemeFiles: Setting Random start of %d for %s" % (randomStart, filename), self.debug_logging_enabled)

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

        if Settings.isSmbEnabled() and not ('@' in workingPath):
            if workingPath.startswith("smb://"):
                log("### Try authentication share")
                workingPath = workingPath.replace("smb://", "smb://%s:%s@" % (Settings.getSmbUser(), Settings.getSmbPassword()))
                log("### %s" % workingPath)
            # Also handle the apple format
            elif workingPath.startswith("afp://"):
                log("### Try authentication share")
                workingPath = workingPath.replace("afp://", "afp://%s:%s@" % (Settings.getSmbUser(), Settings.getSmbPassword()))
                log("### %s" % workingPath)

        # handle episodes stored as rar files
        if workingPath.startswith("rar://"):
            workingPath = workingPath.replace("rar://", "")

        # Support special paths like smb:// means that we can not just call
        # os.path.isfile as it will return false even if it is a file
        # (A bit of a shame - but that's the way it is)
        fileExt = None
        if workingPath.startswith("smb://") or workingPath.startswith("afp://") or os_path_isfile(workingPath):
            fileExt = os.path.splitext(workingPath)[1]
        # If this is a file, then get it's parent directory
        # Also limit file extensions to a maximum of 4 characters
        if fileExt is not None and fileExt != "" and len(fileExt) < 5:
            workingPath = os_path_split(workingPath)[0]

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
            themeDir = os_path_join(themeDir, Settings.getThemeDirectory())
            themeFiles = self._generateThemeFilelist(themeDir)

        # Check for the case where there is a DVD directory and the themes
        # directory is above it
        if len(themeFiles) < 1:
            if ('VIDEO_TS' in rawPath) or ('BDMV' in rawPath):
                log("ThemeFiles: Found VIDEO_TS in path: Correcting the path for DVDR tv shows", self.debug_logging_enabled)
                themeDir = self._getUsablePath(rawPath)
                themeDir = os_path_split(themeDir)[0]
                themeDir = os_path_join(themeDir, Settings.getThemeDirectory())
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

        themeList = self._getThemeFiles(workingPath)

        # If no themes have been found
        if len(themeList) < 1:
            # TV shows stored as ripped disc folders
            if ('VIDEO_TS' in workingPath) or ('BDMV' in workingPath):
                log("ThemeFiles: Found VIDEO_TS or BDMV in path: Correcting the path for DVDR tv shows", self.debug_logging_enabled)
                workingPath = os_path_split(workingPath)[0]
                themeList = self._getThemeFiles(workingPath)
                if len(themeList) < 1:
                    workingPath = os_path_split(workingPath)[0]
                    themeList = self._getThemeFiles(workingPath)
            else:
                # If no theme files were found in this path, look at the parent directory
                workingPath = os_path_split(workingPath)[0]

                # Check for the case where there is the theme forlder settings, we want to
                # check the parent folders themes directory
                if Settings.isThemeDirEnabled():
                    themeDir = os_path_join(workingPath, Settings.getThemeDirectory())
                    themeList = self._getThemeFiles(themeDir)

                # If there are still no themes, just check the parent directory
                if len(themeList) < 1:
                    themeList = self._getThemeFiles(workingPath)

        log("ThemeFiles: Playlist size = %d" % len(themeList), self.debug_logging_enabled)
        log("ThemeFiles: Working Path = %s" % workingPath, self.debug_logging_enabled)

        return themeList

    # Check if the given directory should be excluded from the screensaver
    def shouldExcludeFromScreensaver(self, rawPath):
        # Get the full path with any network alterations
        workingPath = self._getUsablePath(rawPath)

        nfoRead = NfoReader(workingPath)
        toExclude = nfoRead.getExcludeFromScreensaver()
        del nfoRead
        return toExclude

    # Search for theme files in the given directory
    def _getThemeFiles(self, directory, extensionOnly=False):
        # First read from the NFO file if it exists
        nfoRead = NfoReader(directory, self.debug_logging_enabled)
        themeFiles = nfoRead.getThemeFiles()

        # Get the theme directories that are referenced and process the data in them
        for nfoDir in nfoRead.getThemeDirs():
            # Do not want the theme keyword if looking at an entire directory
            themeFiles = themeFiles + self._getThemeFiles(nfoDir, True)

        del nfoRead
        log("ThemeFiles: Searching %s for %s" % (directory, Settings.getThemeFileRegEx(directory, extensionOnly, self.audioOnly)), self.debug_logging_enabled)

        # Make sure that the path does not point to a plugin, as we are checking the
        # file-system for themes, not plugins. This can be the case with Emby
        if "plugin://" in directory:
            log("ThemeFiles: Plugin paths do not support theme files: %s" % directory, self.debug_logging_enabled)
        else:
            # check if the directory exists before searching
            if dir_exists(directory):
                dirs, files = list_dir(directory)
                for aFile in files:
                    m = re.search(Settings.getThemeFileRegEx(directory, extensionOnly, self.audioOnly), aFile, re.IGNORECASE)
                    if m:
                        path = os_path_join(directory, aFile)
                        log("ThemeFiles: Found match: %s" % path, self.debug_logging_enabled)
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

    # Applies the rules for where the video themes appear in the list
    def _filterForVideoThemesRule(self):
        # Check if we just leave the list as it is
        if not Settings.isVideoThemesFirst() and not Settings.isVideoThemesOnlyIfOneExists():
            return False

        # Go through each file seeing if it ends with one of the expected
        # video formats that we support
        containsVideoFile = False
        for aThemeFile in self.themeFiles:
            if Settings.isVideoFile(aThemeFile):
                containsVideoFile = True
                break

        # Check if there are no video files, so nothing to do
        if not containsVideoFile:
            return False

        # Now strip out anything that is not a video file
        videoThemes = []
        audioThemes = []
        for aThemeFile in self.themeFiles:
            if Settings.isVideoFile(aThemeFile):
                videoThemes.append(aThemeFile)
            else:
                audioThemes.append(aThemeFile)

        # Check if we need to only return video themes if one exists
        # and we don't want audio themes in this case
        if Settings.isVideoThemesOnlyIfOneExists():
            log("ThemeFiles: Removing non video themes", self.debug_logging_enabled)
            self.themeFiles = videoThemes
        elif Settings.isVideoThemesFirst():
            # If we want to shuffle the tracks, then do this before we join the
            # two arrays together
            if Settings.isShuffleThemes():
                random.shuffle(videoThemes)
                random.shuffle(audioThemes)
            self.themeFiles = videoThemes + audioThemes
            return True

        return False


# Class to handle all themes when browsing music
class MusicThemeFiles():
    def __init__(self, debug_logging_enabled=True):
        self.debug_logging_enabled = debug_logging_enabled
        self.themeFiles = self._getThemesForActiveItem()

    # Define the equals to be based off of the list of theme files
    def __eq__(self, other):
        try:
            if isinstance(other, MusicThemeFiles):
                # If the lengths are not the same, there is no chance of a match
                if len(self.themeFiles) != len(other.themeFiles):
                    return False
                # Make sure each file in the list is also in the source list
                for aFile in other.themeFiles:
                    if self.themeFiles.count(aFile) < 1:
                        return False
            else:
                return False
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
        # This is used for logging the theme group that is active
        return "Music-Themes"

    def clear(self):
        self.themeFiles = []

    # Get the list of themes with their full paths
    def getThemeLocations(self):
        return []

    # Returns the playlist for the themes
    def getThemePlaylist(self):
        # Take the list of files and create a playlist from them
        # Needs to be a Music playlist otherwise repeat will not work
        # via the JSON interface
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        for aFile in self.themeFiles:
            # Add the theme file to a playlist
            playlist.add(url=aFile)

        # Check if we have more than one item in the playlist
        if playlist.size() > 1:
            playlist.shuffle()
            # Check if we are only supposed to play one theme when there are multiple
            # available
            if Settings.onlyPlaySingleTheme():
                firstTheme = playlist[0].getfilename()
                playlist.clear()
                playlist.add(url=firstTheme)

        # Now we have the playlist, and it has been shuffled if needed
        # Check if we need to have a random start time for the first track
        # Note: The following method (rather than seek) should prevent
        # the seek dialog being displayed on the screen and also prevent
        # the need to start the theme playing before changing the start point
        if Settings.isRandomStart() and playlist.size() > 0:
            filename = playlist[0].getfilename()
            duration = int(playlist[0].getduration())

            log("MusicThemeFiles: Duration is %d for file %s" % (duration, filename), self.debug_logging_enabled)

            if duration > 10:
                listitem = xbmcgui.ListItem()
                # Record if the theme should start playing part-way through
                randomStart = random.randint(0, int(duration * 0.75))
                listitem.setProperty('StartOffset', str(randomStart))

                log("MusicThemeFiles: Setting Random start of %d for %s" % (randomStart, filename), self.debug_logging_enabled)

                # Remove the old item from the playlist
                playlist.remove(filename)
                # Add the new item at the start of the list
                playlist.add(filename, listitem, 0)

        return playlist

    def shouldExcludeFromScreensaver(self, rawPath):
        # Do not include music themes in the screensaver
        return True

    def _getThemesForActiveItem(self):
        themes = []
        # There could be several sections for the music library so check the different options
        albumArtist = xbmc.getInfoLabel('ListItem.AlbumArtist')
        log("MusicThemeFiles: AlbumArtist is %s" % albumArtist, self.debug_logging_enabled)

        artist = xbmc.getInfoLabel('ListItem.Artist')
        log("MusicThemeFiles: Artist is %s" % artist, self.debug_logging_enabled)

        album = xbmc.getInfoLabel('ListItem.Album')
        log("MusicThemeFiles: Album is %s" % album, self.debug_logging_enabled)

        # Now build up the JSON command using the values we have
        filterValues = []
        if (albumArtist not in [None, ""]):
            albumArtistFilter = '{"operator": "is", "field": "albumartist", "value": "%s"}' % albumArtist
            filterValues.append(albumArtistFilter)

        if (artist not in [None, ""]):
            artistFilter = '{"operator": "is", "field": "artist", "value": "%s"}' % artist
            filterValues.append(artistFilter)

        if (album not in [None, ""]):
            albumFilter = '{"operator": "is", "field": "album", "value": "%s"}' % album
            filterValues.append(albumFilter)

        # Check to ensure there is some music information to search for
        if len(filterValues) < 1:
            log("MusicThemeFiles: No ListItem information for music", self.debug_logging_enabled)
        else:
            # Join all the filters together
            filterStr = ', '.join(filterValues)
            cmd = '{"jsonrpc": "2.0", "method": "AudioLibrary.GetSongs", "params": {"properties": ["title", "file"], "filter": { "and": [%s] }},"id": 1 }' % filterStr
            json_query = xbmc.executeJSONRPC(cmd)
            json_query = simplejson.loads(json_query)
            log("MusicThemeFiles: json reply %s" % str(json_query), self.debug_logging_enabled)
            if ("result" in json_query) and ('songs' in json_query['result']):
                # Get the list of movies paths from the movie set
                items = json_query['result']['songs']
                for item in items:
                    log("MusicThemeFiles: Audio Theme file: %s" % item['file'], self.debug_logging_enabled)
                    themes.append(item['file'])

        return themes

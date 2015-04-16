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

        log("NfoReader: Searching for NFO file: %s" % nfoFileName, self.debug_logging_enabled)

        # Return False if file does not exist
        if not xbmcvfs.exists(nfoFileName):
            log("NfoReader: No NFO file found: %s" % nfoFileName, self.debug_logging_enabled)
            return False

        returnValue = False

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
    def __init__(self, rawPath, pathList=None, debug_logging_enabled=True):
        self.debug_logging_enabled = debug_logging_enabled
        self.forceShuffle = False
        self.rawPath = rawPath
        if rawPath == "":
            self.clear()
        elif (pathList is not None) and (len(pathList) > 0):
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

    # Returns the playlist for the themes
    def getThemePlaylist(self):
        # Take the list of files and create a playlist from them
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        for aFile in self.themeFiles:
            # Add the theme file to a playlist
            playlist.add(url=aFile)

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
        if workingPath.startswith("smb://") or workingPath.startswith("afp://") or os.path.isfile(workingPath):
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
        return nfoRead.getExcludeFromScreensaver()

    # Search for theme files in the given directory
    def _getThemeFiles(self, directory, extensionOnly=False):
        # First read from the NFO file if it exists
        nfoRead = NfoReader(directory, self.debug_logging_enabled)
        themeFiles = nfoRead.getThemeFiles()

        # Get the theme directories that are referenced and process the data in them
        for nfoDir in nfoRead.getThemeDirs():
            # Do not want the theme keyword if looking at an entire directory
            themeFiles = themeFiles + self._getThemeFiles(nfoDir, True)

        log("ThemeFiles: Searching %s for %s" % (directory, Settings.getThemeFileRegEx(directory, extensionOnly)), self.debug_logging_enabled)

        # check if the directory exists before searching
        if dir_exists(directory):
            dirs, files = list_dir(directory)
            for aFile in files:
                m = re.search(Settings.getThemeFileRegEx(directory, extensionOnly), aFile, re.IGNORECASE)
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

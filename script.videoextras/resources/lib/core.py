# -*- coding: utf-8 -*-
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
import os
import re
import traceback
import xml.etree.ElementTree as ET
import xbmc
import xbmcvfs

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import dir_exists

from ExtrasItem import ExtrasItem


################################################
# Class to control Searching for the extra files
################################################
class VideoExtrasFinder():
    def __init__(self, extrasDb=None, defaultFanArt="", videoType=None):
        self.extrasDb = extrasDb
        self.defaultFanArt = defaultFanArt
        self.videoType = videoType
        # If no Video Type is supplied, try to work it out
        if videoType is None:
            if xbmc.getCondVisibility("Container.Content(movies)"):
                self.videoType = Settings.MOVIES
            elif xbmc.getCondVisibility("Container.Content(musicvideos)"):
                self.videoType = Settings.MUSICVIDEOS
            else:
                self.videoType = Settings.TVSHOWS

    # Controls the loading of the information for Extras Files
    def loadExtras(self, path, filename, exitOnFirst=False):
        # First check to see if there is a videoextras.nfo file
        extradirs, extras = self._getNfoInfo(path)

        if (len(extradirs) > 0) or (len(extras) > 0):
            # There are some extras defined via an NFO file
            extrasList = []
            # Read the extras files from the directories
            for aDir in extradirs:
                extrasList = extrasList + self.findExtras(aDir, filename, exitOnFirst, noExtrasDirNeeded=True)
                # Don't look for more than one if we are only checking for existence of an extra
                if exitOnFirst:
                    break

            # For each of the files, get the directory and filename split
            # and create the extrasItem
            for anExtraFile in extras:
                extraItem = ExtrasItem(os_path_split(anExtraFile)[0], anExtraFile, extrasDb=self.extrasDb, defaultFanArt=self.defaultFanArt)
                extrasList.append(extraItem)
                # Don't look for more than one if we are only checking for existence of an extra
                if exitOnFirst:
                    break

            # Sort the list before returning
            extrasList.sort()
            return extrasList

        # Check if the files are stored in a custom path
        if Settings.isCustomPathEnabled():
            filename = None
            path = self._getCustomPathDir(path)

            if path is None:
                return []
            else:
                log("VideoExtrasFinder: Searching in custom path %s" % path)
        return self.findExtras(path, filename, exitOnFirst, noExtrasDirNeeded=Settings.isCustomPathEnabled())

    # Calculates and checks the path that files should be in
    # if using a custom path
    def _getCustomPathDir(self, path):
        # Get the last element of the path
        pathLastDir = os_path_split(path)[1]

        # Create the path with this added
        custPath = Settings.getCustomPath(self.videoType)
        custPath = os_path_join(custPath, pathLastDir)
        log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)

        # Check if this path exists
        if not dir_exists(custPath):
            # If it doesn't exist, check the path before that, this covers the
            # case where there is a TV Show with each season in it's own directory
            path2ndLastDir = os_path_split((os_path_split(path)[0]))[1]
            custPath = Settings.getCustomPath(self.videoType)
            custPath = os_path_join(custPath, path2ndLastDir)
            custPath = os_path_join(custPath, pathLastDir)
            log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)
            if not dir_exists(custPath):
                # If it still does not exist then check just the 2nd to last path
                custPath = Settings.getCustomPath(self.videoType)
                custPath = os_path_join(custPath, path2ndLastDir)
                log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)
                if not dir_exists(custPath):
                    custPath = None

        return custPath

    def _getNfoInfo(self, directory):
        # Find out the name of the NFO file
        nfoFileName = os_path_join(directory, "videoextras.nfo")

        log("VideoExtrasFinder: Searching for NFO file: %s" % nfoFileName)

        extras = []
        extradirs = []

        # Return None if file does not exist
        if not xbmcvfs.exists(nfoFileName):
            log("VideoExtrasFinder: No NFO file found: %s" % nfoFileName)
            return extradirs, extras

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

            log("VideoExtrasFinder: Root element is = %s" % rootElement.tag)

            # Check which format if being used
            if rootElement.tag == "videoextras":
                log("VideoExtrasFinder: VideoExtras format NFO detected")
                #    <videoextras>
                #        <file>c:\my\extras\afile.avi</file>
                #        <directory>c:\my\extras</directory>
                #    </videoextras>

                # There could be multiple file entries, so loop through all of them
                for fileElem in nfoXml.findall('file'):
                    file = None
                    if fileElem is not None:
                        file = fileElem.text

                    if (file is not None) and (file != ""):
                        if file.startswith('..') or (("/" not in file) and ("\\" not in file)):
                            # Make it a full path if it is not already
                            file = os_path_join(directory, file)
                        log("VideoExtrasFinder: file = %s" % file)
                        # Make sure the file exists before adding it to the list
                        if xbmcvfs.exists(file):
                            extras.append(file)
                        else:
                            log("VideoExtrasFinder: file does not exist = %s" % file)

                # There could be multiple directory entries, so loop through all of them
                for dirElem in nfoXml.findall('directory'):
                    dir = None
                    if dirElem is not None:
                        dir = dirElem.text

                    if (dir is not None) and (dir != ""):
                        if dir.startswith('..') or (("/" not in dir) and ("\\" not in dir)):
                            # Make it a full path if it is not already
                            dir = os_path_join(directory, dir)
                        log("VideoExtrasFinder: directory = %s" % dir)
                        extradirs.append(dir)
            else:
                log("VideoExtrasFinder: Unknown NFO format")

            del nfoXml

        except:
            log("VideoExtrasFinder: Failed to process NFO: %s" % nfoFileName, xbmc.LOGERROR)
            log("VideoExtrasFinder: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return extradirs, extras

    # Searches a given path for extras files
    def findExtras(self, path, filename, exitOnFirst=False, noExtrasDirNeeded=False):
        # Make sure that the path and filename are OK
        try:
            path = path.encode('utf-8')
        except:
            pass
        try:
            filename = filename.encode('utf-8')
        except:
            pass

        # Get the extras that are stored in the extras directory i.e. /Extras/
        files = self._getExtrasDirFiles(path, exitOnFirst, noExtrasDirNeeded)

        # Check if we only want the first entry, in which case exit after
        # we find the first
        if files and (exitOnFirst is True):
            return files

        # Then add the files that have the extras tag in the name i.e. -extras-
        files.extend(self._getExtrasFiles(path, filename, exitOnFirst))

        # Check if we only want the first entry, in which case exit after
        # we find the first
        if files and (exitOnFirst is True):
            return files

        if Settings.isSearchNested():
            # Nested search always needs the extras directory directory
            files.extend(self._getNestedExtrasFiles(path, filename, exitOnFirst))
        files.sort()

        # Check if we have found any extras at this point
        if not files:
            # Check if we have a DVD image directory or Bluray image directory
            if (os_path_split(path)[1] == 'VIDEO_TS') or (os_path_split(path)[1] == 'BDMV'):
                log("VideoExtrasFinder: DVD image directory detected, checking = %s" % os_path_split(path)[0])
                # If nesting extras inside a Disc image - always needs an Extras directory
                files = self.findExtras(os_path_split(path)[0], filename, exitOnFirst)
        return files

    # Gets any extras files that are in the given extras directory
    def _getExtrasDirFiles(self, basepath, exitOnFirst=False, noExtrasDirNeeded=False):
        # If a custom path, then don't looks for the Extras directory
        if noExtrasDirNeeded or Settings.isCustomPathEnabled():
            extrasDir = basepath
        else:
            # Add the name of the extras directory to the end of the path
            extrasDir = os_path_join(basepath, Settings.getExtrasDirName())
        log("VideoExtrasFinder: Checking existence for %s" % extrasDir)
        extras = []
        # Check if the extras directory exists
        if dir_exists(extrasDir):
            # list everything in the extras directory
            dirs, files = xbmcvfs.listdir(extrasDir)
            for filename in files:
                log("VideoExtrasFinder: found file: %s" % filename)
                # Check each file in the directory to see if it should be skipped
                if not self._shouldSkipFile(filename):
                    extrasFile = os_path_join(extrasDir, filename)
                    extraItem = ExtrasItem(extrasDir, extrasFile, extrasDb=self.extrasDb, defaultFanArt=self.defaultFanArt)
                    extras.append(extraItem)
                    # Check if we are only looking for the first entry
                    if exitOnFirst is True:
                        break
            # Now check all the directories in the "Extras" directory
            # Need to see if they contain a DVD image
            for dirName in dirs:
                log("VideoExtrasFinder: found directory: %s" % dirName)
                # Check each directory to see if it should be skipped
                if not self._shouldSkipFile(dirName):
                    extrasSubDir = os_path_join(extrasDir, dirName)
                    # Check to see if this sub-directory is a DVD directory by checking
                    # to see if there is VIDEO_TS directory
                    videoTSDir = os_path_join(extrasSubDir, 'VIDEO_TS')
                    # Also check for Bluray
                    videoBluRayDir = os_path_join(extrasSubDir, 'BDMV')
                    if dir_exists(videoTSDir) or dir_exists(videoBluRayDir):
                        extraItem = ExtrasItem(extrasDir, extrasSubDir, extrasDb=self.extrasDb, defaultFanArt=self.defaultFanArt)
                        extras.append(extraItem)

                    # Check if we are only looking for the first entry
                    if exitOnFirst is True:
                        break

        return extras

    def _getNestedExtrasFiles(self, basepath, filename, exitOnFirst=False, noExtrasDirNeeded=False):
        extras = []
        if dir_exists(basepath):
            dirs, files = xbmcvfs.listdir(basepath)
            for dirname in dirs:
                # Do not search inside Bluray or DVD images
                if (dirname == 'VIDEO_TS') or (dirname == 'BDMV'):
                    continue

                dirpath = os_path_join(basepath, dirname)
                log("VideoExtrasFinder: Nested check in directory: %s" % dirpath)
                if dirname != Settings.getExtrasDirName():
                    log("VideoExtrasFinder: Check directory: %s" % dirpath)
                    extras.extend(self._getExtrasDirFiles(dirpath, exitOnFirst, noExtrasDirNeeded))
                    # Check if we are only looking for the first entry
                    if files and (exitOnFirst is True):
                        break
                    extras.extend(self._getExtrasFiles(dirpath, filename, exitOnFirst))
                    # Check if we are only looking for the first entry
                    if files and (exitOnFirst is True):
                        break
                    extras.extend(self._getNestedExtrasFiles(dirpath, filename, exitOnFirst, noExtrasDirNeeded))
                    # Check if we are only looking for the first entry
                    if files and (exitOnFirst is True):
                        break
        return extras

    # Search for files with the same name as the original video file
    # but with the extras tag on, this will not recurse directories
    # as they must exist in the same directory
    def _getExtrasFiles(self, filepath, filename, exitOnFirst=False):
        extras = []
        extrasTag = Settings.getExtrasFileTag()

        # If there was no filename given, nothing to do
        if (filename is None) or (filename == "") or (extrasTag == ""):
            return extras
        directory = filepath
        dirs, files = xbmcvfs.listdir(directory)

        for aFile in files:
            if not self._shouldSkipFile(aFile) and (extrasTag in aFile) and aFile.startswith(os.path.splitext(filename)[0] + extrasTag):
                extrasFile = os_path_join(directory, aFile)
                extraItem = ExtrasItem(directory, extrasFile, True, extrasDb=self.extrasDb, defaultFanArt=self.defaultFanArt)
                extras.append(extraItem)
                # Check if we are only looking for the first entry
                if exitOnFirst is True:
                    break
        return extras

    # Checks if a file should be skipped because it is in the exclude list
    def _shouldSkipFile(self, filename):
        shouldSkip = False
        if Settings.getExcludeFiles() != "":
            m = re.search(Settings.getExcludeFiles(), filename)
        else:
            m = ""
        if m:
            shouldSkip = True
            log("VideoExtrasFinder: Skipping file: %s" % filename)
        return shouldSkip


###############################################################
# Base Class for handling videoExtras
###############################################################
class VideoExtrasBase():
    def __init__(self, extrasParent, videoType=None):
        log("VideoExtrasBase: Finding extras for %s" % extrasParent)
        self.videoType = videoType
        self.baseDirectory = extrasParent
        if self.baseDirectory.startswith("stack://"):
            self.baseDirectory = self.baseDirectory.split(" , ")[0]
            self.baseDirectory = self.baseDirectory.replace("stack://", "")
        # There is a problem if some-one is using windows shares with
        # \\SERVER\Name as when the addon gets called the first \ gets
        # removed, making an invalid path, so we add it back here
        elif self.baseDirectory.startswith("\\"):
            self.baseDirectory = "\\" + self.baseDirectory

        # Support special paths like smb:// means that we can not just call
        # os.path.isfile as it will return false even if it is a file
        # (A bit of a shame - but that's the way it is)
        fileExt = os.path.splitext(self.baseDirectory)[1]
        # If this is a file, then get it's parent directory
        if fileExt is not None and fileExt != "":
            self.baseDirectory = (os_path_split(self.baseDirectory))[0]
            self.filename = (os_path_split(extrasParent))[1]
        else:
            self.filename = None
        log("VideoExtrasBase: Root directory: %s" % self.baseDirectory)

    def findExtras(self, exitOnFirst=False, extrasDb=None, defaultFanArt=""):
        files = []
        try:
            extrasFinder = VideoExtrasFinder(extrasDb, defaultFanArt=defaultFanArt, videoType=self.videoType)
            files = extrasFinder.loadExtras(self.baseDirectory, self.filename, exitOnFirst)
        except:
            log("VideoExtrasBase: %s" % traceback.format_exc(), xbmc.LOGERROR)
        return files

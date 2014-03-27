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
import sys
import os
import re
import traceback
import xml.etree.ElementTree as ET
#Modules XBMC
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.videoextras')

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

# Load the database interface
from database import ExtrasDB

from VideoParser import VideoParser



########################################################
# Class to store all the details for a given extras file
########################################################
class BaseExtrasItem():
    def __init__( self, directory, filename, isFileMatchExtra=False ):
        self.directory = directory
        self.filename = filename
        self.plot = None
        # Setup the icon and thumbnail images
        self.thumbnailImage = ""
        self.iconImage = ""
        self.fanart = ""
        self._loadImages(filename)

        self.duration = None

        # Record if the match was by filename rather than in Extras sub-directory
        self.isFileMatchingExtra = isFileMatchExtra
        # Check if there is an NFO file to process
        if not self._loadNfoInfo(filename):
            # Get the ordering and display details from the filename
            (self.orderKey, self.displayName) = self._generateOrderAndDisplay(filename)

    # eq and lt defined for sorting order only
    def __eq__(self, other):
        if other == None:
            return False
        # Check key, display then filename - all need to be the same for equals
        return ((self.orderKey, self.displayName, self.directory, self.filename, self.isFileMatchingExtra) ==
                (other.orderKey, other.displayName, other.directory, other.filename, other.isFileMatchingExtra))

    def __lt__(self, other):
        # Order in key, display then filename 
        return ((self.orderKey, self.displayName, self.directory, self.filename, self.isFileMatchingExtra) <
                (other.orderKey, other.displayName, other.directory, other.filename, other.isFileMatchingExtra))

    # Returns the name to display to the user for the file
    def getDisplayName(self):
        # Update the display name to allow for : in the name
        return self.displayName.replace(".sample","").replace("&#58;", ":")

    # Return the filename for the extra
    def getFilename(self):
        return self.filename

    # Gets the file that needs to be passed to the player
    def getMediaFilename(self):
        # Check to see if the filename actually holds a directory
        # If that is the case, we will only support it being a DVD Directory Image
        # So check to see if the expected file is set
        vobFile = self.getVOBFile()
        if vobFile != None:
            return vobFile
        
        return self.filename

    # Gets the path to the VOB playable file, or None if not a VOB
    def getVOBFile(self):
        # Check to see if the filename actually holds a directory
        # If that is the case, we will only support it being a DVD Directory Image
        # So check to see if the expected file is set
        videoTSDir = os_path_join( self.filename, 'VIDEO_TS' )
        if xbmcvfs.exists(videoTSDir):
            ifoFile = os_path_join( videoTSDir, 'VIDEO_TS.IFO' )
            if xbmcvfs.exists( ifoFile ):
                return ifoFile
        # Also check for BluRay
        videoBluRayDir = os_path_join( self.filename, 'BDMV' )
        if xbmcvfs.exists(videoBluRayDir):
            dbmvFile = os_path_join( videoBluRayDir, 'index.bdmv' )
            if xbmcvfs.exists( dbmvFile ):
                return dbmvFile
        return None

    # Compare if a filename matches the existing one
    def isFilenameMatch(self, compareToFilename):
        srcFilename = self.filename
        tgtFilename = compareToFilename
        try:
            srcFilename = srcFilename.decode("utf-8")
        except:
            pass
        try:
            tgtFilename = tgtFilename.decode("utf-8")
        except:
            pass
        if srcFilename == tgtFilename:
            return True
        return False

    def getDirectory(self):
        return self.directory

    def isFileMatchExtra(self):
        return self.isFileMatchingExtra
    
    def getOrderKey(self):
        return self.orderKey

    def getPlot(self):
        return self.plot

    def getThumbnailImage(self):
        return self.thumbnailImage

    def getIconImage(self):
        return self.iconImage

    def getFanArt(self):
        if self.fanart == "":
            self.fanart = SourceDetails.getFanArt()
        return self.fanart

    # Returns the duration in seconds
    def getDuration(self):
        if self.duration == None:
            try:
                # Parse the video file for the duration
                self.duration = VideoParser().getVideoLength(self.filename)
                log("BaseExtrasItem: Duration retrieved is = %d" % self.duration)
            except:
                log("BaseExtrasItem: Failed to get duration from %s" % self.filename)
                log("BaseExtrasItem: %s" % traceback.format_exc())
                self.duration = 0
        
        return self.duration

    def getDisplayDuration(self, forcedDuration=0):
        durationInt = forcedDuration
        if forcedDuration < 1:
            durationInt = self.getDuration()

        displayDuration = ""
        seconds = 0
        minutes = 0
        hours = 0

        # Convert the duration into a viewable format
        if durationInt > 0:
            seconds = durationInt % 60
 
            if durationInt > 60:
                minutes = ((durationInt - seconds) % 3600)/60

            # Default the display to MM:SS
            displayDuration = "%02d:%02d" % (minutes, seconds)

            # Only add the hours is really needed
            if durationInt > 3600:
                hours = (durationInt - (minutes*60) - seconds)/3600
                displayDuration = "%02d:%s" % (hours, displayDuration)

        # Set the display duration to be the time in minutes
        return displayDuration
        

    # Load the Correct set of images for icons and thumbnails
    # Image options are
    # (NFO - Will overwrite these values)
    # <filename>.tbn/jpg
    # <filename>-poster.jpg (Auto picked up by player)
    # <filename>-thumb.jpg
    # poster.jpg
    # folder.jpg
    #
    # See:
    # http://wiki.xbmc.org/?title=Thumbnails
    # http://wiki.xbmc.org/index.php?title=Frodo_FAQ#Local_images
    def _loadImages(self, filename):
        imageList = []
        # Find out the name of the image files
        fileNoExt = os.path.splitext( filename )[0]

        # Start by searching for the filename match
        fileNoExtImage = self._loadImageFile( fileNoExt )
        if fileNoExtImage != "":
            imageList.append(fileNoExtImage)

        # Check for -poster added to the end
        fileNoExtImage = self._loadImageFile( fileNoExt + "-poster" )
        if fileNoExtImage != "":
            imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for -thumb added to the end
            fileNoExtImage = self._loadImageFile( fileNoExt + "-thumb" )
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for poster.jpg
            fileDir = os_path_join(self.directory, "poster")
            fileNoExtImage = self._loadImageFile( fileDir )
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for folder.jpg
            fileDir = os_path_join(self.directory, "folder")
            fileNoExtImage = self._loadImageFile( fileDir )
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)
                
        # Set the first one to the thumbnail, and the second the the icon
        if len(imageList) > 0:
            self.thumbnailImage = imageList[0]
            if len(imageList) > 1:
                self.iconImage = imageList[1]

        # Now check for the fanart
        # Check for -fanart added to the end
        fileNoExtImage = self._loadImageFile( fileNoExt + "-fanart" )
        if fileNoExtImage != "":
            self.fanart = fileNoExtImage
        else:
            # Check for fanart.jpg
            fileDir = os_path_join(self.directory, "fanart")
            fileNoExtImage = self._loadImageFile( fileDir )
            if fileNoExtImage != "":
                self.fanart = fileNoExtImage


    # Searched for a given image name under different extensions
    def _loadImageFile(self, fileNoExt):
        if xbmcvfs.exists( fileNoExt + ".tbn" ):
            return fileNoExt + ".tbn"
        if xbmcvfs.exists( fileNoExt + ".png" ):
            return fileNoExt + ".png"
        if xbmcvfs.exists( fileNoExt + ".jpg" ):
            return fileNoExt + ".jpg"
        return ""

    # Parses the filename to work out the display name and order key
    def _generateOrderAndDisplay(self, filename):
        # First thing is to trim the display name from the filename
        # Get just the filename, don't need the full path
        displayName = os.path.split(filename)[1]
        # Remove the file extension (e.g .avi)
        displayName = os.path.splitext( displayName )[0]
        # Remove anything before the -extras- tag (if it exists)
        extrasTag = Settings.getExtrasFileTag()
        if (extrasTag != "") and (extrasTag in displayName):
            justDescription = displayName.split(extrasTag,1)[1]
            if len(justDescription) > 0:
                displayName = justDescription
        
        result = ( displayName, displayName )
        # Search for the order which will be written as [n]
        # Followed by the display name
        match = re.search("^\[(?P<order>.+)\](?P<Display>.*)", displayName)
        if match:
            orderKey = match.group('order')
            if orderKey != "":
                result = ( orderKey, match.group('Display') )
        return result

    # Check for an NFO file for this video and reads details out of it
    # if it exists
    def _loadNfoInfo(self, filename):
        # Find out the name of the NFO file
        nfoFileName = os.path.splitext( filename )[0] + ".nfo"
        
        log("BaseExtrasItem: Searching for NFO file: %s" % nfoFileName)
        
        # Return False if file does not exist
        if not xbmcvfs.exists( nfoFileName ):
            log("BaseExtrasItem: No NFO file found: %s" % nfoFileName)
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
            try:
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr))
            except:
                log("BaseExtrasItem: Trying encoding to UTF-8 with ignore")
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr.decode("UTF-8", 'ignore')))

            rootElement = nfoXml.getroot()
            
            log("BaseExtrasItem: Root element is = %s" % rootElement.tag)
            
            # Check which format if being used
            if rootElement.tag == "movie":
                log("BaseExtrasItem: Movie format NFO detected")
                #    <movie>
                #        <title>Who knows</title>
                #        <sorttitle>Who knows 1</sorttitle>
                #    </movie>
                
                # Get the title
                self.displayName = nfoXml.findtext('title')
                # Get the sort key
                self.orderKey = nfoXml.findtext('sorttitle')
                # Get the plot
                self.plot = nfoXml.findtext('plot')
    
            elif rootElement.tag == "tvshow":
                log("BaseExtrasItem: TvShow format NFO detected")
                #    <tvshow>
                #        <title>Who knows</title>
                #        <sorttitle>Who knows 1</sorttitle>
                #    </tvshow>
    
                # Get the title
                self.displayName = nfoXml.findtext('title')
                # Get the sort key
                self.orderKey = nfoXml.findtext('sorttitle')
                # Get the plot
                self.plot = nfoXml.findtext('plot')

            elif rootElement.tag == "episodedetails":
                log("BaseExtrasItem: TvEpisode format NFO detected")
                #    <episodedetails>
                #        <title>Who knows</title>
                #        <season>2</season>
                #        <episode>1</episode>
                #    </episodedetails>
    
                # Get the title
                self.displayName = nfoXml.findtext('title')
                # Get the plot
                self.plot = nfoXml.findtext('plot')
                # Get the sort key
                season = nfoXml.findtext('season')
                episode = nfoXml.findtext('episode')
                
                # Need to use the season and episode to order the list
                if (season == None) or (season == ""):
                    season = "0"
                if (episode == None) or (episode == ""):
                    episode = "0"
                self.orderKey = "%02d_%02d" % (int(season), int(episode))

            else:
                self.displayName = None
                self.orderKey = None
                log("BaseExtrasItem: Unknown NFO format")
    
            # Now get the thumbnail - always called the same regardless of
            # movie of TV
            thumbnail = self._getNfoThumb(nfoXml)
            if thumbnail != None:
                self.thumbnailImage = thumbnail

            # Now get the fanart - always called the same regardless of
            # movie of TV
            fanart = self._getNfoFanart(nfoXml)
            if fanart != None:
                self.fanart = fanart
    
            del nfoXml

            if (self.displayName != None) and (self.displayName != ""):
                returnValue = True
                # If there is no order specified, use the display name
                if (self.orderKey == None) or (self.orderKey == ""):
                    self.orderKey = self.displayName
                log("BaseExtrasItem: Using sort key %s for %s" % (self.orderKey, self.displayName))
        except:
            log("BaseExtrasItem: Failed to process NFO: %s" % nfoFileName)
            log("BaseExtrasItem: %s" % traceback.format_exc())
            returnValue = False

        return returnValue

    # Sets the title for a given extras file
    def setTitle(self, newTitle):
        log("BaseExtrasItem: Setting title to %s" % newTitle)
        self.displayName = newTitle

        # Find out the name of the NFO file
        nfoFileName = os.path.splitext( self.filename )[0] + ".nfo"
        
        log("BaseExtrasItem: Searching for NFO file: %s" % nfoFileName)
                
        try:
            nfoFileStr = None
            newNfoRequired = False
            
            if xbmcvfs.exists( nfoFileName ):
                # Need to first load the contents of the NFO file into
                # a string, this is because the XML File Parse option will
                # not handle formats like smb://
                nfoFile = xbmcvfs.File(nfoFileName, 'r')
                nfoFileStr = nfoFile.read()
                nfoFile.close()
    
            # Check to ensure we have some NFO data
            if (nfoFileStr == None) or (nfoFileStr == ""):
                # Create a default NFO File
                # Need to create a new file if one does not exist
                log("BaseExtrasItem: No NFO file found, creating new one: %s" % nfoFileName)
                tagType = 'movie'
                if SourceDetails.getTvShowTitle() != "":
                    tagType = 'tvshow'

                nfoFileStr = ("<%s>\n    <title> </title>\n</%s>\n" % (tagType, tagType))
                newNfoRequired = True
                
                
            # Create an XML parser
            try:
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr))
            except:
                log("BaseExtrasItem: Trying encoding to UTF-8 with ignore")
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr.decode("UTF-8", 'ignore')))

            # Get the title element
            titleElement = nfoXml.find('title')

            # Make sure the title exists in the file            
            if titleElement == None:
                log("BaseExtrasItem: title element not found")
                return False

            # Set the title to the new value
            titleElement.text = newTitle

            # Only set the sort title if already set
            sorttitleElement = nfoXml.find('sorttitle')
            if sorttitleElement != None:
                sorttitleElement.text = newTitle
            
            # Save the file back to the filesystem
            newNfoContent = ET.tostring(nfoXml.getroot(), encoding="UTF-8")
            del nfoXml
            
            nfoFile = xbmcvfs.File(nfoFileName, 'w')
            try:
                nfoFile.write(newNfoContent)
            except:
                log("BaseExtrasItem: Failed to write NFO: %s" % nfoFileName)
                log("BaseExtrasItem: %s" % traceback.format_exc())
                # Make sure we close the file handle
                nfoFile.close()
                # If there was no file before, make sure we delete and partial file
                if newNfoRequired:
                    xbmcvfs.delete(nfoFileName)
                return False
            nfoFile.close()

        except:
            log("BaseExtrasItem: Failed to write NFO: %s" % nfoFileName)
            log("BaseExtrasItem: %s" % traceback.format_exc())
            return False
        
        return True

        

    # Reads the thumbnail information from an NFO file
    def _getNfoThumb(self, nfoXml):
        # Get the thumbnail
        thumbnail = nfoXml.findtext('thumb')
        if (thumbnail != None) and (thumbnail != ""):
            # Found the thumb entry, check if this is a local path
            # which just has a filename, this is the case if there are
            # no forward slashes and no back slashes
            if (not "/" in thumbnail) and (not "\\" in thumbnail):
                thumbnail = os_path_join(self.directory, thumbnail)
        else:
            thumbnail = None
        return thumbnail

    # Reads the fanart information from an NFO file
    def _getNfoFanart(self, nfoXml):
        # Get the fanart
        fanart = nfoXml.findtext('fanart')
        if (fanart != None) and (fanart != ""):
            # Found the fanart entry, check if this is a local path
            # which just has a filename, this is the case if there are
            # no forward slashes and no back slashes
            if (not "/" in fanart) and (not "\\" in fanart):
                fanart = os_path_join(self.directory, fanart)
        else:
            fanart = None
        return fanart


####################################################################
# Extras item that extends the base type to supply extra information
# that can be read or set via a database
####################################################################
class ExtrasItem(BaseExtrasItem):
    def __init__( self, directory, filename, isFileMatchExtra=False, extrasDb=None ):
        self.extrasDb = extrasDb
        self.watched = 0
        self.totalDuration = -1
        self.resumePoint = 0
        BaseExtrasItem.__init__(self, directory, filename, isFileMatchExtra)
        self._loadState()

    # Note: An attempt was made to re-use the existing XBMC database to
    # read the playcount to work out if a video file has been watched,
    # however this did not seem to work, call was:
    # json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetFileDetails", "params": {"file": "%s", "media": "video", "properties": [ "playcount" ]},"id": 1 }' % filename)
    # Even posted on the forum, but this hasn't resolved it:
    # http://forum.xbmc.org/showthread.php?tid=177368
    def getWatched(self):
        return self.watched

    # If the playing progress should be recorded for this file, things like
    # ISO's and VOBs do not handle this well as the incorrect values are
    # returned from the player
    def shouldStoreProgress(self):
        if self.getVOBFile() != None:
            return False
        # Get the extension of the file
        fileExt = os.path.splitext( self.getFilename() )[1]
        if (fileExt == None) or (fileExt == "") or (fileExt.lower() == '.iso') :
            return False
        # Default is true
        return True


    def setTotalDuration(self, totalDuration):
        # Do not set the total duration on DVD Images as
        # this will be incorrect
        if not self.shouldStoreProgress():
            return

        self.totalDuration = totalDuration

    def getTotalDuration(self):
        if self.totalDuration < 0:
            self.totalDuration = self.getDuration()
        return self.totalDuration

    def getDisplayDuration(self):
        return BaseExtrasItem.getDisplayDuration(self, self.totalDuration)

    def setResumePoint(self, currentPoint):
        # Do not set the resume point on DVD Images as
        # this will be incorrect
        if not self.shouldStoreProgress():
            return

        # Now set the flag to show if it has been watched
        # Consider watched if within 15 seconds of the end
        if (currentPoint + 15 > self.totalDuration) and (self.totalDuration > 0):
            self.watched = 1
            self.resumePoint = 0
        # Consider not watched if not watched at least 5 seconds
        elif currentPoint < 6:
            self.watched = 0
            self.resumePoint = 0
        # Otherwise save the resume point
        else:
            self.watched = 0
            self.resumePoint = currentPoint

    def getResumePoint(self):
        return self.resumePoint

    # Get the string display version of the Resume time
    def getDisplayResumePoint(self):
        # Split the time up ready for display
        minutes, seconds = divmod(self.resumePoint, 60)

        hoursString = ""        
        if minutes > 60:
            # Need to collect hours if needed
            hours, minutes = divmod(minutes, 60)
            hoursString = "%02d:" % hours
        
        newLabel = "%s%02d:%02d" % (hoursString, minutes, seconds)
        return newLabel


    def isResumable(self):
        if self.watched == 1 or self.resumePoint < 1:
            return False
        return True

    def saveState(self):
        # Do not save the state on DVD Images as
        # this will be incorrect
        if not self.shouldStoreProgress():
            return

        if self.extrasDb == None:
            log("ExtrasItem: Database not enabled")
            return
        
        log("ExtrasItem: Saving state for %s" % self.getFilename())

        rowId = -1
        # There are some cases where we want to remove the entries from the database
        # This is the case where the resume point is 0, watched is 0
        if (self.resumePoint == 0) and (self.watched == 0):
            self.extrasDb.delete(self.getFilename())
        else:
            rowId = self.extrasDb.insertOrUpdate(self.getFilename(), self.resumePoint, self.totalDuration, self.getWatched())
        return rowId

    def _loadState(self):
        if self.extrasDb == None:
            log("ExtrasItem: Database not enabled")
            return

        log("ExtrasItem: Loading state for %s" % self.getFilename())

        returnData = self.extrasDb.select(self.getFilename())

        if returnData != None:
            self.resumePoint = returnData['resumePoint']
            self.totalDuration = returnData['totalDuration']
            self.watched = returnData['watched']


################################################
# Class to control Searching for the extra files
################################################
class VideoExtrasFinder():
    def __init__(self, extrasDb=None):
        self.extrasDb = extrasDb
        
    # Controls the loading of the information for Extras Files
    def loadExtras(self, path, filename, exitOnFirst=False):
        # Check if the files are stored in a custom path
        if Settings.isCustomPathEnabled():
            filename = None
            path = self._getCustomPathDir(path)
            
            if path == None:
                return []
            else:
                log("VideoExtrasFinder: Searching in custom path %s" % path)
        return self.findExtras(path, filename, exitOnFirst)

    # Calculates and checks the path that files should be in
    # if using a custom path
    def _getCustomPathDir(self, path):
        # Work out which section to look in
        typeSection = Settings.getCustomPathMoviesDir()
        if not xbmc.getCondVisibility("Container.Content(movies)"):
            typeSection = Settings.getCustomPathTvShowsDir()

        # Get the last element of the path
        pathLastDir = os.path.split(path)[1]

        # Create the path with this added
        custPath = os_path_join(Settings.getCustomPath(), typeSection)
        custPath = os_path_join(custPath, pathLastDir)
        log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)

        # Check if this path exists
        if not xbmcvfs.exists(custPath):
            # If it doesn't exist, check the path before that, this covers the
            # case where there is a TV Show with each season in it's own directory
            path2ndLastDir = os.path.split((os.path.split(path)[0]))[1]
            custPath = os_path_join(Settings.getCustomPath(), typeSection)
            custPath = os_path_join(custPath, path2ndLastDir)
            custPath = os_path_join(custPath, pathLastDir)
            log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)
            if not xbmcvfs.exists(custPath):
                # If it still does not exist then check just the 2nd to last path
                custPath = os_path_join(Settings.getCustomPath(), typeSection)
                custPath = os_path_join(custPath, path2ndLastDir)
                log("VideoExtrasFinder: Checking existence of custom path %s" % custPath)
                if not xbmcvfs.exists(custPath):
                    custPath = None

        return custPath
        
    
    # Searches a given path for extras files
    def findExtras(self, path, filename, exitOnFirst=False):
        # Get the extras that are stored in the extras directory i.e. /Extras/
        files = self._getExtrasDirFiles(path, exitOnFirst)
        
        # Check if we only want the first entry, in which case exit after
        # we find the first
        if files and (exitOnFirst == True):
            return files
        
        # Then add the files that have the extras tag in the name i.e. -extras-
        files.extend( self._getExtrasFiles( path, filename, exitOnFirst ) )

        # Check if we only want the first entry, in which case exit after
        # we find the first
        if files and (exitOnFirst == True):
            return files
        
        if Settings.isSearchNested():
            files.extend( self._getNestedExtrasFiles( path, filename, exitOnFirst ) )
        files.sort()
        
        # Check if we have found any extras at this point
        if not files:
            # Check if we have a DVD image directory or Bluray image directory
            if (os.path.split(path)[1] == 'VIDEO_TS') or (os.path.split(path)[1] == 'BDMV'):
                log("VideoExtrasFinder: DVD image directory detected, checking = %s" % os.path.split(path)[0])
                files = self.findExtras(os.path.split(path)[0], filename, exitOnFirst)
        return files

    # Gets any extras files that are in the given extras directory
    def _getExtrasDirFiles(self, basepath, exitOnFirst=False):
        # If a custom path, then don't looks for the Extras directory
        if not Settings.isCustomPathEnabled():
            # Add the name of the extras directory to the end of the path
            extrasDir = os_path_join( basepath, Settings.getExtrasDirName() )
        else:
            extrasDir = basepath
        log( "VideoExtrasFinder: Checking existence for %s" % extrasDir )
        extras = []
        # Check if the extras directory exists
        if xbmcvfs.exists( extrasDir ):
            # lest everything in the extras directory
            dirs, files = xbmcvfs.listdir( extrasDir )
            for filename in files:
                log( "VideoExtrasFinder: found file: %s" % filename)
                # Check each file in the directory to see if it should be skipped
                if not self._shouldSkipFile(filename):
                    extrasFile = os_path_join( extrasDir, filename )
                    extraItem = ExtrasItem(extrasDir, extrasFile, extrasDb=self.extrasDb)
                    extras.append(extraItem)
                    # Check if we are only looking for the first entry
                    if exitOnFirst == True:
                        break
            # Now check all the directories in the "Extras" directory
            # Need to see if they contain a DVD image
            for dirName in dirs:
                log( "VideoExtrasFinder: found directory: %s" % dirName)
                # Check each directory to see if it should be skipped
                if not self._shouldSkipFile(dirName):
                    extrasSubDir = os_path_join( extrasDir, dirName )
                    # Check to see if this sub-directory is a DVD directory by checking
                    # to see if there is VIDEO_TS directory
                    videoTSDir = os_path_join( extrasSubDir, 'VIDEO_TS' )
                    # Also check for Bluray
                    videoBluRayDir = os_path_join( extrasSubDir, 'BDMV' )
                    if xbmcvfs.exists( videoTSDir ) or xbmcvfs.exists( videoBluRayDir ):
                        extraItem = ExtrasItem(extrasDir, extrasSubDir, extrasDb=self.extrasDb)
                        extras.append(extraItem)
                        
                    # Check if we are only looking for the first entry
                    if exitOnFirst == True:
                        break

        return extras

    def _getNestedExtrasFiles(self, basepath, filename, exitOnFirst=False):
        extras = []
        if xbmcvfs.exists( basepath ):
            dirs, files = xbmcvfs.listdir( basepath )
            for dirname in dirs:
                dirpath = os_path_join( basepath, dirname )
                log( "VideoExtrasFinder: Nested check in directory: %s" % dirpath )
                if( dirname != Settings.getExtrasDirName() ):
                    log( "VideoExtrasFinder: Check directory: %s" % dirpath )
                    extras.extend( self._getExtrasDirFiles(dirpath, exitOnFirst) )
                     # Check if we are only looking for the first entry
                    if files and (exitOnFirst == True):
                        break
                    extras.extend( self._getExtrasFiles( dirpath, filename, exitOnFirst ) )
                     # Check if we are only looking for the first entry
                    if files and (exitOnFirst == True):
                        break
                    extras.extend( self._getNestedExtrasFiles( dirpath, filename, exitOnFirst ) )
                     # Check if we are only looking for the first entry
                    if files and (exitOnFirst == True):
                        break
        return extras

    # Search for files with the same name as the original video file
    # but with the extras tag on, this will not recurse directories
    # as they must exist in the same directory
    def _getExtrasFiles(self, filepath, filename, exitOnFirst=False):
        extras = []
        extrasTag = Settings.getExtrasFileTag()

        # If there was no filename given, nothing to do
        if (filename == None) or (filename == "") or (extrasTag == ""):
            return extras
        directory = filepath
        dirs, files = xbmcvfs.listdir(directory)

        for aFile in files:
            if not self._shouldSkipFile(aFile) and (extrasTag in aFile) and aFile.startswith(os.path.splitext(filename)[0] + extrasTag):
                extrasFile = os_path_join( directory, aFile )
                extraItem = ExtrasItem(directory, extrasFile, True, extrasDb=self.extrasDb)
                extras.append(extraItem)
                # Check if we are only looking for the first entry
                if exitOnFirst == True:
                    break
        return extras

    # Checks if a file should be skipped because it is in the exclude list
    def _shouldSkipFile(self, filename):
        shouldSkip = False
        if( Settings.getExcludeFiles() != "" ):
            m = re.search(Settings.getExcludeFiles(), filename )
        else:
            m = ""
        if m:
            shouldSkip = True
            log( "VideoExtrasFinder: Skipping file: %s" % filename)
        return shouldSkip

##################################################
# Class to store the details of the selected item
##################################################
class SourceDetails():
    title = None
    tvshowtitle = None
    fanart = None
    filenameAndPath = None

    # Forces the loading of all the source details
    # This is needed if the "Current Window" is going to
    # change - and we need a reference to the source before
    # it changes
    @staticmethod
    def forceLoadDetails():
        SourceDetails.getFanArt()
        SourceDetails.getFilenameAndPath()
        SourceDetails.getTitle()
        SourceDetails.getTvShowTitle()

    @staticmethod
    def getTitle():
        if SourceDetails.title == None:
            # Get the title of the Movie or TV Show
            if WindowShowing.isTv():
                SourceDetails.title = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            else:
                SourceDetails.title = xbmc.getInfoLabel( "ListItem.Title" )
            # There are times when the title has a different encoding
            try:
                SourceDetails.title = SourceDetails.title.decode("utf-8")
            except:
                pass

        return SourceDetails.title

    @staticmethod
    def getTvShowTitle():
        if SourceDetails.tvshowtitle == None:
            if WindowShowing.isTv():
                SourceDetails.tvshowtitle = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            else:
                SourceDetails.tvshowtitle = ""
            # There are times when the title has a different encoding
            try:
                SourceDetails.tvshowtitle = SourceDetails.tvshowtitle.decode("utf-8")
            except:
                pass

        return SourceDetails.tvshowtitle

    # This is a bit of a hack, when we set the path we need to set it an extra
    # directory below where we really are - this path is not used to retrieve
    # the extras files (This class highlights where the script was called from)
    # It is used to trigger the TV Tunes, and for some reason between VideoExtras
    # setting the value and TvTunes getting it, it loses the final directory
    @staticmethod
    def getFilenameAndPath():
        if SourceDetails.filenameAndPath == None:
            SourceDetails.filenameAndPath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" ) + "Extras"
        return SourceDetails.filenameAndPath
    
    @staticmethod
    def getFanArt():
        if SourceDetails.fanart == None:
            # Save the background
            SourceDetails.fanart = xbmc.getInfoLabel( "ListItem.Property(Fanart_Image)" )
        return SourceDetails.fanart

###############################################################
# Class to make it easier to see which screen is being checked
###############################################################
class WindowShowing():
    xbmcMajorVersion = 0

    @staticmethod
    def getXbmcMajorVersion():
        if WindowShowing.xbmcMajorVersion == 0:
            xbmcVer = xbmc.getInfoLabel('system.buildversion')
            log("WindowShowing: XBMC Version = %s" % xbmcVer)
            WindowShowing.xbmcMajorVersion = 12
            try:
                # Get just the major version number
                WindowShowing.xbmcMajorVersion = int(xbmcVer.split(".", 1)[0])
            except:
                # Default to frodo as the default version if we fail to find it
                log("WindowShowing: Failed to get XBMC version")
            log("WindowShowing: XBMC Version %d (%s)" % (WindowShowing.xbmcMajorVersion, xbmcVer))
        return WindowShowing.xbmcMajorVersion

    @staticmethod
    def isTv():
        if xbmc.getCondVisibility("Container.Content(tvshows)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Seasons)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Episodes)"):
            return True
        
        folderPathId = "videodb://2/2/"
        # The ID for the TV Show Title changed in Gotham
        if WindowShowing.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://tvshows/titles/"
        if xbmc.getInfoLabel( "container.folderpath" ) == folderPathId:
            return True # TvShowTitles

        return False

###############################################################
# Base Class for handling videoExtras
###############################################################
class VideoExtrasBase():
    def __init__( self, inputArg ):
        log( "VideoExtrasBase: Finding extras for %s" % inputArg )
        self.baseDirectory = inputArg
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
        fileExt = os.path.splitext( self.baseDirectory )[1]
        # If this is a file, then get it's parent directory
        if fileExt != None and fileExt != "":
            self.baseDirectory = os.path.dirname(self.baseDirectory)
            self.filename = (os.path.split(inputArg))[1]
        else:
            self.filename = None
        log( "VideoExtrasBase: Root directory: %s" % self.baseDirectory )

    def findExtras(self, exitOnFirst=False, extrasDb=None):
        files = []
        try:
            extrasFinder = VideoExtrasFinder(extrasDb)
            files = extrasFinder.loadExtras(self.baseDirectory, self.filename, exitOnFirst )
        except:
            log("VideoExtrasBase: %s" % traceback.format_exc())
        return files


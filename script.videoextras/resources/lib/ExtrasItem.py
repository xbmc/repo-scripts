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
import xbmcgui
import xbmcvfs

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import dir_exists

from VideoParser import VideoParser


########################################################
# Class to store all the details for a given extras file
########################################################
class BaseExtrasItem():
    def __init__(self, directory, filename, isFileMatchExtra=False, defaultFanArt=""):
        self.directory = directory
        self.filename = filename
        self.plot = None
        # Setup the icon and thumbnail images
        self.thumbnailImage = ""
        self.iconImage = ""
        # Set the default fanart - this will be over-written if there is a better one
        self.fanart = defaultFanArt
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
        if other is None:
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
        return self.displayName.replace(".sample", "").replace("&#58;", ":")

    # Return the filename for the extra
    def getFilename(self):
        return self.filename

    # Gets the file that needs to be passed to the player
    def getMediaFilename(self):
        # Check to see if the filename actually holds a directory
        # If that is the case, we will only support it being a DVD Directory Image
        # So check to see if the expected file is set
        vobFile = self.getVOBFile()
        if vobFile is not None:
            return vobFile

        return self.filename

    # Gets the path to the VOB playable file, or None if not a VOB
    def getVOBFile(self):
        # Check to see if the filename actually holds a directory
        # If that is the case, we will only support it being a DVD Directory Image
        # So check to see if the expected file is set
        videoTSDir = os_path_join(self.filename, 'VIDEO_TS')
        if dir_exists(videoTSDir):
            ifoFile = os_path_join(videoTSDir, 'VIDEO_TS.IFO')
            if xbmcvfs.exists(ifoFile):
                return ifoFile
        # Also check for BluRay
        videoBluRayDir = os_path_join(self.filename, 'BDMV')
        if dir_exists(videoBluRayDir):
            dbmvFile = os_path_join(videoBluRayDir, 'index.bdmv')
            if xbmcvfs.exists(dbmvFile):
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
        return self.fanart

    # Returns the duration in seconds
    def getDuration(self):
        if self.duration is None:
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
                minutes = ((durationInt - seconds) % 3600) / 60

            # Default the display to MM:SS
            displayDuration = "%02d:%02d" % (minutes, seconds)

            # Only add the hours is really needed
            if durationInt > 3600:
                hours = (durationInt - (minutes * 60) - seconds) / 3600
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
        fileNoExt = os.path.splitext(filename)[0]

        # Start by searching for the filename match
        fileNoExtImage = self._loadImageFile(fileNoExt)
        if fileNoExtImage != "":
            imageList.append(fileNoExtImage)

        # Check for -poster added to the end
        fileNoExtImage = self._loadImageFile(fileNoExt + "-poster")
        if fileNoExtImage != "":
            imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for -thumb added to the end
            fileNoExtImage = self._loadImageFile(fileNoExt + "-thumb")
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for poster.jpg
            fileDir = os_path_join(self.directory, "poster")
            fileNoExtImage = self._loadImageFile(fileDir)
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)

        if len(imageList) < 2:
            # Check for folder.jpg
            fileDir = os_path_join(self.directory, "folder")
            fileNoExtImage = self._loadImageFile(fileDir)
            if fileNoExtImage != "":
                imageList.append(fileNoExtImage)

        # Set the first one to the thumbnail, and the second the the icon
        if len(imageList) > 0:
            self.thumbnailImage = imageList[0]
            if len(imageList) > 1:
                self.iconImage = imageList[1]

        # Now check for the fanart
        # Check for -fanart added to the end
        fileNoExtImage = self._loadImageFile(fileNoExt + "-fanart")
        if fileNoExtImage != "":
            self.fanart = fileNoExtImage
        else:
            # Check for fanart.jpg
            fileDir = os_path_join(self.directory, "fanart")
            fileNoExtImage = self._loadImageFile(fileDir)
            if fileNoExtImage != "":
                self.fanart = fileNoExtImage

    # Searched for a given image name under different extensions
    def _loadImageFile(self, fileNoExt):
        if xbmcvfs.exists(fileNoExt + ".tbn"):
            return fileNoExt + ".tbn"
        if xbmcvfs.exists(fileNoExt + ".png"):
            return fileNoExt + ".png"
        if xbmcvfs.exists(fileNoExt + ".jpg"):
            return fileNoExt + ".jpg"
        return ""

    # Parses the filename to work out the display name and order key
    def _generateOrderAndDisplay(self, filename):
        # First thing is to trim the display name from the filename
        # Get just the filename, don't need the full path
        displayName = os_path_split(filename)[1]
        # Remove the file extension (e.g .avi)
        displayName = os.path.splitext(displayName)[0]
        # Remove anything before the -extras- tag (if it exists)
        extrasTag = Settings.getExtrasFileTag()
        if (extrasTag != "") and (extrasTag in displayName):
            justDescription = displayName.split(extrasTag, 1)[1]
            if len(justDescription) > 0:
                displayName = justDescription

        result = (displayName, displayName)
        # Search for the order which will be written as [n]
        # Followed by the display name
        match = re.search("^\[(?P<order>.+)\](?P<Display>.*)", displayName)
        if match:
            orderKey = match.group('order')
            if orderKey != "":
                result = (orderKey, match.group('Display'))
        return result

    # Check for an NFO file for this video and reads details out of it
    # if it exists
    def _loadNfoInfo(self, filename):
        # Find out the name of the NFO file
        nfoFileName = os.path.splitext(filename)[0] + ".nfo"

        log("BaseExtrasItem: Searching for NFO file: %s" % nfoFileName)

        # Return False if file does not exist
        if not xbmcvfs.exists(nfoFileName):
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
                if (season is None) or (season == ""):
                    season = "0"
                if (episode is None) or (episode == ""):
                    episode = "0"
                self.orderKey = "%02d_%02d" % (int(season), int(episode))

            else:
                self.displayName = None
                self.orderKey = None
                log("BaseExtrasItem: Unknown NFO format")

            # Now get the thumbnail - always called the same regardless of
            # movie of TV
            thumbnail = self._getNfoThumb(nfoXml)
            if thumbnail is not None:
                self.thumbnailImage = thumbnail

            # Now get the fanart - always called the same regardless of
            # movie of TV
            fanart = self._getNfoFanart(nfoXml)
            if (fanart is not None) and (fanart != ""):
                self.fanart = fanart

            del nfoXml

            if (self.displayName is not None) and (self.displayName != ""):
                returnValue = True
                # If there is no order specified, use the display name
                if (self.orderKey is None) or (self.orderKey == ""):
                    self.orderKey = self.displayName
                log("BaseExtrasItem: Using sort key %s for %s" % (self.orderKey, self.displayName))
        except:
            log("BaseExtrasItem: Failed to process NFO: %s" % nfoFileName)
            log("BaseExtrasItem: %s" % traceback.format_exc())
            returnValue = False

        return returnValue

    # Sets the title for a given extras file
    def setTitle(self, newTitle, isTV=False):
        log("BaseExtrasItem: Setting title to %s" % newTitle)
        self.displayName = newTitle

        # Find out the name of the NFO file
        nfoFileName = os.path.splitext(self.filename)[0] + ".nfo"

        log("BaseExtrasItem: Searching for NFO file: %s" % nfoFileName)

        try:
            nfoFileStr = None
            newNfoRequired = False

            if xbmcvfs.exists(nfoFileName):
                # Need to first load the contents of the NFO file into
                # a string, this is because the XML File Parse option will
                # not handle formats like smb://
                nfoFile = xbmcvfs.File(nfoFileName, 'r')
                nfoFileStr = nfoFile.read()
                nfoFile.close()

            # Check to ensure we have some NFO data
            if (nfoFileStr is None) or (nfoFileStr == ""):
                # Create a default NFO File
                # Need to create a new file if one does not exist
                log("BaseExtrasItem: No NFO file found, creating new one: %s" % nfoFileName)
                tagType = 'movie'
                if isTV:
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
            if titleElement is None:
                log("BaseExtrasItem: title element not found")
                return False

            # Set the title to the new value
            titleElement.text = newTitle

            # Only set the sort title if already set
            sorttitleElement = nfoXml.find('sorttitle')
            if sorttitleElement is not None:
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

    # Sets the title for a given extras file
    def setPlot(self, newPlot, isTV=False):
        log("BaseExtrasItem: Setting plot to %s" % newPlot)
        self.plot = newPlot

        # Find out the name of the NFO file
        nfoFileName = os.path.splitext(self.filename)[0] + ".nfo"

        log("BaseExtrasItem: Searching for NFO file: %s" % nfoFileName)

        try:
            nfoFileStr = None
            newNfoRequired = False

            if xbmcvfs.exists(nfoFileName):
                # Need to first load the contents of the NFO file into
                # a string, this is because the XML File Parse option will
                # not handle formats like smb://
                nfoFile = xbmcvfs.File(nfoFileName, 'r')
                nfoFileStr = nfoFile.read()
                nfoFile.close()

            # Check to ensure we have some NFO data
            if (nfoFileStr is None) or (nfoFileStr == ""):
                # Create a default NFO File
                # Need to create a new file if one does not exist
                log("BaseExtrasItem: No NFO file found, creating new one: %s" % nfoFileName)
                tagType = 'movie'
                if isTV:
                    tagType = 'tvshow'

                nfoFileStr = ("<%s>\n    <plot> </plot>\n</%s>\n" % (tagType, tagType))
                newNfoRequired = True

            # Create an XML parser
            try:
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr))
            except:
                log("BaseExtrasItem: Trying encoding to UTF-8 with ignore")
                nfoXml = ET.ElementTree(ET.fromstring(nfoFileStr.decode("UTF-8", 'ignore')))

            # Get the plot element
            plotElement = nfoXml.find('plot')

            # Make sure the title exists in the file
            if plotElement is None:
                log("BaseExtrasItem: plot element not found")
                return False

            # Set the plot to the new value
            plotElement.text = newPlot

            # Save the file back to the file-system
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
        if (thumbnail is not None) and (thumbnail != ""):
            # Found the thumb entry, check if this is a local path
            # which just has a filename, this is the case if there are
            # no forward slashes and no back slashes
            if thumbnail.startswith('..') or (("/" not in thumbnail) and ("\\" not in thumbnail)):
                thumbnail = os_path_join(self.directory, thumbnail)
        else:
            thumbnail = None
        return thumbnail

    # Reads the fanart information from an NFO file
    def _getNfoFanart(self, nfoXml):
        # Get the fanart
        fanart = nfoXml.findtext('fanart')
        if (fanart is not None) and (fanart != ""):
            # Found the fanart entry, check if this is a local path
            # which just has a filename, this is the case if there are
            # no forward slashes and no back slashes
            if fanart.startswith('..') or (("/" not in fanart) and ("\\" not in fanart)):
                fanart = os_path_join(self.directory, fanart)
        else:
            fanart = None
        return fanart


####################################################################
# Extras item that extends the base type to supply extra information
# that can be read or set via a database
####################################################################
class ExtrasItem(BaseExtrasItem):
    def __init__(self, directory, filename, isFileMatchExtra=False, extrasDb=None, defaultFanArt=""):
        self.extrasDb = extrasDb
        self.watched = 0
        self.totalDuration = -1
        self.resumePoint = 0

        BaseExtrasItem.__init__(self, directory, filename, isFileMatchExtra, defaultFanArt)
        self._loadState()

    # Note: An attempt was made to re-use the existing XBMC database to
    # read the playcount to work out if a video file has been watched,
    # however this did not seem to work, call was:
    # json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Files.GetFileDetails", "params": {"file": "%s", "media": "video", "properties": [ "playcount" ]},"id": 1 }' % filename)
    # Even posted on the forum, but this hasn't resolved it:
    # http://forum.xbmc.org/showthread.php?tid=177368
    # UPDATE: Found out what the problem was, with window paths you need to additionally escape them!
    #         self.getFilename().replace("\\", "\\\\")
    # However, as it turns out, we can't use the official database, as it only stores the "playcount"
    # (The number of time the file has been played) and nothing about the resume point for partially
    # played files
    def getWatched(self):
        return self.watched

    # If the playing progress should be recorded for this file, things like
    # ISO's and VOBs do not handle this well as the incorrect values are
    # returned from the player
    def shouldStoreProgress(self):
        if self.getVOBFile() is not None:
            return False
        # Get the extension of the file
        fileExt = os.path.splitext(self.getFilename())[1]
        if (fileExt is None) or (fileExt == "") or (fileExt.lower() == '.iso'):
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

        if self.extrasDb is None:
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
        if self.extrasDb is None:
            log("ExtrasItem: Database not enabled")
            return

        log("ExtrasItem: Loading state for %s" % self.getFilename())

        returnData = self.extrasDb.select(self.getFilename())

        if returnData is not None:
            self.resumePoint = returnData['resumePoint']
            self.totalDuration = returnData['totalDuration']
            self.watched = returnData['watched']

    def createListItem(self, path="", parentTitle="", tvShowTitle="", defaultIconImage=""):
        # Label2 is used to store the duration in HH:MM:SS format
        anItem = xbmcgui.ListItem(self.getDisplayName(), self.getDisplayDuration(), path=path)
        anItem.setProperty("FileName", self.getFilename())
        anItem.setInfo('video', {'PlayCount': self.getWatched()})
        anItem.setInfo('video', {'Title': parentTitle})
        # We store the duration here, but it is only in minutes and does not
        # look very good if displayed, so we also set Label2 to a viewable value
        intDuration = self.getDuration()
        # Only add the duration if there is one
        if intDuration > 0:
            anItem.setInfo('video', {'Duration': int(self.getDuration() / 60)})
        if tvShowTitle != "":
            anItem.setInfo('video', {'TvShowTitle': tvShowTitle})

        # If the plot is supplied, then set it
        plot = self.getPlot()
        if (plot is not None) and (plot != ""):
            anItem.setInfo('video', {'Plot': plot})
        # If the order sort title is supplied, then set it
        orderKey = self.getOrderKey()
        if (orderKey is not None) and (orderKey != ""):
            anItem.setInfo('video', {'sorttitle': orderKey})

        # If both the Icon and Thumbnail is set, the list screen will choose to show
        # the thumbnail
        if self.getIconImage() != "":
            anItem.setIconImage(self.getIconImage())
        if self.getThumbnailImage() != "":
            anItem.setThumbnailImage(self.getThumbnailImage())

        # Set the default image if available
        if defaultIconImage != "":
            if (self.getIconImage() == "") and (self.getThumbnailImage() == ""):
                anItem.setIconImage(defaultIconImage)

        # The following two will give us the resume flag
        anItem.setProperty("TotalTime", str(self.getTotalDuration()))
        anItem.setProperty("ResumeTime", str(self.getResumePoint()))

        # Set the background image
        anItem.setProperty("Fanart_Image", self.getFanArt())

        return anItem

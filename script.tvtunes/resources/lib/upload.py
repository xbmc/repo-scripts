# -*- coding: utf-8 -*-
import os
import sys
import base64
import random
import xml.etree.ElementTree as ET
import traceback
import urllib2
import ftplib
import xbmc
import xbmcaddon
import xbmcvfs

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

from settings import Settings
from settings import log
from settings import dir_exists
from themeFinder import ThemeFiles
from idLookup import IdLookup
from library import ThemeLibrary

ADDON = xbmcaddon.Addon(id='script.tvtunes')
ADDON_ID = ADDON.getAddonInfo('id')


# Class to handle the uploading of themes
class UploadThemes(ThemeLibrary):
    def __init__(self):
        ThemeLibrary.__init__(self)

        # Set up the addon directories if they do not already exist
        if not dir_exists(xbmc.translatePath('special://profile/addon_data/%s' % ADDON_ID).decode("utf-8")):
            xbmcvfs.mkdir(xbmc.translatePath('special://profile/addon_data/%s' % ADDON_ID).decode("utf-8"))

        self.tvtunesUploadRecord = xbmc.translatePath('special://profile/addon_data/%s/tvtunesUpload.xml' % ADDON_ID).decode("utf-8")

        # Records if the entire upload system is disabled
        self.uploadsDisabled = False
        self.isVideoEnabled = True
        self.isAudioEnabled = True
        self.isTvShowsEnabled = True
        self.isMoviesEnabled = True
        self.skipMultipleThemes = False

        self.ftpArg = None
        self.userArg = None
        self.passArg = None

        self.uploadRecord = None

    # Loads all of the configuration settings
    def loadConfig(self):
        log("UploadThemes: Loading Upload Config")
        try:
            remoteSettings = urllib2.urlopen(base64.b64decode(Settings.getUploadSettings()))
            uploadSetting = remoteSettings.read()
            # Closes the connection after we have read the remote settings
            try:
                remoteSettings.close()
            except:
                log("UploadThemes: Failed to close connection for upload settings", xbmc.LOGERROR)

            # Check all of the settings
            uploadSettingET = ET.ElementTree(ET.fromstring(base64.b64decode(uploadSetting)))

            # First check to see if uploads are actually enabled
            isEnabled = uploadSettingET.find('enabled')
            if (isEnabled is None) or (isEnabled.text != 'true'):
                log("UploadThemes: Uploads disabled via online settings")
                self.uploadsDisabled = True
                return

            minVersion = uploadSettingET.find('version')
            if minVersion not in [None, ""]:
                if not self._isSupportedVersion(minVersion.text):
                    log("UploadThemes: Uploads disabled for older version")
                    self.uploadsDisabled = True
                    return

            # Check if audio uploads are enabled
            isAudioElem = uploadSettingET.find('audio')
            if (isAudioElem is None) or (isAudioElem.text != 'true'):
                log("UploadThemes: Uploads disabled for audio via online settings")
                self.isAudioEnabled = False

            # Check if video uploads are enabled
            isVideoElem = uploadSettingET.find('video')
            if (isVideoElem is None) or (isVideoElem.text != 'true'):
                log("UploadThemes: Uploads disabled for videos via online settings")
                self.isVideoEnabled = False

            # Check if tv show uploads are enabled
            isTvShowsElem = uploadSettingET.find('tvshows')
            if (isTvShowsElem is None) or (isTvShowsElem.text != 'true'):
                log("UploadThemes: Uploads disabled for tvshows via online settings")
                self.isTvShowsEnabled = False

            # Check if movie uploads are enabled
            isMoviesElem = uploadSettingET.find('movies')
            if (isMoviesElem is None) or (isMoviesElem.text != 'true'):
                log("UploadThemes: Uploads disabled for movies via online settings")
                self.isMoviesEnabled = False

            isSkipMultipleElem = uploadSettingET.find('skipmultiple')
            if (isSkipMultipleElem is None) or (isSkipMultipleElem.text != 'false'):
                log("UploadThemes: Skip Multiple enabled via online settings")
                self.skipMultipleThemes = True

            # Check if a reset is required
            isRecordResetElem = uploadSettingET.find('recordreset')
            if (isRecordResetElem is not None) and (isRecordResetElem.text == 'true'):
                log("UploadThemes: Clearing local record")
                if xbmcvfs.exists(self.tvtunesUploadRecord):
                    xbmcvfs.delete(self.tvtunesUploadRecord)

            # Get the details for where themes are uploaded to
            ftpArgElem = uploadSettingET.find('ftp')
            userArgElem = uploadSettingET.find('username')
            passArgElem = uploadSettingET.find('password')
            if (ftpArgElem in ["", None]) or (userArgElem in ["", None]) or (passArgElem in ["", None]):
                log("UploadThemes: Online settings not correct")
                self.uploadsDisabled = True
                return

            # Save off the values we have now read from the config file
            self.ftpArg = ftpArgElem.text
            self.userArg = userArgElem.text
            self.passArg = passArgElem.text
        except:
            log("UploadThemes: Failed to read upload settings %s" % traceback.format_exc(), xbmc.LOGERROR)
            # If we have had an error, stop trying to do any uploads
            self.uploadsDisabled = True

        # Now also load the existing elements that are in the library
        loadOK = self.loadLibraryContents()

        # If we failed to load then disable everything
        if not loadOK:
            log("UploadThemes: Disabling as load library failed")
            self.uploadsDisabled = True

        # Check if the upload record file exists, if it does read it in
        if xbmcvfs.exists(self.tvtunesUploadRecord):
            try:
                recordFile = xbmcvfs.File(self.tvtunesUploadRecord, 'r')
                recordFileStr = recordFile.read()
                recordFile.close()

                self.uploadRecord = ET.ElementTree(ET.fromstring(recordFileStr))
            except:
                log("UploadThemes: Failed to read in file %s" % self.tvtunesUploadRecord, xbmc.LOGERROR)
                log("UploadThemes: %s" % traceback.format_exc(), xbmc.LOGERROR)
        else:
            # <tvtunesUpload machineid="XXXXXXXXX">
            #    <tvshows></tvshows>
            #    <movies></movies>
            # </tvtunesUpload>
            try:
                root = ET.Element('tvtunesUpload')
                root.attrib['machineid'] = Settings.getTvTunesId()
                tvshows = ET.Element('tvshows')
                movies = ET.Element('movies')
                root.append(tvshows)
                root.append(movies)
                self.uploadRecord = ET.ElementTree(root)
            except:
                log("UploadThemes: Failed to create XML Content %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Gets all the themes of a given type
    def processVideoThemes(self, jsonGet, target):
        # Only process anything if it is enabled
        if self.uploadsDisabled:
            return

        # Check if we need to upload the TV Shows
        if (target == 'tvshows') and not self.isTvShowsEnabled:
            return

        # Check if we need to upload the movies
        if (target == 'movies') and not self.isMoviesEnabled:
            return

        # Get the videos that are in the library
        themeList = self.getVideos(jsonGet, target)

        lastFileUploaded = False
        for videoItem in themeList:
            # We want to wait between each upload, there is no rush and we do not want
            # to interfere with anything that is playing, so spread out the uploads
            # As each sleep is a tenth of a second, lets split the uploads by 5 minutes each
            uploadWait = 3000
            while (uploadWait > 0) and lastFileUploaded:
                # Check to make sure we have not been requested to stop yet
                if xbmc.abortRequested:
                    return
                # Wait for a tenth of a second
                xbmc.sleep(100)
                uploadWait = uploadWait - 1

            lastFileUploaded = self.uploadThemeItem(videoItem)

            # Check if all uploads were disabled
            if self.uploadsDisabled or xbmc.abortRequested:
                return

    # Do a lookup in the database for the given type of videos
    def getVideos(self, jsonGet, target):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.%s", "params": {"properties": ["title", "file", "imdbnumber", "year"], "sort": { "method": "title" } }, "id": 1}' % jsonGet)
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log(json_response)
        videolist = []
        if ("result" in json_response) and (target in json_response['result']):
            for item in json_response['result'][target]:
                # Before we process anything make sure we are not due to shut down
                if xbmc.abortRequested:
                    return []

                videoItem = {}
                # Record if this is tvshows or movies
                videoItem['type'] = target
                videoItem['title'] = item['title'].encode("utf-8")
                videoItem['year'] = item['year']
                # The file is actually the path for a TV Show, the video file for movies
                videoItem['file'] = item['file']
                # The name is a bit misleading, it's the ID for whatever scanner was used
                videoItem['imdbnumber'] = str(item['imdbnumber'])

                # Not sure why there would be a video in the library without an ID, but check just in case
                if videoItem['imdbnumber'] in ["", None]:
                    continue

                isTvShow = False
                if target == 'tvshows':
                    isTvShow = True

                # We have an ID for the video, check to see if we already have
                # something uploaded with this ID
                matchedThemeIds = self._getThemes(videoItem['imdbnumber'], isTvShow)

                if matchedThemeIds not in [None, ""]:
                    log("UploadThemes: Theme for target %s and id %s already in library" % (target, videoItem['imdbnumber']))
                    continue

                # Get the themes if they exist
                themeFileMgr = ThemeFiles(videoItem['file'], videotitle=item['title'])

                # Make sure there are themes
                if not themeFileMgr.hasThemes():
                    continue

                if (len(themeFileMgr.getThemeLocations()) > 1) and self.skipMultipleThemes:
                    log("UploadThemes: Skipping multiple themes")
                    continue

                # Check if any of the themes available as suitable for upload
                requiredThemes = self._getThemesToUpload(videoItem['imdbnumber'], themeFileMgr.getThemeLocations())
                if len(requiredThemes) < 1:
                    log("UploadThemes: No Required themes found")
                    continue

                # This video has themes that are needed
                videoItem['themes'] = requiredThemes

                # Also check our local record of things that have already been done
                if self.isThemeAlreadyUploaded(videoItem):
                    log("UploadThemes: Theme %s already uploaded" % videoItem['imdbnumber'])
                    continue

                videolist.append(videoItem)

        # Before returning the list, randonise it so that things are not always in the same order
        random.shuffle(videolist)

        return videolist

    # Will upload the details for a given file
    def uploadThemeItem(self, videoItem):
        isTvShow = False
        if videoItem['type'] == 'tvshows':
            isTvShow = True

        # Use the details of this video to find the ID we need
        idLookup = IdLookup()
        checkedIdDetails = idLookup.getIds(videoItem['title'], videoItem['year'], isTvShow)
        del idLookup

        # The Id we use is either the imdb for movies or the tvdb for TV Shows
        masterId = checkedIdDetails['imdb']
        if isTvShow:
            masterId = checkedIdDetails['tvdb']
        else:
            # For movies we want the tmdb value as well as imdb
            if checkedIdDetails['tmdb'] in [None, ""]:
                log("UploadThemes: No TMDB id found for %s" % videoItem['imdbnumber'])
                return False

        if masterId in [None, ""]:
            log("UploadThemes: No suitable Id found for %s" % videoItem['imdbnumber'])
            return False

        # Check all the IDs to see if this theme is required
        matchedThemeIds = self._getThemes(masterId, isTvShow)

        if matchedThemeIds not in [None, ""]:
            log("UploadThemes: Theme %s already in library" % masterId)
            return False

        # Now set the master id to the one we have just found
        # that will be used from now on
        videoItem['masterId'] = masterId

        # Perform the upload
        result = self.uploadFile(videoItem)

        # Check if all uploads were disabled
        if self.uploadsDisabled:
            return False

        # Need to record that this videos themes have been uploaded
        if result:
            # Update the local record file
            self.recordUploadedFile(videoItem)

        return result

    # Check if a theme has already been uploaded
    def isThemeAlreadyUploaded(self, videoItem):
        alreadyUploaded = False
        # Check for the correct type
        typeElm = self.uploadRecord.find(videoItem['type'])
        if typeElm is not None:
            for elemItem in typeElm.findall(videoItem['type'][:-1]):
                if elemItem.attrib['id'] == videoItem['imdbnumber']:
                    # Check each theme to ensure they have all been uploaded
                    themesToUpload = []
                    for localTheme in videoItem['themes']:
                        themeMatched = False
                        # Check if this theme is in the local record
                        for themeRec in elemItem.findall('theme'):
                            if themeRec.text == localTheme:
                                themeMatched = True
                                break
                        if not themeMatched:
                            themesToUpload.append(localTheme)
                    # Check if we have any themes to upload
                    if len(themesToUpload) > 0:
                        videoItem['themes'] = themesToUpload
                    else:
                        alreadyUploaded = True
                    # Found the item we were looking for so stop looking
                    break
        return alreadyUploaded

    # Saves the themes that have been uploaded
    def recordUploadedFile(self, videoItem):
        log("UploadThemes: Uploaded (%s) id:%s, title:%s, themePath:%s, themes:%s" % (videoItem['type'], videoItem['imdbnumber'], videoItem['title'], videoItem['file'], len(videoItem['themes'])))

        record = self.uploadRecord.find(videoItem['type'])

        # Check to see if this video item is already there
        videoElem = None
        for existingVidElem in record.findall(videoItem['type'][:-1]):
            if existingVidElem is not None:
                existingId = existingVidElem.attrib['id']
                if existingId == videoItem['imdbnumber']:
                    videoElem = existingVidElem
                    break

        # Check the case where the item does not already exist
        if videoElem is None:
            videoElem = ET.Element(videoItem['type'][:-1])
            videoElem.attrib['id'] = videoItem['imdbnumber']

            title = ET.SubElement(videoElem, 'title')
            title.text = videoItem['title']
            record.append(videoElem)

        for themeName in videoItem['themes']:
            alreadyRecorded = False
            # Check if the theme already exists
            for themeRec in videoElem.findall('theme'):
                if themeRec.text == themeName:
                    alreadyRecorded = True
                    break
            if not alreadyRecorded:
                themeFile = ET.SubElement(videoElem, 'theme')
                themeFile.text = themeName

        fileContent = ET.tostring(self.uploadRecord.getroot(), encoding="UTF-8")

        # Save the XML file to disk
        recordFile = xbmcvfs.File(self.tvtunesUploadRecord, 'w')
        try:
            recordFile.write(fileContent)
        except:
            log("UploadThemes: Failed to write file: %s" % recordFile, xbmc.LOGERROR)
            log("UploadThemes: %s" % traceback.format_exc(), xbmc.LOGERROR)
        recordFile.close()

    # Filters the theme to work out which are needed
    def _getThemesToUpload(self, id, themes):
        themeList = []
        for theme in themes:
            maxFileSize = 104857600
            if Settings.isVideoFile(theme):
                # Check if all videos are disabled
                if not self.isVideoEnabled:
                    continue
            else:
                # Check if all audio are disabled
                if not self.isAudioEnabled:
                    continue

                # Audio files have a smaller limit
                maxFileSize = 20971520

            # Check to make sure the theme file is not too large, anything over 100 megabytes
            # is too large for a theme
            stat = xbmcvfs.Stat(theme)
            themeFileSize = stat.st_size()
            if themeFileSize > maxFileSize:
                log("UploadThemes: Theme %s too large %s" % (theme, themeFileSize))
                continue
            if themeFileSize < 19460:
                log("UploadThemes: Theme %s too small %s" % (theme, themeFileSize))
                continue

            # If we reach here it is not in either exclude list
            themeList.append(theme)
        return themeList

    # Handles the uploading of a given file
    def uploadFile(self, videoItem):
        fileUploaded = False
        # Get the name of the folder to store this theme in
        remoteDirName = videoItem['masterId']

        log("UploadThemes: Checking upload for theme directory %s" % remoteDirName)

        # Check to make sure there are themes to process
        if len(videoItem['themes']) < 1:
            log("UploadThemes: No themes set to process")
            return False

        ftp = None
        try:
            # Connect to the ftp server
            ftp = ftplib.FTP(self.ftpArg, self.userArg, self.passArg)

            if xbmc.abortRequested:
                ftp.quit()
                return False

            # Now we are connected go into the uploads directory, this should always exist
            ftp.cwd('uploads')

            if xbmc.abortRequested:
                ftp.quit()
                return False

            # Check if uploads were enabled, if there is a file called enabled.txt then it
            # means the server is configured to receive uploads
            if 'enabled.txt' not in ftp.nlst():
                # Uploads are disabled if the file does not exist
                log("UploadThemes: Uploads are disabled")
                self.uploadsDisabled = True
                ftp.quit()
                return False

            # Then into whichever type we are uploading, again this is pre-created
            ftp.cwd(videoItem['type'])

            if xbmc.abortRequested:
                ftp.quit()
                return False

            # Get the list of all the directories that exist, and see if the one we need is there
            if remoteDirName not in ftp.nlst():
                # Directory does not exist, so create it
                log("UploadThemes: Directory does not exist, creating %s" % remoteDirName)
                ftp.mkd(remoteDirName)

            if xbmc.abortRequested:
                ftp.quit()
                return False

            # Go into the required directory
            ftp.cwd(remoteDirName)

            if xbmc.abortRequested:
                ftp.quit()
                return False

            dirContents = ftp.nlst()

            # Need to check each theme to see if it needs to be uploaded
            themeNum = 0
            for aTheme in videoItem['themes']:
                if xbmc.abortRequested:
                    ftp.quit()
                    return False

                # Get the file Extension
                fileExt = os.path.splitext(aTheme)[1]
                if fileExt in ["", None]:
                    continue

                # Check to see if this file is larger than the largest file
                # that already exists
                largestFilesize = 0
                for fileInDir in dirContents:
                    # Skip hidden files and directory markers
                    if fileInDir.startswith('.'):
                        continue
                    # Check if it is the same filetype
                    if fileInDir.endswith(fileExt):
                        thisFileSize = ftp.size(fileInDir)

                        if xbmc.abortRequested:
                            ftp.quit()
                            return False

                        if thisFileSize > largestFilesize:
                            largestFilesize = thisFileSize

                log("UploadThemes: Largest file on server %s (%s) is %d" % (remoteDirName, fileExt, largestFilesize))

                stat = xbmcvfs.Stat(aTheme)
                currentFileSize = stat.st_size()

                log("UploadThemes: Theme file %s has a size of %d" % (aTheme, currentFileSize))

                # Check all of the themes to see if their size is larger than what is already there
                if currentFileSize > largestFilesize:
                    log("UploadThemes: Uploading new file of size %d" % currentFileSize)

                    # Name the file using the machine it comes from
                    fileToCreate = Settings.getTvTunesId()
                    if themeNum > 0:
                        fileToCreate = fileToCreate + "-" + str(themeNum)
                    # Now add the extension to it
                    fileToCreate = fileToCreate + fileExt
                    themeNum = themeNum + 1

                    # Transfer the file in binary mode
                    srcFile = xbmcvfs.File(aTheme, 'rb')
                    ftp.storbinary("STOR " + fileToCreate, srcFile)
                    srcFile.close()

                    fileUploaded = True
                    log("UploadThemes: Uploading of file %s complete" % fileToCreate)

            # Exit the ftp session
            ftp.quit()

        except:
            log("UploadThemes: Failed to upload file %s" % traceback.format_exc(), xbmc.LOGERROR)
            # If we have had an error, stop trying to do any uploads
            self.uploadsDisabled = True
            if ftp is not None:
                # Do a forced close to ensure the connection is no longer active
                try:
                    ftp.close()
                except:
                    pass
            fileUploaded = False

        return fileUploaded

    # Checks if the version installed is supported
    def _isSupportedVersion(self, requiredVersion):
        # Check if there is no minimum version set
        if requiredVersion in [None, ""]:
            return True

        log("UploadThemes: Required version is %s" % requiredVersion)

        # Get the current version
        currentVersion = ADDON.getAddonInfo('version')
        log("UploadThemes: Current version is %s" % currentVersion)

        # Split each version into parts
        requiredVersionParts = requiredVersion.split('.')
        currentVersionParts = currentVersion.split('.')

        try:
            if (len(requiredVersionParts) > 0) and (len(currentVersionParts) > 0):
                if int(currentVersionParts[0]) < int(requiredVersionParts[0]):
                    return False
                elif int(currentVersionParts[0]) > int(requiredVersionParts[0]):
                    return True
            if (len(requiredVersionParts) > 1) and (len(currentVersionParts) > 1):
                if int(currentVersionParts[1]) < int(requiredVersionParts[1]):
                    return False
                elif int(currentVersionParts[1]) > int(requiredVersionParts[1]):
                    return True
            if (len(requiredVersionParts) > 2) and (len(currentVersionParts) > 2):
                if int(currentVersionParts[2]) < int(requiredVersionParts[2]):
                    return False
                elif int(currentVersionParts[2]) > int(requiredVersionParts[2]):
                    return True
        except:
            log("UploadThemes: Problem checking version (%s and %s)" % (requiredVersion, currentVersion), xbmc.LOGERROR)

        return True


#########################
# Main
#########################
if __name__ == '__main__':
    log("UploadThemes: Upload themes called")

    # We want to avoid and errors appearing on the screen, not the end of the world
    # if it fails to upload the themes
    try:
        uploadMgr = UploadThemes()

        # Load all of the config settings
        uploadMgr.loadConfig()

        # We want to process all the Videos (TV and Movies) but no need to get them all at
        # once, so start with TV and then move onto Movies later
        if not xbmc.abortRequested:
            uploadMgr.processVideoThemes('GetTVShows', 'tvshows')

        # If the system is not being shut down, move onto the movies
        if not xbmc.abortRequested:
            uploadMgr.processVideoThemes('GetMovies', 'movies')

        del uploadMgr
    except:
        log("UploadThemes: Error while running: %s" % traceback.format_exc())

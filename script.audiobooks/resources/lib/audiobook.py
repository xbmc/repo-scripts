# -*- coding: utf-8 -*-
import os
import locale
import sys
import re
import subprocess
import traceback
import xbmc
import xbmcvfs
import xbmcgui
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.audiobooks')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__media__ = xbmc.translatePath(os.path.join(__resource__, 'media').encode("utf-8")).decode("utf-8")

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split

from database import AudioBooksDB


# Generic class for handling audiobook details
class AudioBookHandler():
    def __init__(self, audioBookFilePath):
        self.filePath = audioBookFilePath
        self.fileName = os_path_split(audioBookFilePath)[-1]
        self.coverImage = None
        self.title = None
        self.chapters = []
        self.numChapters = 0
        self.position = -1
        self.chapterPosition = -1
        self.totalDuration = -1
        self.isComplete = None

    @staticmethod
    def createHandler(audioBookFilePath):
        audiobookType = None
        # Check which type of Audiobook it is
        if audioBookFilePath.lower().endswith('.m4b'):
            audiobookType = M4BHandler(audioBookFilePath)
        else:
            audiobookType = FolderHandler(audioBookFilePath)

        return audiobookType

    # Will load the basic details needed for simple listings
    def _loadDetails(self):
        log("AudioBookHandler: Loading audio book %s (%s)" % (self.filePath, self.fileName))

        # Check to see if we already have an image available
        self.coverImage = self._getExistingCoverImage()

        # Check in the database to see if this audio book is already recorded
        audiobookDB = AudioBooksDB()
        audiobookDetails = audiobookDB.getAudioBookDetails(self.filePath)

        if audiobookDetails not in [None, ""]:
            self.title = audiobookDetails['title']
            self.numChapters = audiobookDetails['numChapters']
            self.position = audiobookDetails['position']
            self.chapterPosition = audiobookDetails['chapterPosition']
            self.isComplete = audiobookDetails['complete']
        else:
            self.position = 0
            self.chapterPosition = 0
            self.isComplete = False
            self._loadSpecificDetails()

            if self.title in [None, ""]:
                log("AudioBookHandler: No title found for %s, using filename" % self.filePath)
                self.title = self._getFallbackTitle()

            self.numChapters = len(self.chapters)

            # Now update the database entry for this audio book
            audiobookDB.addAudioBook(self.filePath, self.title, self.numChapters)

        del audiobookDB

    def _loadSpecificDetails(self, includeCover=True):
        pass

    def getFile(self, tryUtf8=False):
        filePathValue = self.filePath
        if tryUtf8:
            try:
                filePathValue = filePathValue.encode("utf-8")
            except:
                pass
        return filePathValue

    def getTitle(self):
        if self.title in [None, ""]:
            self._loadDetails()
        return self.title

    def getCoverImage(self, tryUtf8=False):
        if self.coverImage is None:
            self._loadDetails()

        coverImageValue = self.coverImage
        # Make sure the cover is correctly encoded
        if tryUtf8 and (coverImageValue not in [None, ""]):
            try:
                coverImageValue = coverImageValue.encode("utf-8")
            except:
                pass

        return coverImageValue

    def getPosition(self):
        if self.position < 0:
            self._loadDetails()
        return self.position, self.chapterPosition

    def getChapterDetails(self):
        # If the chapter information has not been loaded yet, then we need to load it
        if len(self.chapters) < 1:
            self._loadSpecificDetails(includeCover=False)
        return self.chapters

    def getTotalDuration(self):
        if self.totalDuration < 0:
            # The duration is actually set by the last chapter
            self._loadSpecificDetails(includeCover=False)
        return self.totalDuration

    def isCompleted(self):
        if self.isComplete is None:
            self._loadDetails()
        return self.isComplete

    def getChapterPosition(self, filename):
        # Default behaviour is to not track using the chapter
        return 0

    # Create a list item from an audiobook details
    def getPlayList(self, startTime=-1, startChapter=0):
        log("AudioBookHandler: Getting playlist to start for time %d" % startTime)
        listitem = self._getListItem(self.getTitle(), startTime)

        # Wrap the audiobook up in a playlist
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()
        playlist.add(self.getFile(), listitem)

        return playlist

    # Create a list item from an audiobook details
    def _getListItem(self, title, startTime=-1, chapterTitle=''):
        log("AudioBookHandler: Getting listitem for %s (Chapter: %s)" % (title, chapterTitle))

        listitem = xbmcgui.ListItem()
        # Set the display title on the music player
        # Have to set this as video otherwise it will not start the audiobook at the correct Offset place
        listitem.setInfo('video', {'Title': title})

        if chapterTitle not in [None, ""]:
            listitem.setInfo('music', {'album': chapterTitle})

        # If both the Icon and Thumbnail is set, the list screen will choose to show
        # the thumbnail
        coverImage = self.getCoverImage()
        if coverImage in [None, ""]:
            coverImage = __addon__.getAddonInfo('icon')

        listitem.setIconImage(coverImage)
        listitem.setThumbnailImage(coverImage)

        # Record if the video should start playing part-way through
        startPoint = startTime
        if startTime < 0:
            startPoint = self.getPosition()
        if startPoint > 0:
            listitem.setProperty('StartOffset', str(startPoint))

        return listitem

    def _getExistingCoverImage(self):
        # Check if there is a cached version, or a local one on the drive
        fullpathLocalImage, bookExt = os.path.splitext(self.filePath)
        fullpathLocalImage = "%s.jpg" % fullpathLocalImage

        if xbmcvfs.exists(fullpathLocalImage):
            log("AudioBookHandler: Found local cached image %s" % fullpathLocalImage)
            return fullpathLocalImage

        # Check for a cached cover
        return self._getCachedCover(self.fileName)

    # Checks the cache to see if there is a cover for this audiobook
    def _getCachedCover(self, fileName):
        cachedCover = None
        # check if the directory exists before searching
        dirs, files = xbmcvfs.listdir(Settings.getCoverCacheLocation())
        for aFile in files:
            # Get the filename without extension
            coverSrc, ext = os.path.splitext(aFile)

            # Get the name that the cached cover will have been stored as
            targetSrc, bookExt = os.path.splitext(fileName)

            if targetSrc == coverSrc:
                cachedCover = os_path_join(Settings.getCoverCacheLocation(), aFile)
                log("AudioBookHandler: Cached cover found: %s" % cachedCover)

        return cachedCover

    def _getFallbackTitle(self):
        # Remove anything after the final dot
        sections = self.fileName.split('.')
        sections.pop()
        # Replace the dots with spaces
        return ' '.join(sections)

    # Runs the ffmpeg command, returning the text output, saving the cover image if
    # a target is given in the request
    def _runFFmpegCommand(self, inputFileName, coverTargetName=None):
        # Check to see if ffmpeg is enabled
        ffmpeg = Settings.getFFmpegLocation()

        if ffmpeg in [None, ""]:
            log("AudioBookHandler: ffmpeg not enabled")
            return None

        log("AudioBookHandler: Running ffmpeg for %s" % inputFileName)

        # FFmpeg will not recognise paths that start with smb:// or nfs://
        # These paths are specific to Kodi, so we need to copy the file locally
        # before we can run the FFmpeg command
        copiedFile = None
        fullFileName = inputFileName
        if fullFileName.startswith('smb://') or fullFileName.startswith('nfs://'):
            try:
                # Copy the file to the local disk
                justFileName = os_path_split(fullFileName)[-1]
                copiedFile = os_path_join(Settings.getTempLocation(), justFileName)
                copy = xbmcvfs.copy(fullFileName, copiedFile)
                if copy:
                    log("AudioBookHandler: copy successful for %s" % copiedFile)
                    fullFileName = copiedFile
                else:
                    log("AudioBookHandler: copy failed from %s to %s" % (fullFileName, copiedFile))
            except:
                log("AudioBookHandler: Failed to copy file %s to local directory" % fullFileName)

        info = None

        # Use ffmpeg to read the audio book and extract all of the details
        startupinfo = None
        if sys.platform.lower() == 'win32':
            # Need to stop the dialog appearing on windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Check if we need the image
        coverTempName = None
        if coverTargetName not in [None, '']:
            coverTempName = os_path_join(Settings.getTempLocation(), 'maincover.jpg')
            # Remove the temporary name if it is already there
            if xbmcvfs.exists(coverTempName):
                xbmcvfs.delete(coverTempName)

        try:
            # Generate the ffmpeg command
            ffmpegCmd = [ffmpeg, '-hide_banner', '-y', '-i', fullFileName]

            # Handle non ascii characters in the file name path
            try:
                ffmpegCmd[4] = ffmpegCmd[4].decode('utf-8').encode(locale.getpreferredencoding())
            except:
                log("AudioBookHandler: Failed file system encoding ffmpeg command 1, using default")
                try:
                    ffmpegCmd[4] = ffmpegCmd[4].encode(locale.getpreferredencoding())
                except:
                    log("AudioBookHandler: Failed file system encoding ffmpeg command 2, using default")

            # Add the output image to the command line if it is needed
            if coverTempName is not None:
                try:
                    coverTempName = coverTempName.decode('utf-8').encode(locale.getpreferredencoding())
                except:
                    log("AudioBookHandler: Failed file system encoding coverTempName ffmpeg command 1, using default")
                    try:
                        coverTempName = coverTempName.encode(locale.getpreferredencoding())
                    except:
                        log("AudioBookHandler: Failed file system encoding coverTempName ffmpeg command 2, using default")
                ffmpegCmd.append(coverTempName)

            # Make the ffmpeg call
            info = subprocess.check_output(ffmpegCmd, shell=False, startupinfo=startupinfo, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError as error:
            # This exception will be thrown if ffmpeg prints to STDERR, which it will do if
            # you try and run the command without an output (i.e. image file), but in most
            # cases it does actually have the information we need
            log("AudioBookHandler: CalledProcessError received, processing remaining output")
            info = error.output
        except:
            log("AudioBookHandler: Failed to get data using ffmpeg for file %s with error %s" % (self.filePath, traceback.format_exc()), xbmc.LOGERROR)

        # If we had to copy the file locally, make sure we delete it
        if copiedFile not in [None, ""]:
            if xbmcvfs.exists(copiedFile):
                xbmcvfs.delete(copiedFile)

        # Check if there is an image in the temporary location
        if coverTempName not in [None, ""]:
            if xbmcvfs.exists(coverTempName):
                # Now move the file to the covers cache directory
                copy = xbmcvfs.copy(coverTempName, coverTargetName)
                if copy:
                    log("AudioBookHandler: copy successful for %s" % coverTargetName)
                else:
                    log("AudioBookHandler: copy failed from %s to %s" % (coverTempName, coverTargetName))

                # Tidy up the image that we actually do not need
                xbmcvfs.delete(coverTempName)

        # Now the command has been run
        ffmpegOutput = None
        if info not in [None, ""]:
            ffmpegOutput = self._processFFmpegOutput(info)

        return ffmpegOutput

    # Handles the processing of the text output of ffmpeg
    def _processFFmpegOutput(self, info):
        log("AudioBookHandler: FFmpeg info is: %s" % info)

        # The pattern to find chapter info
        chapter_pattern = re.compile('^Chapter #(\d+)[\.:](\d+): start (\d+\.\d+), end (\d+\.\d+)$', re.IGNORECASE)
        # The pattern that finds the title for a chapter
        title_pattern = re.compile('^\s*title\s*:\s*(.*)$', re.IGNORECASE)
        album_pattern = re.compile('^\s*album\s*:\s*(.*)$', re.IGNORECASE)
        # The pattern to find the total duration
        duration_pattern = re.compile('^\s*Duration\s*:\s*(.*), start', re.IGNORECASE)

        title = None
        album = None
        duration = None
        chapters = []
        totalDuration = None

        # Get the title from the output
        lines = info.split('\n')
        linenum = 0

        chapterNum = 1
        while linenum < len(lines):
            line = lines[linenum]
            line = line.strip()

            # ffmpeg will list the details, first as input and then as output, so we process the input
            # and then stop when we reach output
            if line.startswith('Output '):
                break

            # Check for the first title as that will be the main title
            if title in [None, ""]:
                main_title_match = title_pattern.match(line)
                if main_title_match:
                    title = main_title_match.group(1)
                    log("AudioBookHandler: Found title in ffmpeg output: %s" % title)

            if album in [None, ""]:
                main_album_match = album_pattern.match(line)
                if main_album_match:
                    album = main_album_match.group(1)
                    log("AudioBookHandler: Found album in ffmpeg output: %s" % album)

            if duration in [None, 0, ""]:
                main_duration_match = duration_pattern.match(line)
                if main_duration_match:
                    duration = self._getSecondsInTimeString(main_duration_match.group(1))
                    log("AudioBookHandler: Found duration in ffmpeg output: %s" % duration)

            # Chapters are listed in the following format
            # ---
            # Chapter #0:29: start 26100.000000, end 27000.000000
            # Metadata:
            #   title           : Part 30
            # ---
            chapter_match = chapter_pattern.match(line)
            # If we found a chapter, skip ahead to the title and ignore the lines between them
            if not chapter_match:
                linenum += 1
                continue

            # Now extract all of the details
            title_match = title_pattern.match(lines[linenum + 2])
            linenum += 3

            # chapter_num = chapter_match.group(1)
            # chapter_subnum = chapter_match.group(2)
            start_time = int(float(chapter_match.group(3)))
            end_time = int(float(chapter_match.group(4)))
            chapterDuration = end_time - start_time

            chapterTitle = ""
            if title_match:
                chapterTitle = title_match.group(1)

            if chapterTitle in [None, ""]:
                chapterTitle = "%s %d" % (__addon__.getLocalizedString(32017), chapterNum)

            chapterNum += 1
            log("AudioBookHandler: Chapter details. Title: %s, start_time: %s, end_time: %s, duration: %d" % (chapterTitle, start_time, end_time, chapterDuration))

            detail = {'title': chapterTitle.strip(), 'startTime': start_time, 'endTime': end_time, 'duration': chapterDuration}
            chapters.append(detail)

            # The total Duration is always the end of the last chapter
            totalDuration = end_time

        # If there is no duration, then use the last chapter duration
        if duration in [None, 0, '']:
            duration = totalDuration

        returnData = {'title': title, 'album': album, 'duration': duration, 'chapters': chapters}
        return returnData

    def _getMainCoverLocation(self):
        coverFileName, oldExt = os.path.splitext(self.fileName)
        targetCoverName = "%s.jpg" % coverFileName
        coverTargetName = os_path_join(Settings.getCoverCacheLocation(), targetCoverName)

        log("AudioBookHandler: Cached cover target location is %s" % coverTargetName)
        return coverTargetName

    # Converts a time string 00:00:00.00 to the total number of seconds
    def _getSecondsInTimeString(self, fullTimeString):
        # Start by splitting the time into sections
        hours = 0
        minutes = 0
        seconds = 0

        try:
            timeParts = list(reversed(fullTimeString.split(':')))
            if len(timeParts) > 2:
                hours = int(timeParts[2])
            if len(timeParts) > 1:
                minutes = int(timeParts[1])
            if len(timeParts) > 1:
                seconds = int(float(timeParts[0]))
        except:
            # time sections are not numbers
            log("AudioBookHandler: Exception Details: %s" % traceback.format_exc())
            hours = 0
            minutes = 0
            seconds = 0

        totalInSeconds = (((hours * 60) + minutes) * 60) + seconds
        log("AudioBookHandler: Time %s, splits into hours=%d, minutes=%d, seconds=%d, total=%d" % (fullTimeString, hours, minutes, seconds, totalInSeconds))

        # Return the total time in seconds
        return totalInSeconds

    def getChapterStart(self, chapterNum):
        # Work out at what time the given chapter starts, this will be part wat through a file
        idx = chapterNum - 1
        if (idx > -1) and (len(self.chapters) > idx):
            chapterDetails = self.chapters[idx]
            return chapterDetails['startTime']
        return 0


# Class for handling m4b files
class M4BHandler(AudioBookHandler):
    def __init__(self, audioBookFilePath):
        AudioBookHandler.__init__(self, audioBookFilePath)

    # Will load the basic details needed for simple listings
    def _loadSpecificDetails(self, includeCover=True):
        # check if the cover is required
        coverTargetName = None
        if includeCover:
            coverTargetName = self._getMainCoverLocation()

        info = self._runFFmpegCommand(self.filePath, coverTargetName)

        # If we needed the cover, then save the details
        if includeCover:
            if xbmcvfs.exists(coverTargetName):
                self.coverImage = coverTargetName

        if info not in [None, ""]:
            self.title = info['title']
            self.chapters = info['chapters']
            self.totalDuration = info['duration']

    def _getFallbackTitle(self):
        # Remove anything after the final dot
        sections = self.fileName.split('.')
        sections.pop()
        # Replace the dots with spaces
        return ' '.join(sections)


# Class for handling m4b files
class FolderHandler(AudioBookHandler):
    def __init__(self, audioBookFilePath):
        AudioBookHandler.__init__(self, audioBookFilePath)
        # The fileName value will be the directory name for Folder audiobooks
        self.chapterFiles = []

    # Will load the basic details needed for simple listings
    def _loadSpecificDetails(self, includeCover=True):
        # List all the files in the directory, as that will be the chapters
        dirs, files = xbmcvfs.listdir(self.filePath)

        # Check if the cover image is required
        coverTargetName = None
        if includeCover and (self.coverImage in [None, ""]):
            coverTargetName = self._getMainCoverLocation()

        runningStartTime = 0
        for audioFile in files:
            if not Settings.isPlainAudioFile(audioFile):
                continue

            # Store this audio file in the chapter file list
            fullpath = os_path_join(self.filePath, audioFile)
            self.chapterFiles.append(fullpath)

            # Make the call to ffmpeg to get the details of the chapter
            info = self._runFFmpegCommand(fullpath, coverTargetName)

            # If we needed the cover, then save the details
            if coverTargetName not in [None, ""]:
                if xbmcvfs.exists(coverTargetName):
                    self.coverImage = coverTargetName
                    # Clear the cover image flag so we do not get it again
                    coverTargetName = None

            duration = 0
            chapterTitle = None
            endTime = 0
            if info not in [None, ""]:
                if self.title in [None, ""]:
                    self.title = info['album']
                duration = info['duration']
                chapterTitle = info['title']
                if duration not in [None, 0]:
                    endTime = runningStartTime + info['duration']

            if chapterTitle in [None, ""]:
                # Now generate the name of the chapter from the audio file
                sections = audioFile.split('.')
                sections.pop()
                # Replace the dots with spaces
                chapterTitle = ' '.join(sections)

            detail = {'title': chapterTitle, 'startTime': runningStartTime, 'endTime': endTime, 'duration': duration}
            self.chapters.append(detail)
            # Set the next start time to be after this chapter
            runningStartTime = endTime

        if runningStartTime > 0:
            self.totalDuration = runningStartTime

    # Create a list item from an audiobook details
    def getPlayList(self, startTime=-1, startChapter=0):
        log("FolderHandler: Getting playlist to start for time %d" % startTime)

        # Wrap the audiobook up in a playlist
        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        # Add each chapter file
        idx = 0
        startPosition = 0
        if startTime > 0:
            startPosition = startTime

        # Start on the correct chapter
        if startChapter > 1:
            idx = startChapter - 1

        while idx < len(self.getChapterDetails()):
            chapterDetail = self.chapters[idx]
            listitem = self._getListItem(self.getTitle(), startPosition, chapterDetail['title'])
            playlist.add(self.chapterFiles[idx], listitem)
            # Once we set the correct starting position for the main chapter, reset it
            # that that the next chapters start at the beginning
            startPosition = 0
            idx += 1

        return playlist

    def getChapterPosition(self, filename):
        chapterPosition = 0
        if len(self.chapterFiles) < 1:
            self._loadSpecificDetails(False)

        # Make sure the filename passed in is not utf-8 othersise it will not work
        compareFilename = filename
        try:
            compareFilename = compareFilename .decode('utf-8')
        except:
            pass

        if compareFilename in self.chapterFiles:
            chapterPosition = self.chapterFiles.index(compareFilename)
            chapterPosition += 1
            log("FolderHandler: Found Chapter at position %d for %s" % (chapterPosition, filename))

        return chapterPosition

    def getChapterStart(self, chapterNum):
        # As each chapter is in it's own file, it will always start at zero
        return 0

    def _getFallbackTitle(self):
        # Replace the dots with spaces
        return self.fileName.replace('.', ' ')

    def _getExistingCoverImage(self):
        # Call the common cover file check first
        coverImg = AudioBookHandler._getExistingCoverImage(self)

        # There is an extra check that we can make for folder audiobooks
        # so if one has not been found then look in the folder for folder.jpg
        if coverImg is None:
            dirs, files = xbmcvfs.listdir(self.filePath)

            for coverFile in files:
                if coverFile.lower() in ['folder.jpg', 'folder.png']:
                    coverImg = os_path_join(self.filePath, coverFile)
                    break

        return coverImg

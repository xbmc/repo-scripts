# -*- coding: utf-8 -*-
import sys
import os
import random
import time
import traceback
import xml.etree.ElementTree as ET
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.settings import list_dir
from resources.lib.settings import os_path_join
from resources.lib.settings import dir_exists
from resources.lib.settings import os_path_isfile
from resources.lib.settings import os_path_split

from resources.lib.VideoParser import VideoParser
from resources.lib.collectSets import CollectSets

ADDON = xbmcaddon.Addon(id='screensaver.video')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


# Video Screensaver Player that can detect when the next item in a playlist starts
class VideoScreensaverPlayer(xbmc.Player):
    def __init__(self, *args):
        self.initialStart = True
        xbmc.Player.__init__(self, *args)

    def onPlayBackStarted(self):
        # The first item in a playlist will have already had it's start time
        # set correctly if it is a clock
        if self.initialStart is True:
            self.initialStart = False
            log("onPlayBackStarted received for initial video")
            return

        if self.isPlayingVideo():
            # Get the currently playing file
            filename = self.getPlayingFile()
            log("onPlayBackStarted received for file %s" % filename)

            duration = self._getVideoDuration(filename)
            log("onPlayBackStarted: Duration is %d for file %s" % (duration, filename))

            startTime = Settings.getTimeForClock(filename, duration)

            # Set the clock start time
            if startTime > 0 and duration > 10:
                self.seekTime(startTime)
        else:
            log("onPlayBackStarted received, but not playing video file")

        xbmc.Player.onPlayBackStarted(self)

    # Returns the duration in seconds
    def _getVideoDuration(self, filename):
        duration = 0
        try:
            # Parse the video file for the duration
            duration = VideoParser().getVideoLength(filename)
        except:
            log("Failed to get duration from %s" % filename, xbmc.LOGERROR)
            log("Error: %s" % traceback.format_exc(), xbmc.LOGERROR)
            duration = 0

        log("Duration retrieved is = %d" % duration)

        return duration


class ScreensaverWindow(xbmcgui.WindowXMLDialog):
    TIME_CONTROL = 3002
    DIM_CONTROL = 3003
    OVERLAY_CONTROL = 3004

    def __init__(self, *args, **kwargs):
        self.isClosed = False
        self.player = VideoScreensaverPlayer()
        # Create the scheduler that will store when each item should be played
        self.scheduler = Scheduler()
        self.currentScheduleItem = -1

    # Static method to create the Window class
    @staticmethod
    def createScreensaverWindow():
        return ScreensaverWindow("screensaver-video-main.xml", CWD)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)
        self.volumeCtrl = None

        # Get the videos to use as a screensaver
        playlist = self._getPlaylist()
        # If there is nothing to play, then exit now
        if playlist is None:
            self.close()
            return

        # Update the playlist with any settings such as random start time
        self._updatePlaylistForSettings(playlist)

        # Update the volume if needed
        self.volumeCtrl = VolumeDrop()
        self.volumeCtrl.lowerVolume()

        # Now play the video
        self.player.play(playlist)

        # Set the video to loop, as we want it running as long as the screensaver
        self._setRepeat()
        log("Started playing")

        # Now check to see if we are overlaying the time on the screen
        # Default is hidden
        timeControl = self.getControl(ScreensaverWindow.TIME_CONTROL)
        timeControl.setVisible(Settings.isShowTime())

        # Set the value of the dimming for the video
        dimLevel = Settings.getDimValue()
        if dimLevel is not None:
            log("Setting Dim Level to: %s" % dimLevel)
            dimControl = self.getControl(ScreensaverWindow.DIM_CONTROL)
            dimControl.setColorDiffuse(dimLevel)

        # Set the overlay image
        self._setOverlayImage()

        # Update any settings that need to be done after the video is playing
        self._updatePostPlayingForSettings(playlist)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("Action received: %s" % str(action.getId()))
        # For any action we want to close, as that means activity
        if action.getId() in [0, "0"]:
            # When the refresh rate is set to change it can generate an
            # action with a zero Id, we need to ignore it as it is not
            # actually a user action
            log("Ignoring action %s" % str(action.getId()))
        else:
            self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("OnClick received")
        self.close()

    def isComplete(self):
        return self.isClosed

    # A request to close the window has been made, tidy up the screensaver window
    def close(self):
        log("Ending Screensaver")
        # Exiting, so stop the video
        if self.player.isPlayingVideo():
            log("Stopping screensaver video")
            # There is a problem with using the normal "xbmc.Player().stop()" to stop
            # the video playing if another addon is selected - it will just continue
            # playing the video because the call to "xbmc.Player().stop()" will hang
            # instead we use the built in option
            xbmc.executebuiltin("PlayerControl(Stop)")

        # Reset the Player Repeat
        xbmc.executebuiltin("PlayerControl(RepeatOff)", True)

        if self.volumeCtrl is not None:
            # Restore the volume
            self.volumeCtrl.restoreVolume()
            self.volumeCtrl = None

        log("Closing Window")
        # Record that we are closing
        self.isClosed = True
        xbmcgui.WindowXML.close(self)

    # Generates the playlist to use for the screensaver
    def _getPlaylist(self):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        # Note: The playlist clear option seems to impact all playlist settings,
        # so will remove the repeat settings on a playlist that is currently playing,
        # not just this instance - a bit nasty, but not much we can do about it
        playlist.clear()

        # Check to see if we should be using a video from the schedule
        scheduleEntry = self.scheduler.getScheduleEntry()

        if scheduleEntry != -1:
            # There is an item scheduled, so check to see if the item has actually changed
            if scheduleEntry == self.currentScheduleItem:
                return None
            # Set the entry we are about to play
            self.currentScheduleItem = scheduleEntry
            # Get the actual video file that should be played
            scheduledVideo = self.scheduler.getScheduleVideo(scheduleEntry)
            # Do a quick check to see if the video exists
            if xbmcvfs.exists(scheduledVideo):
                log("Screensaver video for scheduled item %d is: %s" % (scheduleEntry, scheduledVideo))
                playlist.add(scheduledVideo)

        # Check if we are showing all the videos in a given folder
        elif Settings.isFolderSelection():
            videosFolder = Settings.getScreensaverFolder()

            # Check if we are dealing with a Folder of videos
            if videosFolder not in [None, ""]:
                if dir_exists(videosFolder):
                    self.currentScheduleItem = -1
                    files = self._getAllFilesInDirectory(videosFolder)

                    # Check if we are limiting to a single folder per session
                    if Settings.isLimitSessionToSingleCollection():
                        # Select just one file at random
                        singleVideo = random.choice(files)

                        # Check if this file is part of a collection
                        justFilename = (os_path_split(singleVideo))[-1]
                        collectionCtrl = CollectSets()
                        collectionVideos = collectionCtrl.getFilesInSameCollection(justFilename)
                        del collectionCtrl

                        # If it is part of a collection, then limit to only files in
                        # this collection
                        if len(collectionVideos) > 0:
                            log("Screensaver restricting to collection containing %s" % singleVideo)
                            # Check each of the videos to see which are in the collection
                            collectionFileList = []
                            for aFile in files:
                                # Get just the filename
                                aFilename = (os_path_split(aFile))[-1]
                                if aFilename in collectionVideos:
                                    log("Screensaver including collection video %s" % aFile)
                                    collectionFileList.append(aFile)
                                else:
                                    log("Screensaver excluding non collection video %s" % aFile)
                        else:
                            log("Screensaver restricting to directory containing %s" % singleVideo)
                            # Not in a collection, so just gather the files in the same directory
                            # Get the directory that file was part of
                            parentPath = (os_path_split(singleVideo))[0]

                            # Now only select videos from that directory
                            files = self._getAllFilesInDirectory(parentPath, False)

                    # Now shuffle the playlist to ensure that if there are more
                    # than one video a different one starts each time
                    random.shuffle(files)
                    for vidFile in files:
                        log("Screensaver video in directory is: %s" % vidFile)
                        playlist.add(vidFile)
        else:
            # Must be dealing with a single file
            videoFile = Settings.getScreensaverVideo()

            # Check to make sure the screensaver video file exists
            if videoFile not in [None, ""]:
                if xbmcvfs.exists(videoFile):
                    self.currentScheduleItem = -1
                    log("Screensaver video is: %s" % videoFile)
                    playlist.add(videoFile)

        # If there are no videos in the playlist yet, then display an error
        if playlist.size() < 1:
            errorLocation = Settings.getScreensaverVideo()
            if Settings.isFolderSelection():
                errorLocation = Settings.getScreensaverFolder()

            log("No Screensaver file set or not valid %s" % errorLocation)
            cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(ADDON.getLocalizedString(32300).encode('utf-8'), errorLocation, ADDON.getAddonInfo('icon'))
            xbmc.executebuiltin(cmd)
            return None

        return playlist

    # Get the files in the directory and all subdirectories
    def _getAllFilesInDirectory(self, baseDir, includeSubDirs=True):
        videoFiles = []
        dirs, files = list_dir(baseDir)

        # Get the list of files that are to be excluded
        collectionCtrl = CollectSets()
        disabledVideos = collectionCtrl.getDisabledVideos()
        del collectionCtrl

        # Get all the files in the current directory
        for vidFile in files:
            # Check if this file is excluded
            if vidFile in disabledVideos:
                log("Ignoring disabled screensaver video %s" % vidFile)
                continue

            fullPath = os_path_join(baseDir, vidFile)
            videoFiles.append(fullPath)

        # Now check each directory
        if includeSubDirs and Settings.isFolderNested():
            for aDir in dirs:
                fullPath = os_path_join(baseDir, aDir)
                dirContents = self._getAllFilesInDirectory(fullPath)
                videoFiles = videoFiles + dirContents

        return videoFiles

    # Apply any user setting to the created playlist
    def _updatePlaylistForSettings(self, playlist):
        if playlist.size() < 1:
            return playlist

        filename = playlist[0].getfilename()
        duration = self._getVideoDuration(filename)
        log("Duration is %d for file %s" % (duration, filename))

        startTime = 0

        # Check if we have a random start time
        if Settings.isRandomStart():
            startTime = random.randint(0, int(duration * 0.75))

        clockStart = Settings.getTimeForClock(filename, duration)
        if clockStart > 0:
            startTime = clockStart

        # Set the random start
        if (startTime > 0) and (duration > 10):
            listitem = xbmcgui.ListItem()
            # Record if the theme should start playing part-way through
            listitem.setProperty('StartOffset', str(startTime))

            log("Setting start of %d for %s" % (startTime, filename))

            # Remove the old item from the playlist
            playlist.remove(filename)
            # Add the new item at the start of the list
            playlist.add(filename, listitem, 0)

        return playlist

    # Update anything needed once the video is playing
    def _updatePostPlayingForSettings(self, playlist):
        # Check if we need to start at a random location
        if Settings.isRandomStart() and playlist.size() > 0:
            # Need to reset the offset to the start so that if it loops
            # it will play from the start
            playlist[0].setProperty('StartOffset', "0")

    # Returns the duration in seconds
    def _getVideoDuration(self, filename):
        duration = 0
        try:
            # Parse the video file for the duration
            duration = VideoParser().getVideoLength(filename)
        except:
            log("Failed to get duration from %s" % filename, xbmc.LOGERROR)
            log("Error: %s" % traceback.format_exc(), xbmc.LOGERROR)
            duration = 0

        log("Duration retrieved is = %d" % duration)

        return duration

    # Set the overlay image to the correct value
    def _setOverlayImage(self):
        overlayImage = Settings.getOverlayImage()

        # Check if we should set the overlay image based on a schedule
        if self.currentScheduleItem != -1:
            overlayImage = self.scheduler.getScheduleOverlay(self.currentScheduleItem)

        overlayControl = self.getControl(ScreensaverWindow.OVERLAY_CONTROL)

        if overlayImage is not None:
            log("Setting Overlay Image to: %s" % overlayImage)
            overlayControl.setImage(overlayImage)
            overlayControl.setVisible(True)
        else:
            overlayControl.setVisible(False)

    def _setRepeat(self):
        # Set the video to loop, as we want it running as long as the screensaver
        repeatType = Settings.getFolderRepeatType()
        if repeatType is not None:
            log("Setting Repeat Type to %s" % repeatType)
            xbmc.executebuiltin("PlayerControl(%s)" % repeatType)

    def check(self):
        # Check to see if we should be changing the video for the schedule
        scheduleEntry = self.scheduler.getScheduleEntry()
        # There is an item scheduled, so check to see if the item has actually changed
        if scheduleEntry == self.currentScheduleItem:
            return None

        log("Old Schedule %d different from new: %d" % (self.currentScheduleItem, scheduleEntry))

        # Check to see if there needs to be a change in what is playing
        # This will also update the schedule item so we know what has been selected
        newPlaylist = self._getPlaylist()

        # If we reach here, there is a change of some sort
        if newPlaylist is not None:
            # Update the playlist with any settings such as random start time
            self._updatePlaylistForSettings(newPlaylist)

            # Start playing the new file, just override the existing one that is playing
            self.player.play(newPlaylist)

            # Also update the overlay
            self._setOverlayImage()

            # Now set the repeat option
            self._setRepeat()

            # Update any settings that need to be done after the video is playing
            self._updatePostPlayingForSettings(newPlaylist)


class VolumeDrop(object):
    def __init__(self, *args):
        self.screensaverVolume = Settings.getVolume()
        if self.screensaverVolume > -1:
            # Save the volume from before any alterations
            self.original_volume = self._getVolume()

    # This will return the volume in a range of 0-100
    def _getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = json.loads(result)
        if ("result" in json_query) and ('volume' in json_query['result']):
            # Get the volume value
            volume = json_query['result']['volume']

        log("VolumeDrop: current volume: %s%%" % str(volume))
        return volume

    # Sets the volume in the range 0-100
    def _setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('SetVolume(%d)' % newvolume, True)

    def lowerVolume(self):
        try:
            # If we are after a zero volume then we have the option to suspend
            # the Audio Engine
            if Settings.isUseAudioSuspend():
                xbmc.audioSuspend()
            elif self.screensaverVolume > -1:
                vol = self.screensaverVolume
                # Make sure the volume still has a value, otherwise we see the mute symbol
                if vol < 1:
                    vol = 1
                log("Player: volume goal: %d%%" % vol)
                self._setVolume(vol)
            else:
                log("Player: No reduced volume option set")
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), xbmc.LOGERROR)

    def restoreVolume(self):
        try:
            if Settings.isUseAudioSuspend():
                xbmc.audioResume()
            # Don't change the volume unless requested to
            elif self.screensaverVolume > -1:
                self._setVolume(self.original_volume)
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), xbmc.LOGERROR)


# Class to store all the schedule details and work out which video should
# be playing at a given time
class Scheduler(object):
    def __init__(self, *args):
        self.scheduleDetails = []
        self.idOffset = 0
        self.lastScheduleModified = 0

        if Settings.getScheduleSetting() == Settings.SCHEDULE_SETTINGS:
            self._loadFromSettings()
        elif Settings.getScheduleSetting() == Settings.SCHEDULE_FILE:
            self._loadFromFile()

    # Get the ID of which schedule should be used
    def getScheduleEntry(self):
        # Get the current time that we are checking the schedule for
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        # Get the current day of the week
        # 0 = Monday 6 = Sunday
        today = localTime.tm_wday
        # Make sure that the day returned is within our expected list
        if today not in Settings.DAY_TYPE:
            log("Schedule: Unknown day today %d, setting to everyday" % today)
            today = Settings.EVERY_DAY

        # Check if we need to refresh the schedule details from the file
        # in case they have changed
        if Settings.getScheduleSetting() == Settings.SCHEDULE_FILE:
            # Check if the file has changed
            scheduleFileName = Settings.getScheduleFile()
            if scheduleFileName not in [None, ""]:
                if xbmcvfs.exists(scheduleFileName):
                    statFile = xbmcvfs.Stat(scheduleFileName)
                    modified = statFile.st_mtime()
                    if modified != self.lastScheduleModified:
                        log("Schedule: Schedule file has changed (%s)" % str(modified))
                        # We use the offset to work out if the data has changed
                        if self.idOffset > 0:
                            self.idOffset = 0
                        else:
                            self.idOffset = 1000
                        # Clear the existing schedule items
                        self.scheduleDetails = []
                        # Load the new schedule items
                        self._loadFromFile()

        # Check the scheduled items to see if any cover the current time
        for item in self.scheduleDetails:
            if (item['start'] <= currentTime) and (item['end'] >= currentTime):
                # Make sure this is for the current day
                if (today == Settings.EVERY_DAY) or (item['day'] in [Settings.EVERY_DAY, today]):
                    return item['id']
            # Check for the case where the time laps over midnight
            if item['start'] > item['end']:
                if (currentTime >= item['start']) or (currentTime <= item['end']):
                    # Check to see if we are restricting to day
                    if (today == Settings.EVERY_DAY) or (item['day'] == Settings.EVERY_DAY):
                        return item['id']
                    else:
                        if (currentTime >= item['start']) and (item['day'] in [Settings.EVERY_DAY, today]):
                            return item['id']
                        else:
                            # The day is set for the start of the time interval
                            # so if we go over to the next day we need to update
                            # what the expected day is
                            nextDay = Settings.getNextDay(item['day'])
                            if (currentTime <= item['end']) and (item['day'] in [Settings.EVERY_DAY, nextDay]):
                                return item['id']
        return -1

    # Get the video for a given Id
    def getScheduleVideo(self, id):
        videoFile = None
        # Find the entry matching this Id
        for item in self.scheduleDetails:
            if item['id'] == id:
                videoFile = item['video']
                break
        return videoFile

    # Get the overlay image for a given Id
    def getScheduleOverlay(self, id):
        imageFile = None
        # Find the entry matching this Id
        for item in self.scheduleDetails:
            if item['id'] == id:
                if item['overlay'] not in [None, ""]:
                    imageFile = item['overlay']
                break
        return imageFile

    def _loadFromSettings(self):
        # Collect together all of the scheduled videos
        numScheduleEntries = Settings.getNumberOfScheduleRules()
        log("Schedule: Number of schedule entries is %d" % numScheduleEntries)
        itemNum = self.idOffset + 1
        while itemNum <= numScheduleEntries:
            videoFile = Settings.getRuleVideoFile(itemNum)
            if videoFile not in [None, ""]:
                # Support special paths like smb:// means that we can not just call
                # os.path.isfile as it will return false even if it is a file
                # (A bit of a shame - but that's the way it is)
                if videoFile.startswith("smb://") or os_path_isfile(videoFile):
                    overlayFile = Settings.getRuleOverlayFile(itemNum)
                    startTime = Settings.getRuleStartTime(itemNum)
                    endTime = Settings.getRuleEndTime(itemNum)
                    day = Settings.getRuleDay(itemNum)
                    log("Schedule: Item %d (Start:%d, End:%d, Day: %d) contains video %s" % (itemNum, startTime, endTime, day, videoFile))
                    details = {'id': itemNum, 'start': startTime, 'end': endTime, 'day': day, 'video': videoFile, 'overlay': overlayFile}
                    self.scheduleDetails.append(details)
                else:
                    log("Schedule: File does not exist: %s" % videoFile)
            else:
                log("Schedule: Video file not set for entry %d" % itemNum)
            itemNum = itemNum + 1

    def _loadFromFile(self):
        # Get the videos schedule that is stored in the file
        scheduleFileName = Settings.getScheduleFile()
        if scheduleFileName in [None, ""]:
            log("Schedule: No schedule file set")
            return

        log("Schedule: Searching for schedule file: %s" % scheduleFileName)

        # Return False if file does not exist
        if not xbmcvfs.exists(scheduleFileName):
            log("Schedule: No schedule file found: %s" % scheduleFileName)
            return

        # Save off the time this file was modified
        statFile = xbmcvfs.Stat(scheduleFileName)
        self.lastScheduleModified = statFile.st_mtime()
        log("Schedule: Reading in schedule file with modify time: %s" % str(self.lastScheduleModified))

        # The file exists, so start loading it
        try:
            # Need to first load the contents of the file into
            # a string, this is because the XML File Parse option will
            # not handle formats like smb://
            scheduleFile = xbmcvfs.File(scheduleFileName, 'r')
            scheduleFileStr = scheduleFile.read()
            scheduleFile.close()

            # Create an XML parser
            scheduleXml = ET.ElementTree(ET.fromstring(scheduleFileStr))
            rootElement = scheduleXml.getroot()

            log("Schedule: Root element is = %s" % rootElement.tag)

            # Check which format if being used
            if rootElement.tag == "schedule":
                log("Schedule: Schedule format file detected")
                #    <schedule>
                #        <rule start="14:24" end="14:37" video="video3.mkv" overlay="WindowFrame1.png" />
                #    </schedule>

                # Get the directory that the schedule file is in as this might be needed
                # if we have local paths in the XML file
                directory = os_path_split(scheduleFileName)[0]

                # There could be multiple rule entries, so loop through all of them
                itemNum = self.idOffset + 1
                for ruleElem in scheduleXml.findall('rule'):
                    if ruleElem is not None:
                        videoFile = ruleElem.get('video', None)
                        overlayFile = ruleElem.get('overlay', None)
                        startTime = self._convertTimeToMinutes(ruleElem.get('start', "00:00"))
                        endTime = self._convertTimeToMinutes(ruleElem.get('end', "00:00"))
                        day = self._convertDayFormat(ruleElem.get('day', None))

                    if (videoFile not in [None, ""]) and (startTime not in [None, ""]) and (endTime not in [None, ""]):
                        # Make it a full path if it is not already
                        if videoFile.startswith('..') or (("/" not in videoFile) and ("\\" not in videoFile)):
                            videoFile = os_path_join(directory, videoFile)
                        if overlayFile not in [None, ""]:
                            if overlayFile.startswith('..') or (("/" not in overlayFile) and ("\\" not in overlayFile)):
                                overlayFile = os_path_join(directory, overlayFile)
                        log("Schedule File: Item %d (Start:%d, End:%d) contains video %s" % (itemNum, startTime, endTime, videoFile))

                        # Support special paths like smb:// means that we can not just call
                        # os.path.isfile as it will return false even if it is a file
                        # (A bit of a shame - but that's the way it is)
                        if videoFile.startswith("smb://") or os_path_isfile(videoFile):
                            details = {'id': itemNum, 'start': startTime, 'end': endTime, 'day': day, 'video': videoFile, 'overlay': overlayFile}
                            self.scheduleDetails.append(details)
                        else:
                            log("Schedule: File does not exist: %s" % videoFile)

                        itemNum = itemNum + 1
            else:
                log("Schedule: Unknown schedule file format")

            del scheduleXml
        except:
            log("Schedule: Failed to process schedule file: %s" % scheduleFileName, xbmc.LOGERROR)
            log("Schedule: %s" % traceback.format_exc(), xbmc.LOGERROR)

    # Converts the string format time (e.g. 14:10) to minutes
    def _convertTimeToMinutes(self, strTime):
        if strTime in [None, ""]:
            log("Schedule: Time not set")
            return None
        strTimeSplit = strTime.split(':')
        if len(strTimeSplit) < 2:
            log("Schedule: Incorrect time format: %s" % strTime)
            return None
        return (int(strTimeSplit[0]) * 60) + int(strTimeSplit[1])

    def _convertDayFormat(self, dayStr):
        if dayStr in [None, ""]:
            log("Schedule: Day not set")
            return Settings.EVERY_DAY
        day = Settings.EVERY_DAY
        if dayStr.lower() == "monday":
            day = Settings.MONDAY
        elif dayStr.lower() == "tuesday":
            day = Settings.TUESDAY
        elif dayStr.lower() == "wednesday":
            day = Settings.WEDNESDAY
        elif dayStr.lower() == "thursday":
            day = Settings.THURSDAY
        elif dayStr.lower() == "friday":
            day = Settings.FRIDAY
        elif dayStr.lower() == "saturday":
            day = Settings.SATURDAY
        elif dayStr.lower() == "sunday":
            day = Settings.SUNDAY
        return day


##################################
# Main of the Video Screensaver
##################################
if __name__ == '__main__':
    # Check for the case where the screensaver has been launched as a script
    # But needs to behave like the full screensaver, not just a video player
    # This is the case for things like screensaver.random
    if (len(sys.argv) > 1) and ("screensaver" in sys.argv[1]):
        # Launch the core screensaver script - this will ensure all the pre-checks
        # are done (like TvTunes) before running the screensaver
        log("Screensaver started by script with screensaver argument")
        xbmc.executebuiltin('RunScript(%s)' % (os.path.join(CWD, "default.py")))
    else:
        # Before we start, make sure that the settings have been updated correctly
        Settings.cleanAddonSettings()

        screenWindow = ScreensaverWindow.createScreensaverWindow()

        xbmcgui.Window(10000).setProperty("VideoScreensaverRunning", "true")

        didScreensaverTimeout = False
        try:
            # Now show the window and block until we exit
            screensaverTimeout = Settings.screensaverTimeout()
            scheduleSetting = Settings.getScheduleSetting()

            if (screensaverTimeout < 1) and (scheduleSetting == Settings.SCHEDULE_OFF):
                log("Starting Screensaver in Modal Mode")
                screenWindow.doModal()
            else:
                log("Starting Screensaver in Show Mode")
                screenWindow.show()

                # The timeout is in minutes, and the sleep is in msec, so convert the
                # countdown into the correct "sleep units" which will be every 0.1 seconds
                checkInterval = 100
                countdown = screensaverTimeout * 60 * (1000 / checkInterval)

                # Now wait until the screensaver is closed
                while not screenWindow.isComplete():
                    xbmc.sleep(checkInterval)
                    if screensaverTimeout > 0:
                        # Update the countdown
                        countdown = countdown - 1
                        if countdown < 1:
                            log("Stopping Screensaver as countdown expired")
                            # Close the screensaver window
                            screenWindow.close()
                            # Reset the countdown to stop multiple closes being sent
                            countdown = 100
                            # Record that the screensaver hit the timeout, this means that
                            # we can then check to see if there is any action to perform
                            # before we completely exit the screensaver script
                            didScreensaverTimeout = True
                            break

                    # Check to see if there is anything that needs to be done
                    # for the screensaver, like change the video on schedule
                    screenWindow.check()
        except:
            log("VideoScreensaver ERROR: %s" % traceback.format_exc(), xbmc.LOGERROR)

        xbmcgui.Window(10000).clearProperty("VideoScreensaverRunning")

        del screenWindow

        # Check if there are any actions to perform after a timeout occurs
        if didScreensaverTimeout:
            if Settings.isShutdownAfterTimeout():
                log("Shutting down system after video screensaver timeout")
                # Using ShutDown will perform the default behaviour that Kodi has in the system settings
                xbmc.executebuiltin("ShutDown")

        log("Leaving Screensaver Script")

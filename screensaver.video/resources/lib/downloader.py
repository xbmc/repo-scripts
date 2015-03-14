# -*- coding: utf-8 -*-
import urllib
import traceback
import base64
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='screensaver.video')
__addonid__ = __addon__.getAddonInfo('id')

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import dir_exists
from settings import list_dir


class Downloader:
    def __init__(self):
        addonRootDir = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8")
        self.tempDir = os_path_join(addonRootDir, 'temp')
        self.videoDir = os_path_join(addonRootDir, 'videos')

        # Set up the addon directories if they do not already exist
        if not dir_exists(addonRootDir):
            xbmcvfs.mkdir(addonRootDir)
        if not dir_exists(self.tempDir):
            xbmcvfs.mkdir(self.tempDir)
        if not dir_exists(self.videoDir):
            xbmcvfs.mkdir(self.videoDir)

    def showSelection(self):
        displayList = self._getDisplayList()

        videoLocation = None
        # Show the list to the user
        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32020), displayList)
        if select == -1:
            log("Downloader: Selection cancelled by user")
            return (None, None)
        elif select == len(displayList) - 1:
            # If it is the last entry in the list, then that means all
            # of the files, so first display an information dialog so
            # the user knows it will only use videos already downloaded
            log("Downloader: Selection is to use all downloaded videos")
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32304), __addon__.getLocalizedString(32305))
            return (-1, self.videoDir)
        else:
            log("Downloader: Selected item %d" % select)
            selectedItem = Settings.PRESET_VIDEOS[select]
            # Download the file selected
            data = base64.b64decode(selectedItem[2])
            videoLocation = self.download(data, selectedItem[1], __addon__.getLocalizedString(selectedItem[0]))

        return (select, videoLocation)

    # Download the video file
    def download(self, fileUrl, filename, displayName):
        log("Download: %s" % fileUrl)
        tmpdestination = os_path_join(self.tempDir, filename)
        destination = os_path_join(self.videoDir, filename)

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            useExisting = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32301), displayName, __addon__.getLocalizedString(32302))
            if useExisting:
                # Don't want to overwrite, so nothing to do
                log("Download: Reusing existing video file %s" % destination)
                return destination
            else:
                log("Download: Removing existing file %s ready for fresh download" % destination)
                xbmcvfs.delete(destination)

        # Create a progress dialog for the  download
        downloadProgressDialog = xbmcgui.DialogProgress()
        downloadProgressDialog.create(__addon__.getLocalizedString(32303), displayName, filename, destination)

        try:
            # Callback method to report progress
            def _report_hook(count, blocksize, totalsize):
                percent = int(float(count * blocksize * 100) / totalsize)
                downloadProgressDialog.update(percent, displayName, filename, destination)

            # Now retrieve the actual file
            fp, h = urllib.urlretrieve(fileUrl, tmpdestination, _report_hook)
            log(h)

            # Check to make sure that the file created downloaded correctly
            st = xbmcvfs.Stat(tmpdestination)
            fileSize = st.st_size()
            log("Download: Size of file %s is %d" % (tmpdestination, fileSize))
            # Check for something that has a size greater than zero (in case some OSs do not
            # support looking at the size), but less that 1,000,000 (As all our files are
            # larger than that
            if (fileSize > 0) and (fileSize < 1000000):
                log("Download: Detected that file %s did not download correctly as file size is only %d" % (fileUrl, fileSize))
                xbmcgui.Dialog().ok(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32306), __addon__.getLocalizedString(32307))
            else:
                log("Download: Copy from %s to %s" % (tmpdestination, destination))
                copy = xbmcvfs.copy(tmpdestination, destination)
                if copy:
                    log("Download: Copy Successful")
                else:
                    log("Download: Copy Failed")
            xbmcvfs.delete(tmpdestination)
        except:
            log("Download: Theme download Failed!!!", xbmc.LOGERROR)
            log("Download: %s" % traceback.format_exc(), xbmc.LOGERROR)

        # Make sure the progress dialog has been closed
        downloadProgressDialog.close()
        return destination

    # Gets the list of names to display, will highlight the videos that have already
    # been downloaded
    def _getDisplayList(self):
        # Check the directory where the default videos are stored to see if
        # there are any videos already stored there
        dirs, files = list_dir(self.videoDir)

        displayList = []
        for videoItem in Settings.PRESET_VIDEOS:
            displayNamePrefix = '   '
            # Check if the file already exists, and has been downloaded already
            if videoItem[1] in files:
                log("Downloader: File %s already exists" % videoItem[1])
                displayNamePrefix = '* '

            displayList.append("%s%s" % (displayNamePrefix, __addon__.getLocalizedString(videoItem[0])))

        # Now add the option to allow the user randomly play the downloaded
        # videos
        displayList.append(__addon__.getLocalizedString(32100))

        return displayList

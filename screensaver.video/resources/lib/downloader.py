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
            return None
        else:
            log("Downloader: Selected item %d" % select)
            selectedItem = Settings.PRESET_VIDEOS[select]
            # Download the file selected
            data = base64.b64decode(selectedItem[2])
            videoLocation = self.download(data, selectedItem[1], selectedItem[0])

        return (select, videoLocation)

    # Download the video file
    def download(self, fileUrl, filename, displayName):
        log("Download: %s" % fileUrl)
        tmpdestination = os_path_join(self.tempDir, filename)
        destination = os_path_join(self.videoDir, filename)

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            overwrite = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32004), __addon__.getLocalizedString(32301), displayName, __addon__.getLocalizedString(32302))
            if overwrite is False:
                xbmcvfs.delete(destination)
            else:
                # Don't want to overwrite, so nothing to do
                log("Download: Reusing existing video file %s" % destination)
                return destination

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
            log("Download: Copy from %s to %s" % (tmpdestination, destination))
            copy = xbmcvfs.copy(tmpdestination, destination)
            if copy:
                log("Download: Copy Successful")
            else:
                log("Download: Copy Failed")
            xbmcvfs.delete(tmpdestination)
        except:
            log("Download: Theme download Failed!!!")
            log("Download: %s" % traceback.format_exc())

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
            displayNamePrefix = ''
            # Check if the file already exists, and has been downloaded already
            if videoItem[1] in files:
                log("Downloader: File %s already exists" % videoItem[1])
                displayNamePrefix = '* '

            displayList.append("%s%s" % (displayNamePrefix, videoItem[0]))

        return displayList

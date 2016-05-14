# -*- coding: utf-8 -*-
import sys
import urllib
import urlparse
import traceback
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon

# Import the common settings
from resources.lib.settings import Settings
from resources.lib.settings import log
from resources.lib.settings import os_path_join
from resources.lib.settings import list_dir
from resources.lib.collectSets import CollectSets

ADDON = xbmcaddon.Addon(id='screensaver.video')
ICON = ADDON.getAddonInfo('icon')
FANART = ADDON.getAddonInfo('fanart')


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # The root menu shows all of the available collections
    def rootMenu(self):
        collectionCtrl = CollectSets()
        collectionMap = collectionCtrl.getCollections()

        log("VideoScreensaverPlugin: Available Number of Collections is %d" % len(collectionMap))

        for collectionKey in sorted(collectionMap.keys()):
            collectionDetail = collectionMap[collectionKey]
            li = xbmcgui.ListItem(collectionKey, iconImage=collectionDetail['image'])
            li.addContextMenuItems(self._getCollectionsContextMenu(collectionDetail), replaceItems=True)
            li.setProperty("Fanart_Image", FANART)
            url = self._build_url({'mode': 'collection', 'name': collectionKey, 'link': collectionDetail['filename']})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        del collectionCtrl

        # Add a button to support adding a custom collection
        li = xbmcgui.ListItem(ADDON.getLocalizedString(32082), iconImage=ICON)
        li.addContextMenuItems([], replaceItems=True)
        li.setProperty("Fanart_Image", FANART)
        url = self._build_url({'mode': 'addcollection'})
        xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Lists all the available videos for a given collection
    def viewCollection(self, name, link):
        log("VideoScreensaverPlugin: %s (%s)" % (name, link))

        collectionCtrl = CollectSets()
        collectionDetails = collectionCtrl.loadCollection(link)
        del collectionCtrl

        # If the file was not processed just don't display anything
        if collectionDetails in [None, ""]:
            return

        screensaverFolder = Settings.getScreensaverFolder()

        for videoItem in collectionDetails['videos']:
            displayName = videoItem['name']
            if videoItem['enabled'] is False:
                displayName = "%s %s" % (ADDON.getLocalizedString(32016), displayName)

            # Create the list-item for this video
            li = xbmcgui.ListItem(displayName, iconImage=videoItem['image'])
            if videoItem['duration'] not in [None, "", 0]:
                li.setInfo('video', {'Duration': videoItem['duration']})

            # Set the background image
#             if videoItem['fanart'] is not None:
#                 li.setProperty("Fanart_Image", videoItem['fanart'])

            # If theme already exists flag it using the play count
            # This will normally put a tick on the GUI
            if screensaverFolder not in [None, ""]:
                if self._getVideoLocation(screensaverFolder, videoItem['filename']) not in [None, ""]:
                    li.setInfo('video', {'PlayCount': 1})

            li.addContextMenuItems(self._getContextMenu(videoItem), replaceItems=True)

            url = self._build_url({'mode': 'download', 'name': videoItem['name'], 'filename': videoItem['filename'], 'primary': videoItem['primary']})

            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Support users relocating videos into sub-directories
    def _getVideoLocation(self, folder, filename):
        log("VideoScreensaverPlugin: Checking if %s already downloaded to %s" % (filename, folder))
        videoLocation = os_path_join(folder, filename)
        if xbmcvfs.exists(videoLocation):
            return videoLocation

        # Check nested directories
        if Settings.isFolderNested():
            dirs, files = list_dir(folder)
            for aDir in dirs:
                fullPath = os_path_join(folder, aDir)
                filePath = self._getVideoLocation(fullPath, filename)
                if filePath not in [None, ""]:
                    return filePath
        return None

    def download(self, name, filename, downloadURL):
        log("VideoScreensaverPlugin: Downloading %s" % name)

        tmpdestination = os_path_join(Settings.getTempFolder(), filename)
        destination = os_path_join(Settings.getScreensaverFolder(), filename)

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            useExisting = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32301), name, ADDON.getLocalizedString(32302))
            if useExisting:
                # Don't want to overwrite, so nothing to do
                log("Download: Reusing existing video file %s" % destination)
                return
            else:
                log("Download: Removing existing file %s ready for fresh download" % destination)
                xbmcvfs.delete(destination)

        # Create a progress dialog for the  download
        downloadProgressDialog = xbmcgui.DialogProgress()
        downloadProgressDialog.create(ADDON.getLocalizedString(32303), name, filename, destination)

        # Callback method to report progress
        def _report_hook(count, blocksize, totalsize):
            percent = int(float(count * blocksize * 100) / totalsize)
            downloadProgressDialog.update(percent, name, filename, destination)
            if downloadProgressDialog.iscanceled():
                log("Download: Operation cancelled")
                raise ValueError('Download Cancelled')

        try:
            log("Download: Using server: %s" % downloadURL)

            # Now retrieve the actual file
            fp, h = urllib.urlretrieve(downloadURL, tmpdestination, _report_hook)
            log(h)

            # Check to make sure that the file created downloaded correctly
            st = xbmcvfs.Stat(tmpdestination)
            fileSize = st.st_size()
            log("Download: Size of file %s is %d" % (tmpdestination, fileSize))
            # Check for something that has a size greater than zero (in case some OSs do not
            # support looking at the size), but less that 1,000,000 (As all our files are
            # larger than that
            if (fileSize > 0) and (fileSize < 1000000):
                log("Download: Detected that file %s did not download correctly as file size is only %d" % (downloadURL, fileSize))
                xbmcgui.Dialog().ok(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32306))
            else:
                log("Download: Copy from %s to %s" % (tmpdestination, destination))
                copy = xbmcvfs.copy(tmpdestination, destination)
                if copy:
                    log("Download: Copy Successful")
                else:
                    log("Download: Copy Failed")
            xbmcvfs.delete(tmpdestination)
        except ValueError:
            # This was a cancel by the user, so remove any file that may be part downloaded
            if xbmcvfs.exists(tmpdestination):
                xbmcvfs.delete(tmpdestination)
        except:
            log("Download: Theme download Failed!!!", xbmc.LOGERROR)
            log("Download: %s" % traceback.format_exc(), xbmc.LOGERROR)

        # Make sure the progress dialog has been closed
        downloadProgressDialog.close()
        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    # Delete an existing file
    def delete(self, name, filename):
        log("VideoScreensaverPlugin: Deleting %s" % name)

        screensaverFolder = Settings.getScreensaverFolder()
        destination = self._getVideoLocation(screensaverFolder, filename)

        # Check to see if there is already a file present
        if destination not in [None, ""]:
            deleteFile = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32014), name)
            if deleteFile:
                log("VideoScreensaverPlugin: Removing existing file %s" % destination)
                xbmcvfs.delete(destination)
                # Now reload the screen to reflect the change
                xbmc.executebuiltin("Container.Refresh")
        else:
            log("VideoScreensaverPlugin: Files does not exists %s" % destination)

    def play(self, name, filename):
        log("VideoScreensaverPlugin: Playing %s" % name)

        destination = filename
        if not filename.startswith('http'):
            screensaverFolder = Settings.getScreensaverFolder()
            destination = self._getVideoLocation(screensaverFolder, filename)

        # Check to see if there is already a file present
        if destination not in [None, ""]:
            player = xbmc.Player()
            player.play(destination)
            del player
        else:
            log("VideoScreensaverPlugin: Files does not exists %s" % destination)

    def enable(self, filename, disable):
        log("VideoScreensaverPlugin: Enable toggle %s" % filename)

        # Get the current list of disabled items
        collectionCtrl = CollectSets()
        disabledVideos = collectionCtrl.getDisabledVideos()

        # Check if we are adding or removing from the list
        if disable == 'false':
            if filename in disabledVideos:
                log("VideoScreensaverPlugin: Removing %s from the disabled videos" % filename)
                disabledVideos.remove(filename)
        else:
            if filename not in disabledVideos:
                log("VideoScreensaverPlugin: Adding %s to the disabled videos" % filename)
                disabledVideos.append(filename)

        collectionCtrl.saveDisabledVideos(disabledVideos)
        del collectionCtrl

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    # Adds a custom collection to the list of sets
    def addCollection(self):
        # Prompt the user to select the file
        customXml = xbmcgui.Dialog().browse(1, ADDON.getLocalizedString(32082), 'files', '.xml')

        if not customXml:
            return

        # If file selected then check it is OK
        collectionCtrl = CollectSets()
        isCollectionValid = collectionCtrl.addCustomCollection(customXml)
        del collectionCtrl

        if isCollectionValid:
            log("VideoScreensaverPlugin: collection added: %s" % customXml)
        else:
            log("VideoScreensaverPlugin: Failed to add collection: %s" % customXml)
            xbmcgui.Dialog().notification(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32083), ICON, 5000, False)

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    # Adds a custom collection to the list of sets
    def removeCollection(self, name, link):
        if name in [None, ""]:
            return

        collectionCtrl = CollectSets()
        collectionDetails = collectionCtrl.loadCollection(link)

        filesToDelete = []
        # If the file was not processed just don't display anything
        if collectionDetails not in [None, ""]:
            screensaverFolder = Settings.getScreensaverFolder()

            for videoItem in collectionDetails['videos']:
                # If theme exists we need to check if we want to delete it
                if screensaverFolder not in [None, ""]:
                    videoLocation = os_path_join(screensaverFolder, videoItem['filename'])

                    log("VideoScreensaverPlugin: Checking if %s already downloaded to %s" % (videoItem['filename'], videoLocation))
                    if xbmcvfs.exists(videoLocation):
                        filesToDelete.append(videoLocation)

        # If there are possible files to delete, then prompt the user to see if we should
        if len(filesToDelete) > 0:
            needDelete = xbmcgui.Dialog().yesno(ADDON.getLocalizedString(32005), ADDON.getLocalizedString(32086))

            if needDelete:
                for vidFile in filesToDelete:
                    xbmcvfs.delete(vidFile)

        # Now remove the actual collection
        collectionCtrl.removeCustomCollection(name)
        del collectionCtrl

        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    # Construct the context menu
    def _getContextMenu(self, videoItem):
        ctxtMenu = []

        # Check if the file has already been downloaded
        if self._getVideoLocation(Settings.getScreensaverFolder(), videoItem['filename']) in [None, ""]:
            # If not already exists, add a download option
            cmd = self._build_url({'mode': 'download', 'name': videoItem['name'], 'filename': videoItem['filename'], 'primary': videoItem['primary']})
            ctxtMenu.append((ADDON.getLocalizedString(32013), 'RunPlugin(%s)' % cmd))
            # If not already exists, add a download option
            cmd = self._build_url({'mode': 'play', 'name': videoItem['name'], 'filename': videoItem['primary']})
            ctxtMenu.append((ADDON.getLocalizedString(32019), 'RunPlugin(%s)' % cmd))
        else:
            # If already exists then add a play option
            cmd = self._build_url({'mode': 'play', 'name': videoItem['name'], 'filename': videoItem['filename']})
            ctxtMenu.append((ADDON.getLocalizedString(32015), 'RunPlugin(%s)' % cmd))
            # If already exists then add a delete option
            cmd = self._build_url({'mode': 'delete', 'name': videoItem['name'], 'filename': videoItem['filename']})
            ctxtMenu.append((ADDON.getLocalizedString(32014), 'RunPlugin(%s)' % cmd))

            # Check if we need a menu item to enable and disable the videos
            if videoItem['enabled']:
                cmd = self._build_url({'mode': 'enable', 'disable': 'true', 'filename': videoItem['filename']})
                ctxtMenu.append((ADDON.getLocalizedString(32017), 'RunPlugin(%s)' % cmd))
            else:
                cmd = self._build_url({'mode': 'enable', 'disable': 'false', 'filename': videoItem['filename']})
                ctxtMenu.append((ADDON.getLocalizedString(32018), 'RunPlugin(%s)' % cmd))

        return ctxtMenu

    # Construct the context menu for collections
    def _getCollectionsContextMenu(self, collectSet):
        ctxtMenu = []

        # Add the menu item for the custom collections
        if collectSet['default'] is not True:
            # If not already exists, add a download option
            cmd = self._build_url({'mode': 'removecollection', 'name': collectSet['name'], 'link': collectSet['filename']})
            ctxtMenu.append((ADDON.getLocalizedString(32085), 'RunPlugin(%s)' % cmd))

        return ctxtMenu


######################################
# Main of the VideoScreensaver Plugin
######################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("VideoScreensaverPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("VideoScreensaverPlugin: Mode is NONE - showing collection list")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.rootMenu()
        del menuNav

    elif mode[0] == 'collection':
        log("VideoScreensaverPlugin: Mode is collection")

        name = ''
        link = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        linkItem = args.get('link', None)
        if (linkItem is not None) and (len(linkItem) > 0):
            link = linkItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.viewCollection(name, link)
        del menuNav

    elif mode[0] == 'download':
        log("VideoScreensaverPlugin: Mode is download")

        name = ''
        filename = None
        primary = None
        secondary = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        primaryItem = args.get('primary', None)
        if (primaryItem is not None) and (len(primaryItem) > 0):
            primary = primaryItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.download(name, filename, primary)
        del menuNav

    elif mode[0] == 'delete':
        log("VideoScreensaverPlugin: Mode is delete")

        name = ''
        filename = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.delete(name, filename)
        del menuNav

    elif mode[0] == 'play':
        log("VideoScreensaverPlugin: Mode is play")

        name = ''
        filename = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.play(name, filename)
        del menuNav

    elif mode[0] == 'enable':
        log("VideoScreensaverPlugin: Mode is enable")

        filename = None
        disable = 'false'

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        disableItem = args.get('disable', None)
        if (disableItem is not None) and (len(disableItem) > 0):
            disable = disableItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.enable(filename, disable)
        del menuNav

    elif mode[0] == 'addcollection':
        log("VideoScreensaverPlugin: Mode is addcollection")

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.addCollection()
        del menuNav

    elif mode[0] == 'removecollection':
        log("VideoScreensaverPlugin: Mode is removecollection")

        name = ''
        link = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        linkItem = args.get('link', None)
        if (linkItem is not None) and (len(linkItem) > 0):
            link = linkItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.removeCollection(name, link)
        del menuNav

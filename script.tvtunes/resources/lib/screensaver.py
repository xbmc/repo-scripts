# -*- coding: utf-8 -*-
import random
import sys
import os
import traceback
import threading
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json


__addon__ = xbmcaddon.Addon(id='script.tvtunes')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__media__ = xbmc.translatePath(os.path.join(__resource__, 'media').encode("utf-8")).decode("utf-8")


from settings import ScreensaverSettings
from settings import Settings
from settings import log
from settings import list_dir
from settings import dir_exists
from settings import os_path_join
from settings import os_path_split

from themeFinder import ThemeFiles


# Helper method to allow the cycling through a list of values
def _cycle(iterable):
    saved = []
    for element in iterable:
        yield element
        saved.append(element)
    while saved:
        for element in saved:
            yield element


# Class used to create the correct type of screensaver class
class ScreensaverManager(object):
    # Creates the correct type of Screensaver class
    def __new__(cls):
        mode = ScreensaverSettings.getMode()
        if mode == 'Random':
            # Just choose one of the options at random from everything that
            # extends the base screensaver
            subcls = random.choice(ScreensaverBase.__subclasses__())
            return subcls()
        # Find out which screensaver format is selected
        for subcls in ScreensaverBase.__subclasses__():
            if subcls.MODE == mode:
                return subcls()
        raise ValueError('Not a valid ScreensaverBase subclass: %s' % mode)


# Monitor class to handle events like the screensaver deactivating
class ExitMonitor(xbmc.Monitor):
    # Create the monitor passing in the method to call when we want to exit
    # and stop the screensaver
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

    # Called when the screensaver should be stopped
    def onScreensaverDeactivated(self):
        # Make the callback to stop the screensaver
        self.exit_callback()


# The Dialog used to display the screensaver in
class ScreensaverWindow(xbmcgui.WindowDialog):
    # Create the Dialog, giving the method to call when it is exited
    def __init__(self, exit_callback):
        self.exit_callback = exit_callback

    # Handle the action to exit the screensaver
    def onAction(self, action):
        action_id = action.getId()
        if action_id in [9, 10, 13, 92]:
            self.exit_callback()


# Class to hold all of the media files used that are stored in the addon
class MediaFiles(object):
    LOADING_IMAGE = os.path.join(__media__, 'loading.gif')
    BLACK_IMAGE = os.path.join(__media__, 'black.jpg')
    STARS_IMAGE = os.path.join(__media__, 'stars.jpg')
    TABLE_IMAGE = os.path.join(__media__, 'table.jpg')


class VolumeDrop(object):
    def __init__(self, *args):
        self.reduceVolume = Settings.getDownVolume()
        if self.reduceVolume != 0:
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
        xbmc.executebuiltin('XBMC.SetVolume(%d)' % newvolume, True)

    def lowerVolume(self):
        try:
            if self.reduceVolume != 0:
                vol = self.original_volume - self.reduceVolume
                # Make sure the volume still has a value
                if vol < 1:
                    vol = 1
                log("Player: volume goal: %d%%" % vol)
                self._setVolume(vol)
            else:
                log("Player: No reduced volume option set")
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), True, xbmc.LOGERROR)

    def restoreVolume(self):
        try:
            if self.reduceVolume != 0:
                self._setVolume(self.original_volume)
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), True, xbmc.LOGERROR)


# Class to collect all the extra images provided by Artwork Downloader
class ArtworkDownloaderSupport(object):
    def loadExtraFanart(self, path):
        # Make sure a valid path is given
        if (path is None) or (path == ""):
            return []

        # Check if the user actually wants to include the extra artwork
        if not ScreensaverSettings.includeArtworkDownloader():
            return []

        log("ArtworkDownloaderSupport: Loading extra images for: %s" % path)

        # Start by calculating the location of the extra fanart
        extrafanartdir = self._media_path(path)

        extraFanartFiles = []

        # Now read the contents of the directory
        if dir_exists(extrafanartdir):
            dirs, files = list_dir(extrafanartdir)
            for aFile in files:
                artFile = os_path_join(extrafanartdir, aFile)
                log("ArtworkDownloaderSupport: Found file: %s" % artFile)
                # Add the file to the list
                extraFanartFiles.append(artFile)

        return extraFanartFiles

    # Gets the path that is the root of the given media
    def _media_path(self, path):
        baseDirectory = path
        # handle episodes stored as rar files
        if baseDirectory.startswith("rar://"):
            baseDirectory = baseDirectory.replace("rar://", "")
        # Check for stacked movies
        elif baseDirectory.startswith("stack://"):
            baseDirectory = baseDirectory.split(" , ")[0]
            baseDirectory = baseDirectory.replace("stack://", "")

        if Settings.isSmbEnabled() and not ('@' in baseDirectory):
            if baseDirectory.startswith("smb://"):
                log("ArtworkDownloaderSupport: Try authentication share")
                baseDirectory = baseDirectory.replace("smb://", "smb://%s:%s@" % (Settings.getSmbUser(), Settings.getSmbPassword()))
            # Also handle the apple format
            elif baseDirectory.startswith("afp://"):
                log("ArtworkDownloaderSupport: Try authentication share")
                baseDirectory = baseDirectory.replace("afp://", "afp://%s:%s@" % (Settings.getSmbUser(), Settings.getSmbPassword()))

        # Support special paths like smb:// means that we can not just call
        # os.path.isfile as it will return false even if it is a file
        # (A bit of a shame - but that's the way it is)
        fileExt = os.path.splitext(baseDirectory)[1]
        # If this is a file, then get it's parent directory
        if fileExt is not None and fileExt != "":
            baseDirectory = (os_path_split(baseDirectory))[0]

        baseDirectory = os_path_join(baseDirectory, 'extrafanart')
        log("ArtworkDownloaderSupport: Searching directory: %s" % baseDirectory)
        return baseDirectory


# Class to hold groups of images and media
class MediaGroup(object):
    def __init__(self, videoPath="", imageArray=[]):
        self.isPlayingTheme = False
        self.path = videoPath
        # If the user does not want to play themes, just have an empty set of themes
        # have this as the default, as we will load the theme later
        self.themeFiles = ThemeFiles("")

        self.images = []
        # If images were supplied, then add them to the list
        for img in imageArray:
            self.addImage(img, 16.0 / 9.0)

        self.dataLoaded = False
        self.imageRepeat = False

        # Not currently showing any images
        self.currentImageIdx = -1
        # Record the number of images that are shown while the theme is playing
        self.approxImagesPerTheme = -1
        self.themePlayed = False

        self.loadLock = threading.Lock()

    # Check if this media group should be excluded
    def shouldExclude(self):
        if (self.path is None) or (self.path == ""):
            return False
        shouldSkip = self.themeFiles.shouldExcludeFromScreensaver(self.path)
        if shouldSkip:
            log("MediaGroup: Skipping %s" % self.path)
        return shouldSkip

    # Add an image to the group, giving it's aspect radio
    def addImage(self, imageURL, aspectRatio):
        try:
            # Handle non ascii characters
            safeImageURL = imageURL.encode('utf-8')
        except:
            safeImageURL = imageURL
        imageDetails = {'file': safeImageURL, 'aspect_ratio': aspectRatio}
        self.images.append(imageDetails)

    # Gets the number of images in the group
    def imageCount(self, forceLoad=False):
        if forceLoad:
            self.loadData()
        return len(self.images)

    # Called when we need to load all the data that may take a little time
    # this can even have to wait for NAS drives etc to spin up, so it has
    # been done under a different method so that it can be launched in a
    # different thread if needed
    def loadData(self):
        # Get the lock so that only one instance is updated at a time
        self.loadLock.acquire()
        try:
            # We could be called multiple times, so make sure we only do it once
            if not self.dataLoaded:
                # Record the fact we have already started loading, we do not
                # want multiple threads loading the data at the same time
                self.dataLoaded = True

                log("MediaGroup: Loading data for %s" % self.path)

                # Check if the user wants to play themes
                if ScreensaverSettings.isPlayThemes():
                    self.themeFiles = ThemeFiles(self.path)
                    # Check if we only want groups with themes in
                    if ScreensaverSettings.isOnlyIfThemes():
                        if not self.themeFiles.hasThemes():
                            # Clear all images, that will ensure we skip this one
                            log("MediaGroup: Clearing image list for %s" % self.path)
                            self.images = []
                            return

                # Now add the Extra FanArt folders
                artDownloader = ArtworkDownloaderSupport()
                for artImg in artDownloader.loadExtraFanart(self.path):
                    self.addImage(artImg, 16.0 / 9.0)

                # Now that we have all of the images, mix them up
                random.shuffle(self.images)
        finally:
            self.loadLock.release()

    # Start playing a theme if there is one to play
    # The fastImageCount records the number of images that were loaded
    # quickly without the normal wait time
    def startTheme(self, fastImageCount=0):
        if self.themeFiles.hasThemes() and not xbmc.Player().isPlayingAudio():
            # There are cases where the theme is quite short and we have not
            # shown all the images left, so should repeat the theme, so we first
            # check to see how many images are getting shown
            if self.themePlayed and (self.approxImagesPerTheme < 0):
                # This is the first time the theme has completed, work out
                # how many images were shown in that time
                self.approxImagesPerTheme = (self.currentImageIdx - fastImageCount) + 1

            # Don't start the theme if we have already shown all the images
            if not self.imageRepeat:
                # So we have not shown all the images yet, work out if we have time to
                # play the theme again
                startPlayingTheme = not self.themePlayed
                if (not startPlayingTheme) and ScreensaverSettings.isRepeatTheme():
                    if self.imageCount() - (self.currentImageIdx + 1) > self.approxImagesPerTheme:
                        startPlayingTheme = True
                if startPlayingTheme:
                    self.isPlayingTheme = True
                    self.themePlayed = True
                    xbmc.Player().play(self.themeFiles.getThemePlaylist())

    # Check if the theme has completed playing
    def completedGroup(self):
        # The group is never complete while there is a theme still playing
        # We can't stop the theme, as sending the stop signal to the player
        # will stop the screensaver running
        if self.themeFiles.hasThemes():
            if xbmc.Player().isPlayingAudio():
                return False
            self.isPlayingTheme = False

            # Check to see if we have completed playing a theme and we are supposed
            # to stop after one theme
            if self.themePlayed and ScreensaverSettings.isSkipAfterThemeOnce():
                return True

        # Not playing a theme, so return if we have already shown all the images
        return self.imageRepeat

    # Stop the theme playing if it is currently playing
    # NOTE: If you stop a theme that is playing, then it will also
    # exit out of the screensaver
    def stopTheme(self):
        if self.isPlayingTheme:
            self.isPlayingTheme = False
            self.themePlayed = True
            if xbmc.Player().isPlayingAudio():
                xbmc.Player().stop()

    # Gets the next image details
    def getNextImage(self):
        # Make sure that the required data has been loaded,
        # if not, do it now, this will skip it if already done
        self.loadData()

        # Make sure that we have some images to show
        if self.imageCount() < 1:
            log("MediaGroup: No Images for %s" % self.path)
            return None

        # Move onto the next image
        self.currentImageIdx = self.currentImageIdx + 1

        if self.currentImageIdx > self.imageCount() - 1:
            # We have finished showing the images at least once each
            # so flag that we have looped and reset to the start
            self.imageRepeat = True
            self.currentImageIdx = 0
            # If we are resetting the images to the start, then we have looped.
            # Check if we art still playing the theme for the first time and
            # if so, record that it is longer than the time to show all the images
            if self.approxImagesPerTheme < 0:
                # Just make it large than all the images, doesn't matter how much more
                self.approxImagesPerTheme = self.imageCount() + 100

        return self.images[self.currentImageIdx]


# Class to handle gathering all of the data for a given video in the background
class BackgroundUpdater(object):
    def __init__(self, imageGroupList):
        self.imageGroups = imageGroupList
        self.stop = False
        self.stopping = False

    def startProcessing(self):
        # Create a thread to gather all the data in the background
        self.athread = threading.Thread(target=self.loadExtraData)
        self.athread.setDaemon(True)
        self.athread.start()
        log("BackgroundUpdater: Thread started")

    def stopProcessing(self):
        log("BackgroundUpdater: stopping")
        if not self.stopping:
            self.stopping = True
            self.stop = True

            if self.athread.is_alive():
                # Make sure the thread is dead at this point
                try:
                    self.athread.join(3)
                except:
                    log("BackgroundUpdater: Thread join error: %s" % traceback.format_exc(), True, xbmc.LOGERROR)

    def loadExtraData(self):
        log("BackgroundUpdater: Loading data")
        # For every Image Group, tell it to gather all the other data it needs
        # this will include themes and additional image files
        for img in self.imageGroups:
            if self.stop:
                break
            img.loadData()


# Base Screensaver class that handles all of the operations for a screensaver
class ScreensaverBase(object):
    MODE = None

    def __init__(self):
        log('Screensaver: __init__ start')
        self.exit_requested = False

        # Set up all the required controls for the window
        self.loading_control = xbmcgui.ControlImage(576, 296, 128, 128, MediaFiles.LOADING_IMAGE)
        self.background_control = xbmcgui.ControlImage(0, 0, 1280, 720, '', colorDiffuse=ScreensaverSettings.getDimValue())
        self.preload_control = xbmcgui.ControlImage(-1, -1, 1, 1, '')
        self.global_controls = [self.preload_control, self.background_control, self.loading_control]

        self.image_count = 0
        self.image_controls = []
        self.exit_monitor = ExitMonitor(self.stop)
        self.xbmc_window = ScreensaverWindow(self.stop)
        self.xbmc_window.show()

        # Add all the controls to the window
        self.xbmc_window.addControls(self.global_controls)

        self._init_cycle_controls()
        self.stack_cycle_controls()

        self.backgroundUpdate = None
        log('Screensaver: __init__ end')

    def _init_cycle_controls(self):
        log('Screensaver: init_cycle_controls start')
        dimSetting = ScreensaverSettings.getDimValue()
        for i in xrange(self.getImageControlCount()):
            img_control = xbmcgui.ControlImage(0, 0, 0, 0, '', aspectRatio=1, colorDiffuse=dimSetting)
            self.image_controls.append(img_control)

    def stack_cycle_controls(self):
        log('Screensaver: stack_cycle_controls')
        # add controls to the window in same order as image_controls list
        # so any new image will be in front of all previous images
        self.xbmc_window.addControls(self.image_controls)

    def start_loop(self):
        log('Screensaver: start_loop start')
        imageGroups = self._getImageGroups()

        # Check to see if we failed to find any images
        if (imageGroups is None) or (not imageGroups) or self.exit_requested:
            # A notification has already been shown
            return

        # We have a lot of groups (Each different Movie or TV Show) so
        # mix them all up so they are not always in the same order
        random.shuffle(imageGroups)

        log("Screensaver: Image group total = %d" % len(imageGroups))

        # Before we start processing the groups, find the first item with
        # images and remove the other ones
        for index, imgGrp in enumerate(imageGroups):
            # If we are required to exit while loading images, then stop loading them
            if self.exit_requested:
                return
            if imgGrp.imageCount(True) > 0:
                # Found an image so stop loading, only need to get all the images
                # for the first entry
                # However we know that we do not want any of the items before
                # this group, so we need to delete the groups before this one
                for idx in range(index):
                    del imageGroups[0]
                break

        log("Screensaver: Image groups being used = %d" % len(imageGroups))

        # Make sure there are still image groups to process
        if len(imageGroups) < 1:
            log("Screensaver: No image groups with images in")
            return

        # We are at the point of starting the screensaver we should decrease the volume
        # this point if needed
        volumeCtrl = VolumeDrop()
        volumeCtrl.lowerVolume()

        imageGroup_cycle = _cycle(imageGroups)
        image_controls_cycle = _cycle(self.image_controls)
        self._hide_loading_indicator()
        imageGroup = imageGroup_cycle.next()

        # Force the data to load for the first entry (Need that immediately)
        imageDetails = imageGroup.getNextImage()

        # For the rest we want to start the update in a different thread
        self.backgroundUpdate = BackgroundUpdater(imageGroups)
        self.backgroundUpdate.startProcessing()

        while not self.exit_requested:
            log('Screensaver: Using image: %s' % repr(imageDetails['file']))

            # Start playing theme if there is one
            imageGroup.startTheme(self.getFastImageCount())
            # Get the next control and set it displaying the image
            image_control = image_controls_cycle.next()
            self.process_image(image_control, imageDetails)
            # Now that we are showing the last image, load up the next one
            imageDetails = imageGroup.getNextImage()

            # At this point we have moved the image onto the next one
            # so check if we have gone in a complete loop and there is
            # another group of images to pre-load

            # Wait for the theme to complete playing at least once, if it has not
            # completed playing the theme at least once, then we can safely repeat
            # the images we show
            if (len(imageGroups) > 1) and imageGroup.completedGroup():
                # Move onto the next group, and the first image in that group
                imageGroup = imageGroup_cycle.next()
                # If there are no images in this group, skip to the next (We know there
                # is at least one group with images as we have already checked that before the loop)
                while imageGroup.imageCount(True) < 1:
                    imageGroup = imageGroup_cycle.next()
                # Get the next image from the new group
                imageDetails = imageGroup.getNextImage()

            if self.image_count < self.getFastImageCount():
                self.image_count += 1
            else:
                # Pre-load the next image that is going to be shown
                self._preload_image(imageDetails['file'])
                # Wait before showing the next image
                self.wait()

        # Make sure we are not still gathering images
        if self.backgroundUpdate is not None:
            self.backgroundUpdate.stopProcessing()
            self.backgroundUpdate = None

        # Make sure we stop any outstanding playing theme
        imageGroup.stopTheme()

        # Now restore the volume to what it should be
        volumeCtrl.restoreVolume()

        log('Screensaver: start_loop end')

    # Gets the set of images that are going to be used
    def _getImageGroups(self):
        log('Screensaver: getImageGroups')
        source = ScreensaverSettings.getSource()
        imageTypes = ScreensaverSettings.getImageTypes()

        imageGroups = []
        if ('movies' in source) and not self.exit_requested:
            imgGrp = self._getJsonImageGroups('VideoLibrary.GetMovies', 'movies', imageTypes)
            imageGroups.extend(imgGrp)
        if ('tvshows' in source) and not self.exit_requested:
            imgGrp = self._getJsonImageGroups('VideoLibrary.GetTVShows', 'tvshows', imageTypes)
            imageGroups.extend(imgGrp)
        if ('image_folder' in source) and not self.exit_requested:
            path = ScreensaverSettings.getImagePath()
            if path:
                imgGrp = self._getFolderImages(path)
                imageGroups.extend(imgGrp)
        if not imageGroups and not self.exit_requested:
            cmd = 'XBMC.Notification("{0}", "{1}")'.format(__addon__.getLocalizedString(32101).encode('utf-8'), __addon__.getLocalizedString(32995).encode('utf-8'))
            xbmc.executebuiltin(cmd)
        return imageGroups

    # Makes a JSON call to get the images for a given category
    def _getJsonImageGroups(self, method, key, imageTypes):
        log("Screensaver: getJsonImages for %s" % key)
        jsonProps = list(imageTypes)
        # The file is actually the path for a TV Show, the video file for movies
        jsonProps.append('file')
        query = {'jsonrpc': '2.0', 'id': 0, 'method': method, 'params': {'properties': jsonProps}}
        response = json.loads(xbmc.executeJSONRPC(json.dumps(query)))

        mediaGroups = []
        if ('result' in response) and (key in response['result']):
            for item in response['result'][key]:
                # Check to see if we can get the path or file for the video
                if ('file' in item) and not self.exit_requested:
                    mediaGroup = MediaGroup(item['file'])

                    # Check if we want to include this media group
                    if not mediaGroup.shouldExclude():
                        # Now get all the image information
                        for prop in imageTypes:
                            if prop in item:
                                # If we are dealing with fanart or thumbnail, then we can just store this value
                                if prop in ['fanart']:
                                    # Set the aspect radio based on the type of image being shown
                                    mediaGroup.addImage(item[prop], 16.0 / 9.0)
                                elif prop in ['thumbnail']:
                                    mediaGroup.addImage(item[prop], 2.0 / 3.0)
                                elif prop in ['cast']:
                                    # If this cast member has an image, add it to the array
                                    for castItem in item['cast']:
                                        if 'thumbnail' in castItem:
                                            mediaGroup.addImage(castItem['thumbnail'], 2.0 / 3.0)
                        # Don't return an empty image list if there are no images
                        if mediaGroup.imageCount() > 0:
                            mediaGroups.append(mediaGroup)
                else:
                    log("Screensaver: No file specified when searching")
        log("Screensaver: Found %d image sets for %s" % (len(mediaGroups), key))
        return mediaGroups

    # Creates a group containing all the images in a given directory
    def _getFolderImages(self, path):
        log('Screensaver: getFolderImages for path: %s' % repr(path))
        dirs, files = xbmcvfs.listdir(path)
        images = [xbmc.validatePath(path + f) for f in files
                  if f.lower()[-3:] in ('jpg', 'png')]
        if ScreensaverSettings.isRecursive() and not self.exit_requested:
            for directory in dirs:
                if directory.startswith('.'):
                    continue
                images.extend(self._getFolderImages(xbmc.validatePath('/'.join((path, directory, '')))))
        log("Screensaver: Found %d images for %s" % (len(images), path))
        mediaGroup = MediaGroup(imageArray=images)
        return [mediaGroup]

    def _hide_loading_indicator(self):
        self.loading_control.setAnimations([('conditional', 'effect=fade start=100 end=0 time=500 condition=true')])
        self.background_control.setAnimations([('conditional', 'effect=fade start=0 end=100 time=500 delay=500 condition=true')])
        self.background_control.setImage(self.getBackgroundImage())

    # Gets the image to use as the background
    def getBackgroundImage(self):
        # Default to a black image
        return MediaFiles.BLACK_IMAGE

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        # Needs to be implemented in sub class
        raise NotImplementedError

    # The number of images that need to be loaded quickly when launching the screen saver
    def getFastImageCount(self):
        # Allow specific screen savers to override this - default is none loaded quickly
        return 0

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        # Needs to be implemented in sub class
        raise NotImplementedError

    def process_image(self, image_control, imageDetails):
        # Needs to be implemented in sub class
        raise NotImplementedError

    def _preload_image(self, image_url):
        # set the next image to an invisible image-control for caching
        log('Screensaver: preloading image: %s' % repr(image_url))
        self.preload_control.setImage(image_url)
        log('Screensaver: preloading done')

    # Wait for the image to finish being displayed before starting on the next one
    def wait(self):
        CHUNK_WAIT_TIME = 250
        # wait in chunks of 250ms to react earlier on exit request
        chunk_wait_time = int(CHUNK_WAIT_TIME)
        remaining_wait_time = self.getNextImageTime()
        while remaining_wait_time > 0:
            if self.exit_requested:
                log('Screensaver: wait aborted')
                return
            if remaining_wait_time < chunk_wait_time:
                chunk_wait_time = remaining_wait_time
            remaining_wait_time -= chunk_wait_time
            xbmc.sleep(chunk_wait_time)

    def stop(self):
        log('Screensaver: stop')
        self.exit_requested = True
        self.exit_monitor = None

    def close(self):
        # Delete all the controls on close
        log('Screensaver: close')
        self.xbmc_window.removeControls(self.image_controls)
        self.xbmc_window.removeControls(self.global_controls)
        self.preload_control = None
        self.background_control = None
        self.loading_control = None
        self.image_controls = []
        self.global_controls = []
        self.xbmc_window.close()
        self.xbmc_window = None
        # Make sure we are not still gathering images
        if self.backgroundUpdate is not None:
            self.backgroundUpdate.stopProcessing()
            self.backgroundUpdate = None


# Shows the images as if they are being dropped one after the other onto a table
class TableDropScreensaver(ScreensaverBase):
    MODE = 'TableDrop'

    def __init__(self):
        log('TableDropScreensaver: __init__')

        # Animation values
        self.ROTATE_ANIMATION = ('effect=rotate start=0 end=%d center=auto time=%d delay=0 tween=circle condition=true')
        self.DROP_ANIMATION = ('effect=zoom start=%d end=100 center=auto time=%d delay=0 tween=circle condition=true')
        self.FADE_ANIMATION = ('effect=fade start=0 end=100 time=200 condition=true')

        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()

        self.MIN_WIDEST_DIMENSION = 500
        self.MAX_WIDEST_DIMENSION = 700

        ScreensaverBase.__init__(self)

    # Gets the image to use as the background
    def getBackgroundImage(self):
        return MediaFiles.TABLE_IMAGE

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        return 20

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        # There is an even amount of time between each image drop
        return int(self.NEXT_IMAGE_TIME)

    def process_image(self, image_control, imageDetails):
        # Hide the image - this could have been used previously and visible at the bottom of the stack
        # of images that we have
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        # check if wider or taller, then set the dimensions from that
        if imageDetails['aspect_ratio'] < 1.0:
            height = random.randint(self.MIN_WIDEST_DIMENSION, self.MAX_WIDEST_DIMENSION)
            width = int(height * imageDetails['aspect_ratio'])
        else:
            width = random.randint(self.MIN_WIDEST_DIMENSION, self.MAX_WIDEST_DIMENSION)
            height = int(width / imageDetails['aspect_ratio'])
        x_position = random.randint(0, 1280 - width)
        y_position = random.randint(0, 720 - height)
        drop_height = random.randint(400, 800)
        drop_duration = drop_height * 1.5
        rotation_degrees = random.uniform(-20, 20)
        rotation_duration = drop_duration
        animations = [('conditional', self.FADE_ANIMATION),
                      ('conditional', self.ROTATE_ANIMATION % (rotation_degrees, rotation_duration)),
                      ('conditional', self.DROP_ANIMATION % (drop_height, drop_duration))]
        # set all parameters and properties
        image_control.setImage(imageDetails['file'])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


# Shows the images like the Star Wars introduction sequence moving of into the distance
class StarWarsScreensaver(ScreensaverBase):
    MODE = 'StarWars'

    def __init__(self):
        log('StarWarsScreensaver: __init__')

        # Animation values
        self.TILT_ANIMATION = ('effect=rotatex start=0 end=55 center=auto time=0 condition=true')
        self.MOVE_ANIMATION = ('effect=slide start=0,2000 end=0,-3840 time=%d tween=linear condition=true')

        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()

        self.SPEED = ScreensaverSettings.getSpeed()
        self.EFFECT_TIME = 9000.0 / self.SPEED
        self.NEXT_IMAGE_TIME = self.EFFECT_TIME / 11

        # If we are dealing with a fanart image, then it will be
        # targeted at 1280 x 720, this would calculate as follows:
        # int(self.EFFECT_TIME / 11)
        # if the item is a thumbnail, then the proportions are different
        # in fact is will be 1280 x 1920 so we need to wait 2.8 times as along
        for imgType in ScreensaverSettings.getImageTypes():
            if imgType in ['thumbnail', 'cast']:
                self.NEXT_IMAGE_TIME = self.NEXT_IMAGE_TIME * 2.7
                break

        ScreensaverBase.__init__(self)

    # Gets the image to use as the background
    def getBackgroundImage(self):
        return MediaFiles.STARS_IMAGE

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        return 6

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        return int(self.NEXT_IMAGE_TIME)

    def process_image(self, image_control, imageDetails):
        # Hide the image (It should have already disappeared off the screen, but just in case)
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        width = 1280
        height = int(width / imageDetails['aspect_ratio'])
        x_position = 0
        y_position = 0
        if height > 720:
            y_position = int((height - 720) / -2)
        animations = [('conditional', self.TILT_ANIMATION),
                      ('conditional', self.MOVE_ANIMATION % self.EFFECT_TIME)]
        # set all parameters and properties
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        image_control.setImage(imageDetails['file'])
        # show the image
        image_control.setVisible(True)


# Shows the images being zoomed into one after the other
class RandomZoomInScreensaver(ScreensaverBase):
    MODE = 'RandomZoomIn'

    def __init__(self):
        log('RandomZoomInScreensaver: __init__')

        # Animation values
        self.ZOOM_ANIMATION = ('effect=zoom start=1 end=100 center=%d,%d time=%d tween=quadratic condition=true')

        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()
        self.EFFECT_TIME = ScreensaverSettings.getEffectTime()

        ScreensaverBase.__init__(self)

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        return 7

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        # Even amount of time between each zoom
        return int(self.NEXT_IMAGE_TIME)

    def process_image(self, image_control, imageDetails):
        # hide the image
        image_control.setVisible(False)
        image_control.setImage('')
        # re-stack it (to be on top)
        self.xbmc_window.removeControl(image_control)
        self.xbmc_window.addControl(image_control)
        # calculate all parameters and properties
        width = 1280
        height = int(width / imageDetails['aspect_ratio'])
        x_position = 0
        y_position = 0
        # Make sure if the image is too large to all fit on the screen
        # then make sure it is zoomed into about a third down, this is because
        # it is most probably a DVD Cover of Cast member, so it will result in
        # the focus at a better location after the zoom
        if height > 720:
            y_position = int((height - 720) / -3)
        zoom_x = random.randint(0, 1280)
        zoom_y = random.randint(0, 720)
        animations = [('conditional', self.ZOOM_ANIMATION % (zoom_x, zoom_y, self.EFFECT_TIME))]
        # set all parameters and properties
        image_control.setImage(imageDetails['file'])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


# Shows images creeping up from the bottom of the screen with a random overlap
class AppleTVLikeScreensaver(ScreensaverBase):
    MODE = 'AppleTVLike'

    def __init__(self):
        log('AppleTVLikeScreensaver: __init__')

        # Animation values (Make sure the images scroll completely off the screen)
        self.MOVE_ANIMATION = ('effect=slide start=0,720 end=0,-1280 center=auto time=%s tween=linear delay=0 condition=true')

        self.SPEED = ScreensaverSettings.getSpeed()
        self.CONCURRENCY = ScreensaverSettings.getAppletvlikeConcurrency()
        self.MAX_TIME = int(15000 / self.SPEED)
        self.NEXT_IMAGE_TIME = int(4500.0 / self.CONCURRENCY / self.SPEED)

        self.DISTANCE_RATIO = 0.7

        ScreensaverBase.__init__(self)

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        return 35

    # The number of images that need to be loaded quickly when launching the screen saver
    def getFastImageCount(self):
        return 2

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        return int(self.NEXT_IMAGE_TIME)

    def stack_cycle_controls(self):
        # randomly generate a zoom in percent as betavariant
        # between 10 and 70 and assign calculated width to control.
        # Remove all controls from window and re-add sorted by size.
        # This is needed because the bigger (=nearer) ones need to be in front
        # of the smaller ones.
        # Then shuffle image list again to have random size order.
        for image_control in self.image_controls:
            zoom = int(random.betavariate(2, 2) * 40) + 10
            # zoom = int(random.randint(10, 70))
            width = 1280 / 100 * zoom
            image_control.setWidth(width)
        self.image_controls = sorted(self.image_controls, key=lambda c: c.getWidth())
        self.xbmc_window.addControls(self.image_controls)
        random.shuffle(self.image_controls)

    def process_image(self, image_control, imageDetails):
        image_control.setVisible(False)
        image_control.setImage('')
        # calculate all parameters and properties based on the already set
        # width. We can not change the size again because all controls need
        # to be added to the window in size order.
        width = image_control.getWidth()
        zoom = width * 100 / 1280
        height = int(width / imageDetails['aspect_ratio'])
        # let images overlap max 1/2w left or right
        center = random.randint(0, 1280)
        x_position = center - width / 2
        y_position = 0

        time = self.MAX_TIME / zoom * self.DISTANCE_RATIO * 100

        animations = [('conditional', self.MOVE_ANIMATION % time)]
        # set all parameters and properties
        image_control.setImage(imageDetails['file'])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(animations)
        # show the image
        image_control.setVisible(True)


# Shows all the images in a grid and then fades new images in over time
class GridSwitchScreensaver(ScreensaverBase):
    MODE = 'GridSwitch'

    def __init__(self):
        log('GridSwitchScreensaver: __init__')

        # Animation values (The effect time is fixes at 500)
        self.EFFECT_TIME = 400
        self.fadeOutAnimations = [('conditional', ('effect=fade start=100 end=0 time=%d condition=true' % self.EFFECT_TIME))]
        self.fadeInAnimations = [('conditional', ('effect=fade start=0 end=100 time=%d condition=true' % self.EFFECT_TIME))]

        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()
        self.COLUMNS = ScreensaverSettings.getGridswitchRowsColumns()
        self.RANDOM_ORDER = ScreensaverSettings.isGridswitchRandom()

        # Work out if we are dealing with images that are 16.0 / 9.0 (Fanart)
        # or 2.0 / 3.0 (Thumbnail and Cast)
        self.ROWS = self.COLUMNS
        if 'fanart' not in ScreensaverSettings.getImageTypes():
            # Screen is 16 x 9, but images are 2 x 3
            # So for every 8 across we get 3 down
            self.ROWS = int(self.COLUMNS * 3 / 8) + 1

        ScreensaverBase.__init__(self)

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        return self.COLUMNS * self.ROWS

    # The number of images that need to be loaded quickly when launching the screen saver
    def getFastImageCount(self):
        # As we display all the images at the same time, set it to all of them
        return self.getImageControlCount()

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        return int(self.NEXT_IMAGE_TIME)

    def stack_cycle_controls(self):
        # Set position and dimensions based on stack position.
        # Shuffle image list to have random order.
        super(GridSwitchScreensaver, self).stack_cycle_controls()
        for i, image_control in enumerate(self.image_controls):
            current_row, current_col = divmod(i, self.COLUMNS)
            width = int(1280 / self.COLUMNS)
            height = int(720 / self.ROWS)
            x_position = width * current_col
            y_position = height * current_row
            image_control.setPosition(x_position, y_position)
            image_control.setWidth(width)
            image_control.setHeight(height)
        if self.RANDOM_ORDER:
            random.shuffle(self.image_controls)

    def process_image(self, image_control, imageDetails):
        if not self.image_count < self.getFastImageCount():
            image_control.setAnimations(self.fadeOutAnimations)
            xbmc.sleep(self.EFFECT_TIME)
        image_control.setImage(imageDetails['file'])
        image_control.setAnimations(self.fadeInAnimations)


# Shows the images by sliding one image into view while sliding the old one out of view
class SliderScreensaver(ScreensaverBase):
    MODE = 'Slider'

    def __init__(self):
        log('SliderScreensaver: __init__')

        self.previousImageControl = None
        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()
        self.EFFECT_TIME = ScreensaverSettings.getEffectTime()

        # Default is to slide in from the left
        SLIDE_IN_ANIMATION = ('effect=slide start=-1280.0 end=0,0 time=%d tween=cubic easing="inout" condition=true')
        SLIDE_OUT_ANIMATION = ('effect=slide start=0,0 end=1280,0 time=%d tween=cubic easing="inout" condition=true')
        origin = ScreensaverSettings.getSlideFromOrigin()
        if origin == 'Right':
            SLIDE_IN_ANIMATION = ('effect=slide start=1280,0 end=0,0 time=%d tween=cubic easing="inout" condition=true')
            SLIDE_OUT_ANIMATION = ('effect=slide start=0,0 end=-1280,0 time=%d tween=cubic easing="inout" condition=true')
        elif origin == 'Top':
            SLIDE_IN_ANIMATION = ('effect=slide start=0,-1280 end=0,0 time=%d tween=cubic easing="inout" condition=true')
            SLIDE_OUT_ANIMATION = ('effect=slide start=0,0 end=0,1280 time=%d tween=cubic easing="inout" condition=true')
        elif origin == 'Bottom':
            SLIDE_IN_ANIMATION = ('effect=slide start=0,1280 end=0,0 time=%d tween=cubic easing="inout" condition=true')
            SLIDE_OUT_ANIMATION = ('effect=slide start=0,0 end=0,-1280 time=%d tween=cubic easing="inout" condition=true')

        self.inAnimations = [('conditional', SLIDE_IN_ANIMATION % self.EFFECT_TIME)]
        self.outAnimations = [('conditional', SLIDE_OUT_ANIMATION % self.EFFECT_TIME)]

        ScreensaverBase.__init__(self)

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        # Only need two image controls, one on the screen, and one to slide on next
        return 2

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        # Even amount of time between each slide
        return int(self.NEXT_IMAGE_TIME)

    def process_image(self, image_control, imageDetails):
        # hide the image
        image_control.setVisible(False)

        # Work out the dimensions of the image to fill the screen but aspect ratio
        x_position = 0
        y_position = 0
        width = 1280
        height = 720
        if imageDetails['aspect_ratio'] < 1:
            # Taller than it is wide
            width = int(height * imageDetails['aspect_ratio'])
            x_position = int((1280 - width) / 2)

        # set all parameters and properties
        image_control.setImage(imageDetails['file'])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(self.inAnimations)

        # If the previous image is set, then slide it out
        if self.previousImageControl:
            self.previousImageControl.setAnimations(self.outAnimations)

        # show the image
        image_control.setVisible(True)
        self.previousImageControl = image_control


# Shows the images by fading the old one out and fading the new one in
class CrossfadeScreensaver(ScreensaverBase):
    MODE = 'Crossfade'

    def __init__(self):
        log('CrossfadeScreensaver: __init__')

        self.previousImageControl = None
        self.NEXT_IMAGE_TIME = ScreensaverSettings.getWaitTime()
        self.EFFECT_TIME = ScreensaverSettings.getEffectTime()

        # Default is to slide in from the left
        FADE_IN_ANIMATION = ('effect=fade start=0 end=100 time=%d easing="inout" condition=true')
        FADE_OUT_ANIMATION = ('effect=fade start=100 end=0 time=%d easing="inout" condition=true')

        self.inAnimations = [('conditional', FADE_IN_ANIMATION % self.EFFECT_TIME)]
        self.outAnimations = [('conditional', FADE_OUT_ANIMATION % self.EFFECT_TIME)]

        ScreensaverBase.__init__(self)

    # The number of image controls to create to handle the images
    def getImageControlCount(self):
        # Only need two image controls, one on the screen, and one to fade in next
        return 2

    # Get how long to wait until the next image is shown
    def getNextImageTime(self):
        # Even amount of time between each fade
        return int(self.NEXT_IMAGE_TIME)

    def process_image(self, image_control, imageDetails):
        # hide the image
        image_control.setVisible(False)

        # Work out the dimensions of the image to fill the screen but aspect ratio
        x_position = 0
        y_position = 0
        width = 1280
        height = 720
        if imageDetails['aspect_ratio'] < 1:
            # Taller than it is wide
            width = int(height * imageDetails['aspect_ratio'])
            x_position = int((1280 - width) / 2)

        # set all parameters and properties
        image_control.setImage(imageDetails['file'])
        image_control.setPosition(x_position, y_position)
        image_control.setWidth(width)
        image_control.setHeight(height)
        image_control.setAnimations(self.inAnimations)

        # If the previous image is set, then slide it out
        if self.previousImageControl:
            self.previousImageControl.setAnimations(self.outAnimations)

        # show the image
        image_control.setVisible(True)
        self.previousImageControl = image_control


# Function that will launch the screensaver and deal with all the work
# to tidy it up afterwards
def launchScreensaver():
    screensaver = ScreensaverManager()
    screensaver.start_loop()
    screensaver.close()
    del screensaver
    sys.modules.clear()

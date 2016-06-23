# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log
from settings import Settings

ADDON = xbmcaddon.Addon(id='script.recap')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


# Handles the display window
class Viewer(xbmcgui.WindowXMLDialog):
    TEXT_BOX_ID = 202
    TITLE_LABEL_ID = 201
    IMAGE_ID = 204
    CAPTION_ID = 205
    CLOSE_BUTTON = 302
    PREVIOUS_BUTTON = 305
    NEXT_BUTTON = 304
    CACHED_IMAGE_OFFSET = 400

    def __init__(self, *args, **kwargs):
        self.isClosedFlag = False
        self.currentImage = 0
        self.title = kwargs.get('title', '')
        self.summary = kwargs.get('summary', '')
        self.slideshow = kwargs.get('slideshow', '')
        self.alreadyCachedIdx = []
        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createViewer(title, summary, slideshow):
        return Viewer("script-recap-window.xml", CWD, title=title, summary=summary, slideshow=slideshow)

    # Called when setting up the window
    def onInit(self):
        # Update the dialog to show the correct data
        labelControl = self.getControl(Viewer.TITLE_LABEL_ID)
        labelControl.setLabel(self.title)

        textControl = self.getControl(Viewer.TEXT_BOX_ID)
        textControl.setText(self.summary)

        # Set the initial image
        if len(self.slideshow) > 0:
            self._setSlideshowImage(0)

        xbmcgui.WindowXMLDialog.onInit(self)

    # Handle any activity on the screen
    def onAction(self, action):
        # actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/input/Key.h
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        ACTION_PAGE_UP = 5
        ACTION_PAGE_DOWN = 6

        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("Viewer: Close Action received: %s" % str(action.getId()))
            self.close()
        elif action == ACTION_PAGE_UP:
            log("Viewer: Page Up Action received: %s" % str(action.getId()))
            # Page up is going to the previous page
            self.onClick(Viewer.PREVIOUS_BUTTON)
        elif action == ACTION_PAGE_DOWN:
            log("Viewer: Page Down Action received: %s" % str(action.getId()))
            # Page down is going to the next page
            self.onClick(Viewer.NEXT_BUTTON)

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == Viewer.CLOSE_BUTTON:
            log("Viewer: Close click action received: %d" % controlID)
            self.close()
        elif controlID == Viewer.NEXT_BUTTON:
            log("Viewer: Request to view next image: %d" % controlID)
            self._setSlideshowImage(self.currentImage + 1)
        elif controlID == Viewer.PREVIOUS_BUTTON:
            log("Viewer: Request to view previous image: %d" % controlID)
            self._setSlideshowImage(self.currentImage - 1)

    def close(self):
        log("Viewer: Closing window")
        self.isClosedFlag = True
        xbmcgui.WindowXMLDialog.close(self)

    def isClosed(self):
        return self.isClosedFlag

    def showNextSlideshowImage(self):
        autoNextImage = self.currentImage + 1
        # If we are already on the last image, check if we loop or not
        if autoNextImage > (len(self.slideshow) - 1):
            if Settings.isLoopSlideshow():
                autoNextImage = 0
            else:
                return

        # Move on to the next image in the slideshow
        self._setSlideshowImage(autoNextImage)

    def _setSlideshowImage(self, idx):
        log("Viewer: Showing image %d" % idx)
        if idx < 0:
            if not Settings.isLoopSlideshow():
                log("Viewer: Image %d out of range 0 to %d" % (idx, len(self.slideshow)))
            idx = len(self.slideshow) - 1
            log("Viewer: Image looped to last image %d" % idx)
        elif idx > (len(self.slideshow) - 1):
            if not Settings.isLoopSlideshow():
                log("Viewer: Image %d out of range 0 to %d" % (idx, len(self.slideshow)))
            idx = 0
            log("Viewer: Image looped to first image %d" % idx)

        self.currentImage = idx

        # Make sure the images are loaded
        self._cacheImages()

        imageControl = self.getControl(Viewer.IMAGE_ID)
        imageControl.setImage(self.slideshow[idx]["image"])

        if Settings.showImageCaptions():
            captionControl = self.getControl(Viewer.CAPTION_ID)
            captionControl.setText(self.slideshow[idx]["caption"])

        previousControl = self.getControl(Viewer.PREVIOUS_BUTTON)
        nextControl = self.getControl(Viewer.NEXT_BUTTON)
        # For automated slideshows, do not show the next and previous buttons
        if Settings.isAutoSlideshow():
            previousControl.setVisible(False)
            nextControl.setVisible(False)
        # If we are looping then need to always show the next and previous buttons
        elif Settings.isLoopSlideshow():
            previousControl.setVisible(True)
            nextControl.setVisible(True)
        else:
            if idx < 1:
                previousControl.setVisible(False)
            else:
                previousControl.setVisible(True)

            if idx >= (len(self.slideshow) - 1):
                nextControl.setVisible(False)
            else:
                nextControl.setVisible(True)

        # Highlight the pre-loaded image to show some form of progress
        # load all the images into the cache
        for i in range(1, 51):
            # Default colour is grey
            colour = 'EE000000'
            if i <= idx + 1:
                # Highlight in blue
                colour = 'EE000099'

            # If we have an image to highlight
            if i <= len(self.slideshow):
                cacheImageControlId = Viewer.CACHED_IMAGE_OFFSET + i
                imageControl = self.getControl(cacheImageControlId)
                imageControl.setColorDiffuse(colour)

    # Cache some of the images to speed up browsing
    def _cacheImages(self):
        # We need to cache 8 ahead
        for i in range(1, self.currentImage + 8):
            cacheImageControlId = i
            # If we have an image to cache
            if (i <= len(self.slideshow)) and (i > 0) and (i not in self.alreadyCachedIdx):
                log("Viewer: Caching image number %d" % i)
                cacheImageControlId = Viewer.CACHED_IMAGE_OFFSET + i
                imageControl = self.getControl(cacheImageControlId)
                imageControl.setImage(self.slideshow[i - 1]["image"])
                self.alreadyCachedIdx.append(i)

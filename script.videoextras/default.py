# -*- coding: utf-8 -*-
import sys
import os
import urllib
import traceback
import xbmc
import xbmcgui
import xbmcaddon


__addon__ = xbmcaddon.Addon(id='script.videoextras')
__addonid__ = __addon__.getAddonInfo('id')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log

# Load the database interface
from database import ExtrasDB

# Load the core Video Extras classes
from core import VideoExtrasBase

# Load the Video Extras Player that handles playing the extras files
from ExtrasPlayer import ExtrasPlayer

# Load any common dialogs
from dialogs import VideoExtrasResumeWindow


##################################################
# Class to store the details of the selected item
##################################################
class SourceDetails():
    title = None
    tvshowtitle = None
    fanart = None
    filenameAndPath = None
    isTvSource = None

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
        if SourceDetails.title is None:
            # Get the title of the Movie or TV Show
            if SourceDetails.isTv():
                SourceDetails.title = xbmc.getInfoLabel("ListItem.TVShowTitle")
            else:
                SourceDetails.title = xbmc.getInfoLabel("ListItem.Title")
            # There are times when the title has a different encoding
            try:
                SourceDetails.title = SourceDetails.title.decode("utf-8")
            except:
                pass

        return SourceDetails.title

    @staticmethod
    def getTvShowTitle():
        if SourceDetails.tvshowtitle is None:
            if SourceDetails.isTv():
                SourceDetails.tvshowtitle = xbmc.getInfoLabel("ListItem.TVShowTitle")
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
        if SourceDetails.filenameAndPath is None:
            extrasDirName = Settings.getExtrasDirName()
            if (extrasDirName is None) or (extrasDirName == ""):
                extrasDirName = "Extras"
            SourceDetails.filenameAndPath = "%s%s" % (xbmc.getInfoLabel("ListItem.FilenameAndPath"), extrasDirName)
        return SourceDetails.filenameAndPath

    @staticmethod
    def getFanArt():
        if SourceDetails.fanart is None:
            # Save the background
            SourceDetails.fanart = xbmc.getInfoLabel("ListItem.Property(Fanart_Image)")
            if SourceDetails.fanart is None:
                SourceDetails.fanart = ""
        return SourceDetails.fanart

    @staticmethod
    def isTv():
        if SourceDetails.isTvSource is None:
            if xbmc.getCondVisibility("Container.Content(tvshows)"):
                SourceDetails.isTvSource = True
            if xbmc.getCondVisibility("Container.Content(Seasons)"):
                SourceDetails.isTvSource = True
            if xbmc.getCondVisibility("Container.Content(Episodes)"):
                SourceDetails.isTvSource = True
            if xbmc.getInfoLabel("container.folderpath") == "videodb://tvshows/titles/":
                SourceDetails.isTvSource = True  # TvShowTitles
            # If still not set
            if SourceDetails.isTvSource is None:
                SourceDetails.isTvSource = False
        return SourceDetails.isTvSource


####################################################
# Class to control displaying and playing the extras
####################################################
class VideoExtrasDialog(xbmcgui.Window):
    def showList(self, exList):
        # Get the list of display names
        displayNameList = []
        for anExtra in exList:
            log("VideoExtrasDialog: filename: %s" % anExtra.getFilename())
            displayNameList.append(anExtra.getDisplayName())

        # Check if we are supporting YouTube Search
        vimeoPosition = -4
        if Settings.isVimeoSearchSupportEnabled():
            vimeoPosition = 0
            displayNameList.insert(0, __addon__.getLocalizedString(32122))

        # Check if we are supporting YouTube Search
        youtubePosition = -3
        if Settings.isYouTubeSearchSupportEnabled():
            youtubePosition = 0
            vimeoPosition = vimeoPosition + 1
            displayNameList.insert(0, __addon__.getLocalizedString(32116))

        addPlayAll = (len(exList) > 1)
        if addPlayAll:
            youtubePosition = youtubePosition + 1
            vimeoPosition = vimeoPosition + 1
            # Play All Selection Option
            displayNameList.insert(0, __addon__.getLocalizedString(32101))

        # Show the list to the user
        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), displayNameList)

        # User has made a selection, -1 is exit
        if select != -1:
            xbmc.executebuiltin("Dialog.Close(all, true)", True)
            waitLoop = 0
            while xbmc.Player().isPlaying() and waitLoop < 10:
                xbmc.sleep(100)
                waitLoop = waitLoop + 1
            xbmc.Player().stop()
            # Give anything that was already playing time to stop
            while xbmc.Player().isPlaying():
                xbmc.sleep(100)
            if (select == 0) and (addPlayAll is True):
                ExtrasPlayer.playAll(exList, SourceDetails.getTitle())
            elif select == youtubePosition:
                searchDetails = "/search/?q=%s+Extras" % urllib.quote_plus(SourceDetails.getTitle().encode('utf8'))
                log("VideoExtras: Running YouTube Addon/Plugin with search %s" % searchDetails)
                xbmc.executebuiltin("RunAddon(plugin.video.youtube,%s)" % searchDetails)
            elif select == vimeoPosition:
                searchDetails = "/search/?q=%s+Extras" % urllib.quote_plus(SourceDetails.getTitle().encode('utf8'))
                log("VideoExtras: Running Vimeo Addon/Plugin with search %s" % searchDetails)
                xbmc.executebuiltin("RunAddon(plugin.video.vimeo,%s)" % searchDetails)
            else:
                itemToPlay = select
                # If we added the PlayAll option to the list need to allow for it
                # in the selection, so add one
                if addPlayAll is True:
                    itemToPlay = itemToPlay - 1
                if vimeoPosition >= 0:
                    itemToPlay = itemToPlay - 1
                if youtubePosition >= 0:
                    itemToPlay = itemToPlay - 1
                log("VideoExtrasDialog: Start playing %s" % exList[itemToPlay].getFilename())
                ExtrasPlayer.performPlayAction(exList[itemToPlay], SourceDetails.getTitle())
        else:
            return False
        return True


#################################
# Main Class to control the work
#################################
class VideoExtras(VideoExtrasBase):

    def findExtras(self, exitOnFirst=False, extrasDb=None, defaultFanArt=""):
        # Display the busy icon while searching for files
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        files = VideoExtrasBase.findExtras(self, exitOnFirst, extrasDb, defaultFanArt)
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        return files

    # Enable and disable the display of the extras button
    def checkButtonEnabled(self):
        # See if the option to force the extras button is enabled,
        # if which case just make sure the hide option is cleared
        # Also if we are using YouTube, we want to always display the button
        if Settings.isForceButtonDisplay() or Settings.isYouTubeSearchSupportEnabled() or Settings.isVimeoSearchSupportEnabled():
            xbmcgui.Window(12003).clearProperty("HideVideoExtrasButton")
            log("VideoExtras: Force VideoExtras Button Enabled")
        else:
            # Search for the extras, stopping when the first is found
            # only want to find out if the button should be available
            # No need for DB or default fanart, as just checking for existence
            files = self.findExtras(True)
            if files:
                # Set a flag on the window so we know there is data
                xbmcgui.Window(12003).clearProperty("HideVideoExtrasButton")
                log("VideoExtras: Button Enabled")
            else:
                # Hide the extras button, there are no extras
                xbmcgui.Window(12003).setProperty("HideVideoExtrasButton", "true")
                log("VideoExtras: Button disabled")

    def run(self, files):
        # All the files have been retrieved, now need to display them
        if not files and not Settings.isYouTubeSearchSupportEnabled() and not Settings.isVimeoSearchSupportEnabled():
            # "Info", "No extras found"
            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32102), __addon__.getLocalizedString(32103))
        else:
            isTvTunesAlreadySet = True
            needsWindowReset = True

            # Make sure we don't leave global variables set
            try:
                # Check which listing format to use
                if Settings.isDetailedListScreen():
                    # Check if TV Tunes override is already set
                    isTvTunesAlreadySet = (xbmcgui.Window(12000).getProperty("TvTunesContinuePlaying").lower() == "true")
                    # If TV Tunes is running we want to ensure that we still keep the theme going
                    # so set this variable on the home screen
                    if not isTvTunesAlreadySet:
                        log("VideoExtras: Setting TV Tunes override")
                        xbmcgui.Window(12000).setProperty("TvTunesContinuePlaying", "True")
                    else:
                        log("VideoExtras: TV Tunes override already set")

                    extrasWindow = VideoExtrasWindow.createVideoExtrasWindow(files=files)
                    xbmc.executebuiltin("Dialog.Close(movieinformation)", True)
                    extrasWindow.doModal()
                    del extrasWindow
                else:
                    extrasWindow = VideoExtrasDialog()
                    needsWindowReset = extrasWindow.showList(files)
                    del extrasWindow

                # The video selection will be the default return location
                if (not Settings.isMenuReturnVideoSelection()) and needsWindowReset:
                    if Settings.isMenuReturnHome():
                        xbmc.executebuiltin("ActivateWindow(home)", True)
                    else:
                        infoDialogId = 12003
                        # Put the information dialog back up
                        xbmc.executebuiltin("ActivateWindow(movieinformation)")
                        if Settings.isMenuReturnExtras():
                            # Wait for the Info window to open, it can take a while
                            # this is to avoid the case where the exList dialog displays
                            # behind the info dialog
                            counter = 0
                            while (xbmcgui.getCurrentWindowDialogId() != infoDialogId) and (counter < 30):
                                xbmc.sleep(100)
                                counter = counter + 1
                            # Allow time for the screen to load - this could result in an
                            # action such as starting TvTunes
                            xbmc.sleep(1000)
                            # Before showing the list, check if someone has quickly
                            # closed the info screen while it was opening and we were waiting
                            if xbmcgui.getCurrentWindowDialogId() == infoDialogId:
                                # Reshow the exList that was previously generated
                                self.run(files)
            except:
                log("VideoExtras: %s" % traceback.format_exc(), xbmc.LOGERROR)

            # Tidy up the TV Tunes flag if we set it
            if not isTvTunesAlreadySet:
                log("VideoExtras: Clearing TV Tunes override")
                xbmcgui.Window(12000).clearProperty("TvTunesContinuePlaying")


#####################################################################
# Extras display Window that contains a few more details and looks
# more like the TV SHows listing
#####################################################################
class VideoExtrasWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.files = kwargs.pop('files')
        self.lastRecordedListPosition = -1

    # Static method to create the Window class
    @staticmethod
    def createVideoExtrasWindow(files):
        return VideoExtrasWindow("script-videoextras-main.xml", __addon__.getAddonInfo('path').decode("utf-8"), files=files)

    def onInit(self):
        # Need to clear the list of the default items
        self.clearList()

        # Start by adding an option to Play All
        if len(self.files) > 0:
            anItem = xbmcgui.ListItem(__addon__.getLocalizedString(32101), path=SourceDetails.getFilenameAndPath())
            # Get the first items fanart for the play all option
            anItem.setProperty("Fanart_Image", self.files[0].getFanArt())

            if SourceDetails.getTvShowTitle() != "":
                anItem.setInfo('video', {'TvShowTitle': SourceDetails.getTvShowTitle()})

            if SourceDetails.getTitle() != "":
                anItem.setInfo('video', {'Title': SourceDetails.getTitle()})

            self.addItem(anItem)

        # Check if we want to have YouTube Extra Support
        if Settings.isYouTubeSearchSupportEnabled():
            # Create the message to the YouTube Plugin
            li = xbmcgui.ListItem(__addon__.getLocalizedString(32116))
            # Need to set the title to get it in the header
            if SourceDetails.getTvShowTitle() != "":
                li.setInfo('video', {'TvShowTitle': SourceDetails.getTvShowTitle()})
            if SourceDetails.getTitle() != "":
                li.setInfo('video', {'Title': SourceDetails.getTitle()})

            li.setProperty("Fanart_Image", SourceDetails.getFanArt())
            li.setProperty("search", "/search/?q=%s+Extras" % urllib.quote_plus(SourceDetails.getTitle().encode('utf8')))
            self.addItem(li)

        # Check if we want to have Vimeo Extra Support
        if Settings.isVimeoSearchSupportEnabled():
            # Create the message to the Vimeo Plugin
            li = xbmcgui.ListItem(__addon__.getLocalizedString(32122))
            # Need to set the title to get it in the header
            if SourceDetails.getTvShowTitle() != "":
                li.setInfo('video', {'TvShowTitle': SourceDetails.getTvShowTitle()})
            if SourceDetails.getTitle() != "":
                li.setInfo('video', {'Title': SourceDetails.getTitle()})

            li.setProperty("Fanart_Image", SourceDetails.getFanArt())
            li.setProperty("search", "/search/?q=%s+Extras" % urllib.quote_plus(SourceDetails.getTitle().encode('utf8')))
            self.addItem(li)

        for anExtra in self.files:
            log("VideoExtrasWindow: filename: %s" % anExtra.getFilename())

            # Create the list item
            anItem = anExtra.createListItem(path=SourceDetails.getFilenameAndPath(), parentTitle=SourceDetails.getTitle(), tvShowTitle=SourceDetails.getTvShowTitle())

            self.addItem(anItem)

        # Before we return, set back the selected on screen item to the one just watched
        # This is in the case of a reload
        if self.lastRecordedListPosition > 0:
            self.setCurrentListPosition(self.lastRecordedListPosition)

        xbmcgui.WindowXML.onInit(self)

    # Handle the close action and the context menu request
    def onAction(self, action):
        # actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        ACTION_CONTEXT_MENU = 117

        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("VideoExtrasWindow: Close Action received: %s" % str(action.getId()))
            self.close()
        elif action == ACTION_CONTEXT_MENU:
            youtubePosition = 0
            vimeoPosition = 0
            if len(self.files) > 0:
                youtubePosition = youtubePosition + 1
                vimeoPosition = vimeoPosition + 1

            if Settings.isYouTubeSearchSupportEnabled():
                vimeoPosition = vimeoPosition + 1
                # Check to see if the context menu has been called up for the You Tube option
                if self.getCurrentListPosition() == youtubePosition:
                    contextWindow = VideoPluginContextMenu.createYouTubeContextMenu(SourceDetails.getTitle())
                    contextWindow.doModal()
                    del contextWindow
                    return

            if Settings.isVimeoSearchSupportEnabled() and self.getCurrentListPosition() == vimeoPosition:
                contextWindow = VideoPluginContextMenu.createVimeoContextMenu(SourceDetails.getTitle())
                contextWindow.doModal()
                del contextWindow
                return

            # Check for the Play All case
            if self.getCurrentListPosition() == 0:
                return

            # Get the item that was clicked on
            extraItem = self._getCurrentSelection()
            # create the context window
            contextWindow = VideoExtrasContextMenu.createVideoExtrasContextMenu(extraItem)
            contextWindow.doModal()

            # Check the return value, if exit, then we play nothing
            if contextWindow.isExit():
                return
            # If requested to restart from beginning, reset the resume point before playing
            if contextWindow.isRestart():
                extraItem.setResumePoint(0)
                ExtrasPlayer.performPlayAction(extraItem, SourceDetails.getTitle())

            if contextWindow.isResume():
                ExtrasPlayer.performPlayAction(extraItem, SourceDetails.getTitle())

            if contextWindow.isMarkUnwatched():
                # Need to remove the row from the database
                if Settings.isDatabaseEnabled():
                    # Refresh the screen now that we have change the flag
                    extraItem.setResumePoint(0)
                    extraItem.saveState()
                    self.onInit()

            if contextWindow.isMarkWatched():
                # If marking as watched we need to set the resume time so it doesn't
                # start in the middle the next time it starts
                if Settings.isDatabaseEnabled():
                    extraItem.setResumePoint(extraItem.getTotalDuration())
                    extraItem.saveState()
                    self.onInit()

            if contextWindow.isEditTitle():
                # Prompt the user for the new name
                keyboard = xbmc.Keyboard()
                keyboard.setDefault(extraItem.getDisplayName())
                keyboard.doModal()

                if keyboard.isConfirmed():
                    try:
                        newtitle = keyboard.getText().decode("utf-8")
                    except:
                        newtitle = keyboard.getText()

                    # Only set the title if it has changed
                    if (newtitle != extraItem.getDisplayName()) and (len(newtitle) > 0):
                        result = extraItem.setTitle(newtitle, isTV=SourceDetails.isTv())
                        if not result:
                            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32102), __addon__.getLocalizedString(32109))
                        else:
                            self.onInit()

            if contextWindow.isEditPlot():
                # Prompt the user for the new plot description
                keyboard = xbmc.Keyboard()
                keyboard.setDefault(extraItem.getPlot())
                keyboard.doModal()

                if keyboard.isConfirmed():
                    try:
                        newplot = keyboard.getText().decode("utf-8")
                    except:
                        newplot = keyboard.getText()

                    # Only set the plot if it has changed
                    if (newplot != extraItem.getPlot()) and ((len(newplot) > 0) or (extraItem.getPlot() is not None)):
                        result = extraItem.setPlot(newplot, isTV=SourceDetails.isTv())
                        if not result:
                            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32102), __addon__.getLocalizedString(32115))
                        else:
                            self.onInit()

            del contextWindow

    def onClick(self, control):
        WINDOW_LIST_ID = 51
        # Check to make sure that this click was for the extras list
        if control != WINDOW_LIST_ID:
            return

        # Check the YouTube Search first, as if there are no Extras on disk
        # There will not be a PlayAll button and it will just be the YouTube Link
        youtubePosition = 0
        vimeoPosition = 0
        if len(self.files) > 0:
            youtubePosition = youtubePosition + 1
            vimeoPosition = vimeoPosition + 1

        if Settings.isYouTubeSearchSupportEnabled():
            vimeoPosition = vimeoPosition + 1
            if self.getCurrentListPosition() == youtubePosition:
                anItem = self.getListItem(youtubePosition)
                searchDetails = anItem.getProperty("search")
                log("VideoExtras: Running YouTube Addon/Plugin with search %s" % searchDetails)
                xbmc.executebuiltin("RunAddon(plugin.video.youtube,%s)" % searchDetails)
                return

        if Settings.isVimeoSearchSupportEnabled() and self.getCurrentListPosition() == vimeoPosition:
                anItem = self.getListItem(vimeoPosition)
                searchDetails = anItem.getProperty("search")
                log("VideoExtras: Running Vimeo Addon/Plugin with search %s" % searchDetails)
                xbmc.executebuiltin("RunAddon(plugin.video.vimeo,%s)" % searchDetails)
                return

        # Check for the Play All case
        if self.getCurrentListPosition() == 0:
            ExtrasPlayer.playAll(self.files, SourceDetails.getTitle())
            return

        # Get the item that was clicked on
        extraItem = self._getCurrentSelection()

        if extraItem is None:
            # Something has gone very wrong, there is no longer the item that was selected
            log("VideoExtrasWindow: Unable to match item to current selection")
            return

        # If part way viewed prompt the user for resume or play from beginning
        if extraItem.getResumePoint() > 0:
            resumeWindow = VideoExtrasResumeWindow.createVideoExtrasResumeWindow(extraItem.getDisplayResumePoint())
            resumeWindow.doModal()

            # Check the return value, if exit, then we play nothing
            if resumeWindow.isExit():
                return
            # If requested to restart from beginning, reset the resume point before playing
            if resumeWindow.isRestart():
                extraItem.setResumePoint(0)
            # Default is to actually resume
            del resumeWindow

        ExtrasPlayer.performPlayAction(extraItem, SourceDetails.getTitle())

    # Search the list of extras for a given filename
    def _getCurrentSelection(self):
        self.lastRecordedListPosition = self.getCurrentListPosition()
        log("VideoExtrasWindow: List position = %d" % self.lastRecordedListPosition)
        anItem = self.getListItem(self.lastRecordedListPosition)
        filename = anItem.getProperty("Filename")
        log("VideoExtrasWindow: Selected file = %s" % filename)
        # Now search the Extras list for a match
        for anExtra in self.files:
            if anExtra.isFilenameMatch(filename):
                log("VideoExtrasWindow: Found  = %s" % filename)
                return anExtra
        return None


#######################################################
# Context Menu
#
# - Resume From 00:00
# - Play From Start
# - Mark as watched (If not watched)
# - Mark as unwatched (If watched)
# - Set title (Write NFO file if directory writable)
#######################################################
class VideoExtrasContextMenu(xbmcgui.WindowXMLDialog):
    EXIT = 1
    RESUME = 2
    RESTART = 40
    MARK_WATCHED = 41
    MARK_UNWATCHED = 42
    EDIT_TITLE = 43
    EDIT_PLOT = 44

    def __init__(self, *args, **kwargs):
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.extraItem = kwargs.pop('extraItem')
        self.selectionMade = VideoExtrasContextMenu.EXIT

    # Static method to create the Window Dialog class
    @staticmethod
    def createVideoExtrasContextMenu(extraItem):
        # Pull out the resume time as this will be processed by the base class
        return VideoExtrasContextMenu("script-videoextras-context.xml", __addon__.getAddonInfo('path').decode("utf-8"), extraItem=extraItem)

    def onInit(self):
        # Need to populate the resume point
        resumeButton = self.getControl(VideoExtrasContextMenu.RESUME)
        currentLabel = resumeButton.getLabel()
        newLabel = "%s %s" % (currentLabel, self.extraItem.getDisplayResumePoint())

        # Reset the resume label with the addition of the time
        resumeButton.setLabel(newLabel)

        xbmcgui.WindowXMLDialog.onInit(self)

    def onClick(self, control):
        # Save the item that was clicked
        self.selectionMade = control
        # If not resume or restart - we just want to exit without playing
        if not (self.isResume() or self.isRestart() or self.isMarkWatched() or self.isMarkUnwatched() or self.isEditTitle() or self.isEditPlot()):
            self.selectionMade = VideoExtrasContextMenu.EXIT
        # Close the dialog after the selection
        self.close()

    def isResume(self):
        return self.selectionMade == VideoExtrasContextMenu.RESUME

    def isRestart(self):
        return self.selectionMade == VideoExtrasContextMenu.RESTART

    def isExit(self):
        return self.selectionMade == VideoExtrasContextMenu.EXIT

    def isMarkWatched(self):
        return self.selectionMade == VideoExtrasContextMenu.MARK_WATCHED

    def isMarkUnwatched(self):
        return self.selectionMade == VideoExtrasContextMenu.MARK_UNWATCHED

    def isEditTitle(self):
        return self.selectionMade == VideoExtrasContextMenu.EDIT_TITLE

    def isEditPlot(self):
        return self.selectionMade == VideoExtrasContextMenu.EDIT_PLOT


# Context Menu for the YouTube/Vimeo Command
# Overwrites the values in our own custom Context menu
class VideoPluginContextMenu(xbmcgui.WindowXMLDialog):
    EXIT = 1
    RESUME__EXTRAS = 2
    RESTART__DELETED_SCENES = 40
    MARK_WATCHED__SPECIAL_FEATURES = 41
    MARK_UNWATCHED__BLOOPERS = 42
    EDIT_TITLE__INTERVIEW = 43
    EDIT_PLOT__VFX = 44

    def __init__(self, *args, **kwargs):
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.title = kwargs.pop('title')
        if self.title is not None:
            self.title = self.title.replace(" ", "+")
        self.pluginName = kwargs.pop('pluginName')
        self.selectionMade = VideoPluginContextMenu.EXIT

    # Static method to create the Window Dialog class
    @staticmethod
    def createYouTubeContextMenu(title):
        return VideoPluginContextMenu("script-videoextras-context.xml", __addon__.getAddonInfo('path').decode("utf-8"), pluginName='plugin.video.youtube', title=title)

    # Static method to create the Window Dialog class
    @staticmethod
    def createVimeoContextMenu(title):
        return VideoPluginContextMenu("script-videoextras-context.xml", __addon__.getAddonInfo('path').decode("utf-8"), pluginName='plugin.video.vimeo', title=title)

    def onInit(self):
        # Reset all the labels for the Context Menu
        ctxButton = self.getControl(VideoPluginContextMenu.RESUME__EXTRAS)
        ctxButton.setLabel(__addon__.getLocalizedString(32001))

        ctxButton = self.getControl(VideoPluginContextMenu.RESTART__DELETED_SCENES)
        ctxButton.setLabel(__addon__.getLocalizedString(32117))

        ctxButton = self.getControl(VideoPluginContextMenu.MARK_WATCHED__SPECIAL_FEATURES)
        ctxButton.setLabel(__addon__.getLocalizedString(32118))

        ctxButton = self.getControl(VideoPluginContextMenu.MARK_UNWATCHED__BLOOPERS)
        ctxButton.setLabel(__addon__.getLocalizedString(32119))

        ctxButton = self.getControl(VideoPluginContextMenu.EDIT_TITLE__INTERVIEW)
        ctxButton.setLabel(__addon__.getLocalizedString(32120))

        ctxButton = self.getControl(VideoPluginContextMenu.EDIT_PLOT__VFX)
        ctxButton.setLabel(__addon__.getLocalizedString(32121))

        xbmcgui.WindowXMLDialog.onInit(self)

    def onClick(self, control):
        # Save the item that was clicked
        self.selectionMade = control

        # Close the dialog after the selection
        self.close()

        cmd = None
        escTitle = urllib.quote_plus(self.title.encode('utf8'))
        # Check what the action was
        if self.selectionMade == VideoPluginContextMenu.RESUME__EXTRAS:
            cmd = "/search/?q=%s+Extras" % escTitle
        elif self.selectionMade == VideoPluginContextMenu.RESTART__DELETED_SCENES:
            cmd = "/search/?q=%s+Deleted+Scene" % escTitle
        elif self.selectionMade == VideoPluginContextMenu.MARK_WATCHED__SPECIAL_FEATURES:
            cmd = "/search/?q=%s+Special+Features" % escTitle
        elif self.selectionMade == VideoPluginContextMenu.MARK_UNWATCHED__BLOOPERS:
            cmd = "/search/?q=%s+Blooper" % escTitle
        elif self.selectionMade == VideoPluginContextMenu.EDIT_TITLE__INTERVIEW:
            cmd = "/search/?q=%s+Interview" % escTitle
        elif self.selectionMade == VideoPluginContextMenu.EDIT_PLOT__VFX:
            cmd = "/search/?q=%s+VFX" % escTitle

        if cmd not in [None, ""]:
            xbmc.executebuiltin("RunAddon(%s,%s)" % (self.pluginName, cmd))


#########################
# Main
#########################
if __name__ == '__main__':
    try:
        if len(sys.argv) > 2:
            # get the type of operation
            log("Operation = %s" % sys.argv[1])

            # Check to make sure that there was actually some data in the second argument
            # it's possible that a skin has sent us an empty string
            if (sys.argv[2] is None) or (len(sys.argv[2]) < 1):
                log("VideoExtras: Called with empty final argument", xbmc.LOGERROR)
            else:
                # Load the details of the current source of the extras
                SourceDetails.forceLoadDetails()

                # handle the plugins that VideoExtras supports
                forceExtrasSupport = False
                if ("plugin.video.emby" in sys.argv[2]) and Settings.isCustomPathEnabled():
                    forceExtrasSupport = True

                # Make sure we are not passed a plugin path
                if ("plugin://" in sys.argv[2]) and not forceExtrasSupport:
                    if sys.argv[1] == "check":
                        xbmcgui.Window(12003).setProperty("HideVideoExtrasButton", "true")
                else:
                    # Create the extras class that deals with any extras request
                    videoExtras = VideoExtras(sys.argv[2])

                    # We are either running the command or just checking for existence
                    if sys.argv[1] == "check":
                        videoExtras.checkButtonEnabled()
                    else:
                        # Check if the use database setting is enabled
                        extrasDb = None
                        if Settings.isDatabaseEnabled():
                            extrasDb = ExtrasDB()
                        # Perform the search command
                        files = videoExtras.findExtras(extrasDb=extrasDb, defaultFanArt=SourceDetails.getFanArt())
                        # need to display the extras
                        videoExtras.run(files)

                    del videoExtras
        else:
            # Close any open dialogs
            xbmc.executebuiltin("Dialog.Close(all, true)", True)

            log("VideoExtras: Running as Addon/Plugin")
            xbmc.executebuiltin("RunAddon(script.videoextras)")
    except:
        log("VideoExtras: %s" % traceback.format_exc(), xbmc.LOGERROR)

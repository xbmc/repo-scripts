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
import sys
import os
import re
import traceback
import xml.etree.ElementTree as ET
#Modules XBMC
import xbmcplugin
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon

if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson


__addon__     = xbmcaddon.Addon(id='script.videoextras')
__addonid__   = __addon__.getAddonInfo('id')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join

# Load the database interface
from database import ExtrasDB

# Load the core Video Extras classes
from core import ExtrasItem
from core import SourceDetails
from core import WindowShowing
from core import VideoExtrasBase

# Load the Video Extras Player that handles playing the extras files
from ExtrasPlayer import ExtrasPlayer

# Load any common dialogs
from dialogs import VideoExtrasResumeWindow

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

        addPlayAll = (len(exList) > 1)
        if addPlayAll:
            # Play All Selection Option
            displayNameList.insert(0, __addon__.getLocalizedString(32101) )

        # Show the list to the user
        select = xbmcgui.Dialog().select(__addon__.getLocalizedString(32001), displayNameList)

        # User has made a selection, -1 is exit
        if select != -1:
            xbmc.executebuiltin("Dialog.Close(all, true)", True)
            extrasPlayer = ExtrasPlayer()
            waitLoop = 0
            while extrasPlayer.isPlaying() and waitLoop < 10:
                xbmc.sleep(100)
                waitLoop = waitLoop + 1
            extrasPlayer.stop()
            # Give anything that was already playing time to stop
            while extrasPlayer.isPlaying():
                xbmc.sleep(100)
            if (select == 0) and (addPlayAll == True):
                extrasPlayer.playAll( exList )
            else:
                itemToPlay = select
                # If we added the PlayAll option to the list need to allow for it
                # in the selection, so add one
                if addPlayAll == True:
                    itemToPlay = itemToPlay - 1
                log( "VideoExtrasDialog: Start playing %s" % exList[itemToPlay].getFilename() )
                extrasPlayer.play( exList[itemToPlay] )
            while extrasPlayer.isPlayingVideo():
                xbmc.sleep(100)
                
                # If the user selected the "Play All" option, then we do not want to
                # stop between the two videos, so do an extra wait
                if (select == 0) and (addPlayAll == True) and (not extrasPlayer.isPlayingVideo()):
                    xbmc.sleep(3000)      
        else:
            return False
        return True


#################################
# Main Class to control the work
#################################
class VideoExtras(VideoExtrasBase):

    def findExtras(self, exitOnFirst=False, extrasDb=None):
        # Display the busy icon while searching for files
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        files = VideoExtrasBase.findExtras(self, exitOnFirst, extrasDb)
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        return files

    # Enable and disable the display of the extras button
    def checkButtonEnabled(self):
        # See if the option to force the extras button is enabled,
        # if which case just make sure the hide option is cleared
        if Settings.isForceButtonDisplay():
            xbmcgui.Window( 12003 ).clearProperty("HideVideoExtrasButton")
            log("VideoExtras: Force VideoExtras Button Enabled")
        else:
            # Search for the extras, stopping when the first is found
            # only want to find out if the button should be available
            files = self.findExtras(True)
            if files:
                # Set a flag on the window so we know there is data
                xbmcgui.Window( 12003 ).clearProperty("HideVideoExtrasButton")
                log("VideoExtras: Button Enabled")
            else:
                # Hide the extras button, there are no extras
                xbmcgui.Window( 12003 ).setProperty( "HideVideoExtrasButton", "true" )
                log("VideoExtras: Button disabled")


    def run(self, files):
        # All the files have been retrieved, now need to display them       
        if not files:
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
                    isTvTunesAlreadySet = (xbmcgui.Window( 12000 ).getProperty("TvTunesContinuePlaying").lower() == "true")
                    # If TV Tunes is running we want to ensure that we still keep the theme going
                    # so set this variable on the home screen
                    if not isTvTunesAlreadySet:
                        log("VideoExtras: Setting TV Tunes override")
                        xbmcgui.Window( 12000 ).setProperty( "TvTunesContinuePlaying", "True" )
                    else:
                        log("VideoExtras: TV Tunes override already set")
    
                    extrasWindow = VideoExtrasWindow.createVideoExtrasWindow(files=files)
                    xbmc.executebuiltin( "Dialog.Close(movieinformation)", True )
                    extrasWindow.doModal()
                else:
                    extrasWindow = VideoExtrasDialog()
                    needsWindowReset = extrasWindow.showList( files )
                
                # The video selection will be the default return location
                if (not Settings.isMenuReturnVideoSelection()) and needsWindowReset:
                    if Settings.isMenuReturnHome():
                        xbmc.executebuiltin("xbmc.ActivateWindow(home)", True)
                    else:
                        infoDialogId = 12003
                        # Put the information dialog back up
                        xbmc.executebuiltin("xbmc.ActivateWindow(movieinformation)")
                        if Settings.isMenuReturnExtras():
                            # Wait for the Info window to open, it can take a while
                            # this is to avoid the case where the exList dialog displays
                            # behind the info dialog
                            counter = 0
                            while( xbmcgui.getCurrentWindowDialogId() != infoDialogId) and (counter <30):
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
                log("VideoExtras: %s" % traceback.format_exc())

            # Tidy up the TV Tunes flag if we set it
            if not isTvTunesAlreadySet:
                log("VideoExtras: Clearing TV Tunes override")
                xbmcgui.Window( 12000 ).clearProperty( "TvTunesContinuePlaying" )


#####################################################################
# Extras display Window that contains a few more details and looks
# more like the TV SHows listing
#####################################################################
class VideoExtrasWindow(xbmcgui.WindowXML):
    def __init__( self, *args, **kwargs ):
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
        anItem = xbmcgui.ListItem(__addon__.getLocalizedString(32101))
        self.addItem(anItem)
        
        for anExtra in self.files:
            log("VideoExtrasWindow: filename: %s" % anExtra.getFilename())

            # Create the list item
            anItem = anExtra.createListItem()

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
        ACTION_NAV_BACK      = 92
        ACTION_CONTEXT_MENU = 117

        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("VideoExtrasWindow: Close Action received: %s" % str(action.getId()))
            self.close()
        elif action == ACTION_CONTEXT_MENU:
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
                ExtrasPlayer.performPlayAction(extraItem)
                
            if contextWindow.isResume():
                ExtrasPlayer.performPlayAction(extraItem)

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
                        result = extraItem.setTitle(newtitle)
                        if not result:
                            xbmcgui.Dialog().ok(__addon__.getLocalizedString(32102), __addon__.getLocalizedString(32109))
                        else:
                            self.onInit()


    def onClick(self, control):
        WINDOW_LIST_ID = 51
        # Check to make sure that this click was for the extras list
        if control != WINDOW_LIST_ID:
            return
        
        # Check for the Play All case
        if self.getCurrentListPosition() == 0:
            extrasPlayer = ExtrasPlayer()
            extrasPlayer.playAll( self.files )
            return
        
        # Get the item that was clicked on
        extraItem = self._getCurrentSelection()
        
        if extraItem == None:
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
            
        ExtrasPlayer.performPlayAction(extraItem)
        

    # Search the list of extras for a given filename
    def _getCurrentSelection(self):
        self.lastRecordedListPosition = self.getCurrentListPosition()
        log("VideoExtrasWindow: List position = %d" % self.lastRecordedListPosition)
        anItem = self.getListItem(self.lastRecordedListPosition)
        filename = anItem.getProperty("Filename")
        log("VideoExtrasWindow: Selected file = %s" % filename)
        # Now search the Extras list for a match
        for anExtra in self.files:
            if anExtra.isFilenameMatch( filename ):
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
    
    def __init__( self, *args, **kwargs ):
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
        if not (self.isResume() or self.isRestart() or self.isMarkWatched() or self.isMarkUnwatched() or self.isEditTitle()):
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



#########################
# Main
#########################
if __name__ == '__main__':
    try:
        if len(sys.argv) > 2:
            # get the type of operation
            log("Operation = %s" % sys.argv[1])
    
            # Load the details of the current source of the extras        
            SourceDetails.forceLoadDetails()
                
            # Make sure we are not passed a plugin path
            if "plugin://" in sys.argv[2]:
                if sys.argv[1] == "check":
                    xbmcgui.Window( 12003 ).setProperty( "HideVideoExtrasButton", "true" )
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
                        # Make sure the database has been created
                        extrasDb.createDatabase()
                    # Perform the search command
                    files = videoExtras.findExtras(extrasDb=extrasDb)
                    # need to display the extras
                    videoExtras.run(files)
        else:
            # Close any open dialogs
            xbmc.executebuiltin("Dialog.Close(all, true)", True)
        
            # Default to the plugin method
            xbmc.executebuiltin("xbmc.ActivateWindow(Video, addons://sources/video/)", True)
        
            # It is a bit hacky, but the only way I can get it to work
            # After loading the plugin screen, navigate to the VideoExtras entry and select it
            maxChecks = 100
            selectedTitle = None
            while selectedTitle != 'VideoExtras' and maxChecks > 0:
                maxChecks = maxChecks - 1
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.Up", "params": { }, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                log( json_response )
        
                # Allow time for the command to be reflected on the screen      
                xbmc.sleep(100)
        
                selectedTitle = xbmc.getInfoLabel('ListItem.Label')
                log("VideoExtras: plugin screen selected Title=%s" % selectedTitle)
        
            # Now select the menu item if it is TvTunes
            if selectedTitle == 'VideoExtras':
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.Select", "params": { }, "id": 1}')
                json_query = unicode(json_query, 'utf-8', errors='ignore')
                json_response = simplejson.loads(json_query)
                log( json_response )
            

    except:
        log("VideoExtras: %s" % traceback.format_exc())


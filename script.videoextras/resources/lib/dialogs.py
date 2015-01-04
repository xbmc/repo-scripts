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


##################################################
# Dialog window to find out is a video should be
# resumes or started from the beginning
##################################################
class VideoExtrasResumeWindow(xbmcgui.WindowXMLDialog):
    EXIT = 1
    RESUME = 2
    RESTART = 40

    def __init__(self, *args, **kwargs):
        # Copy off the key-word arguments
        # The non keyword arguments will be the ones passed to the main WindowXML
        self.resumetime = kwargs.pop('resumetime')
        self.selectionMade = VideoExtrasResumeWindow.EXIT

    # Static method to create the Window Dialog class
    @staticmethod
    def createVideoExtrasResumeWindow(resumetime=0):
        return VideoExtrasResumeWindow("script-videoextras-resume.xml", __addon__.getAddonInfo('path').decode("utf-8"), resumetime=resumetime)

    def onInit(self):
        # Need to populate the resume point
        resumeButton = self.getControl(VideoExtrasResumeWindow.RESUME)
        currentLabel = resumeButton.getLabel()
        newLabel = "%s %s" % (currentLabel, self.resumetime)

        # Reset the resume label with the addition of the time
        resumeButton.setLabel(newLabel)
        xbmcgui.WindowXMLDialog.onInit(self)

    def onClick(self, control):
        # Save the item that was clicked
        # Item ID 2 is resume
        # Item ID 40 is start from beginning
        self.selectionMade = control
        # If not resume or restart - we just want to exit without playing
        if not (self.isResume() or self.isRestart()):
            self.selectionMade = VideoExtrasResumeWindow.EXIT
        # Close the dialog after the selection
        self.close()

    def isResume(self):
        return self.selectionMade == VideoExtrasResumeWindow.RESUME

    def isRestart(self):
        return self.selectionMade == VideoExtrasResumeWindow.RESTART

    def isExit(self):
        return self.selectionMade == VideoExtrasResumeWindow.EXIT

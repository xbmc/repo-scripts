# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.videoextras')


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
        return VideoExtrasResumeWindow("script-videoextras-resume.xml", ADDON.getAddonInfo('path').decode("utf-8"), resumetime=resumetime)

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

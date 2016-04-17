# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

# Import the common settings
from settings import log

ADDON = xbmcaddon.Addon(id='script.suitability')
CWD = ADDON.getAddonInfo('path').decode("utf-8")


class SuitabilityViewer(xbmcgui.WindowXMLDialog):
    TITLE_LABEL_ID = 201
    VIEWER_CHANGE_BUTTON = 301
    CLOSE_BUTTON = 302
    SWITCH_BUTTON = 303

    def __init__(self, *args, **kwargs):
        self.isSwitchFlag = False
        self.isChangeViewerFlag = False
        self.switchText = kwargs.get('switchText', '')
        self.title = kwargs.get('title', '')
        xbmcgui.WindowXMLDialog.__init__(self)

    # Called when setting up the window
    def onInit(self):
        # Update the dialog to show the correct data
        labelControl = self.getControl(SuitabilityViewer.TITLE_LABEL_ID)
        labelControl.setLabel(self.title)

        # Set the label on the switch button
        switchButton = self.getControl(SuitabilityViewer.SWITCH_BUTTON)
        if self.switchText in [None, ""]:
            switchButton.setVisible(False)
        else:
            switchButton.setVisible(True)
            switchButton.setLabel(ADDON.getLocalizedString(self.switchText))

        xbmcgui.WindowXMLDialog.onInit(self)

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == SuitabilityViewer.CLOSE_BUTTON:
            log("SuitabilityViewer: Close click action received: %d" % controlID)
            self.close()
        elif controlID == SuitabilityViewer.SWITCH_BUTTON:
            log("SuitabilityViewer: Switch click action received: %d" % controlID)
            self.isSwitchFlag = True
            self.close()
        elif controlID == SuitabilityViewer.VIEWER_CHANGE_BUTTON:
            log("SuitabilityViewer: Change click action received: %d" % controlID)
            self.isChangeViewerFlag = True
            self.close()

    def close(self):
        log("SuitabilityViewer: Closing window")
        xbmcgui.WindowXMLDialog.close(self)

    def isSwitch(self):
        return self.isSwitchFlag

    def isChangeViewer(self):
        return self.isChangeViewerFlag


######################################
# Details listing screen
######################################
class SummaryViewer(SuitabilityViewer):

    def __init__(self, *args, **kwargs):
        details = kwargs.get('details', '')
        if details not in [None, ""]:
            self._setProperties(details)

        SuitabilityViewer.__init__(self, *args, **kwargs)

    @staticmethod
    def createSummaryViewer(switchText, title, details):
        return SummaryViewer("script-suitability-summary.xml", CWD, switchText=switchText, title=title, details=details)

    def close(self):
        log("SuitabilityViewer: Closing window")
        # Clear all the properties that were previously set
        i = 1
        while i < 9:
            xbmcgui.Window(10000).clearProperty("Suitability.%d.Section" % i)
            xbmcgui.Window(10000).clearProperty("Suitability.%d.Rating" % i)
            i = i + 1
        SuitabilityViewer.close(self)

    # Set all the values to display on the property screen
    def _setProperties(self, details):
        i = 1
        for entry in details:
            if i < 9:
                sectionTag = "Suitability.%d.Section" % i
                ratingTag = "Suitability.%d.Rating" % i
                xbmcgui.Window(10000).setProperty(sectionTag, entry["name"])

                ratingImage = "rating-%02d.png" % entry["score"]
                xbmcgui.Window(10000).setProperty(ratingTag, ratingImage)
            i = i + 1


######################################
# Details listing screen
######################################
class DetailViewer(SuitabilityViewer):
    TEXT_BOX_ID = 202

    def __init__(self, *args, **kwargs):
        self.content = kwargs.get('content', '')
        SuitabilityViewer.__init__(self, *args, **kwargs)

    @staticmethod
    def createDetailViewer(switchText, title, content):
        return DetailViewer("script-suitability-dialog.xml", CWD, switchText=switchText, title=title, content=content)

    # Called when setting up the window
    def onInit(self):
        # Fill in the text for the details
        textControl = self.getControl(DetailViewer.TEXT_BOX_ID)
        textControl.setText(self.content)

        SuitabilityViewer.onInit(self)

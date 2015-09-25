# -*- coding: utf-8 -*-
import xbmcgui
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='script.ebooks')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")


# Import the common settings
from settings import log
from settings import Settings


# Handles the simple text display window
class TextViewer(xbmcgui.WindowXMLDialog):
    TEXT_BOX_ID = 202
    TEXT_BOX_WHITE_BACKGROUND_ID = 204
    WHITE_BACKGROUND = 104
    TITLE_LABEL_ID = 201
    CLOSE_BUTTON = 302
    READ_BUTTON = 301
    PREVIOUS_BUTTON = 305
    NEXT_BUTTON = 304

    def __init__(self, *args, **kwargs):
        self.isClosedFlag = False
        self.markedAsRead = False
        self.nextSelected = False
        self.previousSelected = False
        self.textControlId = TextViewer.TEXT_BOX_ID
        self.title = kwargs.get('title', '')
        self.content = kwargs.get('content', '')
        self.isFirstChapter = kwargs.get('firstChapter', False)
        self.isLastChapter = kwargs.get('lastChapter', False)
        xbmcgui.WindowXMLDialog.__init__(self)

    @staticmethod
    def createTextViewer(title, content, isFirstChapter, isLastChapter):
        return TextViewer("script-ebook-text-window.xml", __cwd__, title=title, content=content, firstChapter=isFirstChapter, lastChapter=isLastChapter)

    # Called when setting up the window
    def onInit(self):
        # Check if the user wants a white background
        if Settings.useWhiteBackground():
            xbmcgui.Window(10000).setProperty("EBooks_WhiteBackground", "true")
            self.textControlId = TextViewer.TEXT_BOX_WHITE_BACKGROUND_ID
        else:
            xbmcgui.Window(10000).clearProperty("EBooks_WhiteBackground")
            self.textControlId = TextViewer.TEXT_BOX_ID

        # Update the dialog to show the correct data
        self.updateScreen(self.title, self.content, self.isFirstChapter, self.isLastChapter)
        xbmcgui.WindowXMLDialog.onInit(self)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        # actioncodes from https://github.com/xbmc/xbmc/blob/master/xbmc/input/Key.h
        ACTION_PREVIOUS_MENU = 10
        ACTION_NAV_BACK = 92
        ACTION_PAGE_UP = 5
        ACTION_PAGE_DOWN = 6

        if (action == ACTION_PREVIOUS_MENU) or (action == ACTION_NAV_BACK):
            log("TextViewer: Close Action received: %s" % str(action.getId()))
            self.close()
        elif action == ACTION_PAGE_UP:
            log("TextViewer: Page Up Action received: %s" % str(action.getId()))
            # Page up is going to the previous page
            self.onClick(TextViewer.PREVIOUS_BUTTON)
        elif action == ACTION_PAGE_DOWN:
            log("TextViewer: Page Down Action received: %s" % str(action.getId()))
            # Page down is going to the next page
            self.onClick(TextViewer.NEXT_BUTTON)

    def onClick(self, controlID):
        # Play button has been clicked
        if controlID == TextViewer.CLOSE_BUTTON:
            log("TextViewer: Close click action received: %d" % controlID)
            self.close()
        elif controlID == TextViewer.READ_BUTTON:
            log("TextViewer: Mark as read action received: %d" % controlID)
            self.markedAsRead = True
            self.close()
        elif controlID == TextViewer.NEXT_BUTTON:
            log("TextViewer: Request to view next chapter: %d" % controlID)
            self.nextSelected = True
            # Check if we should mark this chapter as read when we navigate to the next one
            if Settings.isMarkReadWhenNavToNextChapter():
                self.markedAsRead = True
        elif controlID == TextViewer.PREVIOUS_BUTTON:
            log("TextViewer: Request to view previous chapter: %d" % controlID)
            self.previousSelected = True

    def close(self):
        log("TextViewer: Closing window")
        self.isClosedFlag = True
        xbmcgui.WindowXMLDialog.close(self)
        xbmcgui.Window(10000).clearProperty("EBooks_WhiteBackground")

    def isClosed(self):
        return self.isClosedFlag

    def isRead(self):
        return self.markedAsRead

    def isNext(self):
        return self.nextSelected

    def isPrevious(self):
        return self.previousSelected

    def updateScreen(self, title, content, firstChapter=True, lastChapter=True):
        # If new data is being displayed, reset the status flags
        self.markedAsRead = False
        self.nextSelected = False
        self.previousSelected = False

        textControl = self.getControl(self.textControlId)
        textControl.setText(content)

        labelControl = self.getControl(TextViewer.TITLE_LABEL_ID)
        labelControl.setLabel(title)

        previousControl = self.getControl(TextViewer.PREVIOUS_BUTTON)
        if firstChapter:
            previousControl.setVisible(False)
        else:
            previousControl.setVisible(True)

        nextControl = self.getControl(TextViewer.NEXT_BUTTON)
        if lastChapter:
            nextControl.setVisible(False)
        else:
            nextControl.setVisible(True)

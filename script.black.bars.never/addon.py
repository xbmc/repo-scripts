import os
import sys

import xbmc
import xbmcaddon
import xbmcgui
import soupsieve

from imdb import getOriginalAspectRatio

monitor = xbmc.Monitor()
capture = xbmc.RenderCapture()
player = xbmc.Player()

CaptureWidth = 48
CaptureHeight = 54


def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)


class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

        if "toggle" in sys.argv:
            if xbmcgui.Window(10000).getProperty("blackbarsnever_status") == "on":
                self.showOriginal()
            else:
                self.abolishBlackBars()

    def onAVStarted(self):
        if xbmcaddon.Addon().getSetting("automatically_execute") == "true":
            self.abolishBlackBars()
        else:
            self.showOriginal()

    def CaptureFrame(self):
        capture.capture(CaptureWidth, CaptureHeight)
        capturedImage = capture.getImage(2000)
        return capturedImage

    ##############
    #
    # LineColorLessThan
    #    _bArray: byte Array that contains the data we want to test
    #    _lineStart: where to start testing
    #    _lineCount: how many lines to test
    #    _threshold: value to determine testing
    # returns: True False
    ###############

    def LineColorLessThan(self, _bArray, _lineStart, _lineCount, _threshold):
        __sliceStart = _lineStart * CaptureWidth * 4
        __sliceEnd = (_lineStart + _lineCount) * CaptureWidth * 4

        # zero out the alpha channel
        i = __sliceStart + 3
        while i < __sliceEnd:
            _bArray[i] &= 0x00
            i += 4

        __imageLine = _bArray[__sliceStart:__sliceEnd]
        __result = all([v < _threshold for v in __imageLine])

        return __result

    ###############
    #
    # GetAspectRatioFromFrame
    #   - returns Aspect ratio * 100 (i.e. 2.35 = 235)
    #   Detects hardcoded black bars
    ###############

    def GetAspectRatioFromFrame(self):
        __aspect_ratio = int((capture.getAspectRatio() + 0.005) * 100)
        __threshold = 25

        line1 = "Interim Aspect Ratio = " + str(__aspect_ratio)
        xbmc.log(line1, level=xbmc.LOGINFO)

        # screen capture and test for an image that is not dark in the 2.40
        # aspect ratio area. keep on capturing images until captured image
        # is not dark
        while True:
            __myimage = self.CaptureFrame()

            xbmc.log(line1, level=xbmc.LOGINFO)

            __middleScreenDark = self.LineColorLessThan(__myimage, 7, 2, __threshold)
            if __middleScreenDark == False:
                # xbmc.sleep(1000)
                break
            else:
                pass
                # xbmc.sleep(1000)

        # Capture another frame. after we have waited for transitions
        # __myimage = self.CaptureFrame()
        __ar185 = self.LineColorLessThan(__myimage, 0, 1, __threshold)
        __ar200 = self.LineColorLessThan(__myimage, 1, 3, __threshold)
        __ar235 = self.LineColorLessThan(__myimage, 1, 5, __threshold)

        if __ar235 == True:
            __aspect_ratio = 235

        elif __ar200 == True:
            __aspect_ratio = 200

        elif __ar185 == True:
            __aspect_ratio = 185

        return __aspect_ratio

    def abolishBlackBars(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "on")
        # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

        original_aspect_ratio = None
        android_workaround = (
            xbmcaddon.Addon().getSetting("android_workaround") == "true"
        )

        imdb_number = xbmc.getInfoLabel("VideoPlayer.IMDBNumber")
        if player.getVideoInfoTag().getMediaType() == "episode":
            # media is a TV show
            title = player.getVideoInfoTag().getTVShowTitle()
        else:
            # media is probably a film
            title = player.getVideoInfoTag().getTitle()
            if not title:
                title = player.getVideoInfoTag().getOriginalTitle()
            if not title:
                title = (
                    os.path.basename(player.getVideoInfoTag().getFilenameAndPath())
                    .split("/")[-1]
                    .split(".", 1)[0]
                )

        original_aspect_ratio = getOriginalAspectRatio(title, imdb_number=imdb_number)

        if isinstance(original_aspect_ratio, list):
            # media has multiple aspect ratios, show unaltered and let user do manual intervention
            notify("Multiple aspect ratios detected")
        else:
            if android_workaround and original_aspect_ratio:
                aspect_ratio = int(original_aspect_ratio)

                self.doStiaff(aspect_ratio)
            else:
                aspect_ratio = self.GetAspectRatioFromFrame()
                self.doStiaff(aspect_ratio)

    def doStiaff(self, ratio):
        aspect_ratio = ratio
        aspect_ratio2 = int((capture.getAspectRatio() + 0.005) * 100)

        window_id = xbmcgui.getCurrentWindowId()
        line1 = (
            "Calculated Aspect Ratio = "
            + str(aspect_ratio)
            + " "
            + "Player Aspect Ratio = "
            + str(aspect_ratio2)
        )

        xbmc.log(line1, level=xbmc.LOGINFO)

        if aspect_ratio > 178:
            zoom_amount = aspect_ratio / 178
        else:
            zoom_amount = 1.0

        # zoom in a sort of animated way, isn't working for now
        iterations = (zoom_amount - 1) / 0.01
        # for x in range(iterations):
        if (aspect_ratio > 178) and (aspect_ratio2 == 178):
            # this is 16:9 and has hard coded black bars
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
                + str(zoom_amount)
                + ' }}, "id": 1}'
            )
            notify("Black Bars were detected. Zoomed {:0.2f}".format(zoom_amount))
        elif aspect_ratio > 178:
            # this is an aspect ratio wider than 16:9, no black bars, we assume a 16:9 (1.77:1) display
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": '
                + str(zoom_amount)
                + ' }}, "id": 1}'
            )
            if zoom_amount <= 1.02:
                notify(
                    "Wide screen was detected. Slightly zoomed {:0.2f}".format(
                        zoom_amount
                    )
                )
            elif zoom_amount > 1.02:
                notify("Wide screen was detected. Zoomed {: 0.2f}".format(zoom_amount))

    def showOriginal(self):
        xbmcgui.Window(10000).setProperty("blackbarsnever_status", "off")
        # notify(xbmcgui.Window(10000).getProperty('blackbarsnever_status'))

        xbmc.executeJSONRPC(
            '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": 1.0'
            + ' }}, "id": 1}'
        )
        notify("Showing original aspect ratio")


p = Player()

while not monitor.abortRequested():
    # Sleep/wait for abort for 10 seconds
    if monitor.waitForAbort(10):
        # Abort was requested while waiting. We should exit
        break

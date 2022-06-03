import xbmc
import xbmcaddon
import xbmcgui

import time
import json
import sys
import os.path

addon = xbmcaddon.Addon()
addonversion = addon.getAddonInfo('version')
addonid = addon.getAddonInfo('id')
addonname = addon.getAddonInfo('name')
addonPath = addon.getAddonInfo('path')

monitor = xbmc.Monitor()

LOG_NONE = 0
LOG_ERROR = 1
LOG_INFO = 2
LOG_DEBUG = 3

capture = xbmc.RenderCapture()
myplayer = xbmc.Player()

CaptureWidth = 48
CaptureHeight = 54

messages = []


class Player(xbmc.Player):
    def __init__(self):
        xbmc.Player.__init__(self)

    def onAVStarted(self):
        xbmc.log("AV started")
        self.abolishBlackBars()

    def CaptureFrame(self):
        capture.capture(CaptureWidth, CaptureHeight)
        capturedImage = capture.getImage(1000)
        return capturedImage

    def CaptureFrame_new(self):
        capture.capture(CaptureWidth, CaptureHeight)
        capturedImage = capture.getImage(1000)
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
        while (i < __sliceEnd):
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
        __aspectratio = int((capture.getAspectRatio() + 0.005) * 100)
        __threshold = 25

        # Analyze the frame only if the ratio is 16:9. 2.35 ratio files
        # would not have black bars hardcoded.
        if 140 < __aspectratio < 180:
            # screen capture and test for an image that is not dark in the 2.40
            # aspect ratio area. keep on capturing images until captured image
            # is not dark
            while (True):
                __myimage = self.CaptureFrame()
                __middleScreenDark = self.LineColorLessThan(
                    __myimage, 7, 2, __threshold)
                if __middleScreenDark == False:
                    xbmc.sleep(200)
                    break
                else:
                    xbmc.sleep(100)

            # Capture another frame. after we have waited for transitions
            __myimage = self.CaptureFrame()
            __ar185 = self.LineColorLessThan(__myimage, 0, 1, __threshold)
            __ar200 = self.LineColorLessThan(__myimage, 1, 3, __threshold)
            __ar235 = self.LineColorLessThan(__myimage, 1, 5, __threshold)

            if (__ar235 == True):
                __aspectratio = 235

            elif (__ar200 == True):
                __aspectratio = 200

            elif (__ar185 == True):
                __aspectratio = 185

        return __aspectratio

    def abolishBlackBars(self):
        aspectratio = self.GetAspectRatioFromFrame()
        aspectratio2 = int((capture.getAspectRatio() + 0.005) * 100)

        _info = xbmc.getInfoLabel('Player.Process(VideoDAR)')
        _info2 = xbmc.getInfoLabel('Player.Process(videoheight)')
        window_id = xbmcgui.getCurrentWindowId()
        line1 = 'Calculated Aspect Ratio = ' + \
            str(aspectratio) + ' ' + 'Player Aspect Ratio = ' + str(aspectratio2)

        xbmc.log(line1, level=xbmc.LOGDEBUG)

        zoom_amount = (aspectratio / aspectratio2)

        # zoom in a sort of animated way, isn't working for now
        iterations = (zoom_amount - 1) / 0.01
        # for x in range(iterations):
        if str(zoom_amount) == "1.0":
            zoom_amount = (aspectratio / 177)
            # this is an aspect ratio wider than 16:9, no black bars, we assume a 16:9 (1.77:1) display
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}')
            if (zoom_amount <= 1.02):
                messages.append(
                    "Wide screen was detected. Slightly zoomed " + str(zoom_amount))
            elif (zoom_amount > 1.02):
                messages.append(
                    "Wide screen was detected. Zoomed " + str(zoom_amount))
        else:
            # this is 16:9 and has hard coded black bars
            xbmc.executeJSONRPC(
                '{"jsonrpc": "2.0", "method": "Player.SetViewMode", "params": {"viewmode": {"zoom": ' + str(zoom_amount) + ' }}, "id": 1}')
            messages.append(
                "Black Bars were detected. Zoomed " + str(zoom_amount))
        # time.sleep(0.1)

    def log(self, level, msg):
        if level <= settings.logLevel:
            if level == LOG_ERROR:
                l = xbmc.LOGERROR
            elif level == LOG_INFO:
                l = xbmc.LOGINFO
            elif level == LOG_DEBUG:
                l = xbmc.LOGDEBUG
            xbmc.log(str(msg), l)


p = Player()

while not monitor.abortRequested():
    # Sleep/wait for abort for 10 seconds
    if monitor.waitForAbort(10):
        # Abort was requested while waiting. We should exit
        break

    if (len(messages) > 0):
        xbmcgui.Dialog().notification("header", messages[0], None, 5000)

        messages.pop(0)

import os
import datetime

import xbmc
import xbmcgui

from strings import *

KEY_LEFT = 1
KEY_RIGHT = 2
KEY_UP = 3
KEY_DOWN = 4
KEY_PAGE_UP = 5
KEY_PAGE_DOWN = 6
KEY_SELECT = 7
KEY_BACK = 9
KEY_MENU = 10
KEY_INFO = 11
KEY_NAV_BACK = 92
KEY_CONTEXT_MENU = 117

CHANNELS_PER_PAGE = 9

CELL_HEIGHT = 50
CELL_WIDTH = 275
CELL_WIDTH_CHANNELS = 180

HALF_HOUR = datetime.timedelta(minutes = 30)

ADDON = xbmcaddon.Addon(id = 'script.tvguide')
TEXTURE_BUTTON_NOFOCUS = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('path')), 'resources', 'skins', 'Default', 'media', 'tvguide-program-grey.png')
TEXTURE_BUTTON_FOCUS = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('path')), 'resources', 'skins', 'Default', 'media', 'tvguide-program-grey-focus.png')
TEXTURE_BUTTON_NOFOCUS_NOTIFY = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('path')), 'resources', 'skins', 'Default', 'media', 'tvguide-program-red.png')
TEXTURE_BUTTON_FOCUS_NOTIFY = os.path.join(xbmc.translatePath(ADDON.getAddonInfo('path')), 'resources', 'skins', 'Default', 'media', 'tvguide-program-red-focus.png')

class TVGuide(xbmcgui.WindowXML):
    C_MAIN_TITLE = 4020
    C_MAIN_TIME = 4021
    C_MAIN_DESCRIPTION = 4022
    C_MAIN_IMAGE = 4023
    C_MAIN_LOADING = 4200
    C_MAIN_LOADING_PROGRESS = 4201
    C_MAIN_BACKGROUND = 4600

    def __new__(cls, source):
        return super(TVGuide, cls).__new__(cls, 'script-tvguide-main.xml', ADDON.getAddonInfo('path'))

    def __init__(self,  source):
        """
        @param source: the source of EPG data
        @type source: source.Source
        """
        super(TVGuide, self).__init__()
        self.source = source
        self.controlToProgramMap = {}
        self.focusX = 0
        self.page = 0

        # find nearest half hour
        self.date = datetime.datetime.today()
        self.date -= datetime.timedelta(minutes = self.date.minute % 30)

    def onInit(self):
        self.onRedrawEPG(0, self.date)
        self.getControl(self.C_MAIN_IMAGE).setImage('tvguide-logo-%s.png' % self.source.KEY)

    def onAction(self, action):
        if action.getId() in [KEY_BACK, KEY_MENU, KEY_NAV_BACK]:
            self.close()
            return

        try:
            controlInFocus = self.getFocus()
            (left, top) = controlInFocus.getPosition()
            currentX = left + (controlInFocus.getWidth() / 2)
            currentY = top + (controlInFocus.getHeight() / 2)
        except TypeError:
            currentX = None
            currentY = None

        control = None

        if action.getId() == KEY_LEFT:
            control = self._left(currentX, currentY)
        elif action.getId() == KEY_RIGHT:
            control = self._right(currentX, currentY)
        elif action.getId() == KEY_UP:
            control = self._up(currentY)
        elif action.getId() == KEY_DOWN:
            control = self._down(currentY)
        elif action.getId() == KEY_PAGE_UP:
            control = self._pageUp()
        elif action.getId() == KEY_PAGE_DOWN:
            control = self._pageDown()

        if control is not None:
            self.setFocus(control)


    def onClick(self, controlId):
        program = self.controlToProgramMap[controlId]

        d = PopupMenu(program)
        d.doModal()
        buttonClicked = d.buttonClicked
        del d

        if buttonClicked == PopupMenu.C_POPUP_PLAY:
            program.channel.play()

    def onFocus(self, controlId):
        controlInFocus = self.getControl(controlId)
        (left, top) = controlInFocus.getPosition()
        if left > self.focusX or left + controlInFocus.getWidth() < self.focusX:
            self.focusX = left

        program = self.controlToProgramMap[controlId]

        self.getControl(self.C_MAIN_TITLE).setLabel('[B]%s[/B]' % program.title)
        self.getControl(self.C_MAIN_TIME).setLabel('[B]%s - %s[/B]' % (program.startDate.strftime('%H:%M'), program.endDate.strftime('%H:%M')))
        self.getControl(self.C_MAIN_DESCRIPTION).setText(program.description)

        if program.imageSmall is not None:
            self.getControl(self.C_MAIN_IMAGE).setImage(program.imageSmall)

        if ADDON.getSetting('program.background.enabled') == 'true' and program.imageLarge is not None:
            self.getControl(self.C_MAIN_BACKGROUND).setImage(program.imageLarge)

    def _left(self, currentX, currentY):
        control = self._findControlOnLeft(currentX, currentY)
        if control is None:
            self.date -= datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.page, self.date)
            control = self._findControlOnLeft(1280, currentY)

        (left, top) = control.getPosition()
        self.focusX = left
        return control

    def _right(self, currentX, currentY):
        control = self._findControlOnRight(currentX, currentY)
        if control is None:
            self.date += datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.page, self.date)
            control = self._findControlOnRight(0, currentY)

        (left, top) = control.getPosition()
        self.focusX = left
        return control

    def _up(self, currentY):
        control = self._findControlAbove(currentY)
        if control is None:
            self.page = self.onRedrawEPG(self.page - 1, self.date)
            control = self._findControlAbove(720)
        return control

    def _down(self, currentY):
        control = self._findControlBelow(currentY)
        if control is None:
            self.page = self.onRedrawEPG(self.page + 1, self.date)
            control = self._findControlBelow(0)
        return control

    def _pageUp(self):
        self.page = self.onRedrawEPG(self.page - 1, self.date)
        return self._findControlAbove(720)

    def _pageDown(self):
        self.page = self.onRedrawEPG(self.page+ 1, self.date)
        return self._findControlBelow(0)

    def onRedrawEPG(self, page, startTime, autoChangeFocus = True):
        oldControltoProgramMap = self.controlToProgramMap.copy()
        self.controlToProgramMap.clear()

        progressControl = self.getControl(self.C_MAIN_LOADING_PROGRESS)
        progressControl.setPercent(0)
        self.getControl(self.C_MAIN_LOADING).setVisible(True)

        # move timebar to current time
        timeDelta = datetime.datetime.today() - self.date
        c = self.getControl(4100)
        (x, y) = c.getPosition()
        c.setPosition(self._secondsToXposition(timeDelta.seconds), y)

        self.getControl(4500).setVisible(not(self.source.hasChannelIcons()))
        self.getControl(4501).setVisible(self.source.hasChannelIcons())

        # date and time row
        self.getControl(4000).setLabel(self.date.strftime('%a, %d. %b'))
        for col in range(1, 5):
            self.getControl(4000 + col).setLabel(startTime.strftime('%H:%M'))
            startTime += HALF_HOUR

        # channels
        channels = self.source.getChannelList()
        if channels is None:
            self.onEPGLoadError()
            return
        totalPages = len(channels) / CHANNELS_PER_PAGE
        if len(channels) % CHANNELS_PER_PAGE == 0:
            totalPages -= 1

        if page < 0:
            page = totalPages
        elif page > totalPages:
            page = 0

        channelStart = page * CHANNELS_PER_PAGE
        channelEnd = page * CHANNELS_PER_PAGE + CHANNELS_PER_PAGE

        controlsToAdd = list()
        for idx, channel in enumerate(channels[channelStart : channelEnd]):
            progressControl.setPercent(idx * 100 / CHANNELS_PER_PAGE)
            programs = self.source.getProgramList(channel)
            if programs is None:
                self.onEPGLoadError()
                return

            for program in programs:
                if program.endDate <= self.date:
                    continue

                startDelta = program.startDate - self.date
                stopDelta = program.endDate - self.date

                cellStart = self._secondsToXposition(startDelta.seconds)
                if startDelta.days < 0:
                    cellStart = CELL_WIDTH_CHANNELS
                cellWidth = self._secondsToXposition(stopDelta.seconds) - cellStart
                if cellStart + cellWidth > 1260:
                    cellWidth = 1260 - cellStart

                if cellWidth > 1:
                    control = xbmcgui.ControlButton(
                        cellStart,
                        60 + CELL_HEIGHT * idx,
                        cellWidth - 2,
                        CELL_HEIGHT - 2,
                        program.title,
                        noFocusTexture = TEXTURE_BUTTON_NOFOCUS,
                        focusTexture = TEXTURE_BUTTON_FOCUS
                    )

                    controlsToAdd.append([control, program])


        for controlId in oldControltoProgramMap:
            self.removeControl(self.getControl(controlId))

        # add program controls
        for control, program in controlsToAdd:
            self.addControl(control)
            self.controlToProgramMap[control.getId()] = program

        try:
            self.getFocus()
        except TypeError:
            if len(self.controlToProgramMap.keys()) > 0 and autoChangeFocus:
                self.setFocus(self.getControl(self.controlToProgramMap.keys()[0]))

        self.getControl(self.C_MAIN_LOADING).setVisible(False)

        # set channel logo or text
        channelsToShow = channels[channelStart : channelEnd]
        for idx in range(0, CHANNELS_PER_PAGE):
            if idx >= len(channelsToShow):
                self.getControl(4110 + idx).setImage('')
                self.getControl(4010 + idx).setLabel('')
            else:
                channel = channelsToShow[idx]
                if self.source.hasChannelIcons() and channel.logo is not None:
                    self.getControl(4110 + idx).setImage(channel.logo)
                else:
                    self.getControl(4010 + idx).setLabel(channel.title)

        return page

    def onEPGLoadError(self):
        self.getControl(self.C_MAIN_LOADING).setVisible(False)
        xbmcgui.Dialog().ok(strings(LOAD_ERROR_TITLE), strings(LOAD_ERROR_LINE1), strings(LOAD_ERROR_LINE2))
        self.close()

    def _secondsToXposition(self, seconds):
        return CELL_WIDTH_CHANNELS + (seconds * CELL_WIDTH / 1800)

    def _findControlOnRight(self, currentX, currentY):
        distanceToNearest = 10000
        nearestControl = None

        for controlId in self.controlToProgramMap.keys():
            control = self.getControl(controlId)
            (left, top) = control.getPosition()
            x = left + (control.getWidth() / 2)
            y = top + (control.getHeight() / 2)

            if currentX < x and currentY == y:
                distance = abs(currentX - x)
                if distance < distanceToNearest:
                    distanceToNearest = distance
                    nearestControl = control

        return nearestControl


    def _findControlOnLeft(self, currentX, currentY):
        distanceToNearest = 10000
        nearestControl = None

        for controlId in self.controlToProgramMap.keys():
            control = self.getControl(controlId)
            (left, top) = control.getPosition()
            x = left + (control.getWidth() / 2)
            y = top + (control.getHeight() / 2)

            if currentX > x and currentY == y:
                distance = abs(currentX - x)
                if distance < distanceToNearest:
                    distanceToNearest = distance
                    nearestControl = control

        return nearestControl

    def _findControlBelow(self, currentY):
        nearestControl = None

        for controlId in self.controlToProgramMap.keys():
            control = self.getControl(controlId)
            (leftEdge, top) = control.getPosition()
            y = top + (control.getHeight() / 2)

            if currentY < y:
                rightEdge = leftEdge + control.getWidth()
                if(leftEdge <= self.focusX < rightEdge
                   and (nearestControl is None or nearestControl.getPosition()[1] > top)):
                    nearestControl = control

        return nearestControl

    def _findControlAbove(self, currentY):
        nearestControl = None

        for controlId in self.controlToProgramMap.keys():
            control = self.getControl(controlId)
            (leftEdge, top) = control.getPosition()
            y = top + (control.getHeight() / 2)

            if currentY > y:
                rightEdge = leftEdge + control.getWidth()
                if(leftEdge <= self.focusX < rightEdge
                   and (nearestControl is None or nearestControl.getPosition()[1] < top)):
                    nearestControl = control

        return nearestControl



class PopupMenu(xbmcgui.WindowXMLDialog):
    C_POPUP_PLAY = 4000
    C_POPUP_CANCEL = 4001

    def __new__(cls, program):
        return super(PopupMenu, cls).__new__(cls, 'script-tvguide-menu.xml', ADDON.getAddonInfo('path'))

    def __init__(self, program):
        super(PopupMenu, self).__init__()
        self.program = program
        self.buttonClicked = None

    def onInit(self):
        playControl = self.getControl(self.C_POPUP_PLAY)
        playControl.setLabel(strings(WATCH_CHANNEL, self.program.channel.title))
        if not self.program.channel.isPlayable():
            playControl.setEnabled(False)
            self.setFocusId(self.C_POPUP_CANCEL)

    def onAction(self, action):
        if action.getId() in [KEY_BACK, KEY_MENU, KEY_NAV_BACK]:
            self.close()
            return

    def onClick(self, controlId):
        self.buttonClicked = controlId
        self.close()

    def onFocus(self, controlId):
        pass

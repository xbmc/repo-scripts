#
#      Copyright (C) 2012 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import os
import datetime

import xbmc
import xbmcgui

import source
from strings import *
import buggalo

ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_UP = 3
ACTION_DOWN = 4
ACTION_PAGE_UP = 5
ACTION_PAGE_DOWN = 6
ACTION_SELECT_ITEM = 7
ACTION_PARENT_DIR = 9
ACTION_PREVIOUS_MENU = 10
ACTION_SHOW_INFO = 11
ACTION_NEXT_ITEM = 14
ACTION_PREV_ITEM = 15


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

    def __new__(cls, source, notification):
        return super(TVGuide, cls).__new__(cls, 'script-tvguide-main.xml', ADDON.getAddonInfo('path'))

    def __init__(self,  source, notification):
        """
        @param source: the source of EPG data
        @type source: source.Source
        @type notification: notification.Notification
        """
        super(TVGuide, self).__init__()
        self.source = source
        self.notification = notification
        self.controlToProgramMap = {}
        self.focusX = 0
        self.page = 0

        # find nearest half hour
        self.viewStartDate = datetime.datetime.today()
        self.viewStartDate -= datetime.timedelta(minutes = self.viewStartDate.minute % 30)

    def onInit(self):
        try:
            self.onRedrawEPG(0, self.viewStartDate)
            self.getControl(self.C_MAIN_IMAGE).setImage('tvguide-logo-%s.png' % self.source.KEY)
        except Exception:
            buggalo.onExceptionRaised()

    def onAction(self, action):
        try:
            if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK]:
                self.close()
                return

            control = None
            controlInFocus = None
            try:
                controlInFocus = self.getFocus()
                (left, top) = controlInFocus.getPosition()
                currentX = left + (controlInFocus.getWidth() / 2)
                currentY = top + (controlInFocus.getHeight() / 2)
            except TypeError:
                currentX = None
                currentY = None

            if action.getId() == ACTION_LEFT:
                control = self._left(currentX, currentY)
            elif action.getId() == ACTION_RIGHT:
                control = self._right(currentX, currentY)
            elif action.getId() == ACTION_UP:
                control = self._up(currentY)
            elif action.getId() == ACTION_DOWN:
                control = self._down(currentY)
            elif action.getId() == ACTION_NEXT_ITEM:
                control= self._nextDay( currentY)
            elif action.getId() == ACTION_PREV_ITEM:
                control= self._previousDay(currentY)
            elif action.getId() == ACTION_PAGE_UP:
                control = self._pageUp()
            elif action.getId() == ACTION_PAGE_DOWN:
                control = self._pageDown()
            elif action.getId() == KEY_CONTEXT_MENU and controlInFocus is not None:
                program = self.controlToProgramMap[controlInFocus.getId()]
                self._showContextMenu(program, controlInFocus)

            if control is not None:
                self.setFocus(control)

        except Exception:
            buggalo.onExceptionRaised()


    def onClick(self, controlId):
        try:
            program = self.controlToProgramMap[controlId]
            if self.source.isPlayable(program.channel):
                self.source.play(program.channel)
            else:
                self._showContextMenu(program, self.getControl(controlId))
        except Exception:
            buggalo.onExceptionRaised()

    def _showContextMenu(self, program, control):
        isNotificationRequiredForProgram = self.notification.isNotificationRequiredForProgram(program)

        d = PopupMenu(self.source, program, not isNotificationRequiredForProgram, self.source.hasChannelIcons())
        d.doModal()
        buttonClicked = d.buttonClicked
        del d

        if buttonClicked == PopupMenu.C_POPUP_REMIND:
            if isNotificationRequiredForProgram:
                self.notification.delProgram(program)
            else:
                self.notification.addProgram(program)

            (left, top) = control.getPosition()
            y = top + (control.getHeight() / 2)
            self.onRedrawEPG(self.page, self.viewStartDate, autoChangeFocus = False)
            self.setFocus(self._findControlOnRight(left, y))

        elif buttonClicked == PopupMenu.C_POPUP_CHOOSE_STRM:
            filename = xbmcgui.Dialog().browse(1, ADDON.getLocalizedString(30304), 'video', '.strm')
            if filename:
                self.source.setCustomStreamUrl(program.channel, filename)

        elif buttonClicked == PopupMenu.C_POPUP_PLAY:
            if self.source.isPlayable(program.channel):
                self.source.play(program.channel)


    def onFocus(self, controlId):
        try:
            try:
                controlInFocus = self.getControl(controlId)
            except TypeError:
                return

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

        except Exception:
            buggalo.onExceptionRaised()

    def _left(self, currentX, currentY):
        control = self._findControlOnLeft(currentX, currentY)
        if control is None:
            self.viewStartDate -= datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.page, self.viewStartDate)
            control = self._findControlOnLeft(1280, currentY)

        if control is not None:
            (left, top) = control.getPosition()
            self.focusX = left
        return control

    def _right(self, currentX, currentY):
        control = self._findControlOnRight(currentX, currentY)
        if control is None:
            self.viewStartDate += datetime.timedelta(hours = 2)
            self.onRedrawEPG(self.page, self.viewStartDate)
            control = self._findControlOnRight(0, currentY)

        if control is not None:
            (left, top) = control.getPosition()
            self.focusX = left
        return control

    def _up(self, currentY):
        control = self._findControlAbove(currentY)
        if control is None:
            self.page = self.onRedrawEPG(self.page - 1, self.viewStartDate)
            control = self._findControlAbove(720)
        return control

    def _down(self, currentY):
        control = self._findControlBelow(currentY)
        if control is None:
            self.page = self.onRedrawEPG(self.page + 1, self.viewStartDate)
            control = self._findControlBelow(0)
        return control

    def _nextDay(self, currentY):
        self.viewStartDate += datetime.timedelta(days = 1)
        self.page = self.onRedrawEPG(self.page, self.viewStartDate)
        return self._findControlOnLeft(0, currentY)

    def _previousDay(self, currentY):
        self.viewStartDate -= datetime.timedelta(days = 1)
        self.page = self.onRedrawEPG(self.page, self.viewStartDate)
        return self._findControlOnLeft(1280, currentY)

    def _pageUp(self):
        self.page = self.onRedrawEPG(self.page - 1, self.viewStartDate)
        return self._findControlAbove(720)

    def _pageDown(self):
        self.page = self.onRedrawEPG(self.page+ 1, self.viewStartDate)
        return self._findControlBelow(0)

    def onRedrawEPG(self, page, startTime, autoChangeFocus = True):
        oldControltoProgramMap = self.controlToProgramMap.copy()
        self.controlToProgramMap.clear()

        progressControl = self.getControl(self.C_MAIN_LOADING_PROGRESS)
        progressControl.setPercent(1)
        self.getControl(self.C_MAIN_LOADING).setVisible(True)

        # move timebar to current time
        timeDelta = datetime.datetime.today() - self.viewStartDate
        c = self.getControl(4100)
        (x, y) = c.getPosition()
        c.setPosition(self._secondsToXposition(timeDelta.seconds), y)

        self.getControl(4500).setVisible(not(self.source.hasChannelIcons()))
        self.getControl(4501).setVisible(self.source.hasChannelIcons())

        # date and time row
        self.getControl(4000).setLabel(self.viewStartDate.strftime('%a, %d. %b'))
        for col in range(1, 5):
            self.getControl(4000 + col).setLabel(startTime.strftime('%H:%M'))
            startTime += HALF_HOUR

        # channels
        try:
            channels = self.source.getChannelList()
        except source.SourceException as ex:
            print ex
            self.onEPGLoadError()
            return

        totalPages = len(channels) / CHANNELS_PER_PAGE
        if not len(channels) % CHANNELS_PER_PAGE:
            totalPages -= 1

        if page < 0:
            page = totalPages
        elif page > totalPages:
            page = 0

        channelStart = page * CHANNELS_PER_PAGE
        channelEnd = page * CHANNELS_PER_PAGE + CHANNELS_PER_PAGE

        viewEndDate = self.viewStartDate + datetime.timedelta(hours = 2)
        controlsToAdd = list()
        viewChannels = channels[channelStart : channelEnd]
        for idx, channel in enumerate(viewChannels):
            progressControl.setPercent((idx * 100 / len(viewChannels)) + 1)

            # Loads programs for yesterday as well to compensate for midnight
            programs = list()
            try:
                programList = self.source.getProgramList(channel, self.viewStartDate)
                if programList:
                    programs += programList
                if not isinstance(self.source, source.XMLTVSource):
                    programList = self.source.getProgramList(channel, self.viewStartDate - datetime.timedelta(days = 1))
                    if programList:
                        programs += programList
            except source.SourceException as ex:
                print ex
                self.onEPGLoadError()
                return

            if programs is None:
                self.onEPGLoadError()
                return

            for program in programs:
                if program.endDate <= self.viewStartDate or program.startDate >= viewEndDate:
                    # Program is out of bounds for current view
                    continue

                startDelta = program.startDate - self.viewStartDate
                stopDelta = program.endDate - self.viewStartDate

                cellStart = self._secondsToXposition(startDelta.seconds)
                if startDelta.days < 0:
                    cellStart = CELL_WIDTH_CHANNELS
                cellWidth = self._secondsToXposition(stopDelta.seconds) - cellStart
                if cellStart + cellWidth > 1260:
                    cellWidth = 1260 - cellStart

                if cellWidth > 1:
                    if self.notification.isNotificationRequiredForProgram(program):
                        noFocusTexture = TEXTURE_BUTTON_NOFOCUS_NOTIFY
                        focusTexture = TEXTURE_BUTTON_FOCUS_NOTIFY
                    else:
                        noFocusTexture = TEXTURE_BUTTON_NOFOCUS
                        focusTexture = TEXTURE_BUTTON_FOCUS

                    if cellWidth < 25:
                        title = '' # Text will overflow outside the button if it is to narrow
                    else:
                        title = program.title

                    control = xbmcgui.ControlButton(
                        cellStart,
                        60 + CELL_HEIGHT * idx,
                        cellWidth - 2,
                        CELL_HEIGHT - 2,
                        title,
                        noFocusTexture = noFocusTexture,
                        focusTexture = focusTexture
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
    C_POPUP_CHOOSE_STRM = 4001
    C_POPUP_REMIND = 4002
    C_POPUP_CHANNEL_LOGO = 4100
    C_POPUP_CHANNEL_TITLE = 4101
    C_POPUP_PROGRAM_TITLE = 4102

    def __new__(cls, source, program, showRemind, hasChannelIcon):
        return super(PopupMenu, cls).__new__(cls, 'script-tvguide-menu.xml', ADDON.getAddonInfo('path'))

    def __init__(self, source, program, showRemind, hasChannelIcon):
        """

        @type source: source.Source
        @param program:
        @type program: source.Program
        @param showRemind:
        """
        super(PopupMenu, self).__init__()
        self.source = source
        self.program = program
        self.showRemind = showRemind
        self.buttonClicked = None
        self.hasChannelIcon = hasChannelIcon

    def onInit(self):
        try:
            playControl = self.getControl(self.C_POPUP_PLAY)
            remindControl = self.getControl(self.C_POPUP_REMIND)
            channelLogoControl = self.getControl(self.C_POPUP_CHANNEL_LOGO)
            channelTitleControl = self.getControl(self.C_POPUP_CHANNEL_TITLE)
            programTitleControl = self.getControl(self.C_POPUP_PROGRAM_TITLE)

            playControl.setLabel(strings(WATCH_CHANNEL, self.program.channel.title))
            if not self.source.isPlayable(self.program.channel):
                playControl.setEnabled(False)
                self.setFocusId(self.C_POPUP_CHOOSE_STRM)
            if self.source.getCustomStreamUrl(self.program.channel):
                chooseStrmControl = self.getControl(self.C_POPUP_CHOOSE_STRM)
                chooseStrmControl.setLabel(strings(REMOVE_STRM_FILE))

            if self.hasChannelIcon:
                channelLogoControl.setImage(self.program.channel.logo)
                channelTitleControl.setVisible(False)
            else:
                channelTitleControl.setLabel(self.program.channel.title)
                channelLogoControl.setVisible(False)

            programTitleControl.setLabel(self.program.title)

            if self.showRemind:
                remindControl.setLabel(strings(REMIND_PROGRAM))
            else:
                remindControl.setLabel(strings(DONT_REMIND_PROGRAM))

        except Exception:
            buggalo.onExceptionRaised()

    def onAction(self, action):
        try:
            if action.getId() in [ACTION_PARENT_DIR, ACTION_PREVIOUS_MENU, KEY_NAV_BACK, KEY_CONTEXT_MENU]:
                self.close()
                return
        except Exception:
            buggalo.onExceptionRaised()

    def onClick(self, controlId):
        try:
            if controlId == self.C_POPUP_CHOOSE_STRM and self.source.getCustomStreamUrl(self.program.channel):
                self.source.deleteCustomStreamUrl(self.program.channel)
                chooseStrmControl = self.getControl(self.C_POPUP_CHOOSE_STRM)
                chooseStrmControl.setLabel(strings(CHOOSE_STRM_FILE))

                print self.source.isPlayable(self.program.channel)
                if not self.source.isPlayable(self.program.channel):
                    playControl = self.getControl(self.C_POPUP_PLAY)
                    playControl.setEnabled(False)

            else:
                self.buttonClicked = controlId
                self.close()
        except Exception:
            buggalo.onExceptionRaised()

    def onFocus(self, controlId):
        pass

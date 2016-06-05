import os
import time
import xbmc
import xbmcgui
import kodigui
import actiondialog
import skin
import base
from lib import util

from lib import tablo
from lib.tablo import grid
from lib import player
from lib.util import T


WM = None

SKIN_PATH = skin.init()


class HalfHourData(object):
    def __init__(self):
        self.halfHour = None
        self.startHalfHour = None
        self.cutoff = None
        self.offsetHalfHours = 0
        self.update()

    def update(self):
        halfHour = self.getStartHalfHour()

        if halfHour == self.startHalfHour:
            return self

        self.decrementOffset()  # We've moved to the next half hour, but want to keep our position if we can

        self.startHalfHour = halfHour

        self.cutoff = halfHour + tablo.compat.datetime.timedelta(hours=24)

        self.updateOffsets()

        return self

    def updateOffsets(self):
        self.halfHour = self.startHalfHour + tablo.compat.datetime.timedelta(minutes=self.offsetHalfHours * 30)
        self.maxHalfHour = self.halfHour + tablo.compat.datetime.timedelta(minutes=120)

    def incrementOffset(self):
        if self.offsetHalfHours == 45:
            return False

        self.offsetHalfHours += 1
        self.updateOffsets()

        return True

    def decrementOffset(self):
        if self.offsetHalfHours <= 0:
            return False

        self.offsetHalfHours -= 1
        self.updateOffsets()

        return True

    def getStartHalfHour(self):
        n = tablo.api.now()
        return n - tablo.compat.datetime.timedelta(minutes=n.minute % 30, seconds=n.second, microseconds=n.microsecond)


class LiveTVWindow(kodigui.BaseWindow, util.CronReceiver):
    name = 'LIVETV'
    xmlFile = 'script-tablo-livetv-generated.xml'
    path = SKIN_PATH
    theme = 'Main'

    usesGenerate = True

    GRID_GROUP_ID = 45
    TIME_INDICATOR_ID = 51

    @classmethod
    @base.tabloErrorHandler
    def generate(cls):
        try:
            paths = tablo.API.guide.channels.get()
        except tablo.ConnectionError:
            msg = T(32157).format(tablo.API.device.displayName)
            WM.setError(msg)
            # xbmcgui.Dialog().ok('Connection Failure', msg)
            return False

        gen = EPGXMLGenerator(paths).create()
        new = cls.create()
        new.slotButtons = {}
        new.offButtons = {}
        new.chanLabelButtons = {}
        new.lastFocus = 100
        new.topRow = 0
        new.gen = gen
        return new

    def onFirstInit(self):
        self._showingDialog = False
        self.hhData = HalfHourData()

        self.baseY = self.getControl(45).getY()
        self.rowCount = len(self.gen.paths)
        self.rows = [[]] * len(self.gen.paths)
        self.channels = {}
        self.upDownDatetime = None
        self.tunerInUse = []
        self.nextTunerPoll = 0

        self.gridGroup = self.getControl(self.GRID_GROUP_ID)
        self.timeIndicator = self.getControl(self.TIME_INDICATOR_ID)

        self.grid = grid.Grid(util.PROFILE, self.channelUpdatedCallback)

        self.setTimesHeader()
        self.updateTimeIndicator()

        self.clearChannelColors()
        self.initEPG()
        self.getChannels()

        util.CRON.registerReceiver(self)

    def onReInit(self):
        if not self._showingDialog:
            self.grid.updatePending()

    def onAction(self, action):
        try:
            controlID = self.getFocusId()
            if action == xbmcgui.ACTION_MOVE_LEFT:
                self.setUpDownDatetime(controlID)

                if controlID in self.chanLabelButtons:
                    return self.guideLeft(True)
                elif controlID - 1 in self.chanLabelButtons:
                    return self.guideLeft()
            elif action == xbmcgui.ACTION_MOVE_RIGHT:
                self.setUpDownDatetime(controlID)

                if self.selectionIsOffscreen() or 100 <= controlID <= self.gen.maxEnd:
                    return self.guideRight()
            elif action == xbmcgui.ACTION_MOVE_DOWN:
                if controlID > self.gen.maxEnd:
                    return self.guideNavDown()
            elif action == xbmcgui.ACTION_MOVE_UP:
                if controlID > self.gen.maxEnd:
                    return self.guideNavUp()
            elif action == xbmcgui.ACTION_PAGE_DOWN:
                if controlID > self.gen.maxEnd:
                    return self.guideNavDown(6)
            elif action == xbmcgui.ACTION_PAGE_UP:
                if controlID > self.gen.maxEnd:
                    return self.guideNavUp(6)
            elif action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                WM.showMenu()
                return
        except:
            util.ERROR()

        kodigui.BaseWindow.onAction(self, action)

    def tick(self):
        self.updateTimeIndicator()
        self.updateSelectedDetails()
        self.pollTuners()

    def halfHour(self):
        self.hhData.update()
        self.fillChannels()

    def updateTimeIndicator(self):
        timePosSeconds = tablo.compat.timedelta_total_seconds(tablo.api.now() - self.hhData.halfHour)
        pos = int((timePosSeconds / 1800.0) * self.gen.HALF_HOUR_WIDTH)
        if pos >= 0:
            self.timeIndicator.setPosition(pos, 0)
            self.timeIndicator.setVisible(True)
        else:
            self.timeIndicator.setPosition(0, 0)
            self.timeIndicator.setVisible(False)

    def getAiringByControlID(self, controlID):
        return self.slotButtons.get(controlID)

    def setUpDownDatetime(self, controlID=None):
        controlID = controlID or self.getFocusId()
        selected = self.getAiringByControlID(controlID)
        self.upDownDatetime = selected and selected.datetime or None
        if not self.upDownDatetime:
            return

        if self.upDownDatetime < self.hhData.halfHour:
            self.upDownDatetime = self.hhData.halfHour

    def guideRight(self):
        if not self.hhData.incrementOffset():
            self.selectLastInRow()
            return

        last = self.getAiringByControlID(self.lastFocus)
        airing = self.getSelectedAiring() or last

        row = self.getRow(self.lastFocus)
        self.fillChannels()

        if not self.selectAiring(airing, row):
            self.selectLastInRow()

    def guideLeft(self, at_edge=False, short_airing=None):
        if at_edge:
            if self.hhData.offsetHalfHours == 0:
                self.setFocusId(self.lastFocus)
                WM.showMenu()
                return
            else:
                selected = self.getAiringByControlID(self.lastFocus)
                airing = short_airing or selected
        else:
            selected = self.getSelectedAiring()
            airing = short_airing or selected

        if not short_airing:
            for controlID, rowAiring, short in self.rows[self.getRow()]:
                if airing == rowAiring:
                    if not short and not at_edge:
                        return
                    break

        select = selected or self.getAiringByControlID(self.lastFocus)

        if self.hhData.decrementOffset():
            self.fillChannels()

        self.selectFirstInRow(select=select)

    def guideNavDown(self, offset=1):
        row = self.getRow()
        if row == self.rowCount - 1:
            return

        if not self.upDownDatetime:
            self.setUpDownDatetime()

        row += offset
        if row >= self.rowCount:
            row = self.rowCount - 1

        for idx, (ID, airing, short) in enumerate(self.rows[row]):
            if not airing or airing.airingNow(self.upDownDatetime):
                if idx == 0 and short:
                    self.guideLeft(short_airing=airing)
                if not self.selectAiring(airing, row):
                    self.lastFocus = ID
                    self.setFocusId(ID)
                break
        else:
            # if len(self.rows[row]) == 1:
            self.lastFocus = self.rows[row][0][0]
            self.setFocusId(self.rows[row][0][0])
            # else:
            #     return

        if row > self.topRow + 5:
            self.topRow += offset
            if self.rowCount - self.topRow < 5:
                self.topRow = self.rowCount - 6
            self.gridGroup.setPosition(self.gridGroup.getX(), self.baseY - self.topRow * 52)

    def guideNavUp(self, offset=1):
        row = self.getRow()
        if row == 0:
            return

        if not self.upDownDatetime:
            self.setUpDownDatetime()

        row -= offset
        if row < 0:
            row = 0

        for idx, (ID, airing, short) in enumerate(self.rows[row]):
            if not airing or airing.airingNow(self.upDownDatetime):
                if idx == 0 and short:
                    self.guideLeft(short_airing=airing)
                if not self.selectAiring(airing, row):
                    self.lastFocus = ID
                    self.setFocusId(ID)
                break
        else:
            # if len(self.rows[row]) == 1:
            self.lastFocus = self.rows[row][0][0]
            self.setFocusId(self.rows[row][0][0])
            # else:
            #     return

        if row < self.topRow + 1:
            if self.topRow > 0:
                control = self.getControl(45)
                self.topRow -= offset
                if self.topRow < 0:
                    self.topRow = 0
                control.setPosition(control.getX(), self.baseY - self.topRow * 52)

    def getRow(self, controlID=None):
        controlID = controlID or self.getFocusId()
        if 99 < controlID <= self.gen.maxEnd:
            return controlID - 100
        row = ((controlID - self.gen.maxEnd - 1) / (self.gen.ITEMS_PER_ROW + 2))
        return row

    def onClick(self, controlID):
        airing = self.getAiringByControlID(controlID)
        control = self.getControl(controlID)
        control.setSelected(not control.isSelected())
        if airing:
            self.airingClicked(airing)

    def onFocus(self, controlID):
        if controlID > self.gen.maxEnd and controlID not in self.chanLabelButtons:
            self.lastFocus = controlID

        self.updateSelectedDetails()

    def onWindowFocus(self):
        if not self.selectFirstInRow():
            self.setFocusId(self.gen.maxEnd + 3)  # Upper left grid button

    def clearChannelColors(self):
        for path in self.gen.paths:
            channel = self.gen.channels[path]
            self.setProperty('channel.pulse.{0}'.format(channel['label']), '')
            self.getControl(channel['label']).setLabel('{0}'.format(channel.get('title', '')))

    def getUsedTunerChannelPaths(self):
        paths = []
        for tuner in tablo.API.server.tuners.get():
            if tuner.get('in_use'):
                path = tuner.get('channel')
                if path in self.gen.channels:
                    paths.append(path)

        return paths

    def pollTuners(self):
        now = time.time()
        if now < self.nextTunerPoll:
            return

        self.nextTunerPoll = time.time() + 30
        self.checkTuners()

    def checkTuners(self):
        try:
            paths = self.getUsedTunerChannelPaths()
            if paths != self.tunerInUse:
                self.clearChannelColors()
            self.tunerInUse = paths

            for path in paths:
                channel = self.gen.channels[path]
                self.setProperty('channel.pulse.{0}'.format(channel['label']), '1')
                self.getControl(channel['label']).setLabel(u'[COLOR FFFF2222]{0}[/COLOR]'.format(channel.get('title', '')))
        except:
            util.ERROR()

    def updateSelectedDetails(self):
        airing = self.getSelectedAiring()
        if not airing:
            return

        self.setProperty('background', airing.background)
        self.setProperty('thumb', airing.thumb)
        self.setProperty('title', airing.title)

        self.setProperty('info', airing.data.get('title', ''))
        if airing.type == 'movie' and airing.quality_rating:
            info = []
            if airing.film_rating:
                info.append(airing.film_rating.upper())
            if airing.release_year:
                info.append(str(airing.release_year))

            self.setProperty('info', u' / '.join(info) + u' /')
            self.setProperty('stars', str(airing.quality_rating / 2))
            self.setProperty('half.star', str(airing.quality_rating % 2))
        else:
            self.setProperty('stars', '0')
            self.setProperty('half.star', '')

        if airing.type == 'series':
            info = []
            if airing.data.get('title'):
                info.append(airing.data.get('title'))
            if airing.data.get('season_number'):
                info.append(T(32155).format(airing.data['season_number']))
            if airing.data.get('episode_number'):
                info.append(T(32158).format(airing.data['episode_number']))

            self.setProperty('info', u' / '.join(info))

        if airing.ended():
            secs = airing.secondsSinceEnd()
            start = T(32144).format(util.durationToText(secs))
        else:
            secs = airing.secondsToStart()

            if secs < 1:
                start = T(32145).format(util.durationToText(secs * -1))
            else:
                start = T(32146).format(util.durationToText(secs))

        if airing.conflicted:
            self.setProperty('indicator', 'indicators/conflict_pill_hd.png')
        elif airing.scheduled:
            self.setProperty('indicator', 'indicators/rec_pill_hd.png')
        else:
            self.setProperty('indicator', '')

        self.setProperty('start', start)

    def selectAiring(self, airing, row=None):
        if row is None:
            row = self.getRow()

        if row < 0 or row >= len(self.rows):
            return False

        for controlID, rowAiring, short in self.rows[row]:
            if airing == rowAiring:
                break
        else:
            return False

        self.lastFocus = controlID
        self.setFocusId(controlID)
        return True

    def selectFirstInRow(self, row=None, select=None):
        if row is None:
            row = self.getRow()

        if row < 0 or row >= len(self.rows):
            return False

        controlID = None
        if select:
            if select.datetime < self.hhData.halfHour:
                for newID, rowAiring, short in self.rows[row]:
                    if select == rowAiring:
                        controlID = newID
                        break
                else:
                    controlID = None

        if not controlID:
            if self.rows[row][0][2] and not self.hhData.offsetHalfHours == 0:  # Short and not at start of EPG
                controlID = self.rows[row][1][0]
            else:
                controlID = self.rows[row][0][0]

        self.lastFocus = controlID
        self.setFocusId(controlID)

        return True

    def selectLastInRow(self, row=None):
        if row is None:
            row = self.getRow()

        for i in range(len(self.rows[row]) - 1, -1, -1):
            controlID = self.rows[row][i][0]
            if xbmc.getCondVisibility('Control.IsVisible({0})'.format(controlID)) and not self.rows[row][i][2]:
                break
        else:
            controlID = self.rows[row][0][0]  # Shouldn't happen

        self.lastFocus = controlID
        self.setFocusId(controlID)

        self.setFocusId(controlID)
        return True

    def getSelectedAiring(self):
        return self.getAiringByControlID(self.getFocusId())

    def selectionIsOffscreen(self):
        return self.getFocusId() in self.offButtons

    def setTimesHeader(self, halfhour=None):
        for x in range(4):
            label = self.getControl(40 + x)
            label.setLabel((self.hhData.halfHour + tablo.compat.datetime.timedelta(minutes=x * 30)).strftime('%I:%M %p').lstrip('0'))

    def channelUpdatedCallback(self, channel):
        genData = self.gen.channels[channel.path]
        ID = genData['label']
        self.chanLabelButtons[ID] = True
        label = u'{0} [B]{1}-{2}[/B]'.format(channel.call_sign, channel.major, channel.minor)
        genData['title'] = label
        if channel.path in self.tunerInUse:
            self.getControl(ID).setLabel(u'[COLOR FFFF2222]{0}[/COLOR]'.format(label))
        else:
            self.getControl(ID).setLabel(label)

        self.updateChannelAirings(channel.path)

    def updateGridItem(self, airing, ID):
        if airing.conflicted:
            util.setGlobalProperty('badge.color.{0}'.format(ID), 'FFD93A34')
        elif airing.scheduled:
            util.setGlobalProperty('badge.color.{0}'.format(ID), 'FFFF8000')
        else:
            util.setGlobalProperty('badge.color.{0}'.format(ID), '00FFFFFF')

    def updateChannelAirings(self, path):
        genData = self.gen.channels[path]

        pos = self.gen.paths.index(path)
        pathID = path.rsplit('/', 1)[-1]

        self.setProperty('started.{0}'.format(pathID), '')

        totalwidth = 0

        self.setProperty('nodata.{0}'.format(path.rsplit('/', 1)[-1]), '')

        row = []
        slot = -1
        atEnd = False

        for slot, airing in enumerate(self.grid.airings(self.hhData.halfHour, min(self.hhData.maxHalfHour, self.hhData.cutoff), path)):
            try:
                ID = genData['slots'][slot]
            except IndexError:
                break

            self.slotButtons[ID] = airing
            control = self.getControl(ID)

            if airing.conflicted:
                util.setGlobalProperty('badge.color.{0}'.format(ID), 'FFD93A34')
            elif airing.scheduled:
                util.setGlobalProperty('badge.color.{0}'.format(ID), 'FFFF8000')
            else:
                util.setGlobalProperty('badge.color.{0}'.format(ID), '00FFFFFF')

            if airing.airingNow(self.hhData.halfHour):
                if self.hhData.offsetHalfHours != 0 and self.hhData.halfHour != airing.datetime:
                    self.setProperty('started.{0}'.format(pathID), '1')
                duration = airing.secondsToEnd(start=self.hhData.halfHour)
            else:
                duration = airing.duration

            row.append((ID, airing, duration < 1800 and True or False))

            if airing.datetimeEnd >= self.hhData.cutoff:
                atEnd = True
                if airing.datetimeEnd > self.hhData.cutoff:
                    duration -= tablo.compat.timedelta_total_seconds(airing.datetimeEnd - self.hhData.cutoff)

            if airing.qualifiers:
                new = 'new' in airing.qualifiers and u'[COLOR FF2F8EC0]{0}:[/COLOR] '.format(T(32159)) or u''
                live = 'live' in airing.qualifiers and u'[COLOR FF2F8EC0]{0}:[/COLOR] '.format(T(32160)) or u''
                label = u'{0}{1}'.format(new or live, airing.title)
            else:
                label = airing.title

            width = int(round((duration / 1800.0) * self.gen.HALF_HOUR_WIDTH))
            save = width
            if totalwidth > 1110:
                self.offButtons[ID] = True
                control.setVisible(False)
            else:
                if totalwidth + width > 1110:
                    width = 1110 - totalwidth
                    if width < self.gen.HALF_HOUR_WIDTH:
                        self.offButtons[ID] = True
                control.setVisible(True)

            totalwidth += save

            control.setRadioDimension(width - 31, 1, 30, 30)
            control.setWidth(width)
            if width > 34:
                control.setLabel(label)
            else:
                control.setLabel(' ')

        if slot == -1 or (totalwidth < 1110 and not atEnd):
            slot += 1
            ID = genData['slots'][slot]

            util.setGlobalProperty('badge.color.{0}'.format(ID), '00FFFFFF')

            control = self.getControl(ID)

            control.setSelected(False)
            control.setWidth(1110 - totalwidth)
            if self.grid.hasNoData(path):
                control.setLabel(' ')
                self.setProperty('nodata.{0}'.format(pathID), '1')
            else:
                control.setLabel('Loading...')
            control.setVisible(True)
            self.slotButtons[ID] = None
            row.append((ID, None, False))

        for slot in range(slot + 1, self.gen.ITEMS_PER_ROW):
            ID = genData['slots'][slot]

            self.setProperty('badge.color.{0}'.format(ID), '00FFFFFF')

            control = self.getControl(ID)
            control.setSelected(False)
            control.setVisible(False)
            control.setLabel('')
            self.slotButtons[ID] = None

        self.rows[pos] = row

    def initEPG(self):
        row = []

        for path in self.gen.paths:
            slot = 0
            genData = self.gen.channels[path]

            ID = genData['slots'][slot]
            control = self.getControl(ID)
            control.setWidth(1110)
            control.setVisible(True)
            self.slotButtons[ID] = None
            row.append((ID, None, False))

            for slot in range(slot + 1, self.gen.ITEMS_PER_ROW):
                ID = genData['slots'][slot]

                control = self.getControl(ID)
                control.setSelected(False)
                control.setVisible(False)
                control.setLabel('')
                self.slotButtons[ID] = None

            self.rows[self.gen.paths.index(path)] = row

    @base.tabloErrorHandler
    def getChannels(self):
        self.grid.getChannels(self.gen.paths)
        self.checkTuners()

    def fillChannels(self):
        self.slotButtons = {}
        self.offButtons = {}
        self.rows = [[]] * len(self.gen.paths)

        self.setTimesHeader()
        self.updateTimeIndicator()

        for path in self.gen.paths:
            self.updateChannelAirings(path)

    def setDialogButtons(self, airing, arg_dict):
        if airing.airingNow():
            arg_dict['button1'] = ('watch', T(32140))
            button = 'button2'
        else:
            button = 'button1'

        if airing.conflicted:
            arg_dict[button] = ('unschedule', T(32141).format(util.LOCALIZED_AIRING_TYPES[airing.type.upper()]))
            arg_dict['title_indicator'] = 'indicators/conflict_pill_hd.png'
        elif airing.scheduled:
            arg_dict[button] = ('unschedule', T(32141).format(util.LOCALIZED_AIRING_TYPES[airing.type.upper()]))
            arg_dict['title_indicator'] = 'indicators/rec_pill_hd.png'
        else:
            arg_dict[button] = ('record', T(32142).format(util.LOCALIZED_AIRING_TYPES[airing.type.upper()]))

    @base.dialogFunction
    def airingClicked(self, airing):
        # while not airing and backgroundthread.BGThreader.working() and not xbmc.abortRequested:
        #     xbmc.sleep(100)
        #     airing = item.dataSource.get('airing')
        try:
            info = T(32143).format(
                airing.gridAiring.displayChannel(),
                airing.gridAiring.network,
                airing.gridAiring.displayDay(),
                airing.gridAiring.displayTimeStart(),
                airing.gridAiring.displayTimeEnd()
            )
        except tablo.ConnectionError:
            xbmcgui.Dialog().ok(T(32161), T(32157).format(tablo.API.device.displayName))
            return

        kwargs = {
            'number': airing.gridAiring.number,
            'background': airing.background,
            'callback': self.actionDialogCallback,
            'obj': airing,
            'start_indicator1': 'new' in airing.qualifiers and 'indicators/qualifier_new_hd.png' or '',
            'start_indicator2': 'live' in airing.qualifiers and 'indicators/qualifier_live_hd.png' or ''
        }

        self.setDialogButtons(airing, kwargs)

        if airing.type == 'movie':
            try:
                show = airing.gridAiring.getShow()
                description = show.plot or show.description
            except:
                util.ERROR()
                description = ''
        else:
            description = airing.gridAiring.description

        secs = airing.gridAiring.secondsToStart()

        if secs < 1:
            start = T(32145).format(util.durationToText(secs * -1))
        else:
            start = T(32146).format(util.durationToText(secs))

        actiondialog.openDialog(
            airing.title,
            info,
            description,
            start,
            **kwargs
        )
        # self.updateIndicators()

    def actionDialogCallback(self, obj, action):
        airing = obj
        changes = {}

        if action:
            if action == 'watch':
                player.PLAYER.playAiringChannel(airing.gridAiring)
            elif action == 'record':
                airing.schedule()
                self.grid.updateChannelAiringData(path=airing.gridAiring.channel['path'])
            elif action == 'unschedule':
                airing.schedule(False)
                self.grid.updateChannelAiringData(path=airing.gridAiring.channel['path'])

            self.updateGridItem(airing, self.getFocusId())

        if airing.gridAiring.ended():
            secs = airing.gridAiring.secondsSinceEnd()
            changes['start'] = T(32144).format(util.durationToText(secs))
        else:
            self.setDialogButtons(airing, changes)

            secs = airing.gridAiring.secondsToStart()

            if secs < 1:
                start = T(32145).format(util.durationToText(secs * -1))
            else:
                start = T(32146).format(util.durationToText(secs))

            changes['start'] = start

        return changes


class EPGXMLGenerator(object):
    BASE_ID = 100
    HALF_HOUR_WIDTH = 320
    ITEMS_PER_ROW = 16

    BASE_XML_PATH = os.path.join(
        SKIN_PATH, 'resources', 'skins', 'Main', '720p', 'script-tablo-livetv.xml'
    )

    OUTPUT_PATH = os.path.join(
        SKIN_PATH, 'resources', 'skins', 'Main', '720p', 'script-tablo-livetv-generated.xml'
    )

    CHANNEL_BASE_XML = '''
                <control type="group">
                    <posy>{POSY}</posy>
                    <control type="grouplist" id="{ID}">
                        <hitrect x="2000" y="2000" w="5" h="5"/>
                        <posy>0</posy>
                        <onleft>50</onleft>
                        <onright>50</onright>
                        <height>52</height>
                        <width>1300</width>
                        <orientation>horizontal</orientation>
                        <align>left</align>
                        <itemgap>0</itemgap>
                        <usecontrolcoords>true</usecontrolcoords>
                        {AIRINGS_XML}
                    </control>
                    <control type="image">
                        <visible>!IsEmpty(Window.Property(nodata.{PATH}))</visible>
                        <posx>182</posx>
                        <posy>0</posy>
                        <width>1100</width>
                        <height>52</height>
                        <texture>livetv/livetv_empty_cell_normal_hd.png</texture>
                    </control>
                    <control type="image">
                        <visible>!IsEmpty(Window.Property(started.{PATH})) + !Control.HasFocus({FIRST})</visible>
                        <posx>184</posx>
                        <posy>8</posy>
                        <width>10</width>
                        <height>36</height>
                        <texture>livetv/livetv_airing_started_arrow_normal_hd.png</texture>
                    </control>
                    <control type="image">
                        <visible>!IsEmpty(Window.Property(started.{PATH})) + Control.HasFocus({FIRST})</visible>
                        <posx>184</posx>
                        <posy>8</posy>
                        <width>10</width>
                        <height>36</height>
                        <texture>livetv/livetv_airing_started_arrow_highlighted_hd.png</texture>
                    </control>
                </control>
'''

    AIRING_BASE_XML = '''
                    <control type="radiobutton" id="{ID}">
                        <posx>0</posx>
                        <posy>0</posy>
                        <width>{WIDTH}</width>
                        <height>52</height>
                        <font>font16</font>
                        <textcolor>C8E8E8E8</textcolor>
                        <focusedcolor>FF000000</focusedcolor>
                        <align>left</align>
                        <aligny>center</aligny>
                        <texturefocus colordiffuse="FFE8E8E8" border="2">script-tablo-epg_slot.png</texturefocus>
                        <texturenofocus colordiffuse="FF101924" border="2">script-tablo-epg_slot.png</texturenofocus>
                        <textureradioonfocus colordiffuse="$INFO[Window(10000).Property(script.tablo.badge.color.{ID})]">livetv/livetv_badge_blank_hd.png</textureradioonfocus>
                        <textureradioonnofocus colordiffuse="$INFO[Window(10000).Property(script.tablo.badge.color.{ID})]">livetv/livetv_badge_blank_hd.png</textureradioonnofocus>
                        <textureradioofffocus colordiffuse="$INFO[Window(10000).Property(script.tablo.badge.color.{ID})]">livetv/livetv_badge_blank_hd.png</textureradioofffocus>
                        <textureradiooffnofocus colordiffuse="$INFO[Window(10000).Property(script.tablo.badge.color.{ID})]">livetv/livetv_badge_blank_hd.png</textureradiooffnofocus>
                        <radiowidth>30</radiowidth>
                        <radioheight>30</radioheight>
                        <textoffsetx>16</textoffsetx>
                        <textoffsety>0</textoffsety>
                        <label></label>
                        <scroll>false</scroll>
                    </control>
'''  # noqa E501

    END_BUTTON_XML = '''
                    <control type="button" id="{0}">
                        <width>1</width>
                        <height>52</height>
                        <font>font16</font>
                        <textcolor>000000</textcolor>
                        <focusedcolor>000000</focusedcolor>
                        <texturefocus>-</texturefocus>
                        <texturenofocus>-</texturenofocus>
                        <label> </label>
                        <scroll>false</scroll>
                    </control>
'''

    CHANNEL_LABEL_BASE_XML = '''
                    <control type="button" id="{ID}">
                        <animation effect="fade" start="100" end="20" time="1000" pulse="true" condition="!IsEmpty(Window.Property(channel.pulse.{ID}))">Conditional</animation>
                        <width>180</width>
                        <height>52</height>
                        <font>font13</font>
                        <textcolor>FFE8E8E8</textcolor>
                        <focusedcolor>FFE8E8E8</focusedcolor>
                        <align>right</align>
                        <aligny>center</aligny>
                        <texturefocus colordiffuse="FF000000">script-tablo-white_square.png</texturefocus>
                        <texturenofocus colordiffuse="FF000000">script-tablo-white_square.png</texturenofocus>
                        <textoffsetx>10</textoffsetx>
                        <textoffsety>0</textoffsety>
                        <label></label>
                        <scroll>false</scroll>
                    </control>
'''  # noqa E501

    def __init__(self, paths):
        self.paths = paths
        self.currentID = self.BASE_ID - 1
        self.channels = {}
        self.maxEnd = 0

    def nextID(self):
        self.currentID += 1
        return self.currentID

    def setStartID(self, start):
        self.currentID = start - 1

    def create(self):
        self.setStartID(100 + len(self.paths))
        self.maxEnd = 99 + len(self.paths)
        xml = ''
        posy = 0
        for idx, p in enumerate(self.paths):
            chanID = self.nextID()
            chanLabelID = self.nextID()
            airingsXML = ''
            slots = []
            airingsXML += self.CHANNEL_LABEL_BASE_XML.format(ID=chanLabelID)
            for x in range(self.ITEMS_PER_ROW):
                ID = self.nextID()
                if not x:
                    width = 1100
                    first = ID
                else:
                    width = 1
                slots.append(ID)
                util.setGlobalProperty('badge.color.{0}'.format(ID), '00FFFFFF')
                airingsXML += self.AIRING_BASE_XML.format(ID=ID, WIDTH=width)

            airingsXML += self.END_BUTTON_XML.format(100 + idx)

            xml += self.CHANNEL_BASE_XML.format(ID=chanID, AIRINGS_XML=airingsXML, POSY=posy, PATH=p.rsplit('/', 1)[-1], FIRST=first)
            data = {'ID': chanID, 'label': chanLabelID, 'slots': slots}

            self.channels[p] = data

            posy += 52

        with open(self.BASE_XML_PATH, 'r') as f:
            with open(self.OUTPUT_PATH, 'w') as o:
                o.write(f.read().replace('<!-- GENERATED CONTENT -->', xml))

        return self

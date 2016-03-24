# -*- coding: utf-8 -*-
import time, random, threading
import xbmc, xbmcgui

import hdhr
import kodigui
import util
import player
import skin
import dvr

API_LEVEL = 2

CHANNEL_DISPLAY = u'[COLOR FF99CCFF]{0}[/COLOR] {1}'
GUIDE_UPDATE_INTERVAL = 3300 #55 mins
GUIDE_UPDATE_VARIANT = 600 #10 mins

MAX_TIME_INT = 31536000000

class KodiChannelEntry(kodigui.BaseDialog):
    def __init__(self,*args,**kwargs):
        self.digits = str(kwargs['digit'])
        self.hasSubChannels = kwargs.get('has_sub_channels',False)
        self.channel = ''
        self.set = False
        kodigui.BaseDialog.__init__(self,*args,**kwargs)

    def onInit(self):
        kodigui.BaseDialog.onInit(self)
        self.showChannel()

    def onAction(self,action):
        try:
            if action.getId() >= xbmcgui.REMOTE_0 and action.getId() <= xbmcgui.REMOTE_9:
                digit = str(action.getId() - 58)
                self.digits += digit
                if '.' in self.digits:
                    if len(self.digits.split('.',1)[-1]) > 1: #This can happen if you hit two keys at the same time
                        self.digits = self.digits[:-1]
                    self.showChannel()
                    return self.submit()

                if len(self.digits) < 5:
                    return self.showChannel()

                self.digits = self.digits[:-1]

            elif action == xbmcgui.ACTION_NAV_BACK:
                return self.backspace()
            elif action == xbmcgui.ACTION_MOVE_DOWN:
                return self.addDecimal()
            elif action == xbmcgui.ACTION_SELECT_ITEM:
                return self.submit()
        except:
            util.ERROR()
            kodigui.BaseDialog.onAction(self,action)
            return

        kodigui.BaseDialog.onAction(self,action)

    def submit(self):
        self.set = True
        self.doClose()

    def backspace(self):
        self.digits = self.digits[:-1]
        if not self.digits:
            self.doClose()
            return
        self.showChannel()

    def addDecimal(self):
        if '.' in self.digits:
            return False
        self.digits += '.'
        self.showChannel()
        return True

    def showChannel(self):
        self.channel = self.digits
        try:
            self.setProperty('channel',self.channel)
        except RuntimeError: #Sometimes happens when to fast entry during submission/close
            self.close()

    def getChannel(self):
        if not self.set: return None
        if not self.channel: return None
        if self.channel.endswith('.'):
            return self.channel[:-1]
        return self.channel

class OptionsDialog(kodigui.BaseDialog):
    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.option = None

    def onInit(self):
        kodigui.BaseDialog.onInit(self)
        self.setFocusId(252)
        self.option = None

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                return self.doClose()
            elif action == xbmcgui.ACTION_MOVE_DOWN or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_LEFT:
                if not self.getFocusId():
                    self.setFocusId(241)

        except:
            return kodigui.BaseDialog.onAction(self,action)

        kodigui.BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        if controlID in (238,244,245): return
        if controlID == 241:
            self.option = 'SEARCH'
        elif controlID == 248:
            self.option = 'LIVETV'
        elif controlID == 247:
            self.option = 'EXIT'
            util.setGlobalProperty('window.animations','')
        self.doClose()

class SeekActionHandler(object):
    def __init__(self,callback):
        self.callback = callback
        self.initiallyPaused = False
        self.action = None
        self.event = threading.Event()
        self.event.clear()
        self.timer = None
        self.delay = 0.1

    def onAction(self,action):
        self.action = action
        if self.event.isSet():
            return
        self.startTimer(action)

    def startTimer(self, action):
        self.action = action
        self.event.set()
        if self.timer: self.timer.cancel()
        if action != xbmcgui.ACTION_PLAY:
            self.initiallyPaused = xbmc.getCondVisibility('Player.Paused')
            if not self.initiallyPaused:
                xbmc.executebuiltin('PlayerControl(play)')

        self.timer = threading.Timer(self.delay,self.doAction)
        self.timer.start()

    def doAction(self):
        action = self.action
        try:
            if self.callback(action):
                if action != xbmcgui.ACTION_PLAY and not self.initiallyPaused:
                    self.startTimer(xbmcgui.ACTION_PLAY)
                    return

                self.initiallyPaused = False
                self.event.clear()
            else:
                if self.timer: self.timer.cancel()
                self.timer = threading.Timer(0.05,self.doAction)
                self.timer.start()
                return

            self.action = None
        except:
            util.ERROR()
            self.event.clear()

        self.timer = None

    def clear(self):
        if self.timer: self.timer.cancel()
        return self.event.isSet()


class GuideOverlay(util.CronReceiver):
    _BASE = None

    width = 1920
    height = 1080

    def __init__(self,*args,**kwargs):
        self._BASE.__init__(self,*args,**kwargs)
        self.started = False
        self.touchMode = False
        self.lineUp = None
        self.guide = None
        self.player = None
        self.current = None
        self.fallbackChannel = None
        self.cron = None
        self.guideFetchPreviouslyFailed = False
        self.nextChannelUpdate = MAX_TIME_INT
        self.resetNextGuideUpdate()
        self.lastDiscovery = time.time()
        self.filter = None
        self.optionsDialog = None
        self.dvrWindow = None
        self.propertyTimer = None
        self.currentDetailsTimer = None
        self.seekBarTimer = None
        self.lastSeek = 0
        self.seekHandler = SeekActionHandler(self.seekCallback)
        self.inLoop = False
        self.sliceTimestamp = 0
        self.lastItem = None
        self.abort = False

        self.devices = None

    #==========================================================================
    # EVENT HANDLERS
    #==========================================================================
    def onFirstInit(self):
        if self.touchMode:
            util.DEBUG_LOG('Touch mode: ENABLED')
            self.setProperty('touch.mode','True')
        else:
            util.DEBUG_LOG('Touch mode: DISABLED')
        self.started = True

        self.propertyTimer = kodigui.PropertyTimer(self._winID,util.getSetting('overlay.timeout',0),'show.overlay','', callback=self.overlayTimerCallback)
        self.currentDetailsTimer = kodigui.PropertyTimer(self._winID,5,'show.current','')
        self.seekBarTimer = kodigui.PropertyTimer(self._winID,5,'show.seekbar','')

        self.channelList = kodigui.ManagedControlList(self,201,3)
        self.currentProgress = self.getControl(250)

        #Add item to dummy list - this list allows right click on video to bring up the context menu
        self.getControl(210).addItem(xbmcgui.ListItem(''))

        self.start()

    def onAction(self,action):
        try:
            # print 'ID: {0} CODE: {1} FOCUS: {2} X: {3} Y: {4}'.format(
            #     action.getId(), action.getButtonCode(), self.getFocusId(), self.mouseXTrans(action.getAmount1()), self.mouseXTrans(action.getAmount2())
            # )
            if self.overlayVisible(): self.propertyTimer.reset()


            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return

            mli = self.channelList.getSelectedItem()
            if mli != self.lastItem:
                self.onListItemFocus(mli)
                self.lastItem = mli

            if self.checkSeekActions(action):
                self._BASE.onAction(self, action)
                self.showSeekBar()
                return

            if action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
                if self.overlayVisible():
                    return self.sliceRight()
                else:
                    return self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                return self.showOverlay()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                return self.showOptions()
            elif action == xbmcgui.ACTION_MOVE_LEFT or action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
                if mli.getProperty('slice.offset') and mli.getProperty('slice.offset') != '0':
                    return self.sliceLeft()
                else:
                    return self.showOverlay(False)
            elif action == xbmcgui.ACTION_SELECT_ITEM:
                return self.onSelect(self.getFocusId())
            elif action == xbmcgui.ACTION_BUILT_IN_FUNCTION:
                if self.clickShowOverlay(): return
            elif self.checkChannelEntry(action):
                return
            elif action == xbmcgui.ACTION_CHANNEL_UP: #or action == xbmcgui.ACTION_PAGE_UP: #For testing
                self.channelUp()
            elif action == xbmcgui.ACTION_CHANNEL_DOWN: #or action == xbmcgui.ACTION_PAGE_DOWN: #For testing
                self.channelDown()
            elif action in (xbmcgui.ACTION_MOUSE_LEFT_CLICK, xbmcgui.ACTION_MOUSE_DOUBLE_CLICK): # To catch all clicks we need to catch both
                if self.getFocusId() in (210, 217):
                    return self.handleMouseClick(action, mli)
                elif self.getFocusId() == 201 or (self.getFocusId() == 215 and self.mouseXTrans(action.getAmount1()) < 1774):
                    if not mli.getProperty('slice.offset') or mli.getProperty('slice.offset') == '0':
                        self.channelClicked()
                elif xbmc.getCondVisibility('ControlGroup(216).HasFocus(0)'):
                    return self.sliceRight()
                # elif self.getFocusId() == 217:
                #     return self.sliceLeft()
            elif action.getButtonCode() == 61519:
                xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ShowCodec", "id": 1}')
            elif action.getButtonCode() == 61524:
                #xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Input.ShowCodec", "id": 1}')
                self.player.showSubtitles(not xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled'))
                util.DEBUG_LOG('Subtitles: {0}'.format(xbmc.getCondVisibility('VideoPlayer.SubtitlesEnabled') and 'Enabled' or 'Disabled'))

        except:
            util.ERROR()
            self._BASE.onAction(self,action)
            return
        self._BASE.onAction(self,action)

    def onListItemFocus(self, mli):
        if self.lastItem:
            self.lastItem.setProperty('slice.offset', '0')
            self.lastItem.dataSource['sliceOffset'] = 0
            self.lastItem.setProperty('show', '')

        mli.setProperty('show', '1')

        if self.sliceTimestamp:
            self.adjustSlice(mli)

    def handleMouseClick(self, action, mli):
        x = self.mouseXTrans(action.getAmount1())
        y = self.mouseXTrans(action.getAmount2())
        row = int(xbmc.getInfoLabel('Container(201).Position'))
        #print '{0} , {1} : {2}'.format(x, y, row)


        if self.overlayVisible():
            if y >= 810 and row == 3:
                self.rowClicked(action, mli, x, y)
            elif 540 <= y < 810 and row == 2:
                self.rowClicked(action, mli, x, y)
            elif 270 <= y < 540 and row == 1:
                self.rowClicked(action, mli, x, y)
            elif y < 270 and row == 0:
                self.rowClicked(action, mli, x, y)
            else:
                if action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                    self.clickShowOverlay(210)
        else:
            if action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                self.clickShowOverlay(210)

    def rowClicked(self, action, mli, x, y):
        if not mli.getProperty('slice.offset') or mli.getProperty('slice.offset') == '0':
            if action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
                self.clickShowOverlay(210)
            return

        if x < 146:
            self.sliceLeft()
            return

        if action.getId() != xbmcgui.ACTION_MOUSE_LEFT_CLICK:
            return

        pos = -1
        if x < 240:
            pos = 0
        elif x < 480:
            pos = 1
        elif x < 720:
            pos = 2
        elif x < 960:
            pos = 3
        elif x < 1200:
            pos = 4
        elif x < 1440:
            pos = 5
        else:
            return

        i = pos - (6 - mli.dataSource['sliceOffset'])
        if i < 0:
            if i < -2:
                self.clickShowOverlay(210)
            return

        ep = mli.dataSource['slice'][i]

        self.openRecordDialog(ep)

    def timeDisplay(self, timestamp):
        nowDay = time.localtime().tm_yday
        timeTuple = time.localtime(timestamp)
        if nowDay != timeTuple.tm_yday:
            return time.strftime('%a ', timeTuple) + time.strftime('%I:%M %p', timeTuple).lstrip('0')
        else:
            return time.strftime('%I:%M %p', timeTuple).lstrip('0')

    def adjustSlice(self, mli=None):
        mli = mli or self.channelList.getSelectedItem()

        join = None
        if mli.dataSource['thread'] and mli.dataSource['thread'].isAlive():
            join = mli.dataSource['thread']

        mli.dataSource['thread'] = threading.Thread(target=self._adjustSlice, args=(mli,join))
        mli.dataSource['thread'].start()

    def _adjustSlice(self, mli, join):
        if join:
            join.join()

        if self.abort:
            return

        xbmc.sleep(250)
        if not self.channelList.getSelectedItem() == mli:  # User has moved on, ignore
            return

        ep = mli.dataSource['slice'] and mli.dataSource['slice'][mli.dataSource['sliceOffset']-1] or None
        if not ep or ep.startTimestamp < self.sliceTimestamp:
            self.addToSlice(mli, timestamp=self.sliceTimestamp)

        for o, ep in enumerate(mli.dataSource['slice']):
            if ep.startTimestamp == self.sliceTimestamp:
                mli.dataSource['sliceOffset'] = o + 1
                break
            elif ep.startTimestamp > self.sliceTimestamp:
                mli.dataSource['sliceOffset'] = o
                break
        else:
            mli.dataSource['sliceOffset'] = o

        self.updateSlice(mli)

    def updateSlice(self, mli=None):
        mli = mli or self.channelList.getSelectedItem()

        if mli.dataSource['sliceOffset'] >= len(mli.dataSource['slice']):
            self.addToSlice(mli)
            if mli.dataSource['sliceOffset'] >= len(mli.dataSource['slice']):
                mli.dataSource['sliceOffset'] = len(mli.dataSource['slice']) - 1

        ep = mli.dataSource['slice'][mli.dataSource['sliceOffset']-1]
        mli.setProperty('slice.title', ep.title or ep.showTitle)
        mli.setProperty('slice.synopsis', ep.synopsis)
        if mli.dataSource['sliceOffset'] > 6:
            for i, ep in enumerate(mli.dataSource['slice'][mli.dataSource['sliceOffset']-6:mli.dataSource['sliceOffset']]):
                mli.setProperty('slice{0}.thumb'.format(i), ep.icon)
                mli.setProperty('slice{0}.time'.format(i), ep.startTimestamp and self.timeDisplay(ep.startTimestamp) or '')
        else:
            for i, ep in enumerate(mli.dataSource['slice'][0:6]):
                mli.setProperty('slice{0}.thumb'.format(i), ep.icon)
                mli.setProperty('slice{0}.time'.format(i), ep.startTimestamp and self.timeDisplay(ep.startTimestamp) or '')

        mli.setProperty('slice.offset', str(mli.dataSource['sliceOffset']))

    def addToSlice(self, mli=None, timestamp=None):
        mli = mli or self.channelList.getSelectedItem()
        channel = mli.dataSource['channel']

        try:
            if timestamp:
                if not mli.dataSource['slice']:
                    mli.setProperty('loading', '1')
                    mli.dataSource['slice'] = channel.initialSlice()
                if self.hasDVR():
                    while mli.dataSource['slice'][-1].startTimestamp < timestamp and not self.abort and self.channelList.itemIsSelected(mli):
                        mli.setProperty('loading', '1')
                        mli.dataSource['slice'] += hdhr.guide.slice(self.devices.apiAuthID(), channel, mli.dataSource['slice'][-1].endTimestamp)
            else:
                if mli.dataSource['slice']:
                    if self.hasDVR():
                        mli.setProperty('loading', '1')
                        mli.dataSource['slice'] += hdhr.guide.slice(self.devices.apiAuthID(), channel, mli.dataSource['slice'][-1].endTimestamp)
                else:
                    mli.setProperty('loading', '1')
                    mli.dataSource['slice'] = channel.initialSlice()

            # if False:
            #     for i in range(min(6, len(mli.dataSource['slice']))):
            #         ep = mli.dataSource['slice'][i]
            #         mli.setProperty('slice{0}.thumb'.format(i), ep.icon)
            #         mli.setProperty('slice{0}.time'.format(i), ep.startTimestamp and self.timeDisplay(ep.startTimestamp) or '')
        finally:
            mli.setProperty('loading', '')

    def sliceRight(self):
        mli = self.channelList.getSelectedItem()
        if mli.dataSource['thread'] and mli.dataSource['thread'].isAlive():
            return

        mli.dataSource['thread'] = threading.Thread(target=self._sliceRight, args=(mli,))
        mli.dataSource['thread'].start()

    def _sliceRight(self, mli):
        mli.dataSource['sliceOffset'] += 1

        self.updateSlice(mli)

        self.sliceTimestamp = mli.dataSource['slice'][mli.dataSource['sliceOffset']-1].startTimestamp

        mli.setProperty('slice.offset', str(min(mli.dataSource['sliceOffset'], 6)))

    def sliceLeft(self):
        mli = self.channelList.getSelectedItem()

        mli.dataSource['sliceOffset'] -= 1
        mli.dataSource['sliceOffset'] = max(mli.dataSource['sliceOffset'], 0)

        self.updateSlice()

        self.sliceTimestamp = mli.dataSource['sliceOffset'] and mli.dataSource['slice'][mli.dataSource['sliceOffset']-1].startTimestamp or 0

        mli.setProperty('slice.offset', str(mli.dataSource['sliceOffset']))

    def checkSeekActions(self,action):
        if not self.player.isPlayingRecording():
            return False

        # <f>FastForward</f> <-- ALREADY WORKS
        # <r>Rewind</r> <-- ALREADY WORKS
        # <quote>SmallStepBack</quote> <-- NO ACTION
        # <opensquarebracket>BigStepForward</opensquarebracket> <-- NO ACTION
        # <closesquarebracket>BigStepBack</closesquarebracket> <-- NO ACTION

        # PlayerControl(command): Play, Stop, Forward, Rewind, Next, Previous, BigSkipForward, BigSkipBackward, SmallSkipForward, SmallSkipBackward,

        if action in [xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT, xbmcgui.ACTION_MOVE_UP, xbmcgui.ACTION_MOVE_DOWN]:
            self.seekHandler.onAction(action.getId())
            return True

        if action == xbmcgui.ACTION_PAGE_UP:
            self.seekAction('PlayerControl(Next)')
            return True
        elif action == xbmcgui.ACTION_PAGE_DOWN:
            self.seekAction('PlayerControl(Previous)')
            return True
        elif action == xbmcgui.ACTION_NEXT_ITEM:
            self.seekBackSmall()
            return True
        elif action == xbmcgui.ACTION_PREV_ITEM:
            self.seekBackSmall()
            return True
        elif action == xbmcgui.ACTION_MOVE_LEFT:
            self.seekBackSmall()
            return True
        elif action == xbmcgui.ACTION_MOVE_RIGHT:
            self.seekForwardSmall()
            return True
        elif action == xbmcgui.ACTION_MOVE_UP:
            self.seekAction('PlayerControl(BigSkipForward)')
            return True
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            self.seekAction('PlayerControl(BigSkipBackward)')
            return True
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
            self.seekForwardSmall()
            return True
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
            self.seekBackSmall()
            return True
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_UP:
            self.seekAction('PlayerControl(BigSkipForward)')
            return True
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_DOWN:
            self.seekAction('PlayerControl(BigSkipBackward)')
            return True
        elif action == xbmcgui.ACTION_MOUSE_LEFT_CLICK:
            return True
        # elif self.getFocusId() == 251 and action == xbmcgui.ACTION_MOUSE_DRAG:
        #     return True

        return False

    def seekCallback(self, action):
        if xbmc.getCondVisibility('Player.Seeking') or xbmc.getCondVisibility('Player.Caching'):
           return False

        if action == xbmcgui.ACTION_MOVE_LEFT:
            self.seekBackSmall()
        elif action == xbmcgui.ACTION_MOVE_RIGHT:
            self.seekForwardSmall()
        elif action == xbmcgui.ACTION_MOVE_UP:
            self.seekAction('PlayerControl(BigSkipForward)')
        elif action == xbmcgui.ACTION_MOVE_DOWN:
            self.seekAction('PlayerControl(BigSkipBackward)')
        elif action == xbmcgui.ACTION_PLAY:
            if xbmc.getCondVisibility('Player.Paused'):
                self.player.pause()
                ct = 0
                # Wait till player is actually unpaused before we return, so that initial paused stat var doesn't get confused
                while xbmc.getCondVisibility('Player.Paused') and ct < 20: # Only do this 20 times (2 secs) in case this isn't as safe as I thought :)
                    xbmc.sleep(100)
                    ct += 1

        return True

    def seekBackSmall(self):
        seek = self.player.getTime() - 6
        if seek < 0:
            seek = 0
        self.player.seekTime(seek)

    def seekForwardSmall(self):
        # self.seekAction('PlayerControl(SmallSkipForward)')
        seek = self.player.getTime() + 30
        if seek > self.player.getTotalTime():
            seek = self.player.getTotalTime()
        self.player.seekTime(seek)

    def seekAction(self, action):
        xbmc.executebuiltin(action)

    def onSelect(self,controlID):
        if controlID in (215, 217, 210): #Mouse/touch: handle with onAction()
            #self.sliceRight()
            return

        if self.clickShowOverlay(controlID): return

        if controlID == 201:
            self.channelClicked()

    def channelClicked(self):
        mli = self.channelList.getSelectedItem()

        if mli.getProperty('slice.offset') and mli.getProperty('slice.offset') != '0':
            ep = mli.dataSource['slice'] and mli.dataSource['slice'][mli.dataSource['sliceOffset']-1] or None
            self.openRecordDialog(ep)
        else:
            channel = mli.dataSource['channel']
            self.playChannel(channel)
            self.showOverlay(False)

    @util.busyDialog('BUSY')
    def openRecordDialog(self, ep):
        if not self.hasDVR():
            return

        if not ep:
            return

        if self.dvrWindow:
            return self.dvrWindow.openRecordDialog(None, series=hdhr.guide.Series(ep))

        ss = hdhr.storageservers.StorageServers(self.devices)
        series = hdhr.guide.Series(ep)
        d = dvr.RecordDialog(
            skin.DVR_RECORD_DIALOG,
            skin.getSkinPath(),
            'Main',
            '1080i',
            rule=ss.getSeriesRule(series.ID),
            series=series,
            storage_server=ss,
            show_hide=False
        )

        d.doModal()
        del d

        ep['RecordingRule'] = series.get('RecordingRule')

    def onPlayBackStarted(self):
        util.DEBUG_LOG('ON PLAYBACK STARTED')
        self.fallbackChannel = self.currentIsLive() and self.current.dataSource['channel'] or None
        self.showProgress()

    def onPlayBackStopped(self):
        util.setGlobalProperty('playing.dvr','')
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK STOPPED')
        self.showProgress() #In case we failed to play video on startup
        self.showOverlay(False)
        self.showSeekBar(hide=True)
        self.windowLoop()

    def onPlayBackFailed(self):
        util.setGlobalProperty('playing.dvr','')
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK FAILED')
        self.showProgress() #In case we failed to play video on startup
        self.showSeekBar(hide=True)
        if self.fallbackChannel:
            channel = self.fallbackChannel
            self.fallbackChannel = None
            self.playChannel(channel)
        util.showNotification(util.T(32023),time_ms=5000,header=util.T(32022))
        self.windowLoop()

    def onPlayBackEnded(self):
        util.setGlobalProperty('playing.dvr','')
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK ENDED')
        self.windowLoop()

    def onPlayBackSeek(self, seek_time, seek_offset):
        self.lastSeek = time.time()

    # END - EVENT HANDLERS ####################################################

    def setProperty(self,key,val):
        self._BASE.setProperty(self,key,val)

    def tick(self):
        if xbmc.abortRequested:
            self.doClose()
            util.DEBUG_LOG('Abort requested - closing...')
            return

        if time.time() > self.nextGuideUpdate:
            self.resetNextGuideUpdate()
            self.updateGuide()
            self.updateChannels()
        elif time.time() > self.nextChannelUpdate:
            self.updateChannels()
        else:
            self.updateProgressBars()

    def doClose(self):
        self._BASE.doClose(self)
        if util.getSetting('exit.stops.player',True):
            xbmc.executebuiltin('PlayerControl(Stop)') #self.player.stop() will crash kodi (after a guide list reset at least)
        else:
            if xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'): xbmc.executebuiltin('Action(back)')

    def updateProgressBars(self,force=False):
        if not force and not self.overlayVisible(): return

        if self.currentIsLive():
            self.currentProgress.setPercent(self.current.dataSource['channel'].guide.currentShow().progress() or 0)
        # elif self.currentIsRecorded():
        #     self.currentProgress.setPercent(self.current.progress(self.player.time))

        for mli in self.channelList:
            prog = mli.dataSource['channel'].guide.currentShow().progress()
            if prog == None:
                mli.setProperty('show.progress','')
            else:
                prog = int(prog - (prog % 5))
                mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))

    def setCurrent(self,mli=None,rec=None,force=False):
        if self.current:
            if self.currentIsLive():
                self.current.setProperty('is.current','')
            self.current = None

        if mli and self.player and (self.player.isPlayingHDHR() or force):
            self.current = mli
            self.current.setProperty('is.current','true')
        elif rec:
            self.current = rec

        self.setWinProperties()

    def closeHandler(self):
        if self.hasDVR():
            if self.player.isPlayingRecording():
                self.player.stop()
            else:
                self.windowLoop()
            return True

        if self.overlayVisible():
            if not self.player.isPlaying():
                self.windowLoop()
                return True
            self.showOverlay(False)
        elif self.seekBarVisible():
            self.showSeekBar(hide=True)
        else:
            self.windowLoop()
        return True

    def fullscreenVideo(self):
        if not self.touchMode and util.videoIsPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def setWinProperties(self):
        title = ''
        icon = ''
        nextTitle = ''
        progress = None
        channel = ''

        if self.currentIsLive():
            channel = CHANNEL_DISPLAY.format(self.current.dataSource['channel'].number,self.current.dataSource['channel'].name)
            if self.current.dataSource['channel'].guide:
                currentShow = self.current.dataSource['channel'].guide.currentShow()
                title = currentShow.title
                icon = currentShow.icon
                progress = currentShow.progress()
                nextTitle = u'{0}: {1}'.format(util.T(32004),self.current.dataSource['channel'].guide.nextShow().title or util.T(32005))
        elif self.currentIsRecorded():
            rec = self.current
            title = rec.seriesTitle
            nextTitle = rec.episodeTitle
            icon = rec.icon
            channel = rec.channelName
            progress = rec.progress(self.player.time)

        self.setProperty('show.title',title)
        self.setProperty('show.icon',icon)
        self.setProperty('next.title',nextTitle)
        self.setProperty('channel.name',channel)

        if progress != None:
            self.currentProgress.setPercent(progress)
            self.currentProgress.setVisible(True)
        else:
            self.currentProgress.setPercent(0)
            self.currentProgress.setVisible(False)

    def resetNextGuideUpdate(self,interval=None):
        if not interval:
            interval = GUIDE_UPDATE_INTERVAL + random.SystemRandom().randrange(GUIDE_UPDATE_VARIANT)
        self.nextGuideUpdate = time.time() + interval

    def getLineUpAndGuide(self):
        self.lastDiscovery = time.time()
        if not self.updateLineup(): return False
        self.showProgress(50,util.T(32008))

        if self.devices:
            for d in self.devices.allDevices:
                util.DEBUG_LOG(d.display())

        self.updateGuide()
        self.showProgress(75,util.T(32009))

        return True

    def updateLineup(self,quiet=False):
        try:
            if not self.devices:
                self.devices = hdhr.discovery.Devices()
            else:
                self.devices.reDiscover()

            self.lineUp = hdhr.tuners.LineUp(self.devices)
            return True
        except hdhr.errors.NoCompatibleDevicesException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32011),'',util.T(32012))
            return False
        except hdhr.errors.NoTunersException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32014),'',util.T(32012))
            return False
        except hdhr.errors.EmptyLineupException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32034),'',util.T(32012))
            return False
        except:
            e = util.ERROR()
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32015),e,util.T(32012))
            return False

    def updateGuide(self):
        newLinup = False

        if self.devices.isOld(): #1 hour
            if self.updateLineup(quiet=True):
                newLinup = True
            else:
                util.DEBUG_LOG('Discovery failed!')
                self.resetNextGuideUpdate(300) #Discovery failed, try again in 5 mins
                return False

        err = None
        guide = None
        try:
            guide = hdhr.guide.Guide(self.lineUp)
        except hdhr.errors.NoDeviceAuthException:
            err = util.T(32030)
        except hdhr.errors.NoGuideDataException:
            err = util.T(32031)
        except:
            err = util.ERROR()

        if err:
            if not self.guideFetchPreviouslyFailed: #Only show notification the first time. Don't need this every 5 mins if internet is down
                util.showNotification(err,header=util.T(32013))
                self.resetNextGuideUpdate(300) #Could not get guide data. Check again in 5 minutes
            self.guideFetchPreviouslyFailed = True
            self.setWinProperties()
            if self.lineUp.hasGuideData:
                util.DEBUG_LOG('Next guide update: {0} minutes'.format(int((self.nextGuideUpdate - time.time())/60)))
                return False

        guide = guide or hdhr.guide.Guide()

        self.guideFetchPreviouslyFailed = False

        #Set guide data for each channel
        for channel in self.lineUp.channels.values():
            guideChan = guide.getChannel(channel.number)
            channel.setGuide(guideChan)

        if newLinup:
            self.fillChannelList(update=True)

        self.lineUp.hasGuideData = True

        self.setWinProperties()
        util.DEBUG_LOG('Next guide update: {0} minutes'.format(int((self.nextGuideUpdate - time.time())/60)))
        return True

    def createListItem(self,channel):
        return self.updateListItem(channel,filter_=True)

    def updateListItem(self,channel,mli=None,filter_=False):
        guideChan = channel.guide
        currentShow = guideChan.currentShow()

        if filter_ and self.filter:
            if not channel.matchesFilter(self.filter) and not currentShow.matchesFilter(self.filter):
                return None

        if not mli:
            title = channel.name
            if guideChan.icon: title = CHANNEL_DISPLAY.format(channel.number,title)
            mli = kodigui.ManagedListItem(title,data_source={'channel': channel, 'slice': [], 'sliceOffset': 0, 'thread': None})
            mli.setProperty('channel.icon',guideChan.icon)
            mli.setProperty('channel.number',channel.number)

        end = currentShow.end
        if end and end < self.nextChannelUpdate:
            self.nextChannelUpdate = end

        nextShow = guideChan.nextShow()
        thumb = currentShow.icon

        mli.setThumbnailImage(thumb)
        mli.setProperty('show.title',currentShow.title)
        mli.setProperty('show.synopsis',currentShow.synopsis)
        mli.setProperty('next.title',u'{0}: {1}'.format(util.T(32004),nextShow.title or util.T(32005)))
        mli.setProperty('next.icon',nextShow.icon)
        mli.setProperty('next.start',nextShow.start and time.strftime('%I:%M %p',time.localtime(nextShow.start)) or '')

        prog = currentShow.progress()
        if prog != None:
            prog = int(prog - (prog % 5))
            mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))
        return mli

    def updateChannels(self):
        util.DEBUG_LOG('Updating channels')

        self.nextChannelUpdate = MAX_TIME_INT

        for mli in self.channelList:
            self.updateListItem(mli.dataSource['channel'],mli)


    def fillChannelList(self,update=False):
        last = util.getSetting('last.channel')

        items = []
        current = None
        for channel in self.lineUp.channels.values():
            mli = self.createListItem(channel)
            if not mli: continue

            if last == channel.number:
                current = mli

            items.append(mli)
        if not items:
            return False

        if update:
            self.channelList.replaceItems(items)
        else:
            self.channelList.reset()
            self.channelList.addItems(items)

        if current: self.setCurrent(current)
        return True

    def getStartChannel(self):
        util.DEBUG_LOG('Found {0} total channels'.format(len(self.lineUp)))
        last = util.getSetting('last.channel')
        if last and last in self.lineUp:
            return self.lineUp[last]
        elif len(self.lineUp):
            return self.lineUp.indexed(0)
        return None

    def hasDVR(self):
        return self.devices.hasStorageServers()

    def start(self):
        if not self.getLineUpAndGuide(): #If we fail to get lineUp, just exit
            self.doClose()
            return

        util.setGlobalProperty('DVR_ENABLED',self.hasDVR() and 'true' or '')
        self.fillChannelList()

        self.player = player.HDHRPlayer().init(self,self.devices,self.touchMode)

        channel = self.getStartChannel()
        if not channel:
            xbmcgui.Dialog().ok(util.T(32018),util.T(32017),'',util.T(32012))
            self.doClose()
            return

        if self.player.isPlayingHDHR():
            self.fullscreenVideo()
            self.showProgress()
            if self.player.isPlayingRecording():
                util.DEBUG_LOG('HDHR video already playing (recorded)')
                try:
                    url = self.player.url
                    rec = hdhr.storageservers.StorageServers(self.devices).getRecordingByPlayURL(url)
                    self.setCurrent(rec=rec)
                except:
                    util.ERROR()
            else:
                util.DEBUG_LOG('HDHR video already playing (live)')
                self.setCurrent(self.getListItemByChannel(channel))
        else:
            util.DEBUG_LOG('HDHR video not currently playing. Starting channel...')
            self.playChannel(channel)

        self.selectChannel(channel)

        self.cron.registerReceiver(self)

        self.setFocusId(210) #Set focus now that dummy list is ready

        self.checkIfUpdated()

    def getListItemByChannel(self, channel):
        for mli in self.channelList:
            if mli.dataSource['channel'] == channel:
                return mli
        return None

    def selectChannel(self, channel):
        pos = self.lineUp.index(channel.number)
        if pos > -1:
            self.channelList.selectItem(pos)

    def showProgress(self,progress='',message=''):
        self.setProperty('loading.progress',str(progress))
        self.setProperty('loading.status',message)

    def seekBarVisible(self):
        return self.getProperty('show.seekbar')

    def showSeekBar(self,hide=False):
        if hide:
            self.setProperty('show.seekbar','')
            self.seekBarTimer.stop()
        else:
            self.setProperty('show.seekbar','1')
            self.seekBarTimer.reset()

    def clickShowOverlay(self,controlID=None):
        if self.player.isPlayingRecording():
            if self.overlayVisible():
                self.showOverlay(False)
            self.player.pause()
            # if controlID and controlID == 251:
            #     self.showSeekBar() #Make sure the bar stays visible when we're interacting with it
            # else:
            #     self.showSeekBar(hide=self.seekBarVisible())
            return True
        else:
            if not self.overlayVisible():
                self.showOverlay()
                self.setFocusId(201)
                return True
            elif self.getFocusId() != 201:
                self.showOverlay(False)
                return True
            return False

    def showOverlay(self,show=True,from_filter=False):
        if not self.overlayVisible():
            if not from_filter:
                if not self.clearFilter():
                    self.cron.forceTick()
            else:
                self.cron.forceTick()

        if not show:
            self.channelList.getSelectedItem().setProperty('slice.offset', '0')

        self.setProperty('show.current','')
        self.setProperty('show.overlay',show and 'SHOW' or '')
        self.propertyTimer.reset()
        if show and self.getFocusId() != 201: self.setFocusId(201)

    def overlayTimerCallback(self, property):
        mli = self.channelList.getSelectedItem()
        if mli.getProperty('loading'):
            self.showOverlay()
        mli.setProperty('slice.offset', '0')

    def overlayVisible(self):
        return bool(self.getProperty('show.overlay'))

    def windowLoop(self):
        if self.inLoop: return
        self.inLoop = True
        while not xbmc.abortRequested and not self._closing:
            if self.openDVRWindow():
                break
            if self.showOptions():
                break
            if self.player.isPlaying():
                break
        self.inLoop = False

    def showOptions(self):
        if not self.optionsDialog:
            path = util.ADDON.getAddonInfo('path')
            self.optionsDialog = OptionsDialog(skin.OPTIONS_DIALOG,path,'Main','1080i')

        self.optionsDialog.modal()

        option = self.optionsDialog.option
        self.optionsDialog.option = None

        if option == 'SEARCH':
            self.setFilter()
            return True
        elif option == 'LIVETV':
            channel = self.getStartChannel()
            if channel:
                self.playChannel(channel)
            else:
                self.player.stop()
            return True
        elif option == 'EXIT':
            self.doClose()
            return True


    def openDVRWindow(self):
        if not self.hasDVR():
            return

        if (self.dvrWindow and self.dvrWindow.open) or (self.optionsDialog and self.optionsDialog.open):
            return

        if not self.dvrWindow:
            path = skin.getSkinPath()
            if util.getSetting('touch.mode',False):
                self.dvrWindow = dvr.DVRWindow(skin.DVR_WINDOW,path,'Main','1080i',main=self)
            else:
                self.dvrWindow = dvr.DVRDialog(skin.DVR_WINDOW,path,'Main','1080i',main=self)

        self.dvrWindow.modal()

        self.showProgress() #Hide the progress because of re-init triggering <onload>


        if self.dvrWindow.play:
            self.showOverlay(False)
            util.setGlobalProperty('window.animations',util.getSetting('window.animations',True) and '1' or '')

            if isinstance(self.dvrWindow.play, hdhr.storageservers.Recording):
                rec = self.dvrWindow.play
                self.playRecording(rec)
                util.setGlobalProperty('playing.dvr','1')
            else:
                self.playChannelByNumber(self.dvrWindow.play.channelNumber)

            self.dvrWindow.play = None


            return True

        return False

    def playRecording(self,rec):
        self.setCurrent(rec=rec)
        self.player.playRecording(rec)
        self.fullscreenVideo()

    def playChannel(self,channel):
        self.setCurrent(self.getListItemByChannel(channel),force=True)
        self.player.playChannel(channel)
        self.fullscreenVideo()

    def playChannelByNumber(self,number):
        if number in self.lineUp:
            channel = self.lineUp[number]
            self.playChannel(channel)
            self.selectChannel(channel)
            return channel
        return None

    def currentIsLive(self):
        return self.current and isinstance(self.current,kodigui.ManagedListItem)

    def currentIsRecorded(self):
        return self.current and isinstance(self.current,hdhr.storageservers.Recording)

    def checkChannelEntry(self,action):
        if action.getId() >= xbmcgui.REMOTE_0 and action.getId() <= xbmcgui.REMOTE_9:
            self.doChannelEntry(str(action.getId() - 58))
            return True
        return False

    def doChannelEntry(self,digit):
        window = KodiChannelEntry(skin.CHANNEL_ENTRY,skin.getSkinPath(),'Main','1080p',digit=digit,has_sub_channels=self.lineUp.hasSubChannels)
        window.doModal()
        channelNumber = window.getChannel()
        del window
        if not channelNumber: return
        util.DEBUG_LOG('Channel entered: {0}'.format(channelNumber))
        if not channelNumber in self.lineUp: return
        channel = self.lineUp[channelNumber]
        self.playChannel(channel)
        self.selectChannel(channel)

    def channelUp(self):
        self.channelChange(1)

    def channelDown(self):
        self.channelChange(-1)

    def channelChange(self,offset):
        if not self.currentIsLive(): return
        currentChannel = self.current.dataSource['channel'].number
        pos = self.lineUp.index(currentChannel)
        pos += offset
        channel = self.lineUp.indexed(pos)
        if not channel: return
        self.setProperty('show.current','true')
        self.currentDetailsTimer.reset()
        self.playChannel(channel)
        self.selectChannel(channel)

    def clearFilter(self):
        if not self.filter: return False
        self.filter = None
        if not self.currentIsLive(): self.current = None
        self.fillChannelList()
        channel = self.getStartChannel()
        self.selectChannel(channel)
        return True

    def setFilter(self):
        terms = xbmcgui.Dialog().input(util.T(32024))
        if not terms: return self.clearFilter()
        self.filter = terms.lower() or None
        if not self.currentIsLive(): self.current = None
        if not self.fillChannelList():
            self.filter = None
            xbmcgui.Dialog().ok(util.T(32025),util.T(32026))
            return
        self.showOverlay(from_filter=True)
        self.setFocusId(201)

    def shutdown(self):
        util.DEBUG_LOG('Shutting down...')
        if self.propertyTimer:
            self.propertyTimer.close()
        util.DEBUG_LOG('Overlay timer done')
        if  self.currentDetailsTimer:
            self.currentDetailsTimer.close()
        util.DEBUG_LOG('Details timer done')

    def checkIfUpdated(self):
        lastAPILevel = util.getSetting('API.LEVEL',0)
        util.setSetting('API.LEVEL',API_LEVEL)

        if not lastAPILevel:
            return self.firstRun()
        elif lastAPILevel < 2:
            util.showTextDialog('Info',util.T(32100))

    def firstRun(self):
        util.showTextDialog('Info',util.T(32100))

class GuideOverlayWindow(GuideOverlay,kodigui.BaseWindow):
    _BASE = kodigui.BaseWindow

class GuideOverlayDialog(GuideOverlay,kodigui.BaseDialog):
    _BASE = kodigui.BaseDialog

class BackgroundWindow(kodigui.BaseWindow):
    def onAction(self, action):
        return

def start():
    util.LOG('Version: {0}'.format(util.ADDON.getAddonInfo('version')))
    util.DEBUG_LOG('Current Kodi skin: {0}'.format(skin.currentKodiSkin()))

    util.setGlobalProperty('guide.full.detail',util.getSetting('guide.full.detail',False) and 'true' or '')
    util.setGlobalProperty('DVR_ENABLED','')
    util.setGlobalProperty('busy','')
    util.setGlobalProperty('window.animations',util.getSetting('window.animations',True) and '1' or '')
    util.setGlobalProperty('search.terms','')

    path = skin.getSkinPath()

    back = BackgroundWindow('script-hdhomerun-view-background.xml',path,'Main','1080i')
    back.show()

    if util.getSetting('touch.mode',False):
        util.setGlobalProperty('touch.mode','true')
        window = GuideOverlayWindow(skin.OVERLAY,path,'Main','1080i')
        window.touchMode = True
    else:
        #player.FullsceenVideoInitializer().start()
        util.setGlobalProperty('touch.mode','')
        window = GuideOverlayDialog(skin.OVERLAY,path,'Main','1080i')

    with util.Cron(5) as window.cron:
        window.doModal()
        window.shutdown()
        window.abort = True
        del window

    threads = threading.enumerate()
    while len(threads) > 1:
        util.DEBUG_LOG('Waiting on {0} threads...'.format(len(threads) - 1))
        threads = threading.enumerate()
        for t in threads:
            if t != threading.currentThread():
                t.join()
                break

    back.doClose()
    del back

    util.DEBUG_LOG('Finished')

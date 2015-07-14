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

        self.propertyTimer = kodigui.PropertyTimer(self._winID,util.getSetting('overlay.timeout',0),'show.overlay','')
        self.currentDetailsTimer = kodigui.PropertyTimer(self._winID,5,'show.current','')
        self.seekBarTimer = kodigui.PropertyTimer(self._winID,5,'show.seekbar','')

        self.channelList = kodigui.ManagedControlList(self,201,3)
        self.currentProgress = self.getControl(250)

        #Add item to dummy list - this list allows right click on video to bring up the context menu
        self.getControl(210).addItem(xbmcgui.ListItem(''))

        self.start()

    def onAction(self,action):
        try:
            #'{"jsonrpc": "2.0", "method": "Input.ShowCodec", "id": 1}'
            if self.overlayVisible(): self.propertyTimer.reset()


            if action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return

            if self.checkSeekActions(action):
                self._BASE.onAction(self, action)
                self.showSeekBar()
                return

            if action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
                if not self.overlayVisible():
                    return self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                return self.showOverlay()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                return self.showOptions()
            elif action == xbmcgui.ACTION_MOVE_LEFT or action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
                return self.showOverlay(False)
            elif action == xbmcgui.ACTION_BUILT_IN_FUNCTION:
                if self.clickShowOverlay(): return
            elif self.checkChannelEntry(action):
                return
            elif action == xbmcgui.ACTION_CHANNEL_UP: #or action == xbmcgui.ACTION_PAGE_UP: #For testing
                self.channelUp()
            elif action == xbmcgui.ACTION_CHANNEL_DOWN: #or action == xbmcgui.ACTION_PAGE_DOWN: #For testing
                self.channelDown()
        except:
            util.ERROR()
            self._BASE.onAction(self,action)
            return
        self._BASE.onAction(self,action)

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
        seek = self.player.getTime() + 30
        if seek > self.player.getTotalTime():
            seek = self.player.getTotalTime()
        self.player.seekTime(seek)

    def seekAction(self, action):
        xbmc.executebuiltin(action)

    def onClick(self,controlID):
        if self.clickShowOverlay(controlID): return

        if controlID == 201:
            mli = self.channelList.getSelectedItem()
            channel = mli.dataSource
            self.playChannel(channel)
            self.showOverlay(False)

    def onPlayBackStarted(self):
        util.DEBUG_LOG('ON PLAYBACK STARTED')
        self.fallbackChannel = self.currentIsLive() and self.current.dataSource or None
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
            self.currentProgress.setPercent(self.current.dataSource.guide.currentShow().progress() or 0)
        # elif self.currentIsRecorded():
        #     self.currentProgress.setPercent(self.current.progress(self.player.time))

        for mli in self.channelList:
            prog = mli.dataSource.guide.currentShow().progress()
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
            channel = CHANNEL_DISPLAY.format(self.current.dataSource.number,self.current.dataSource.name)
            if self.current.dataSource.guide:
                currentShow = self.current.dataSource.guide.currentShow()
                title = currentShow.title
                icon = currentShow.icon
                progress = currentShow.progress()
                nextTitle = u'{0}: {1}'.format(util.T(32004),self.current.dataSource.guide.nextShow().title or util.T(32005))
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
                if self.player: self.player.init(self,self.lineUp,self.touchMode)
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
            mli = kodigui.ManagedListItem(title,data_source=channel)
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
            self.updateListItem(mli.dataSource,mli)


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
                mli = self.channelList.getListItemByDataSource(channel)
                self.setCurrent(mli)
        else:
            util.DEBUG_LOG('HDHR video not currently playing. Starting channel...')
            self.playChannel(channel)

        self.selectChannel(channel)

        self.cron.registerReceiver(self)

        self.setFocusId(210) #Set focus now that dummy list is ready

        self.checkIfUpdated()

    def selectChannel(self,channel):
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
            if controlID and controlID == 251:
                self.showSeekBar() #Make sure the bar stays visible when we're interacting with it
            else:
                self.showSeekBar(hide=self.seekBarVisible())
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

        self.setProperty('show.current','')
        self.setProperty('show.overlay',show and 'SHOW' or '')
        self.propertyTimer.reset()
        if show and self.getFocusId() != 201: self.setFocusId(201)

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
            rec = self.dvrWindow.play
            self.playRecording(rec)
            self.dvrWindow.play = None
            util.setGlobalProperty('window.animations',util.getSetting('window.animations',True) and '1' or '')
            util.setGlobalProperty('playing.dvr','1')
            return True

        return False

    def playRecording(self,rec):
        self.setCurrent(rec=rec)
        self.player.playRecording(rec)
        self.fullscreenVideo()

    def playChannel(self,channel):
        self.setCurrent(self.channelList.getListItemByDataSource(channel),force=True)
        self.player.playChannel(channel)
        self.fullscreenVideo()

    def playChannelByNumber(self,number):
        if number in self.lineUp:
            channel = self.lineUp[number]
            self.playChannel(channel)
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
        currentChannel = self.current.dataSource.number
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

def start():
    util.LOG('Version: {0}'.format(util.ADDON.getAddonInfo('version')))
    util.DEBUG_LOG('Current Kodi skin: {0}'.format(skin.currentKodiSkin()))

    util.setGlobalProperty('guide.full.detail',util.getSetting('guide.full.detail',False) and 'true' or '')
    util.setGlobalProperty('DVR_ENABLED','')
    util.setGlobalProperty('busy','')
    util.setGlobalProperty('window.animations',util.getSetting('window.animations',True) and '1' or '')
    util.setGlobalProperty('search.terms','')

    path = skin.getSkinPath()
    if util.getSetting('touch.mode',False):
        util.setGlobalProperty('touch.mode','true')
        window = GuideOverlayWindow(skin.OVERLAY,path,'Main','1080i')
        window.touchMode = True
    else:
        player.FullsceenVideoInitializer().start()
        util.setGlobalProperty('touch.mode','')
        window = GuideOverlayDialog(skin.OVERLAY,path,'Main','1080i')

    with util.Cron(5) as window.cron:
        window.doModal()
        window.shutdown()
        del window
    util.DEBUG_LOG('Finished')

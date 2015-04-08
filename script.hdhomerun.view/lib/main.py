# -*- coding: utf-8 -*-
import time, random
import xbmc, xbmcgui

import hdhr
import kodigui
import util
import player
import skin

API_LEVEL = 1

CHANNEL_DISPLAY = u'[COLOR FF99CCFF]{0}[/COLOR] {1}'
GUIDE_UPDATE_INTERVAL = 3300 #55 mins
GUIDE_UPDATE_VARIANT = 600 #10 mins

class BaseWindow(xbmcgui.WindowXML):
    def __init__(self,*args,**kwargs):
        self._closing = False
        self._winID = ''

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowId()

    def setProperty(self,key,value):
        if self._closing: return
        xbmcgui.Window(self._winID).setProperty(key,value)
        xbmcgui.WindowXML.setProperty(self,key,value)

    def doClose(self):
        self._closing = True
        self.close()

    def onClosed(self): pass

class BaseDialog(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self._closing = False
        self._winID = ''

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowDialogId()

    def setProperty(self,key,value):
        if self._closing: return
        xbmcgui.Window(self._winID).setProperty(key,value)
        xbmcgui.WindowXMLDialog.setProperty(self,key,value)

    def doClose(self):
        self._closing = True
        self.close()

    def onClosed(self): pass

class KodiChannelEntry(BaseDialog):
    def __init__(self,*args,**kwargs):
        self.digits = str(kwargs['digit'])
        self.hasSubChannels = kwargs.get('has_sub_channels',False)
        self.channel = ''
        self.set = False
        BaseDialog.__init__(self,*args,**kwargs)

    def onInit(self):
        BaseDialog.onInit(self)
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
            BaseDialog.onAction(self,action)
            return

        BaseDialog.onAction(self,action)

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

class OptionsDialog(BaseDialog):
    def __init__(self,*args,**kwargs):
        self.main = kwargs.get('main')
        self.touchMode = kwargs.get('touch_mode',False)
        BaseDialog.__init__(self,*args,**kwargs)

    def onInit(self):
        BaseDialog.onInit(self)
        self.searchClicked = False
        self.setFocusId(240)
        self.main.propertyTimer.reset(self)

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT or  action == xbmcgui.ACTION_MOVE_LEFT:
                return self.doClose()
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                print 'TEST'
                return self.doClose()

            self.main.propertyTimer.reset(self)
        except:
            return BaseDialog.onAction(self,action)

        BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        if controlID in (238,244,245): return
        if controlID == 241: self.searchClicked = True
        self.doClose()


class GuideOverlay(util.CronReceiver):
    _BASE = None
    def __init__(self,*args,**kwargs):
        self._BASE.__init__(self,*args,**kwargs)
        self.started = False
        self.touchMode = False
        self.lineUp = None
        self.guide = None
        self.current = None
        self.fallbackChannel = None
        self.cron = None
        self.guideFetchPreviouslyFailed = False
        self.resetNextGuideUpdate()
        self.lastDiscovery = time.time()
        self.filter = None
        self.optionsDialog = None

    #==========================================================================
    # EVENT HANDLERS
    #==========================================================================
    def onInit(self):
        self._BASE.onInit(self)
        if self.started: return
        if self.touchMode:
            util.DEBUG_LOG('Touch mode: ENABLED')
            self.setProperty('touch.mode','True')
        else:
            util.DEBUG_LOG('Touch mode: DISABLED')
        self.started = True

        self.propertyTimer = kodigui.PropertyTimer(self._winID,util.getSetting('overlay.timeout',0),'show.overlay','')
        self.currentDetailsTimer = kodigui.PropertyTimer(self._winID,5,'show.current','')

        self.channelList = kodigui.ManagedControlList(self,201,3)
        self.currentProgress = self.getControl(250)

        #Add item to dummy list - this list allows right click on video to bring up the context menu
        self.getControl(210).addItem(xbmcgui.ListItem(''))

        self.start()

    def onAction(self,action):
        try:
            #'{"jsonrpc": "2.0", "method": "Input.ShowCodec", "id": 1}'
            if self.overlayVisible(): self.propertyTimer.reset()
            if action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
                if self.overlayVisible():
                    return self.showOptions()
                else:
                    return self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                return self.showOverlay()
            elif action == xbmcgui.ACTION_CONTEXT_MENU:
                return self.showOptions()
#            elif action == xbmcgui.ACTION_SELECT_ITEM:
#                if self.clickShowOverlay(): return
            elif action == xbmcgui.ACTION_MOVE_LEFT or action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
                return self.showOverlay(False)
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return
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

    def onClick(self,controlID):
        if self.clickShowOverlay(): return

        if controlID == 201:
            mli = self.channelList.getSelectedItem()
            channel = mli.dataSource
            self.playChannel(channel)

    def onPlayBackStarted(self):
        util.DEBUG_LOG('ON PLAYBACK STARTED')
        self.fallbackChannel = self.current and self.current.dataSource or None
        self.showProgress()

    def onPlayBackStopped(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK STOPPED')
        self.showProgress() #In case we failed to play video on startup
        self.showOverlay()

    def onPlayBackFailed(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK FAILED')
        self.showProgress() #In case we failed to play video on startup
        if self.fallbackChannel:
            channel = self.fallbackChannel
            self.fallbackChannel = None
            self.playChannel(channel)
        util.showNotification(util.T(32023),time_ms=5000,header=util.T(32022))

    def onPlayBackEnded(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK ENDED')
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

        if self.current:
            self.currentProgress.setPercent(self.current.dataSource.guide.currentShow().progress() or 0)

        for mli in self.channelList:
            prog = mli.dataSource.guide.currentShow().progress()
            if prog == None:
                mli.setProperty('show.progress','')
            else:
                prog = int(prog - (prog % 5))
                mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))

    def setCurrent(self,mli=None):
        if self.current:
            self.current.setProperty('is.current','')
            self.current = None
        if not mli: return self.setWinProperties()
        self.current = mli
        self.current.setProperty('is.current','true')
        self.setWinProperties()

    def closeHandler(self):
        if self.overlayVisible():
            if not self.player.isPlaying():
                return self.handleExit()
            self.showOverlay(False)
            return True
        else:
            return self.handleExit()

    def handleExit(self):
        if util.getSetting('confirm.exit',True):
            if not xbmcgui.Dialog().yesno(util.T(32006),'',util.T(32007),''): return True
        self.doClose()
        return True


    def fullscreenVideo(self):
        if not self.touchMode and util.videoIsPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def resetNextGuideUpdate(self,interval=None):
        if not interval:
            interval = GUIDE_UPDATE_INTERVAL + random.SystemRandom().randrange(GUIDE_UPDATE_VARIANT)
        self.nextGuideUpdate = time.time() + interval

    def getLineUpAndGuide(self):
        self.lastDiscovery = time.time()
        if not self.updateLineup(): return False
        self.showProgress(50,util.T(32008))

        for d in self.lineUp.devices.values():
            util.DEBUG_LOG(d.display())

        self.updateGuide()
        self.showProgress(75,util.T(32009))

        return True

    def updateLineup(self,quiet=False):
        try:
            self.lineUp = hdhr.LineUp()
            return True
        except hdhr.NoCompatibleDevicesException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32011),'',util.T(32012))
            return False
        except hdhr.NoDevicesException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32014),'',util.T(32012))
            return False
        except hdhr.EmptyLineupException:
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32034),'',util.T(32012))
            return False
        except:
            e = util.ERROR()
            if not quiet: xbmcgui.Dialog().ok(util.T(32016),util.T(32015),e,util.T(32012))
            return False

    def updateGuide(self):
        if self.lineUp.isOld(): #1 hour
            if not self.updateLineup(quiet=True):
                util.DEBUG_LOG('Discovery failed!')
                self.resetNextGuideUpdate(300) #Discovery failed, try again in 5 mins
                return False

        err = None
        guide = None
        try:
            guide = hdhr.Guide(self.lineUp)
        except hdhr.NoDeviceAuthException:
            err = util.T(32030)
        except hdhr.NoGuideDataException:
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

        guide = guide or hdhr.Guide()

        self.guideFetchPreviouslyFailed = False

        #Set guide data for each channel
        for channel in self.lineUp.channels.values():
            guideChan = guide.getChannel(channel.number)
            channel.setGuide(guideChan)

        self.lineUp.hasGuideData = True

        self.setWinProperties()
        util.DEBUG_LOG('Next guide update: {0} minutes'.format(int((self.nextGuideUpdate - time.time())/60)))
        return True

    def setWinProperties(self):
        title = ''
        icon = ''
        nextTitle = ''
        progress = None
        channel = ''
        if self.current:
            channel = CHANNEL_DISPLAY.format(self.current.dataSource.number,self.current.dataSource.name)
            if self.current.dataSource.guide:
                currentShow = self.current.dataSource.guide.currentShow()
                title = currentShow.title
                icon = currentShow.icon
                progress = currentShow.progress()
                nextTitle = u'{0}: {1}'.format(util.T(32004),self.current.dataSource.guide.nextShow().title or util.T(32005))

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

    def updateChannels(self):
        util.DEBUG_LOG('Updating channels')
        self.updateGuide()
        for mli in self.channelList:
            guideChan = mli.dataSource.guide
            currentShow = guideChan.currentShow()
            nextShow = guideChan.nextShow()
            title = mli.dataSource.name
            thumb = currentShow.icon
            icon = guideChan.icon
            if icon: title = CHANNEL_DISPLAY.format(mli.dataSource.number,title)
            mli.setLabel(title)
            mli.setThumbnailImage(thumb)
            mli.setProperty('show.title',currentShow.title)
            mli.setProperty('show.synopsis',currentShow.synopsis)
            mli.setProperty('next.title',u'{0}: {1}'.format(util.T(32004),nextShow.title or util.T(32005)))
            mli.setProperty('next.icon',nextShow.icon)
            start = nextShow.start
            if start:
                mli.setProperty('next.start',time.strftime('%I:%M %p',time.localtime(start)))
            prog = currentShow.progress()
            if prog != None:
                prog = int(prog - (prog % 5))
                mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))

    def fillChannelList(self):
        last = util.getSetting('last.channel')

        self.channelList.reset()

        items = []
        for channel in self.lineUp.channels.values():
            guideChan = channel.guide
            currentShow = guideChan.currentShow()
            if self.filter:
                if not channel.matchesFilter(self.filter) and not currentShow.matchesFilter(self.filter): continue
            nextShow = guideChan.nextShow()
            title = channel.name
            thumb = currentShow.icon
            icon = guideChan.icon
            if icon: title = CHANNEL_DISPLAY.format(channel.number,title)
            item = kodigui.ManagedListItem(title,thumbnailImage=thumb,data_source=channel)
            item.setProperty('channel.icon',icon)
            item.setProperty('channel.number',channel.number)
            item.setProperty('show.title',currentShow.title)
            item.setProperty('show.synopsis',currentShow.synopsis)
            item.setProperty('next.title',u'{0}: {1}'.format(util.T(32004),nextShow.title or util.T(32005)))
            item.setProperty('next.icon',nextShow.icon)
            start = nextShow.start
            if start:
                item.setProperty('next.start',time.strftime('%I:%M %p',time.localtime(start)))
            if last == channel.number:
                self.setCurrent(item)
            prog = currentShow.progress()
            if prog != None:
                prog = int(prog - (prog % 5))
                item.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))
            items.append(item)

        self.channelList.addItems(items)

    def getStartChannel(self):
        util.DEBUG_LOG('Found {0} total channels'.format(len(self.lineUp)))
        last = util.getSetting('last.channel')
        if last and last in self.lineUp:
            return self.lineUp[last]
        elif len(self.lineUp):
            return self.lineUp.indexed(0)
        return None

    def start(self):
        if not self.getLineUpAndGuide(): #If we fail to get lineUp, just exit
            self.doClose()
            return

        self.fillChannelList()

        self.player = player.ChannelPlayer().init(self,self.lineUp,self.touchMode)

        channel = self.getStartChannel()
        if not channel:
            xbmcgui.Dialog().ok(util.T(32018),util.T(32017),'',util.T(32012))
            self.doClose()
            return

        if self.player.isPlayingHDHR():
            util.DEBUG_LOG('HDHR video already playing')
            self.fullscreenVideo()
            self.showProgress()
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

    def clickShowOverlay(self):
        if not self.overlayVisible():
            self.showOverlay()
            self.setFocusId(201)
            return True
        elif not self.getFocusId() == 201:
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

    def showOptions(self):
        if self.optionsDialog: return
        path = util.ADDON.getAddonInfo('path')
        self.optionsDialog = OptionsDialog(skin.OPTIONS_DIALOG,path,'Main','1080i',main=self)
        self.optionsDialog.doModal()
        search = self.optionsDialog.searchClicked
        self.optionsDialog = None
        if search: self.setFilter()

    def playChannel(self,channel):
        self.setCurrent(self.channelList.getListItemByDataSource(channel))
        self.player.playChannel(channel)
        self.fullscreenVideo()

    def playChannelByNumber(self,number):
        if number in self.lineUp:
            channel = self.lineUp[number]
            self.playChannel(channel)
            return channel
        return None

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
        self.current = None
        self.fillChannelList()
        channel = self.getStartChannel()
        self.selectChannel(channel)
        return True

    def setFilter(self):
        terms = xbmcgui.Dialog().input(util.T(32024))
        if not terms: return self.clearFilter()
        self.filter = terms.lower() or None
        self.current = None
        self.fillChannelList()
        self.showOverlay(from_filter=True)
        self.setFocusId(201)

    def checkIfUpdated(self):
        lastAPILevel = util.getSetting('API.LEVEL')
        util.setSetting('API.LEVEL',API_LEVEL)

        if not lastAPILevel:
            return self.firstRun()

    def firstRun(self):
        util.showTextDialog('Info',util.T(32100))

class GuideOverlayWindow(GuideOverlay,BaseWindow):
    _BASE = BaseWindow

class GuideOverlayDialog(GuideOverlay,BaseDialog):
    _BASE = BaseDialog

def start():
    util.LOG('Version: {0}'.format(util.ADDON.getAddonInfo('version')))
    util.DEBUG_LOG('Current Kodi skin: {0}'.format(skin.currentKodiSkin()))

    util.setGlobalProperty('guide.full.detail',util.getSetting('guide.full.detail',False) and 'true' or '')

    path = skin.getSkinPath()
    if util.getSetting('touch.mode',False):
        util.setGlobalProperty('touch.mode','true')
        window = GuideOverlayWindow(skin.OVERLAY,path,'Main','1080i')
        window.touchMode = True
    else:
        util.setGlobalProperty('touch.mode','')
        window = GuideOverlayDialog(skin.OVERLAY,path,'Main','1080i')

    with util.Cron(5) as window.cron:
        window.doModal()
        util.DEBUG_LOG('Shutting down...')
        window.propertyTimer.close()
        util.DEBUG_LOG('Overlay timer done')
        window.currentDetailsTimer.close()
        util.DEBUG_LOG('Details timer done')
        del window
    util.DEBUG_LOG('Finished')
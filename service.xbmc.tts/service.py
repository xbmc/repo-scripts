import sys, re, xbmc, xbmcgui, time, Queue
import json
from lib import util, addoninfo
T = util.T

__version__ = util.xbmcaddon.Addon().getAddonInfo('version')
util.LOG(__version__)
util.LOG('Platform: {0}'.format(sys.platform))

from lib import backends
from lib import windows
from lib.windows import playerstatus, notice, backgroundprogress

if backends.audio.PLAYSFX_HAS_USECACHED:
    util.LOG('playSFX() has useCached')
else:
    util.LOG('playSFX() does NOT have useCached')

util.initCommands()
addoninfo.initAddonsData()

RESET = False
def resetAddon():
    global RESET
    if RESET: return
    RESET = True
    util.LOG('Resetting addon...')
    xbmc.executebuiltin('XBMC.RunScript(special://home/addons/service.xbmc.tts/enabler.py,RESET)')

class TTSClosedException(Exception): pass

class TTSService(xbmc.Monitor):
    def __init__(self):
        self.readerOn = True
        self.stop = False
        self.disable = False
        self.noticeQueue = Queue.Queue()
        self.initState()
        self._tts = None
        self.backendProvider = None
        util.stopSounds() #To kill sounds we may have started before an update
        util.playSound('on')
        self.playerStatus = playerstatus.PlayerStatus(10115).init()
        self.bgProgress = backgroundprogress.BackgroundProgress(10151).init()
        self.noticeDialog = notice.NoticeDialog(10107).init()
        self.initTTS()
        util.LOG('SERVICE STARTED :: Interval: %sms' % self.tts.interval)

    def onAbortRequested(self):
        self.stop = True
        try:
            self.tts._close()
        except TTSClosedException:
            pass

    @property
    def tts(self):
        if self._tts._closed: raise TTSClosedException()
        return self._tts

    def onSettingsChanged(self):
        try:
            self.tts._update()
        except TTSClosedException:
            return
        self.checkBackend()
        self.reloadSettings()
        self.updateInterval()
        #Deprecated for the addon starting with Gotham - now using NotifyAll (Still used for SHUTDOWN until I figure out the issue when using NotifyAll with that)
        command = util.getCommand()
        if not command: return
        self.processCommand(command)

    def processCommand(self,command,data=None):
        from lib import util #Earlier import apparently not seen when called via NotifyAll
        util.LOG(command)
        if command == 'REPEAT':
            self.repeatText()
        elif command == 'EXTRA':
            self.sayExtra()
        elif command == 'ITEM_EXTRA':
            self.sayItemExtra()
        elif command == 'VOL_UP':
            self.volumeUp()
        elif command == 'VOL_DOWN':
            self.volumeDown()
        elif command == 'STOP':
            self.stopSpeech()
        elif command == 'SHUTDOWN':
            self.shutdown()
        elif command == 'SAY':
            if not data: return
            args = json.loads(data)
            if not args: return
            text = args.get('text')
            if text:
                self.queueNotice(util.safeDecode(text),args.get('interrupt'))
        elif command == 'SETTINGS.BACKEND_DIALOG':
            util.runInThread(util.selectBackend,name='SETTINGS.BACKEND_DIALOG')
        elif command == 'SETTINGS.PLAYER_DIALOG':
            if not data: return
            args = json.loads(data)
            if not args: return
            backend = args.get('backend')
            util.selectPlayer(backend)
        elif command == 'SETTINGS.SETTING_DIALOG':
            if not data: return
            args = json.loads(data)
            util.selectSetting(*args)
#        elif command.startswith('keymap.'): #Not using because will import keymapeditor into running service. May need if RunScript is not working as was my spontaneous experience
#            command = command[7:]
#            from lib import keymapeditor
#            util.runInThread(keymapeditor.processCommand,(command,),name='keymap.INSTALL_DEFAULT')

    def reloadSettings(self):
        self.readerOn = not util.getSetting('reader_off',False)
        util.DEBUG = util.getSetting('debug_logging',True)
        self.speakListCount = util.getSetting('speak_list_count',True)
        self.autoItemExtra = False
        if util.getSetting('auto_item_extra',False):
            self.autoItemExtra = util.getSetting('auto_item_extra_delay',2)

    def onDatabaseScanStarted(self,database):
        util.LOG('DB SCAN STARTED: {0} - Notifying...'.format(database))
        self.queueNotice(u'{0}: {1}'.format(database,T(32100)))

    def onDatabaseUpdated(self,database):
        util.LOG('DB SCAN UPDATED: {0} - Notifying...'.format(database))
        self.queueNotice(u'{0}: {1}'.format(database,T(32101)))

    def onNotification(self, sender, method, data):
        if not sender == 'service.xbmc.tts': return
        self.processCommand(method.split('.',1)[-1],data) #Remove the "Other." prefix
#        util.LOG('NOTIFY: {0} :: {1} :: {2}'.format(sender,method,data))
#        #xbmc :: VideoLibrary.OnUpdate :: {"item":{"id":1418,"type":"episode"}}

    def queueNotice(self,text,interrupt=False):
        assert isinstance(text,unicode), "Not Unicode"
        self.noticeQueue.put((text,interrupt))

    def clearNoticeQueue(self):
        try:
            while not self.noticeQueue.empty():
                self.noticeQueue.get()
                self.noticeQueue.task_done()
        except Queue.Empty:
            return

    def checkNoticeQueue(self):
        if self.noticeQueue.empty(): return False
        while not self.noticeQueue.empty():
            text, interrupt = self.noticeQueue.get()
            self.sayText(text,interrupt)
            self.noticeQueue.task_done()
        return True

    def initState(self):
        if xbmc.abortRequested or self.stop: return
        self.winID = None
        self.windowReader = None
        self.controlID = None
        self.text = None
        self.textCompare = None
        self.secondaryText = None
        self.keyboardText = u''
        self.progressPercent = u''
        self.lastProgressPercentUnixtime = 0
        self.interval = 400
        self.listIndex = None
        self.waitingToReadItemExtra = None
        self.reloadSettings()

    def initTTS(self,backendClass=None):
        if not backendClass: backendClass = backends.getBackend()
        provider = self.setBackend(backendClass())
        self.backendProvider = provider
        self.updateInterval()
        util.LOG('Backend: %s' % provider)

    def fallbackTTS(self,reason=None):
        if reason == 'RESET': return resetAddon()
        backend = backends.getBackendFallback()
        util.LOG('Backend falling back to: {0}'.format(backend.provider))
        self.initTTS(backend)
        self.sayText(T(32102).format(backend.displayName),interrupt=True)
        if reason: self.sayText(u'{0}: {1}'.format(T(32103),reason),interrupt=False)

    def checkNewVersion(self):
        try:
            #Fails on Helix beta 1 on OpenElec #1103
            from distutils.version import LooseVersion
        except ImportError:
            def LooseVersion(v):
                comp = [int(x) for x in re.split(r'a|b',v)[0].split(".")]
                fourth = 2
                fifth = 0
                if 'b' in v:
                    fourth = 1
                    fifth = int(v.split('b')[-1] or 0)
                elif 'a' in 'v':
                    fourth = 0
                    fifth = int(v.split('a')[-1] or 0)
                comp.append(fourth)
                comp.append(fifth)
                return comp


        lastVersion = util.getSetting('version','0.0.0')
        util.setSetting('version',__version__)

        if lastVersion == '0.0.0':
            self.firstRun()
            return True
        elif LooseVersion(lastVersion) < LooseVersion(__version__):
            self.queueNotice(u'{0}... {1}'.format(T(32104),__version__))
            return True
        return False

    def firstRun(self):
        util.LOG('FIRST RUN')
        util.LOG('Installing default keymap')
        from lib import keymapeditor
        keymapeditor.installDefaultKeymap(quiet=True)

    def start(self):
        self.checkNewVersion()
        try:
            while (not xbmc.abortRequested) and (not self.stop):
                #Interface reader mode
                while self.readerOn and (not xbmc.abortRequested) and (not self.stop):
                    xbmc.sleep(self.interval)
                    try:
                        self.checkForText()
                    except RuntimeError:
                        util.ERROR('start()',hide_tb=True)
                    except SystemExit:
                        if util.DEBUG:
                            util.ERROR('SystemExit: Quitting')
                        else:
                            util.LOG('SystemExit: Quitting')
                        break
                    except TTSClosedException:
                        util.LOG('TTSCLOSED')
                    except: #Because we don't want to kill speech on an error
                        util.ERROR('start()',notify=True)
                        self.initState() #To help keep errors from repeating on the loop

                #Idle mode
                while (not self.readerOn) and (not xbmc.abortRequested) and (not self.stop):
                    try:
                        text, interrupt = self.noticeQueue.get_nowait()
                        self.sayText(text,interrupt)
                        self.noticeQueue.task_done()
                    except Queue.Empty:
                        pass
                    except RuntimeError:
                        util.ERROR('start()',hide_tb=True)
                    except SystemExit:
                        if util.DEBUG:
                            util.ERROR('SystemExit: Quitting')
                        else:
                            util.LOG('SystemExit: Quitting')
                        break
                    except TTSClosedException:
                        util.LOG('TTSCLOSED')
                    except: #Because we don't want to kill speech on an error
                        util.ERROR('start()',notify=True)
                        self.initState() #To help keep errors from repeating on the loop
                    for x in range(5): #Check the queue every 100ms, check state every 500ms
                        if self.noticeQueue.empty(): xbmc.sleep(100)
        finally:
            self._tts._close()
            self.end()
            util.playSound('off')
            util.LOG('SERVICE STOPPED')
            if self.disable:
                import enabler
                enabler.disableAddon()

    def end(self):
        if util.DEBUG:
            xbmc.sleep(500) #Give threads a chance to finish
            import threading
            util.LOG('Remaining Threads:')
            for t in threading.enumerate():
                util.LOG('  {0}'.format(t.name))

    def shutdown(self):
        self.stop = True
        self.disable = True

    def updateInterval(self):
        if util.getSetting('override_poll_interval',False):
            self.interval = util.getSetting('poll_interval',self.tts.interval)
        else:
            self.interval = self.tts.interval

    def setBackend(self,backend):
        if self._tts: self._tts._close()
        self._tts = backend
        return backend.provider

    def checkBackend(self):
        provider = util.getSetting('backend',None)
        if provider == self.backendProvider: return
        self.initTTS()

    def checkForText(self):
        self.checkAutoRead()
        newN = self.checkNoticeQueue()
        newW = self.checkWindow(newN)
        newC = self.checkControl(newW)
        newD = newC and self.checkControlDescription(newW) or False
        text, compare = self.windowReader.getControlText(self.controlID)
        secondary = self.windowReader.getSecondaryText()
        if (compare != self.textCompare) or newC:
            self.newText(compare,text,newD,secondary)
        elif secondary != self.secondaryText:
            self.newSecondaryText(secondary)
        else:
            self.checkMonitored()

    def checkMonitored(self):
        monitored = None

        if self.playerStatus.visible():
            monitored = self.playerStatus.getMonitoredText(self.tts.isSpeaking())
        if self.bgProgress.visible():
            monitored = self.bgProgress.getMonitoredText(self.tts.isSpeaking())
        if self.noticeDialog.visible():
            monitored = self.noticeDialog.getMonitoredText(self.tts.isSpeaking())
        if not monitored:
            monitored = self.windowReader.getMonitoredText(self.tts.isSpeaking())
        if monitored:
            if isinstance(monitored,basestring):
                self.sayText(monitored,interrupt=True)
            else:
                self.sayTexts(monitored,interrupt=True)

    def checkAutoRead(self):
        if not self.waitingToReadItemExtra:
            return
        if self.tts.isSpeaking():
            self.waitingToReadItemExtra = time.time()
            return
        if time.time() - self.waitingToReadItemExtra > self.autoItemExtra:
            self.waitingToReadItemExtra = None
            self.sayItemExtra(interrupt=False)

    def repeatText(self):
        self.winID = None
        self.controlID = None
        self.text = None
        self.checkForText()

    def sayExtra(self):
        texts = self.windowReader.getWindowExtraTexts()
        self.sayTexts(texts)

    def sayItemExtra(self,interrupt=True):
        texts = self.windowReader.getItemExtraTexts(self.controlID)
        self.sayTexts(texts,interrupt=interrupt)

    def sayText(self,text,interrupt=False):
        assert isinstance(text,unicode), "Not Unicode"
        if self.tts.dead: return self.fallbackTTS(self.tts.deadReason)
        self.tts.say(self.cleanText(text),interrupt)

    def sayTexts(self,texts,interrupt=True):
        if not texts: return
        assert all(isinstance(t,unicode) for t in texts), "Not Unicode"
        if self.tts.dead: return self.fallbackTTS(self.tts.deadReason)
        self.tts.sayList(self.cleanText(texts),interrupt=interrupt)

    def insertPause(self,ms=500):
        self.tts.insertPause(ms=ms)

    def volumeUp(self):
        msg = self.tts.volumeUp()
        if not msg: return
        self.sayText(msg,interrupt=True)

    def volumeDown(self):
        msg = self.tts.volumeDown()
        if not msg: return
        self.sayText(msg,interrupt=True)

    def stopSpeech(self):
        self.tts._stop()

    def updateWindowReader(self):
        readerClass = windows.getWindowReader(self.winID)
        if self.windowReader:
            self.windowReader.close()
            if readerClass.ID == self.windowReader.ID:
                self.windowReader._reset(self.winID)
                return
        self.windowReader = readerClass(self.winID,self)

    def window(self):
        return xbmcgui.Window(self.winID)

    def checkWindow(self,newN):
        winID = xbmcgui.getCurrentWindowId()
        dialogID = xbmcgui.getCurrentWindowDialogId()
        if dialogID != 9999: winID = dialogID
        if winID == self.winID: return newN
        self.winID = winID
        self.updateWindowReader()
        if util.DEBUG:
            util.LOG('Window ID: {0} Handler: {1} File: {2}'.format(winID,self.windowReader.ID,xbmc.getInfoLabel('Window.Property(xmlfile)')))

        name = self.windowReader.getName()
        if name:
            self.sayText(u'{0}: {1}'.format(T(32105),name),interrupt=not newN)
            self.insertPause()
        else:
            self.sayText(u' ',interrupt=not newN)

        heading = self.windowReader.getHeading()
        if heading:
            self.sayText(heading)
            self.insertPause()

        texts = self.windowReader.getWindowTexts()
        if texts:
            self.insertPause()
            for t in texts:
                self.sayText(t)
                self.insertPause()
        return True

    def checkControl(self,newW):
        if not self.winID: return newW
        controlID = self.window().getFocusId()
        if controlID == self.controlID: return newW
        if util.DEBUG:
            util.LOG('Control: %s' % controlID)
        self.controlID = controlID
        if not controlID: return newW
        return True

    def checkControlDescription(self,newW):
        post = self.getControlPostfix()
        description = self.windowReader.getControlDescription(self.controlID) or ''
        if description or post:
            self.sayText(description + post,interrupt=not newW)
            self.tts.insertPause()
            return True
        return newW

    def newText(self,compare,text,newD,secondary=None):
        self.textCompare = compare
        label2 = xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(self.controlID)).decode('utf-8')
        seasEp = xbmc.getInfoLabel('Container({0}).ListItem.Property(SeasonEpisode)'.format(self.controlID)).decode('utf-8') or u''
        if label2 and seasEp:
                text = u'{0}: {1}: {2} '.format(label2, text,self.formatSeasonEp(seasEp))
        if secondary:
            self.secondaryText = secondary
            text += self.tts.pauseInsert + u' ' + secondary
        self.sayText(text,interrupt=not newD)
        if self.autoItemExtra:
            self.waitingToReadItemExtra = time.time()

    def getControlPostfix(self):
        if not self.speakListCount: return u''
        numItems = xbmc.getInfoLabel('Container({0}).NumItems'.format(self.controlID)).decode('utf-8')
        if numItems: return u'... {0} {1}'.format(numItems,numItems != '1' and T(32107) or T(32106))
        return u''

    def newSecondaryText(self, text):
        self.secondaryText = text
        if not text: return
        if text.endswith('%'): text = text.rsplit(u' ',1)[-1] #Get just the percent part, so we don't keep saying downloading
        if not self.tts.isSpeaking(): self.sayText(text,interrupt=True)

    def formatSeasonEp(self,seasEp):
        if not seasEp: return u''
        return seasEp.replace(u'S',u'{0} '.format(T(32108))).replace(u'E',u'{0} '.format(T(32109)))

    _formatTagRE = re.compile(r'\[/?(?:CR|B|I|UPPERCASE|LOWERCASE)\](?i)')
    _colorTagRE = re.compile(r'\[/?COLOR[^\]\[]*?\](?i)')
    _okTagRE = re.compile(r'(^|\W|\s)OK($|\s|\W)') #Prevents saying Oklahoma
    def _cleanText(self,text):
        text = self._formatTagRE.sub('',text)
        text = self._colorTagRE.sub('',text)
        text = self._okTagRE.sub(r'\1O K\2', text) #Some speech engines say OK as Oklahoma
        text = text.strip('-[]') #getLabel() on lists wrapped in [] and some speech engines have problems with text starting with -
        text = text.replace('XBMC','X B M C')
        if text == '..': text = T(32110)
        return text

    def cleanText(self,text):
        if isinstance(text,basestring):
            return self._cleanText(text)
        else:
            return [self._cleanText(t) for t in text]


def preInstalledFirstRun():
    if not util.isPreInstalled(): #Do as little as possible if there is no pre-install
        if util.wasPreInstalled():
            util.LOG('PRE INSTALL: REMOVED')
            # Set version to 0.0.0 so normal first run will execute and fix the keymap
            util.setSetting('version','0.0.0')
            import enabler
            enabler.markPreOrPost() # Update the install status
        return False

    import enabler

    lastVersion = util.getSetting('version')

    if not enabler.isPostInstalled() and util.wasPostInstalled():
        util.LOG('POST INSTALL: UN-INSTALLED OR REMOVED')
        # Add-on was removed. Assume un-installed and treat this as a pre-installed first run to disable the addon
    elif lastVersion:
        enabler.markPreOrPost() # Update the install status
        return False

    # Set version to 0.0.0 so normal first run will execute on first enable
    util.setSetting('version','0.0.0')

    util.LOG('PRE-INSTALLED FIRST RUN')
    util.LOG('Installing basic keymap')

    # Install keymap with just F12 enabling included
    from lib import keymapeditor
    keymapeditor.installBasicKeymap()

    util.LOG('Pre-installed - DISABLING')

    enabler.disableAddon()
    return True


def startService():
    if preInstalledFirstRun():
        return

    TTSService().start()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'voice_dialog':
        backends.selectVoice()
    else:
        startService()

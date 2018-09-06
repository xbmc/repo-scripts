# -*- coding: utf-8 -*-
import sys, binascii, json, threading, time, datetime
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import verlib

DEBUG = True

ADDON = xbmcaddon.Addon()

T = ADDON.getLocalizedString

def LOG(msg):
    xbmc.log('script.hdhomerun.view: {0}'.format(msg), xbmc.LOGNOTICE)

def DEBUG_LOG(msg):
    if not getSetting('debug',False) and not xbmc.getCondVisibility('System.GetBool(debug.showloginfo)'): return
    LOG(msg)

def ERROR(txt='',hide_tb=False,notify=False):
    if isinstance (txt,str): txt = txt.decode("utf-8")
    short = str(sys.exc_info()[1])
    if hide_tb:
        xbmc.log('script.hdhomerun.view: ERROR: {0} - {1}'.format(txt,short),xbmc.LOGERROR)
        return short

    import traceback
    tb = traceback.format_exc()
    xbmc.log("_________________________________________________________________________________",xbmc.LOGERROR)
    xbmc.log('script.hdhomerun.view: ERROR: ' + txt,xbmc.LOGERROR)
    for l in tb.splitlines():
        xbmc.log('    ' + l,xbmc.LOGERROR)
    xbmc.log("_________________________________________________________________________________",xbmc.LOGERROR)
    xbmc.log("`",xbmc.LOGERROR)
    if notify: showNotification('ERROR: {0}'.format(short))
    return short

def Version(ver_string):
    return verlib.NormalizedVersion(verlib.suggest_normalized_version(ver_string))

def getSetting(key,default=None):
    setting = ADDON.getSetting(key)
    return _processSetting(setting,default)

def _processSetting(setting,default):
    if not setting: return default
    if isinstance(default,bool):
        return setting.lower() == 'true'
    elif isinstance(default,float):
        return float(setting)
    elif isinstance(default,int):
        return int(float(setting or 0))
    elif isinstance(default,list):
        if setting: return json.loads(binascii.unhexlify(setting))
        else: return default

    return setting

def setSetting(key,value):
    value = _processSettingForWrite(value)
    ADDON.setSetting(key,value)

def _processSettingForWrite(value):
    if isinstance(value,list):
        value = binascii.hexlify(json.dumps(value))
    elif isinstance(value,bool):
        value = value and 'true' or 'false'
    return str(value)

def setGlobalProperty(key,val):
    xbmcgui.Window(10000).setProperty('script.hdhomerun.view.{0}'.format(key),val)

def getGlobalProperty(key):
    return xbmc.getInfoLabel('Window(10000).Property(script.hdhomerun.view.{0})'.format(key))

def showNotification(message,time_ms=3000,icon_path=None,header=ADDON.getAddonInfo('name')):
    try:
        icon_path = icon_path or xbmc.translatePath(ADDON.getAddonInfo('icon')).decode('utf-8')
        xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(header,message,time_ms,icon_path))
    except RuntimeError: #Happens when disabling the addon
        LOG(message)

def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')

def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds/86400)
    if days:
        return '{0}d'.format(days)
    left = seconds % 86400
    hours = int(left/3600)
    if hours:
        return '{0}h'.format(hours)
    left = left % 3600
    mins = int(left/60)
    if mins:
        return '{0}m'.format(mins)
    secs = int(left % 60)
    if secs:
        return '{0}s'.format(secs)
    return '0s'

def durationToMinuteText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    mins = int(seconds/60)
    if mins:
        mins = '{0}m'.format(mins)
    else:
        mins = ''
    secs = int(seconds % 60)
    if secs:
        return mins + '{0}s'.format(secs)
    elif mins:
        return mins

    return '0s'

def timeInDayLocalSeconds():
    now = datetime.datetime.now()
    sod = datetime.datetime(year=now.year,month=now.month,day=now.day)
    sod = int(time.mktime(sod.timetuple()))
    return int(time.time() - sod)

def xbmcvfsGet(url):
    f = xbmcvfs.File(url,'r')
    data = f.read()
    f.close()
    return data

def showTextDialog(heading,text):
    t = TextBox()
    t.setControls(heading,text)

def kodiSimpleVersion():
    try:
        return float(xbmc.getInfoLabel('System.BuildVersion').split(' ',1)[0])
    except:
        return 0

def sortTitle(title):
    return title.startswith('The ') and title[4:] or title

def busyDialog(msg='LOADING'):
    def methodWrap(func):
        def inner(*args,**kwargs):
            try:
                setGlobalProperty('busy',msg)
                return func(*args,**kwargs)
            finally:
                setGlobalProperty('busy','')
        return inner
    return methodWrap

def withBusyDialog(method,msg,*args,**kwargs):
    return busyDialog(msg or 'LOADING')(method)(*args,**kwargs)

class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % ( self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)

    def setControls(self,heading,text):
        # set heading
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)

class CronReceiver():
    def tick(self): pass
    def halfHour(self): pass
    def day(self): pass

class Cron(threading.Thread):
    def __init__(self,interval):
        threading.Thread.__init__(self)
        self.stopped = threading.Event()
        self.force = threading.Event()
        self.interval = interval
        self._lastHalfHour = self._getHalfHour()
        self._receivers = []

    def __enter__(self):
        self.start()
        DEBUG_LOG('Cron started')
        return self

    def __exit__(self,exc_type,exc_value,traceback):
        self.stop()
        self.join()

    def _wait(self):
        ct=0
        while ct < self.interval:
            xbmc.sleep(100)
            ct+=0.1
            if self.force.isSet():
                self.force.clear()
                return True
            if xbmc.abortRequested or self.stopped.isSet(): return False
        return True

    def forceTick(self):
        self.force.set()

    def stop(self):
        self.stopped.set()

    def run(self):
        while self._wait():
            self._tick()
        DEBUG_LOG('Cron stopped')

    def _getHalfHour(self):
        tid = timeInDayLocalSeconds()/60
        return tid - (tid % 30)

    def _tick(self):
        receivers = list(self._receivers)
        receivers = self._halfHour(receivers)
        for r in receivers:
            try:
                r.tick()
            except:
                ERROR()

    def _halfHour(self,receivers):
        hh = self._getHalfHour()
        if hh == self._lastHalfHour: return receivers
        try:
            receivers = self._day(receivers,hh)
            ret = []
            for r in receivers:
                try:
                    if not r.halfHour(): ret.append(r)
                except:
                    ret.append(r)
                    ERROR()
            return ret
        finally:
            self._lastHalfHour = hh

    def _day(self,receivers,hh):
        if hh >= self._lastHalfHour: return receivers
        ret = []
        for r in receivers:
            try:
                if not r.day(): ret.append(r)
            except:
                ret.append(r)
                ERROR()
        return ret

    def registerReceiver(self,receiver):
        self._receivers.append(receiver)

    def cancelReceiver(self,receiver):
        if receiver in self._receivers:
            self._receivers.pop(self._receivers.index(receiver))

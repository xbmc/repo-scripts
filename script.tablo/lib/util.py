# -*- coding: utf-8 -*-
import os
import sys
import binascii
import json
import threading
import math
import time
import datetime

import xbmc
import xbmcgui
import xbmcaddon

import verlib

DEBUG = True

ADDON = xbmcaddon.Addon()

PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile')).decode('utf-8')

T = ADDON.getLocalizedString

LOCALIZED_SHOW_TYPES = {  # TODO: Actually localize these :)
    'SERIES': T(32202),
    'MOVIE': T(32199),
    'SPORT': T(32203),
    'PROGRAM': T(32204),
}

LOCALIZED_AIRING_TYPES = {  # TODO: Actually localize these :)
    'SERIES': T(32136),
    'MOVIE': T(32199),
    'SPORT': T(32138),
    'PROGRAM': T(32201),
}

LOCALIZED_AIRING_TYPES_PLURAL = {  # TODO: Actually localize these :)
    'SERIES': T(32137),
    'MOVIE': T(32200),
    'SPORT': T(32139),
    'PROGRAM': T(32200),
}

LOCALIZED_RECORDING_TYPES = {  # TODO: Actually localize these :)
    'SERIES': T(32136),
    'MOVIE': T(32199),
    'SPORT': T(32138),
    'PROGRAM': T(32198),
}

LOCALIZED_RECORDING_TYPES_PLURAL = {  # TODO: Actually localize these :)
    'SERIES': T(32137),
    'MOVIE': T(32200),
    'SPORT': T(32139),
    'PROGRAM': T(32175),
}


def LOG(msg):
    xbmc.log('script.tablo: {0}'.format(msg), xbmc.LOGNOTICE)


def DEBUG_LOG(msg):
    if not getSetting('debug', False) and not xbmc.getCondVisibility('System.GetBool(debug.showloginfo)'):
        return
    LOG(msg)


def ERROR(txt='', hide_tb=False, notify=False):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    short = str(sys.exc_info()[1])
    if hide_tb:
        xbmc.log('script.tablo: ERROR: {0} - {1}'.format(txt, short), xbmc.LOGERROR)
        return short

    import traceback
    tb = traceback.format_exc()
    xbmc.log("_________________________________________________________________________________", xbmc.LOGERROR)
    xbmc.log('script.tablo: ERROR: ' + txt, xbmc.LOGERROR)
    for l in tb.splitlines():
        xbmc.log('    ' + l, xbmc.LOGERROR)
    xbmc.log("_________________________________________________________________________________", xbmc.LOGERROR)
    xbmc.log("`", xbmc.LOGERROR)
    if notify:
        showNotification('ERROR: {0}'.format(short))
    return short


def errorDialog(msg, heading='Error'):
    xbmcgui.Dialog().ok(heading, msg)


def getSetting(key, default=None):
    setting = ADDON.getSetting(key)
    return _processSetting(setting, default)


def _processSetting(setting, default):
    if not setting:
        return default
    if isinstance(default, bool):
        return setting.lower() == 'true'
    elif isinstance(default, float):
        return float(setting)
    elif isinstance(default, int):
        return int(float(setting or 0))
    elif isinstance(default, list):
        if setting:
            return json.loads(binascii.unhexlify(setting))
        else:
            return default

    return setting


def setSetting(key, value):
    value = _processSettingForWrite(value)
    ADDON.setSetting(key, value)


def _processSettingForWrite(value):
    if isinstance(value, list):
        value = binascii.hexlify(json.dumps(value))
    elif isinstance(value, bool):
        value = value and 'true' or 'false'
    return str(value)


def Version(ver_string):
    return verlib.NormalizedVersion(verlib.suggest_normalized_version(ver_string))


def setGlobalProperty(key, val):
    xbmcgui.Window(10000).setProperty('script.tablo.{0}'.format(key), val)


def getGlobalProperty(key):
    return xbmc.getInfoLabel('Window(10000).Property(script.tablo.{0})'.format(key))


def showNotification(message, time_ms=3000, icon_path=None, header=ADDON.getAddonInfo('name')):
    try:
        icon_path = icon_path or xbmc.translatePath(ADDON.getAddonInfo('icon')).decode('utf-8')
        xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(header, message, time_ms, icon_path))
    except RuntimeError:  # Happens when disabling the addon
        LOG(message)


def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')


def showTextDialog(heading, text):
    t = TextBox()
    t.setControls(heading, text)


def sortTitle(title):
    return title.startswith('The ') and title[4:] or title


def longDurationToText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    years = int(seconds / 31536000)
    if years:
        return '{0} year{1}'.format(years, years > 1 and 's' or '')

    return durationToText(seconds)


def durationToText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400)
    if days:
        return '{0} day{1}'.format(days, days > 1 and 's' or '')
    left = seconds % 86400
    hours = int(left / 3600)
    if hours:
        hours = '{0} hr{1} '.format(hours, hours > 1 and 's' or '')
    else:
        hours = ''
    left = left % 3600
    mins = int(left / 60)
    if mins:
        return hours + '{0} min{1}'.format(mins, mins > 1 and 's' or '')
    elif hours:
        return hours
    secs = int(left % 60)
    if secs:
        return '{0} sec{1}'.format(secs, secs > 1 and 's' or '')
    return '0 seconds'


def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400)
    if days:
        return '{0}d'.format(days)
    left = seconds % 86400
    hours = int(left / 3600)
    if hours:
        hours = '{0}h'.format(hours)
    else:
        hours = ''
    left = left % 3600
    mins = int(left / 60)
    if mins:
        return hours + '{0}m'.format(mins)
    elif hours:
        return hours
    secs = int(left % 60)
    if secs:
        return '{0}s'.format(secs)
    return '0s'


SIZE_NAMES = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


def simpleSize(size):
    """
    Converts bytes to a short user friendly string
    Example: 12345 -> 12.06 KB
    """
    s = 0
    if size > 0:
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size / p, 2)
    if (s > 0):
        return '%s %s' % (s, SIZE_NAMES[i])
    else:
        return '0B'


class LoadingDialogWindow(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.abort = False
        self._winID = None

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowDialogId()

    def onAction(self, action):
        try:
            if action == xbmcgui.ACTION_NAV_BACK or action == xbmcgui.ACTION_PREVIOUS_MENU:
                self.abort = True
                self.setProperty('abort', '1')
                return
        except:
            ERROR()

        xbmcgui.WindowXMLDialog.onAction(self, action)

    def setProperty(self, key, value):
        try:
            xbmcgui.WindowXMLDialog.setProperty(self, key, value)
            xbmcgui.Window(self._winID).setProperty(key, value)
        except RuntimeError:
            import traceback
            traceback.print_exc()


class LoadingDialog(object):
    def __init__(self):
        self.w = None
        self._event = threading.Event()

    def __enter__(self):
        return self.show()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def show(self):
        self.w = LoadingDialogWindow('script-tablo-loading.xml', ADDON.getAddonInfo('path'), 'Main')
        self.w.show()
        self._event.clear()
        return self

    def close(self):
        self._event.set()

        if self.w:
            self.w.close()
            del self.w

        self.w = None

    @property
    def canceled(self):
        if self.w:
            return self.w.abort
        else:
            return False

    def wait(self):
        self._event.wait()


def busyDialog(func):
    def inner(*args, **kwargs):
        w = None
        try:
            w = xbmcgui.WindowXMLDialog('script-tablo-busy.xml', ADDON.getAddonInfo('path'), 'Main')
            w.show()
            return func(*args, **kwargs)
        finally:
            if w:
                w.close()
            del w
    return inner


def withBusyDialog(method, *args, **kwargs):
    return busyDialog(method)(*args, **kwargs)


def loadingDialog(func):
    def inner(*args, **kwargs):
        w = None
        try:
            w = xbmcgui.WindowXMLDialog('script-tablo-loading.xml', ADDON.getAddonInfo('path'), 'Main')
            w.show()
            return func(*args, **kwargs)
        finally:
            if w:
                w.close()
            del w
    return inner


class TextBox:
    # constants
    WINDOW = 10147
    CONTROL_LABEL = 1
    CONTROL_TEXTBOX = 5

    def __init__(self, *args, **kwargs):
        # activate the text viewer window
        xbmc.executebuiltin("ActivateWindow(%d)" % (self.WINDOW, ))
        # get window
        self.win = xbmcgui.Window(self.WINDOW)
        # give window time to initialize
        xbmc.sleep(1000)

    def setControls(self, heading, text):
        # set heading
        self.win.getControl(self.CONTROL_LABEL).setLabel(heading)
        # set text
        self.win.getControl(self.CONTROL_TEXTBOX).setText(text)


def timeInDayLocalSeconds():
    now = datetime.datetime.now()
    sod = datetime.datetime(year=now.year, month=now.month, day=now.day)
    sod = int(time.mktime(sod.timetuple()))
    return int(time.time() - sod)


CRON = None


class CronReceiver():
    def tick(self):
        pass

    def halfHour(self):
        pass

    def day(self):
        pass


class Cron(threading.Thread):
    def __init__(self, interval):
        threading.Thread.__init__(self)
        self.stopped = threading.Event()
        self.force = threading.Event()
        self.interval = interval
        self._lastHalfHour = self._getHalfHour()
        self._receivers = []

        global CRON

        CRON = self

    def __enter__(self):
        self.start()
        DEBUG_LOG('Cron started')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.join()

    def _wait(self):
        ct = 0
        while ct < self.interval:
            xbmc.sleep(100)
            ct += 0.1
            if self.force.isSet():
                self.force.clear()
                return True
            if xbmc.abortRequested or self.stopped.isSet():
                return False
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
        tid = timeInDayLocalSeconds() / 60
        return tid - (tid % 30)

    def _tick(self):
        receivers = list(self._receivers)
        receivers = self._halfHour(receivers)
        for r in receivers:
            try:
                r.tick()
            except:
                ERROR()

    def _halfHour(self, receivers):
        hh = self._getHalfHour()
        if hh == self._lastHalfHour:
            return receivers
        try:
            receivers = self._day(receivers, hh)
            ret = []
            for r in receivers:
                try:
                    if not r.halfHour():
                        ret.append(r)
                except:
                    ret.append(r)
                    ERROR()
            return ret
        finally:
            self._lastHalfHour = hh

    def _day(self, receivers, hh):
        if hh >= self._lastHalfHour:
            return receivers
        ret = []
        for r in receivers:
            try:
                if not r.day():
                    ret.append(r)
            except:
                ret.append(r)
                ERROR()
        return ret

    def registerReceiver(self, receiver):
        if receiver not in self._receivers:
            self._receivers.append(receiver)

    def cancelReceiver(self, receiver):
        if receiver in self._receivers:
            self._receivers.pop(self._receivers.index(receiver))


def saveTabloDeviceID(ID):
    with open(os.path.join(PROFILE, 'device.ID'), 'w') as f:
        f.write(ID)


def loadTabloDeviceID():
    path = os.path.join(PROFILE, 'device.ID')
    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return f.read()


def clearTabloDeviceID():
    path = os.path.join(PROFILE, 'device.ID')
    if not os.path.exists(path):
        return

    os.remove(path)

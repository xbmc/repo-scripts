# -*- coding: utf-8 -*-
import os
import math
import xbmc
from yd_private_libs import util

IS_WEB = False
try:
    import xbmcgui
    import xbmcvfs
except ImportError:
    IS_WEB = True

T = util.T


###############################################################################
# Dialogs
###############################################################################
def showMessage(heading, line1, line2=None, line3=None, bg=False):
    if bg:
        icon = util.ADDON.getAddonInfo('icon')
        xbmcgui.Dialog().notification(heading, line1, icon=icon)
    else:
        xbmcgui.Dialog().ok(heading, line1, line2, line3)


class xbmcDialogProgressBase:
    def __init__(self, heading, line1='', line2='', line3='', update_callback=None):
        self.heading = heading
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self._updateCallback = update_callback
        self.lastPercent = 0
        self.closed = False
        self.setRange()
        self.initDialog()

    def initDialog(self): assert False, 'Not Implemented'

    def __enter__(self):
        self.create(self.heading, self.line1, self.line2, self.line3)
        self.update(0, self.line1, self.line2, self.line3)
        return self

    def __exit__(self, etype, evalue, traceback):
        self.close()

    def setRange(self, start=0, end=100):
        self.start = start
        self.end = end
        self.range = end - start

    def recalculatePercent(self, pct):
        # rint '%s - %s %s %s' % (pct,self.start,self.range,self.start + int((pct/100.0) * self.range))
        return self.start + int((pct / 100.0) * self.range)

    def create(self, heading, line1='', line2='', line3=''):
        self.dialog.create(heading, line1, line2, line3)

    def update(self, pct, line1='', line2='', line3=''):
        if self._iscanceled():
            return False
        pct = self.recalculatePercent(pct)
        if pct < self.lastPercent:
            pct = self.lastPercent
        self.lastPercent = pct
        self._update(pct, line1, line2, line3)
        return True

    def _update(self, pct, line1, line2, line3):
        assert False, 'Not Implemented'

    def updateSimple(self, message):
        pct = 0
        if hasattr(message, 'percent'):
            pct = message.percent
        return self.update(pct, message)

    def updateCallback(self, a):
        if self._updateCallback:
            return self._updateCallback(self, a)
        return True

    def iscanceled(self):
        return self.dialog.iscanceled()

    def _iscanceled(self):
        return self.dialog.iscanceled()

    def close(self):
        self.closed = True
        self.dialog.close()


class xbmcDialogProgress(xbmcDialogProgressBase):
    def initDialog(self):
        self.dialog = xbmcgui.DialogProgress()

    def _update(self, pct, line1, line2, line3):
        self.dialog.update(pct, line1, line2, line3)


class xbmcDialogProgressBG(xbmcDialogProgressBase):
    def _condenseLines(self, line2, line3):
        lines = []
        for line in (line2, line3):
            if line:
                lines.append(line)
        return '  |  '.join(lines)

    def initDialog(self):
        self.dialog = xbmcgui.DialogProgressBG()

    def create(self, heading, line1='', line2='', line3=''):
        self.dialog.create(line1, self._condenseLines(line2, line3))

    def _update(self, pct, line1, line2, line3):
        self.dialog.update(pct, line1, self._condenseLines(line2, line3))

    def isFinished(self):
        return self.dialog.isFinished()

    def iscanceled(self):
        return self.closed

    def _iscanceled(self):
        return self.closed


class DownloadProgress(xbmcDialogProgress):
    def __init__(self, heading=T(32004), line1=''):
        xbmcDialogProgress.__init__(self, heading, line1=line1, update_callback=downloadProgressCallback)

    def __call__(self, info):
        return self._updateCallback(self, info)


class DownloadProgressBG(xbmcDialogProgressBG):
    def __init__(self, heading=T(32004), line1=''):
        xbmcDialogProgressBG.__init__(self, heading, line1=line1, update_callback=downloadProgressCallbackBG)

    def __call__(self, info):
        return self._updateCallback(self, info)


def downloadProgressCallback(prog, data):
    if not hasattr(data, 'info'):
        return prog.update(0, T(32035), data)
    line1 = os.path.basename(data.info.get('filename', ''))
    line2 = []
    if data.speedStr:
        line2.append(data.speedStr)
    if data.etaStr:
        line2.append('{0}: {1}'.format(T(32001), data.etaStr))
    line2 = ' - '.join(line2)
    line3 = []
    total = data.info.get('total_bytes')
    if total:
        line3.append('{0}: {1}'.format(T(32002), simpleSize(total)))
    downloaded = data.info.get('downloaded_bytes')
    if downloaded:
        line3.append('{0}: {1}'.format(T(32003), simpleSize(downloaded)))
    line3 = ' - '.join(line3)
    return prog.update(data.percent or 0, line1, line2, line3)


def downloadProgressCallbackBG(prog, data):
    if not hasattr(data, 'info'):
        return prog.update(0, T(32035), data)
    line1 = os.path.basename(data.info.get('filename', ''))
    line2 = []
    if data.speedStr:
        line2.append(data.speedStr)
    if data.etaStr:
        line2.append('{0}: {1}'.format(T(32001), data.etaStr))
    line2 = '  -  '.join(line2)
    line3 = ''
    downloaded = data.info.get('downloaded_bytes')
    if downloaded:
        total = data.info.get('total_bytes', 0)
        if total:
            line3 = '({0}/{1})'.format(simpleSize(downloaded), simpleSize(total))
        else:
            line3 = '({0})'.format(simpleSize(downloaded))
    return prog.update(data.percent or 0, line1, line2, line3)


###############################################################################
# Functions
###############################################################################
def moveFile(file_path, dest_path, filename=None):
    fname = filename or os.path.basename(file_path)
    destFilePath = os.path.join(dest_path, fname)
    if xbmcvfs.copy(file_path, destFilePath):
        xbmcvfs.delete(file_path)
        return True

    return False


def getDownloadPath(use_default=None):
    if use_default is None:
        use_default = not util.getSetting('confirm_download_path', True)
    path = util.getSetting('last_download_path', '')
    if path:
        if not use_default:
            new = xbmcgui.Dialog().yesno(T(32005), T(32006), path, T(32007), T(32008), T(32009))
            if new:
                path = ''
    if not path:
        path = xbmcgui.Dialog().browse(3, T(32010), 'files', '', False, True)
    if not path:
        return
    util.setSetting('last_download_path', path)
    return path


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


def durationToShortText(seconds):
    """
    Converts seconds to a short user friendly string
    Example: 143 -> 2m 23s
    """
    days = int(seconds / 86400)
    if days:
        return '%sd' % days
    left = seconds % 86400
    hours = int(left / 3600)
    if hours:
        return '%sh' % hours
    left = left % 3600
    mins = int(left / 60)
    if mins:
        return '%sm' % mins
    sec = int(left % 60)
    if sec:
        return '%ss' % sec
    return '0s'


###############################################################################
# xbmc player functions
###############################################################################
def play(path, preview=False):
    """
    Plays the video specified by path.
    If preview is True plays in current skins preview or background.
    """
    xbmc.executebuiltin('PlayMedia(%s,,%s)' % (path, preview and 1 or 0))


def pause():
    """
    Pauses currently playing video.
    """
    if isPlaying():
        control('play')


def resume():
    """
    Un-pauses currently paused video.
    """
    if not isPlaying():
        control('play')


def current():
    """
    Returns the currently playing file.
    """
    try:
        return xbmc.Player().getPlayingFile()
    except RuntimeError:
        return None


def control(command):
    """
    Send the command to the player.
    """
    xbmc.executebuiltin('PlayerControl(%s)' % command)


def isPlaying():
    """
    Returns True if the player is playing video.
    """
    return xbmc.getCondVisibility('Player.Playing') and xbmc.getCondVisibility('Player.HasVideo')


def playAt(path, h=0, m=0, s=0, ms=0):
    """
    Plays the video specified by path.
    Optionally set the start position with h,m,s,ms keyword args.
    """
    xbmc.executeJSONRPC(
        '{"jsonrpc": "2.0", "method": "Player.Open", "params": {"item":{"file":"%s"},"options":{"resume":{"hours":%s,"minutes":%s,"seconds":%s,"milliseconds":%s}}}, "id": 1}' % (path, h, m, s, ms)  # noqa 501

    )

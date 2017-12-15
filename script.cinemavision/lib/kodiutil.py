import os
import time
import json
import binascii

import xbmc
import xbmcgui
import xbmcaddon

API_LEVEL = 4

ADDON_ID = 'script.cinemavision'
ADDON = xbmcaddon.Addon(ADDON_ID)


def translatePath(path):
    return xbmc.translatePath(path).decode('utf-8')


PROFILE_PATH = translatePath(ADDON.getAddonInfo('profile'))
ADDON_PATH = translatePath(ADDON.getAddonInfo('path'))

if not os.path.exists(PROFILE_PATH):
    os.makedirs(PROFILE_PATH)


def T(ID, eng=''):
    return ADDON.getLocalizedString(ID)


def DEBUG():
    return getSetting('debug.log', True) or xbmc.getCondVisibility('System.GetBool(debug.showloginfo)')


def LOG(msg):
    xbmc.log('[- CinemaVision -]: {0}'.format(msg), xbmc.LOGNOTICE)


def DEBUG_LOG(msg):
    if not DEBUG():
        return
    LOG(msg)


def ERROR(msg=''):
    if msg:
        LOG(msg)
    import traceback
    xbmc.log(traceback.format_exc(), xbmc.LOGNOTICE)


def TEST(msg):
    xbmc.log('-- TEST: {0}'.format(repr(msg)), xbmc.LOGNOTICE)


def firstRun():
    LOG('FIRST RUN')


def infoLabel(info):
    return xbmc.getInfoLabel(info).decode('utf-8')


def checkAPILevel():
    old = getSetting('API_LEVEL', 0)
    if not old:
        firstRun()
    elif old == 1:
        setSetting('from.beta', ADDON.getAddonInfo('version'))
    elif old < 3:
        LOG('API LEVEL < 3: Clearing trailers and updating DB')
        last = os.path.join(PROFILE_PATH, 'itunes.last')
        watched = os.path.join(PROFILE_PATH, 'watched.db')
        if os.path.exists(last):
            os.remove(last)
        if os.path.exists(watched):
            os.remove(watched)
        import cvutil
        cvutil.loadContent()
        xbmc.sleep(1000)

    if old < 4:
        LOG('API LEVEL < 4: Migrating default sequences')

        contentPath = getSetting('content.path')
        if contentPath:
            from lib import cinemavision

            sequencesPath = cinemavision.util.pathJoin(contentPath, 'Sequences')

            for stereoType in ['2D', '3D']:
                default = getSetting('sequence.{0}'.format(stereoType))
                if default:
                    path = cinemavision.util.pathJoin(sequencesPath, '{0}.cvseq'.format(default))
                    if cinemavision.util.vfs.exists(path):
                        LOG('API Migration: Activating sequence for {0}: {1}'.format(stereoType, default))
                        seqData = cinemavision.sequence.SequenceData.load(path)
                        seqData.active = True
                        seqData.set('type', stereoType)
                        seqData.save()

    if getSetting('from.beta'):
        DEBUG_LOG('UPDATED FROM BETA: {0}'.format(getSetting('from.beta')))

    setSetting('API_LEVEL', API_LEVEL)


def strRepr(str_obj):
    return repr(str_obj).lstrip('u').strip("'")


def getSetting(key, default=None):
    setting = ADDON.getSetting(key).decode('utf-8')
    return _processSetting(setting, default)


def _processSetting(setting, default):
    if not setting:
        return default
    try:
        if isinstance(default, bool):
            return setting.lower() == 'true'
        elif isinstance(default, float):
            return float(setting)
        elif isinstance(default, int):
            return int(float(setting or 0))
        elif isinstance(default, list):
            return json.loads(binascii.unhexlify(setting))
    except:
        ERROR()
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


def intOrZero(val):
    try:
        return int(val)
    except:
        return 0


def setGlobalProperty(key, val):
    xbmcgui.Window(10000).setProperty('script.cinemavision.{0}'.format(key), val)


def getGlobalProperty(key):
    return xbmc.getInfoLabel('Window(10000).Property(script.cinemavision.{0})'.format(key))


def setScope():
    setGlobalProperty('scope.2.40:1', '')
    setGlobalProperty('scope.2.35:1', '')
    setGlobalProperty('scope.16:9', '')
    setGlobalProperty('scope.{0}'.format(getSetting('scope', '16:9')), '1')


try:
    xbmc.Monitor().waitForAbort

    def wait(timeout):
        return xbmc.Monitor().waitForAbort(timeout)
except:
    def wait(timeout):
        start = time.time()
        while not xbmc.abortRequested and time.time() - start < timeout:
            xbmc.sleep(100)
        return xbmc.abortRequested


def getPeanutButter():
    import binascii
    return binascii.a2b_base64('WlRObE1tVTVaV1V5TTJKaVpXSm1aR1U1TkRVMk1EZ3dNemRrWVRSbFlUVT0=')


class Progress(object):
    def __init__(self, heading, line1='', line2='', line3='', bg=False):
        self.isBackground = bg
        if bg:
            self.dialog = xbmcgui.DialogProgressBG()
            self.iscanceled = self.iscanceledBG
            self._update = self._updateBG
        else:
            self.dialog = xbmcgui.DialogProgress()

        self.heading = heading
        self.line1 = line1
        self.line2 = line2
        self.line3 = line3
        self.pct = 0
        self.message = ''

    def __enter__(self):
        if self.isBackground:
            heading = u'{0} - {1}'.format(self.heading, self.line1)
            msg = u'{0} - {1}'.format(self.line2, self.line3)
            self.dialog.create(heading, msg)
        else:
            self.dialog.create(self.heading, self.line1, self.line2, self.line3)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.dialog.close()

    def update(self, pct, line1=None, line2=None, line3=None):
        self.pct = pct
        if line1 is not None:
            self.line1 = line1
        if line2 is not None:
            self.line2 = line2
        if line3 is not None:
            self.line3 = line3

        self._update()

    def _update(self):
        self.dialog.update(self.pct, self.line1, self.line2, self.line3)

    def _updateBG(self):
        heading = u'{0} - {1}'.format(self.heading, self.line1)
        msg = u'{0} - {1}'.format(self.line2, self.line3)
        self.dialog.update(self.pct, heading, msg)

    def msg(self, msg=None, heading=None, pct=None):
        if pct is not None:
            self.pct = pct
        self.message = msg is not None and msg or self.message
        self.update(self.pct, heading, self.message)
        return not self.iscanceled()

    def iscanceled(self):
        return self.dialog.iscanceled()

    def iscanceledBG(self):
        return False

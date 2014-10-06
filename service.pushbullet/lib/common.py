import xbmc
import xbmcaddon

__addon__        = xbmcaddon.Addon()
__addonid__      = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonname__    = __addon__.getAddonInfo('name')
__addonauthor__  = __addon__.getAddonInfo('author')
__addonpath__    = xbmc.translatePath(__addon__.getAddonInfo('path')).decode('utf-8')
__addonprofile__ = xbmc.translatePath(__addon__.getAddonInfo('profile')).decode('utf-8')
__addonicon__    = __addon__.getAddonInfo('icon')


def localise(id):
    string = __addon__.getLocalizedString(id).encode('utf-8', 'ignore')
    return string


def log(txt, level=xbmc.LOGDEBUG):
    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'[%s]: %s' % (__addonname__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=level)


def traceError():
    import traceback
    xbmc.log(traceback.format_exc(), level=xbmc.LOGERROR)

def showNotification(title, message, timeout=2000, icon=__addonicon__):
    xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (
        title.encode('utf-8', 'ignore'), message.encode('utf-8', 'ignore'), timeout, icon))


def executeJSONRPC(jsonStr):
    import json

    response = json.loads(xbmc.executeJSONRPC(jsonStr))
    response = response['result'] if 'result' in response else response

    return response


def getMainSetting(name):
    result = executeJSONRPC('{ "jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "' + str(name) + '"}, "id": 1 }')
    return result['value']


def base64ToFile(strBase64, filePath, imgFormat='JPEG', imgSize=None):
    import base64
    fileDecoded = base64.b64decode(strBase64)

    # change image size and set format
    if imgSize:
        import cStringIO
        from PIL import Image

        file = cStringIO.StringIO(fileDecoded)

        img = Image.open(file)
        img.thumbnail(imgSize, Image.BICUBIC)
        img.save(filePath, format=imgFormat)

    # only save image (do not image transformation)
    else:
        file = open(filePath, "wb")
        file.write(fileDecoded)
        file.close()

    return filePath


def fileTobase64(filePath, imgFormat='JPEG', imgSize=None):
    import base64
    import xbmcvfs

    filePath = xbmc.translatePath(filePath).decode('utf-8')

    f = xbmcvfs.File(filePath)
    file = f.readBytes()
    f.close()

    # change image size and set format
    if imgSize:
        import cStringIO
        from PIL import Image

        file = cStringIO.StringIO(file)

        img = Image.open(file)
        img.thumbnail(imgSize, Image.BICUBIC)

        output = cStringIO.StringIO()
        img.save(output, imgFormat)

        imgEncoded = base64.b64encode(output.getvalue())
        output.close()

    # only save image (do not image transformation)
    else:
        imgEncoded = base64.b64encode(file)

    return imgEncoded


class serviceMonitor(xbmc.Monitor):
    def __init__(self, onSettingsChangedAction=None, onNotificationAction=None):
        xbmc.Monitor.__init__(self)

        self.onSettingsChangedAction = onSettingsChangedAction
        self.onNotificationAction = onNotificationAction

    def onSettingsChanged(self):
        if self.onSettingsChangedAction:
            self.onSettingsChangedAction()

    def onNotification(self, sender, method, json):
        if self.onNotificationAction:
            self.onNotificationAction(sender, method, json)

    def setOnSettingsChangedAction(self, action):
        self.onSettingsChangedAction = action

    def setOnNotificationAction(self, action):
        self.onNotificationAction = action


# TESTING ====================================================================================

# import time
# from threading import Thread, Event
#
# class IntervalTimer(Thread):
# def __init__(self, worker_func, interval, worker_func_args):
#         Thread.__init__(self)
#         self._interval = interval
#         self._worker_func = worker_func
#         self._worker_func_args = worker_func_args
#         self._stop_event = Event()
#
#     def run(self):
#         while not self._stop_event.is_set():
#             self._worker_func(self, *self._worker_func_args)
#             time.sleep(self._interval)
#
#     def stop(self):
#         if self.isAlive() is True:
#             # set event to signal thread to terminate
#             self._stop_event.set()
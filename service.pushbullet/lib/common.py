import xbmc
from util import * #TODO: Move util funtions to here

__addon__        = ADDON
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
    if getSetting('debug_logging',False) and not xbmc.getCondVisibility('System.GetBool(debug.showloginfo)'):
        if not level == xbmc.LOGERROR:
            level = xbmc.LOGNOTICE

    if isinstance(txt, str):
        txt = txt.decode("utf-8")
    message = u'[%s]: %s' % (__addonname__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=level)


def traceError():
    import traceback
    xbmc.log(traceback.format_exc(), level=xbmc.LOGERROR)

def showNotification(title, message, timeout=2000, icon=__addonicon__):
    if showNotification.proportionalTextLengthTimeout:
        timeout = min(len(message)/10*2000, timeout)

    title = title.replace('"', '\\"')
    message = message.replace('"', '\\"')

    xbmc.executebuiltin('Notification("%s","%s","%s","%s")' % (
        title.encode('ascii', 'ignore'), message.encode('ascii', 'ignore'), timeout, icon))
showNotification.proportionalTextLengthTimeout = False


def executeJSONRPC(jsonStr):
    import json

    response = json.loads(xbmc.executeJSONRPC(jsonStr))
    response = response['result'] if 'result' in response else response

    return response

def executeJSONRPCMethod(method, params={}):

    rpc = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }

    # Check if is there is an active player
    activePlayers = executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')

    if len(activePlayers) > 0:

        del activePlayers[0]['type']
        rpc['params'].update(activePlayers[0])

        if method == 'Player.GoTo':
            rpc['params'].setdefault('to', 'next')

        from json import dumps

        return executeJSONRPC(dumps(rpc))

    return False

def getMainSetting(name):
    result = executeJSONRPC('{ "jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "' + str(name) + '"}, "id": 1 }')
    return result['value']

def getKodiCmdsFromFiles():
    import os
    internalKodiCmdsFile = os.path.join(__addonpath__, 'resources', 'kcmds.json')

    file = open(internalKodiCmdsFile, 'r')
    jsonKodiCmds = file.read()
    file.close()

    import json
    jsonKodiCmds = json.loads(jsonKodiCmds)

    try:
        externalKodiCmdsFile = os.path.join(__addonprofile__, 'kcmds.json')

        file = open(externalKodiCmdsFile, 'r')
        externalJsonKodiCmds = file.read()
        file.close()

        externalJsonKodiCmds = json.loads(externalJsonKodiCmds)
        jsonKodiCmds.update(externalJsonKodiCmds)

    except IOError:
        log('No user Kody commands defined. (Create %s for that)' % externalKodiCmdsFile, xbmc.LOGWARNING)

    except Exception as ex:
        traceError()
        message = ' '.join(str(arg) for arg in ex.args)

        log(message, xbmc.LOGERROR)

    else:
        log('Loaded user Kody commands: %s' % externalJsonKodiCmds.keys())

    return jsonKodiCmds


def base64ToFile(strBase64, filePath, imgFormat='JPEG', imgSize=None):
    import base64
    fileDecoded = base64.b64decode(strBase64)

    # change image size and set format
    if imgSize:
        import cStringIO
        file = cStringIO.StringIO(fileDecoded)
        try:
            from PIL import Image

            img = Image.open(file)
            img.thumbnail(imgSize, Image.BICUBIC)
            img.save(filePath, format=imgFormat)
            return filePath
        except ImportError: #Some platforms don't have PIL...
            log('base64ToFile(): PIL Not available - skipping resize')
            pass #So we just fallback to saving

    # only save image (do not image transformation)
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
    size = len(file)

    # change image size and set format
    if imgSize:
        try:
            from PIL import Image
            import cStringIO

            file = cStringIO.StringIO(file)

            img = Image.open(file)
            img.thumbnail(imgSize, Image.BICUBIC)

            output = cStringIO.StringIO()
            img.save(output, imgFormat)

            imgEncoded = base64.b64encode(output.getvalue())
            output.close()
            return imgEncoded
        except ImportError:
            log('fileTobase64(): PIL Not available - falling back to limpp')

        try:
            import limpp
            from io import BytesIO

            with BytesIO() as outputIO:
                with BytesIO(file) as inputIO:
                    img = limpp.Get_image(size=size,file=inputIO)
                    limpp.Manipulator(img).Scale(*imgSize)
                    img.Write_PNG(outputIO)
                imgEncoded = base64.b64encode(outputIO.getvalue())
            return imgEncoded
        except:
            traceError()
            log('fileTobase64(): No resizing available - returning None')

        return None

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
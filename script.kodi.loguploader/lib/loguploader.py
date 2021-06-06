import os
import re
import socket
import pyqrcode
import requests
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
CWD = ADDON.getAddonInfo('path')
PROFILE = ADDON.getAddonInfo('profile')
LANGUAGE = ADDON.getLocalizedString

socket.setdefaulttimeout(5)

URL = 'https://paste.kodi.tv/'
LOGPATH = xbmcvfs.translatePath('special://logpath')
LOGFILE = os.path.join(LOGPATH, 'kodi.log')
OLDLOG = os.path.join(LOGPATH, 'kodi.old.log')
REPLACES = (('//.+?:.+?@', '//USER:PASSWORD@'),('<user>.+?</user>', '<user>USER</user>'),('<pass>.+?</pass>', '<pass>PASSWORD</pass>'),)

def log(txt):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


class QRCode(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.image = kwargs["image"]
        self.text = kwargs["text"]

    def onInit(self):
        self.imagecontrol = 501
        self.textbox = 502
        self.okbutton = 503
        self.showdialog()

    def showdialog(self):
        self.getControl(self.imagecontrol).setImage(self.image)
        self.getControl(self.textbox).setText(self.text)
        self.setFocus(self.getControl(self.okbutton))

    def onClick(self, controlId):
        if (controlId == self.okbutton):
            self.close()


class LogView(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.name = kwargs["name"]
        self.content = kwargs["content"]

    def onInit(self):
        self.header = 501
        self.textbox = 502
        self.showdialog()

    def showdialog(self):
        self.getControl(self.header).setLabel(self.name)
        self.getControl(self.textbox).setText(self.content)
        self.setFocusId(503)


class Main():
    def __init__(self):
        log('script started')
        self.getSettings()
        if not xbmcvfs.exists(PROFILE):
            xbmcvfs.mkdirs(PROFILE)
        files = self.getFiles()
        for item in files:
            filetype = item[0]
            if filetype == 'log':
                error = LANGUAGE(32011)
                name = LANGUAGE(32031)
            elif filetype == 'oldlog':
                error = LANGUAGE(32012)
                name = LANGUAGE(32032)
            elif filetype == 'crashlog':
                error = LANGUAGE(32013)
                name = LANGUAGE(32033)
            succes, data = self.readLog(item[1])
            if succes:
                content = self.cleanLog(data)
                dialog = xbmcgui.Dialog()
                confirm = dialog.yesno(ADDONNAME, LANGUAGE(32040) % name, nolabel=LANGUAGE(32041), yeslabel=LANGUAGE(32042))
                if confirm:
                    succes, data = self.postLog(content)
                    if succes:
                        self.showResult(LANGUAGE(32006) % (name, data), data)
                    else:
                        self.showResult('%s[CR]%s' % (error, data))
                else:
                    lv = LogView( "script-loguploader-view.xml" , CWD, "default", name=name, content=content)
                    lv.doModal()
                    del lv
            else:
                self.showResult('%s[CR]%s' % (error, data))
        log('script ended')

    def getSettings(self):
        self.oldlog = ADDON.getSettingBool('oldlog')
        self.crashlog = ADDON.getSettingBool('crashlog')

    def getFiles(self):
        logfiles = []
        logfiles.append(['log', LOGFILE])
        if self.oldlog:
            if xbmcvfs.exists(OLDLOG):
                logfiles.append(['oldlog', OLDLOG])
            else:
                self.showResult(LANGUAGE(32021))
        if self.crashlog:
            crashlog_path = ''
            items = []
            if xbmc.getCondVisibility('system.platform.osx'):
                crashlog_path = os.path.join(os.path.expanduser('~'), 'Library/Logs/DiagnosticReports/')
                filematch = 'Kodi'
            elif xbmc.getCondVisibility('system.platform.ios'):
                crashlog_path = '/var/mobile/Library/Logs/CrashReporter/'
                filematch = 'Kodi'
            elif xbmc.getCondVisibility('system.platform.linux'):
                crashlog_path = os.path.expanduser('~') # not 100% accurate (crashlogs can be created in the dir kodi was started from as well)
                filematch = 'kodi_crashlog'
            elif xbmc.getCondVisibility('system.platform.windows'):
                self.showResult(LANGUAGE(32023))
            elif xbmc.getCondVisibility('system.platform.android'):
                self.showResult(LANGUAGE(32024))
            if crashlog_path and os.path.isdir(crashlog_path):
                lastcrash = None
                dirs, files = xbmcvfs.listdir(crashlog_path)
                for item in files:
                    if filematch in item and os.path.isfile(os.path.join(crashlog_path, item)):
                        items.append(os.path.join(crashlog_path, item))
                        items.sort(key=lambda f: os.path.getmtime(f))
                        lastcrash = items[-1]
                if lastcrash:
                    logfiles.append(['crashlog', lastcrash])
            if len(items) == 0:
                self.showResult(LANGUAGE(32022))
        return logfiles

    def readLog(self, path):
        try:
            lf = xbmcvfs.File(path)
            sz = lf.size()
            if sz > 2000000:
                log('file is too large')
                return False, LANGUAGE(32005)
            content = lf.read()
            lf.close()
            if content:
                return True, content
            else:
                log('file is empty')
                return False, LANGUAGE(32001)
        except:
            log('unable to read file')
            return False, LANGUAGE(32002)

    def cleanLog(self, content):
        for pattern, repl in REPLACES:
            content = re.sub(pattern, repl, content)
            return content

    def postLog(self, data):
        self.session = requests.Session()
        UserAgent = '%s: %s' % (ADDONID, ADDONVERSION)
        try:
            response = self.session.post(URL + 'documents', data=data.encode('utf-8'), headers={'User-Agent': UserAgent})
            if 'key' in response.json():
                result = URL + response.json()['key']
                return True, result
            elif 'message' in response.json():
                log('upload failed, paste may be too large')
                return False, response.json()['message']
            else:
                log('error: %s' % response.text)
                return False, LANGUAGE(32007)
        except:
            log('unable to retrieve the paste url')
            return False, LANGUAGE(32004)

    def showResult(self, message, url=None):
        if url:
            imagefile = os.path.join(xbmcvfs.translatePath(PROFILE),'%s.png' % str(url.split('/')[-1]))
            qrIMG = pyqrcode.create(url)
            qrIMG.png(imagefile, scale=10)
            qr = QRCode( "script-loguploader-main.xml" , CWD, "default", image=imagefile, text=message)
            qr.doModal()
            del qr
            xbmcvfs.delete(imagefile)
        else:
            dialog = xbmcgui.Dialog()
            confirm = dialog.ok(ADDONNAME, message)

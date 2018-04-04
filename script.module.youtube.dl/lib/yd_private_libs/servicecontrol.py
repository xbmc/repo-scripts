# -*- coding: utf-8 -*-
import xbmc
import os
import binascii
import json
import util
import jsonqueue

IS_WEB = False
try:
    import xbmcgui
except ImportError:
    IS_WEB = True

BASE_COMMAND = 'XBMC.NotifyAll(script.module.youtube.dl,{0},"{{{1}}}")'
BASE_ARG = '\\"{0}\\":\\"{1}\\"'


def safeEncode(text):
    return binascii.hexlify(text.encode('utf-8'))


def safeDecode(enc_text):
    return binascii.unhexlify(enc_text).decode('utf-8')


class ServiceControl(object):
    def sendCommand(self, command, **kwargs):
        args = []
        for k, v in kwargs.items():
            args.append(BASE_ARG.format(k, safeEncode(v)))
        command = BASE_COMMAND.format(command, ','.join(args))
        xbmc.executebuiltin(command)

    def processCommandData(self, data):
        args = json.loads(data)
        for k in args.keys():
            v = args[k]
            args[k] = safeDecode(v)
        return args

    def download(self, info, path, duration):
        addonPath = xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8')
        service = os.path.join(addonPath, 'service.py')
        data = {'data': info, 'path': path, 'duration': duration}
        dataJSON = json.dumps(data)
        jsonqueue.XBMCJsonRAFifoQueue(util.QUEUE_FILE).push(binascii.hexlify(dataJSON))
        xbmc.executebuiltin('RunScript({0})'.format(service))

    def stopDownload(self):
        self.sendCommand('DOWNLOAD_STOP')

    def stopAllDownloads(self):
        jsonqueue.XBMCJsonRAFifoQueue(util.QUEUE_FILE).clear()
        self.stopDownload()

    def isDownloading(self):
        return self.status == 'ACTIVE'

    def manageQueue(self):
        ID = True
        q = jsonqueue.XBMCJsonRAFifoQueue(util.QUEUE_FILE)

        while ID:
            items = q.items()
            if not items:
                return xbmcgui.Dialog().ok('Queue Empty', 'No downloads are in the queue.')
            d = util.xbmcDialogSelect('Select Item To Delete')
            for qID, val in items:
                data = json.loads(binascii.unhexlify(val))['data']
                d.addItem(qID, data['title'])
            ID = d.getResult()
            if not ID:
                return
            q.remove(ID)

    @property
    def status(self):
        return xbmc.getInfoLabel('Window(10000).Property(script.module.youtube.dl_STATUS)')

    @status.setter
    def status(self, value):
        xbmcgui.Window(10000).setProperty('script.module.youtube.dl_STATUS', value)

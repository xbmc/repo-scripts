# -*- coding: utf-8 -*-
import sys
import json
import binascii
import xbmc
from lib.yd_private_libs import util, servicecontrol, jsonqueue
sys.path.insert(0, util.MODULE_PATH)
import YDStreamExtractor  # noqa E402
import threading  # noqa E402
import AddonSignals


class Service():
    def __init__(self):
        self.downloadCount = 0
        self.controller = servicecontrol.ServiceControl()

        AddonSignals.registerSlot('script.module.youtube.dl', 'DOWNLOAD_STOP', self.stopDownload)

        self.start()

    def stopDownload(self, args):
        YDStreamExtractor._cancelDownload()

    def getNextQueuedDownload(self):
        try:
            dataHEX = jsonqueue.XBMCJsonRAFifoQueue(util.QUEUE_FILE).pop()
            if not dataHEX:
                return None
            dataJSON = binascii.unhexlify(dataHEX)
            self.downloadCount += 1
            util.LOG('Loading from queue. #{0} this session'.format(self.downloadCount))
            return json.loads(dataJSON)
        except:
            import traceback
            traceback.print_exc()

        return None

    def start(self):
        if self.controller.status == 'ACTIVE':
            return

        try:
            self.controller.status = 'ACTIVE'
            self._start()
        finally:
            self.controller.status = ''

    def _start(self):
        util.LOG('DOWNLOAD SERVICE: START')
        info = self.getNextQueuedDownload()
        monitor = xbmc.Monitor()

        while info and not monitor.abortRequested():
            t = threading.Thread(target=YDStreamExtractor._handleDownload, args=(
                info['data'],), kwargs={'path': info['path'], 'duration': info['duration'], 'bg': True})
            t.start()

            while t.isAlive() and not monitor.abortRequested():
                xbmc.sleep(100)

            info = self.getNextQueuedDownload()

        util.LOG('DOWNLOAD SERVICE: FINISHED')

Service()

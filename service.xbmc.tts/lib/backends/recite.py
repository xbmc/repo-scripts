# -*- coding: utf-8 -*-
import base
import subprocess
import os
from lib import util


class ReciteTTSBackend(base.SimpleTTSBackendBase):
    provider = 'recite'
    displayName = 'Recite'

    def init(self):
        self.process = None

    def runCommandAndSpeak(self,text):
        args = ['recite',text]
        self.process = subprocess.Popen(args)
        while self.process.poll() == None and self.active: util.sleep(10)

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @staticmethod
    def available():
        try:
            subprocess.call(['recite','-VERSion'], stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except:
            return False
        return True


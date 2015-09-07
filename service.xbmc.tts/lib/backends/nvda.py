# -*- coding: utf-8 -*-
import os, ctypes
from lib import util
from base import TTSBackendBase

def getDLLPath():
    p = os.path.join(util.profileDirectory(),'nvdaControllerClient32.dll')
    if os.path.exists(p): return p
    p = os.path.join(util.backendsDirectory(),'nvda','nvdaControllerClient32.dll')
    if os.path.exists(p): return p
    try:
        import xbmc
        if xbmc.getCondVisibility('System.HasAddon(script.module.nvdacontrollerclient)'):
            if util.DEBUG: util.LOG('Found script.module.nvdacontrollerclient module for NVDA')
            import xbmcaddon
            nvdaCCAddon = xbmcaddon.Addon('script.module.nvdacontrollerclient')
            p = os.path.join(nvdaCCAddon.getAddonInfo('path').decode('utf-8'),'nvda','nvdaControllerClient32.dll')
            if os.path.exists(p): return p
    except (ImportError,AttributeError):
        return None
    return None

try:
    from ctypes import windll
except ImportError:
    windll =None

class NVDATTSBackend(TTSBackendBase):
    provider = 'nvda'
    displayName = 'NVDA'

    @staticmethod
    def available():
        dllPath = getDLLPath()
        if not dllPath or not windll:
            return False
        try:
            dll = ctypes.windll.LoadLibrary(dllPath)
            res = dll.nvdaController_testIfRunning() == 0
            ctypes.windll.kernel32.FreeLibrary(dll._handle)
            del dll
            return res
        except:
            return False

    def init(self):
        try:
            self.dll = ctypes.windll.LoadLibrary(getDLLPath())
        except:
            self.dll = None

    def isRunning(self):
        return self.dll.nvdaController_testIfRunning() == 0

    def say(self,text,interrupt=False):
        if not self.dll:
            return

        if interrupt:
            self.stop()
        if not self.dll.nvdaController_speakText(text) == 0:
            if not self.isRunning():
                self.flagAsDead('Not running')
                return

    def sayList(self,texts,interrupt=False):
        self.say('\n'.join(texts),interrupt)

    def stop(self):
        if not self.dll: return
        self.dll.nvdaController_cancelSpeech()

    def close(self):
        if not self.dll: return
        ctypes.windll.kernel32.FreeLibrary(self.dll._handle)
        del self.dll
        self.dll = None


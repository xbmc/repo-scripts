# -*- coding: utf-8 -*-
from base import ThreadedTTSBackend
import locale, os
import speechd
from lib import util

def getSpeechDSpeaker(test=False):
    try:
        return speechd.Speaker('XBMC', 'XBMC')
    except:
        try:
            socket_path = os.path.expanduser('~/.speech-dispatcher/speechd.sock')
            so = speechd.Speaker('XBMC', 'XBMC',socket_path=socket_path)
            try:
                so.set_language(locale.getdefaultlocale()[0][:2])
            except (KeyError,IndexError):
                pass
            return so
        except:
            if not test: util.ERROR('Speech-Dispatcher: failed to create Speaker',hide_tb=True)
    return None

class SpeechDispatcherTTSBackend(ThreadedTTSBackend):
    """Supports The speech-dispatcher on linux"""

    provider = 'Speech-Dispatcher'
    displayName = 'Speech Dispatcher'
    volumeConstraints = (-100,0,100,True)
    volumeExternalEndpoints = (0,200)
    volumeStep = 5
    volumeSuffix = '%'
    settings = {
                    'module':None,
                    'voice':None,
                    'speed':0,
                    'pitch':0,
                    'volume':100
    }

    def init(self):
        self.updateMessage = None
        self.connect()

    def connect(self):
        self.speechdObject = getSpeechDSpeaker()
        if not self.speechdObject: return
        self.update()

    def threadedSay(self,text,interrupt=False):
        if not self.speechdObject:
            return
        try:
            self.speechdObject.speak(text)
        except speechd.SSIPCommunicationError:
            self.reconnect()
        except AttributeError: #Happens on shutdown
            pass

    def stop(self):
        try:
            self.speechdObject.cancel()
        except speechd.SSIPCommunicationError:
            self.reconnect()
        except AttributeError: #Happens on shutdown
            pass

    def reconnect(self):
        self.close()
        if self.active:
            util.LOG('Speech-Dispatcher reconnecting...')
            self.connect()

    def volumeUp(self):
        #Override because returning the message (which causes speech) causes the backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeUp(self)

    def volumeDown(self):
        #Override because returning the message (which causes speech) causes the backend to hang, not sure why... threading issue?
        self.updateMessage = ThreadedTTSBackend.volumeDown(self)

    def getUpdateMessage(self):
        msg = self.updateMessage
        self.updateMessage = None
        return msg

    def update(self):
        try:
            module = self.setting('module')
            if module: self.speechdObject.set_output_module(module)
            voice = self.setting('voice')
            if voice:
                self.speechdObject.set_language(self.getVoiceLanguage(voice))
                self.speechdObject.set_synthesis_voice(voice)
            self.speechdObject.set_rate(self.setting('speed'))
            self.speechdObject.set_pitch(self.setting('pitch'))
            vol = self.setting('volume')
            self.speechdObject.set_volume(vol - 100) #Covert from % to (-100 to 100)
        except speechd.SSIPCommunicationError:
            util.ERROR('SpeechDispatcherTTSBackend.update()',hide_tb=True)
        msg = self.getUpdateMessage()
        if msg: self.say(msg,interrupt=True)

    def getVoiceLanguage(self,voice):
        res = None
        voices = self.speechdObject.list_synthesis_voices()
        for v in voices:
            if voice == v[0]:
                res = v[1]
                break
        return res

    @classmethod
    def settingList(cls,setting,*args):
        so = getSpeechDSpeaker()
        if setting == 'voice':
            module = cls.setting('module')
            if module: so.set_output_module(module)
            voices = so.list_synthesis_voices()
            return [(v[0],v[0]) for v in voices]
        elif setting == 'module':
            return [(m,m) for m in so.list_output_modules()]

    def close(self):
        if self.speechdObject: self.speechdObject.close()
        del self.speechdObject
        self.speechdObject = None

    @staticmethod
    def available():
        return bool(getSpeechDSpeaker(test=True))


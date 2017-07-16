# -*- coding: utf-8 -*-
import sys, subprocess, os
from lib import util
from base import ThreadedTTSBackend

class OSXSayTTSBackend_Internal(ThreadedTTSBackend):
    provider = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True
    volumeConstraints = (0,100,100,True)
    volumeExternalEndpoints = (0,100)
    volumeStep = 5
    volumeSuffix = '%'
    voicesPath = os.path.join(util.configDirectory(),'{0}.voices'.format(provider))
    settings = {
                    'voice':'',
                    'volume':100,
                    'speed':0
    }

    def __new__(cls):
        try:
            import xbmc #analysis:ignore
            return super(OSXSayTTSBackend, cls).__new__(cls)
        except:
            pass
        return OSXSayTTSBackend_SubProcess()

    def init(self):
        import cocoapy
        self.cocoapy = cocoapy
        self.pool = cocoapy.ObjCClass('NSAutoreleasePool').alloc().init()
        self.synth = cocoapy.ObjCClass('NSSpeechSynthesizer').alloc().init()
        voices = self.longVoices()
        self.saveVoices(voices) #Save the voices to file, so we can get provide them for selection without initializing the synth again
        self.update()

    def threadedSay(self,text):
        if not text: return
        self.synth.startSpeakingString_(self.cocoapy.get_NSString(text))
        while self.synth.isSpeaking():
            util.sleep(10)

    def getWavStream(self,text):
        wav_path = os.path.join(util.getTmpfs(),'speech.wav')
        subprocess.call(['say', '-o', wav_path,'--file-format','WAVE','--data-format','LEI16@22050',text.encode('utf-8')])
        return open(wav_path,'rb')

    def isSpeaking(self):
        return self.synth.isSpeaking()

    def longVoices(self):
        vNSCFArray = self.synth.availableVoices()
        voices = [self.cocoapy.cfstring_to_string(vNSCFArray.objectAtIndex_(i,self.cocoapy.get_NSString('UTF8String'))) for i in range(vNSCFArray.count())]
        return voices

    def update(self):
        self.voice = self.setting('voice')
        self.volume = self.setting('volume') / 100.0
        self.rate = self.setting('speed')
        if self.voice: self.synth.setVoice_(self.cocoapy.get_NSString(self.voice))
        if self.volume: self.synth.setVolume_(self.volume)
        if self.rate: self.synth.setRate_(self.rate)

    def stop(self):
        self.synth.stopSpeaking()

    def close(self):
        self.pool.release()

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'voice':
            lvoices = cls.loadVoices()
            if not lvoices: return None
            voices = [(v,v.rsplit('.',1)[-1]) for v in lvoices]
            return voices

    @classmethod
    def saveVoices(cls,voices):
        if not voices: return
        out = '\n'.join(voices)
        with open(cls.voicesPath,'w') as f: f.write(out)

    @classmethod
    def loadVoices(cls):
        if not os.path.exists(cls.voicesPath): return None
        with open(cls.voicesPath,'r') as f:
            return f.read().splitlines()

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not util.isATV2()

#OLD
class OSXSayTTSBackend(ThreadedTTSBackend):
    provider = 'OSXSay'
    displayName = 'OSX Say (OSX Internal)'
    canStreamWav = True

    def __init__(self):
        util.LOG('OSXSay using subprocess method class')
        self.process = None
        ThreadedTTSBackend.__init__(self)

    def threadedSay(self,text):
        if not text: return
        self.process = subprocess.Popen(['say', text.encode('utf-8')])
        while self.process.poll() == None and self.active: util.sleep(10)

    def getWavStream(self,text):
        wav_path = os.path.join(util.getTmpfs(),'speech.wav')
        subprocess.call(['say', '-o', wav_path,'--file-format','WAVE','--data-format','LEI16@22050',text.encode('utf-8')])
        return open(wav_path,'rb')

    def isSpeaking(self):
        return (self.process and self.process.poll() == None) or ThreadedTTSBackend.isSpeaking(self)

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @staticmethod
    def available():
        return sys.platform == 'darwin' and not util.isATV2()
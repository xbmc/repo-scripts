# -*- coding: utf-8 -*-
import os, subprocess
from base import SimpleTTSBackendBase

class FestivalTTSBackend(SimpleTTSBackendBase):
    provider = 'Festival'
    displayName = 'Festival'
    speedConstraints = (-16,0,12,True)
    pitchConstraints = (50,105,500,True)
    settings = {    
                'voice':'',
                'volume':0,
                'speed':0,
                'pitch':105,
                'player':None
    }
    
    def init(self):
        self.festivalProcess = None
        self.setMode(SimpleTTSBackendBase.WAVOUT)
        self.update()
        
    def runCommand(self,text,outFile):
        if not text: return
        voice = self.voice and '(voice_{0})'.format(self.voice) or ''
        durMult = self.durationMultiplier and "(Parameter.set 'Duration_Stretch {0})".format(self.durationMultiplier) or ''
        pitch = self.pitch != 105 and "(require 'prosody-param)(set-pitch {0})".format(self.pitch) or ''
        self.festivalProcess = subprocess.Popen(['festival','--pipe'],stdin=subprocess.PIPE)
        out = '(audio_mode \'async){0}{1}{2}(utt.save.wave (utt.wave.rescale (SynthText "{3}") {4:.2f} nil)"{5}")\n'.format(voice,durMult,pitch,text.encode('utf-8'),self.volume,outFile)
        self.festivalProcess.communicate(out)
        return True
        
    def update(self):
        self.setPlayer(self.setting('player'))
        self.voice = self.setting('voice')
        volume = self.setting('volume')
        self.volume = 1 * (10**(volume/20.0)) #convert from dB to percent
        speed = self.setting('speed')
        self.durationMultiplier = 1.8 - (((speed + 16)/28.0) * 1.4) #Convert from (-16 to +12) value to (1.8 to 0.4)
        self.pitch = self.setting('pitch')

    def stop(self):
        try:
            self.festivalProcess.terminate()
        except:
            return
    
    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'voice':
            p = subprocess.Popen(['festival','-i'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            d = p.communicate('(voice.list)')
            l = map(str.strip,d[0].rsplit('> (',1)[-1].rsplit(')',1)[0].split('\n'))
            if l: return [(v,v) for v in l]
        return None
        
    @staticmethod
    def available():
        try:
            subprocess.call(['festival', '--help'], stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True
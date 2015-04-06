# -*- coding: utf-8 -*-
import os, subprocess
import base

class Pico2WaveTTSBackend(base.SimpleTTSBackendBase):
    provider = 'pico2wave'
    displayName = 'pico2wave'
    speedConstraints = (20,100,200,True)
    settings = {        'language':'',
                    'speed':0,
                    'player':None,
                    'volume':0
    }

    def init(self):
        self.setMode(base.SimpleTTSBackendBase.WAVOUT)
        self.update()

    def runCommand(self,text,outFile):
        args = ['pico2wave']
        if self.language: args.extend(['-l',self.language])
        args.extend(['-w', '{0}'.format(outFile), '{0}'.format(text.encode('utf-8'))])
        subprocess.call(args)
        return True

    def update(self):
        self.language = self.setting('language')
        self.setPlayer(self.setting('player'))
        self.setSpeed(self.setting('speed'))
        self.setVolume(self.setting('volume'))

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'language':
            try:
                out = subprocess.check_output(['pico2wave','-l','NONE','-w','/dev/null','X'],stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, e:
                out = e.output
            if not 'languages:' in out: return None

        return [ (v,v) for v in out.split('languages:',1)[-1].split('\n\n')[0].strip('\n').split('\n')]

    @staticmethod
    def available():
        try:
            subprocess.call(['pico2wave', '--help'], stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True
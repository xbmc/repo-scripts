# -*- coding: utf-8 -*-

import os, subprocess
import base
from lib import util

def getStartupInfo():
    if hasattr(subprocess,'STARTUPINFO'): #Windows
        startupinfo = subprocess.STARTUPINFO()
        try:
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW #Suppress terminal window
        except:
            startupinfo.dwFlags |= 1
        return startupinfo

    return None

class CepstralTTSOEBackend(base.SimpleTTSBackendBase):
    provider = 'Cepstral_OE'
    displayName = 'Cepstral OpenElec'
    canStreamWav = True

    def init(self):
        self.process = None
        self.aplayProcess = None
        self.setMode(base.SimpleTTSBackendBase.ENGINESPEAK)
        self.restartProcess()

    def runCommand(self,text,outFile):
        args = ['/lib/ld-linux.so.3', '--library-path',  '/storage/music/callie/lib', '/storage/music/callie/bin/swift.bin', '-d', '/storage/music/callie/voices/Callie', '-o', outFile, text]
        subprocess.call(args)
        return True

    def runCommandAndPipe(self,text):
        args = ['/lib/ld-linux.so.3', '--library-path',  '/storage/music/callie/lib', '/storage/music/callie/bin/swift.bin', '-d', '/storage/music/callie/voices/Callie', '-o', '-', text]
        self.process = subprocess.Popen(args,stdout=subprocess.PIPE)
        return self.process.stdout

    def runCommandAndSpeak(self,text):
        self.process.stdin.write(text + '\n\n')

    def restartProcess(self):
        self.stopProcess()
        args = ['/lib/ld-linux.so.3', '--library-path',  '/storage/music/callie/lib', '/storage/music/callie/bin/swift.bin', '-d', '/storage/music/callie/voices/Callie', '-f','-','-o', '-']
        self.process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=(open(os.path.devnull, 'w')))
        self.aplayProcess = subprocess.Popen(['aplay','-q'], stdin=self.proces.stdout, stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)

    def stopProcess(self):
        if self.process:
            try:
                self.process.terminate()
            except:
                pass
        if self.aplayProcess:
            try:
                self.aplayProcess.terminate()
            except:
                pass

#    def stop(self):
#        if not self.process: return
#        try:
#            self.process.terminate()
#        except:
#            pass

    def stop(self):
        self.restartProcess()

    def close(self):
        self.stopProcess()

    @staticmethod
    def available():
        return True

class CepstralTTSBackend(base.SimpleTTSBackendBase):
    provider = 'Cepstral'
    displayName = 'Cepstral'
    canStreamWav = False
    settings = {    'voice':'',
                    'use_aoss':False,
                    'speed':170,
                    'volume':0,
                    'pitch':0

    }

    def init(self):
        self.setMode(base.SimpleTTSBackendBase.ENGINESPEAK)
        self.startupinfo = getStartupInfo()
        self.update()
        self.process = None
        self.restartProcess()

    def restartProcess(self):
        self.stopProcess()
        args = ['swift']
        if self.useAOSS: args.insert(0,'aoss')
        if self.voice: args.extend(('-n',self.voice))
        args.extend(('-p','audio/volume={0},speech/rate={1},speech/pitch/shift={2}'.format(self.volume,self.rate,self.pitch)))
        args.extend(('-f','-'))
        self.process = subprocess.Popen(args, startupinfo=self.startupinfo, stdin=subprocess.PIPE, stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)

    def stopProcess(self):
        if self.process:
            try:
                self.process.terminate()
            except:
                pass

    def runCommandAndSpeak(self,text):
        self.process.stdin.write(text + '\n\n')

    def update(self):
        self.voice = self.setting('voice')
        self.rate = self.setting('speed')
        self.useAOSS = self.setting('use_aoss')
        if self.useAOSS and not util.commandIsAvailable('aoss'):
            util.LOG('Cepstral: Use aoss is enabled, but aoss is not found. Disabling.')
            self.useAOSS = False
        volume = self.setting('volume')
        self.volume = int(round(100 * (10**(volume/20.0)))) #convert from dB to percent
        pitch = self.setting('pitch')
        self.pitch = 0.4 + ((pitch+6)/20.0) * 2 #Convert from (-6 to +14) value to (0.4 to 2.4)

    def stop(self):
        self.restartProcess()

    def close(self):
        self.stopProcess()

    @classmethod
    def getVoiceLines(cls):
        import re
        ret = []
        out = subprocess.check_output(['swift','--voices'],startupinfo=getStartupInfo()).splitlines()
        for l in reversed(out):
            if l.startswith(' ') or l.startswith('-'): break
            ret.append(re.split('\s+\|\s+',l.strip(),6))
        return ret

    @classmethod
    def voices(cls):
        ret = []
        for v in cls.getVoiceLines():
            voice = v[0]
            ret.append((voice,voice))
        return ret

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'voice':
            return cls.voices()
        return None

    @staticmethod
    def available():
        try:
            subprocess.call(['swift', '-V'], startupinfo=getStartupInfo(),stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except (OSError, IOError):
            return False
        return True

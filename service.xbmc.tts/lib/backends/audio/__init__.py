# -*- coding: utf-8 -*-
import os, sys, subprocess, wave, hashlib, threading, shutil, errno

from lib import util

try:
    import xbmc
except:
    xbmc = None

PLAYSFX_HAS_USECACHED = False

try:
    voidWav = os.path.join(xbmc.translatePath(util.xbmcaddon.Addon().getAddonInfo('path')).decode('utf-8'),'resources','wavs','void.wav')
    xbmc.playSFX(voidWav,False)
    PLAYSFX_HAS_USECACHED = True
except:
    pass

def check_snd_bm2835():
    try:
        return 'snd_bcm2835' in subprocess.check_output(['lsmod'])
    except:
        util.ERROR('check_snd_bm2835(): lsmod filed',hide_tb=True)
    return False

def load_snd_bm2835():
    try:
        if not xbmc or not xbmc.getCondVisibility('System.Platform.Linux.RaspberryPi'): return
    except: #Handles the case where there is an xbmc module installed system wide and we're not running xbmc
        return
    if check_snd_bm2835(): return
    import getpass
    #TODO: Maybe use util.raspberryPiDistro() to confirm distro
    if getpass.getuser() == 'root':
        util.LOG('OpenElec on RPi detected - loading snd_bm2835 module...')
        util.LOG(os.system('modprobe snd-bcm2835') and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS')
        #subprocess.call(['modprobe','snd-bm2835']) #doesn't work on OpenElec (only tested) - can't find module
    elif getpass.getuser() == 'pi':
        util.LOG('RaspBMC detected - loading snd_bm2835 module...')
        util.LOG(os.system('sudo -n modprobe snd-bcm2835') and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS') #Will just fail if sudo needs a password
    else:
        util.LOG('UNKNOWN Raspberry Pi - maybe loading snd_bm2835 module...')
        util.LOG(os.system('sudo -n modprobe snd-bcm2835') and 'Load snd_bm2835: FAILED' or 'Load snd_bm2835: SUCCESS') #Will just fail if sudo needs a password

class AudioPlayer:
    ID = ''
    name = ''

    _advanced = False
    needsHashedFilename = False

    types = ('wav',)

    def setSpeed(self,speed): pass
    def setPitch(self,pitch): pass
    def setVolume(self,volume): pass
    def canPipe(self): return False
    def pipe(self,source): pass
    def play(self,path): pass
    def isPlaying(self): return False
    def stop(self): pass
    def close(self): pass

    @staticmethod
    def available(ext=None): return False

class PlaySFXAudioPlayer(AudioPlayer):
    ID = 'PlaySFX'
    name = 'XBMC PlaySFX'
    def __init__(self):
        self._isPlaying = False
        self.event = threading.Event()
        self.event.clear()

    def doPlaySFX(self,path):
        xbmc.playSFX(path,False)

    def play(self,path):
        if not os.path.exists(path):
            util.LOG('playSFXHandler.play() - Missing wav file')
            return
        self._isPlaying = True
        self.doPlaySFX(path)
        f = wave.open(path,'r')
        frames = f.getnframes()
        rate = f.getframerate()
        f.close()
        duration = frames / float(rate)
        self.event.clear()
        self.event.wait(duration)
        self._isPlaying = False

    def isPlaying(self):
        return self._isPlaying

    def stop(self):
        self.event.set()
        xbmc.stopSFX()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        return xbmc and hasattr(xbmc,'stopSFX') and PLAYSFX_HAS_USECACHED

class PlaySFXAudioPlayer_Legacy(PlaySFXAudioPlayer):
    ID = 'PlaySFX_Legacy'
    name = 'XBMC PlaySFX (Legacy)'
    needsHashedFilename = True

    def doPlaySFX(self,path):
        xbmc.playSFX(path)

    def play(self,path):
        PlaySFXAudioPlayer.play(self,path)
        if os.path.exists(path): os.remove(path)

    def stop(self):
        self.event.set()

    @staticmethod
    def available(ext=None):
        return xbmc and hasattr(xbmc,'playSFX') and (not hasattr(xbmc,'stopSFX') or not PLAYSFX_HAS_USECACHED)

class WindowsAudioPlayer(AudioPlayer):
    ID = 'Windows'
    name = 'Windows Internal'
    types = ('wav','mp3')

    def __init__(self,*args,**kwargs):
        import winplay
        self._player = winplay
        self.audio = None
        self.event = threading.Event()
        self.event.clear()

    def play(self,path):
        if not os.path.exists(path):
            util.LOG('WindowsAudioPlayer.play() - Missing wav file')
            return
        self.audio = self._player.load(path)
        self.audio.play()
        self.event.clear()
        self.event.wait(self.audio.milliseconds() / 1000.0)
        if self.event.isSet(): self.audio.stop()
        while self.audio.isplaying(): util.sleep(10)
        self.audio = None

    def isPlaying(self):
        return not self.event.isSet()

    def stop(self):
        self.event.set()

    def close(self):
        self.stop()

    @staticmethod
    def available(ext=None):
        if not sys.platform.startswith('win'): return False
        try:
            import winplay #@analysis:ignore
            return True
        except:
            util.ERROR('winplay import failed',hide_tb=True)
        return False

class SubprocessAudioPlayer(AudioPlayer):
    _availableArgs = None
    _playArgs = None
    _speedArgs = None
    _speedMultiplier = 1
    _volumeArgs = None
    _pipeArgs = None
    kill = False

    def __init__(self):
        self._wavProcess = None
        self.speed = 0
        self.volume = None
        self.active = True

    def speedArg(self,speed):
        return str(speed * self._speedMultiplier)

    def baseArgs(self,path):
        args = []
        args.extend(self._playArgs)
        args[args.index(None)] = path
        return args

    def playArgs(self,path):
        return self.baseArgs(path)

    def canPipe(self):
        return bool(self._pipeArgs)

    def pipe(self,source):
        self._wavProcess = subprocess.Popen(self._pipeArgs,stdin=subprocess.PIPE,stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        try:
            shutil.copyfileobj(source,self._wavProcess.stdin)
        except IOError,e:
            if e.errno != errno.EPIPE:
                util.ERROR('Error piping audio',hide_tb=True)
        except:
            util.ERROR('Error piping audio',hide_tb=True)
        source.close()
        self._wavProcess.stdin.close()
        while self._wavProcess.poll() == None and self.active: util.sleep(10)

    def setSpeed(self,speed):
        self.speed = speed

    def setVolume(self,volume):
        self.volume = volume

    def play(self,path):
        args = self.playArgs(path)
        self._wavProcess = subprocess.Popen(args,stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)

        while self._wavProcess.poll() == None and self.active: util.sleep(10)

    def isPlaying(self):
        return self._wavProcess and self._wavProcess.poll() == None

    def stop(self):
        if not self._wavProcess or self._wavProcess.poll(): return
        try:
            if self.kill:
                self._wavProcess.kill()
            else:
                self._wavProcess.terminate()
        except:
            pass

    def close(self):
        self.active = False
        if not self._wavProcess or self._wavProcess.poll(): return
        try:
            self._wavProcess.kill()
        except:
            pass

    @classmethod
    def available(cls,ext=None):
        try:
            subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except:
            return False
        return True

class AplayAudioPlayer(SubprocessAudioPlayer):
    ID = 'aplay'
    name = 'aplay'
    _availableArgs = ('aplay','--version')
    _playArgs = ('aplay','-q',None)
    _pipeArgs = ('aplay','-q')
    kill = True

class PaplayAudioPlayer(SubprocessAudioPlayer):
    ID = 'paplay'
    name = 'paplay'
    _availableArgs = ('paplay','--version')
    _playArgs = ('paplay',None)
    _pipeArgs = ('paplay',)
    _volumeArgs = ('--volume',None)

    def playArgs(self,path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(int(65536 * (10**(self.volume/20.0)))) #Convert dB to paplay value
        return args

class AfplayPlayer(SubprocessAudioPlayer): #OSX
    ID = 'afplay'
    name = 'afplay'
    _availableArgs = ('afplay','-h')
    _playArgs = ('afplay',None)
    _speedArgs = ('-r',None)
    _volumeArgs = ('-v',None)
    kill = True
    types = ('wav','mp3')

    def setVolume(self,volume):
        self.volume = min(int(100 * (10**(volume/20.0))),100) #Convert dB to percent

    def setSpeed(self,speed):
        self.speed = speed * 0.01

    def playArgs(self,path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = str(self.speed)
        return args

class SOXAudioPlayer(SubprocessAudioPlayer):
    ID = 'sox'
    name = 'SOX'
    _availableArgs = ('sox','--version')
    _playArgs = ('play','-q',None)
    _pipeArgs = ('play','-q','-')
    _speedArgs = ('tempo','-s',None)
    _speedMultiplier = 0.01
    _volumeArgs = ('vol',None,'dB')
    kill = True
    types = ('wav','mp3')

    def playArgs(self,path):
        args = self.baseArgs(path)
        if self.volume:
            args.extend(self._volumeArgs)
            args[args.index(None)] = str(self.volume)
        if self.speed:
            args.extend(self._speedArgs)
            args[args.index(None)] = self.speedArg(self.speed)
        return args

    @classmethod
    def available(cls,ext=None):
        try:
            if ext == 'mp3':
                if not 'mp3' in subprocess.check_output(['sox','--help']): return False
            else:
                subprocess.call(cls._availableArgs, stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        except:
            return False
        return True

class MPlayerAudioPlayer(SubprocessAudioPlayer):
    ID = 'mplayer'
    name = 'MPlayer'
    _availableArgs = ('mplayer','--help')
    _playArgs = ('mplayer','-really-quiet',None)
    _pipeArgs = ('mplayer','-','-really-quiet','-cache','8192')
    _speedArgs = 'scaletempo=scale={0}:speed=none'
    _speedMultiplier = 0.01
    _volumeArgs = 'volume={0}'
    types = ('wav','mp3')

    def playArgs(self,path):
        args = self.baseArgs(path)
        if self.speed or self.volume:
            args.append('-af')
            filters = []
            if self.speed:
                filters.append(self._speedArgs.format(self.speedArg(self.speed)))
            if self.volume != None:
                filters.append(self._volumeArgs.format(self.volume))
            args.append(','.join(filters))
        return args

class Mpg123AudioPlayer(SubprocessAudioPlayer):
    ID = 'mpg123'
    name = 'mpg123'
    _availableArgs = ('mpg123','--version')
    _playArgs = ('mpg123','-q',None)
    _pipeArgs = ('mpg123','-q','-')
    types = ('mp3',)

class Mpg321AudioPlayer(SubprocessAudioPlayer):
    ID = 'mpg321'
    name = 'mpg321'
    _availableArgs = ('mpg321','--version')
    _playArgs = ('mpg321','-q',None)
    _pipeArgs = ('mpg321','-q','-')
    types = ('mp3',)

class Mpg321OEPiAudioPlayer(SubprocessAudioPlayer):
    ID = 'mpg321_OE_Pi'
    name = 'mpg321 OE Pi'

    types = ('mp3',)

    def __init__(self):
        self._wavProcess = None
        import OEPiExtras
        OEPiExtras.init()
        self.env = OEPiExtras.getEnvironment()
        self.active = True

    def canPipe(self): return True

    def pipe(self,source):
        self._wavProcess = subprocess.Popen('mpg321 - --wav - | aplay',stdin=subprocess.PIPE,stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT,env=self.env,shell=True)
        try:
            shutil.copyfileobj(source,self._wavProcess.stdin)
        except IOError,e:
            if e.errno != errno.EPIPE:
                util.ERROR('Error piping audio',hide_tb=True)
        except:
            util.ERROR('Error piping audio',hide_tb=True)
        source.close()
        self._wavProcess.stdin.close()
        while self._wavProcess.poll() == None and self.active: util.sleep(10)

    def play(self,path):
        self._wavProcess = subprocess.Popen('mpg321 --wav - "{0}" | aplay'.format(path),stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT,env=self.env,shell=True)

    @classmethod
    def available(cls,ext=None):
        try:
            import OEPiExtras #analysis:ignore
        except:
            return False
        return True

class BasePlayerHandler:
    def setSpeed(self,speed): pass
    def setVolume(self,speed): pass
    def player(self): return None
    def canPipe(self): return False
    def pipeAudio(self,source): pass
    def getOutFile(self,text): raise Exception('Not Implemented')
    def play(self): raise Exception('Not Implemented')
    def isPlaying(self): raise Exception('Not Implemented')
    def stop(self): raise Exception('Not Implemented')
    def close(self): raise Exception('Not Implemented')

    def setOutDir(self):
        tmpfs = util.getTmpfs()
        if util.getSetting('use_tmpfs',True) and tmpfs:
            util.LOG('Using tmpfs at: {0}'.format(tmpfs))
            self.outDir = os.path.join(tmpfs,'xbmc_speech')
        else:
            self.outDir = os.path.join(util.profileDirectory(),'xbmc_speech')
        if not os.path.exists(self.outDir): os.makedirs(self.outDir)

class WavAudioPlayerHandler(BasePlayerHandler):
    players = (PlaySFXAudioPlayer,PlaySFXAudioPlayer_Legacy,WindowsAudioPlayer,AfplayPlayer,SOXAudioPlayer,PaplayAudioPlayer,AplayAudioPlayer,MPlayerAudioPlayer)
    def __init__(self,preferred=None,advanced=False):
        self.preferred = False
        self.advanced = advanced
        self.setOutDir()
        self.outFileBase = os.path.join(self.outDir,'speech%s.wav')
        self.outFile = os.path.join(self.outDir,'speech.wav')
        self._player = AudioPlayer()
        self.hasAdvancedPlayer = False
        self._getAvailablePlayers()
        self.setPlayer(preferred,advanced)

    def getPlayerID(self,ID):
        for i in self.availablePlayers:
            if i.ID == ID: return i
        return None

    def player(self):
        return self._player and self._player.ID or None

    def canPipe(self):
        return self._player.canPipe()

    def pipeAudio(self,source):
        return self._player.pipe(source)

    def playerAvailable(self):
        return bool(self.availablePlayers)

    def _getAvailablePlayers(self):
        self.availablePlayers = self.getAvailablePlayers()
        for p in self.availablePlayers:
            if p._advanced:
                break
                self.hasAdvancedPlayer = True

    def setPlayer(self,preferred=None,advanced=None):
        if preferred == self._player.ID or preferred == self.preferred: return self._player
        self.preferred = preferred
        if advanced == None: advanced = self.advanced
        old = self._player
        player = None
        if preferred: player = self.getPlayerID(preferred)
        if player:
            self._player = player()
        elif advanced and self.hasAdvancedPlayer:
            for p in self.availablePlayers:
                if p._advanced:
                    self._player = p()
                    break
        elif self.availablePlayers:
            self._player = self.availablePlayers[0]()
        else:
            self._player = AudioPlayer()

        if self._player and old.ID != self._player: util.LOG('Player: %s' % self._player.name)
        if not self._player.ID == 'PlaySFX': load_snd_bm2835() #For Raspberry Pi
        return self._player

    def _deleteOutFile(self):
        if os.path.exists(self.outFile): os.remove(self.outFile)

    def getOutFile(self,text):
        if self._player.needsHashedFilename:
            self.outFile = self.outFileBase % hashlib.md5(text).hexdigest()
        return self.outFile

    def setSpeed(self,speed):
        return self._player.setSpeed(speed)

    def setVolume(self,volume):
        return self._player.setVolume(volume)

    def play(self):
        return self._player.play(self.outFile)

    def isPlaying(self):
        return self._player.isPlaying()

    def stop(self):
        return self._player.stop()

    def close(self):
        for f in os.listdir(self.outDir):
            if f.startswith('.'): continue
            fpath = os.path.join(self.outDir,f)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except:
                    util.ERROR('Error Removing File',hide_tb=True)
        return self._player.close()

    @classmethod
    def getAvailablePlayers(cls):
        players = []
        for p in cls.players:
            if p.available(): players.append(p)
        return players

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available(): return True
        return False

class MP3AudioPlayerHandler(WavAudioPlayerHandler):
    players = (WindowsAudioPlayer,AfplayPlayer,SOXAudioPlayer,Mpg123AudioPlayer,Mpg321AudioPlayer,MPlayerAudioPlayer)
    def __init__(self,*args,**kwargs):
        WavAudioPlayerHandler.__init__(self,*args,**kwargs)
        self.outFile = os.path.join(self.outDir,'speech.mp3')

    @classmethod
    def canPlay(cls):
        for p in cls.players:
            if p.available('mp3'): return True
        return False




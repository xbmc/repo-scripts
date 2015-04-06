# -*- coding: utf-8 -*-
import base
import urllib, urllib2
from lib import util
import shutil

class SpeechServerBackend(base.SimpleTTSBackendBase):
    provider = 'ttsd'
    displayName = 'HTTP TTS Server (Requires Running Server)'
    canStreamWav = False

    settings = {    'engine': None,
                    'voice': None,
                    'voice.Flite': None,
                    'voice.eSpeak': None,
                    'voice.SAPI': None,
                    'voice.Cepstral': None,
                    'remote_speed': 0,
                    'player_speed': 0,
                    'remote_pitch': 0,
                    'remote_volume': 0,
                    'player_volume': 0,
                    'host':     '127.0.0.1',
                    'port':     8256,
                    'player': None,
                    'perl_server': True,
                    'speak_on_server': False,
                    'pipe': False
    }

    def init(self):
        self.process = None
        self.failFlag = False
        self.update()

    def setHTTPURL(self):
        host = self.setting('host')
        port = self.setting('port')
        if host and port:
            self.httphost = 'http://{0}:{1}/'.format(host,port)
        else:
            self.httphost = 'http://127.0.0.1:8256/'

    def updatePostdata(self,postdata):
        postdata['engine'] = self.engine
        if self.voice: postdata['voice'] = self.voice
        postdata['rate'] = self.remote_speed
        postdata['pitch'] = self.remote_pitch
        postdata['volume'] = self.remote_volume

    def runCommand(self,text,outFile):
        postdata = {'text': text.encode('utf-8')} #TODO: This fixes encoding errors for non ascii characters, but I'm not sure if it will work properly for other languages
        if self.perlServer:
            postdata['voice'] = self.voice
            postdata['rate'] = self.remote_speed
            req = urllib2.Request(self.httphost + 'speak.wav', urllib.urlencode(postdata))
        else:
            self.updatePostdata(postdata)
            req = urllib2.Request(self.httphost + 'wav', urllib.urlencode(postdata))
        with open(outFile, "w") as wav:
            try:
                res = urllib2.urlopen(req)
                if not res.info().get('Content-Type') == 'audio/x-wav': return False #If not a wav we will crash XBMC
                shutil.copyfileobj(res,wav)
                self.failFlag = False
            except:
                err = util.ERROR('SpeechServerBackend: wav.write',hide_tb=True)
                if self.failFlag: self.flagAsDead(reason=err) #This is the second fail in a row, mark dead
                self.failFlag = True
                return False
        return True

    def runCommandAndSpeak(self,text):
        postdata = {'text': text.encode('utf-8')} #TODO: This fixes encoding errors for non ascii characters, but I'm not sure if it will work properly for other languages
        self.updatePostdata(postdata)
        req = urllib2.Request(self.httphost + 'say', urllib.urlencode(postdata))
        try:
            urllib2.urlopen(req)
            self.failFlag = False
        except:
            err = util.ERROR('SpeechServerBackend: say',hide_tb=True)
            if self.failFlag: self.flagAsDead(reason=err) #This is the second fail in a row, mark dead
            self.failFlag = True
            return False

    def runCommandAndPipe(self,text):
        postdata = {'text': text.encode('utf-8')} #TODO: This fixes encoding errors for non ascii characters, but I'm not sure if it will work properly for other languages
        if self.perlServer:
            postdata['voice'] = self.voice
            postdata['rate'] = self.remote_speed
            req = urllib2.Request(self.httphost + 'speak.wav', urllib.urlencode(postdata))
        else:
            self.updatePostdata(postdata)
            req = urllib2.Request(self.httphost + 'wav', urllib.urlencode(postdata))
        try:
            res = urllib2.urlopen(req)
            if not res.info().get('Content-Type') == 'audio/x-wav': return None
            self.failFlag = False
            return res
        except:
            err = util.ERROR('SpeechServerBackend: Failed to get wav from server',hide_tb=True)
            if self.failFlag: self.flagAsDead(reason=err) #This is the second fail in a row, mark dead
            self.failFlag = True
            return False
        return True

    def getMode(self):
        self.serverMode = False
        if self.setting('speak_on_server'):
            self.serverMode = True
            return base.SimpleTTSBackendBase.ENGINESPEAK
        elif self.setting('pipe'):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def update(self):
        self.setPlayer(self.setting('player'))
        self.setMode(self.getMode())

        self.setHTTPURL()
        self.perlServer = self.setting('perl_server') #Not really currently used
        version = self.getVersion()
        if version.startswith('speech.server'):
            if self.perlServer:
                util.LOG('Perl server not detected. Switch to speech.server mode.')
                self.perlServer = False
        elif version.startswith('perl.server'):
            if not self.perlServer:
                util.LOG('speech.server not detected. Switch to Perl server mode.')
                self.perlServer = True
        else:
            util.LOG('No server detected. Flagging as dead.')
            self.flagAsDead(reason=version)

        if self.perlServer:
            self.voice = self.setting('voice')
        else:
            self.engine = self.setting('engine')
            voice = self.setting('voice.{0}'.format(self.engine))
            if voice: voice = '{0}.{1}'.format(self.engine,voice)
            self.voice = voice
        self.remote_pitch = self.setting('remote_pitch')
        self.remote_speed = self.setting('remote_speed')
        self.setSpeed(self.setting('player_speed'))
        self.remote_volume = self.setting('remote_volume')
        self.setVolume(self.setting('player_volume'))

    def getVersion(self):
        req = urllib2.Request(self.httphost + 'version')
        try:
            resp = urllib2.urlopen(req)
            return resp.read()
        except urllib2.HTTPError, e:
            if e.code == 404: return 'perl.server'
            err = util.ERROR('Failed to get speech.server version',hide_tb=True)
            return err
        except:
            err = util.ERROR('Failed to get speech.server version',hide_tb=True)
            return err

    def serverStop(self):
        req = urllib2.Request(self.httphost + 'stop', '')
        try:
            urllib2.urlopen(req)
        except:
            util.ERROR('SpeechServerBackend: stop',hide_tb=True)

    def stop(self):
        if self.serverMode: self.serverStop()
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    def voices(self,engine=''):
        if engine: engine = '?engine={0}'.format(engine)
        try:
            return urllib2.urlopen(self.httphost + 'voices{0}'.format(engine)).read().splitlines()
        except urllib2.HTTPError:
            return None
        except:
            util.ERROR('SpeechServerBackend: voices',hide_tb=True)
            self.failFlag = True
            return None

    @classmethod
    def settingList(cls,setting,*args):
        self = cls()
        if setting == 'engine':
            try:
                engines = urllib2.urlopen(self.httphost + 'engines/wav',data='').read().splitlines()
            except urllib2.HTTPError:
                return None
            except:
                util.ERROR('SpeechServerBackend: engines',hide_tb=True)
                self.failFlag = True
                return None

            ret = []
            for e in engines:
                ret.append(e.split('.',1))
            return ret
        elif setting.startswith('voice.'):
            ret = []
            voices = self.voices(args[0])
            if not voices: return None
            for v in voices:
                v = v.split('.')[-1]
                ret.append((v,v))
            return ret
        return None

    @staticmethod
    def available():
        return True


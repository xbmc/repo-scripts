# -*- coding: utf-8 -*-

import urllib, urllib2, shutil, os, subprocess
import base, audio
from lib import util
import textwrap

LANGUAGES = [    ('af', 'Afrikaans'),
                ('sq', 'Albanian'),
                ('ca', 'Catalan'),
                ('zh', 'Chinese (Mandarin)'),
                ('hr', 'Croatian'),
                ('cs', 'Czech'),
                ('da', 'Danish'),
                ('nl', 'Dutch'),
                ('en', 'English'),
                ('fi', 'Finnish'),
                ('fr', 'French'),
                ('de', 'German'),
                ('el', 'Greek'),
                ('ht', 'Haitian Creole'),
                ('hu', 'Hungarian'),
                ('is', 'Icelandic'),
                ('id', 'Indonesian'),
                ('it', 'Italian'),
                ('lv', 'Latvian'),
                ('mk', 'Macedonian'),
                ('no', 'Norwegian'),
                ('pl', 'Polish'),
                ('pt', 'Portuguese'),
                ('ro', 'Romanian'),
                ('ru', 'Russian'),
                ('sr', 'Serbian'),
                ('sk', 'Slovak'),
                ('sw', 'Swahili'),
                ('sv', 'Swedish'),
                ('tr', 'Turkish'),
                ('vi', 'Vietnamese'),
                ('cy', 'Welsh')
]

class GoogleTTSBackend(base.SimpleTTSBackendBase):
    provider = 'Google'
    displayName = 'Google'
    ttsURL = 'http://translate.google.com/translate_tts?tl={0}&q={1}'
    canStreamWav = util.commandIsAvailable('mpg123')
    playerClass = audio.MP3AudioPlayerHandler
    settings = {
                    'language':'en',
                    'player':'mpg123',
                    'volume':0,
                    'pipe':False
    }

    def init(self):
        self.process = None
        self.update()

    def threadedSay(self,text):
        if not text: return
        sections = textwrap.wrap(text,100)
        if self.mode == self.PIPE:
            for text in sections:
                source = self.runCommandAndPipe(text)
                if not source: continue
                self.player.pipeAudio(source)
        else:
            for text in sections:
                outFile = self.player.getOutFile(text)
                if not self.runCommand(text,outFile): return
                self.player.play()

    def runCommand(self,text,outFile):
        url = self.ttsURL.format(self.language,urllib.quote(text.encode('utf-8')))
        req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' })
        try:
            resp = urllib2.urlopen(req)
        except:
            util.ERROR('Failed to open Google TTS URL',hide_tb=True)
            return False

        with open(outFile,'wb') as out:
            shutil.copyfileobj(resp,out)
        return True

    def runCommandAndPipe(self,text):
        url = self.ttsURL.format(self.language,urllib.quote(text.encode('utf-8')))
        req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' })
        try:
            resp = urllib2.urlopen(req)
        except:
            util.ERROR('Failed to open Google TTS URL',hide_tb=True)
            return None
        return resp

    def getWavStream(self,text):
        wav_path = os.path.join(util.getTmpfs(),'speech.wav')
        mp3_path = os.path.join(util.getTmpfs(),'speech.mp3')
        self.runCommand(text,mp3_path)
        self.process = subprocess.Popen(['mpg123','-w',wav_path,mp3_path],stdout=(open(os.path.devnull, 'w')), stderr=subprocess.STDOUT)
        while self.process.poll() == None and self.active: util.sleep(10)
        os.remove(mp3_path)
        return open(wav_path,'rb')

    def update(self):
        self.language = self.setting('language')
        self.setPlayer(self.setting('player'))
        self.setVolume(self.setting('volume'))
        self.setMode(self.getMode())

    def getMode(self):
        if self.setting('pipe'):
            return base.SimpleTTSBackendBase.PIPE
        else:
            return base.SimpleTTSBackendBase.WAVOUT

    def stop(self):
        if not self.process: return
        try:
            self.process.terminate()
        except:
            pass

    @classmethod
    def settingList(cls,setting,*args):
        if setting == 'language':
            return LANGUAGES
        return None

    @staticmethod
    def available():
        return audio.MP3AudioPlayerHandler.canPlay()

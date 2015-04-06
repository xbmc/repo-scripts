# -*- coding: utf-8 -*-

import urllib, urllib2, shutil, os
import base, audio
from lib import util
import textwrap
import asyncconnections

class SpeechUtilComTTSBackend(base.SimpleTTSBackendBase):
    provider = 'speechutil'
    displayName = 'speechutil.com'
    ttsURL = 'http://speechutil.com/convert/wav?text={0}'
    headers = { 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36' }
    canStreamWav = True

    def init(self):
        self.process = None

    def threadedSay(self,text):
        if not text: return
        sections = textwrap.wrap(text,100)
        for text in sections:
            outFile = self.player.getOutFile(text)
            if not self.runCommand(text,outFile): return
            self.player.play()

    def runCommand(self,text,outFile):
        h = asyncconnections.Handler()
        o = urllib2.build_opener(h)
        url = self.ttsURL.format(urllib.quote(text.encode('utf-8')))
        req = urllib2.Request(url, headers=self.headers)
        try:
            resp = o.open(req)
        except (asyncconnections.StopRequestedException, asyncconnections.AbortRequestedException):
            return False
        except:
            util.ERROR('Failed to open speechutil.com TTS URL',hide_tb=True)
            return False

        with open(outFile,'wb') as out:
            shutil.copyfileobj(resp,out)
        return True

    def getWavStream(self,text):
        wav_path = os.path.join(util.getTmpfs(),'speech.wav')
        if not self.runCommand(text,wav_path): return None
        return open(wav_path,'rb')

    def stop(self):
        asyncconnections.StopConnection()

    @staticmethod
    def available():
        return audio.WavAudioPlayerHandler.canPlay()

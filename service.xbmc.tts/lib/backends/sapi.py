# -*- coding: utf-8 -*-
import os, sys, wave, array, StringIO
try:
    import importlib
    importHelper = importlib.import_module
except ImportError:
    importHelper = __import__

from base import SimpleTTSBackendBase
from lib import util
from xml.sax import saxutils

def lookupGenericComError(com_error):
    try:
        errno = '0x%08X' % (com_error.hresult & 0xffffffff)
        with open(os.path.join(util.backendsDirectory(),'comerrors.txt'),'r') as f:
            lines = f.read().splitlines()
        for l1,l2,l3 in zip(lines[0::3],lines[1::3],lines[2::3]):
            if errno in l2:
                return l1,l3
    except:
        pass
    return None


class SAPI():
    DEFAULT = 0
    ASYNC = 1
    PURGE_BEFORE_SPEAK = 2
    IS_FILENAME = 4
    IS_XML = 8
    IS_NOT_XML = 16
    PERSIST_XML = 32
    SPEAK_PUNC = 64
    PARSE_SAPI = 128


    def __init__(self):
        self.SpVoice = None
        self.comtypesClient = None
        self.valid = False
        self._voiceName = None
        self.interrupt = False
        try:
            self.reset()
        except:
            util.ERROR('SAPI: Initialization failed: retrying...')
            util.sleep(1000) #May not be necessary, but here it is
            try:
                self.reset()
            except:
                util.ERROR('SAPI: Initialization failed: Giving up.')
                return
        self.valid = True
        self.COMError = importHelper('_ctypes').COMError
        self.setStreamFlags()

    def importComtypes(self):
        #Remove all (hopefully) refrences to comtypes import...
        del self.comtypesClient
        self.comtypesClient = None
        for m in sys.modules.keys():
            if m.startswith('comtypes'): del sys.modules[m]
        import gc
        gc.collect()
        #and then import
        self.comtypesClient = importHelper('comtypes.client')


    def reset(self):
        del self.SpVoice
        self.SpVoice = None
        self.cleanComtypes()
        self.importComtypes()
        self.resetSpVoice()

    def resetSpVoice(self):
        self.SpVoice = self.comtypesClient.CreateObject("SAPI.SpVoice")
        voice = self._getVoice()
        if voice: self.SpVoice.Voice = voice

    def setStreamFlags(self):
        self.flags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        self.streamFlags = self.PARSE_SAPI | self.IS_XML | self.ASYNC
        try:
            self.SpVoice.Speak('',self.flags)
        except self.COMError,e:
            if util.DEBUG:
                self.logSAPIError(e)
                util.LOG('SAPI: XP Detected - changing flags')
            self.flags = self.ASYNC
            self.streamFlags = self.ASYNC

    def cleanComtypes(self): #TODO: Make this SAPI specific?
        try:
            gen = os.path.join(util.backendsDirectory(),'comtypes','gen')
            import stat, shutil
            os.chmod(gen,stat.S_IWRITE)
            shutil.rmtree(gen,ignore_errors=True)
            if not os.path.exists(gen): os.makedirs(gen)
        except:
            util.ERROR('SAPI: Failed to empty comtypes gen dir')

    def logSAPIError(self,com_error,extra=''):
        try:
            errno = str(com_error.hresult)
            with open(os.path.join(util.backendsDirectory(),'sapi_comerrors.txt'),'r') as f:
                lines = f.read().splitlines()
            for l1,l2 in zip(lines[0::2],lines[1::2]):
                bits = l1.split()
                if errno in bits:
                    util.LOG('SAPI specific COM error ({0})[{1}]: {2}'.format(errno,bits[0],l2 or '?'))
                    break
            else:
                error = lookupGenericComError(com_error)
                if error:
                    util.LOG('SAPI generic COM error ({0})[{1}]: {2}'.format(errno,error[0],error[1] or '?'))
                else:
                    util.LOG('Failed to lookup SAPI/COM error: {0}'.format(com_error))
        except:
            util.ERROR('Error looking up SAPI error: {0}'.format(com_error))
        util.LOG('Line: {1} In: {0}{2}'.format(sys.exc_info()[2].tb_frame.f_code.co_name, sys.exc_info()[2].tb_lineno, extra and ' ({0})'.format(extra) or ''))
        if util.DEBUG: util.ERROR('Debug:')

    def _getVoice(self,voice_name=None):
        voice_name = voice_name or self._voiceName
        if voice_name:
            v = self.SpVoice.getVoices() or []
            for i in xrange(len(v)):
                voice=v[i]
                if voice_name==voice.GetDescription():
                    return voice
        return None

    def checkSAPI(func):
        def checker(self,*args,**kwargs):
            if not self.valid:
                util.LOG('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return None
            try:
                return func(self,*args,**kwargs)
            except self.COMError,e:
                self.logSAPIError(e,func.__name__)
            except:
                util.ERROR('SAPI: {0} error'.format(func.__name__))
            self.valid = False
            util.LOG('SAPI: Resetting...')
            util.sleep(1000)
            try:
                self.reset()
                self.valid = True
                util.LOG('SAPI: Resetting succeded.')
                return func(self,*args,**kwargs)
            except self.COMError,e:
                self.valid = False
                self.logSAPIError(e,func.__name__)
            except:
                self.valid = False
                util.ERROR('SAPI: {0} error'.format(func.__name__))

        return checker

    #Wrapped SAPI methods
    @checkSAPI
    def SpVoice_Speak(self,ssml,flags):
        return self.SpVoice.Speak(ssml,flags)

    @checkSAPI
    def SpVoice_GetVoices(self):
        return self.SpVoice.getVoices()

    @checkSAPI
    def stopSpeech(self):
        self.SpVoice.Speak('',self.ASYNC | self.PURGE_BEFORE_SPEAK)

    @checkSAPI
    def SpFileStream(self):
        return self.comtypesClient.CreateObject("SAPI.SpFileStream")

    @checkSAPI
    def SpAudioFormat(self):
        return self.comtypesClient.CreateObject("SAPI.SpAudioFormat")

    @checkSAPI
    def SpMemoryStream(self):
        return self.comtypesClient.CreateObject("SAPI.SpMemoryStream")

    def validCheck(func):
        def checker(self,*args,**kwargs):
            if not self.valid:
                util.LOG('SAPI: Broken - ignoring {0}'.format(func.__name__))
                return
            return func(self,*args,**kwargs)
        return checker

    @validCheck
    def set_SpVoice_Voice(self,voice_name):
        self._voiceName = voice_name
        voice = self._getVoice(voice_name)
        self.SpVoice.Voice = voice

    @validCheck
    def set_SpVoice_AudioOutputStream(self,stream):
        self.SpVoice.AudioOutputStream = stream

class SAPITTSBackend(SimpleTTSBackendBase):
    provider = 'SAPI'
    displayName = 'SAPI (Windows Internal)'
    settings = {        'speak_via_xbmc':True,
                    'voice':'',
                    'speed':0,
                    'pitch':0,
                    'volume':100
    }
    canStreamWav = True
    speedConstraints = (-10,0,10,True)
    pitchConstraints = (-10,0,10,True)
    volumeConstraints = (0,100,100,True)
    volumeExternalEndpoints = (0,100)
    volumeStep = 5
    volumeSuffix = '%'
    baseSSML = u'''<?xml version="1.0"?>
<speak version="1.0"
         xmlns="http://www.w3.org/2001/10/synthesis"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://www.w3.org/2001/10/synthesis
                   http://www.w3.org/TR/speech-synthesis/synthesis.xsd"
         xml:lang="en-US">
  <volume level="{volume}" />
  <pitch absmiddle="{pitch}" />
  <rate absspeed="{speed}" />
  <p>{text}</p>
</speak>'''

    def init(self):
        self.sapi = SAPI()
        if not self.sapi.valid:
            self.flagAsDead('RESET')
            return
        self.update()

    def sapiValidCheck(func):
        def checker(self,*args,**kwargs):
            if not self.sapi or not self.sapi.valid:
                return self.flagAsDead('RESET')
            else:
                return func(self,*args,**kwargs)

        return checker

    @sapiValidCheck
    def runCommand(self,text,outFile):
        stream = self.sapi.SpFileStream()
        if not stream: return False
        try:
            stream.Open(outFile, 3) #3=SSFMCreateForWrite
        except self.sapi.COMError,e:
            self.sapi.logSAPIError(e)
            return False
        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml,self.sapi.streamFlags)
        stream.close()
        return True

    @sapiValidCheck
    def runCommandAndSpeak(self,text):
        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml,self.sapi.flags)

    @sapiValidCheck
    def getWavStream(self,text):
        fmt = self.sapi.SpAudioFormat()
        if not fmt: return None
        fmt.Type = 22

        stream = self.sapi.SpMemoryStream()
        if not stream: return None
        stream.Format = fmt
        self.sapi.set_SpVoice_AudioOutputStream(stream)

        ssml = self.ssml.format(text=saxutils.escape(text))
        self.sapi.SpVoice_Speak(ssml,self.streamFlags)

        wavIO = StringIO.StringIO()
        self.createWavFileObject(wavIO,stream)
        return wavIO

    def createWavFileObject(self,wavIO,stream):
        #Write wave via the wave module
        wavFileObj = wave.open(wavIO,'wb')
        wavFileObj.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
        wavFileObj.writeframes(array.array('B',stream.GetData()).tostring())
        wavFileObj.close()

    def stop(self):
        if not self.sapi: return
        if not self.inWavStreamMode:
            self.sapi.stopSpeech()

    def update(self):
        self.setMode(self.getMode())
        self.ssml = self.baseSSML.format(text='{text}',volume=self.setting('volume'),speed=self.setting('speed'),pitch=self.setting('pitch'))
        voice_name = self.setting('voice')
        self.sapi.set_SpVoice_Voice(voice_name)

    def getMode(self):
        if self.setting('speak_via_xbmc'):
            return SimpleTTSBackendBase.WAVOUT
        else:
            if self.sapi: self.sapi.set_SpVoice_AudioOutputStream(None)
            return SimpleTTSBackendBase.ENGINESPEAK

    @classmethod
    def settingList(cls,setting,*args):
        sapi = SAPI()
        if setting == 'voice':
            voices=[]
            v=sapi.SpVoice_GetVoices()
            if not v: return voices
            for i in xrange(len(v)):
                try:
                    name=v[i].GetDescription()
                except COMError,e: #analysis:ignore
                    sapi.logSAPIError(e)
                voices.append((name,name))
            return voices

    @staticmethod
    def available():
        return sys.platform.lower().startswith('win')

#    def getWavStream(self,text):
#        #Have SAPI write to file
#        stream = self.sapi.SpFileStream()
#        fpath = os.path.join(util.getTmpfs(),'speech.wav')
#        open(fpath,'w').close()
#        stream.Open(fpath,3)
#        self.sapi.set_SpVoice_AudioOutputStream(stream)
#        self.sapi.SpVoice_Speak(text,0)
#        stream.close()
#        return open(fpath,'rb')

#    def createWavFileObject(self,wavIO,stream):
#        #Write wave headers manually
#        import struct
#        data = array.array('B',stream.GetData()).tostring()
#        dlen = len(data)
#        header = struct.pack(        '4sl8slhhllhh4sl',
#                                            'RIFF',
#                                            dlen+36,
#                                            'WAVEfmt ',
#                                            16, #Bits
#                                            1, #Mode
#                                            1, #Channels
#                                            22050, #Samplerate
#                                            22050*16/8, #Samplerate*Bits/8
#                                            1*16/8, #Channels*Bits/8
#                                            16,
#                                            'data',
#                                            dlen
#        )
#        wavIO.write(header)
#        wavIO.write(data)
# -*- coding: utf-8 -*-
import sys, os

sys.path.insert(0,os.path.dirname(__file__))

from lib import util
from base import LogOnlyTTSBackend
from nvda import NVDATTSBackend
from festival import FestivalTTSBackend
from pico2wave import Pico2WaveTTSBackend
from flite import FliteTTSBackend
from osxsay import OSXSayTTSBackend
from sapi import SAPITTSBackend
from espeak import ESpeakTTSBackend, ESpeakCtypesTTSBackend
from speechdispatcher import SpeechDispatcherTTSBackend
from jaws import JAWSTTSBackend
from speech_server import SpeechServerBackend
from cepstral import CepstralTTSBackend #, CepstralTTSOEBackend
from google import GoogleTTSBackend
from speechutil import SpeechUtilComTTSBackend
from recite import ReciteTTSBackend
#from voiceover import VoiceOverBackend #Can't test

backendsByPriority = [  SAPITTSBackend,
                        OSXSayTTSBackend,
                        ESpeakTTSBackend,
                        JAWSTTSBackend,
                        NVDATTSBackend,
                        FliteTTSBackend,
                        Pico2WaveTTSBackend,
                        FestivalTTSBackend,
                        CepstralTTSBackend,
#                        CepstralTTSOEBackend,
                        SpeechDispatcherTTSBackend,
#                        VoiceOverBackend,
                        SpeechServerBackend,
                        ReciteTTSBackend,
                        GoogleTTSBackend,
                        SpeechUtilComTTSBackend,
                        ESpeakCtypesTTSBackend,
                        LogOnlyTTSBackend
]

def removeBackendsByProvider(to_remove):
    rem = []
    for b in backendsByPriority:
        if b.provider in to_remove:
            rem.append(b)
    for r in rem: backendsByPriority.remove(r)

def getAvailableBackends(can_stream_wav=False):
    available = []
    for b in backendsByPriority:
        if not b._available(): continue
        if can_stream_wav and not b.canStreamWav: continue
        available.append(b)
    return available

def getBackendFallback():
    if util.isATV2():
        return FliteTTSBackend
    elif util.isWindows():
        return SAPITTSBackend
    elif util.isOSX():
        return OSXSayTTSBackend
    elif util.isOpenElec():
        return ESpeakTTSBackend
    for b in backendsByPriority:
        if b._available(): return b
    return None

def getVoices(provider):
    voices = None
    bClass = getBackendByProvider(provider)
    if bClass:
        voices = bClass.voices()
    return voices

def getLanguages(provider):
    languages = None
    bClass = getBackendByProvider(provider)
    if bClass:
        with bClass() as b: languages = b.languages()
    return languages

def getSettingsList(provider,setting,*args):
    settings = None
    bClass = getBackendByProvider(provider)
    if bClass:
        settings = bClass.settingList(setting,*args)
    return settings

def getPlayers(provider):
    players = None
    bClass = getBackendByProvider(provider)
    if bClass and hasattr(bClass,'players'):
        players = bClass.players()
    return players

def getBackend(provider='auto'):
    provider = util.getSetting('backend') or provider
    b = getBackendByProvider(provider)
    if not b or not b._available():
         for b in backendsByPriority:
            if b._available(): break
    return b

def getWavStreamBackend(provider='auto'):
    b = getBackendByProvider(provider)
    if not b or not b._available() or not b.canStreamWav:
         for b in backendsByPriority:
            if b._available() and b.canStreamWav: break
    return b

def getBackendByProvider(name):
    if name == 'auto': return None
    for b in backendsByPriority:
        if b.provider == name and b._available():
            return b
    return None

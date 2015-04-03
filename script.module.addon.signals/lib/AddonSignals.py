# -*- coding: utf-8 -*-
import xbmc, xbmcaddon
import binascii
import json

RECEIVER = None

def _getReceiver():
    global RECEIVER
    if not RECEIVER: RECEIVER = SignalReceiver()
    return RECEIVER

def _decodeData(data):
    data = json.loads(data)
    if data: return json.loads(binascii.unhexlify(data[0]))

def _encodeData(data):
    return '\\"[\\"{0}\\"]\\"'.format(binascii.hexlify(json.dumps(data)))

class SignalReceiver(xbmc.Monitor):
    def __init__(self):
        self._slots = {}

    def registerSlot(self,signaler_id,signal,callback):
        if not signaler_id in self._slots: self._slots[signaler_id] = {}
        self._slots[signaler_id][signal] = callback

    def unRegisterSlot(self,signaler_id,signal):
        if not signaler_id in self._slots: return
        if not signal in self._slots[signaler_id]: return
        del self._slots[signaler_id][signal]

    def onNotification(self, sender, method, data):
        if not sender[-7:] == '.SIGNAL': return
        sender = sender[:-7]
        if not sender in self._slots: return
        signal = method.split('.',1)[-1]
        if not signal in self._slots[sender]: return
        self._slots[sender][signal](_decodeData(data))

def registerSlot(signaler_id,signal,callback):
    receiver = _getReceiver()
    receiver.registerSlot(signaler_id,signal,callback)

def unRegisterSlot(signaler_id,signal):
    receiver = _getReceiver()
    receiver.unRegisterSlot(signaler_id,signal)

def sendSignal(signal,data=None,sourceID=None):
    sourceID = sourceID or xbmcaddon.Addon().getAddonInfo('id')
    command = 'XBMC.NotifyAll({0}.SIGNAL,{1},{2})'.format(sourceID,signal,_encodeData(data))
    xbmc.executebuiltin(command)
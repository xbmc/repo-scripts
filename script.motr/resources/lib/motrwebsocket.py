import xbmc, xbmcaddon
from resources.lib import kodiutils

from .ws4py import *
from .ws4py.client.threadedclient import WebSocketClient

import sys
import threading

try:
    import simplejson as json
except ImportError:
    import json

ADDON = xbmcaddon.Addon()
__lang__ = ADDON.getLocalizedString

class MOTRWebsocket(WebSocketClient):
    def __init__(self, MainGUI, url=None, protocols=None, extensions=None, heartbeat_freq=None,
                 ssl_options=None, headers=None, exclude_headers=None):

        if url is None:
            self.WS = None
        else:
            try:
                WebSocketClient.__init__(self, url, protocols, extensions, heartbeat_freq,
                                         ssl_options, headers, exclude_headers)
                self.WS = self
                self.WS.isConnected = False
            except Exception as e:
                xbmc.log(__lang__(30200) + repr(e), xbmc.LOGERROR)

        #Store the GUI for later use
        self.MainGUI = MainGUI

    def isSocketConnected(self):
        if self.WS != None:
            return self.WS.isConnected
        else:
            return False
        
    def opened(self):
        if self.WS != None:
            self.WS.isConnected = True
        self.MainGUI.onWebsocketConnected()

    def terminate(self):
        try:
            if self.WS != None:
                self.WS.isConnected = False
                self.WS.close(1000, "MOTR Kodi going away")
        except Exception as e:
            xbmc.log(__lang__(30201) + repr(e), xbmc.LOGERROR)
            kodiutils.dialogokerror(__lang__(30201) + repr(e))
        finally:
            self.MainGUI.onWebsocketDisconnected()
            
    def closed(self, code, reason=None):
        if self.WS != None:
            self.WS.isConnected = False

    def received_message(self, m):
        self.MainGUI.onWebsocketMessage(m)

    def SendMOTRCommand(self, command, parameter):
        self.JSONSend = json.dumps({'command': command, 'parameter': parameter})
        self.WS.send(self.JSONSend)
        
    def ConnectTo(self, Url, Port, UseSSL, Path):
        if UseSSL == True:
            Header = "wss://"
        else:
            Header = "ws://"
        self.ConnectURL = Header + Url + ":" + str(Port) + "/" + Path
        self.WS= MOTRWebsocket(self.MainGUI, self.ConnectURL)
        self._ConnectThread = threading.Thread(target=self.ConnectThread)
        self._ConnectThread.daemon = True
        self._ConnectThread.start()
        self.MainGUI.onWebsocketConnect()

    def ConnectThread(self):
        try:
            self.WS.connect()
        except Exception as e:
            xbmc.log("ConnectThread - " + __lang__(30200) + repr(e), xbmc.LOGERROR)
            self.MainGUI.onWebsocketError(__lang__(30202) + self.ConnectURL, repr(e))

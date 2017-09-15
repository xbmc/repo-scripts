import json
import os
import random
import threading
import urllib

import websocket
import thread

from texts import PAIRED, UNPAIRED_FROM_ALEXA
from utils import debug, notify, is_websocket_debug_mode, error
import xbmc
import xbmcaddon

NUM_SERVERS = 16
SERVER_DOMAIN = 'miracle-gw-%s.vertolab.com'
SERVER_PORT = 8012
SERVER_PATH = '/miracle/kodi/client/'

KODI_ID_ARG_NAME = 'kodi_id'

INITIAL_BACKOFF_GRACE_PERIOD = 0.4
MAX_BACKOFF_GRACE_PERIOD = 60 * 60


def backoff_step(x):
    if x > MAX_BACKOFF_GRACE_PERIOD:
        return x

    return x * (1 + random.random())


class Client(object):
    def __init__(self, conf, action_map={}):
        self._ws = None
        self._conf = conf
        self._action_map = {
            'set_kodi_id': self.update_kodi_id
        }
        self._action_map.update(action_map)
        self._shutting_down = False
        self._shutdown_complete = threading.Event(True)
        self._connect_complete = threading.Event()
        self._backoff_grace_period = INITIAL_BACKOFF_GRACE_PERIOD

    def update_kodi_id(self, message):
        try:
            if KODI_ID_ARG_NAME not in message:
                debug('No %s was given' % KODI_ID_ARG_NAME)
            else:
                new_kodi_id = message[KODI_ID_ARG_NAME]
                if len(new_kodi_id) > 0:
                    notify(PAIRED)
                else:
                    notify(UNPAIRED_FROM_ALEXA)
                debug('Setting Kodi id to %s' % new_kodi_id)
                # self._conf.kodi_id = new_kodi_id
                self._conf.set_kodi_id(new_kodi_id)
                self._conf.is_paired = len(new_kodi_id) > 0
                self.reconnect()
        except Exception as e:
            error('Error updating kodi_id: %s' % str(e))

    def on_message(self, ws, message):
        debug('Got message %s' % message)
        message = self.parse_message(message)

        if message is None:
            return

        self.take_action(message)

    def take_action(self, miracle_message):
        action = miracle_message['action']
        if action in self._action_map:
            self._action_map[action](miracle_message)
        else:
            debug('Action %s is unknown' % action)

    def parse_message(self, message):
        try:
            unquoted = urllib.unquote(message)
            debug('Received message %s' % unquoted)
            message = json.loads(unquoted)
        except AttributeError:
            debug('Bad format %s' % message)
            message = None
        return message

    def on_error(self, ws, error):
        debug('Got error: %s' % str(error))
        self._backoff_grace_period = backoff_step(self._backoff_grace_period)

    def _should_reconnect(self):
        return not self._shutting_down and self._conf.is_paired

    def on_close(self, ws):
        debug('WebSocket connection on_close')
        self._shutdown_complete.set()
        if self._should_reconnect():
            debug('Should reconnect within %.2f' % self._backoff_grace_period)
            threading.Timer(self._backoff_grace_period, self.connect_in_background).start()
        else:
            debug('Should not reconnect')

    def on_open(self, ws):
        debug('WebSocket connection opened')
        self._backoff_grace_period = INITIAL_BACKOFF_GRACE_PERIOD
        self._shutdown_complete.clear()
        self._connect_complete.set()

    def send_async(self, msg):
        debug('Sending: %s' % msg)

        def inner_send(msg):
            try:
                self._ws.send(msg)
            except websocket.WebSocketConnectionClosedException:
                debug('Tried sending while connection is closed ' + msg)

        thread.start_new_thread(inner_send, (msg, ))

    def pair(self, pair_code):
        debug('Sending pair action with pair_code = %s' % pair_code)
        self.shut_down()
        if not self.connect_and_wait():
            return False
        self.send_async(json.dumps(
            {
                'action': 'pair',
                'pair_code': pair_code
            }
        ))
        return True

    def close(self):
        debug('WebSocket closing connection')
        self._ws.close()
        debug('WebSocket connection closed')

    def shut_down(self):
        debug('Shutting down WebSocket connection')
        self._shutting_down = True
        if self._ws:
            self._ws.close()
            if not self._shutdown_complete.wait(5):
                debug('Socket did not close after 5 seconds')
            self._ws = None
        self._shutting_down = False

    def connect_in_background(self):
        self._connect()

    def connect_and_wait(self):
        return self._connect(True)

    def _connect(self, wait_for_completion=False):
        if is_websocket_debug_mode():
            websocket.enableTrace(True)
        if self._shutting_down:
            debug('Connect requested during shutdown, aborting')
            return
        self._connect_complete.clear()
        url = "wss://%s:%d%s%s" % (
                SERVER_DOMAIN % (ord(self._conf.get_kodi_id()[0]) % NUM_SERVERS,),
                SERVER_PORT,
                SERVER_PATH,
                self._conf.get_kodi_id())
        debug('Connecting to %s' % url)
        ws = websocket.WebSocketApp(
            url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close)
        debug('Connected to %s' % url)
        ws.on_open = self.on_open

        self._ws = ws

        def run_forever():
            ws.run_forever(
                sslopt=dict(
                            ca_certs=xbmc.translatePath(
                                xbmcaddon.Addon().getAddonInfo('path') + '/resources/server.crt').decode('utf-8')
                            ))

        thread.start_new_thread(run_forever, ())
        if wait_for_completion:
            if not self._connect_complete.wait(5):
                debug('Connection failed after 5 seconds')
                return False
        return True

    def reconnect(self):
        debug('Reconnecting...')
        self.close()

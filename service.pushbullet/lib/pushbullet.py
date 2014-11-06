import json

import httplib2
import websocket
import threading

from common import traceError

class Pushbullet():
    """
    Higher level of Pushbullet APIs are provided.
    """

    def __init__(self, access_token=None, user_iden=None, device_iden=None, filter_deny={}, filter_allow={},
                 mirror_mode=True, view_channels = True, base_url='https://api.pushbullet.com/v2/', ping_timeout=6,
                 try_reconnect=10, json_format_response=True, last_modified=0, last_modified_callback=None):
        """
        access_token: access toke.
        user_iden; used for send and receive ephemerals (if not set receive all pushes)
        device_iden: used for send and receive push (if not set receive all pushes)
        filter_deny: object with key as push JSON fields to deny
        filter_allow: object with key as push JSON fields to allow
        mirror_mode: get pushes from other devices
        base_url: default is 'https://api.pushbullet.com/v2/'
        ping_timeout: for not blocking socket
        response_json: if false response is a string, otherwise is a JSON object
        """

        if not access_token:
            raise Exception('You must define access_token')

        self.access_token = access_token
        self.user_iden = user_iden
        self.device_iden = device_iden
        self.filter_deny = filter_deny
        self.filter_allow = filter_allow
        self.mirror_mode = mirror_mode
        self.view_channels = view_channels
        self.base_url = base_url
        self.ping_timeout = ping_timeout
        self.try_reconnect = try_reconnect
        self.json_format_response = json_format_response

        self._h = httplib2.Http()
        self._h.add_credentials(self.access_token, '')

        self._REST_URLS = {
            'pushes': 'pushes',
            'devices': 'devices',
            'contacts': 'contacts',
            'me': 'users/me',
            'ephemerals': 'ephemerals',
            'websocket': 'wss://stream.pushbullet.com/websocket/'
        }

        self._ws = None
        self._ws_thread = None
        self._ws_thread_keep_alive = None
        self._response = None
        self._abortRequested = False
        
        self._last_modified_callback = last_modified_callback
        self.initLastModified(last_modified)

        self._user_on_open = None
        self._user_on_message = None
        self._user_on_close = None
        self._user_on_error = None

    def initLastModified(self,last_modified):
        self._last_modified = last_modified
        # get a push list to find the most recent modified time
        try:
            pushes = self.getPushes()
            if not pushes: return
            self._last_modified = pushes[0].get('modified',0)
            if self._last_modified_callback: self._last_modified_callback(self._last_modified)
        except:
            traceError()

    def getUserInfo(self, json_format_response=None):
        """
        Get the current user information.
        """

        self._response = self._h.request(self.base_url + self._REST_URLS['me'], method='GET')

        return self._getResponse(json_format_response=json_format_response)

    def getDevices(self, json_format_response=None):
        """
        Get devices list.
        """

        self._response = self._h.request(self.base_url + self._REST_URLS['devices'], method='GET')

        return self._getResponse(json_format_response=json_format_response)

    def getDevice(self, iden):
        """
        Get single device.
        """

        devices = self.getDevices(json_format_response=True)['devices']
        for device in devices:
            if device['iden'] == iden:
                return device

        return False

    def getPushes(self, modified_after=0):
        """
        Get pushes list.
        """

        modified_after = self._last_modified if modified_after is 0 else modified_after

        self._response = self._h.request(
            self.base_url + self._REST_URLS['pushes'] + '?modified_after=' + (modified_after and '{0:10f}'.format(modified_after) or '0'), method='GET') # Modified after must be formated or it will be rounded to the nearest 1/100

        pushes = self._getResponse(json_format_response=True)['pushes']

        # filter: only active == True
        pushes = [push for push in pushes if push['active']]

        # filter: for this device target (iden)
        if self.device_iden:
            pushes = [push for push in pushes if ('target_device_iden' not in push or ('target_device_iden' in push and push['target_device_iden'] == self.device_iden))]

        # filter: not view channels
        if not self.view_channels:
            pushes = [push for push in pushes if ('channel_iden' not in push)]

        # filter: only not dismissed
        pushes = [push for push in pushes if ('dismissed' in push and push['dismissed'] is False)]

        if len(pushes):
            # save modified time for next query on pushes
            self._last_modified = pushes[0]['modified']
            if self._last_modified_callback: self._last_modified_callback(self._last_modified)

        return pushes

    def filter(self, pushes, filter_deny={}, filter_allow={}):
        """
        Apply deny allow directive to pushes
        """

        if type(pushes) is not list:
            pushes = [pushes]

        for index, push in enumerate(pushes):
            remove = False

            # deny filter
            if self._matchPush(push, filter_deny):
                remove = True

            # allow filter
            if self._matchPush(push, filter_allow):
                remove = False

            if remove:
                pushes.pop(index)

        return pushes

    def _matchPush(self, push, filter):
        import re

        for (field, filters) in filter.iteritems():
            for filter in filters:
                if field in push and re.match(filter, push[field], re.IGNORECASE):
                    return True

        return False

    def createDevice(self, data, json_format_response=None):
        """
        Get devices list.
        """

        data = json.dumps(data)

        self._response = self._h.request(self.base_url + self._REST_URLS['devices'], method='POST', body=data,
                                         headers={'Content-Type': 'application/json'})

        return self._getResponse(json_format_response=json_format_response)

    def dismissPush(self, iden, json_format_response=None):
        data = json.dumps({'dismissed': True})

        self._response = self._h.request(self.base_url + self._REST_URLS['pushes'] + '/' + str(iden), method='POST', body=data,
                                         headers={'Content-Type': 'application/json'})

        return self._getResponse(json_format_response=json_format_response)

    def _getResponse(self, response=None, json_format_response=None):
        response = self._response if response is None else response
        json_format_response = self.json_format_response if json_format_response is None else json_format_response

        # response is not 200
        if response[0].status != 200:
            raise Exception('Pushbullet server response: (%d) %s' % (
                response[0].status, json.loads(response[1])['error']['message']))

        return json.loads(response[1]) if json_format_response else response


    def realTimeEventStream(self, on_open=None, on_message=None, on_close=None, on_error=None):
        """
        Start Real Time Event Stream
        """

        self._user_on_open = on_open
        self._user_on_message = on_message
        self._user_on_close = on_close
        self._user_on_error = on_error

        # Start thread and reconnect if disconnect
        self._ws_thread_keep_alive = threading.Thread(target=self._webSocketThreadKeepAlive)
        self._ws_thread_keep_alive.start()

    def _webSocketThreadKeepAlive(self):
        evtThreadEnded = None

        while not self._abortRequested:
            # wait websocket disconnection (only on windows)
            # first start don't wait
            if not evtThreadEnded or evtThreadEnded.wait():
                # not first start
                if evtThreadEnded:

                    evtThreadEnded.clear()

                    # wait try_reconnect seconds before try to reconnect
                    for i in range(self.try_reconnect):

                        # if add-on is closed
                        if self._abortRequested: break

                        import time
                        time.sleep(1)

                if self._abortRequested: break

                evtThreadEnded = threading.Event()
                # start real websocket thread
                self._ws_thread = threading.Thread(target=self._websocketThread, kwargs={'evtThreadEnded': evtThreadEnded})
                self._ws_thread.start()

        self._ws_thread.join()

    def _websocketThread(self, evtThreadEnded):
        try:
            websocket.enableTrace(False)
            self._ws = websocket.WebSocketApp(self._REST_URLS['websocket'] + self.access_token,
                                              on_open=self._on_open,
                                              on_message=self._on_message,
                                              on_close=self._on_close,
                                              on_error=self._on_error)

            # ping_timeout is for no blocking call
            self._ws.run_forever(ping_interval=self.ping_timeout/2, ping_timeout=self.ping_timeout)

        except AttributeError:
            self._on_error(websocket, 'No internet connection!')
        except Exception as ex:
            self._on_error(websocket, ex)
        finally:
            evtThreadEnded.set()

    def _on_open(self, websocket):
        self._user_on_open()

    def _on_message(self, websocket, message):
        data = json.loads(message)

        # message type: mirror
        if self.mirror_mode and data['type'] == 'push':
            pushes = data['push']

            # remove/ignore pushes send by this client
            if self.device_iden is not None:
                pushes = self.filter(pushes, filter_deny={'source_device_iden': [self.device_iden]})

            if len(pushes):
                if data['push']['type'] == 'mirror':

                    # apply object/user filters
                    pushes = self.filter(pushes, self.filter_deny, self.filter_allow)

                    if len(pushes):
                        self._user_on_message(pushes[0])

                elif data['push']['type'] == 'dismissal':
                    self._user_on_message(pushes[0])

        # something has changed on the server /v2/pushes resources
        elif data['type'] == 'tickle' and data['subtype'] == 'push':
            for push in self.getPushes():
                if self._user_on_message(push):
                    self.dismissPush(push['iden'])

    def _on_close(self, websocket):
        self._user_on_close()

    def _on_error(self, websocket, error):
        self._user_on_error(error)

    def sendEphemeral(self, data, json_format_response=None):
        """
        Send arbitrary JSON messages, called "ephemerals", to all devices on your account.
        """

        # init defautl data
        data.update({
            'type': 'mirror',
            'package_name': 'com.xbmc.service.pushbullet',
            'notification_tag': None,
            'has_root': True,
            'client_version': 126
        })

        # application_name != 'Pushbullet' => not viewed on Chrome Pushbullet extension
        data['application_name'] = data['application_name'] if 'application_name' in data is not None else 'Pushbullet Kodi Add-on'
        data['dismissable'] = data['dismissable'] if 'dismissable' in data is not None else True

        import random
        data['notification_id'] = data['notification_id'] if 'notification_id' in data is not None else random.randint(-300000000, 300000000)

        if self.user_iden is None:
            self.user_iden = self.getUserInfo(json_format_response=True)['iden']

        data['source_user_iden'] = self.user_iden

        if self.device_iden is None:
            raise Exception('You must define device_iden for send ephemeral')

        data['source_device_iden'] = self.device_iden

        data = {'type': 'push', 'push': data}

        data = json.dumps(data)

        self._response = self._h.request(self.base_url + self._REST_URLS['ephemerals'], method='POST', body=data,
                                         headers={'Content-Type': 'application/json'})

        return self._getResponse(json_format_response=json_format_response)

    def dismissEphemeral(self, data, json_format_response=None):
        """
        Dismiss push called "ephemerals"
        """

        # init defautl data
        data.update({
            'type': 'dismissal',
            'package_name': 'com.xbmc.service.pushbullet',
            'notification_tag': None
        })

        if 'notification_id' not in data:
            raise Exception('You must define notification_id for dismiss ephemeral')

        if self.user_iden is None:
            self.user_iden = self.getUserInfo(json_format_response=True)['iden']

        data['source_user_iden'] = self.user_iden

        if self.device_iden is None:
            raise Exception('You must define device_iden for dismiss ephemeral')

        data['source_device_iden'] = self.device_iden

        data = {'type': 'push', 'push': data}

        data = json.dumps(data)

        self._response = self._h.request(self.base_url + self._REST_URLS['ephemerals'], method='POST', body=data,
                                         headers={'Content-Type': 'application/json'})

        return self._getResponse(json_format_response=json_format_response)

    def setDeviceIden(self, iden):
        """
        Set iden (for send or receive push)
        """
        self.device_iden = iden

    def setUserIden(self, iden):
        """
        Set iden (for send or receive ephemerals)
        """
        self.user_iden = iden

    def setFilterDeny(self, filter_deny):
        """
        Set filter_deny
        """
        self.filter_deny = filter_deny

    def setFilterAllow(self, filter_allow):
        """
        set filter_allow
        """
        self.filter_allow = filter_allow

    def setMirrorMode(self, mirror_mode):
        """
        Set mirror_mode
        """
        self.mirror_mode = mirror_mode

    def setViewChannels(self, view_channels):
        """
        Set view_channels
        """
        self.view_channels = view_channels

    def close(self):
        """
        Stop Real Time Event Stream
        """
        self._abortRequested = True

        if self._ws:
            self._ws.close()

        if self._ws_thread:
            self._ws_thread.join()

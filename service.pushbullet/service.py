# import rpdb2
# rpdb2.start_embedded_debugger('pw')

import xbmc

from lib import common

__addon__        = common.__addon__
__addonid__      = common.__addonid__
__addonversion__ = common.__addonversion__
__addonname__    = common.__addonname__
__addonauthor__  = common.__addonauthor__
__addonpath__    = common.__addonpath__
__addonprofile__ = common.__addonprofile__
__addonicon__    = common.__addonicon__

class Service:
    def __init__(self):
        common.log('Service version %s starting' % __addonversion__)

        self.pushbullet = None
        self.serviceMonitor = None
        self.push2Notification = None
        self.stg_pbAccessToken = None

        # notification time for service error
        self.serviceNotifcationTime = 6000

        # xbmc icon (used as ephemerals icon)
        import os
        xbmcImgPath = os.path.join(__addonpath__, 'resources', 'media', 'xbmc.jpg')
        kodiCmdsNotificationIcon = os.path.join(__addonpath__, 'resources', 'media', 'kcmd.png')

        import base64
        with open(xbmcImgPath, "rb") as imgFile:
            self.xbmcImgEncoded = base64.b64encode(imgFile.read())

        # catch add-on settings change
        self.serviceMonitor = common.serviceMonitor(onSettingsChangedAction=self._checkSettingChanged)

        # convert push to Kodi notification
        import random
        self.pbPlaybackNotificationId = random.randint(-300000000, 300000000)

        from lib.push2Notification import Push2Notification
        self.push2Notification = Push2Notification(notificationIcon=__addonicon__, tempPath=__addonprofile__,
                                                   pbPlaybackNotificationId=self.pbPlaybackNotificationId,
                                                   kodiCmds=common.getKodiCmdsFromFiles(),
                                                   kodiCmdsNotificationIcon=kodiCmdsNotificationIcon)

        self._getSettings()
        self.run()

        while not xbmc.abortRequested:
            xbmc.sleep(200)

        common.log('Closing socket (waiting...)')

        if self.pushbullet: self.pushbullet.close()

        common.log('Service closed')

    def run(self):
        """
        Run or restart service.
        """

        if self.pushbullet:
            common.log('Restarting')
            self.pushbullet.close()

        try:
            if not self.stg_pbAccessToken or not self.stg_pbClientIden:
                raise Exception(common.localise(30100))

            from lib.pushbullet import Pushbullet

            # init pushbullet
            self.pushbullet = Pushbullet(   access_token=self.stg_pbAccessToken,
                                            ping_timeout=6,
                                            last_modified=common.getSetting('last_modified',0),
                                            last_modified_callback=self.setLastModified,
                                            log_callback=common.log)

            # get device info (also if edited by user on Pushbullet panel)
            self._getDevice()

            # setup service and pushbullet (iden, mirroring, filter)
            self._setupService()

            # start listening websocket
            self.pushbullet.realTimeEventStream(on_open=self.push2Notification.onOpen,
                                                on_message=self.push2Notification.onMessage,
                                                on_error=self.push2Notification.onError,
                                                on_close=self.push2Notification.onClose)

            common.log('Service started successfully')

        except Exception as ex:
            common.traceError()
            message = ' '.join(str(arg) for arg in ex.args)

            common.log(message, xbmc.LOGERROR)
            common.showNotification(common.localise(30101), message, self.serviceNotifcationTime)

    def setLastModified(self,modified):
        common.setSetting('last_modified','{0:10f}'.format(modified))
        common.log('Updating last_modified: {0}'.format(modified))

    def _setupService(self):
        common.log('Setup Service and Pushbullet Client')

        # setup pushbullet
        self.pushbullet.setDeviceIden(self.stg_pbClientIden)
        self.pushbullet.setFilterDeny({'application_name': self.stg_pbFilterDeny.split()})
        self.pushbullet.setFilterAllow({'application_name': self.stg_pbFilterAllow.split()})
        self.pushbullet.setMirrorMode(self.stg_pbMirroring)
        self.pushbullet.setAutodismissPushes(self.stg_autodismissPushes)
        self.pushbullet.setViewChannels(self.stg_pbChannels)

        # setup service
        self.push2Notification.setNotificationTime(self.stg_notificationTime*1000)
        common.showNotification.proportionalTextLengthTimeout = self.stg_propotificationTime
        self.push2Notification.setCmdOnDismissPush(self.stg_cmdOnDismissPush.lower())
        self.push2Notification.setCmdOnPhoneCallPush(self.stg_cmdOnPhoneCallPush.lower())

        # outbound mirroring
        if self.stg_pbMirroringOut:
            # trigger for Kodi Notification
            self.serviceMonitor.setOnNotificationAction(self._onKodiNotification)
        else:
            self.serviceMonitor.setOnNotificationAction(None)

    def _checkSettingChanged(self):
        """
        Run the correct "procedure" following which settings are changed
        """

        # if access_token is changed => (re)start service
        if self.stg_pbAccessToken != __addon__.getSetting('pb_access_token'):
            common.log('Access token is changed')

            self._getSettings()
            self.run()

        # if access token is set and...
        elif self.stg_pbAccessToken:

            # ...client_iden has been set => (re)start service
            if not self.stg_pbClientIden and __addon__.getSetting('pb_client_iden'):
                common.log('Device has been set')

                self._getSettings()
                self.run()

            # ...one of the listed settings are changed  => read setting setup service
            elif self._isSettingChanged():
                common.log('Setting is changed by user')

                self._getSettings()
                self._setupService()

    def _isSettingChanged(self):
        if self.stg_notificationTime != int(__addon__.getSetting('notification_time')): return True
        elif self.stg_propotificationTime != (__addon__.getSetting('proportional_notification_time') == 'true'): return True
        elif self.stg_autodismissPushes != (__addon__.getSetting('autodismiss_pushes') == 'true'): return True
        elif self.stg_pbClientIden != __addon__.getSetting('pb_client_iden'): return True
        elif self.stg_pbChannels != (__addon__.getSetting('pb_channels') == 'true'): return True
        elif self.stg_pbMirroring != (__addon__.getSetting('pb_mirroring') == 'true'): return True
        elif self.stg_pbFilterDeny != __addon__.getSetting('pb_filter_deny'): return True
        elif self.stg_pbFilterAllow != __addon__.getSetting('pb_filter_allow'): return True
        elif self.stg_pbMirroringOut != (__addon__.getSetting('pb_mirroring_out') == 'true'): return True
        elif self.stg_pbMirroringOutMediaNfo != (__addon__.getSetting('pb_mirroring_out_media_nfo') == 'true'): return True
        elif self.stg_cmdOnDismissPush != __addon__.getSetting('cmd_on_dismiss_push'): return True
        elif self.stg_cmdOnPhoneCallPush != __addon__.getSetting('cmd_on_phone_call_push'): return True

        # ignore read only settings (pb_client_iden, pb_client_nickname, pb_client_model)

        return False

    def _getSettings(self):
        common.log('Reading settings')

        self.stg_pbAccessToken          = __addon__.getSetting('pb_access_token')
        self.stg_notificationTime       = int(__addon__.getSetting('notification_time'))
        self.stg_propotificationTime    = __addon__.getSetting('proportional_notification_time') == 'true'
        self.stg_autodismissPushes             = __addon__.getSetting('autodismiss_pushes') == 'true'
        self.stg_pbChannels             = __addon__.getSetting('pb_channels') == 'true'

        self.stg_pbMirroring            = __addon__.getSetting('pb_mirroring') == 'true'
        self.stg_pbFilterDeny           = __addon__.getSetting('pb_filter_deny')
        self.stg_pbFilterAllow          = __addon__.getSetting('pb_filter_allow')

        self.stg_pbMirroringOut         = __addon__.getSetting('pb_mirroring_out') == 'true'
        self.stg_pbMirroringOutMediaNfo = __addon__.getSetting('pb_mirroring_out_media_nfo') == 'true'
        self.stg_cmdOnDismissPush       = __addon__.getSetting('cmd_on_dismiss_push')
        self.stg_cmdOnPhoneCallPush       = __addon__.getSetting('cmd_on_phone_call_push')

        # read only settings
        self.stg_pbClientIden           = __addon__.getSetting('pb_client_iden')
        self.stg_pbClientNickname       = __addon__.getSetting('pb_client_nickname')
        self.stg_pbClientModel          = __addon__.getSetting('pb_client_model')

    def _getDevice(self):
        device = self.pushbullet.getDevice(self.stg_pbClientIden)

        if device:
            # set setting
            __addon__.setSetting(id='pb_client_nickname', value=device['nickname'])
            __addon__.setSetting(id='pb_client_model', value=device.get('model','')) # use .get() as model may not be set

            # update vars setting
            self.stg_pbClientNickname = __addon__.getSetting('pb_client_nickname')
            self.stg_pbClientModel  = __addon__.getSetting('pb_client_model')

            common.log('Device %s (%s) found e loaded' % (self.stg_pbClientNickname, self.stg_pbClientModel))
        else:
            raise Exception('No device found with iden: ' + self.stg_pbClientIden)

    # TODO: create a notification2Push class

    def _onKodiNotification(self, sender, method, data):

        import json
        data = json.loads(data)

        if sender == 'xbmc':
            if method == 'Player.OnPlay' and self.stg_pbMirroringOutMediaNfo:
                common.log('onKodiNotification: %s %s %s' % (sender, method, data))

                title = body = icon = None
                playerId = data['player']['playerid']
                if playerId < 0:
                    result = data
                else:
                    result = common.executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetItem", "params": { "properties": ["title","year","tagline","album","artist","plot","episode","season","showtitle","channel","channeltype","channelnumber","thumbnail","file"], "playerid": ' + str(playerId) + ' }, "id": "1"}')

                if 'item' in result:
                    if data['item']['type'] == 'movie':
                        if 'title' in result['item'] and result['item']['title'] != '':
                            title = '%s (%s)' % (result['item']['title'], result['item'].get('year',''))
                            body = result['item'].get('tagline',xbmc.getInfoLabel('VideoPlayer.Tagline'))

                    elif data['item']['type'] == 'song' or data['item']['type'] == 'musicvideo':
                        if 'title' in result['item'] and result['item']['title'] != '':
                            title = result['item']['title']
                            body = '%s / %s' % (result['item']['album'], ', '.join(result['item']['artist']))

                    elif data['item']['type'] == 'picture':
                        title = 'Picture'
                        body = data['item']['file']

                    elif data['item']['type'] == 'episode':
                        title = result['item']['title']
                        body = '%s %sx%s' % (result['item']['showtitle'], result['item']['episode'], result['item']['season'])

                    elif data['item']['type'] == 'channel':
                        title = result['item']['title']
                        body = '%s - %s (%s)' % (result['item']['channelnumber'], result['item']['channel'], result['item']['channeltype'], )

                    else:
                        title = result['item']['label'] if 'label' in result['item'] else result['item']['file']
                        body = None

                    thumbnailFilePath = None
                    if 'thumbnail' in result['item']:
                        thumbnailFilePath = result['item']['thumbnail']
                    else:
                        thumbnailFilePath = xbmc.getInfoLabel('Player.Art(thumb)')

                    if thumbnailFilePath:
                        try:
                            icon = common.fileTobase64(thumbnailFilePath, imgFormat='JPEG', imgSize=(72, 72))
                            if not icon: raise Exception('No Icon')
                        except:
                            icon = self.xbmcImgEncoded

                else:
                    title = 'unknown'
                    body = None
                    icon = self.xbmcImgEncoded

                ephemeralMsg = {'title': title, 'body': body, 'notification_id': self.pbPlaybackNotificationId, 'icon': icon}

                if len(self.pushbullet.sendEphemeral(ephemeralMsg)) == 0:
                    common.log(u'Ephemeral push sended: {0} - {1}'.format(ephemeralMsg['title'], ephemeralMsg['body']))
                else:
                    common.log(u'Ephemeral push NOT send: {0} - {1}'.format(ephemeralMsg['title'], ephemeralMsg['body']), xbmc.LOGERROR)

            elif method == 'Player.OnStop' and self.stg_pbMirroringOutMediaNfo:
                common.log('onKodiNotification: %s %s %s' % (sender, method, data))

                ephemeralDimiss = {'notification_id': self.pbPlaybackNotificationId}

                if len(self.pushbullet.dismissEphemeral(ephemeralDimiss)) == 0:
                    common.log('Ephemeral dismiss send')
                else:
                    common.log('Ephemeral dismiss NOT send', xbmc.LOGERROR)

if __name__ == "__main__":
    import sys

    if sys.argv[0] == 'service.pushbullet' and len(sys.argv) < 2:
        import main
        main.main()

    try:
        args = None
        if len(sys.argv) > 1:
            args = sys.argv[1:]

        if args:
            import main
            main.handleArg(args[0])
        else:
            Service()
    except:
        common.traceError()
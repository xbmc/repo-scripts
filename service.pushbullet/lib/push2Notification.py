import xbmc
from lib import common
from lib import pushhandler

class Push2Notification():
    """
    Pushbullet push to Kodi Notification
    """

    def __init__(self, notificationTime=6000, notificationIcon=None, tempPath=None, pbPlaybackNotificationId=None, cmdOnDismissPush='stop', cmdOnPhoneCallPush='pause', kodiCmds=None, kodiCmdsNotificationIcon=None):
        self.notificationTime = notificationTime
        self.notificationIcon = notificationIcon
        self.tempPath = tempPath
        self.pbPlaybackNotificationId = pbPlaybackNotificationId
        self.cmdOnDismissPush = cmdOnDismissPush
        self.cmdOnPhoneCallPush = cmdOnPhoneCallPush
        self.kodiCmds = kodiCmds
        self.kodiCmdsNotificationIcon = kodiCmdsNotificationIcon

        from os.path import join
        self.imgFilePath = join(self.tempPath, 'temp-notification-icon')

        import re
        self.re_kodiCmd= re.compile('kcmd::(?P<cmd>[a-zA-Z0-9_.-]+)')
        self.re_kodiCmdPlaceholder = re.compile('<\$([a-zA-Z0-9_\[\]]+)>')

    def onMessage(self, message):
        try:
            from json import dumps
            common.log('New push (%s) received: %s' % (message['type'], dumps(message)))

            if message['type'] == 'mirror':
                return self._onMirrorPush(message)

            # kodi action (pause, stop, skip) on push dismiss (from devices)
            elif message['type'] == 'dismissal':
                return self._onDismissPush(message, self.cmdOnDismissPush)

            elif message['type'] == 'link':
                return self._onMessageLink(message)

            elif message['type'] == 'file':
                return self._onMessageFile(message)

            elif message['type'] == 'note':
                return self._onMessageNote(message)

            elif message['type'] == 'address':
                return self._onMessageAddress(message)

            elif message['type'] == 'list':
                return self._onMessageList(message)


        except Exception as ex:
            common.traceError()
            common.log(' '.join(str(arg) for arg in ex.args), xbmc.LOGERROR)

    def _onMessageLink(self, message):
        mediaType = pushhandler.canHandle(message)
        if not mediaType: return False
        return self.handleMediaPush(mediaType,message)

    def _onMessageFile(self, message):
        mediaType = pushhandler.canHandle(message)
        if not mediaType: return False
        return self.handleMediaPush(mediaType,message)

    def _onMessageNote(self, message):
        if not self.executeKodiCmd(message):
            # Show instantly if enabled
            if common.getSetting('handling_note',0) == 0 and pushhandler.canHandle(message):
                pushhandler.handlePush(message)
            # else show notification if enabled
            elif common.getSetting('handling_note',0) == 1:
                self.showNotificationFromMessage(message)
            else:
                return False
        return True

    def _onMessageAddress(self, message):
        # Show instantly if enabled
        if common.getSetting('handling_address',0) == 0 and pushhandler.canHandle(message):
            pushhandler.handlePush(message)
        elif common.getSetting('handling_address',0) == 1:
            self.showNotificationFromMessage(message)
        else:
            return False
        return True

    def _onMessageList(self, message):
        # Show instantly if enabled
        if common.getSetting('handling_list',0) == 0 and pushhandler.canHandle(message):
            pushhandler.handlePush(message)
        elif common.getSetting('handling_list',0) == 1:
            self.showNotificationFromMessage(message)
        else:
            return False
        return True

    def _onDismissPush(self, message, cmd):

        # TODO: add package_name, source_device_iden for be sure is the right dismission
        """
        {"notification_id": 1812, "package_name": "com.podkicker", "notification_tag": null,
        "source_user_iden": "ujy9SIuzSFw", "source_device_iden": "ujy9SIuzSFwsjzWIEVDzOK", "type": "dismissal"}
        """
        if message['notification_id'] == self.pbPlaybackNotificationId:
            common.log('Execute action on dismiss push: %s' % cmd)

            if cmd == 'pause':
                common.executeJSONRPCMethod('Player.PlayPause')
            elif cmd == 'stop':
                common.executeJSONRPCMethod('Player.Stop')
            elif cmd == 'next':
                common.executeJSONRPCMethod('Player.GoTo', {'to': 'next'})

        # Action on phone call
        # Works only with com.android.dialer (Android stock dialer)
        if self.cmdOnPhoneCallPush != 'none' and message.get('package_name', '') in ['com.android.dialer']:

            common.log('Execute action on phone call end (dismiss): %s' % self.cmdOnPhoneCallPush)

            if self.cmdOnPhoneCallPush == 'pause':
                common.executeJSONRPCMethod('Player.PlayPause', {'play': True})

    def _onMirrorPush(self, message):

        if 'icon' in message:
            # BUILD KODI NOTIFICATION
            applicationNameMirrored = message.get('application_name', '')
            titleMirrored = message.get('title', '')

            # Add Title...
            title = applicationNameMirrored if not titleMirrored else applicationNameMirrored + ': '
            title += titleMirrored

            # ...Body...
            body = message.get('body', '').rstrip('\n').replace('\n', ' / ')

            # ...and Icon
            iconPath = common.base64ToFile(message['icon'], self.imgFilePath, imgFormat='JPEG', imgSize=(96, 96))

            common.showNotification(title, body, self.notificationTime, iconPath)

            # Action on phone call
            # Works only with com.android.dialer (Android stock dialer)
            if self.cmdOnPhoneCallPush != 'none' and message.get('package_name', '') in ['com.android.dialer']:

                common.log('Execute action on phone call start (mirror): %s' % self.cmdOnPhoneCallPush)

                if self.cmdOnPhoneCallPush == 'pause':
                    common.executeJSONRPCMethod('Player.PlayPause', {'play': False})
                elif self.cmdOnPhoneCallPush == 'stop':
                    common.executeJSONRPCMethod('Player.Stop')

    def onError(self, error):
        common.log(error, xbmc.LOGERROR)
        common.showNotification(common.localise(30101), error, self.notificationTime, self.notificationIcon)

    def onClose(self):
        common.log('Socket closed')

    def onOpen(self):
        common.log('Socket opened')

    def showNotificationFromMessage(self,message):
        title = message.get('title',message.get('name',message.get('file_name',''))) or message.get('url','').rsplit('/',1)[-1]
        body = message.get('body',message.get('address','')).replace("\n", " / ")
        if not body and message['type'] == 'list':
            body = '{0} items'.format(len(message.get('items',[])))

        common.showNotification(title, body, self.notificationTime, self.notificationIcon)

    def handleMediaPush(self, media_type, message):
        # Check if instant play is enabled for the media type and play
        if media_type in ('video','audio','image'):
            if common.getSetting('handling_{0}'.format(media_type),0) == 0:
                if not pushhandler.mediaPlaying() or common.getSetting('interrupt_media',False):
                    pushhandler.handlePush(message)
                    return True

        if common.getSetting('handling_{0}'.format(media_type),0) == 1:
            self.showNotificationFromMessage(message)
            return True
        return False

    def executeKodiCmd(self, message):
        if self.kodiCmds and 'title' in message:
            match = self.re_kodiCmd.match(message['title'])

            if match:
                cmd = match.group('cmd')

                if cmd in self.kodiCmds:
                    try:
                        cmdObj = self.kodiCmds[cmd]
                        jsonrpc = cmdObj['JSONRPC']

                        if 'body' in message and len(message['body']) > 0:
                            params = message['body'].split('||')

                            # escape bracket '{}' => '{{}}'
                            jsonrpc = jsonrpc.replace('{', '{{').replace('}', '}}')
                            # sobstitute custom placeholder '<$var>' => '{var}'
                            jsonrpc = self.re_kodiCmdPlaceholder.sub('{\\1}', jsonrpc)
                            # format with passed params
                            jsonrpc = jsonrpc.format(params=params)

                        common.log('Executing cmd "%s": %s' % (cmd, jsonrpc))

                        result = common.executeJSONRPC(jsonrpc)

                        common.log('Result for cmd "%s": %s' % (cmd, result))

                        title = common.localise(30104) % cmd
                        body = ''

                        if 'notification' in cmdObj:
                            # same transformation as jsonrpc var
                            body = cmdObj['notification'].replace('{', '{{').replace('}', '}}')
                            body = self.re_kodiCmdPlaceholder.sub('{\\1}', body)
                            body = body.format(result=result)

                    except Exception as ex:
                        title = 'ERROR: ' + common.localise(30104) % cmd
                        body = ' '.join(str(arg) for arg in ex.args)
                        common.log(body, xbmc.LOGERROR)
                        common.traceError()

                    common.showNotification(title, body, self.notificationTime, self.kodiCmdsNotificationIcon)
                    return True

                else:
                    common.log('No "%s" cmd founded!' % cmd, xbmc.LOGERROR)

        return False

    def setNotificationTime(self, notificationTime):
        self.notificationTime = notificationTime

    def setPbPlaybackNotificationId(self, pbPlaybackNotificationId):
        self.pbPlaybackNotificationId = pbPlaybackNotificationId

    def setCmdOnDismissPush(self, cmdOnDismissPush):
        self.cmdOnDismissPush = cmdOnDismissPush

    def setCmdOnPhoneCallPush(self, cmdOnPhoneCallPush):
        self.cmdOnPhoneCallPush = cmdOnPhoneCallPush

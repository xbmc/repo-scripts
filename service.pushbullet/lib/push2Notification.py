import xbmc
from lib.common import *
from lib import pushhandler

class Push2Notification():
    """
    Pushbullet push to Kodi Notification
    """

    def __init__(self, notificationTime=6000, notificationIcon=None, tempPath=None, pbPlaybackNotificationId=None, cmdOnDismissPush='stop', kodiCmds=None, kodiCmdsNotificationIcon=None):
        self.notificationTime = notificationTime
        self.notificationIcon = notificationIcon
        self.tempPath = tempPath
        self.pbPlaybackNotificationId = pbPlaybackNotificationId
        self.cmdOnDismissPush = cmdOnDismissPush
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
            log('New push (%s) received: %s' % (message['type'], dumps(message)))

            if message['type'] == 'mirror':
                if 'icon' in message:
                    iconPath = base64ToFile(message['icon'], self.imgFilePath, imgFormat='JPEG', imgSize=(96, 96))

                    if 'body' in message:
                        body = message['body'].rstrip('\n').replace('\n', ' / ')
                    else:
                        body = None

                    showNotification(message["application_name"], body, self.notificationTime, iconPath)

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
            traceError()
            log(' '.join(str(arg) for arg in ex.args), xbmc.LOGERROR)

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
            if getSetting('handling_note',0) == 0 and pushhandler.canHandle(message):
                pushhandler.handlePush(message)
            # else show notification if enabled
            elif getSetting('handling_note',0) == 1:
                self.showNotificationFromMessage(message)
            else:
                return False
        return True

    def _onMessageAddress(self, message):
        # Show instantly if enabled
        if getSetting('handling_address',0) == 0 and pushhandler.canHandle(message):
            pushhandler.handlePush(message)
        elif getSetting('handling_address',0) == 1:
            self.showNotificationFromMessage(message)
        else:
            return False
        return True

    def _onMessageList(self, message):
        # Show instantly if enabled
        if getSetting('handling_list',0) == 0 and pushhandler.canHandle(message):
            pushhandler.handlePush(message)
        elif getSetting('handling_list',0) == 1:
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
            log('Execute action on dismiss push: %s' % cmd)

            result = executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 1}')

            if len(result) > 0:
                playerId = result[0]['playerid']

                if cmd == 'pause':
                    executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.PlayPause", "params": { "playerid":' + str(playerId) + '}, "id": 1}')
                elif cmd == 'stop':
                    executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.Stop", "params": { "playerid":' + str(playerId) + '}, "id": 1}')
                elif cmd == 'next':
                    executeJSONRPC('{"jsonrpc": "2.0", "method": "Player.GoTo", "params": { "playerid":' + str(playerId) + ', "to": "next"}, "id": 1}')

    def onError(self, error):
        log(error, xbmc.LOGERROR)
        showNotification(localise(30101), error, self.notificationTime, self.notificationIcon)

    def onClose(self):
        log('Socket closed')

    def onOpen(self):
        log('Socket opened')

    def showNotificationFromMessage(self,message):
        title = message.get('title',message.get('name',message.get('file_name',''))) or message.get('url','').rsplit('/',1)[-1]
        body = message.get('body',message.get('address','')).replace("\n", " / ")
        if not body and message['type'] == 'list':
            body = '{0} items'.format(len(message.get('items',[])))

        showNotification(title, body, self.notificationTime, self.notificationIcon)

    def handleMediaPush(self, media_type, message):
        # Check if instant play is enabled for the media type and play
        if media_type in ('video','audio','image'):
            if getSetting('handling_{0}'.format(media_type),0) == 0:
                if not pushhandler.mediaPlaying() or getSetting('interrupt_media',False):
                    pushhandler.handlePush(message)
                    return True

        if getSetting('handling_{0}'.format(media_type),0) == 1:
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

                        log('Executing cmd "%s": %s' % (cmd, jsonrpc))

                        result = executeJSONRPC(jsonrpc)

                        log('Result for cmd "%s": %s' % (cmd, result))

                        title = localise(30104) % cmd
                        body = ''

                        if 'notification' in cmdObj:
                            # same transformation as jsonrpc var
                            body = cmdObj['notification'].replace('{', '{{').replace('}', '}}')
                            body = self.re_kodiCmdPlaceholder.sub('{\\1}', body)
                            body = body.format(result=result)

                    except Exception as ex:
                        title = 'ERROR: ' + localise(30104) % cmd
                        body = ' '.join(str(arg) for arg in ex.args)
                        log(body, xbmc.LOGERROR)
                        traceError()

                    showNotification(title, body, self.notificationTime, self.kodiCmdsNotificationIcon)
                    return True

                else:
                    log('No "%s" cmd founded!' % cmd, xbmc.LOGERROR)

        return False

    def setNotificationTime(self, notificationTime):
        self.notificationTime = notificationTime

    def setPbPlaybackNotificationId(self, pbPlaybackNotificationId):
        self.pbPlaybackNotificationId = pbPlaybackNotificationId

    def setCmdOnDismissPush(self, cmdOnDismissPush):
        self.cmdOnDismissPush = cmdOnDismissPush

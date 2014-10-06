import xbmc
from lib.common import *

class Push2Notification():
    """
    Pushbullet push to Kodi Notification
    """

    def __init__(self, notificationTime=6000, notificationIcon=None, tempPath=None, pbPlaybackNotificationId=None, cmdOnDismissPush='stop'):
        self.notificationTime = notificationTime
        self.notificationIcon = notificationIcon
        self.tempPath = tempPath
        self.pbPlaybackNotificationId = pbPlaybackNotificationId
        self.cmdOnDismissPush = cmdOnDismissPush

        from os.path import join
        self.imgFilePath = join(self.tempPath, 'temp-notification-icon')

        import re
        self.re_youtubeMatchLink = re.compile('http://youtu\.be/(?P<id>[a-zA-Z0-9_-]+)', re.IGNORECASE)
        self.re_youtubeMatch2Link = re.compile('https?://www\.youtube\.com/watch\?v=(?P<id>[a-zA-Z0-9_-]+)', re.IGNORECASE)

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
                self._onDismissPush(message, self.cmdOnDismissPush)

            elif message['type'] == 'link':
                self._onMessageLink(message)

            elif message['type'] == 'note':
                title = message['title'] if 'title' in message else ''
                body = message['body'].replace("\n", " / ") if 'body' in message else ''

                showNotification(title, body, self.notificationTime, self.notificationIcon)

        except Exception as ex:
            traceError()
            log(' '.join(str(arg) for arg in ex.args), xbmc.LOGERROR)

    def _onMessageLink(self, message):
        match = self.re_youtubeMatchLink.search(message['url'])
        if match:
            return playYoutubeVideo(match.group('id'))

        match = self.re_youtubeMatch2Link.search(message['url'])
        if match:
            return playYoutubeVideo(match.group('id'))

        playMedia(message['url'])

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

    def setNotificationTime(self, notificationTime):
        self.notificationTime = notificationTime

    def setPbPlaybackNotificationId(self, pbPlaybackNotificationId):
        self.pbPlaybackNotificationId = pbPlaybackNotificationId

    def setCmdOnDismissPush(self, cmdOnDismissPush):
        self.cmdOnDismissPush = cmdOnDismissPush

def playYoutubeVideo(id):
    log('Opening Youtube video (%s) plugin' % id)

    playMedia('plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + str(id))

def playMedia(url):
    log('Play media: ' + url)

    xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Playlist.Clear","params":{"playlistid":1}}')
    xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Playlist.Add","params":{"playlistid":1,"item":{"file":"' + str(url) + '"}}}')
    return xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Player.Open","params":{"item":{"playlistid":1,"position":0}}}')
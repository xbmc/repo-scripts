import json
import xbmc
import xbmcaddon

from lib import quickjson
from lib.chapters import ChaptersFile
from lib.notificationwindow import NotificationWindow

DURING_CREDITS_STINGER_MESSAGE = 32000
AFTER_CREDITS_STINGER_MESSAGE = 32001
BOTH_STINGERS_MESSAGE = 32002
DURING_CREDITS_STINGER_TYPE = 32003
AFTER_CREDITS_STINGER_TYPE = 32004
DURING_CREDITS_STINGER_TAG = 'duringcreditsstinger'
AFTER_CREDITS_STINGER_TAG = 'aftercreditsstinger'
BOTH_STINGERS_PROPERTY = DURING_CREDITS_STINGER_TAG + ' ' + AFTER_CREDITS_STINGER_TAG

addon = xbmcaddon.Addon()

def log(message, level=xbmc.LOGDEBUG):
    xbmc.log('[service.stinger.notification] {0}'.format(message), level)

class StingerService(xbmc.Monitor):
    def __init__(self):
        super(StingerService, self).__init__()
        self.currentid = None
        self.totalchapters = None
        self._stingertype = None
        self.notified = False
        self.externalchapterstart = None
        self.get_settings()

    def reset(self):
        self.currentid = None
        self.totalchapters = None
        self._stingertype = None
        xbmc.executebuiltin('ClearProperty(stinger, fullscreenvideo)')
        self.notified = False
        self.externalchapterstart = None

    def get_settings(self):
        self.use_simplenotification = addon.getSetting('use_simplenotification') == 'true'
        self.query_chapterdb = addon.getSetting('query_chapterdb') == 'true'
        self.preferredfps = addon.getSetting('preferredfps')
        self.aftercredits_tag = addon.getSetting('aftercreditsstinger_tag')
        self.duringcredits_tag = addon.getSetting('duringcreditsstinger_tag')
        try:
            self.whereis_theend = int(addon.getSetting('timeremaining_notification'))
        except ValueError:
            self.whereis_theend = 10
        try:
            self.notification_visibletime = int(addon.getSetting('notification_visibletime'))
        except ValueError:
            self.notification_visibletime = 8

    @property
    def stingertype(self):
        return self._stingertype

    @stingertype.setter
    def stingertype(self, value):
        self._stingertype = value
        xbmc.executebuiltin('SetProperty(stinger, %s, fullscreenvideo)' % value)

    def run(self):
        while not self.waitForAbort(5):
            if self.currentid and not self.notified:
                if self.check_for_display():
                    self.notify()

    def onNotification(self, sender, method, data):
        if sender == 'service.stinger.notification' and method == 'Other.TagCheck':
            from lib import commander
            commander.graball_stingertags()
            return
        if method not in (('Player.OnStop', 'Player.OnAVStart') if quickjson.get_kodi_version() >= 18
                else ('Player.OnPlay', 'Player.OnStop')):
            return

        data = json.loads(data)
        if is_data_onplay_bugged(data, method):
            data['item']['id'], data['item']['type'] = hack_onplay_databits()

        if not data or 'item' not in data or 'id' not in data['item'] or \
                data['item'].get('type') != 'movie' or data['item']['id'] == -1:
            return
        if method == 'Player.OnStop':
            self.reset()
            return
        if not self.currentid:
            self.currentid = data['item']['id']
            self.checkstingerinfo()

    def checkstingerinfo(self):
        movie = quickjson.get_movie_details(self.currentid)
        if not movie or 'tag' not in movie or not movie['tag']:
            self.stingertype = None
        else:
            duringcredits = DURING_CREDITS_STINGER_TAG in movie['tag'] or self.duringcredits_tag and self.duringcredits_tag in movie['tag']
            aftercredits = AFTER_CREDITS_STINGER_TAG in movie['tag'] or self.aftercredits_tag and self.aftercredits_tag in movie['tag']
            if duringcredits and aftercredits:
                self.stingertype = BOTH_STINGERS_PROPERTY
            elif duringcredits:
                self.stingertype = DURING_CREDITS_STINGER_TAG
            elif aftercredits:
                self.stingertype = AFTER_CREDITS_STINGER_TAG
            else:
                self.stingertype = None

        if not self.stingertype:
            self.currentid = None
            return
        player = xbmc.Player()
        title = xbmc.getInfoLabel('Player.Title')
        while not title:
            if self.waitForAbort(2) or not player.isPlayingVideo():
                self.currentid = None
                return
            title = xbmc.getInfoLabel('Player.Title')
        try:
            self.totalchapters = int(xbmc.getInfoLabel('Player.ChapterCount'))
        except ValueError:
            self.totalchapters = None
        if not player.isPlayingVideo():
            self.currentid = None
            return
        if not self.totalchapters:
            duration = player.getTotalTime()
            chapters = ChaptersFile(title, int(duration), self.preferredfps, self.query_chapterdb)
            self.externalchapterstart = chapters.lastchapterstart

    def check_for_display(self):
        if self.totalchapters:
            if self.on_lastchapter():
                return True
        elif self.externalchapterstart:
            if self.on_lastexternalchapter():
                return True
        else:
            if self.near_endofmovie():
                return True
        return False

    def on_lastchapter(self):
        try:
            return int(xbmc.getInfoLabel('Player.Chapter')) == self.totalchapters
        except ValueError:
            return False

    def on_lastexternalchapter(self):
        return xbmc.getInfoLabel('Player.Time(hh:mm:ss)') > self.externalchapterstart

    def near_endofmovie(self):
        player = xbmc.Player()
        if not player.isPlayingVideo():
            return False
        try:
            timeremaining = (player.getTotalTime() - player.getTime()) // 60
            return timeremaining < self.whereis_theend
        except ValueError:
            return False

    def notify(self):
        if self.notified:
            return
        self.notified = True
        message = None
        if self.stingertype == DURING_CREDITS_STINGER_TAG:
            message = addon.getLocalizedString(DURING_CREDITS_STINGER_MESSAGE)
            stingertype = addon.getLocalizedString(DURING_CREDITS_STINGER_TYPE)
        elif self.stingertype == AFTER_CREDITS_STINGER_TAG:
            message = addon.getLocalizedString(AFTER_CREDITS_STINGER_MESSAGE)
            stingertype = addon.getLocalizedString(AFTER_CREDITS_STINGER_TYPE)
        elif self.stingertype == BOTH_STINGERS_PROPERTY:
            message = addon.getLocalizedString(BOTH_STINGERS_MESSAGE)
            stingertype = '{0}, [LOWERCASE]{1}[/LOWERCASE]'.format(addon.getLocalizedString(DURING_CREDITS_STINGER_TYPE), addon.getLocalizedString(AFTER_CREDITS_STINGER_TYPE))
        if not message:
            return
        if self.use_simplenotification:
            xbmc.executebuiltin('Notification("{0}", "{1}", {2}, special://home/addons/service.stinger.notification/resources/media/logo.png)'.format(stingertype, message, self.notification_visibletime * 1000))
        else:
            window = NotificationWindow('script-stinger-notification-Notification.xml', addon.getAddonInfo('path'), 'Default', '1080i')
            window.message = message
            window.stingertype = stingertype
            window.show()
            self.waitForAbort(self.notification_visibletime)
            window.close()

    def onSettingsChanged(self):
        self.get_settings()

def is_data_onplay_bugged(data, method):
    return 'item' in data and 'id' not in data['item'] and data['item'].get('type') == 'movie' and \
        data['item'].get('title') == '' and quickjson.get_kodi_version() >= 17 and method == 'Player.OnPlay'

def hack_onplay_databits():
    # HACK: Workaround for Kodi 17 bug, not including the correct info in the notification when played
    #  from home window or other non-media windows. http://trac.kodi.tv/ticket/17270

    # VideoInfoTag can be incorrect immediately after the notification as well, keep trying
    if not xbmc.Player().isPlayingVideo(): # But not isPlayingVideo
        return -1, ""
    mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
    count = 0
    while not mediatype and count < 10:
        xbmc.sleep(200)
        if not xbmc.Player().isPlayingVideo():
            return -1, ""
        mediatype = xbmc.Player().getVideoInfoTag().getMediaType()
        count += 1
    if not mediatype:
        return -1, ""
    return xbmc.Player().getVideoInfoTag().getDbId(), mediatype

if __name__ == '__main__':
    log('Started', xbmc.LOGINFO)
    StingerService().run()
    log('Stopped', xbmc.LOGINFO)

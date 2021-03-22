# -*- coding: utf-8 -*-
import sys
from lib.yd_private_libs import util, servicecontrol, updater
from kodi_six import xbmc
from kodi_six import xbmcgui

T = util.T
PY3 = sys.version_info >= (3, 0)


class PlayMonitor(xbmc.Player):
    def onPlayBackStarted(self):
        self.setVideoValidity()

    def onAVStarted(self):
        self.setVideoValidity()

    def setVideoValidity(self):
        if not self.isPlayingVideo():
            return

        valid = ''
        try:
            if '://' in self.getPlayingFile():
                valid = 'VIDEO'
        except RuntimeError:  # Not playing a file
            pass

        xbmcgui.Window(10000).setProperty(
            'script.module.youtube.dl_VALID', valid)


def showOptions(main=None):
    w = OptionsDialog(
        'script-module-youtube-dl-options_dialog.xml',
        util.ADDON.getAddonInfo('path'), 'main', '720p', main=main
    )
    w.doModal()
    del w


class OptionsDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.main = kwargs.get('main')
        self.player = PlayMonitor()
        self.player.setVideoValidity()

    def onClick(self, controlID):
        if controlID == 200:
            self.main.stopDownload()
        elif controlID == 201:
            self.main.stopAllDownloads()
        elif controlID == 202:
            self.main.manageQueue()
        elif controlID == 203:
            self.main.downloadPlaying()
        elif controlID == 204:
            self.main.settings()


class main():
    def __init__(self):
        arg = self.getArg()
        if arg == 'INFO':
            self.showInfo()
        else:
            showOptions(self)

    def getArg(self):
        return sys.argv[-1]

    def downloadPlaying(self):
        title = xbmc.getInfoLabel('Player.Title')
        # xbmc.getInfoLabel('Player.Filenameandpath')
        url = xbmc.Player().getPlayingFile()
        thumbnail = xbmc.getInfoLabel('Player.Art(thumb)')
        extra = None
        if '|' in url:
            url, extra = url.rsplit('|', 1)
            url = url.rstrip('?')
        import time
        info = {'url': url, 'title': title, 'thumbnail': thumbnail,
                'id': int(time.time()), 'media_type': 'video'}
        if extra:
            try:
                if PY3:
                    import urllib.parse as urlparse
                else:
                    import urlparse
                for k, v in urlparse.parse_qsl(extra):
                    if k.lower() == 'user-agent':
                        info['user_agent'] = v
                        break
            except Exception:
                util.ERROR(hide_tb=True)

        util.LOG(repr(info), debug=True)

        from lib import YDStreamExtractor
        YDStreamExtractor.handleDownload(info, filename=title, bg=True)

    def stopDownload(self):
        yes = xbmcgui.Dialog().yesno(T(32039), T(32040))

        if yes:
            servicecontrol.ServiceControl().stopDownload()

    def stopAllDownloads(self):
        yes = xbmcgui.Dialog().yesno(
            T(32041),
            T(32042)
        )
        if yes:
            servicecontrol.ServiceControl().stopAllDownloads()

    def manageQueue(self):
        servicecontrol.ServiceControl().manageQueue()

    def settings(self):
        util.ADDON.openSettings()

    @util.busyDialog
    def _update(self):
        return updater.updateCore(force=True)

    def showInfo(self, updated=False):
        updater.set_youtube_dl_importPath()
        from lib import youtube_dl

        line1 = T(32043).format(
            '[B]{0}[/B]'.format(util.ADDON.getAddonInfo('version')))
        version = youtube_dl.version.__version__
        line2 = T(32044).format('[B]{0}[/B]'.format(version))

        xbmcgui.Dialog().ok(T(32045), line1 + ' ' + line2)

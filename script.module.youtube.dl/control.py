# -*- coding: utf-8 -*-
import sys
from lib.yd_private_libs import util, servicecontrol, updater
import xbmc
import xbmcgui


class PlayMonitor(xbmc.Player):
    def onPlayBackStarted(self):
        self.setVideoValidity()

    def setVideoValidity(self):
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
        elif arg == 'UPDATE':
            self.update()
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
                import urlparse
                for k, v in urlparse.parse_qsl(extra):
                    if k.lower() == 'user-agent':
                        info['user_agent'] = v
                        break
            except:
                util.ERROR(hide_tb=True)

        util.LOG(repr(info), debug=True)

        from lib import YDStreamExtractor
        YDStreamExtractor.handleDownload(info, bg=True)

    def stopDownload(self):
        yes = xbmcgui.Dialog().yesno(
            'Cancel Download', 'Cancel current download?')
        if yes:
            servicecontrol.ServiceControl().stopDownload()

    def stopAllDownloads(self):
        yes = xbmcgui.Dialog().yesno(
            'Cancel Downloads',
            'Cancel current download and',
            'all queued downloads?'
        )
        if yes:
            servicecontrol.ServiceControl().stopAllDownloads()

    def manageQueue(self):
        servicecontrol.ServiceControl().manageQueue()

    def settings(self):
        util.ADDON.openSettings()

    def update(self):
        updated = self._update()
        if updated:
            self.showInfo(updated=True)
        else:
            xbmcgui.Dialog().ok(
                'Up To Date', 'youtube-dl core is already up to date!')

    @util.busyDialog
    def _update(self):
        return updater.updateCore(force=True)

    def showInfo(self, updated=False):
        updater.set_youtube_dl_importPath()
        from lib import youtube_dl
#        from lib import YDStreamUtils
#        import time
        line1 = 'Addon version: [B]{0}[/B]'.format(
            util.ADDON.getAddonInfo('version'))
        version = youtube_dl.version.__version__
        line2 = 'Core version: [B]{0}[/B]'.format(version)
#        line1 = '{0} core version: [B]{1}[/B]'.format(updated and 'Updated' or 'Used', version)
#        check = util.getSetting('last_core_check',0)
#        line2 = 'Never checked for new version.'
#        if check:
#            duration = YDStreamUtils.durationToShortText(int(time.time() - check))
#            line2 = 'Last check for new version: [B]{0}[/B] ago'.format(duration)

        xbmcgui.Dialog().ok('Info', line1, '', line2)


main()

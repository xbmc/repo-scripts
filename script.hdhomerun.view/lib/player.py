# -*- coding: utf-8 -*-
import os
import xbmc, xbmcgui
import util

TRANSCODE_PROFILES = (None,'none','heavy','mobile','internet540','internet480','internet360','internet240')

class PlayerStatus(object):
    def __init__(self):
        self.reset()

    def __eq__(self,val):
        return self.status == val

    def __ne__(self,val):
        return self.status != val

    def __call__(self,status,channel=None,item=None):
        if channel:
            self.channel = channel
            self.item = item
        else:
            if not self.channel:
                return
        self.status = status

    def reset(self):
        self.status = None
        self.index = 0
        self.channel = None
        self.item = None

    def nextSource(self):
        if not self.channel: return None
        self.index += 1
        if len(self.channel.sources) <= self.index: return None
        return self.channel.sources[self.index]

class ChannelPlayer(xbmc.Player):
    def init(self,owner,lineup,touch_mode=False):
        self.status = hasattr(self,'status') and self.status or PlayerStatus() #Keep old if we reset
        self.owner = owner
        self.lineUp = lineup
        self.touchMode = touch_mode

        return self

    def onPlayBackStarted(self):
        self.status('STARTED')
        self.owner.onPlayBackStarted()

    def onPlayBackStopped(self):
        if self.status == 'NOT_STARTED':
            if self.onPlayBackFailed(): return
        self.owner.onPlayBackStopped()
        self.status.reset()

    def onPlayBackEnded(self):
        if self.status == 'NOT_STARTED':
            if self.onPlayBackFailed(): return
        self.owner.onPlayBackEnded()
        self.status.reset()

    def onPlayBackFailed(self):
        source = self.status.nextSource()
        if source:
            util.DEBUG_LOG('Playing from NEXT source: {0}'.format(source.ID))
            self.play(source.url,self.item,self.touchMode,0)
            return True
        else:
            self.status.reset()
            self.owner.onPlayBackFailed()
            return True

    @property
    def url(self):
        return xbmc.getInfoLabel('Player.Filenameandpath') or ''

    def getArgs(self):
        transcode = TRANSCODE_PROFILES[util.getSetting('transcode',0)]
        if not transcode: return ''
        return '?transcode=' + transcode

    def playChannel(self,channel):
        url = channel.sources[0].url
        util.DEBUG_LOG('Playing from source: {0}'.format(channel.sources[0].ID))
        title = '{0} - {1}'.format(channel.number,channel.name)
        item = xbmcgui.ListItem(title,thumbnailImage=channel.guide.icon)
        info = {'Title':  title,
                #'Plot':   currentShow.synopsis,
                'Studio': channel.guide.affiliate
        }
        item.setInfo('video', info)
        util.setSetting('last.channel',channel.number)
        self.status('NOT_STARTED',channel,item)
        args = self.getArgs()
        self.play(url + args,item,self.touchMode,0)

    def isPlayingHDHR(self):
        if not self.isPlaying(): return False
        try:
            path = xbmc.getInfoLabel('Player.Filenameandpath')
            #path = self.getVideoInfoTag().getPath() #Doesn't work, occasionally returns ''
            ip = path.split('://',1)[-1].split('/')[0].split(':')[0]
            if self.lineUp.getDeviceByIP(ip):
                return True
        except:
            util.ERROR()
        return False

class FullsceenVideoInitializer(xbmc.Player):
    def start(self):
        util.DEBUG_LOG('FS video initializer: STARTED')
        ver = util.kodiSimpleVersion()
        print ver
        if ver and ver < 15:
            util.DEBUG_LOG('FS video initializer: FINISHED (Not needed)')
            return
        self._finished = False
        if self.isPlaying():
            return self.finish()
        dummy = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'),'resources','dummy.mp4')
        self.play(dummy)
        while not self._finished:
            xbmc.sleep(100)
        util.DEBUG_LOG('FS video initializer: FINISHED')

    def finish(self):
        if self._finished: return
        util.DEBUG_LOG('WORKAROUND: Activating fullscreen')
        while xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'):
            xbmc.sleep(100)
        xbmc.sleep(500)
        xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')
        self._finished = True

    def onPlayBackStarted(self):
        self.stop()

    def onPlayBackStopped(self):
        self.finish()

    def onPlayBackEnded(self):
        self.finish()
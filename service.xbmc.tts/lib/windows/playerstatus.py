# -*- coding: utf-8 -*-
from base import WindowReaderBase, WindowHandlerBase
from lib import util
import xbmc
T = util.T

class PlayerStatus(WindowHandlerBase):
    ID = 'playerstatus'

    def init(self):
        self.mode = None
        self.progress = ''
        return self

    def updateMode(self,new_mode):
        if new_mode == self.mode: return False
        self.mode = new_mode
        return True

    def updateProgress(self,new_prog):
        if new_prog == self.progress: return False
        self.progress = new_prog
        return True

    def seek(self,isSpeaking):
        if self.updateMode('seeking'):
            return util.XT(773)
        else:
            st = xbmc.getInfoLabel('Player.Time')
            if not isSpeaking and self.updateProgress(st):
                return st.decode('utf-8')

    def getMonitoredText(self,isSpeaking=False):
        #print "%s %s %s" % (xbmc.getCondVisibility('Player.Playing'),xbmc.getCondVisibility('Player.Forwarding'),xbmc.getCondVisibility('Player.Paused'))
        if xbmc.getCondVisibility('Player.Playing'):
            if xbmc.getCondVisibility('Player.DisplayAfterSeek'):
                return self.seek(isSpeaking)
            self.updateMode(None)
            return None
        elif xbmc.getCondVisibility('Player.Paused'):
            if xbmc.getCondVisibility('Player.Caching'):
                if self.updateMode('buffering'):
                    return util.XT(15107)
                else:
                    pct = xbmc.getInfoLabel('Player.CacheLevel')
                    if not isSpeaking and self.updateProgress(pct):
                        return pct.decode('utf-8')
            elif xbmc.getCondVisibility('!Player.Seeking + !Player.DisplayAfterSeek'):
                if self.updateMode('paused'):
                    return u'{0}... {1} {2}'.format(util.XT(112),util.XT(143), xbmc.getInfoLabel('$INFO[MusicPlayer.Artist,$LOCALIZE[557]: ,:] $INFO[Player.Title,$LOCALIZE[369]: ,:]').decode('utf-8'))
            elif xbmc.getCondVisibility('Player.DisplayAfterSeek'):
                return self.seek(isSpeaking)
        elif xbmc.getCondVisibility('Player.Forwarding'):
            if self.updateMode('fastforward'):
                return T(32170)
            else:
                if not isSpeaking:
                    if        xbmc.getCondVisibility('Player.Forwarding2x') and self.updateProgress('2x'): return u'2 X'
                    elif    xbmc.getCondVisibility('Player.Forwarding4x') and self.updateProgress('4x'): return u'4 X'
                    elif    xbmc.getCondVisibility('Player.Forwarding8x') and self.updateProgress('8x'): return u'8 X'
                    elif    xbmc.getCondVisibility('Player.Forwarding16x') and self.updateProgress('16x'): return u'16 X'
                    elif    xbmc.getCondVisibility('Player.Forwarding32x') and self.updateProgress('32x'): return u'32 X'
        elif xbmc.getCondVisibility('Player.Rewinding'):
            if self.updateMode('rewind'):
                return T(32169)
            else:
                if not isSpeaking:
                    if        xbmc.getCondVisibility('Player.Rewinding2x') and self.updateProgress('2x'): return u'2 X'
                    elif    xbmc.getCondVisibility('Player.Rewinding4x') and self.updateProgress('4x'): return u'4 X'
                    elif    xbmc.getCondVisibility('Player.Rewinding8x') and self.updateProgress('8x'): return u'8 X'
                    elif    xbmc.getCondVisibility('Player.Rewinding16x') and self.updateProgress('16x'): return u'16 X'
                    elif    xbmc.getCondVisibility('Player.Rewinding32x') and self.updateProgress('32x'): return u'32 X'
        return None

class PlayerStatusReader(PlayerStatus,WindowReaderBase): pass
#TODO: NOT WORKING AND NOT USED CURRENTLY

# -*- coding: utf-8 -*-
from base import WindowHandlerBase
from lib import addoninfo, util
import xbmcgui
T = util.T

class NoticeDialog(WindowHandlerBase):
    ID = 'notice'

    def init(self):
        self.notices = []
        self._visible = True #Pretend notice was show so we check stuff on startup
        self.lastHeading = '' #401
        self.lastMessage = '' #402
        self.setWindow()
        return self

    def visible(self):
        visible = WindowHandlerBase.visible(self)
        if visible:
            self._visible = True
            return True
        elif self._visible:
            self._visible = False
            return True
        return False

    def setWindow(self):
        self.win = xbmcgui.Window(10107)

    def addNotice(self,heading,message):
        if heading == self.lastHeading and message == self.lastMessage: return False
        self.lastHeading = heading
        self.lastMessage = message
        self.notices.append((heading,message))
        return True

    def takeNoticesForSpeech(self):
        #print 'y'
        if not self.notices: return None
        ret = []
        for n in self.notices:
            ret.append(u'{0}: {1}... {2}'.format(T(32168),n[0],n[1]))
        self.init()
        #print ret
        return ret

    def getMonitoredText(self,isSpeaking=False): #getLabel() Doesn't work currently with FadeLabels
        if self._visible: return None
        if not addoninfo.checkForNewVersions(): return None
        details = addoninfo.getUpdatedAddons()
        if not details: return None
        ret = [u'{0}... '.format(T(32166))]
        for d in details:
            item = u'{0} {1} {2}'.format(d['name'],T(32167),d['version'])
            if not item in ret:
                ret.append(item)
        #print ret
        return ret
#        #print 'x'
#        heading = self.win.getControl(401).getLabel()
#        message = self.win.getControl(402).getLabel()
#        #print repr(message)
#        self.addNotice(heading,message)
#        if not isSpeaking: return self.takeNoticesForSpeech()
#        return None


#class NoticeDialogReader(NoticeHandler,WindowReaderBase): pass
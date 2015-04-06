# -*- coding: utf-8 -*-
import xbmc, re, difflib, time
from base import WindowReaderBase
from lib import util
class VirtualKeyboardReader(WindowReaderBase):
    ID = 'virtualkeyboard'
    ip_re = re.compile('^[\d ]{3}\.[\d ]{3}\.[\d ]{3}.[\d ]{3}$')

    def init(self):
        self.editID = None
        if self.winID == 10103: #Keyboard
            if xbmc.getCondVisibility('Control.IsVisible(310)'): #For Gotham
                self.editID = 310
            else:
                self.editID = 312
        elif self.winID == 10109: #Numeric?
            self.editID = 4
        elif self.winID == 10607: #PVR Search
            self.editID = 9
        self.keyboardText = ''
        self.lastChange = time.time()
        self.lastRead = None

    def getHeading(self):
        return xbmc.getInfoLabel('Control.GetLabel(311)').decode('utf-8')

    def isIP(self,text=None):
        text = text or self.getEditText()
        return self.winID == 10109 and '.' in text #Is numeric input with . in it, so must be IP

    def getEditText(self):
        info = 'Control.GetLabel({0}).index(1)'.format(self.editID)
        return xbmc.getInfoLabel(info).decode('utf-8')
#        t = xbmc.getInfoLabel(info).decode('utf-8')
#        if t == info: return '' #To handle pre GetLabel().index() addition
#        return t

    def getMonitoredText(self,isSpeaking=False):
        text = self.getEditText()
        if text != self.keyboardText:
            if not self.keyboardText and len(text) > 1:
                self.keyboardText = text
                self.lastChange = time.time()
                return None
            self.lastChange = time.time()
            out = ''
            d = difflib.Differ()
            if not text and self.keyboardText:
                self.keyboardText = ''
                out = util.T(32178)
            elif self.isIP(text):
                if self.isIP(text) and self.isIP(self.keyboardText): #IP Address
                    oldip = self.keyboardText.replace(' ','').split('.')
                    newip = text.replace(' ','').split('.')
                    for old,new in zip(oldip,newip):
                        if old == new: continue
                        out = ' '.join(list(new))
                        break
            elif len(text) > len(self.keyboardText):
                for c in d.compare(self.keyboardText,text):
                    if c.startswith('+'):
                        out += u' ' + (c.strip(' +') or util.T(32177))
            else:
                for c in d.compare(self.keyboardText,text):
                    if c.startswith('-'): out += u' ' + (c.strip(' -') or util.T(32177))
                if out: out = out.strip() + ' {0}'.format(util.T(32179))
            self.keyboardText = text
            if out:
                return out.strip()
        else:
            now = time.time()
            if now - self.lastChange > 2: #We haven't had input for a second, read all the text
                if text != self.lastRead:
                    self.lastChange = now
                    self.lastRead = text
                    if self.isIP(text): return text.replace(' ','')
                    return text
        return None

class PVRSGuideSearchDialogReader(VirtualKeyboardReader):
    ID = 'pvrguidesearch'
    editIDs = (9,14,15,16,17)

    def init(self):
        VirtualKeyboardReader.init(self)
        self.editID = 9

    def _resetEditInfo(self):
        self.lastChange = time.time()
        self.lastRead = None
        self.keyboardText = ''

    def getControlText(self,controlID):
        ID = self.window().getFocusId()
        if ID == 9:
            text = xbmc.getLocalizedString(19133).decode('utf-8')
        else:
            text = xbmc.getInfoLabel('System.CurrentControl').decode('utf-8')
            text = text.replace('( )','{0} {1}'.format(self.service.tts.pauseInsert,util.T(32174))).replace('(*)','{0} {1}'.format(self.service.tts.pauseInsert,util.T(32173))) #For boolean settings
        return (text,text)

    def getMonitoredText(self,isSpeaking=False):
        ID = self.window().getFocusId()
        if not ID in self.editIDs:
            self._resetEditInfo()
            return None
        if ID != self.editID:
            self._resetEditInfo()
        self.editID = ID
        return VirtualKeyboardReader.getMonitoredText(self,isSpeaking=isSpeaking)
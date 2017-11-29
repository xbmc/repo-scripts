# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import guitables
import windowparser
import skintables
from lib import util

CURRENT_SKIN = skintables.CURRENT_SKIN

def parseItemExtra(controlID,current=None):
    texts = windowparser.getWindowParser().getListItemTexts(controlID)
    if current and texts:
        while current in texts: texts.pop(texts.index(current))
    return texts

class WindowHandlerBase:
    ID = None
    def __init__(self,win_id=None,service=None):
        self.service = service
        self._reset(win_id)

    def _reset(self,win_id):
        self.winID = win_id
        self.init()

    def window(self):
        return xbmcgui.Window(self.winID)

    def visible(self):
        return xbmc.getCondVisibility('Window.IsVisible({0})'.format(self.winID))

    def init(self): pass

    def getMonitoredText(self,isSpeaking=False): return None

    def close(self): pass

class WindowReaderBase(WindowHandlerBase):
    _slideoutGroupID = 9000

    def getName(self): return guitables.getWindowName(self.winID)

    def getHeading(self): return None

    def getWindowTexts(self): return None

    def getControlDescription(self,controlID): return None

    def getControlText(self,controlID):
        text = xbmc.getInfoLabel('System.CurrentControl').decode('utf-8')
        return (text,text)

    def getControlPostfix(self, controlID, ):
        if not self.service.speakListCount:
            return u''
        numItems = xbmc.getInfoLabel('Container({0}).NumItems'.format(self.service.controlID)).decode('utf-8')
        if numItems:
            return u'... {0} {1}'.format(numItems,numItems != '1' and util.T(32107) or util.T(32106))
        return u''

    def getSecondaryText(self): return None

    def getItemExtraTexts(self,controlID): return None

    def getWindowExtraTexts(self):
        texts = guitables.getExtraTexts(self.winID)
        if not texts: texts = windowparser.getWindowParser().getWindowTexts()
        return texts or None

    def slideoutHasFocus(self):
        return xbmc.getCondVisibility('ControlGroup({0}).HasFocus(0)'.format(self._slideoutGroupID))

    def getSettingControlText(self,controlID):
        text = xbmc.getInfoLabel('System.CurrentControl')
        if text.endswith(')'): #Skip this most of the time
            text = text.replace('( )','{0} {1}'.format(self.service.tts.pauseInsert,util.T(32174))).replace('(*)','{0} {1}'.format(self.service.tts.pauseInsert,util.T(32173))) #For boolean settings
        return text

    def getSlideoutText(self,controlID):
        text = self.getSettingControlText(controlID)
        if not text: return (u'',u'')
        return (text.decode('utf-8'),text)

class DefaultWindowReader(WindowReaderBase):
    ID = 'default'

    def getHeading(self):
        return xbmc.getInfoLabel('Control.GetLabel(1)').decode('utf-8') or u''

    def getWindowTexts(self):
        return guitables.getWindowTexts(self.winID)

    def getControlDescription(self,controlID):
        return skintables.getControlText(self.winID, controlID) or u''

    def getControlText(self,controlID):
        if self.slideoutHasFocus():
            return self.getSlideoutText(controlID)

        if not controlID: return (u'',u'')
        text = xbmc.getInfoLabel('ListItem.Title')
        if not text: text = xbmc.getInfoLabel('Container({0}).ListItem.Label'.format(controlID))
        if not text: text = xbmc.getInfoLabel('Control.GetLabel({0})'.format(controlID))
        if not text: text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        compare = text + xbmc.getInfoLabel('ListItem.StartTime') + xbmc.getInfoLabel('ListItem.EndTime')
        return (text.decode('utf-8'),compare)

    def getSecondaryText(self):
        return guitables.getListItemProperty(self.winID)

    def getItemExtraTexts(self,controlID):
        text = guitables.getItemExtraTexts(self.winID)
        if not text: text = xbmc.getInfoLabel('ListItem.Plot').decode('utf-8')
        if not text: text = xbmc.getInfoLabel('Container.ShowPlot').decode('utf-8')
        if not text: text = xbmc.getInfoLabel('ListItem.Property(Artist_Description)').decode('utf-8')
        if not text: text = xbmc.getInfoLabel('ListItem.Property(Album_Description)').decode('utf-8')
        if not text: text = xbmc.getInfoLabel('ListItem.Property(Addon.Description)').decode('utf-8')
        if not text: text = guitables.getSongInfo()
        if not text: text = parseItemExtra(controlID,self.getControlText(controlID)[0])
        if not text: return None
        if not isinstance(text,(list,tuple)): text = [text]
        return text

class NullReader(WindowReaderBase):
    ID = 'null'
    def getName(self): return None

    def getControlText(self,controlID): return (u'',u'')

    def getWindowExtraTexts(self): return None

class KeymapKeyInputReader(NullReader):
    ID = 'keymapkeyinput'
    def getWindowTexts(self): return [util.T(32124)]

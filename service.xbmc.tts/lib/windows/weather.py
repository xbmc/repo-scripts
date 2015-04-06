# -*- coding: utf-8 -*-
from base import WindowReaderBase, parseItemExtra
import xbmc
import windowparser

class WeatherReader(WindowReaderBase):
    ID = 'weather'

    def getWindowTexts(self):
        return self.getWindowExtraTexts()
    
    def getWindowExtraTexts(self):
        texts = windowparser.getWindowParser().getWindowTexts()
        return texts or None

    def getItemExtraTexts(self,controlID):
        return parseItemExtra(controlID, self.getControlText(controlID)[0])
        
    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        return (text.decode('utf-8'),text)
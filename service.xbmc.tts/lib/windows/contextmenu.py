# -*- coding: utf-8 -*-
import xbmc
from base import WindowReaderBase

class ContextMenuReader(WindowReaderBase):
    ID = 'contextmenu'

    def getControlText(self,controlID):
        text = xbmc.getInfoLabel('System.CurrentControl').decode('utf-8')
        return (text,text)
    
    def getWindowExtraTexts(self):
        return None
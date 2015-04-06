# -*- coding: utf-8 -*-
import xbmc
from base import WindowReaderBase, CURRENT_SKIN
from lib import util

class SelectDialogReader(WindowReaderBase):
    ID = 'selectdialog'

    def getHeading(self):
        if CURRENT_SKIN == 'confluence': return None #Broken for Confluence
        return WindowReaderBase.getHeading(self)

    def getControlText(self,controlID):
        label = xbmc.getInfoLabel('System.CurrentControl').decode('utf-8')
        selected = xbmc.getCondVisibility('Container({0}).ListItem.IsSelected'.format(controlID)) and ': {0}'.format(util.T(32200)) or ''
        text = u'{0}{1}'.format(label,selected)
        return (text,text)

    def getWindowExtraTexts(self):
        return None
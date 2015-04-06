# -*- coding: utf-8 -*-
from base import WindowReaderBase
import xbmc
from lib import util

class SettingsReader(WindowReaderBase):
    ID = 'settings'

    def getWindowExtraTexts(self):
        return None

    def getItemExtraTexts(self,controlID):
        text = xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(controlID))
        if not text: return None
        return [text.decode('utf-8')]

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        sub = u''
        text = self.getSettingControlText(controlID)
        if text.startswith('-'): sub = u'{0}: '.format(util.T(32172))
        return (u'{0}{1}'.format(sub,text.decode('utf-8')),text)
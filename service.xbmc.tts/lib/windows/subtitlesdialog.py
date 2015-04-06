# -*- coding: utf-8 -*-
import xbmc
from base import WindowReaderBase

class SubtitlesDialogReader(WindowReaderBase):
    ID = 'subtitlesdialog'

    def getControlText(self,controlID):
        texts = [xbmc.getInfoLabel('System.CurrentControl').decode('utf-8')]
        if xbmc.getCondVisibility('Container({0}).ListItem.property(hearing_imp)'.format(controlID)): texts.append('closed caption')
        if xbmc.getCondVisibility('Container({0}).ListItem.property(sync)'.format(controlID)): texts.append('sync')
        texts.append(xbmc.getInfoLabel('Container({0}).ListItem.Label2'.format(controlID)).decode('utf-8'))
        texts.append(u'{0} stars'.format(xbmc.getInfoLabel('Container({0}).ListItem.ActualIcon'.format(controlID)).decode('utf-8')))
        text = u': '.join(texts)
        compare = text+xbmc.getInfoLabel('Container({0}).Position'.format(controlID)).decode('utf-8') #TODO: Fix - this doesn't work when scrolling off the top or bottom of the list
        print repr(compare)
        return (text,compare)

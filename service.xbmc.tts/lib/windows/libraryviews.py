# -*- coding: utf-8 -*-
import xbmc
import base
from lib import util

class VideoLibraryWindowReader(base.DefaultWindowReader):
    ID = 'videolibrary'

    def getControlText(self,controlID):
        if self.slideoutHasFocus():
            return self.getSlideoutText(controlID)
        if not controlID: return (u'',u'')
        text = xbmc.getInfoLabel('ListItem.Label')
        if not text: return base.DefaultWindowReader.getControlText(self,controlID)
        status = u''
        if xbmc.getCondVisibility('ListItem.IsResumable'):
            status = u': {0}'.format(util.T(32199).decode('utf-8'))
        else:
            if xbmc.getInfoLabel('ListItem.Overlay') == 'OverlayWatched.png':
                status = u': {0}'.format(util.T(32198).decode('utf-8'))
        return (u'{0}{1}'.format(text.decode('utf-8'),status),text)
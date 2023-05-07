# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui

from resources.kutil131 import addon

ID_BUTTON_YES = 11
ID_BUTTON_NO = 10
ID_BUTTON_EXTRA = 12
ID_LABEL_HEADER = 1
ID_LABEL_TEXT = 9
ID_PROGRESS = 20


class ConfirmDialog(xbmcgui.WindowXMLDialog):
    """
    open yesnodialog, return -1 for cancelled, otherwise index (0-2)
    """
    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, 'ConfirmDialog.xml', kwargs.get('path', ''))
        self.yeslabel = kwargs.get('yeslabel')
        self.nolabel = kwargs.get('nolabel')
        self.header = kwargs.get('header')
        self.text = kwargs.get('text')
        self.extrabutton = kwargs.get('extrabutton')
        self.index = -1

    def onInit(self):
        self.setFocusId(10)
        self.getControl(ID_BUTTON_YES).setLabel(self.yeslabel)
        self.getControl(ID_BUTTON_NO).setLabel(self.nolabel)
        self.getControl(ID_LABEL_HEADER).setLabel(self.header)
        self.getControl(ID_LABEL_TEXT).setText(self.text)
        if self.extrabutton:
            self.getControl(ID_BUTTON_EXTRA).setVisible(True)
            self.getControl(ID_BUTTON_EXTRA).setLabel(self.extrabutton)
        else:
            self.getControl(ID_BUTTON_EXTRA).setVisible(False)
        self.getControl(ID_PROGRESS).setVisible(False)
        self.setFocusId(ID_BUTTON_NO)

    def onClick(self, control_id):
        self.index = control_id - ID_BUTTON_NO
        self.close()


def open(header="", text="", yeslabel=addon.LANG(107), nolabel=addon.LANG(106), extrabutton=False, path=""):
    """
    open yesnodialog, return -1 for cancelled, otherwise index (0-2)
    """
    xbmc.executebuiltin("Dialog.Close(busydialognocancel)")
    w = ConfirmDialog('DialogConfirm.xml', path,
                      yeslabel=yeslabel,
                      nolabel=nolabel,
                      header=header,
                      text=text,
                      extrabutton=extrabutton)
    w.doModal()
    return w.index

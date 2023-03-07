# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmc
import xbmcgui

from resources.kutil131 import addon

C_LABEL_HEADER = 1
C_LIST_SIMPLE = 3
C_LIST_DETAIL = 6
C_BUTTON_GET_MORE = 5
C_BUTTON_CANCEL = 7


class SelectDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.items = kwargs.get('listing')
        self.header = kwargs.get('header')
        self.detailed = kwargs.get('detailed')
        self.extrabutton = kwargs.get('extrabutton')
        self.listitems = [i.get_listitem() for i in self.items] if self.items else []
        self.index = -1
        self.list: xbmcgui.ControlList = None

    def onInit(self):
        if not self.listitems:
            self.index == -1
            self.close()
        self.list: xbmcgui.ControlList = self.getControl(C_LIST_DETAIL)
        self.getControl(C_LIST_DETAIL).setVisible(self.detailed)
        self.getControl(C_LIST_SIMPLE).setVisible(not self.detailed)
        self.getControl(C_BUTTON_GET_MORE).setVisible(bool(self.extrabutton))
        if self.extrabutton:
            self.getControl(C_BUTTON_GET_MORE).setLabel(self.extrabutton)
        self.getControl(C_LABEL_HEADER).setLabel(self.header)
        self.list.addItems(self.listitems)
        self.setFocus(self.list)

    def onClick(self, control_id):
        if control_id in [C_LIST_SIMPLE, C_LIST_DETAIL]:
            self.index = int(self.list.getSelectedPosition())
            self.close()
        elif control_id == C_BUTTON_GET_MORE:
            self.index = -2
            self.close()
        elif control_id == C_BUTTON_CANCEL:
            self.close()


def open(listitems, header: str, detailed=True, extrabutton=False) -> int:
    """
    open selectdialog, return index (-1 for closing, -2 for extra button)
    *listitems needs to be an iterable with ListItems (array, ItemList)
    """
    xbmc.executebuiltin("Dialog.Close(busydialognocancel)")
    w = SelectDialog('DialogSelect.xml', addon.PATH,
                     listing=listitems,
                     header=header,
                     detailed=detailed,
                     extrabutton=extrabutton)
    w.doModal()
    return w.index

#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.skinbackup
    Kodi addon to backup skin settings
'''

import xbmcgui
import xbmc


class DialogSelect(xbmcgui.WindowXMLDialog):
    '''Wrapper around Kodi dialogselect dialog'''
    list_control = None

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listing = kwargs.get("listing")
        self.windowtitle = kwargs.get("windowtitle")
        self.extrabutton = kwargs.get("extrabutton", "")
        self.autofocus = kwargs.get("autofocus", "")
        self.result = None

    def close_dialog(self, cancelled=False):
        '''close dialog and return value'''
        if cancelled:
            self.result = None
        else:
            self.result = self.list_control.getSelectedItem()
        self.close()

    def onInit(self):
        '''Initialization when the window is loaded'''

        # set correct list
        self.set_list_control()

        # set window header
        self.getControl(1).setLabel(self.windowtitle)

        self.list_control.addItems(self.listing)
        self.setFocus(self.list_control)

        # autofocus item if needed
        if self.autofocus:
            try:
                for count, item in enumerate(self.listing):
                    if item.getLabel().decode("utf-8") == self.autofocus:
                        self.list_control.selectItem(count)
            except Exception:
                self.list_control.selectItem(0)

    def onAction(self, action):
        '''Respond to Kodi actions e.g. exit'''
        if action.getId() in (9, 10, 92, 216, 247, 257, 275, 61467, 61448, ):
            self.close_dialog(True)

        # an item in the list is clicked
        if (action.getId() == 7 or action.getId() == 100) and xbmc.getCondVisibility(
                "Control.HasFocus(3) | Control.HasFocus(6)"):
            self.close_dialog()

    def onClick(self, controlID):
        '''Fires if user clicks one of the dialog buttons'''
        # special button
        if controlID == 5 and self.extrabutton:
            self.result = True
        self.close()

    def set_list_control(self):
        '''select correct list (3=small, 6=big with icons)'''
        try:
            # prefer list control 6
            self.list_control = self.getControl(6)
            self.list_control.setEnabled(True)
            self.list_control.setVisible(True)
            other_list = self.getControl(3)
            other_list.setEnabled(False)
            other_list.setVisible(False)
        except Exception:
            self.list_control = self.getControl(3)
            self.list_control.setEnabled(True)
            self.list_control.setVisible(True)

        self.set_cancel_button()
        self.getControl(5).setVisible(False)

        # show extra button
        if self.extrabutton:
            self.getControl(5).setVisible(True)
            self.getControl(5).setLabel(self.extrabutton)

    def set_cancel_button(self):
        '''set cancel button if exists'''
        try:
            self.getControl(7).setLabel(xbmc.getLocalizedString(222))
            self.getControl(7).setVisible(True)
            self.getControl(7).setEnabled(True)
        except Exception:
            pass
